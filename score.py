"""score.py: score a 3-D tracker on one SwarmLights show.

usage:  python score.py <your_tracks.csv[.gz]> <show_dir> [--all-frames]
input:  CSV with columns frame,track,x,y,z (metres, same world frame as gt.csv.gz; frame = 0-based frame index;
        track = your identity number, kept across frames).
output: MOTA and IDF1 (plus misses, false positives, ID switches) printed as JSON.

Rules (same as the published baselines):
- Ground truth for a frame: every drone seen by at least 2 of the 3 cameras in that frame (in1+in2+in3 >= 2).
- Match distance 1.0 m (Euclidean, 3-D).
- Default scope "airborne": all frames except the take-off climb and the final landing descent
  (phase of a frame = last phase in show.json whose frame_start <= frame). --all-frames scores every frame.
- MOTA, switches, misses and false positives from py-motmetrics; IDF1 by the standard definition
  (Ristani et al. 2016), computed sparsely so trackers with many identities fit in memory.
needs:  pip install numpy pandas scipy motmetrics
"""
import sys, json, os
from collections import defaultdict
import numpy as np, pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
import motmetrics as mm

MATCH_M = 1.0
EXCLUDED = ('takeoff_climb', 'landing_descent')


def idf1_sparse(gt_frames, hyp_frames, max_d):
    cnt = defaultdict(int); ngt = nh = 0
    for (gid, gp), (hid, hp) in zip(gt_frames, hyp_frames):
        ngt += len(gid); nh += len(hid)
        if len(gid) and len(hid):
            for a, js in enumerate(cKDTree(np.asarray(hp)).query_ball_point(np.asarray(gp), r=max_d)):
                for j in js:
                    cnt[(gid[a], hid[j])] += 1
    if not cnt:
        return 0.0
    gids = sorted({g for g, _ in cnt}); gi = {g: k for k, g in enumerate(gids)}
    per_row = defaultdict(list)
    for (g, h), c in cnt.items():
        per_row[g].append((c, h))
    keep = set()
    for lst in per_row.values():
        lst.sort(reverse=True); keep.update(h for _, h in lst[:len(gids)])
    hids = sorted(keep); hi = {h: k for k, h in enumerate(hids)}
    M = np.zeros((len(gids), len(hids)), np.float32)
    for (g, h), c in cnt.items():
        if h in hi:
            M[gi[g], hi[h]] = c
    r, c = linear_sum_assignment(-M)
    return 2 * float(M[r, c].sum()) / (ngt + nh)


def score(gt_frames, hyp_frames, max_d=MATCH_M):
    acc = mm.MOTAccumulator(auto_id=False)
    for f, ((gid, gp), (hid, hp)) in enumerate(zip(gt_frames, hyp_frames)):
        D = mm.distances.norm2squared_matrix(gp, hp, max_d2=max_d ** 2) if len(gid) and len(hid) else np.empty((len(gid), len(hid)))
        acc.update(list(gid), list(hid), D, frameid=f)
    s = mm.metrics.create().compute(acc, metrics=['mota', 'num_switches', 'num_false_positives', 'num_misses', 'num_objects'], name='x')
    out = {k: float(s.loc['x', k]) for k in s.columns}
    out['idf1'] = idf1_sparse(gt_frames, hyp_frames, max_d)
    out['num_hyp_ids'] = len({i for f in hyp_frames for i in f[0]})
    return out


def load(tracks_path, show_dir):
    show = json.load(open(os.path.join(show_dir, 'show.json'))); T = int(show['frames'])
    gt = pd.read_csv(os.path.join(show_dir, 'gt.csv.gz'))
    gt = gt[(gt['in1'] + gt['in2'] + gt['in3']) >= 2]
    gg = {f: d for f, d in gt.groupby('frame')}
    tr = pd.read_csv(tracks_path)
    missing = {'frame', 'track', 'x', 'y', 'z'} - set(tr.columns)
    if missing:
        sys.exit(f'tracks file is missing columns: {sorted(missing)}')
    hh = {f: d for f, d in tr.groupby('frame')}
    empty = (np.zeros(0, int), np.zeros((0, 3)))
    G = [(gg[f]['id'].to_numpy(), gg[f][['x', 'y', 'z']].to_numpy()) if f in gg else empty for f in range(T)]
    H = [(hh[f]['track'].to_numpy(), hh[f][['x', 'y', 'z']].to_numpy()) if f in hh else empty for f in range(T)]
    name = np.empty(T, dtype=object)
    for p in show['phases']:
        name[p['frame_start']:] = p['name']
    return G, H, name


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__)
    G, H, name = load(args[0], args[1])
    keep = range(len(G)) if '--all-frames' in sys.argv else [f for f in range(len(G)) if name[f] not in EXCLUDED]
    res = score([G[f] for f in keep], [H[f] for f in keep])
    res['scope'] = 'all_frames' if '--all-frames' in sys.argv else 'airborne'
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}, indent=1))


if __name__ == '__main__':
    main()
