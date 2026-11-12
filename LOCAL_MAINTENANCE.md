# Local maintenance

## Adopted source and contracts

The 2026-11-12 implementation starts at
`2e8824489c24fd8180eb36acc864046c44bd4417` on local baseline `main`.
The locally available `upstream/main` and merge base are
`1cd9ca9e1a959df51d2631e444400bdf0b327c2f`; no remote refresh was performed.
The implementation branch is `refactor/implementation-20261112`.
Retain the upstream package layout, [LICENSE](LICENSE), USB/parameter state machines
and Humble configuration. Do not rename baselines for consistency alone.

The local history includes compatible GNSS topics (`abd2cab`), an upstream merge
(`b52cee2`), RTK profiles/continuous NTRIP streams (`9a140ef`), and valid matching-epoch
output (`2e88244`). These changes are not interchangeable with an unmodified upstream checkout.

- [GNSS output contract](docs/gnss_output_contract.md) owns epoch matching, flags,
  covariance conversion, source timestamps and missing/stale-output handling.
  No valid epoch means no output, not a repeated last position.
- [RTK preparation and evidence](docs/rtk_tsudanuma.md) owns CIT/Matsudo profiles,
  receiver/correction paths, connection lifetime, credentials policy and unverified Fix/accuracy.
- [README compatibility section](README.md#gnss_launch-compatible-topics) links these
  contracts to current launch usage. Keep historical reception evidence unchanged.

Credentials remain outside Git. Do not read or copy the credential file into reports,
log authentication headers, contact a caster, or connect a USB receiver to check prose.
Correction reception alone is not RTK Fix or position-accuracy acceptance.

## Offline maintenance

For documentation changes, validate local links, referenced files and the diff.
Do not execute launches or infer runtime success from a document check.
For separately authorized code validation, use ROS 2 Humble and the focused build/test
procedure in the output contract, with the actual source checkout and fresh outputs.
The registered checks are:

- `ublox_nav_sat_fix_hp_node/test/test_epoch_output.py`, CTest `epoch_output`,
  synthetic UBX inputs on localhost domain 214, without the receiver or NTRIP.
- `ntrip_client_node/test/test_ntrip_stream.py`, CTest `ntrip_stream`,
  the loopback fake-NTRIP check described in the RTK document, domain 213.
  It is not permission to test against a public caster.

Inspect fixtures and subprocess/network behavior before selecting tests. Preserve USB
RAM-only configuration behavior and the separation between standalone and correction-enabled
launches. No build, test process, receiver or network connection ran for this documentation unit.

## Evidence and data rules

Update authoritative docs in the same change as behavior/interfaces/configuration.
Record full tested SHA, dirty diff, OS/ROS/dependencies, input identity, exact commands,
passed/failed/skipped counts, exit status, log paths and unverified conditions.
Separate offline, simulation and hardware evidence; never promote an old test to a new SHA.

Inspect metadata, paths, sizes and existing summaries before recordings/models/logs.
Read payloads only for a named question with bounded files, topics, time and samples.
Exclude generated output/data/cache from broad searches. Save complete logs separately,
report bounded causal excerpts and preserve original exit codes. Follow [AGENTS.md](AGENTS.md).
