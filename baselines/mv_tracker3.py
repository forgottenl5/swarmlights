"""mv_tracker3.py: T4c for pilot 3 (docs/DATASET_V2_PILOT3_PREREG.md). Built on mv_tracker.T4b.

Differences from T4b:
 - Support: a track is supported when >= 2 cameras associate it AND its associated detections triangulate to one
   point within REPROJ_MAX px in each of those cameras ("consistent"). Tentative tracks extend their streak on
   consistent support; any frame without it deletes a tentative track. Confirmed tracks: inconsistent for BAD_N
   frames -> deleted; no association in any camera for MAX_AGE frames -> deleted.
 - Third-camera presence: when a track's projection is inside a camera's frame but that camera did not associate
   it, there must be SOME detection (associated to another track or not) within GATE_PX of the projection, else the
   frame does not count as consistent (a drone with its LED on must appear as at least part of a dot). Applied to
   tentative tracks only (confirmed tracks may pass behind merged dots).
 - Births from any camera pair (K1K2, K1K3, K2K3) of free detections: rays within the 0.5 m gate, least-squares
   point, reprojection <= REPROJ_MAX in both; if the third camera has a free detection within REPROJ_MAX of the
   projection it joins (point re-triangulated from three rays); otherwise the third camera must show any detection
   within GATE_PX when the point is in its frame (presence rule), or the point must be outside its frame.
   Greedy: three-camera candidates first, then by total reprojection error; each detection used once per camera.
"""
import numpy as np
from scipy.spatial import cKDTree
import mv_tracker as MT

VERSION = 'T4c-v1'


def _ls(rays, cents):
    """rays (n,m,3), cents (n,m,3) -> least-squares points (n,3)."""
    Mp = np.eye(3)[None, None] - rays[..., :, None] * rays[..., None, :]
    A = Mp.sum(1); b = (Mp @ cents[..., None])[..., 0].sum(1)
    return np.linalg.solve(A, b[..., None])[..., 0]


