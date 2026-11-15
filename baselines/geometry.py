"""geometry.py: camera model and constants used by the SwarmLights baseline trackers (pinhole cameras, no distortion).
A camera is (position (3,), basis (right, up, forward)) with the focal length and image size of calibration.json."""
import math
import numpy as np

W, H, HFOV = 1920, 1080, 60.0
F_PX = (W / 2) / math.tan(math.radians(HFOV / 2))   # 1662.77 px, as in calibration.json
DT = 0.1                                             # s per frame (10 fps)
GATE_PX = 6.0                                        # association gate in pixels
SIG_PX = 1.0                                         # detection noise (px) for the Kalman filter
RAY_GATE = 0.5                                       # max distance (m) between two cameras' rays for a 3-D birth
SIG_A = 2.0                                          # process noise: acceleration (m/s^2)
MATCH_3D = 1.0                                       # scoring match distance (m)


def proj_jac(X, cam, basis):
    """X (n,3) -> pixels (n,2), depth (n,), Jacobian (n,2,3)."""
    r, u, f = basis
    d = X - cam
    xc, yc, zc = d @ r, d @ u, d @ f
    zs = np.where(np.abs(zc) < 1e-6, 1e-6, zc)
    px = np.stack([W / 2 + F_PX * xc / zs, H / 2 - F_PX * yc / zs], 1)
    J = np.empty((len(X), 2, 3))
    J[:, 0, :] = F_PX * (r[None, :] / zs[:, None] - (xc / zs ** 2)[:, None] * f[None, :])
    J[:, 1, :] = -F_PX * (u[None, :] / zs[:, None] - (yc / zs ** 2)[:, None] * f[None, :])
    return px, zc, J


def ray(cam, basis, p):
    """Unit viewing rays through pixels p (n,2)."""
    r, u, f = basis
    d = f[None, :] + ((p[:, 0] - W / 2) / F_PX)[:, None] * r[None, :] - ((p[:, 1] - H / 2) / F_PX)[:, None] * u[None, :]
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def ray_pairs(c1, d1, c2, d2):
    """Closest approach between rays c1 + s d1 (n) and c2 + t d2 (m): distance (n,m), midpoint (n,m,3)."""
    w0 = c1 - c2
    a = 1.0; c = 1.0
    b = d1 @ d2.T
    dd = d1 @ w0
    e = d2 @ w0
    den = a * c - b ** 2
    den = np.where(den < 1e-9, 1e-9, den)
    s = (b * e[None, :] - c * dd[:, None]) / den
    t = (a * e[None, :] - b * dd[:, None]) / den
    p1 = c1[None, None, :] + s[..., None] * d1[:, None, :]
    p2 = c2[None, None, :] + t[..., None] * d2[None, :, :]
    ok = (s > 0) & (t > 0)
    dist = np.where(ok, np.linalg.norm(p1 - p2, axis=2), np.inf)
    return dist, (p1 + p2) / 2
