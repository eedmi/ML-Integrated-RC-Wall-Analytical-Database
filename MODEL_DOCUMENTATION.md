# OpenSeesPy model documentation

## 1. Scope and model family

This directory contains the OpenSeesPy implementation used to generate the WSH6-centered analytical database. The published analytical cases retain the WSH6 wall geometry, shear-span ratio, fixed-base condition, and cyclic displacement protocol while varying concrete compressive strength, axial-load ratio, and reinforcement detailing.

Two FE drivers are used:

- `run_FEmodel_webconf.py`: web-reinforcement configurations, with the WSH6 boundary reinforcement retained.
- `run_FEmodel_boundconf.py`: boundary-reinforcement configurations, with the WSH6 web reinforcement retained.

The numerical model is fiber-based and is intended to reproduce global nonlinear cyclic response and deformation capacity. Shear is represented by an uncoupled **linear** base spring. Accordingly, the FEMA P-2208 shear-susceptibility labels are post-processed engineering classifications and are not direct simulations of diagonal cracking, cyclic shear degradation, shear pinching, or nonlinear flexure-shear interaction.

## 2. Geometry and boundary conditions

Reference geometry is defined in `wsh6_reference.py`:

- wall length, \(l_w\) = 2.000 m
- wall thickness, \(t_w\) = 0.150 m
- lateral-load application height = 4.520 m
- loading-beam height = 0.500 m
- shear-span ratio, \(M/(Vl_w)\) = 2.26
- in-plane and out-of-plane concrete cover = 0.020 m
- boundary-region width = 0.385 m
- boundary-region thickness = 0.150 m

The OpenSees model is two-dimensional with three DOFs per node. Node 1 is fully fixed. Nodes 1 and 2 are coincident and connected by a zero-length spring. Nonlinear wall elements extend from node 2 to the wall/loading-beam intersection. The final 0.500 m loading-beam segment is modeled as an `elasticBeamColumn` with elastic modulus \(25E_c\).

## 3. Element formulation and element lengths

The nonlinear wall is modeled with `dispBeamColumn` elements using a `Linear` geometric transformation.

The first nonlinear element length is defined as twice the plastic-hinge length:

\[
L_1 = 2L_P
\]

with

