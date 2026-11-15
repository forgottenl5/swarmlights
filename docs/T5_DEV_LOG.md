# T5 development log (docs/BASELINE_T5_PREREG.md)
## T5-v1 (SHARE_GATE_PX 4.0, SHARE_SIGMA_PX 3.0), dev show n500_s901, 13 Nov 2026
- T4c airborne: MOTA 0.3945, IDF1 0.3721; T4c oracle airborne MOTA 1.0
- T5-v1 airborne: MOTA 0.3636, IDF1 0.3712; T5-v1 oracle airborne MOTA 1.0
- Gate (T5 IDF1 > T4c IDF1 and oracle MOTA >= 0.95): FAIL (IDF1 0.3712 <= 0.3721). Versions used: 1 of 4.

## Diagnosis of T5-v1 (no new version; 14 Nov 2026, dev show n500_s901 only)
- Identity switches are not the main loss: airborne switches T4c 1,557 / T5-v1 1,269. T5-v1 has 31k fewer misses but 76k more false tracks than T4c.
- Detection noise is not the cause: in hold_3_grid (no merging, 1.02 detections per visible drone in every camera) detections sit 0.13 px (median) from the true projection, neighbours 12-15 px apart; yet T4c finds 74% and T5-v1 78% of drones, and 35% of tracks are false in both.
- Cause found: ghost tracks. True tracks in hold_3_grid fit a detection (<=2 px) in all 3 cameras 100% of the time; false tracks fit only 1-2 cameras 75-81% of the time and sit a median 7-10 m from any drone, i.e. two cameras' lines of sight crossing where there is no drone. They are confirmed under the 2-of-3 rule, consume detections, and so also block births of real drones (misses).
- Two remedy shapes tested offline on T5-v1 output, both rejected: (a) per-frame deletion when an in-view camera has no detection within R px: removing 75-90% of false tracks also removes 32-43% of true track-frames (merged blobs put the third camera's detection several px away); (b) the same after N consecutive contradicted frames: worse (keeps only 40-56% of true track-frames), because merges last long.
- Any further remedy changes births or the consistency check, which BASELINE_T5_PREREG.md fixes as unchanged from T4c, so it needs a registered amendment before any T5-v2. Versions used: still 1 of 4.

## Amendment 1 registered (14 Nov 2026, before any registered scoring)
BASELINE_T5_AMENDMENT_1.md sha256 3acbb8cec230bed4b2e97d50b83a75ce7e56fe524a1015d8ceaeffb981070c42. Adds principle 4 (third-view verification of new tracks). Gate, predictions and scoring unchanged. Versions used: 1 of 4.

## T5-v2 (14 Nov 2026, dev show n500_s901, under amendment 1)
Change from v1: births need three-camera agreement whenever the point is inside the third camera's frame (two-camera births only outside it); no merge exception.
| airborne | T4c | T5-v1 | T5-v2 |
|---|---|---|---|
| MOTA | 0.3945 | 0.3636 | 0.4915 |
| IDF1 | 0.3721 | 0.3712 | 0.3897 |
| false tracks | 240,990 | 317,044 | 64,357 |
| misses | 624,163 | 592,698 | 662,406 |
| ID switches | 1,557 | 1,269 | 1,108 |
Oracle airborne MOTA 1.0000, IDF1 0.9984.
Gate: IDF1 0.3897 > 0.3721 PASS; oracle MOTA >= 0.95 PASS. Versions used: 2 of 4. Known weakness: misses rose by 70k (no merge exception), left as is.

## Frozen (14 Nov 2026): T5-v2, approved; remaining versions 3-4 not used
Fingerprints in T5_FROZEN.sha256 (mv_tracker5.py acccff2faa3e5638…). Registered scoring on the 8 v2.1 shows follows, once, with stored detections.

## Registered scoring (14 Nov 2026)
Frozen fingerprints verified before and after. 8 shows, one run each. P1 PASS 6/8, P2 FAIL 0/8, P3 PASS 8/8, P4 PASS (0.401 < 0.486). Results: DATASET_T5_RESULTS.md, v21_out/analysis_t5.json, fingerprints T5_RESULTS.sha256. No deviations.
