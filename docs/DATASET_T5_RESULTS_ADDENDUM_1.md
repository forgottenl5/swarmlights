# T5 results, addendum 1: inputs check (15 Nov 2026, not registered)

Adds to DATASET_T5_RESULTS.md (sha256 a4698cb507c54e96671356acf704dbe7509d91810fd8e196514884f3b650b8ed), which is unchanged.

Found during the release review: the published T4c baseline runs (dataset v2.1 build) used unrounded detections, while T5 was run on the stored detection files, which are rounded to 0.001 px. So the registered T4c-vs-T5 comparison used very slightly different inputs.

Check: T4c rerun on the stored detections for all 8 shows (release code baselines/run_baseline.py, scored with score.py).

| Show | T4c IDF1 published / rerun | T5 IDF1 | T4c MOTA published / rerun | T5 MOTA |
|---|---|---|---|---|
| n500 s20 | 0.435 / 0.438 | 0.466 | 0.549 / 0.553 | 0.683 |
| n500 s21 | 0.402 / 0.398 | 0.480 | 0.210 / 0.205 | 0.377 |
| n500 s22 | 0.448 / 0.454 | 0.525 | 0.481 / 0.483 | 0.614 |
| n500 s23 | 0.519 / 0.520 | 0.471 | 0.419 / 0.420 | 0.373 |
| n1000 s20 | 0.391 / 0.390 | 0.439 | 0.388 / 0.383 | 0.533 |
| n1000 s21 | 0.353 / 0.353 | 0.451 | 0.059 / 0.062 | 0.289 |
| n1000 s22 | 0.390 / 0.395 | 0.451 | 0.274 / 0.318 | 0.544 |
| n1000 s23 | 0.325 / 0.321 | 0.264 | 0.104 / 0.103 | 0.144 |

Result: T4c's airborne IDF1 moves by at most 0.006 and MOTA by at most 0.006, except n1000 s22 MOTA (+0.045). On identical inputs T5 still has higher IDF1 than T4c on 6 of 8 shows, so P1's outcome is unchanged. The registered numbers stay as published; this check is reported alongside them.
