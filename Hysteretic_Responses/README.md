# Hysteretic Responses

This folder contains the complete point-by-point cyclic force-displacement histories for the 620 analytical specimens.

Each CSV file contains:

- `Top_Displacement_mm`: top-node lateral displacement, converted from the OpenSees `TopDisp.out` recorder from m to mm.
- `Base_Shear_kN`: lateral base shear, obtained from the horizontal base reaction in `RBase.out` and reported with the sign convention that positive shear corresponds to positive top displacement.

The histories are provided without envelope extraction, resampling, smoothing, or downsampling.

File names follow the analytical-database specimen identifiers. For consistency with the final database, `Base model` is written as `Base_model`, and `W-HL3` is written as `W-HL-3`.
