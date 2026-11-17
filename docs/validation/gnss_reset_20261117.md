# GNSS reset offline validation — 2026-11-17

Scope: localization consistency notification, externally requested GNSS reset,
ublox-owned GNSS reception/quality, two-point gnss2map conversion, opt-in launch wiring.
No navigation decisions, robot commands, physical receiver/NTRIP access, bag replay,
simulator, dependency installation, remote update, merge or push were performed.

Full evidence is under workspace `log/gnss_reset_20261117/` (generated, not committed).
`source_before.json` records full baseline SHAs, branches and clean status;
`*_before.patch` and `*_tested.patch` preserve tracked/new source diffs.
`environment.json` records OS/Python/Humble/system dependencies.
`build_clean.sh` and `test.sh` contain the exact clean environment build/test commands.
The build was invoked through `env -i HOME="$HOME" PATH=/usr/local/bin:/usr/bin:/bin
LANG=C.UTF-8 bash --noprofile --norc ...`; source underlay was `/opt/ros/humble` only.
Fresh output roots: `build/gnss_reset_clean`, `install/gnss_reset_clean`.
Build/test executor sequential, build compilation workers capped at two.

Final build: `build_final2.log/.exit`, 11 packages succeeded, exit 0.
Final focused cases: 83 individual cases passed, zero failed/errors/skipped:
GNSS epoch/status 46, conversion 4 C++ + 6 ROS, recovery 4 C++ + 7 ROS,
launch construction 3, existing navigation guard 7 and waypoint route 6.
`test.log/.exit` covers the initial eight suites, `test_extra2.log/.exit` the expanded
7-case recovery ROS suite. The final complete run after readability cleanup is
`test_final.log/.exit`; `test_result_final2.log/.exit` is the authoritative aggregate
(includes CTest wrappers). All completed final commands exit 0, zero failures/errors/skips.
`test_counts.json` lists individual XML counts. Process logs and synthetic calibration
inputs are retained under `processes/`. Synthetic ROS uses localhost domains 214/216/217.
Fixtures were read before execution; no hardware or motion launch is used.

Intermediate failures are preserved: build.log (Geographic library name), build2.log
(const Clock API), build_clean.log (shell nounset during ROS setup), build_clean2.log
(explicit-source build needed receiver/NTRIP dependencies selected too). Corrected
without installing dependencies or falling back to stale installed packages.
An additional duplicate-scan fixture initially failed due to an undrained genuinely
new scan; test_extra_failure.txt documents the race, test_extra.exit=1, corrected
fixture test_extra2.exit=0. Production code did not need changing for that case.
An early test_result.log ran during a test and saw a placeholder missing-result XML;
use the completed final result named above.

Not evaluated: real receiver output, CIT correction forwarding, RTK Fix/accuracy,
actual map calibration, kidnapping/recovery accuracy, motion, simulation, rollout.
Alpha is wall-nonpenetration consistency, not ground truth or unique scan matching.
Thresholds and covariance floor are configurable initial values, not calibrated acceptance.
The historical +/-3 m/axis-scale calibration is preserved but is not auto-applied.
The two reference points must be measured/revalidated for the selected map.

Baseline repositories:
- `emcl2_ros2`: `2927ec7496a60242ff16281fcb82be898ecc7f98`, `main`, clean.
- `gnss2map`: `ad6c97760f71b74a2e672641524339f7d7a8bfc9`, `feat/vps`, clean.
- `ublox_dgnss`: `de7cd53ad8947b705462fa63e75e8c844ef640cd`, `main`, clean.
- `cat_robot`: `e1ea294aac4a37774fe7de0fae40450efddfec90`, `main`, clean.
- `emcl2_msgs`: new independent repository, no previous HEAD; Apache-2.0.

Readability cleanup was followed by a rebuild and the complete focused suite.
Static Python AST/XML/YAML parsing and staged diff checks passed; see syntax_checks.json
and static_checks.json. Pure C++ tests total 8; synthetic/deterministic Python cases total 75.
