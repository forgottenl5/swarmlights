# Second baseline T5 (merge-tolerant three-camera tracker): pre-registration (13 Nov 2026)

Status: REGISTERED before the T5 code exists. T5 is developed only on development shows (v2.1 generator, seeds 900 and 901, 500 drones), frozen and fingerprinted, then scored once on the 8 registered v2.1 shows using their stored detections. Deviations logged.

## Why
v2.1 (docs/DATASET_V2_1_RESULTS.md): the three-camera baseline T4c scores below the best single camera in all 8 shows. Diagnosed cause: formations seen edge-on or deep collapse into merged blobs in one camera (e.g. 14 detections for 500 drones), and T4c needs two consistent cameras per track per frame and one detection per track per camera. A release needs a reasonable second baseline so the benchmark's difficulty is not mistaken for one weak tracker.

## T5 principles (fixed now; details frozen in code before scoring)
Starts from T4c-v1 (tools/pilot_v2/mv_tracker3.py) and changes only:
1. Shared detections: after the one-to-one association in a camera, confirmed tracks still unassociated in that camera may attach to an already-used detection within a gate of 4 px; such a shared measurement updates the state with inflated pixel noise (σ 3 px instead of 1 px) and does not count towards the consistency check.
2. Single-camera survival: a confirmed track supported by one camera (shared or not) is kept and updated; it is deleted only after MAX_AGE frames without any support (as T4c).
3. Consistency check, births, tentative-track rules and duplicate removal are unchanged from T4c and use only non-shared detections.
No ground-truth information is used.

## Development (fixed now)
- Seeds 900 and 901 only; at most 4 T5 versions; each logged with its numbers.
- Gate on seed 901 (rendered): T5 airborne IDF1 > T4c airborne IDF1 on the same show, and T5 oracle airborne MOTA ≥ 0.95.
- If no version passes within 4, stop and report; no registered scoring.

## Predictions (8 registered v2.1 shows, stored detections, scoring as v2.1)
P1. T5 airborne IDF1 > T4c airborne IDF1 on ≥ 6 of 8 shows.
P2. T5 airborne IDF1 > best single-camera 2-D IDF1 on ≥ 4 of 8 shows.
P3. T5 oracle airborne MOTA ≥ 0.95 on ≥ 6 of 8 shows (same as T4c's 6/8 or better).
P4. Mean T5 airborne IDF1 at 1,000 drones < mean at 500 drones (the larger shows stay harder).

## Not claimed
Not a state-of-the-art tracker; a second reasonable baseline. Same scoring caveat as v2.1: 2-D and 3-D IDF1 are not strictly comparable.
