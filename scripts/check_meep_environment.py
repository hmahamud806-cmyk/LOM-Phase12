"""Check that the Phase 12-B Meep runtime is available.

This is an environment check only. It does not run an FDTD simulation and
must not be interpreted as a numerical result.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import meep as mp


def main() -> None:
    required = ("Simulation", "Vector3", "Medium", "ContinuousSource")
    missing = [name for name in required if not hasattr(mp, name)]
    if missing:
        raise RuntimeError(f"Meep import succeeded, but APIs are missing: {missing}")

    report = {
        "check": "meep_environment",
        "status": "passed",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "meep_version": getattr(mp, "__version__", "not exposed by this build"),
        "required_api": {name: hasattr(mp, name) for name in required},
        "simulation_executed": False,
        "note": "Environment verification only; no FDTD result was generated.",
    }
    output = Path("meep_environment_report.json")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
