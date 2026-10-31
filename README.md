# LOM-Phase12

Living Optical Matrix — Phase 12 computational execution workspace.

## Phase 12-B: Meep environment check

The manually triggered workflow **Phase 12-B — Meep environment check** verifies that Meep and its required APIs can be installed and imported. This check does not run an FDTD simulation.

## Phase 12-B: 2D Meep FDTD slab benchmark

A separate manually triggered workflow now runs the first numerical benchmark using the Phase 12-A symmetric Si3N4/SiO2 slab reference.

### Run the FDTD benchmark

1. Open the **Actions** tab.
2. Select **Phase 12-B — Meep FDTD slab benchmark**.
3. Press **Run workflow**. Keep the default run time of 150 unless the Director changes it.
4. Wait for the job to finish.
5. Open the **phase12b-fdtd-results** artifact. It contains the convergence CSV, transverse field profiles and JSON report.

The workflow runs `scripts/lom_phase12b_meep_fdtd.py` at 30, 45, 60 and 80 pixels/µm. If the last two successful effective-index estimates differ by more than 0.5%, it automatically adds higher resolutions (100, 120, then 160 pixels/µm).

### Acceptance gates

- The final two successful resolutions must differ by no more than 0.5%.
- The finest-resolution FDTD effective-index estimate must agree with the Phase 12-A analytical reference (neff = 1.930425598) within 1%.
- The report records the measured values and whether each gate passed. A workflow exit code indicating that a gate was not met is not a successful scientific validation; it is a reason to inspect the data and method.

## Scientific limits

This is only a 2D, symmetric, lossless, isotropic, nondispersive slab benchmark at 0.633 µm using frozen real refractive indices. It excludes material dispersion, absorption, scattering, fabrication variation and 3D effects. It does not model LOM folds, bends, multilayer routing, coupling, reconvergence or the central core. Passing this benchmark does not validate the complete LOM architecture, experimental performance, fabrication feasibility or novelty.

**The architecture must follow physics. Physics must never be altered to protect the architecture.**
