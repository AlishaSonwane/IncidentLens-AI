"""Allowlisted, read-only sample tools. No shell, network, or remediation tools."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "samples"
MAX_BYTES = 2_000_000
MAX_EVENTS = 1000

# Source text is untrusted data. Redaction is defense in depth, not a guarantee.
def redact(text):
    text = str(text)
    text = re.sub(r"(?i)\b(authorization\s*:\s*bearer|bearer)\s+\S+", r"\1 [REDACTED]", text)
    text = re.sub(r"(?i)\b(password|passwd|token|api[_-]?key|secret)\s*[:=]\s*[^\s,;]+",
                  r"\1=[REDACTED]", text)
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL]", text, flags=re.I)
    return text[:4000]


def _load(filename):
    # The filename comes from our fixed catalog, never from a request.
    base = DATA.resolve()
    path = (DATA / filename).resolve()
    if path.parent != base or path.is_symlink():
        raise ValueError("Sample file must stay inside the sample directory.")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Sample file is too large.")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be text.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Timestamp must be ISO-8601 with timezone.") from exc
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone.")
    return dt


class SampleTools:
    def __init__(self):
        self._incidents, self.incident_sha256 = _load("incidents.json")
        self._runbooks, self.runbook_sha256 = _load("runbooks.json")
        self._validate()

    def _validate(self):
        if not isinstance(self._incidents, list) or len(self._incidents) > 100:
            raise ValueError("Invalid sample incident catalog.")
        ids = set()
        for incident in self._incidents:
            if incident["id"] in ids:
                raise ValueError("Duplicate incident ID.")
            ids.add(incident["id"])
            if len(incident["events"]) > MAX_EVENTS:
                raise ValueError("Too many events.")
            evidence_ids = set()
            for event in incident["events"] + incident.get("changes", []) + incident.get("snapshots", []):
                parse_time(event["timestamp"])
                if event["id"] in evidence_ids:
                    raise ValueError("Duplicate evidence ID within incident.")
                evidence_ids.add(event["id"])
        section_ids = [section["id"] for section in self._runbooks]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Duplicate runbook section ID.")

    def _get(self, incident_id):
        if not isinstance(incident_id, str) or len(incident_id) > 80:
            raise ValueError("Invalid incident ID.")
        for incident in self._incidents:
            if incident["id"] == incident_id:
                return incident
        raise ValueError("Unknown sample incident ID.")

    def catalog(self):
        return [{"id": i["id"], "title": i["title"], "description": i["description"],
                 "services": i["services"], "scenario": i["scenario"]} for i in self._incidents]

    def search_logs(self, incident_id, query="", service="", start="", end="", limit=100):
        incident = self._get(incident_id)
        if service and service not in incident["services"]:
            raise ValueError("Service is not in this sample incident.")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
            raise ValueError("limit must be an integer between 1 and 200.")
        for value in (query, service, start, end):
            if not isinstance(value, str) or len(value) > 300:
                raise ValueError("Invalid search parameter.")
        lower = parse_time(start) if start else None
        upper = parse_time(end) if end else None
        if lower and upper and lower > upper:
            raise ValueError("start must be before end.")
        matches = []
        for line, event in enumerate(incident["events"], 1):
            timestamp = parse_time(event["timestamp"])
            if service and event["service"] != service:
                continue
            if lower and timestamp < lower or upper and timestamp > upper:
                continue
            # Literal search: no regular expressions or interpreted instructions.
            if query.casefold() not in event["message"].casefold():
                continue
            result = dict(event)
            result["message"] = redact(event["message"])
            result["line"] = event.get("line", line)
            result["source"] = incident.get("source", "samples/incidents.json")
            matches.append(result)
        return {"events": matches[:limit], "matched": len(matches),
                "truncated": len(matches) > limit, "source_sha256": incident.get("source_sha256", self.incident_sha256), "source": incident.get("source", "samples/incidents.json")}

    def get_incident_timeline(self, incident_id):
        incident = self._get(incident_id)
        events = self.search_logs(incident_id, limit=200)["events"]
        for kind, key in (("change", "changes"), ("snapshot", "snapshots")):
            for event in incident.get(key, []):
                events.append({**event, "message": redact(event["message"]), "kind": kind,
                               "source": incident.get("source", "samples/incidents.json")})
        return {"events": sorted(events, key=lambda e: parse_time(e["timestamp"])),
                "source_sha256": incident.get("source_sha256", self.incident_sha256), "source": incident.get("source", "samples/incidents.json"),
                "truncated": len(incident["events"]) > 200}

    def search_runbooks(self, incident_id, query=""):
        incident = self._get(incident_id)
        if not isinstance(query, str) or len(query) > 300:
            raise ValueError("Invalid runbook query.")
        # Explainable lexical ranking with a small, explicit synonym dictionary.
        aliases = {"db":"database", "exhausted":"saturation", "exhaustion":"saturation",
                   "saturated":"saturation", "timeout":"timeouts", "refused":"unreachable"}
        def terms(text):
            return {aliases.get(w,w) for w in re.findall(r"[a-z0-9]+", text.lower())}
        wanted = terms(query) if query.strip() else terms(' '.join(e['message'] for e in incident['events']))
        results = []
        for section in self._runbooks:
            matched = wanted & terms(section['title'] + ' ' + section['text'])
            service_match = bool(set(section['services']) & set(incident['services']))
            if query.strip() and not matched: continue
            if not query.strip() and not matched and not service_match: continue
            score = len(matched) * 2 + (1 if service_match else 0)
            results.append({**section, 'text': redact(section['text']),
                            'source': 'samples/runbooks.json', 'score': score,
                            'matched_terms': sorted(matched), 'service_match': service_match})
        results.sort(key=lambda r: (-r['score'], r['id']))
        return {'sections': results, 'source_sha256': self.runbook_sha256,
                'ranking': 'Lexical overlap + curated synonyms + service boost; not semantic embeddings.'}

    def get_sample_service_status(self, incident_id):
        incident = self._get(incident_id)
        return {"snapshots": [{**s, "message": redact(s["message"]),
                              "source": incident.get("source", "samples/incidents.json")}
                             for s in incident.get("snapshots", [])],
                "changes": [{**c, "message": redact(c["message"]),
                             "source": incident.get("source", "samples/incidents.json")}
                            for c in incident.get("changes", [])],
                "dependencies": incident["dependencies"],
                "note": "Supplied records only; no live system access."}

    def call(self, name, arguments):
        if not isinstance(name, str) or name not in TOOL_SCHEMAS:
            raise ValueError("Tool is not on the read-only allowlist.")
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object.")
        schema = TOOL_SCHEMAS[name]["inputSchema"]
        if set(arguments) - set(schema["properties"]):
            raise ValueError("Unexpected tool argument.")
        if any(key not in arguments for key in schema["required"]):
            raise ValueError("Missing required tool argument.")
        return getattr(self, name)(**arguments)


def _schema(description, extra=None):
    properties = {"incident_id": {"type": "string", "description": "Allowlisted sample incident ID."}}
    properties.update(extra or {})
    return {"description": description, "inputSchema": {"type": "object",
            "properties": properties, "required": ["incident_id"], "additionalProperties": False}}

TOOL_SCHEMAS = {
    "search_logs": _schema("Read synthetic incident logs with literal filters; returns evidence IDs and line numbers.", {
        "query": {"type": "string", "maxLength": 300}, "service": {"type": "string"},
        "start": {"type": "string"}, "end": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 200}}),
    "get_incident_timeline": _schema("Read a timestamp-sorted synthetic log, change and status timeline."),
    "search_runbooks": _schema("Read relevant local runbook sections; no execution.", {
        "query": {"type": "string", "maxLength": 300}}),
    "get_sample_service_status": _schema("Read synthetic service status, changes and dependencies; not live health."),
}
