# Verification — IncidentLens AI
Date: 11 October 2026 (Asia/Calcutta)
Platform: Windows; existing bundled Python 3.12.14. No package installation.

## Completed checks
- 33 automated checks passed: evidence citations, known/unknown/conflicting sample cases, incident isolation, literal/time filters, input limits, source hashes, redaction, destructive-tool rejection, local planner validation/fallback, real MCP subprocess framing and loopback HTTP protection.
- JavaScript syntax check passed using an existing Node runtime.
- Browser checked: sample queue, report switching, counter-evidence confidence reduction, unknown-cause result and evidence links focusing the cited source.
- JSON and Markdown report API output verified. Browser download buttons were not exercised, to respect the earlier no-download constraint.
- MIT notice is Copyright (c) 2026 Alisha; implementation and fixtures were created independently.
- CLI report smoke check performed after the final text-label cleanup.

## Pending
- Reliable end-to-end local Ollama planning; current model fell back during live checks.
- External MCP client/Inspector interoperability.
- Other Python versions, mobile/responsive browser interaction and accessibility audit.
- Production telemetry adapters, semantic retrieval, persistence and production-scale evaluation.

This is a sample-only prototype. The default browser workflow is deterministic; local Ollama planning was live-tested but did not complete reliably; fallback remains enabled.

## Follow-up live checks
- Existing Ollama service was already running; no service was started/stopped or reconfigured.
- Existing llama3.2:1b (1.2B Q8_0) advertised completion/tools and no remote model/host metadata.
- First planner check hit the 15-second request boundary and fell back. A warmed diagnostic exposed a mismatch: advertised optional filters were rejected by the full-evidence guard.
- Corrected the planner-only schemas to expose exactly the current incident ID. General MCP search tools still support safe filters.
- Retest recorded one valid native tool-planning turn, then fallback; elapsed 27.14 seconds. Remaining failure cause was not captured, so it is not asserted.
- Evidence report remained root cause unconfirmed and all four read-only evidence tools completed.
- Independent no-install subprocess MCP client: 9 checks passed; see verification/mcp-client-result.json. External SDK/Inspector remains pending.
- All 33 regression tests passed again after the schema correction.
- No models/packages downloaded, no persistent settings changed and no paid service used.

## Advanced planner improvements
- Added compact structured tool-result summaries that exclude raw source instructions while retaining counts and evidence IDs. Full source evidence remains in the report.
- Added explicit completed/remaining tool context and strict current-incident schemas.
- Increased the bounded planner budget to 90 seconds, with at most 30 seconds per local request.
- Fallback notes now expose the exception category without leaking raw diagnostic text.
- Added four meaningful regression checks; all 37 tests passed.
- Live trial with existing llama3.2:1b: 21.17 seconds, no accepted native tool turns, ValueError fallback, four evidence tools completed and root cause remained unconfirmed.
- Separate live diagnostic: the model attempted to switch incident; validation rejected it. No incorrect incident tool call executed.
- Reliable AI planning remains pending for this small model. No validation was relaxed, and no model/package was downloaded.

## Structured planner live validation
- Added JSON-schema constrained tool selection; incident identity and arguments are bound by the controller. The model cannot supply another incident ID in this mode.
- Native mode remains available with its previous guards; no invalid native call was reinterpreted as valid.
- Added six safety checks for extra arguments, destructive/unavailable tools, malformed output, schema bounds and source-text exclusion. All 43 tests passed.
- Existing local llama3.2:1b, INC-1001: 40.55 seconds, four model-selected decisions, no fallback. Order: search_logs, get_incident_timeline, search_runbooks, get_sample_service_status.
- Root cause stayed unconfirmed and remediation stayed disabled. Evidence analysis remains deterministic.
- Only this one structured-mode live scenario is verified; broader reliability, cold starts and native-mode reliability are still pending.
- Browser mode remains deterministic; the structured local AI planner is available through the CLI. No downloads, installs, paid service or persistent settings changes.

