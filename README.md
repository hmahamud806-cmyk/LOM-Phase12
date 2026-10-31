# LOM-Phase12

Living Optical Matrix — Phase 12 computational execution workspace.

## Phase 12-B: Meep runtime preparation

The repository currently contains a manually triggered GitHub Actions workflow that checks whether the Meep runtime can be installed and imported on an Ubuntu runner.

### Run the environment check

1. Open the **Actions** tab.
2. Select **Phase 12-B — Meep environment check**.
3. Press **Run workflow** and confirm.
4. Open the completed run and inspect the **meep-environment-report** artifact.

The workflow uses the Conda environment in `environment.yml` and runs `scripts/check_meep_environment.py`.

## Scientific status — important

**The current workflow is an environment check only. It does not run FDTD, calculate effective index, produce field profiles, test convergence, or validate the LOM architecture.**

The analytical slab benchmark recorded in the project notes is a reference case only. The next implementation step is to add and independently review the Phase 12-B FDTD model before claiming any simulation result.

No material, geometry, or optical-performance claim is established by a successful environment check.
