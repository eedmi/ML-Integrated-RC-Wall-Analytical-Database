# An Analytical Database for Reinforced Concrete Structural Walls Based on an Experimentally Validated ML-Integrated Modeling Framework

This folder contains the reproducible OpenSeesPy model used to generate the 620-specimen analytical database accompanying the manuscript **“An Analytical Database for Reinforced Concrete Structural Walls Based on an Experimentally Validated ML-Integrated Modeling Framework.”**

## Main files

- `RC_analytical_database_generation.ipynb` — end-to-end database-generation workflow
- `run_FEmodel_webconf.py` — FE driver for web-reinforcement configurations
- `run_FEmodel_boundconf.py` — FE driver for boundary-reinforcement configurations
- `wsh6_reference.py` — fixed WSH6 geometry and material reference properties
- `predict_peakconfstrain_110.py` — ML-assisted confined-concrete peak-strain predictor
- `fema_p2208_classification.py` — FEMA P-2208 failure mode classification routine
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

## Numerical implementation details

The nonlinear wall model is implemented in OpenSeesPy using fiber-based `dispBeamColumn` elements with a `Linear` geometric transformation. The first nonlinear element has a length of \(2L_P\), where

$$
L_P = 0.27 l_w (1-ALR)
\left(1-\frac{f_y \rho_t}{f'_c}\right)
\left(\frac{M}{V l_w}\right)^{0.45}
$$

The remaining nonlinear wall height is divided into equal-length elements according to the same discretization procedure used in the previously validated model (Tahaei et al. 2026). Across the 620 analytical cases, the wall is represented by 3–6 nonlinear `dispBeamColumn` elements.

Each nonlinear element uses two-point Legendre integration with the same fiber section assigned at both integration points. The section consists of two confined boundary-core concrete patches discretized with 32 × 1 fibers each, together with unconfined cover and web-concrete patches. For the fixed WSH6 geometry, the section contains 558 concrete fibers; the reinforcing-fiber layout varies according to the reinforcement configuration.

Concrete is modeled using `Concrete04`, while longitudinal reinforcement is modeled using `ReinforcingSteel` with the `-GABuck` buckling and `-CMFatigue` low-cycle-fatigue formulations. `MinMax` wrappers impose the tensile rupture-strain limit. No additional constitutive regularization is applied beyond the adopted element and fiber discretization, which follows the previously validated implementation.

Strain penetration is represented by extending the effective wall height by
$$
L_{sp} = 0.022 f_y d_b
$$

rather than through a separate bond-slip element. Shear response is represented by an uncoupled zero-length spring at the wall base with elastic lateral stiffness of 0.02.

All analytical cases are subjected to the same WSH6 cyclic displacement protocol. For each target displacement, the nominal displacement increment is defined as `dU = maxU/150`. Gravity analysis uses a `NormDispIncr` convergence test with a tolerance of \(10^{-12}\) and a maximum of 10 iterations with the `Newton` algorithm. The cyclic analysis uses `NormDispIncr` with a tolerance of \(10^{-6}\) and a maximum of 1000 iterations. `NewtonLineSearch` is used as the primary solution algorithm. If convergence is not achieved, the following fallback sequence is applied:`ModifiedNewton → KrylovNewton → Broyden → BFGS`

Following a successful fallback step, the analysis returns to `NewtonLineSearch`. If all algorithms fail for a given increment, the displacement loop associated with that target is terminated and the analysis proceeds to the next target in the loading protocol.

The complete material definitions, section generation, loading sequence, recorder definitions, and analysis procedures are provided directly in `run_FEmodel_webconf.py` and `run_FEmodel_boundconf.py`.

Note: The OpenSeespy model uses a linear uncoupled shear spring. FEMA P-2208 failure type classification labels in the generated database are therefore post-processed engineering assessments. They are not direct simulations of physical shear failure.
