"""mv_tracker.py: multi-view 3-D tracker with confirmation (T4b), for dataset v2 pilot 2.

Developed on non-registered shows only (seeds 98, 99), gated on oracle detections before use.
Built on run_pilot2.py's geometry (proj_jac, ray, ray_pairs).

Per frame:
 1. Predict (constant velocity, sigma_a 2 m/s^2).
 2. For each camera K1, K2, K3: associate CONFIRMED tracks first (Hungarian on pixel distance, gate 6 px), then
    TENTATIVE tracks to the remaining detections; batched EKF update (pixel sigma 1 px).
 3. Support = number of cameras that associated the track this frame.
    Tentative: support == 3 increments a streak; anything less deletes the track. Streak >= CONFIRM_N -> confirmed.
    Confirmed: deleted after MAX_AGE (3) consecutive frames with support 0.
 3b. Consistency: a track associated in all three cameras whose three detections do not triangulate to one point
    within REPROJ_MAX px in every camera is inconsistent; tentative tracks need consistency to extend their streak;
    confirmed tracks inconsistent for BAD_N consecutive frames are deleted.
 4. Duplicates: confirmed tracks closer than DUP_M -> the younger is deleted.
 5. Births from detections unused in all three cameras: K1-K2 ray pairs within 0.5 m, nearest unused K3 detection
    within 6 px of the midpoint projection, least-squares triangulation from the three rays, reprojection error
    <= 2 px in every camera, greedy by total error, each detection used once; candidates within SUPPRESS_M of any
    existing track are discarded. New tracks start tentative.
 Output: confirmed tracks with support >= 1 this frame.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

CONFIRM_N = 5
DUP_M = 0.5
SUPPRESS_M = 1.5
REPROJ_MAX = 2.0
MAX_AGE = 3
BAD_N = 3          # consecutive inconsistent frames before a confirmed track is deleted


class MultiViewConfirmed:
    def __init__(self, R2, cams):
        self.R2, self.cams = R2, cams
        self.X = np.zeros((0, 6)); self.P = np.zeros((0, 6, 6)); self.ids = np.zeros(0, int)
        self.miss = np.zeros(0, int); self.streak = np.zeros(0, int); self.conf = np.zeros(0, bool); self.born = np.zeros(0, int)
        self.bad = np.zeros(0, int)
        self.next = 0; self.frame = 0
        DT = R2.DT
        Fm = np.eye(6); Fm[:3, 3:] = np.eye(3) * DT; self.F = Fm
        G = np.array([[DT ** 2 / 2], [DT]]); q1 = (G @ G.T) * R2.SIG_A ** 2
        Q = np.zeros((6, 6))
        for k in range(3): Q[np.ix_([k, k + 3], [k, k + 3])] = q1
        self.Q = Q

    def _associate(self, k, sel, dets, used):
        R2 = self.R2; cam, basis = self.cams[k]
        if not len(sel) or not len(dets): return np.zeros(0, int)
        px, zc, J = R2.proj_jac(self.X[sel, :3], cam, basis)
        free = np.flatnonzero(~used)
        if not len(free): return np.zeros(0, int)
        front = np.flatnonzero(zc > 0)
        if not len(front): return np.zeros(0, int)
        near = cKDTree(dets[free]).query_ball_point(px[front], r=R2.GATE_PX)
        rows, cols, vals = [], [], []
        for a, js in enumerate(near):
            for j in js:
                rows.append(a); cols.append(j); vals.append(np.hypot(*(px[front[a]] - dets[free[j]])))
        if not rows: return np.zeros(0, int)
        C = np.full((len(front), len(free)), 1e6); C[rows, cols] = vals
        ra, ca = linear_sum_assignment(C)
        keep = C[ra, ca] <= R2.GATE_PX
        loc = front[ra[keep]]; dj = free[ca[keep]]
        ti = sel[loc]
        Hm = np.zeros((len(ti), 2, 6)); Hm[:, :, :3] = J[loc]
        Pt = self.P[ti]
        S = Hm @ Pt @ Hm.transpose(0, 2, 1) + np.eye(2)[None] * R2.SIG_PX ** 2
        K = Pt @ Hm.transpose(0, 2, 1) @ np.linalg.inv(S)
        y = dets[dj] - px[loc]
        self.X[ti] = self.X[ti] + (K @ y[..., None])[..., 0]
        self.P[ti] = (np.eye(6)[None] - K @ Hm) @ Pt
        used[dj] = True
        self._det[k][ti] = dj
        return ti

    def _births(self, dets, used):
        R2 = self.R2; (c1, b1), (c2, b2), (c3, b3) = self.cams
        u = [np.flatnonzero(~x) for x in used]
        if not all(len(x) for x in u): return []
        p = [dets[k][u[k]] for k in range(3)]
        d1 = R2.ray(c1, b1, p[0]); d2 = R2.ray(c2, b2, p[1]); d3 = R2.ray(c3, b3, p[2])
        dist, mid = R2.ray_pairs(c1, d1, c2, d2)
        i1, i2 = np.nonzero(dist <= R2.RAY_GATE)
        if not len(i1): return []
        M = mid[i1, i2]
        px3, z3, _ = R2.proj_jac(M, c3, b3)
        dd, i3 = cKDTree(p[2]).query(px3, k=1)
        ok = (z3 > 0) & (dd <= R2.GATE_PX)
        i1, i2, i3 = i1[ok], i2[ok], i3[ok]
        if not len(i1): return []
        D = np.stack([d1[i1], d2[i2], d3[i3]], 1)
        C = np.stack([np.broadcast_to(c, (len(i1), 3)) for c in (c1, c2, c3)], 1)
        Mp = np.eye(3)[None, None] - D[..., :, None] * D[..., None, :]
        A = Mp.sum(1); b = (Mp @ C[..., None])[..., 0].sum(1)
        X = np.linalg.solve(A, b[..., None])[..., 0]
        err = np.zeros(len(X)); good = np.ones(len(X), bool)
        for k, idx in ((0, i1), (1, i2), (2, i3)):
            pxk, zk, _ = R2.proj_jac(X, *self.cams[k])
            e = np.linalg.norm(pxk - p[k][idx], axis=1)
            good &= (zk > 0) & (e <= REPROJ_MAX); err += e
        if len(self.X):
            dn, _ = cKDTree(self.X[:, :3]).query(X, k=1)
            good &= dn > SUPPRESS_M
        order = np.flatnonzero(good)[np.argsort(err[good])]
        f = [np.ones(len(x), bool) for x in u]; out = []
        for m in order:
            a, bq, c = i1[m], i2[m], i3[m]
            if f[0][a] and f[1][bq] and f[2][c]:
                f[0][a] = f[1][bq] = f[2][c] = False; out.append(X[m])
        if len(out) > 1:                                     # births must also be SUPPRESS_M apart from each other
            O = np.array(out); keep = np.ones(len(O), bool)
            for i, js in enumerate(cKDTree(O).query_ball_point(O, r=SUPPRESS_M)):
                if keep[i]:
                    for j in js:
                        if j > i: keep[j] = False
            out = list(O[keep])
        return out

    def step(self, dets_per_cam):
        if len(self.X):
            self.X = self.X @ self.F.T
            self.P = self.F[None] @ self.P @ self.F.T[None] + self.Q[None]
        n = len(self.X)
        support = np.zeros(n, int)
        self._det = [np.full(n, -1) for _ in range(3)]
        used = [np.zeros(len(d), bool) for d in dets_per_cam]
        conf_idx = np.flatnonzero(self.conf); tent_idx = np.flatnonzero(~self.conf)
        for k in range(3):
            for sel in (conf_idx, tent_idx):
                ti = self._associate(k, sel, dets_per_cam[k], used[k])
                support[ti] += 1
        # consistency: the three associated detections must triangulate to one point within REPROJ_MAX in every camera
        consistent = np.zeros(n, bool)
        idx3 = np.flatnonzero(support == 3)
        if len(idx3):
            R2 = self.R2
            D = np.stack([R2.ray(*self.cams[k], dets_per_cam[k][self._det[k][idx3]]) for k in range(3)], 1)
            C = np.stack([np.broadcast_to(self.cams[k][0], (len(idx3), 3)) for k in range(3)], 1)
            Mp = np.eye(3)[None, None] - D[..., :, None] * D[..., None, :]
            Xl = np.linalg.solve(Mp.sum(1), (Mp @ C[..., None])[..., 0].sum(1)[..., None])[..., 0]
            ok = np.ones(len(idx3), bool)
            for k in range(3):
                pk, zk, _ = R2.proj_jac(Xl, *self.cams[k])
                ok &= (zk > 0) & (np.linalg.norm(pk - dets_per_cam[k][self._det[k][idx3]], axis=1) <= REPROJ_MAX)
            consistent[idx3[ok]] = True
        self.bad[(support == 3) & ~consistent] += 1
        self.bad[consistent | (support < 3)] = 0
        # tentative bookkeeping
        tent = ~self.conf
        full = (support == 3) & consistent
        self.streak[tent & full] += 1
        drop = tent & ~full
        self.conf[tent & (self.streak >= CONFIRM_N)] = True
        # confirmed bookkeeping
        self.miss[support > 0] = 0; self.miss[support == 0] += 1
        alive = ~drop & ~(self.conf & (self.miss > MAX_AGE)) & ~(self.bad >= BAD_N)
        # duplicates among confirmed
        ci = np.flatnonzero(self.conf & alive)
        if len(ci) > 1:
            for i, js in enumerate(cKDTree(self.X[ci, :3]).query_ball_point(self.X[ci, :3], r=DUP_M)):
                for j in js:
                    if j > i and alive[ci[i]] and alive[ci[j]]:
                        older = ci[i] if self.born[ci[i]] <= self.born[ci[j]] else ci[j]
                        alive[ci[j] if older == ci[i] else ci[i]] = False
        out_mask = self.conf & alive & (support > 0)
        out = (list(self.ids[out_mask]), self.X[out_mask, :3].copy())
        keep = alive
        self.X, self.P, self.ids = self.X[keep], self.P[keep], self.ids[keep]
        self.miss, self.streak, self.conf, self.born = self.miss[keep], self.streak[keep], self.conf[keep], self.born[keep]
        self.bad = self.bad[keep]
        used = [u for u in used]
        B = self._births(dets_per_cam, used)
        if B:
            B = np.array(B); nb = len(B)
            P0 = np.zeros((nb, 6, 6)); P0[:, :3, :3] = np.eye(3) * 0.25; P0[:, 3:, 3:] = np.eye(3) * 16.0
            self.X = np.vstack([self.X, np.hstack([B, np.zeros((nb, 3))])])
            self.P = np.concatenate([self.P, P0]) if len(self.P) else P0
            self.ids = np.concatenate([self.ids, np.arange(self.next, self.next + nb)]); self.next += nb
            self.miss = np.concatenate([self.miss, np.zeros(nb, int)]); self.streak = np.concatenate([self.streak, np.ones(nb, int)])
            self.conf = np.concatenate([self.conf, np.zeros(nb, bool)]); self.born = np.concatenate([self.born, np.full(nb, self.frame)])
            self.bad = np.concatenate([self.bad, np.zeros(nb, int)])
        self.frame += 1
        return out
