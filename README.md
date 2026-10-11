# IncidentLens AI

Incident triage and root cause investigation · Original implementation by Alisha · MIT · v0.1.0

**The agreed local prototype is implemented.** It supports sample incidents, controlled custom-log imports, evidence-linked reports, local saved history/comparison, ranked runbooks and optional local AI tool selection. It is suitable for local demonstrations and development; production deployment is outside this release.

For a simple Hinglish walkthrough, open **START-HERE.md**. Final check record: `verification/final-handover.json`.

## Start on this Windows computer

Open PowerShell in `C:\GenAI-Projects\AI-Incident-RCA-Agent` and run:

```powershell
.\Launch-IncidentLens.ps1
```

Open http://127.0.0.1:8765/. Stop the server with Ctrl+C. Use `-Port 8766` if the default port is occupied. The launcher uses an existing Python interpreter, including the already available bundled runtime; it installs nothing and does not change PowerShell policy. If Windows blocks the script, run an existing Python executable with `-m incidentlens.server` from this folder instead.

Python 3.10+ is declared; verification used the existing Python 3.12 runtime. There are no third-party Python package dependencies. Default reports need no model or internet access. The optional browser AI button requires the existing Ollama service at 127.0.0.1:11434 and an already installed `llama3.2:1b` model. The app never pulls models.

## Five-minute walkthrough

1. Select INC-1001. Review observed facts, the likely failure mechanism and missing evidence. Click an evidence ID to inspect its source.
2. Select INC-1003 or INC-1004 to see uncertainty or contradictory evidence. A hypothesis is not a confirmed underlying root cause.
3. Click **Local AI investigation** if the existing Ollama service is available. Check **Tool audit** for model decisions and actual read-only tool calls. The model chooses tool order; evidence analysis remains rules-based.
4. Click **Save investigation**. Open **Saved investigations**, reopen a snapshot without inference, or select exactly two snapshots and compare them.
5. Search runbooks with `db pool exhaustion`. Scores explain word matches, synonym normalization and service context; they are not diagnostic confidence scores.
6. Open **Import custom logs**, enter a title and paste this synthetic example, then click **Validate & import locally**:

```text
2026-10-11T10:00:00Z | checkout | ERROR | pool_exhausted wait_ms=5000 | demo-1
2026-10-11T10:00:02Z | checkout | ERROR | upstream_timeout | demo-1
```

7. Review the imported report, then save it or use **Export JSON / Export Markdown** for the displayed snapshot.

The workspace contains one clearly labelled synthetic custom demo and saved deterministic/AI demo reports from verification. Imported logs and saved reports persist across restarts; unsaved reports may need regenerating after a restart or after 64 newer reports.

## Implemented capabilities

- Four synthetic scenarios: pool saturation, deployment correlation, insufficient evidence and conflicting telemetry.
- Literal log filtering, chronological timeline, request correlation and sample dependency mapping.
- Facts and hypotheses with evidence IDs, counter-evidence, missing evidence, source hashes and a bounded tool audit.
- Custom imports, immutable saved snapshots, reopening and comparison in the browser.
- Local runbook ranking using word overlap, curated synonyms and service relevance. No embeddings/vector search.
- Optional structured Ollama planner; strict allowlist and incident identity binding, bounded requests and deterministic fallback.
- Four actual MCP stdio tools using JSON-RPC: search_logs, get_incident_timeline, search_runbooks and get_sample_service_status.
- Loopback-only browser UI and JSON/Markdown reports. No remediation executor.

## Custom input contract

Use UTF-8 JSONL (one object per line) or `timestamp | service | level | message | correlation_id`; correlation_id is optional. JSON keys are timestamp, service, level, message and optional correlation_id. Unknown keys and invalid rows are rejected. Use JSONL for messages containing pipe characters.

Timestamps must include an ISO-8601 timezone. Service names contain letters, digits, underscores, dots or hyphens (maximum 80 characters). Levels: DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL. Limits: 512 KB of log text, 200 events, 4000 characters/message, 128 characters/correlation ID, 120 characters/title, 100 imported incidents and 500 saved reports.

Known failure detection recognizes `pool_exhausted`, `connection_refused` and `upstream_timeout` as exact first whitespace-delimited tokens in ERROR/CRITICAL messages, case-insensitively. Prose mentions, quoted tokens and negative statements such as `no pool_exhausted events observed` are not classified as positive event codes. Other formats remain uncertain. Even an apparently valid event code is an unverified source claim, not independent proof.

