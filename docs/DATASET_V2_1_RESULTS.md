# Dataset v2.1: build, checks and results (13 Nov 2026)

Pre-registration docs/DATASET_V2_1_PREREG.md (ff153553..., 12 Nov 22:13 UTC). Code frozen 22:22 UTC (V2_1_FROZEN.sha256), verified OK before the build, after the container restart and before the checks. 8 shows, 8 different choreographies (500 and 1,000 drones × seeds 20–23). 1.7 GB in 8 archives (17 files each).

## Checks: all PASS
- C1 rebuild: 30/30 random frames rebuilt from seeds match the decoded videos (minimum PSNR 39.0 dB; limit 30).
- C2 ground truth: pixel positions recompute to < 0.01 px in every show.
- C3 detections: 30/30 reproduce exactly from the decoded videos.
- C4 checksums: every file matches.

## Predictions: 5 of 6 PASS
- W1 spacing: **PASS** 8/8 (every show ≥ 2.12 m, every transition and shift check passes).
- W2 choreographies differ: **PASS**, mean drone-position difference between shows 42–54 m (threshold 10 m).
- W3 oracle ceiling ≥ 0.95 MOTA in every show: **FAIL** 6/8. The tracker's ceiling broke on two 1,000-drone shows (seed 21: MOTA 0.869 / IDF1 0.669; seed 23: 0.865 / 0.744), even with exact detections.
- W4 images make it hard (rendered/oracle IDF1 < 0.95): **PASS** 8/8.
- W5 realism direction: **PASS**, coloured dots 99%, clipped dots 20% (registered: > 20% coloured, 15–50% clipped).
- W6 harder than v2.0: **PASS**, mean rendered airborne IDF1 at 500 drones 0.451 vs 0.817 in v2.0.

| Show | Best single camera IDF1 (2-D) | T4c rendered airborne MOTA / IDF1 | T4c oracle airborne MOTA / IDF1 |
|---|---|---|---|
| n500 s20 | 0.539 | 0.549 / 0.435 | 1.000 / 0.999 |
| n500 s21 | 0.505 | 0.210 / 0.402 | 1.000 / 0.999 |
| n500 s22 | 0.703 | 0.481 / 0.448 | 0.999 / 0.998 |
| n500 s23 | 0.601 | 0.419 / 0.519 | 1.000 / 1.000 |
| n1000 s20 | 0.531 | 0.388 / 0.390 | 0.990 / 0.967 |
| n1000 s21 | 0.494 | 0.059 / 0.353 | 0.869 / 0.669 |
| n1000 s22 | 0.532 | 0.273 / 0.390 | 0.976 / 0.961 |
| n1000 s23 | 0.502 | 0.104 / 0.325 | 0.865 / 0.744 |

## Not registered, stated plainly
- In all 8 shows the three-camera 3-D tracker scores below the best single camera's 2-D IDF1. The metrics are not directly comparable (pixels vs metres; the 2-D score only counts drones visible to that camera), but the baseline is clearly weak on varied choreography. Cause seen in the data: formations edge-on to one camera collapse into a few blobs (e.g. 14 detections for 500 drones), which breaks the tracker's two-camera agreement rule.
- At 1,000 drones the tracker fails even with exact detections on 2 of 4 shows, so the hardest shows are hard for association as well as for detection.

## Deviations
- D1 A container restart interrupted rendering of n1000 s20 and s21 (camera K1 partial). Both were restarted from scratch with unchanged frozen code; partial outputs were overwritten. Recorded in v21_out/DEVIATIONS.txt.

## Meaning for the release
v2.1 is reproducible, physically valid, varied and much harder than v2.0. The baseline result needs care in the dataset card: "a textbook three-camera tracker does worse than a single camera" is the honest headline and the open challenge; a second, merge-tolerant baseline is still planned before release.
