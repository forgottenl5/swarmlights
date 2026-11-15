"""mv_tracker5.py: T5, merge-tolerant three-camera tracker (docs/BASELINE_T5_PREREG.md).
Built on T4c-v1 (mv_tracker3.MultiView2of3). Changes only:
 1. Shared detections: after one-to-one association in a camera, CONFIRMED tracks still unassociated in that camera may
    attach to an already-used detection within SHARE_GATE_PX; the update uses pixel sigma SHARE_SIGMA_PX. Shared
    measurements do not count towards the consistency check.
 2. Single-camera survival: a confirmed track is kept while any camera (shared or not) supports it; deletion after
    MAX_AGE frames without support (as T4c). Consistency and tentative rules use non-shared support only.
 4. (Amendment 1, BASELINE_T5_AMENDMENT_1.md) Third-view verification of births: a birth candidate that projects inside
    all three cameras' frames needs a free detection within REPROJ_MAX in the third camera (three rays agree). Two-camera
    births are allowed only where the point is outside the third camera's frame. v2: no merge exception.
"""
import numpy as np
from scipy.spatial import cKDTree
import mv_tracker as MT
import mv_tracker3 as M3

VERSION = 'T5-v2'
SHARE_GATE_PX = 4.0
SHARE_SIGMA_PX = 3.0


class MultiViewMerge(M3.MultiView2of3):

    def _births(self, dets, used):
        """T4c births, but a candidate seen by only two cameras is dropped when it is inside the third camera's frame."""
        R2 = self.R2
        u = [np.flatnonzero(~x) for x in used]
        p = [dets[k][u[k]] for k in range(3)]
        rays = [R2.ray(*self.cams[k], p[k]) if len(p[k]) else np.zeros((0, 3)) for k in range(3)]
        cand = []
        for a, b in ((0, 1), (0, 2), (1, 2)):
            c = 3 - a - b
            if not len(p[a]) or not len(p[b]):
                continue
            dist, mid = R2.ray_pairs(self.cams[a][0], rays[a], self.cams[b][0], rays[b])
            ia, ib = np.nonzero(dist <= R2.RAY_GATE)
            if not len(ia):
                continue
            X = M3._ls(np.stack([rays[a][ia], rays[b][ib]], 1),
                       np.stack([np.broadcast_to(self.cams[a][0], (len(ia), 3)), np.broadcast_to(self.cams[b][0], (len(ia), 3))], 1))
            ok = np.ones(len(X), bool); err = np.zeros(len(X))
            for k, idx in ((a, ia), (b, ib)):
                pk, zk, _ = R2.proj_jac(X, *self.cams[k])
                e = np.linalg.norm(pk - p[k][idx], axis=1); ok &= (zk > 0) & (e <= MT.REPROJ_MAX); err += e
            ia, ib, X, err = ia[ok], ib[ok], X[ok], err[ok]
            if not len(X):
                continue
            pc, inside_c = self._in_frame(c, X)
            ic = np.full(len(X), -1)
            if len(p[c]):
                dc, jc = cKDTree(p[c]).query(pc, k=1)
                three = inside_c & (dc <= MT.REPROJ_MAX)
                ic[three] = jc[three]
            for m in np.flatnonzero((ic >= 0) | ~inside_c):          # principle 4: two-camera births only outside the third view
                idx = {a: ia[m], b: ib[m]}
                Xm = X[m]; e = err[m]; n = 2
                if ic[m] >= 0:
                    ks = sorted([a, b, c]); idx[c] = ic[m]
                    X3 = M3._ls(np.stack([rays[k][idx[k]] for k in ks])[None], np.stack([self.cams[k][0] for k in ks])[None])[0]
                    e3 = 0.0; good = True
                    for k in ks:
                        pk, zk, _ = R2.proj_jac(X3[None], *self.cams[k])
                        ek = float(np.linalg.norm(pk[0] - p[k][idx[k]])); good &= (zk[0] > 0) and ek <= MT.REPROJ_MAX; e3 += ek
                    if not good:
                        continue                                       # third view disagrees: no birth
                    Xm, e, n = X3, e3, 3
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

    def _share(self, k, sel, dets, used):
        """Attach confirmed tracks in sel (unassociated in camera k) to already-used detections."""
        R2 = self.R2; cam, basis = self.cams[k]
        if not len(sel) or not len(dets) or not used.any(): return np.zeros(0, int)
        px, zc, J = R2.proj_jac(self.X[sel, :3], cam, basis)
        uidx = np.flatnonzero(used)
        d, j = cKDTree(dets[uidx]).query(px, k=1)
        ok = (zc > 0) & (d <= SHARE_GATE_PX)
        loc = np.flatnonzero(ok)
        if not len(loc): return np.zeros(0, int)
        ti = sel[loc]; dj = uidx[j[loc]]
        Hm = np.zeros((len(ti), 2, 6)); Hm[:, :, :3] = J[loc]
        Pt = self.P[ti]
        S = Hm @ Pt @ Hm.transpose(0, 2, 1) + np.eye(2)[None] * SHARE_SIGMA_PX ** 2
        K = Pt @ Hm.transpose(0, 2, 1) @ np.linalg.inv(S)
        y = dets[dj] - px[loc]
        self.X[ti] = self.X[ti] + (K @ y[..., None])[..., 0]
        self.P[ti] = (np.eye(6)[None] - K @ Hm) @ Pt
        return ti

    def step(self, dets_per_cam):
        R2 = self.R2
        if len(self.X):
            self.X = self.X @ self.F.T
            self.P = self.F[None] @ self.P @ self.F.T[None] + self.Q[None]
        n = len(self.X)
        support = np.zeros(n, int); shared = np.zeros(n, int)
        self._det = [np.full(n, -1) for _ in range(3)]
        used = [np.zeros(len(d), bool) for d in dets_per_cam]
        conf_idx = np.flatnonzero(self.conf); tent_idx = np.flatnonzero(~self.conf)
        for k in range(3):
            for sel in (conf_idx, tent_idx):
                ti = self._associate(k, sel, dets_per_cam[k], used[k])
                support[ti] += 1
            miss = conf_idx[self._det[k][conf_idx] < 0]
            ts = self._share(k, miss, dets_per_cam[k], used[k])
            shared[ts] += 1
        consistent = np.zeros(n, bool)
        for i in np.flatnonzero(support >= 2):
            ks = [k for k in range(3) if self._det[k][i] >= 0]
            dd = [dets_per_cam[k][self._det[k][i]] for k in ks]
            rays = np.stack([R2.ray(*self.cams[k], dd[j][None])[0] for j, k in enumerate(ks)])
            Xl = M3._ls(rays[None], np.stack([self.cams[k][0] for k in ks])[None])[0]
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
        anysup = (support + shared) > 0
        self.miss[anysup] = 0; self.miss[~anysup] += 1
        alive = ~drop & ~(self.conf & (self.miss > MT.MAX_AGE)) & ~(self.bad >= MT.BAD_N)
        ci = np.flatnonzero(self.conf & alive)
        if len(ci) > 1:
            for i, js in enumerate(cKDTree(self.X[ci, :3]).query_ball_point(self.X[ci, :3], r=MT.DUP_M)):
                for j in js:
                    if j > i and alive[ci[i]] and alive[ci[j]]:
                        older = ci[i] if self.born[ci[i]] <= self.born[ci[j]] else ci[j]
                        alive[ci[j] if older == ci[i] else ci[i]] = False
        out_mask = self.conf & alive & anysup
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
