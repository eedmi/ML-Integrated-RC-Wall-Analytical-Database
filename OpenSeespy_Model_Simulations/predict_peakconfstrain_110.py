import numpy as np
import scipy.io as sio
import pandas as pd


# ============================================================
#  SCALING
# ============================================================
def MyscaleData(trn, XtrainMin, XtrainMax):
    trn = np.asarray(trn, dtype=float)
    denom = XtrainMax - XtrainMin
    denom = np.where(denom == 0, 1e-12, denom)
    trnOut = 2*((trn - XtrainMin)/denom) - 1
    trnOut = np.where(np.isnan(trnOut), -1, trnOut)
    return trnOut


# ============================================================
#  BACK TRANSFORM
# ============================================================
def backTransform(Y, transformY, powerY):
    Y = np.asarray(Y, dtype=float)
    if transformY == "squareRoot":
        return Y**2
    return Y


# ============================================================
#  HELPERS
# ============================================================
def safe_scalar(x):
    return float(np.array(x).flatten()[0])


# ============================================================
#  KRR PREDICT
# ============================================================
def testKRR(model, Xtest):
    sigma  = safe_scalar(model[0])
    Xtrain = np.array(model[2]).astype(float)
    alpha  = np.array(model[3]).astype(float)
    gamma = 1/(2*sigma**2)
    d = ((Xtest[:,None,:] - Xtrain[None,:,:])**2).sum(axis=2)
    K = np.exp(-gamma*d)
    return (K @ alpha).ravel()


# ============================================================
#  SVR PREDICT
# ============================================================
def testSVR(model, Xtest):
    params = model[0]
    gamma  = safe_scalar(params[3])
    rho    = safe_scalar(model[3])
    sv_coef = np.array(model[9]).astype(float)
    SVs     = np.array(model[10]).astype(float)
    d = ((Xtest[:,None,:] - SVs[None,:,:])**2).sum(axis=2)
    K = np.exp(-gamma*d)
    return (K @ sv_coef - rho).ravel()


# ============================================================
#  GPR PREDICT (ARD kernel)
# ============================================================
def testGPR(model_struct, Xtest):
    loghyper = np.array(model_struct[0]).astype(float).flatten()
    Xtrain   = np.array(model_struct[4]).astype(float)
    alpha    = np.array(model_struct[7]).astype(float).flatten()


    D = Xtrain.shape[1]
    ell = np.exp(loghyper[:D])
    sf2 = np.exp(2*loghyper[D])


    Xtest_s  = Xtest  / ell
    Xtrain_s = Xtrain / ell


    d = ((Xtest_s[:,None,:] - Xtrain_s[None,:,:])**2).sum(axis=2)
    K = sf2 * np.exp(-0.5*d)
    return (K @ alpha).ravel()
    


def predict_peakconfstrain_110(features_vector, root, verbose=True):

    if root is None:
        raise ValueError("ERROR: You must provide 'root' argument. (Example: root='/path/to/MLmodel/')")

    # ============================================================
    # FIXED TO 110-Walls ONLY
    # ============================================================
    folder = "110-Walls"
    weight_KRR = 1.0
    weight_SVR = 1.0
    weight_GPR = 1.0
    use_GPR = True

    refDir = f"{root}{folder}/"

    # ============================================================
    # LOAD SUPPORT DATA
    # ============================================================
    meanY = np.loadtxt(refDir + "supportFiles/meanY.txt")
    Xmin  = np.loadtxt(refDir + "supportFiles/XtrainMin.txt")
    Xmax  = np.loadtxt(refDir + "supportFiles/XtrainMax.txt")

    # reshape to (1, N)
    x = np.asarray(features_vector, dtype=float).reshape(1, -1)

    # scale
    X_scaled = x.copy()
    for i in range(X_scaled.shape[1]):
        X_scaled[:, i] = MyscaleData(X_scaled[:, i], Xmin[i], Xmax[i])

    # ============================================================
    # LOAD MODELS (110 only)
    # ============================================================
    krr_model = sio.loadmat(refDir + "KRR/chosen.mat")["zzz"].item()
    svr_model = sio.loadmat(refDir + "SVR/chosen.mat")["zzz"].item()
    gpr_model = sio.loadmat(refDir + "GPR/chosen.mat")["zzz"].item()

    # ============================================================
    # PREDICT
    # ============================================================
    Ykrr = backTransform(testKRR(krr_model, X_scaled) + meanY, "squareRoot", 1)[0]
    Ysvr = backTransform(testSVR(svr_model, X_scaled) + meanY, "squareRoot", 1)[0]
    Ygpr = backTransform(testGPR(gpr_model, X_scaled) + meanY, "squareRoot", 1)[0]

    ensemble = (weight_KRR*Ykrr + weight_SVR*Ysvr + weight_GPR*Ygpr) / \
               (weight_KRR + weight_SVR + weight_GPR)

    if verbose:
        print("\nPrediction results (110-Walls):")
        print("------------------------------")
        print("Predicted peak confined strain:", ensemble)
       # print("KRR:", Ykrr)
       # print("SVR:", Ysvr)
       # print("GPR:", Ygpr)

    return ensemble
