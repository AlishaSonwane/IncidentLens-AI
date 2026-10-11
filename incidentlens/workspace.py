"""Local sanitized imports and immutable investigation snapshots."""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .tools import SampleTools, parse_time, redact, ROOT

MAX_IMPORT_BYTES = 512_000

def parse_import(title, content):
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError("Title must contain 1–120 characters.")
    if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_IMPORT_BYTES:
        raise ValueError("Logs must be UTF-8 text, at most 512 KB.")
    events = []
    for line, raw in enumerate(content.splitlines(), 1):
        if not raw.strip(): continue
        if len(events) >= 200: raise ValueError("At most 200 events per import.")
        try:
            if raw.lstrip().startswith('{'):
                item = json.loads(raw)
            else:
                parts = [p.strip() for p in raw.split('|')]
                if len(parts) not in (4, 5): raise ValueError()
                item = dict(zip(('timestamp','service','level','message','correlation_id'), parts))
            required = {'timestamp','service','level','message'}
            if not isinstance(item, dict) or not required <= item.keys() or item.keys() - required - {'correlation_id'}:
                raise ValueError()
            if any(not isinstance(v, str) for v in item.values()): raise ValueError()
            parse_time(item['timestamp'])
            if len(item['timestamp']) > 50: raise ValueError()
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', item['service']): raise ValueError()
            item['level'] = item['level'].upper()
            if item['level'] not in ('DEBUG','INFO','WARN','WARNING','ERROR','CRITICAL'): raise ValueError()
            if not 1 <= len(item['message']) <= 4000: raise ValueError()
            cid = item.get('correlation_id','')
            if len(cid) > 128: raise ValueError()
            events.append({**item, 'message': redact(item['message']),
                           'correlation_id': redact(cid), 'line': line})
        except (ValueError, TypeError, KeyError):
            raise ValueError(f"Invalid event at line {line}. Check format, limits and timezone.") from None
    if not events: raise ValueError("Supply at least one log event.")
    clean = {'title': redact(title.strip()), 'events': events}
    digest = hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()
    ident = 'CUSTOM-' + digest[:20]
    for i, event in enumerate(events, 1): event['id'] = ident + '-E' + str(i)
    return {'id': ident, 'title': clean['title'], 'events': events,
            'description': 'Locally imported, sanitized logs; no live telemetry.',
            'scenario': 'Custom logs', 'services': sorted({e['service'] for e in events}),
            'dependencies': [], 'changes': [], 'snapshots': [],
            'source': 'local-imports/' + ident + '.sanitized.json',
            'source_sha256': hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest()}

class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else ROOT / '.local' / 'incidentlens.sqlite3'

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('CREATE TABLE IF NOT EXISTS imports (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, saved TEXT NOT NULL, body TEXT NOT NULL)')
        try:
            with db:
                yield db
        finally:
            db.close()

    def imports(self):
        if not self.path.exists(): return []
        with self._connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT body FROM imports ORDER BY rowid DESC')]

    def add_import(self, title, content):
        incident = parse_import(title, content)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM imports WHERE id=?', (incident['id'],)).fetchone():
                return incident
            if db.execute('SELECT count(*) FROM imports').fetchone()[0] >= 100:
                raise ValueError('Local import limit reached (100 incidents).')
            db.execute('INSERT OR IGNORE INTO imports VALUES (?, ?)', (incident['id'], json.dumps(incident)))
        return incident

    def save(self, ident, report):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM reports WHERE id=?', (ident,)).fetchone():
                return ident
            if db.execute('SELECT count(*) FROM reports').fetchone()[0] >= 500:
                raise ValueError('Saved report limit reached (500).')
            db.execute('INSERT OR IGNORE INTO reports VALUES (?, ?, ?)',
                       (ident, datetime.now(timezone.utc).isoformat(), json.dumps(report)))
        return ident

    def history(self):
        if not self.path.exists(): return []
        with self._connect() as db:
            rows = db.execute('SELECT id, saved, body FROM reports ORDER BY saved DESC').fetchall()
        return [{'id': ident, 'saved_at': saved, 'incident_id': (r:=json.loads(body))['incident_id'],
                 'title': r['title'], 'planner': r['planner_strategy']} for ident,saved,body in rows]

    def report(self, ident):
        if not isinstance(ident,str) or not re.fullmatch(r'[a-f0-9]{32}', ident): raise ValueError('Invalid snapshot ID.')
        if not self.path.exists(): raise ValueError('Snapshot not found.')
        with self._connect() as db:
            row = db.execute('SELECT body FROM reports WHERE id=?', (ident,)).fetchone()
        if not row: raise ValueError('Snapshot not found.')
        return json.loads(row[0])

class WorkspaceTools(SampleTools):
    def __init__(self, store):
        super().__init__()
        self.store = store
    def _get(self, incident_id):
        if isinstance(incident_id,str) and incident_id.startswith('CUSTOM-'):
            for incident in self.store.imports():
                if incident['id'] == incident_id: return incident
        return super()._get(incident_id)
    def catalog(self):
        return super().catalog() + [{k:i[k] for k in ('id','title','description','services','scenario')}
                                   for i in self.store.imports()]
