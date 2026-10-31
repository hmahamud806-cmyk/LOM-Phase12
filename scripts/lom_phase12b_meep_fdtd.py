#!/usr/bin/env python3
"""Phase 12-B: 2D Meep FDTD benchmark for a symmetric Si3N4/SiO2 slab.

This is a numerical benchmark only. It is not the LOM architecture.
Units: micrometres; Meep time units use um / c.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import traceback
from pathlib import Path

import meep as mp
import numpy as np

# Phase 12-A analytical reference (Lipkowitz et al., APL Photonics 11, 046105, 2026)
WAVELENGTH_UM = 0.633
N_CORE = 2.014552744
N_CLAD = 1.457595676
CORE_THICKNESS_UM = 0.400
ANALYTICAL_NEFF = 1.930425598

CELL_X_UM = 12.0
CELL_Y_UM = 8.0
PML_UM = 1.5
SOURCE_X_UM = -3.5
MONITOR_HALF_SPAN_UM = 2.0
MONITOR_Y_HALF_SPAN_UM = 2.0


def run_one(resolution: int, run_time: float, output_dir: Path) -> dict:
    freq = 1.0 / WAVELENGTH_UM
    geometry = [
        mp.Block(
            size=mp.Vector3(mp.inf, CORE_THICKNESS_UM, mp.inf),
            center=mp.Vector3(),
            material=mp.Medium(epsilon=N_CORE**2),
        )
    ]
    sources = [
        mp.EigenModeSource(
            src=mp.GaussianSource(frequency=freq, fwidth=0.08 * freq, cutoff=5),
            center=mp.Vector3(SOURCE_X_UM, 0),
            size=mp.Vector3(0, 4.5),
            direction=mp.X,
            eig_band=1,
            eig_match_freq=True,
            eig_resolution=resolution,
        )
    ]
    sim = mp.Simulation(
        cell_size=mp.Vector3(CELL_X_UM, CELL_Y_UM),
        geometry=geometry,
        default_material=mp.Medium(epsilon=N_CLAD**2),
        boundary_layers=[mp.PML(PML_UM)],
        sources=sources,
        resolution=resolution,
        dimensions=2,
        Courant=0.5,
        eps_averaging=True,
        filename_prefix=f"phase12b_r{resolution}",
    )

    x_monitor = sim.add_dft_fields(
        [mp.Ez], freq, 0, 1,
        center=mp.Vector3(0, 0),
        size=mp.Vector3(2 * MONITOR_HALF_SPAN_UM, 0),
    )
    y_monitor = sim.add_dft_fields(
        [mp.Ez], freq, 0, 1,
        center=mp.Vector3(0, 0),
        size=mp.Vector3(0, 2 * MONITOR_Y_HALF_SPAN_UM),
    )

    sim.run(until=run_time)

    x_field = np.asarray(sim.get_dft_array(x_monitor, mp.Ez, 0)).squeeze()
    y_field = np.asarray(sim.get_dft_array(y_monitor, mp.Ez, 0)).squeeze()
    sim_time = float(sim.meep_time())

    if x_field.ndim != 1 or y_field.ndim != 1 or x_field.size < 10 or y_field.size < 10:
        raise RuntimeError(
            f"Unexpected DFT monitor array shapes: x={x_field.shape}, y={y_field.shape}"
        )

    x_um = np.linspace(-MONITOR_HALF_SPAN_UM, MONITOR_HALF_SPAN_UM, x_field.size)
    y_um = np.linspace(-MONITOR_Y_HALF_SPAN_UM, MONITOR_Y_HALF_SPAN_UM, y_field.size)

    amplitude_x = np.abs(x_field)
    mask = amplitude_x > max(amplitude_x.max() * 0.15, 1e-12)
    if int(mask.sum()) < 8:
        raise RuntimeError("Insufficient non-negligible field samples for phase fitting.")

    phase = np.unwrap(np.angle(x_field[mask]))
    slope, intercept = np.polyfit(x_um[mask], phase, 1)
    predicted = slope * x_um[mask] + intercept
    ss_res = float(np.sum((phase - predicted) ** 2))
    ss_tot = float(np.sum((phase - phase.mean()) ** 2))
    phase_fit_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    neff_fdtd = abs(float(slope)) / (2.0 * math.pi * freq)
    relative_error_pct = abs(neff_fdtd - ANALYTICAL_NEFF) / ANALYTICAL_NEFF * 100.0

    profile = np.abs(y_field)
    peak = float(profile.max())
    if peak <= 0:
        raise RuntimeError("The transverse DFT field profile is zero.")
    profile_norm = profile / peak

    profile_path = output_dir / f"lom_phase12b_field_profile_r{resolution}.csv"
    with profile_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["y_um", "abs_Ez", "normalized_abs_Ez"])
        writer.writerows(zip(y_um.tolist(), profile.tolist(), profile_norm.tolist()))

    return {
        "resolution_px_per_um": resolution,
        "simulated_time_um_over_c": sim_time,
        "fdtd_neff_phase_fit": neff_fdtd,
        "analytical_neff_reference": ANALYTICAL_NEFF,
        "relative_error_percent": relative_error_pct,
        "phase_fit_r2": phase_fit_r2,
        "x_monitor_samples": int(x_field.size),
        "y_monitor_samples": int(y_field.size),
        "field_profile_csv": profile_path.name,
        "status": "completed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolutions", nargs="+", type=int, default=[30, 45, 60, 80])
    parser.add_argument("--run-time", type=float, default=150.0)
    parser.add_argument("--output-dir", type=Path, default=Path("phase12b_results"))
    args = parser.parse_args()

    if any(r < 10 for r in args.resolutions):
        parser.error("Every resolution must be at least 10 pixels/um.")
    if args.run_time <= 0:
        parser.error("--run-time must be positive.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    errors = []
    resolution_plan = list(dict.fromkeys(args.resolutions))
    escalation_resolutions = [100, 120, 160]
    next_escalation = 0
    index = 0
    while index < len(resolution_plan):
        resolution = resolution_plan[index]
        index += 1
        print(f"\n=== Phase 12-B FDTD: resolution={resolution} px/um ===", flush=True)
        try:
            result = run_one(resolution, args.run_time, args.output_dir)
            results.append(result)
            print(json.dumps(result, indent=2), flush=True)
        except Exception as exc:
            error = {
                "resolution_px_per_um": resolution,
                "status": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            errors.append(error)
            print(json.dumps(error, indent=2), file=sys.stderr, flush=True)

        successful = sorted(results, key=lambda item: item["resolution_px_per_um"])
        if index >= len(resolution_plan) and len(successful) >= 2:
            last_two = successful[-2:]
            change_pct = abs(
                last_two[-1]["fdtd_neff_phase_fit"] - last_two[-2]["fdtd_neff_phase_fit"]
            ) / abs(last_two[-1]["fdtd_neff_phase_fit"]) * 100.0
            if change_pct > 0.5 and next_escalation < len(escalation_resolutions):
                next_resolution = escalation_resolutions[next_escalation]
                next_escalation += 1
                if next_resolution > max(item["resolution_px_per_um"] for item in successful):
                    resolution_plan.append(next_resolution)
                    print(
                        f"Convergence change is {change_pct:.4f}% (>0.5%); "
                        f"adding resolution {next_resolution}.",
                        flush=True,
                    )

    csv_path = args.output_dir / "lom_phase12b_convergence.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "resolution_px_per_um", "simulated_time_um_over_c",
            "fdtd_neff_phase_fit", "analytical_neff_reference",
            "relative_error_percent", "phase_fit_r2",
            "x_monitor_samples", "y_monitor_samples", "status",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fields})

    successful = sorted(results, key=lambda item: item["resolution_px_per_um"])
    convergence_change_pct = None
    if len(successful) >= 2:
        convergence_change_pct = abs(
            successful[-1]["fdtd_neff_phase_fit"] - successful[-2]["fdtd_neff_phase_fit"]
        ) / abs(successful[-1]["fdtd_neff_phase_fit"]) * 100.0
    converged = convergence_change_pct is not None and convergence_change_pct <= 0.5
    analytical_agreement = bool(successful) and successful[-1]["relative_error_percent"] <= 1.0

    report = {
        "phase": "12-B",
        "model": "2D lossless isotropic nondispersive symmetric slab FDTD benchmark",
        "wavelength_um": WAVELENGTH_UM,
        "core_material": "Si3N4",
        "cladding_material": "SiO2",
        "core_thickness_um": CORE_THICKNESS_UM,
        "analytical_neff_reference": ANALYTICAL_NEFF,
        "requested_resolutions_px_per_um": args.resolutions,
        "executed_resolutions_px_per_um": [r["resolution_px_per_um"] for r in successful],
        "convergence_change_last_two_percent": convergence_change_pct,
        "convergence_gate_passed_le_0_5_percent": converged,
        "analytical_agreement_gate_passed_le_1_percent": analytical_agreement,
        "run_time_um_over_c": args.run_time,
        "results": results,
        "errors": errors,
        "scientific_limitations": [
            "This is a symmetric slab benchmark, not the complete LOM architecture.",
            "The model uses frozen real refractive indices at one wavelength.",
            "Material dispersion, absorption, scattering, fabrication variation and 3D effects are excluded.",
            "No folds, bends, multilayer routing, coupling region or central core are modeled.",
            "A successful workflow run is not proof of experimental performance or novelty.",
            "Convergence and analytical agreement must be assessed from the generated data; no result is assumed in advance."
        ],
        "overall_status": (
            "simulation_error" if errors else
            "benchmark_gates_passed" if converged and analytical_agreement else
            "completed_but_gates_not_met"
        ),
    }
    report_path = args.output_dir / "lom_phase12b_fdtd_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {csv_path} and {report_path}", flush=True)
    return 1 if errors else (0 if converged and analytical_agreement else 2)


if __name__ == "__main__":
    raise SystemExit(main())
