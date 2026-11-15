# T5 pre-registration, amendment 1 (14 Nov 2026)

Amends: BASELINE_T5_PREREG.md (sha256 84ab9010e4be29f50fb2a7935fad25b7e188664bb7cdd9f328866d32c1b514db).
Status: written after T5-v1 failed the development gate and before any T5 code is scored on the 8 registered shows. No registered show has been touched by T5. Versions used so far: 1 of 4 (T5-v1).

## Why
Diagnosis of T5-v1 on development show n500_s901 (logged in T5_DEV_LOG.md, ground truth used for diagnosis only, never as tracker input):
- The main loss is ghost tracks: a point where two cameras' lines of sight through two different drones cross, with no drone there. In a phase with no merged blobs (hold_3_grid), true tracks fit a detection in all three cameras every frame, while 75-81 % of false tracks fit only one or two cameras and sit a median 7-10 m from any drone.
- Ghosts are born because a two-camera birth only needs "some detection within 6 px" of its projection in the third camera, and in a regular formation almost any point is that close to some dot (spacing 12-15 px).
- Ghosts also take detections that real drones need, which explains part of the misses.
- Deleting confirmed tracks that a camera contradicts was tested offline and rejected: it removes 32-60 % of true tracks, because merged blobs make real tracks look contradicted too.

## Change (adds principle 4; principles 1-3 stay as registered)
4. Third-view verification of new tracks. When a birth candidate or a tentative track projects inside all three cameras' frames, it is created or confirmed only if the third camera supports it: a free detection within REPROJ_MAX (2 px) of its projection, so that three rays agree. An exception may allow two-camera births where the third camera's view is plausibly merged; the exact exception rule and its threshold are development choices, frozen in code before scoring. This rule never deletes a confirmed track. No ground-truth information is used.

## Unchanged
- Development: seeds 900 and 901 only; the remaining 3 versions (T5-v2 to T5-v4), each logged with its numbers.
- Gate on seed 901: T5 airborne IDF1 > T4c airborne IDF1 on the same show, and T5 oracle airborne MOTA ≥ 0.95. If no version passes, stop and report; no registered scoring.
- Predictions P1-P4, scoring, and the "Not claimed" section, word for word.

## Disclosure
Results will state that T5 was amended once, before scoring, with this file's fingerprint, and that T5-v1 (registered principles only) failed the development gate.
