"""Reference properties for the WSH6 reinforced-concrete wall specimen.

The experimental geometry, reinforcement layout, and reinforcing-steel
properties are based on WSH6 reported by Dazio, Beyer, and Bachmann (2009).
Values under ``FE-model implementation constants`` are retained from the
validated OpenSees model used in this study.

Reference
---------
Dazio, A., Beyer, K., & Bachmann, H. (2009). Quasi-static cyclic tests and
plastic hinge analysis of RC structural walls. Engineering Structures,
31(7), 1556-1571. https://doi.org/10.1016/j.engstruct.2009.02.018
"""

# =============================================================================
# Experimental reference properties (WSH6, Dazio et al., 2009)
# =============================================================================

# Geometry
wall_length = 2.000                 # m
wall_thickness = 0.150              # m
drift_height = 4.520                # m; lateral-load application height
shear_span_ratio = 2.26             # M/(V*lw)

# Measured reference concrete and axial load (metadata; not used in LHS runs)
reference_fc_mpa = 45.6             # MPa
reference_axial_load_kn = 1522.27    # kN
reference_alr_percent = 11.13        # %

# Reinforcement ratios used in the analytical design matrix are read from
# Configurations_model_input.xlsx to preserve the published rounding convention.

# Boundary longitudinal reinforcement
boundary_bar_diameter = 0.012       # m; 6 phi-12 per boundary region
boundary_bars_per_region = 6
fy_boundary = 576.0e6               # Pa; D12
fu_boundary = 674.9e6               # Pa; D12

# Longitudinal web reinforcement
web_bar_diameter = 0.008            # m; 22 phi-8 total
web_bar_spacing = 0.125             # m; nominal spacing
web_face_count = 2
web_bars_per_face = 11
fy_web = 583.7e6                    # Pa; D8
fu_web = 714.4e6                    # Pa; D8

# Horizontal web reinforcement

# Boundary confinement reinforcement
hoop_diameter = 0.006               # m; D6
confinement_spacing = 0.050         # m
fy_hoop = 518.9e6                   # Pa; D6
fu_hoop = 558.7e6                   # Pa; D6


# =============================================================================
# FE-model implementation constants
# =============================================================================
# These values are retained from the experimentally validated WSH6 OpenSees
# model used to generate the analytical database.

loading_beam_height = 0.500         # m
loading_beam_volume = 0.681         # m^3
concrete_density = 2500.0           # kg/m^3
gravity = 9.81                      # m/s^2

cover_y = 0.020                     # m; in-plane concrete cover
cover_z = 0.020                     # m; out-of-plane concrete cover

# Confined boundary-region dimensions used in the validated WSH6 FE model.
boundary_depth = 0.150              # m; out-of-plane dimension
boundary_width = 0.385              # m; in-plane dimension

source_citation = (
    "Dazio, A., Beyer, K., & Bachmann, H. (2009). Quasi-static cyclic tests "
    "and plastic hinge analysis of RC structural walls. Engineering "
    "Structures, 31(7), 1556-1571."
)
