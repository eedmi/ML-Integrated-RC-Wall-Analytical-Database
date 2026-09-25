# An Analytical Database for Reinforced Concrete Structural Walls Based on an Experimentally Validated ML-Integrated Modeling Framework

This folder contains the reproducible OpenSeesPy model used to generate the 620-case WSH6-centered analytical database accompanying the manuscript **“An Analytical Database for Reinforced Concrete Structural Walls Based on an Experimentally Validated ML-Integrated Modeling Framework.”**

## Main files

- `RC_analytical_database_generation.ipynb` — end-to-end database-generation workflow
- `run_FEmodel_webconf.py` — FE driver for web-reinforcement configurations
- `run_FEmodel_boundconf.py` — FE driver for boundary-reinforcement configurations
- `wsh6_reference.py` — fixed WSH6 geometry and material reference properties
- `predict_peakconfstrain_110.py` — ML-assisted confined-concrete peak-strain predictor
- `failure_type.py` — FEMA P-2208 failure mode classification routine
- `Configurations_model_input.xlsx` — 31 reinforcement configurations used by the FE workflow
- `WSH6_measured.csv` — experimental WSH6 response used in the reference-model comparison
- `PublicUse/MLmodel/110-Walls/` — ML calibration models and scaling/support files
- `MODEL_DOCUMENTATION.md` — detailed implementation documentation

## Running the workflow

1. Create a Python 3.9 environment.
2. Install the packages listed in `requirements.txt`.
3. Start Jupyter in this directory.
4. Run `WSH6_analytical_database_620_clean.ipynb` from top to bottom.

The notebook uses relative paths only and creates its own `outputs/` directory.



See `MODEL_DOCUMENTATION.md` for element discretization, integration points, fiber discretization, constitutive models, strain penetration, shear-spring formulation, loading increments, convergence criteria, fallback algorithms, recorder outputs, and limitations.

Note: The OpenSeespy model uses a linear uncoupled shear spring. FEMA P-2208 failure type classification labels in the generated database are therefore post-processed engineering assessments. They are not direct simulations of physical shear failure.
