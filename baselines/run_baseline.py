"""run_baseline.py: run a SwarmLights baseline tracker on one show's reference detections.

usage:  python run_baseline.py T4c|T5 <show_dir> <out_tracks.csv.gz>
then:   python ../score.py <out_tracks.csv.gz> <show_dir>
Reads calibration.json, show.json and detections_K{1,2,3}.csv.gz; writes frame,track,x,y,z.
T4c = mv_tracker3.MultiView2of3 (two-of-three-camera tracker); T5 = mv_tracker5.MultiViewMerge (T4c + shared
detections + third-view verification of new tracks).
T5: reproduces the published outputs exactly (it was scored on these stored detections).
T4c: the published T4c outputs were computed from unrounded detections; the stored detections are rounded to 0.001 px,
and T4c is sensitive enough that a rerun differs slightly (see README, "Reproducing the baselines").
needs:  pip install numpy pandas scipy
"""
import sys, os, json, gzip, time
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geometry as G, mv_tracker3 as M3, mv_tracker5 as M5


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ('T4c', 'T5'):
        sys.exit(__doc__)
    which, show_dir, out = sys.argv[1:]
    cal = json.load(open(os.path.join(show_dir, 'calibration.json')))
    cams = [(np.array(cal[k]['position_m'], float), (np.array(cal[k]['right'], float), np.array(cal[k]['up'], float),
             np.array(cal[k]['forward'], float))) for k in ('K1', 'K2', 'K3')]
    T = int(json.load(open(os.path.join(show_dir, 'show.json')))['frames'])
    D = []
    for k in (1, 2, 3):
        df = pd.read_csv(os.path.join(show_dir, f'detections_K{k}.csv.gz'))
        g = {f: d[['u', 'v']].to_numpy() for f, d in df.groupby('frame')}
        D.append([g.get(f, np.zeros((0, 2))) for f in range(T)])
    tr = M3.MultiView2of3(G, cams) if which == 'T4c' else M5.MultiViewMerge(G, cams)
    t0 = time.time()
    with gzip.open(out, 'wt') as fh:
        fh.write('frame,track,x,y,z\n')
        for f in range(T):
            ids, X = tr.step([D[k][f] for k in range(3)])
            for i, p in zip(ids, X):
                fh.write(f'{f},{i},{p[0]:.4f},{p[1]:.4f},{p[2]:.4f}\n')
            if f % 500 == 0:
                print(f'frame {f}/{T}  {round(time.time() - t0)} s', flush=True)
    print('wrote', out)


if __name__ == '__main__':
    main()
