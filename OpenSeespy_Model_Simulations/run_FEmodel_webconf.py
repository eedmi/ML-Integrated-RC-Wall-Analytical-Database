"""OpenSees model for WSH6-based web-reinforcement configurations.

Fixed specimen properties are imported from :mod:`wsh6_reference`; only the
configuration variables and LHS-sampled concrete strength/axial-load ratio are
passed to :func:`run_wall_model`.
"""

import openseespy.opensees as op
from predict_peakconfstrain_110 import predict_peakconfstrain_110
import math
import numpy as np
import os
import wsh6_reference as ref

from fema_p2208_classification import (
    compute_yield_moment_wall,
    compute_shear_capacity_ACI,
    check_shear_flexure_dominance
)


def run_wall_model(case_id, fc_MPa, ALR, rho_bl, rho_sh, rho_t,
                   dbar, webspacing,
                   calibration_dir, output_root, disps):

    print("\n---------------------------------------------------")
    print(f"Running virtual specimen: {case_id}")
    print("---------------------------------------------------")

    op.wipe()

    case_output_dir = os.path.join(output_root, str(case_id))
    os.makedirs(case_output_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # WSH6 REFERENCE GEOMETRY AND FIXED REINFORCEMENT
    # -------------------------------------------------------------------------
    # Fixed reference quantities are defined once in wsh6_reference.py
    # (WSH6, Dazio et al., 2009).
    wallthickness = ref.wall_thickness
    wallLength = ref.wall_length
    A_gross = wallthickness * wallLength

    Loadingbeam = ref.loading_beam_height
    driftHeight = ref.drift_height
    netHeight = driftHeight - Loadingbeam
    M_Vlw = ref.shear_span_ratio

    # -------------------------------------------------------------------------
    # REINFORCEMENT INPUTS FROM DESIGN MATRIX
    # -------------------------------------------------------------------------
    rho_bl = float(rho_bl)
    rho_sh = float(rho_sh)
    rho_t = float(rho_t)

    dbar2 = float(dbar) * 1e-3
    webspacing = float(webspacing) * 1e-3

    # Boundary reinforcement remains fixed at the WSH6 reference layout.
    fy1 = ref.fy_boundary
    fy2 = ref.fy_web
    dhoop = ref.hoop_diameter
    dbar1 = ref.boundary_bar_diameter
    no_bars_bl = ref.boundary_bars_per_region

    covery = ref.cover_y
    coverz = ref.cover_z
    bo = ref.boundary_depth
    do = ref.boundary_width

    Acc = ((bo - 2 * coverz) * (do - 2 * covery)) * 2
    if rho_sh == 0:
        Acc = 0
        print("No Boundary Confinement!")

    # -------------------------------------------------------------------------
    # WEB REINFORCEMENT
    # -------------------------------------------------------------------------
    wall_web_length = wallLength - 2 * do
    wall_web_length = math.floor(wall_web_length * 10) / 10

    no_face_web = ref.web_face_count
    no_bars_web = math.floor(
        (wall_web_length - 2 * webspacing) / webspacing
    ) + 1

    # Preserve the experimentally observed WSH6 base layout exactly:
    # 22 phi-8 longitudinal web bars = 11 bars per face.
    if (
        math.isclose(dbar2, ref.web_bar_diameter, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(
            webspacing, ref.web_bar_spacing, rel_tol=0.0, abs_tol=1e-12
        )
    ):
        no_bars_web = ref.web_bars_per_face

    As2 = math.pi * dbar2**2 / 4.0

    # Nominal longitudinal web reinforcement ratio. The ratio is defined from
    # bar area, nominal spacing, wall thickness, and number of reinforced faces.
    rho_l_computed = (
        no_face_web * As2 / (webspacing * wallthickness)
    ) * 100.0

    # Total vertical steel ratio used by the inherited ML calibration feature.
    # This term intentionally uses the actual discrete bar areas in the fiber
    # section and is distinct from the nominal spacing-based rho_l definition.
    A_v = (
        2 * no_bars_bl * math.pi * (dbar1**2 / 4)
        + no_bars_web * no_face_web * As2
    )

    rho_v = A_v / A_gross
    fy_v = np.mean([fy1, fy2])

    # -------------------------------------------------------------------------
    # MATERIAL PROPERTIES FROM LHS
    # -------------------------------------------------------------------------
    fc = float(fc_MPa) * 1e6

    fy_sh = ref.fy_hoop
    fcc = fc * (1 + rho_sh / 100 * fy_sh / fc)

    ep0TH = -0.002
    epc0TH = -0.0023788
    epuTH = -0.0034255
    epcuTH = -0.032935

    # -------------------------------------------------------------------------
    # AXIAL LOAD FROM LHS ALR
    # ALR is supplied in percent: 5–45
    # -------------------------------------------------------------------------
    PW = (wallthickness * wallLength * netHeight + ref.loading_beam_volume) * ref.concrete_density * ref.gravity

    P = float(ALR/100) * wallthickness * wallLength * fc - PW

    # -------------------------------------------------------------------------
    # STEEL MATERIAL PARAMETERS
    # -------------------------------------------------------------------------
    E1 = 200.0e9
    E2 = E1

    fu1 = ref.fu_boundary
    fu2 = ref.fu_web

    eRup1 = 0.6 * (1 - fy1 / fu1)
    eRup2 = 0.6 * (1 - fy2 / fu2)

    esh1 = min(0.03, 0.1 * fy1 / fu1 - 0.055)
    esh2 = min(0.03, 0.1 * fy2 / fu2 - 0.055)

    Esh1 = (fu1 - fy1) / (0.4 * (eRup1 - esh1))
    Esh2 = (fu2 - fy2) / (0.4 * (eRup2 - esh2))

    hoopLength = do - covery * 2
    
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Model calibration process
    myfeatures =  [ALR, wallLength*1000, driftHeight*1000, rho_t, wallLength/wallthickness, fy1/1e6*rho_l_computed, fy_v/1e6*rho_v*100, Acc*1e6]
    
    epc0M_formula = predict_peakconfstrain_110(myfeatures, root=calibration_dir)
    #epc0M = -0.0029850; # Peak strain of the CONFINED concrete; modify this value for calibration
    epc0M = -epc0M_formula ;
    ep0M =  (epc0M/epc0TH)*ep0TH ; # Evaluating the modified peak strain of PLAIN concrete using the modified peak strain of confined concrete
    epuM =  epuTH + (ep0M - ep0TH) ; #  Evaluating the modified ultimate strain of PLAIN concrete
    epcuM =  epcuTH + (epc0M - epc0TH) ; # Evaluating the modified ultimate strain of CONFINED concrete
    #  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    #concrete
    #  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    # Continuing the analysis using the calibrated concrete parameters (i.e. ep0M, epuM, epc0M, epcuM)
    # Complementary data for the concrete material
    ft = 0.333*(fc**0.5)*1000; # Concrete tensile strength in Pascals ( Vecchio & Collins (1986)
    Ec = 4700*fc**0.5*1000; # Initial Young's modulus of concrete in Pascals (ACI 318-11)
    
    # Analysis parameters
    numIncrs = 150 ; # Number of steps to reach a certain displacement
    
    factorLP = 2.0 ; # Length of the first displacement-based element (dispBeamColumn) is assumed as plastic hinge length times factorLP
    intType = "Legendre" ; #The utilised numerical integration technique
    numIntgrPts = 2 ; # Number of integration points along each displacement-based element
    
    #Geometry & section parameters
    #Lsp = 0.135 ; # Strain penetration length (in metres) per (Priestley et al, 2007)
    Lsp = 0.022*fy1/1e6*dbar1;
    LP = 0.27*wallLength*(1-ALR/100)*(1-fy1*(rho_t/100)/fc)*(M_Vlw**0.45); # Plastic hinge length (Kazaz, 2013)
    
    
    height = Lsp + netHeight ;
    #print("Wall height + Length of strain penetration is:", height, " (m)")
    
    topDiv = math.ceil((height - factorLP*LP)/(factorLP*LP)); # Number of wall divisions apart from the first element
    #print("Wall has been divided into ", topDiv + 1, " elements")
    meetPoint = int(topDiv + 3) ; # The point RC wall meets (intersects with) the loading beam
    #print ("The RC wall meets (intersects with) the loading beam @ node:", meetPoint)
    pushNode = int(meetPoint + 1) ; # The point cyclic lateral load is applied by means of hydraulic jacks
    
    print (" ")
    #print ("Calibrated peak strain of the plain concrete is ", ep0M)
    #print ("Calibrated ultimate strain value of unconfined concrete is ", epuM)
    print ("Calibrated peak strain of the confined concrete is ",  epc0M)
    
    
    # Create ModelBuilder (with two-dimensions and 3 DOF/node)
    op.model('basic', '-ndm', 2, '-ndf', 3)
    op.node(1, 0.0, 0.0)
    op.node(2, 0.0, 0.0)
    node3Height = factorLP* LP
    op.node(3, 0.0, node3Height)
    #print ( "Height of node 3 is: ", 0.001*math.ceil(1000.0*node3Height), " (m)")
    for ii in range(4,meetPoint+1):
        nodeHeight = node3Height + (ii - 3)*(height - node3Height)/topDiv
     #   print("Height of node ",ii, " is:", 0.001*math.ceil(1000.0*nodeHeight)," (m)")
        op.node(ii, 0.0, nodeHeight)
    
    op.node(ii+1, 0.0, (Lsp+driftHeight))
    print("Height of the hydraulic jack impact + strain penetration length (node ",ii," is ",0.001*math.ceil(1000.0*(Lsp + driftHeight))," (m)")
    print("---------------------------------------------------")
    
    # Fix support at the base of the wall
    #    tag   DX   DY   RZ
    op.fix  (1,1,1,1)
    
    #Define materials for the nonlinear wall
    # ------------------------------------------
    # CONCRETE
    # lambda and Ets from [3]
    
    # uniaxialMaterial Concrete04    $matTag   $fc    $ec     $ecu   $Ec   <$fct $et>   <$beta>
    op.uniaxialMaterial ('Concrete04',		1,     -fcc,  epc0M,  epcuM,  Ec,    ft,  0.00045,  0.1) ; # Confined concrete
    op.uniaxialMaterial ('Concrete04',		2,     -fc,  ep0M,  epuM,   Ec,    ft,  0.00045,  0.1)  ; # Plain concrete
    
    # Reinforcing steel
    # buckling length has been estimated using Dhakal & Maekawa (2002) method
    bLength1 = 2.0*50.0e-3  ; # buckling length (m) of phi 8 bars per (Dhakal & Maekawa, 2002)
    bLength2 = 15.0*8.0e-3 ; # buckling length (m) of phi 6 bars (assumed as equal to the web horizontal bar spacing)
    bLength3 = 50.0e-3;
    lsr1 = bLength1/dbar1 ; # Bar slenderness (edge phi 12 bars)
    lsr2 = bLength2/dbar2 ; # Bar slenderness (web phi 8 bars)
    lsr3 = bLength3/dbar2 ; # Bar slenderness (edge phi 8 bars)
    
    # Fatigue ductility coefficient and exponent have been estimated using Tripathi et al., (2018) method
    Cf1 = 0.25658 ; # Fatigue ductility coefficient (phi 8 bars)
    #alpha1 = 0.51509 ; # Fatigue ductility exponent (phi 8 bars)
    alpha1 = ((lsr1*(fy1/1e6/100)**0.5)/1200+0.441)
    Cd1 =  1.25*Cf1 ; # Cyclic strength reduction constant approximated as 1.25*fatigue ductility coefficient (phi 8 bars)
    Cf2 = 0.16982 ; # Fatigue ductility coefficient (phi 6 bars)
    #alpha2 = 0.59501 ; # Fatigue ductility exponent (phi 6 bars)
    alpha2 = ((lsr2*(fy2/1e6/100)**0.5)/1200+0.441)
    Cd2 =  1.25*Cf2; # Cyclic strength reduction constant approximated as 1.25*fatigue ductility coefficient (phi 6 bars)
    Cf3 = 0.27143 ; # Fatigue ductility coefficient (phi 6 bars)
    #alpha3 = 0.50734 ; # Fatigue ductility exponent (phi 6 bars)
    alpha3 = ((lsr3*(fy2/1e6/100)**0.5)/1200+0.441)
    Cd3 =  1.25*Cf3; # Cyclic strength reduction constant approximated as 1.25*fatigue ductility coefficient (phi 6 bars)
    
    # Recommended values are used for the following parameters (https://opensees.berkeley.edu/wiki/index.php/Reinforcing_Steel_Material)
    beta1 = 1.0 ; # Amplification factor for the buckled stress strain curve (phi8 bars)
    r1    = 0.4 ; # Buckling reduction factor (phi8 bars)
    gama1 = 0.5 ; # Buckling constant (phi8 bars)
    beta2 = beta1 ; # Amplification factor for the buckled stress strain curve (phi6 bars)
    r2    = r1 ;    # Buckling reduction factor (phi6 bars)
    gama2 = gama1 ; # Buckling constant (phi6 bars)
    beta3 = beta1 ; # Amplification factor for the buckled stress strain curve (phi6 bars)
    r3    = r1 ;    # Buckling reduction factor (phi6 bars)
    gama3 = gama1 ; # Buckling constant (phi6 bars)
    
    
    # uniaxialMaterial ReinforcingSteel $matTag $fy  $fu  $Es $Esh  $esh  $eult < -GABuck $lsr $beta $r $gama > < -DMBuck $lsr < $alpha >> < -CMFatigue $Cf $alpha $Cd > < -IsoHard <$a1 <$limit> > >
    op.uniaxialMaterial ('ReinforcingSteel', 3,fy1, fu1, E1, Esh1, esh1, eRup1 ,'-GABuck', lsr1, beta1, r1, gama1, '-CMFatigue', Cf1, alpha1, Cd1) ; # -GABuck [expr 101.6e-3/$dbar1] 1.0 0.4 0.5
    op.uniaxialMaterial ('ReinforcingSteel', 4,fy2, fu2, E2, Esh2, esh2, eRup2 ,'-GABuck', lsr2, beta2, r2, gama2, '-CMFatigue', Cf2, alpha2, Cd2) ; # -GABuck [expr 101.6e-3/$dbar1] 1.0 0.4 0.5
    op.uniaxialMaterial ('ReinforcingSteel', 5,fy2, fu2, E2, Esh2, esh2, eRup2 ,'-GABuck', lsr3, beta3, r3, gama3, '-CMFatigue', Cf3, alpha3, Cd3) ; # -GABuck [expr 101.6e-3/$dbar1] 1.0 0.4 0.5
    
    op.uniaxialMaterial("MinMax", 6, 3, "-min", -1.0e16, "-max", eRup1)
    op.uniaxialMaterial("MinMax", 7, 4, "-min", -1.0e16, "-max", eRup2)
    op.uniaxialMaterial("MinMax", 8, 5, "-min", -1.0e16, "-max", eRup2)
    
    
    # uniaxialMaterial Elastic   $matTag      $E             <$eta> <$Eneg>
    shearStiffness = 0.02*Ec*wallthickness*wallLength ; # Linear shear-spring stiffness used in the validated model
    
    op.uniaxialMaterial ('Elastic',      9   , shearStiffness) ; # Elastic material for the uncoupled base shear spring
    op.uniaxialMaterial ('Elastic'  ,    10   , 1.0e16) ; # to constrain spring in y & z directions
    
    # Define cross-section for the nonlinear wall
    # ------------------------------------------
    # Define cross-section for the nonlinear wall
    # ------------------------------------------
    
    # Bar area values derived from the introduced bar diameters
    As1 = math.pi * (dbar1**2) / 4.0     # Area of phi 12 bars
    As2 = math.pi * (dbar2**2) / 4.0     # Area of phi 8 bars
    
    # Auxiliary points for generating concrete fibers
    i1y = wallLength/2.0 - covery - hoopLength
    i1z = -1.0*(wallthickness/2.0 - coverz)
    
    j1y = wallLength/2.0 - covery
    j1z = -1.0*(wallthickness/2.0 - coverz)
    
    k1y = wallLength/2.0 - covery
    k1z = wallthickness/2.0 - coverz
    
    l1y = wallLength/2.0 - covery - hoopLength
    l1z = wallthickness/2.0 - coverz
    
    i2y = -j1y; i2z = i1z; j2y = -i1y; j2z = j1z; k2y = -l1y; k2z = k1z; l2y = -k1y; l2z = l1z;
    i3y = -wallLength/2.0; i3z = -wallthickness/2.0; j3y = -i3y; j3z = i3z; k3y = -i3y; k3z = -1.0*(wallthickness/2.0 - coverz); l3y = i3y; l3z = k3z; 
    i4y = i3y; i4z = -l3z; j4y = j3y; j4z = -k3z; k4y = k3y; k4z = -j3z; l4y = l3y; l4z = -i3z;
    
    webDepth = wallLength - 2.0*covery - 2.0*hoopLength
    
    # -------------------------------------------------------
    # Create the fiber section
    # -------------------------------------------------------
    
    op.section("Fiber", 1)
    
    # Concrete core fibers
    op.patch("quad", 1, 32, 1, i1y, i1z, j1y, j1z, k1y, k1z, l1y, l1z)
    op.patch("quad", 1, 32, 1, i2y, i2z, j2y, j2z, k2y, k2z, l2y, l2z)
    
    # Concrete cover fibers
    op.patch("quad", 2, int(math.ceil(wallLength/(hoopLength/32.0))), 1, i3y, i3z, j3y, j3z, k3y, k3z, l3y, l3z)
    op.patch("quad", 2, int(math.ceil(wallLength/(hoopLength/32.0))), 1, i4y, i4z, j4y, j4z, k4y, k4z, l4y, l4z)
    op.patch("quad", 2, int(math.ceil(covery/(hoopLength/32.0))), 1, j1y, j1z, k3y, k3z, j4y, j4z, k1y, k1z)
    op.patch("quad", 2, int(math.ceil(covery/(hoopLength/32.0))), 1, l3y, l3z, i2y, i2z, l2y, l2z, i4y, i4z)
    op.patch("quad", 2, int(math.ceil(webDepth/(hoopLength/32.0))), 1, j2y, j2z, i1y, i1z, l1y, l1z, k2y, k2z)
    
    
    # Reinforcing fibers - Boundary elements
    #op.layer('straight', matTag, numFiber, areaFiber, *start, *end)
    #op.layer("straight", 6, 3, As1,  0.770,  0.045,  0.970,  0.045)
    op.layer("straight", 6, int(no_bars_bl/2), As1,  (wallLength/2-do+covery+dhoop+dbar1/2),  (wallthickness/2-coverz-dhoop-dbar1/2),  (wallLength/2-covery-dhoop-dbar1/2),  (wallthickness/2-coverz-dhoop-dbar1/2))
    op.layer("straight", 6, int(no_bars_bl/2), As1, -(wallLength/2-covery-dhoop-dbar1/2),  (wallthickness/2-coverz-dhoop-dbar1/2), -(wallLength/2-do+covery+dhoop+dbar1/2),  (wallthickness/2-coverz-dhoop-dbar1/2))
    op.layer("straight", 6, int(no_bars_bl/2), As1,  (wallLength/2-do+covery+dhoop+dbar1/2),  -(wallthickness/2-coverz-dhoop-dbar1/2),  (wallLength/2-covery-dhoop-dbar1/2),  -(wallthickness/2-coverz-dhoop-dbar1/2))
    op.layer("straight", 6, int(no_bars_bl/2), As1, -(wallLength/2-covery-dhoop-dbar1/2),  -(wallthickness/2-coverz-dhoop-dbar1/2), -(wallLength/2-do+covery+dhoop+dbar1/2),  -(wallthickness/2-coverz-dhoop-dbar1/2))
    
    # Web bars
    if no_face_web ==2:
        op.layer("straight", 7, int(no_bars_web), As2,  -wall_web_length/2+webspacing/2,  (wallthickness/2-coverz-dhoop-dbar1/2),  wall_web_length/2-webspacing/2,  (wallthickness/2-coverz-dhoop-dbar1/2))
        op.layer("straight", 7, int(no_bars_web), As2, -wall_web_length/2+webspacing/2,  -(wallthickness/2-coverz-dhoop-dbar1/2), wall_web_length/2-webspacing/2,  -(wallthickness/2-coverz-dhoop-dbar1/2))
      
    else:
        op.layer("straight", 7, int(no_bars_web), As2,  -wall_web_length/2,  0.0,  wall_web_length/2,  0.0)

    # Define the wall element
    # Geometry of wall element
    #                tag
    op.geomTransf ('Linear', 1)
    
    #element zeroLength $eleTag $iNode $jNode -mat $matTag1 $matTag2 ... -dir $dir1 $dir2 ...<-doRayleigh $rFlag> <-orient $x1 $x2 $x3 $yp1 $yp2 $yp3>
    op.element('zeroLength',  1000,    1,      2,      '-mat', 9, 10, 10,    '-dir', 1, 2, 3) ; # For the base shear spring
    #print( "Zero length element (Tag = 100) created between nodes 1 & 2")
    
    # beamIntegration('Legendre', tag, secTag, N)
    op.beamIntegration(intType,  2,   1,      numIntgrPts)
    # element('dispBeamColumn',   eleTag, *eleNodes, transfTag, integrationTag, '-cMass', '-mass', mass=0.0)
    for ii in range(2,meetPoint):
        # element('dispBeamColumn',   eleTag, *eleNodes, transfTag, integrationTag, '-cMass', '-mass', mass=0.0)
        op.element('dispBeamColumn',   ii-1,     ii, ii+1,       1,        2) ; 
        #print("dispBeamColumn (Ele",ii-1, ") generated between nodes ",ii,' & ',ii+1)
    
    # The subsequently defined rigid element (an element with elasticity defined as 25 times the uncracked concrete Young's modulus)... 
    #   ...simulates the behaviour of RC wall-loading beam connection
    #                               tag, ndI, ndJ,   A,                  E,       Iz,                              transfTag
    op.element('elasticBeamColumn', ii,   (pushNode - 1),   pushNode,   wallthickness*wallLength, 25.0*Ec, wallthickness*(wallLength**3.0)/12.0,    1)
    #print("Rigid Element (Ele",ii,") generated between node", pushNode - 1," &  node ", pushNode)
    
    # Define gravity loads
    # Create a Plain load pattern with a Linear TimeSeries
    op.timeSeries('Linear', 1)
    op.pattern ('Plain', 1, 1)
    # Create nodal load at node2
    #     nd            FX      FY       MZ
    op.load(pushNode,   0.0,  -P, 0.0) ; # The applied axial load
    op.load(pushNode,   0.0, -PW, 0.0) ; # Weight of the wall & the loading beam
    
    # Create the system of equation, a sparse solver with partial pivoting
    op.system('BandGeneral')
    
    # Create the constraint handler, the transformation method
    op.constraints('Transformation')
    
    # Create the DOF numberer, the reverse Cuthill-McKee algorithm
    op.numberer('RCM')
    
    # Create the convergence test, the norm of the residual with a tolerance of
    # 1e-12 and a max number of iterations of 10
    op.test ('NormDispIncr', 1.0e-12 , 10, 3)
    
    # Create the solution algorithm, a Newton-Raphson algorithm
    op.algorithm ('Newton')
    
    # Create the integration scheme, the LoadControl scheme using steps of 0.1
    op.integrator ('LoadControl', 0.1)
    
    # Create the analysis object
    op.analysis ('Static')
    
    # Perform the analysis
    op.analyze(10)
    
    
    # -----------------------------------------------------------
    # Define  recorders
    topdisp_file = os.path.join(case_output_dir, "TopDisp.out")
    rbase_file   = os.path.join(case_output_dir, "RBase.out")
    
    op.recorder('Node', '-file', topdisp_file,
                '-node', pushNode, '-dof', 1, 'disp')
    
    op.recorder('Node', '-file', rbase_file,
                '-time', '-node', 1, '-dof', 1, 2, 'reaction')
    
    op.recorder('Element', '-ele', 1,
            '-file', os.path.join(case_output_dir, "StWest.out"),
            'section', 1, 'fiber',
            (wallLength/2-covery-dhoop-dbar1/2),
            (wallthickness/2-coverz-dhoop-dbar1/2),
            101, 'stressStrain')
    
    op.recorder('Element', '-ele', 1,
            '-file', os.path.join(case_output_dir, "StEast.out"),
            'section', 1, 'fiber',
            -(wallLength/2-covery-dhoop-dbar1/2),
            (wallthickness/2-coverz-dhoop-dbar1/2),
            101, 'stressStrain')

    op.recorder('Element', '-ele', 1,
            '-file', os.path.join(case_output_dir, "ConCoreWest.out"),
            'section', 1, 'fiber',
            (wallLength/2-covery-dhoop-dbar1/2),
            0.0,
            1, 'stressStrain')

    op.recorder('Element', '-ele', 1,
                '-file', os.path.join(case_output_dir, "ConCoreEast.out"),
                'section', 1, 'fiber',
                -(wallLength/2-covery-dhoop-dbar1/2),
                0.0,
                1, 'stressStrain')
    
    op.recorder('Element', '-ele', 1,
                '-file', os.path.join(case_output_dir, "ConCoverWest.out"),
                'section', 1, 'fiber',
                wallLength/2,
                0.0,
                2, 'stressStrain')
    
    op.recorder('Element', '-ele', 1,
                '-file', os.path.join(case_output_dir, "ConCoverEast.out"),
                'section', 1, 'fiber',
                -wallLength/2,
                0.0,
                2, 'stressStrain')
    #====================================================================
    # Set the gravity loads to be constant & reset the time in the domain
    op.loadConst ('-time', 0.0)
    
    #ve sonrası
    # disps: Target displacement values (in metres) for the cyclic pushover analysis (derived from the test hysteretic curves)
    print(" ")
    print("--------")
    patTag = 1 ;
    dispsLength = len(disps) ;
    
    #op.printModel('-node',pushNode)
    
    for ii in range(0,dispsLength):
      patTag = patTag + 1  
      op.pattern ('Plain', patTag, 1)  
      op.load(pushNode, 1.0, 0.0, 0.0)  
      maxU = disps[ii]
      dU = maxU/numIncrs
      op.integrator('DisplacementControl', pushNode, 1, dU, 10, dU, dU)
    #  op.printModel('-node',pushNode) 
      #print("Target delta value is", 0.001*math.ceil(1000.0*1000.0*maxU), "mm (drift ratio = ", 0.001*math.ceil(100.0*1000.0*maxU/driftHeight), ") for the present step.")
    
      currentDisp = 0.0
      ok = 0.0
      op.test('NormDispIncr', 1.0e-6 , 1000)
      op.algorithm ('NewtonLineSearch')
      if maxU >= 0.0:
          while ok == 0 and currentDisp < maxU:
              ok = op.analyze(1)
              # if the analysis fails try initial tangent iteration
              if ok != 0:
                  print("Newton Line Search failed, examining Modified Newton")
                  op.test('NormDispIncr', 1.0e-6 , 1000)
                  op.algorithm ('ModifiedNewton')
                  ok = op.analyze(1)
                  if ok == 0:
                      print("Modified Newton worked, back to Newton Line Search")
                      op.test('NormDispIncr', 1.0e-6 , 1000)
                      op.algorithm ('NewtonLineSearch')
              if ok != 0:
                 print("Modified Newton failed also, examining Krylov Newton")
                 op.test('NormDispIncr', 1.0e-6 , 1000)
                 op.algorithm ('KrylovNewton')
                 ok = op.analyze(1)
                 if ok == 0:
                    print("Krylov Newton worked, back to Newton Line Search")
                    op.test('NormDispIncr', 1.0e-6 , 1000)
                    op.algorithm ('NewtonLineSearch')
              if ok != 0:
                 print("Krylov Newton failed also, examining Broyden")
                 op.test('NormDispIncr', 1.0e-6 , 1000)
                 op.algorithm ('Broyden')
                 ok = op.analyze(1)
                 if ok == 0:
                    print("Broyden worked, back to Newton Line Search")
                    op.test('NormDispIncr', 1.0e-6 , 1000)
                    op.algorithm ('NewtonLineSearch')
              if ok != 0:
                 print("Broyden failed also, examining BFGS")
                 op.test('NormDispIncr', 1.0e-6 , 1000)
                 op.algorithm ('BFGS')
                 ok = op.analyze(1)
                 if ok == 0:
                    print("BFGS worked, back to Newton Line Search")
                    op.test('NormDispIncr', 1.0e-6 , 1000)
                    op.algorithm ('NewtonLineSearch')
              if ok != 0:
                  print("**********************************************************")
                  print("**********************************************************")
                  print("**********************************************************")
                  print("All algorithms failed, terminating the code")
                  break
              currentDisp = op.nodeDisp(pushNode, 1)
      if maxU < 0.0:
          while ok == 0 and currentDisp > maxU:
              ok = op.analyze(1)
              # if the analysis fails try initial tangent iteration
              if ok != 0:
                  print("Newton Line Search failed, examining Modified Newton")
                  op.test('NormDispIncr', 1.0e-6 , 1000)
                  op.algorithm ('ModifiedNewton')
                  ok = op.analyze(1)
                  if ok == 0:
                      print("Modified Newton worked, back to Newton Line Search")
                      op.test('NormDispIncr', 1.0e-6 , 1000)
                      op.algorithm ('NewtonLineSearch')
              if ok != 0:
                 print("Modified Newton failed also, examining Krylov Newton")
                 op.test('NormDispIncr', 1.0e-6 , 1000)
                 op.algorithm ('KrylovNewton')
                 ok = op.analyze(1)
                 if ok == 0:
                    print("Krylov Newton worked, back to Newton Line Search")
                    op.test('NormDispIncr', 1.0e-6 , 1000)
                    op.algorithm ('NewtonLineSearch')
              if ok != 0:
                 print("Krylov Newton failed also, examining Broyden")
                 op.test('NormDispIncr', 1.0e-6 , 1000)
                 op.algorithm ('Broyden')
                 ok = op.analyze(1)
                 if ok == 0:
                    print("Broyden worked, back to Newton Line Search")
                    op.test('NormDispIncr', 1.0e-6 , 1000)
                    op.algorithm ('NewtonLineSearch')
              if ok != 0:
                 print("Broyden failed also, examining BFGS")
                 op.test('NormDispIncr', 1.0e-6 , 1000)
                 op.algorithm ('BFGS')
                 ok = op.analyze(1)
                 if ok == 0:
                    print("BFGS worked, back to Newton Line Search")
                    op.test('NormDispIncr', 1.0e-6 , 1000)
                    op.algorithm ('NewtonLineSearch')
              if ok != 0:
                  print("**********************************************************")
                  print("**********************************************************")
                  print("**********************************************************")
                  print("All algorithms failed, terminating the code")
                  break
              currentDisp = op.nodeDisp(pushNode, 1)  ;        
              
          
      #wait = input("Press Enter to continue.")
      #print("**********************************************************")
    
    #op.printModel('-node',pushNode)
          
    
    print( "ANALYSIS OVER")
    
    # -------------------------------------------------------------------------
    # FEMA P-2208 CAPACITY-RATIO CLASSIFICATION
    # -------------------------------------------------------------------------
    My = compute_yield_moment_wall(
        wallLength=wallLength,
        wallThickness=wallthickness,
        no_bars_bl=no_bars_bl,
        dbar1=dbar1,
        fy1=fy1,
        Es=E1,
        Ec=Ec,
        P=P,
        PW=PW,
        covery=covery,
        coverz=coverz,
        dhoop=dhoop
    )
    
    heff = M_Vlw * wallLength
    V_MCyE = My / heff
    
    V_CE = compute_shear_capacity_ACI(
        fc=fc,
        fy2=fy2,
        rho_t=rho_t,
        A_gross=A_gross,
        driftHeight=driftHeight,
        wallLength=wallLength
    )
    
    ratio, mode = check_shear_flexure_dominance(V_CE, V_MCyE)
    
    print(f"My = {My/1e3:.2f} kN·m")
    print(f"V_CE = {V_CE:.2f} kN")
    print(f"V_MCyE = {V_MCyE/1e3:.2f} kN")
    print(f"FEMA classification = {mode} (ratio = {ratio:.3f})")

    return {
        "Case_ID": case_id,
        "fc_MPa": fc_MPa,
        "ALR": ALR,
        "rho_bl": rho_bl,
        "rho_sh": rho_sh,
        "rho_t": rho_t,
        "dbar_mm": float(dbar),
        "webspacing_mm": float(webspacing) * 1000,
        "rho_l_computed": rho_l_computed,
        "P_N": P,
        "epc0M": epc0M,
    
        # FEMA capacity-classification outputs
        "My_kNm": My / 1e3,
        "V_CE_kN": V_CE,
        "V_MCyE_kN": V_MCyE / 1e3,
        "V_CE_over_V_MCyE": ratio,
        "Failure_mode": mode
    }
