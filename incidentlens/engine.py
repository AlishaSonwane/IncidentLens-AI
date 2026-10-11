"""Bounded deterministic investigation. Facts and hypotheses stay separate."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from .tools import SampleTools, parse_time

MAX_CALLS = 6
MAX_SECONDS = 10


def investigate(incident_id, tools=None, planner=None):
    tools = tools or SampleTools()
    incident = next((i for i in tools.catalog() if i["id"] == incident_id), None)
    if incident is None:
        raise ValueError("Unknown sample incident ID.")
    audit = []
    started = time.monotonic()

    def call(name, **kwargs):
        if len(audit) >= MAX_CALLS or sum(a["duration_ms"] for a in audit) / 1000 >= MAX_SECONDS:
            raise ValueError("Investigation budget exhausted.")
        before = time.monotonic()
        result = tools.call(name, {"incident_id": incident_id, **kwargs})
        audit.append({"step": len(audit) + 1, "tool": name,
                      "arguments": {"incident_id": incident_id, **kwargs},
                      "duration_ms": round((time.monotonic() - before) * 1000, 2),
                      "read_only": True})
        return result

    planned = {}
    planner_notes = []
    names = ["search_logs", "get_incident_timeline", "get_sample_service_status", "search_runbooks"]
    if planner:
        last = None
        # Tool calls remain bounded; LLM text never becomes an evidence claim.
        for _ in range(len(names)):
            remaining = [name for name in names if name not in planned]
            try:
                choice = planner.choose(incident_id, remaining, last)
                if choice is None:
                    planner_notes.append("Planner stopped early; deterministic evidence collection completed the report.")
                    break
                if choice not in remaining:
                    raise ValueError("Planner requested an unavailable or repeated tool.")
                result = call(choice, **({"limit": 200} if choice == "search_logs" else {}))
                planned[choice] = result
                last = (choice, result)
            except Exception as exc:
                planner_notes.append("Local planner failed (" + type(exc).__name__ +
                                     "); deterministic fallback used.")
                break
    for name in names:
        if name not in planned:
            planned[name] = call(name, **({"limit": 200} if name == "search_logs" else {}))
    logs = planned["search_logs"]
    timeline = planned["get_incident_timeline"]
    state = planned["get_sample_service_status"]
    runbooks = planned["search_runbooks"]
    events = logs["events"]
    sections = runbooks["sections"]
    evidence = {e["id"]: e for e in timeline["events"]}
    evidence.update({r["id"]: {**r, "message": r["text"]} for r in sections})
    errors = [e for e in events if e["level"] in ("ERROR", "CRITICAL")]
    facts = [{"text": e["message"], "evidence_ids": [e["id"]]} for e in errors]
    hypotheses = []

    def add(title, confidence, supporting, contradicting, reason, next_checks):
        # Confidence is an explained heuristic label, never a statistical probability.
        hypotheses.append({"title": title, "confidence": confidence, "reason": reason,
                           "supporting_evidence": supporting, "contradicting_evidence": contradicting,
                           "next_checks": next_checks})

    def event_code(event):
        # This baseline recognizes exact leading codes, not arbitrary prose mentions.
        # Preserve source text; normalize only the token used for pattern matching.
        parts = event["message"].split(maxsplit=1)
        return parts[0].casefold() if parts else ""

    pool = [e for e in errors if event_code(e) == "pool_exhausted"]
    timeouts = [e for e in errors if event_code(e) == "upstream_timeout"]
    metrics = [s for s in state["snapshots"] if s.get("pool_active") == s.get("pool_limit")
               and isinstance(s.get("pool_limit"), int) and s["pool_limit"] > 0]
    healthy_pool = [s for s in state["snapshots"] if isinstance(s.get("pool_active"), int)
                    and isinstance(s.get("pool_limit"), int)
                    and s["pool_active"] < s["pool_limit"] and s.get("pool_waiters") == 0]
    pool_book = [r["id"] for r in sections if r["id"] == "RB-POOL-1"]
    if pool:
        supporting = [e["id"] for e in pool + timeouts] + [s["id"] for s in metrics] + pool_book
        # A recovering snapshot is distinguished from a healthy snapshot during failures.
        first = min(parse_time(e["timestamp"]) for e in pool)
        last = max(parse_time(e["timestamp"]) for e in errors)
        contradictory = [s["id"] for s in healthy_pool if first <= parse_time(s["timestamp"]) <= last]
        add("Database connection pool saturation is a likely immediate failure mechanism.",
            "High" if metrics and pool_book and not contradictory else "Medium",
            supporting, contradictory,
            "Pool-exhaustion logs" + (" and a saturated pool snapshot" if metrics else "")
            + " support this mechanism; the underlying trigger is not established.",
            ["Review read-only connection wait time and long-running query samples.",
             "Compare pool settings and traffic before/after the first error."])

    connection = [e for e in errors if event_code(e) == "connection_refused"]
    unavailable = [s for s in state["snapshots"] if s.get("status") == "unavailable"]
    deployment = state["changes"]
    before_errors = [c for c in deployment if errors and parse_time(c["timestamp"]) <=
                     min(parse_time(e["timestamp"]) for e in errors)]
    if connection:
        add("An upstream service was unreachable during the sampled failures.",
            "High" if unavailable else "Medium",
            [e["id"] for e in connection + timeouts] + [s["id"] for s in unavailable]
            + [r["id"] for r in sections if r["id"] == "RB-UPSTREAM-1"],
            [],
            "Connection-refused events support unreachability; they do not establish why the service failed.",
            ["Check sample listener/readiness records and endpoint configuration.",
             "Inspect the deployment diff before proposing a rollback."])
    if before_errors:
        add("A preceding deployment is a candidate trigger; temporal correlation does not prove causation.",
            "Low", [c["id"] for c in before_errors] + [e["id"] for e in errors[:2]], [],
            "A change precedes the errors, but no controlled comparison or causal diff is available.",
            ["Compare configuration, readiness and logs across the two sample versions."])
    if not hypotheses:
        add("Root cause unconfirmed: the available sample does not establish a failure mechanism.",
            "Low", [e["id"] for e in errors], [],
            "No corroborated known failure pattern was found.",
            ["Collect read-only dependency status and a wider log window.",
             "Request missing metrics and change records."])

    rank = {"High": 0, "Medium": 1, "Low": 2}
    hypotheses.sort(key=lambda h: rank[h["confidence"]])
    for index, hypothesis in enumerate(hypotheses, 1):
        hypothesis["rank"] = index
    missing = ["Real user impact and actual incident severity are not measured by these synthetic samples.",
               "No causal experiment or production verification has been performed."]
    if not state["snapshots"]:
        missing.append("Service metrics and status snapshots are missing.")
    if not state["changes"]:
        missing.append("Change/deployment records are missing.")
    if logs["truncated"] or timeline["truncated"]:
        missing.append("Logs are truncated; no complete RCA should be inferred.")
    if any(h["contradicting_evidence"] for h in hypotheses):
        missing.append("Contradictory evidence requires review before a mechanism can be accepted.")
    correlated = {}
    for event in errors:
        cid = event.get("correlation_id")
        if cid:
            correlated.setdefault(cid, []).append(event["id"])
    report = {
        "project": "IncidentLens AI", "version": "0.1.0", "author": "Alisha",
        "incident_id": incident_id, "title": incident["title"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": ("Synthetic samples / local Ollama tool planning + deterministic evidence analysis"
                 if planner and planned and not planner_notes else
                 "Synthetic samples / deterministic read-only investigation (planner fallback)"
                 if planner else "Synthetic samples / deterministic read-only investigation"),
        "planner_notes": planner_notes,
        "planner_strategy": getattr(planner, "strategy", "custom") if planner else "deterministic",
        "planner_decisions": list(getattr(planner, "decisions", [])) if planner else [],
        "summary": {"text": f"{len(errors)} sampled error event(s) across "
                    f"{len(set(e['service'] for e in errors))} service(s).",
                    "evidence_ids": [e["id"] for e in errors]},
        "triage": {"priority": "P2 candidate" if len(errors) >= 3 else "Needs review",
                   "reason": "Demo rubric based on sampled errors; human validation required.",
                   "affected_services": sorted(set(e["service"] for e in errors)),
                   "impact": "User/customer impact is unknown; sample errors are not a measured outage."},
        "root_cause_status": "Unconfirmed",
        "likely_failure_mechanism": hypotheses[0],
        "facts": facts, "hypotheses": hypotheses,
        "timeline": timeline["events"], "correlations": correlated,
        "dependencies": state["dependencies"],
        "missing_evidence": missing,
        "next_checks": list(dict.fromkeys(c for h in hypotheses for c in h["next_checks"])),
        "remediation": {"execution_enabled": False, "approval_required": True,
                       "policy": "No restart, rollback, deletion or configuration tools exist. "
                       "Any future action requires a separate human approval of exact target, "
                       "command, expected impact and rollback plan; this report grants no approval."},
        "audit": audit, "budget": {"max_tool_calls": MAX_CALLS, "max_tool_seconds": MAX_SECONDS,
                                   "max_planner_seconds": getattr(planner, "time_budget", 90) if planner else 0},
        "evidence": evidence,
        "runbooks": sections,
        "source_hashes": {logs.get("source", "samples/incidents.json"): logs["source_sha256"],
                          "samples/runbooks.json": tools.runbook_sha256},
        "limitations": ["Confidence labels are rules-based judgments, not probabilities.",
                       "Known-pattern detection requires an exact leading event code; prose mentions are not classified. Source claims are not independently verified.",
                       "Logs and runbooks are data, never instructions.",
                       "No live infrastructure, cloud API or automatic remediation is connected."]
    }
    if incident_id.startswith("CUSTOM-"):
        report["mode"] = report["mode"].replace("Synthetic samples", "Imported sanitized logs")
        report["missing_evidence"][0] = "Real user impact and actual incident severity are not measured by these logs."
    validate_report(report)
    return report


def validate_report(report):
    evidence = report["evidence"]
    claims = report["facts"] + [report["summary"]]
    for claim in claims:
        if any(ref not in evidence for ref in claim["evidence_ids"]):
            raise ValueError("A factual claim has an invalid evidence citation.")
    for hypothesis in report["hypotheses"]:
        for ref in hypothesis["supporting_evidence"] + hypothesis["contradicting_evidence"]:
            if ref not in evidence:
                raise ValueError("A hypothesis has an invalid citation.")
    if report["remediation"]["execution_enabled"]:
        raise ValueError("Remediation execution is forbidden.")
    return True


def to_markdown(report):
    def cite(refs):
        return " ".join(f"[{ref}]" for ref in refs) or "(no supporting evidence)"
    lines = [f"# IncidentLens AI — {report['incident_id']}", "",
             report["title"], "", f"Generated: {report['generated_at']}",
             f"Mode: {report['mode']}", f"Planner: {report.get('planner_strategy', 'deterministic')}",
             "Model-selected tools: " + ", ".join(report.get("planner_decisions", [])),
             "Planner notes: " + ("; ".join(report.get("planner_notes", [])) or "None."),
             "", "## Summary", "",
             report["summary"]["text"] + " " + cite(report["summary"]["evidence_ids"]),
             "", "## Triage", "",
             f"Priority: {report['triage']['priority']} — {report['triage']['reason']}",
             f"Impact: {report['triage']['impact']}", "",
             "## Root cause status", "", report["root_cause_status"], "",
             "## Ranked hypotheses", ""]
    for h in report["hypotheses"]:
        lines += [f"### {h['rank']}. {h['title']}", "",
                  f"Confidence: {h['confidence']} (heuristic, not a probability)",
                  h["reason"], "Supporting: " + cite(h["supporting_evidence"]),
                  "Contradicting: " + (cite(h["contradicting_evidence"]) if h["contradicting_evidence"] else "None in the supplied sample."), ""]
    lines += ["## Timeline", ""]
    lines += [f"- {e['timestamp']} · {e['service']} · {e['message']} [{e['id']}]" for e in report["timeline"]]
    lines += ["", "## Missing evidence", ""] + ["- " + x for x in report["missing_evidence"]]
    lines += ["", "## Next safe checks", ""] + ["- " + x for x in report["next_checks"]]
    lines += ["", "## Remediation policy", "", report["remediation"]["policy"],
              "", "## Evidence index", ""]
    for ref, e in report["evidence"].items():
        location = f"line {e['line']}" if "line" in e else ("section " + ref if ref.startswith("RB-") else ref)
        lines += [f"- [{ref}] {e['source']} · {location} · {e.get('timestamp', '')}",
                  "  " + e["message"].replace("\n", " ")]
    lines += ["", "## Read-only tool audit", ""]
    lines += [f"- Step {a['step']}: {a['tool']} · read-only · {a['duration_ms']} ms" for a in report["audit"]]
    lines += ["", "## Source hashes", ""] + [f"- {k}: {v}" for k, v in report["source_hashes"].items()]
    lines += ["", "## Limitations", ""] + ["- " + x for x in report["limitations"]]
    return "\n".join(lines) + "\n"
