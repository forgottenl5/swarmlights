# Second baseline T5: registered results (14 Nov 2026)

Pre-registration: BASELINE_T5_PREREG.md (sha256 84ab9010e4be29f50fb2a7935fad25b7e188664bb7cdd9f328866d32c1b514db, 13 Nov 2026).
Amendment 1: BASELINE_T5_AMENDMENT_1.md (sha256 3acbb8cec230bed4b2e97d50b83a75ce7e56fe524a1015d8ceaeffb981070c42), registered after T5-v1 failed the development gate and before any registered show was touched.
Frozen code: T5-v2, fingerprints in T5_FROZEN.sha256 (mv_tracker5.py acccff2f…), verified before and after the run. Scored once on the 8 registered v2.1 shows with their stored detections. Scoring script: score_t5.py; numbers in v21_out/analysis_t5.json.

## Disclosure
- T5 was amended once, before scoring. T5-v1 (registered principles 1-3 only) failed the development gate on seed 901: airborne IDF1 0.3712 vs T4c 0.3721. Diagnosis (T5_DEV_LOG.md): most errors were ghost tracks, points where two cameras' lines of sight through two different drones cross with no drone there; in a regular formation a two-camera birth almost always finds "some" dot near its projection in the third camera.
- Amendment 1 added principle 4: a new track that projects inside all three cameras must be confirmed by a free third-camera detection within 2 px. It never deletes confirmed tracks and uses no ground truth.
- 2 of the 4 allowed development versions were used.

## Predictions: 3 of 4 PASS
- P1 T5 airborne IDF1 > T4c on ≥ 6 of 8 shows: **PASS, 6/8** (exactly the threshold). T5 is worse than T4c on both seed-23 shows.
- P2 T5 airborne IDF1 > best single camera's 2-D IDF1 on ≥ 4 of 8 shows: **FAIL, 0/8.** The three-camera tracker is still below the best single camera everywhere (same comparability caveat as v2.1).
- P3 T5 oracle airborne MOTA ≥ 0.95 on ≥ 6 of 8 shows: **PASS, 8/8** (lowest 0.9945).
- P4 mean T5 airborne IDF1 at 1,000 drones < at 500 drones: **PASS**, 0.401 vs 0.486.

| Show | Best single camera IDF1 (2-D) | T4c airborne MOTA / IDF1 | T5 airborne MOTA / IDF1 | T5 oracle airborne MOTA / IDF1 |
|---|---|---|---|---|
| n500 s20 | 0.539 | 0.549 / 0.435 | 0.683 / 0.466 | 1.000 / 0.999 |
| n500 s21 | 0.505 | 0.210 / 0.402 | 0.377 / 0.480 | 1.000 / 0.999 |
| n500 s22 | 0.703 | 0.481 / 0.448 | 0.614 / 0.525 | 1.000 / 1.000 |
| n500 s23 | 0.601 | 0.419 / 0.519 | 0.373 / 0.471 | 1.000 / 1.000 |
| n1000 s20 | 0.531 | 0.388 / 0.390 | 0.533 / 0.438 | 0.998 / 0.997 |
| n1000 s21 | 0.494 | 0.059 / 0.353 | 0.289 / 0.451 | 0.995 / 0.995 |
| n1000 s22 | 0.532 | 0.273 / 0.390 | 0.544 / 0.451 | 0.995 / 0.996 |
| n1000 s23 | 0.502 | 0.104 / 0.325 | 0.144 / 0.264 | 0.998 / 0.997 |

## Not registered, stated plainly
- False tracks fall on every show, by 48-82 % (e.g. n1000 s20: 656k to 121k). This is the effect principle 4 was designed for.
- Misses rise on 3 of 8 shows, most on seed 23 (+25 % at 500 drones, +12 % at 1,000). Without a merge exception, real drones inside merged blobs cannot be born, and on seed 23 that loss outweighs the fewer ghosts. This is the known weakness noted at the freeze.
- T5's oracle ceiling holds on all 8 shows, including the two 1,000-drone shows where T4c's ceiling broke (0.869 and 0.865). With exact detections, association is no longer the limit; the remaining gap is detection (merged blobs).
- MOTA improves on 7 of 8 shows.

## Meaning for the release
T5 is a clearly better second baseline (fewer false tracks, higher MOTA, a ceiling that holds everywhere), but it does not beat a single camera. The open challenge for the benchmark stays "make three cameras beat one in dense formations", with two specific failure modes now documented: ghost tracks from line-of-sight crossings (largely fixed by third-view verification) and drones lost inside merged blobs (open).