Custom imports contain logs only. They do not invent health snapshots, deployment records or service dependency maps. CPU, memory, disk, DNS and TLS signals have been tested for safe uncertainty, not implemented as full diagnostic detectors.

## Storage and evidence

The local SQLite database is `.local/incidentlens.sqlite3` inside this project and is ignored by Git. It is unencrypted and protected by the Windows account/filesystem. Known bearer tokens, key/value secrets and emails are masked before import persistence. Masking is best effort; review logs before import. Raw uploads are not persisted. Browser text fields are cleared after a successful import.

Sample source hashes identify sample-file bytes. Custom-import hashes identify canonical sanitized events (`json.dumps(events, sort_keys=True)` encoded as UTF-8), not original file bytes. Sample event line numbers are record positions within an incident; imported line numbers preserve source text row positions.

Saving uses a server-generated report token, not an arbitrary report supplied by a client. Existing saved snapshots are immutable. Comparing different incidents does not establish progression or recovery. Runbook search does not change the evidence in an already generated report.

## Safety and limits

- Evidence tools are read-only. Explicit import/save actions write only to the local workspace.
- Restart, rollback, deletion and configuration execution tools do not exist. Any future such action requires separate human approval of its exact target, action, impact and rollback plan.
- Host/Origin checks and explicit-action headers protect local actions. The server listens on 127.0.0.1 only. This is a single-user local app, not a multi-user authenticated service.
- Source text is treated as data and rendered with textContent. The planner receives compact tool summaries, not raw log instructions.
- High/Medium/Low confidence is heuristic, not a probability. Severity is a demo candidate, not measured customer impact. Root cause remains Unconfirmed without independent causal evidence.
- No live infrastructure, paid API, cloud integration, semantic retrieval, FastAPI or Streamlit is part of this release.

## CLI and MCP

From the project folder, using an existing interpreter:

```powershell
python -m incidentlens.cli --list
python -m incidentlens.cli INC-1001 --json
python -m incidentlens.cli INC-1001 --ollama-model llama3.2:1b --planner-mode structured
python -m incidentlens.mcp
python -m unittest discover -s tests -v
python verification/check_mcp_client.py
```

CLI/MCP use the synthetic sample catalog; browser imports/history use the local workspace. MCP uses newline-delimited JSON-RPC over stdio with initialize, initialized notification, ping, tools/list and tools/call. Supported protocol versions: 2025-06-18, 2025-03-26 and 2024-11-05. No resources/prompts/HTTP transport are advertised. For a client without a working-directory setting, run `mcp_server.py` by absolute path with an existing Python executable.

The optional planner contacts only 127.0.0.1:11434, ignores proxies, rejects redirects and remote/cloud model metadata, never installs models, and has a 90-second overall / 30-second per-request budget. Native tool calling remains available but was unreliable with the existing small model. Structured mode binds arguments in the controller and constrains model output to remaining tool names.

## Verification and completion scope

- 69 regression tests passed in final handover validation.
- Independent MCP subprocess client: nine checks, including rejection of a destructive tool and path-like incident ID.
- Browser sample/custom investigation, secret masking, ranked search, save/reopen/compare and optional sample AI were exercised.
- All four synthetic sample scenarios, the custom demo, three repeat custom trials and three varied imported-log cases completed recorded structured AI checks without fallback. Findings stayed consistent with deterministic analysis.
- Browser file-picker import and local JSON/Markdown exports were exercised in final handover. Exported Markdown exactly matched the JSON snapshot, with redaction and evidence citations retained. External MCP SDK/Inspector interoperability, production data, controlled cold-start timing and broad reliability remain unverified.

See VERIFICATION.md for chronological findings and verification/*.json for recorded results. A completed local prototype does not imply production certification.

## Originality and ownership

Implementation and synthetic fixtures were written independently. No source code from the reviewed public repository was copied/adapted. This original implementation uses **Copyright (c) 2026 Alisha**, under MIT in LICENSE. Runtime software, models and any future dependencies retain their own licenses.

Main files: incidentlens/engine.py (analysis), tools.py (read-only evidence), workspace.py (imports/history), ollama.py (planner), mcp.py (protocol), server.py (local UI), cli.py, static/, samples/, tests/, verification/, Launch-IncidentLens.ps1.
