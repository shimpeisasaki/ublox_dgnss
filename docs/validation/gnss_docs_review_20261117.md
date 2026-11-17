# GNSS documentation review — 2026-11-17

This is a documentation-only audit of the GNSS recovery implementation. Read owning
AGENTS.md, current README/contracts, exact interface definitions, launch wiring,
recovery/quality/conversion source, the URDF and the prior validation summary before edits.
All five repositories were clean on `refactor/gnss-reset-ublox` at audit start.

## Corrections

- gnss2map README now starts with the current conversion contract. The original README
  is preserved verbatim below a dated historical notice in
  `gnss2map/docs/history/README_before_gnss_recovery_20261117.md`; original calibration,
  maps, recordings and legacy code are untouched.
- Public topic/type relationships, responsibility links and exact msg/srv definitions
  are reachable from the current entry documents. ublox's README/index include the
  reception/quality heartbeat. Position non-publication is distinct from status heartbeat.
- Removed the nonexistent `src/rtcm_msgs` path from the output-contract verification
  procedure, focused it on the output converter and required explicit fresh outputs.
  This procedure was statically checked, not executed during this audit.
- Corrected the recovery fixture description: its pipeline case also starts the ublox
  output converter and gnss2map, but no receiver/NTRIP/robot/simulator.
- Clarified retained GNSS input after map replacement and calibration change ownership,
  consistent with implementation; this audit changes no runtime behavior.
- Linked the authoritative URDF and documented per-heading planar XY antenna correction.
  Mounting numbers are not copied into another current configuration.
- Distinguished historical 2026-11-12 maintenance statements and the 2026-11-17 prior
  implementation tests from this documentation check.

## Verification and provenance

The audit uses Python standard-library static checks of Markdown local paths/anchors,
source-defined endpoint names, existing launch/config paths, archived-text preservation,
`git diff --check` and a syntax-only `bash -n src/emcl2_ros2/test/demo.bash` check. The
checker reads bounded named files, not recording/model payloads, and starts no ROS graph.
Complete commands, per-check counts/results, full before SHAs/status and staged diffs
are under workspace `log/gnss_docs_review_20261117/`; `checks.json` and `check.exit`
are authoritative for the audit outcome. Environment and initial full SHAs are in
`source_before.json`. No build, unit/ROS test, simulation, bag replay, receiver, NTRIP,
robot motion or network connection was run for this documentation check. No skill,
remote update, merge or push was used. No runtime source/config files were edited.

The prior 11-package build and 83 individual offline cases remain dated evidence in
`docs/validation/gnss_reset_20261117.md`, not a new validation claim for this prose audit.
Hardware RTK Fix, calibration accuracy and real kidnapping/recovery remain unverified.

## Audited source SHAs

- `emcl2_ros2`: `a63afa7b36a4df89dbfb133e8a97ec107e7e86d7` (clean).
- `emcl2_msgs`: `8450c1f4d9460529dede93880304df326e52c6c4` (clean).
- `gnss2map`: `fa316e6208576b414fc533ff6e2bb274d1757216` (clean).
- `ublox_dgnss`: `13f27b1298fafed7e58b6754c86671881c4f1594` (clean).
- `cat_robot`: `2a533d858132440c114f010e047a717f54761708` (clean).

Static review outcome: 17 Markdown files, 147 checks passed; 0 failures, 0 skips; checker exit 0. This count is not a ROS test count.