\[
L_P = 0.27l_w(1-ALR)\left(1-\frac{f_y\rho_t}{f'_c}\right)\left(\frac{M}{Vl_w}\right)^{0.45},
\]

where the implementation receives ALR and reinforcement ratios in percentage form and applies the corresponding `/100` conversion in the code.

Strain penetration is represented by extending the effective wall height by

\[
L_{sp}=0.022 f_y d_b,
\]

where \(f_y\) is expressed in MPa and \(d_b\) in m in the implementation.

The nonlinear wall height used for element discretization is

\[
H = L_{sp} + (4.520-0.500)\;\text{m}.
\]

After the first element, the remaining height is divided into equal-length `dispBeamColumn` elements using

`topDiv = ceil((H - 2*LP)/(2*LP))`.

For the published 620-case design, the resulting discretization spans approximately:

- strain-penetration length: 0.127–0.228 m
- first nonlinear-element length: 0.741–1.461 m
- remaining nonlinear-element length: 0.665–1.390 m
- number of nonlinear `dispBeamColumn` elements: 3–6

The exact case-specific values are determined from the input parameters by the formulas above during model generation.

## 4. Numerical integration

Each nonlinear `dispBeamColumn` element uses:

- integration rule: `Legendre`
- number of integration points: 2
- fiber section tag: 1

The same fiber section is used at each integration point.

## 5. Fiber-section discretization

The section is constructed with OpenSees `Fiber`, `patch('quad', ...)`, and `layer('straight', ...)` commands.

### Concrete fibers

- Two confined boundary-core patches: 32 x 1 fibers each.
- Cover and web concrete patches use a characteristic subdivision size based on `hoopLength/32`.
- With the fixed WSH6 geometry, this produces 558 concrete fibers in total: 64 confined-core fibers and 494 unconfined-cover/web fibers.

### Reinforcing fibers

Boundary longitudinal reinforcement is represented by four straight steel layers (top/bottom on each boundary region). Web longitudinal reinforcement is represented by two straight layers, one on each wall face. The number and bar area of reinforcing fibers change according to the configuration definition.

The configuration inputs used by the model are provided in `Configurations_model_input.xlsx`.

## 6. Concrete constitutive model and calibration

Concrete is modeled with `Concrete04`:

- material 1: confined concrete
- material 2: unconfined concrete

Concrete elastic modulus and tensile strength are computed as

\[
E_c = 4700\sqrt{f'_c}\ \text{MPa},
\]

and

\[
f_t = 0.333\sqrt{f'_c}\ \text{MPa},
\]

with unit conversions carried out in the Python implementation.

Confined concrete strength is evaluated as

\[
f'_{cc}=f'_c\left(1+\rho_{sh}f_{yh}/f'_c\right).
\]

The peak confined-concrete strain is supplied by the previously developed ML calibration model in `PublicUse/MLmodel/110-Walls/`. The predictor is an equal-weight ensemble of KRR, SVR, and GPR models. The eight input features passed to the model are, in implementation order:

1. axial-load ratio (ALR, %)
2. wall length (mm)
3. lateral-load application height (mm)
4. horizontal web reinforcement ratio \(\rho_t\) (%)
5. wall length/thickness ratio
6. \(f_{y,b}\rho_l\)
7. \(f_{y,v}\rho_v\)
8. confined boundary-core area \(A_{cc}\) (mm²)

The calibration files include the training-range scaling data (`XtrainMin.txt`, `XtrainMax.txt`), model files, and training-feature table.

The ML component provides an internal constitutive-calibration quantity; it does not directly predict wall lateral strength, ultimate displacement, or ductility.

## 7. Reinforcing-steel constitutive model

Longitudinal reinforcing steel is modeled with `ReinforcingSteel`, including the `-GABuck` buckling formulation and `-CMFatigue` low-cycle-fatigue formulation. `MinMax` wrappers are used to impose the tensile rupture-strain limit.

Reference steel properties in `wsh6_reference.py` are:

- boundary longitudinal steel: \(f_y\) = 576.0 MPa, \(f_u\) = 674.9 MPa
- web longitudinal steel: \(f_y\) = 583.7 MPa, \(f_u\) = 714.4 MPa
- hoop steel: \(f_y\) = 518.9 MPa, \(f_u\) = 558.7 MPa
- steel elastic modulus: 200 GPa

Additional rupture, hardening, buckling, and fatigue parameters are calculated directly in `run_FEmodel_webconf.py` and `run_FEmodel_boundconf.py` and are retained in the public implementation.

## 8. Strain-penetration treatment

Strain penetration is not modeled with a separate bond-slip element. Instead, the wall height is extended by the strain-penetration length \(L_{sp}\), calculated as described in Section 3. The displacement-controlled loading node is therefore located at `driftHeight + Lsp`.

## 9. Shear-spring formulation

Shear response is represented by an uncoupled zero-length base spring between nodes 1 and 2. The lateral spring uses an elastic uniaxial material with stiffness

\[
K_s = 0.02 E_c A_g,
\]

where \(A_g=t_wl_w\). The remaining zero-length directions are assigned a stiffness of \(10^{16}\) to constrain those degrees of freedom.

This shear spring remains linear throughout the analysis. It does not model nonlinear shear damage or flexure-shear interaction.

## 10. Gravity loading

The externally applied axial load is computed from the sampled ALR as

\[
P = ALR\,A_gf'_c-P_W,
\]

where ALR is converted from percent to a fraction and \(P_W\) is the wall/loading-beam self-weight contribution.

Gravity analysis uses:

- equation system: `BandGeneral`
- constraint handler: `Transformation`
- DOF numberer: `RCM`
- convergence test: `NormDispIncr`, tolerance \(10^{-12}\), maximum 10 iterations
- solution algorithm: `Newton`
- integrator: `LoadControl`, increment 0.1
- 10 analysis steps

After gravity loading, loads are held constant and analysis time is reset with `loadConst('-time', 0.0)`.

## 11. Cyclic loading protocol and displacement increments

All analytical cases use the same WSH6 target-displacement sequence (m):

`[0.0094934, -0.0085847, 0.0104020, -0.0098859, 0.0257800, -0.0321520, 0.0254130, -0.0263880, 0.0377780, -0.0392380, 0.0448240, -0.0396110, 0.0512100, -0.0515270, 0.0518330, -0.0509550, 0.0646990, -0.0644790, 0.0653210, -0.0638100, 0.0776150, -0.0781410, 0.0775790, -0.0777940, 0.0947030, -0.0908150]`.

For each target displacement `maxU`, the nominal displacement increment is

`dU = maxU / 150`.

The cyclic analysis uses `DisplacementControl(pushNode, 1, dU, 10, dU, dU)`, so the minimum and maximum increments are equal to the nominal increment used for that target.

## 12. Cyclic convergence test and solution algorithms

The cyclic analysis uses:

- convergence test: `NormDispIncr`
- tolerance: \(10^{-6}\)
- maximum iterations: 1000
- primary algorithm: `NewtonLineSearch`

If an increment fails, the following fallback sequence is attempted:

1. `ModifiedNewton`
2. `KrylovNewton`
3. `Broyden`
4. `BFGS`

After a successful fallback step, the algorithm is reset to `NewtonLineSearch` for the next increment.

If all algorithms fail for an increment, the inner displacement loop for that target is terminated. The outer loading-protocol loop then proceeds to the next target. The published database retains the response actually obtained from the analysis, and the response-extraction procedure uses the recorded response history.

## 13. Recorder outputs

For each case, the FE model writes:

- `TopDisp.out`: top-node lateral displacement
- `RBase.out`: base reactions
- `StWest.out`, `StEast.out`: selected boundary-steel response histories
- `ConCoreWest.out`, `ConCoreEast.out`: selected confined-core concrete response histories
- `ConCoverWest.out`, `ConCoverEast.out`: selected cover-concrete response histories

The database-generation notebook uses `TopDisp.out` and `RBase.out` for global response extraction. Local-response recorder files were used for the supplemental WSH6 validation assessment but are not reported as analytical-database response variables.

## 14. FEMA P-2208 engineering classification

`failure_type.py` performs the post-processing capacity-ratio classification. The nominal shear capacity \(V_{CE}\) is compared with the shear associated with flexural yielding \(V_{MCyE}\). A case is labeled flexure-dominated when

\[
V_{CE}/V_{MCyE} \ge 1.15.
\]

Cases below this threshold are labeled shear-susceptible. These labels are derived engineering classifications and should not be interpreted as direct numerical reproduction of physical shear failure.

## 15. Reproduction workflow

Run `WSH6_analytical_database_620_clean.ipynb` from the repository directory. The notebook:

1. reads the 31 configurations from `Configurations_model_input.xlsx`;
2. runs the WSH6 reference model and compares it with `WSH6_measured.csv`;
3. generates the common 20-point two-dimensional LHS using seed 120;
4. crosses the common LHS with all 31 configurations;
5. runs the 620 nonlinear analyses with checkpointing;
6. post-processes the response histories and exports the analytical database.

The notebook uses repository-relative paths and creates an `outputs/` directory at run time.

## 16. Implementation limitations

- Geometry, shear-span ratio, fixed-base condition, and loading protocol are fixed to the WSH6-centered model family.
- Shear is modeled with a linear uncoupled spring; nonlinear shear damage is not simulated.
- The ML model is used for confined-concrete peak-strain calibration rather than direct response prediction.
- Ultimate displacement and ductility are conditional on the adopted WSH6 cyclic loading sequence and the response-extraction definitions used in the companion database workflow.