## Remaining structured-mode scenarios
- INC-1002: four model-selected tools, no fallback, 22.22 seconds. High confidence refers to the immediate upstream failure mechanism; deployment causality and root cause remain unconfirmed.
- INC-1003: four model-selected tools, no fallback, 12.62 seconds. Missing evidence retained; Low confidence and root cause unconfirmed.
- INC-1004: four model-selected tools, no fallback, 14.59 seconds. Contradicting evidence retained; Medium confidence and root cause unconfirmed.
- Together with the earlier INC-1001 check, all four synthetic scenarios completed in structured mode with the existing local llama3.2:1b model.
- This is small-sample functional verification, not a reliability/latency benchmark. Cold starts, repeated runs, production data and external SDK interoperability remain pending.
- No package/model download, paid service or remediation action occurred.

## Browser AI integration
- Added explicit Local AI investigation button for the existing local llama3.2:1b model; default sample viewing never invokes a model.
- Added progress/fallback status, model decision trace and concurrency protection.
- Explicit-action header, incident allowlist and shared loopback/Origin checks protect AI requests; no arbitrary model/endpoint selection is exposed.
- Exports now preserve the displayed report, including planner decisions/notes, rather than recomputing a default report. Browser downloads were not triggered.
- Five new integration checks cover the action gate, invalid incident, model-free default view, report export trace and overlapping request rejection. All 48 tests passed.
- Live browser button run on INC-1001 completed with four model-selected tools and no fallback; audit and re-enabled controls verified in the browser.
- No model download, install, paid service or remediation operation occurred.


## Local history, ranked runbooks and controlled imports — 2026-10-11
- All 56 automated tests passed on the existing Python 3.12 runtime. New coverage includes immutable/idempotent snapshots, database reopen, sanitized persistence, source row/hash provenance, invalid/oversized logs, ranking synonyms and no matches, complete HTTP import-report-save-reopen flow, forged save rejection and cross-origin/action guards.
- JavaScript syntax validation passed with the existing Node runtime.
- Live browser: saved INC-1001; pasted two synthetic custom log rows; verified token masking, custom source label, Medium heuristic mechanism confidence and missing metrics; saved/reopened the custom report without inference; compared the two snapshots; queried “db pool exhaustion” and verified RB-POOL-1 ranked first with matched terms database/pool/saturation.
- The browser leaves one clearly labelled synthetic custom demo and two saved demo snapshots in the local workspace for inspection. No personal file was imported; file-picker interaction itself and downloaded exports were not exercised in this pass.
- Runbook ranking is lexical, not semantic embeddings. Import hashes cover canonical sanitized events, not original bytes. The database is local and unencrypted; masking is best effort.
- No real infrastructure, production reliability evaluation or live AI run on custom imported data was performed. Existing sample AI checks remain as recorded above. No install/download/cost/remediation action occurred.


## Live AI on the custom demo — 2026-10-11
- Used only the existing local llama3.2:1b model and the previously imported synthetic demo, CUSTOM-78808bb47017d50b76de.
- Structured planning completed in 44.03 seconds with four decisions and no fallback: search_logs, get_incident_timeline, search_runbooks, get_sample_service_status.
- Verified every factual citation resolves, all tool calls retain the custom incident ID and are read-only, known-secret masking remains intact, root cause remains Unconfirmed, and remediation is disabled.
- Saved this AI report locally and reopened it through the history endpoint; the full JSON snapshot matched exactly, including Markdown and planner decisions. This adds one AI demo snapshot to history.
- Machine-readable results: verification/custom-ai-result.json. This is one synthetic functional trial, not a production or repeatability benchmark. No packages/models installed, paid APIs used, or remediation executed.


## Three sequential custom-demo AI trials — 2026-10-11
- Existing llama3.2:1b in structured mode, same synthetic custom import. Durations: 9.64 s, 4.72 s, 4.95 s. All three completed four unique planner decisions without fallback.
- Compared facts, hypotheses, summary, timeline, evidence, source hashes, root-cause status and remediation policy against a freshly generated deterministic baseline; all matched in every run.
- Verified incident isolation in tool arguments, read-only calls, factual citation resolution and known-secret masking in each run. Root cause remained Unconfirmed and execution stayed disabled.
- Results: verification/custom-ai-repeatability.json. Sequential repeated-input trials may benefit from a loaded model and cached context; these timings are not cold-start or general production latency measurements. No new history snapshots were persisted during these trials.


