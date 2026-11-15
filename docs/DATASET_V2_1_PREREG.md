# Dataset v2.1 (varied choreography + realism upgrades): pre-registration (12 Nov 2026)

Status: REGISTERED before the new code exists. Code frozen and fingerprinted before the build; deviations logged.

## Why
v2.0 (docs/DATASET_V2_0_RESULTS.md): the show generator ignores its seed, so v2.0 has 4 choreographies, and the tracker was developed on the default one. Realism check v1 (docs/REALISM_CHECK_RESULTS.md): real shows use coloured LEDs, 27–37% of dots clip to white, video is compressed, and other lights appear near the horizon; v2.0 models none of these.

## Choreography (new module core/show_variants.py; show_generator.py unchanged)
- rng = numpy default_rng(seed). Takeoff, landing, ground grid (3 m), speed/acceleration limits, quintic motion and exact assignment exactly as show_generator.
- 3 or 4 formations drawn without replacement from {vertical grid, rings, heart, sphere, flat grid, flat rings} (show_generator builders), random order.
- Per formation: spacing s ∈ U[3.0, 4.0] m; rotation about the vertical axis U[0°, 360°); vertical formations also tilted U[−30°, +30°] about a horizontal axis; centre x, y ∈ U[−40, 40] m; centre height U[60, 110] m, raised if needed so the lowest drone is ≥ 20 m. Hold U[5, 10] s.
- With probability 0.5 after a hold: a rigid shift of the whole formation by a random horizontal vector of length U[15, 35] m.
- Rotations and shifts preserve pairwise distances, so the D/√2 clearance bound (≥ 2.12 m) is expected to hold.

## Lights and rendering (camera layout, resolution, detector, trackers, scoring unchanged from v2.0)
- Colour: each formation gets a scheme drawn from {solid colour, two-colour gradient along a random axis, radial two-colour}; colours from a fixed 8-colour LED palette (red, orange, amber, green, cyan, blue, magenta, white). Each drone's colour interpolates linearly during transitions from its current colour to its target colour. Ground and climb phases: dim white.
- Brightness per drone U(0.8, 1.6) × colour; Gaussian spot σ 1 px plus a bloom halo (σ 3 px, 15% of peak); clipped at 255.
- Distractor lights: 10 static lights per show near the horizon band of each camera (fixed positions and brightness per show, ±10% flicker per frame); labelled in ground truth as non-drone.
- Sensor noise as v2.0 (σ 2/255, seeded per frame), then each camera's frame sequence is encoded with H.264 (libx264, CRF 28, preset medium, yuv420p) as a phone-like video. The MP4 is the official image data; detections are computed on the decoded MP4 frames.
- Detector: v2.0 detector on V = max(R, G, B).

## Content
N ∈ {500, 1000}, seeds {20, 21, 22, 23}: 8 shows, 8 different choreographies. Ground truth adds per-frame drone RGB and the distractor list. Baselines: T2 per camera, T4c-v1 (unchanged, dc00bb98) on rendered and oracle detections. 2,000 and 5,000 drones are left to a later run on the founder's PC.

## Predictions
W1. Every show: minimum pairwise distance ≥ 2.12 m over all frames; formation_spacing_check passes for every transition and shift.
W2. Choreographies differ: for each size, every pair of shows differs by a mean drone-position distance > 10 m over the airborne frames (time-aligned up to the shorter show).
W3. Every show: T4c oracle airborne MOTA ≥ 0.95.
W4. Every show: T4c airborne IDF1 rendered / oracle < 0.95.
W5. Realism direction (realism-check pipeline on K1 frames, 1 frame per 10 s of airborne show): pooled over shows, coloured-dot fraction > 0.2 and clipped-dot fraction in [0.15, 0.50].
W6. Harder than v2.0: mean T4c rendered airborne IDF1 over the four 500-drone v2.1 shows < 0.817 (v2.0 default 500 mean).

## Checks before any release
C1 rebuild: 30 random (show, camera, frame) clean renders rebuilt from seeds match the decoded MP4 frame with PSNR ≥ 30 dB. C2 ground-truth pixel recomputation < 0.01 px. C3 detections reproduce exactly from the decoded MP4 for 30 random frames. C4 checksums.

## Not claimed
Still synthetic; no ground-truth validation against real footage; one camera layout; no camera shake (left for later); T4c was developed on a different choreography (good: all v2.1 shows are unseen).

## Effort guard
If the build or checks need more than two fixes, stop and report.
