import numpy as np
from scipy.optimize import fsolve


# ============================================================
#  YIELD MOMENT OF RC SHEAR WALL
# ============================================================

def compute_yield_moment_wall(
    wallLength,
    wallThickness,
    no_bars_bl,
    dbar1,
    fy1,
    Es,
    Ec,
    P,
    PW,
    covery,
    coverz,
    dhoop
):
    """
    Analytical yield moment of RC shear wall
    Yield defined by first yielding of boundary longitudinal steel
    """

    # --------------------------------------------------
    # Basic quantities
    # --------------------------------------------------
    N = P + PW                      # total axial load (N)
    eps_y = fy1 / Es                # steel yield strain

    # Boundary steel area (tension side)
    As_bar = np.pi * dbar1**2 / 4
    Asb = no_bars_bl * As_bar

    # Effective depth to boundary steel
    d = wallLength/2 - (covery + dhoop + dbar1/2)

    # --------------------------------------------------
    # Neutral axis depth c from equilibrium
    # --------------------------------------------------
    def equilibrium(c):
        kappa = eps_y / (d - c)
        Cc = 0.5 * Ec * kappa * c**2 * wallThickness   # concrete compression
        Ts = Asb * fy1                                # steel tension
        return N + Ts - Cc

    c0 = wallLength / 10
    c = fsolve(equilibrium, c0)[0]

    # --------------------------------------------------
    # Yield moment
    # --------------------------------------------------
    kappa = eps_y / (d - c)

    My = (
        Asb * fy1 * (d - c)
        + (1/3) * Ec * kappa * c**3 * wallThickness
    )

    return My


# ============================================================
#  SHEAR CAPACITY (ACI 318-25 / FEMA P-2208)
# ============================================================

def compute_shear_capacity_ACI(
    fc, fy2, rho_t, A_gross, driftHeight, wallLength
):
    """
    Returns V_CE in kN
    """

    ratio = driftHeight / wallLength

    if ratio <= 1.5:
        alpha = 3.0
    elif ratio >= 2.0:
        alpha = 2.0
    else:
        alpha = 3.0 - (ratio - 1.5) * (1.0 / 0.5)

    # Unit conversions
    fc_psi  = fc / 6894.76
    fy2_psi = fy2 / 6894.76
    A_in2   = A_gross / 0.00064516

    V_lb = (alpha * np.sqrt(fc_psi) + (rho_t/100) * fy2_psi) * A_in2
    V_kN = V_lb * 4.44822 / 1000

    return V_kN


# ============================================================
#  FEMA P-2208 CAPACITY-RATIO CLASSIFICATION
# ============================================================

def check_shear_flexure_dominance(V_CE, V_MCyE, limit=1.15):
    """
    FEMA P-2208 criterion
    Returns:
        ratio : V_CE / V_MCyE
        mode  : 'FLEXURE' or 'SHEAR_SUSCEPTIBLE'
    """
    ratio = V_CE / (V_MCyE / 1e3)

    if ratio >= limit:
        mode = "FLEXURE"
    else:
        mode = "SHEAR_SUSCEPTIBLE"

    return ratio, mode