## Varied synthetic logs and event-code fix — 2026-10-11
- Added tests/test_varied_logs.py: ten tests with multiple CPU/memory/disk/network and misleading-text subcases, timezone/order, Unicode, boundary and isolation checks.
- Before the fix, the new tests exposed six false-positive prose/substring subcases and a capitalization failure. Arbitrary substring detection treated `no pool_exhausted events observed` as evidence of saturation and missed uppercase codes.
- Fixed classification to use exact case-insensitive leading whitespace-delimited event codes, preserving original source messages. Documented the resulting strict-format limitation. This does not validate the truth of a source or solve arbitrary prose interpretation.
- Full suite: 66 tests passed in 7.018 seconds using the existing Python runtime. New tests use isolated temporary SQLite databases. The sandbox-only attempt could not access temporary SQLite files; the authorized host run completed successfully.
- No live AI invocation was needed for the deterministic analysis fix. Existing model checks are historical; varied-log AI reliability and production data remain unverified. No installations, downloads, paid services or remediation occurred.


## Three varied imported-log cases with live local AI — 2026-10-11
- cpu_unknown: 45.22 seconds, Low heuristic confidence, four unique model-selected read-only tools, no fallback.
- misleading_text: 10.95 seconds, Low heuristic confidence, four unique model-selected read-only tools, no fallback.
- uppercase_connection: 11.16 seconds, Medium heuristic confidence, four unique model-selected read-only tools, no fallback.
- All reports matched their deterministic baseline for facts, hypotheses, summary, timeline, source hashes, evidence, missing evidence, root-cause status and remediation policy. Citation validation and current-incident tool arguments passed in every case.
- CPU-only and misleading prose remained Low confidence; the uppercase connection error produced a Medium-confidence immediate mechanism. All root causes remained Unconfirmed. No remediation executed.
- Existing llama3.2:1b only; cases used an isolated temporary database, with no additions to the user workspace history. Results: verification/varied-ai-results.json.
- These are three synthetic functional checks. The model chooses tool order; it does not independently diagnose logs. Production reliability, larger datasets, and controlled cold-start benchmarks remain pending.

## Local prototype completion handoff - 2026-10-11
- Agreed local scope is implemented: triage/evidence reports, controlled imports, ranked runbooks, saved history/reopen/comparison, optional local AI planning, minimal MCP and disabled remediation execution.
- Windows Launch-IncidentLens.ps1 successfully started a fresh server on alternate loopback port 8766 using an existing interpreter; no install or policy change was needed.
- Fresh-server smoke check passed: five catalog entries produced valid reports with Markdown evidence, all three saved snapshots reopened, import/history controls were served, and ranked runbook lookup returned RB-POOL-1 first. See verification/final-smoke-result.json.
- Independent MCP client rechecked all nine protocol/tool safety checks successfully. Latest full regression result remains 66 passing tests; no application code changed after that run.
- README was consolidated into a current quick-start/demo guide and no longer claims imports/history are absent. Remaining limits are explicit: production readiness, external MCP certification, browser file-picker/download interaction and broad reliability are not certified.
- This completes the agreed local prototype, not a production deployment. Primary preview remains on port 8765; the temporary launch-check server was stopped.


## Final local prototype handover — 2026-10-11
- Windows Launch-IncidentLens.ps1 started the app successfully using an existing interpreter; no policy changes or installs.
- Final full suite: 69 tests passed in 7.864 seconds. Independent MCP client: 9 checks passed. JavaScript syntax check passed.
- Fresh browser tab verified the current UI. Selected samples/demo-import.log through the real file chooser, confirmed browser content, imported under the existing demo title, and verified two events and secret masking. Existing identical incident was reused.
- Clicked both browser Export buttons. Read resulting synthetic demo files in Downloads: JSON parsed, Markdown exactly matched report.markdown, factual evidence references resolved, placeholder token was absent, masking present, remediation disabled.
- Added START-HERE.md (Hinglish launch/demo/troubleshooting guide) and samples/demo-import.log (synthetic file-picker example). Final check record: verification/final-handover.json.
- Agreed local demonstration scope is complete. No deployment/publishing or production certification is implied. External MCP SDK/Inspector, production telemetry, broad diagnostic reliability and controlled cold-start benchmarking remain outside verified scope.