class MultiView2of3(MT.MultiViewConfirmed):

    def _in_frame(self, k, X):
        R2 = self.R2
        px, z, _ = R2.proj_jac(X, *self.cams[k])
        return px, (z > 0) & (px[:, 0] >= 0) & (px[:, 0] < R2.W) & (px[:, 1] >= 0) & (px[:, 1] < R2.H)

    def _presence(self, k, X, dets):
        """True where X is outside camera k's frame, or some detection lies within GATE_PX of its projection."""
        px, inside = self._in_frame(k, X)
        if not len(dets):
            return ~inside
        d, _ = cKDTree(dets).query(px, k=1)
        return ~inside | (d <= self.R2.GATE_PX)

    def _births(self, dets, used):
        R2 = self.R2
        u = [np.flatnonzero(~x) for x in used]
        p = [dets[k][u[k]] for k in range(3)]
        rays = [R2.ray(*self.cams[k], p[k]) if len(p[k]) else np.zeros((0, 3)) for k in range(3)]
        cand = []                                                     # (n_cams, err, X, (k: local idx))
        for a, b in ((0, 1), (0, 2), (1, 2)):
            c = 3 - a - b
            if not len(p[a]) or not len(p[b]):
                continue
            dist, mid = R2.ray_pairs(self.cams[a][0], rays[a], self.cams[b][0], rays[b])
            ia, ib = np.nonzero(dist <= R2.RAY_GATE)
            if not len(ia):
                continue
            X = _ls(np.stack([rays[a][ia], rays[b][ib]], 1),
                    np.stack([np.broadcast_to(self.cams[a][0], (len(ia), 3)), np.broadcast_to(self.cams[b][0], (len(ia), 3))], 1))
            ok = np.ones(len(X), bool); err = np.zeros(len(X))
            for k, idx in ((a, ia), (b, ib)):
                pk, zk, _ = R2.proj_jac(X, *self.cams[k])
                e = np.linalg.norm(pk - p[k][idx], axis=1); ok &= (zk > 0) & (e <= MT.REPROJ_MAX); err += e
            ia, ib, X, err = ia[ok], ib[ok], X[ok], err[ok]
            if not len(X):
                continue
            ic = np.full(len(X), -1)
            if len(p[c]):
                pc, inside = self._in_frame(c, X)
                dc, jc = cKDTree(p[c]).query(pc, k=1)
                three = inside & (dc <= MT.REPROJ_MAX)
                ic[three] = jc[three]
            pres = self._presence(c, X, dets[c])
            keep = (ic >= 0) | pres
            for m in np.flatnonzero(keep):
                idx = {a: ia[m], b: ib[m]}
                Xm = X[m]; e = err[m]; n = 2
                if ic[m] >= 0:
                    ks = sorted([a, b, c]); idx[c] = ic[m]
                    X3 = _ls(np.stack([rays[k][idx[k]] for k in ks])[None], np.stack([self.cams[k][0] for k in ks])[None])[0]
                    e3 = 0.0; good = True
                    for k in ks:
                        pk, zk, _ = R2.proj_jac(X3[None], *self.cams[k])
                        ek = float(np.linalg.norm(pk[0] - p[k][idx[k]])); good &= (zk[0] > 0) and ek <= MT.REPROJ_MAX; e3 += ek
                    if good:
                        Xm, e, n = X3, e3, 3
                    else:
                        del idx[c]
                cand.append((n, e, Xm, idx))
        if not cand:
            return []
        cand.sort(key=lambda t: (-t[0], t[1]))
        X = np.array([t[2] for t in cand])
        okd = np.ones(len(X), bool)
        if len(self.X):
            dn, _ = cKDTree(self.X[:, :3]).query(X, k=1); okd = dn > MT.SUPPRESS_M
        free = [np.ones(len(x), bool) for x in u]; out = []
        for (n, e, Xm, idx), ok in zip(cand, okd):
            if not ok or not all(free[k][j] for k, j in idx.items()):
                continue
            if out and np.min(np.linalg.norm(np.array(out) - Xm, axis=1)) <= MT.SUPPRESS_M:
                continue
            for k, j in idx.items():
                free[k][j] = False
            out.append(Xm)
        return out

    def step(self, dets_per_cam):
        R2 = self.R2
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
        consistent = np.zeros(n, bool)
        idx2 = np.flatnonzero(support >= 2)
        for i in idx2:
            ks = [k for k in range(3) if self._det[k][i] >= 0]
            dd = [dets_per_cam[k][self._det[k][i]] for k in ks]
            rays = np.stack([R2.ray(*self.cams[k], dd[j][None])[0] for j, k in enumerate(ks)])
            Xl = _ls(rays[None], np.stack([self.cams[k][0] for k in ks])[None])[0]
            ok = True
            for j, k in enumerate(ks):
                pk, zk, _ = R2.proj_jac(Xl[None], *self.cams[k])
                ok &= (zk[0] > 0) and float(np.linalg.norm(pk[0] - dd[j])) <= MT.REPROJ_MAX
            consistent[i] = ok
        tent = ~self.conf
        pres = np.ones(n, bool)
        if n:
            for k in range(3):
                miss_k = tent & (self._det[k] < 0)
                if miss_k.any():
                    pres[miss_k] &= self._presence(k, self.X[miss_k, :3], dets_per_cam[k])
        good = consistent & pres
        self.bad[(support >= 2) & ~consistent] += 1
        self.bad[consistent | (support < 2)] = 0
        self.streak[tent & good] += 1
        drop = tent & ~good
        self.conf[tent & good & (self.streak >= MT.CONFIRM_N)] = True
        self.miss[support > 0] = 0; self.miss[support == 0] += 1
        alive = ~drop & ~(self.conf & (self.miss > MT.MAX_AGE)) & ~(self.bad >= MT.BAD_N)
        ci = np.flatnonzero(self.conf & alive)
        if len(ci) > 1:
            for i, js in enumerate(cKDTree(self.X[ci, :3]).query_ball_point(self.X[ci, :3], r=MT.DUP_M)):
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
