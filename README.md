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
- `WSH6_Master_Database_620_final_GitHub.xlsx` — Master database of 620 analytical specimens, including input parameters, response metrics, failure mode classifications, model-error bounds, and ML applicability indicators.

## Running the workflow

1. Create a Python 3.9 environment.
2. Install the packages listed in `requirements.txt`.
3. Start Jupyter in this directory.
4. Run `WSH6_analytical_database_620_clean.ipynb` from top to bottom.

The notebook uses relative paths only and creates its own `outputs/` directory.

## Numerical implementation details

The wall is modeled using a two-dimensional finite element model with a stack of line displacement-based elements using the distributed plasticity formulation. OpenSees displacement-based beam-column elements (`dispBeamColumn`) are used with two Gauss-Legendre integration points per element and fiber sections assigned to the integration points.

To address deformation localization associated with material softening, the regularization technique adopted in the previously validated modeling framework is retained. The region adjacent to the critical section, corresponding to the bottom-most nonlinear element of the cantilever wall, is modeled with a length equal to two times the estimated plastic-hinge length: $$2L_p$$

The plastic-hinge length is calculated as:

$$
L_p =
0.27l_w
\left(1-\frac{P}{A_w f'_c}\right)
\left(1-\frac{f_y\rho_t}{f'_c}\right)
\left(\frac{M}{Vl_w}\right)^{0.45}
$$

where the variables are defined as:

$$l_w = \text{wall length}$$, $$P = \text{axial force}$$, $$A_w = \text{wall cross-sectional area}$$, $$f_y = \text{reinforcement yield strength}$$, $$f'_c = \text{concrete compressive strength}$$, $$\rho_t = \text{horizontal web reinforcement ratio}$$, $$M,\;V = \text{moment and shear force at the wall base}$$.

The remaining nonlinear wall height is divided into equal-length displacement-based beam-column elements following the same discretization procedure. For the 620 analytical cases considered in the database, the nonlinear wall region is discretized into `dispBeamColumn` elements, depending on the case-specific plastic-hinge and strain-penetration lengths.

The effect of anchorage deformation, including slip and extension of reinforcing bars anchored into the foundation, is represented by adding a strain-penetration length to the wall height. In the OpenSeesPy implementation:

$$L_{sp}=0.022f_y d_b$$

where $$d_b$$ is longitudinal-bar diameter. Shear behavior is modeled as uncoupled from the flexural and axial behavior using a linear shear spring element at the base of the model.

Plain and confined concrete are modeled using the OpenSees `Concrete04` material. The concrete elastic modulus is calculated as $$E_c=4700\sqrt{f_c}$$ MPa. The strain at peak stress of the confined concrete is supplied by the previously developed ML model and is used as the calibration parameter of the finite element model. Longitudinal reinforcing bars are modeled using the OpenSees `ReinforcingSteel` material. Bar buckling is represented using the Gomes and Appleton formulation, and low-cycle fatigue is included through the corresponding fatigue formulation implemented in `ReinforcingSteel`. The OpenSees `MinMax` wrapper material is used to simulate tensile rupture when the specified ultimate tensile strain is exceeded. Shear behavior is modeled as uncoupled from the flexural and axial behavior using a linear shear spring element at the base of the model. The adopted effective shear modulus $$G_{\mathrm{eff}}=0.02E_c$$.

For the fiber-section discretization, the confined boundary regions are discretized into fibers in the in-plane direction. A constant fiber thickness is used to discretize the web region, while a single fiber is used in the out-of-plane direction. The reinforcing-fiber layout varies according to the reinforcement configuration defined in `Configurations_model_input.xlsx`.

All analytical specimens are subjected to the same cyclic displacement protocol adopted for WSH6. For each target displacement, the nominal displacement increment is defined as $$dU=\frac{\mathrm{maxU}}{150}$$. The gravity analysis uses the `NormDispIncr` convergence test with a tolerance of $$10^{-12}$$ and a maximum of 10 iterations, together with the `Newton` solution algorithm. The cyclic analysis uses `NormDispIncr` with a tolerance of $$10^{-6}$$ and a maximum of 1000 iterations. `NewtonLineSearch` is used as the primary solution algorithm. If convergence is not achieved for a displacement increment, the following fallback sequence is attempted: `ModifiedNewton → KrylovNewton → Broyden → BFGS`. Following a successful fallback step, the solution algorithm is reset to `NewtonLineSearch`. If all algorithms fail for a given increment, the displacement loop associated with that target is terminated and the analysis proceeds to the next target in the loading protocol.

The complete material definitions, section discretization, loading protocol, recorder definitions, and analysis procedures are provided in `run_FEmodel_webconf.py` and `run_FEmodel_boundconf.py`.

Note: The OpenSeespy model uses a linear uncoupled shear spring. FEMA P-2208 failure type classification labels in the generated database are therefore post-processed engineering assessments. They are not direct simulations of physical shear failure.
