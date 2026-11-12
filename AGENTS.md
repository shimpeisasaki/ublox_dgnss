# Repository maintenance

Preserve upstream packages, licenses, USB/parameter state machines, and local output validity behavior. docs/gnss_output_contract.md and docs/rtk_tsudanuma.md own output/RTK contracts. Keep credentials outside Git; do not contact receivers or NTRIP as a documentation check. This workspace uses Humble consistently.

## Changes and evidence

Update the authoritative feature/interface/launch documentation in the same change. Link to the owner rather than copying current instructions; preserve Logbooks and historical evaluation conditions. Record repository SHA, dirty diff, environment, input identity, command, counts, exit status, failures/skips and unverified conditions. Distinguish offline checks, simulation and hardware evidence.

Start with related offline tests after reading their fixtures. Use ROS 2 Humble consistently and explicitly select actual source paths and fresh build/install outputs. Keep parallel workers at most two. Never start hardware nodes, enable motion, send robot commands, replay bags or launch simulation without explicit authorization. Preserve safety latches and require manual permission/rearm.

Inspect metadata, filenames and summaries before any large recording/model/log. Narrow searches to relevant source and exclude generated output/data/cache. Store full check logs in generated log/ paths, report concise failures and preserve the original exit code. Do not install dependencies, update upstream, push, rewrite history or change main/master as part of this implementation.
