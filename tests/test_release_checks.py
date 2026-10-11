import json
import tempfile
import unittest
from pathlib import Path
from incidentlens.workspace import Store
from incidentlens.engine import investigate, to_markdown

class ReleaseChecks(unittest.TestCase):
    def test_existing_import_stays_idempotent_at_capacity(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'db.sqlite3')
            content='2026-10-11T10:00:00Z | api | ERROR | request_failed'
            incident=store.add_import('one',content)
            with store._connect() as db:
                db.executemany('INSERT INTO imports VALUES (?, ?)',[(str(i),'{}') for i in range(99)])
            self.assertEqual(store.add_import('one',content),incident)
            with self.assertRaises(ValueError):store.add_import('two',content)
    def test_saved_report_stays_immutable_at_capacity(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'db.sqlite3')
            report=investigate('INC-1001');ident='a'*32
            store.save(ident,report)
            with store._connect() as db:
                db.executemany('INSERT INTO reports VALUES (?, ?, ?)',[(str(i),'now','{}') for i in range(499)])
            store.save(ident,{'title':'replacement'})
            self.assertEqual(store.report(ident),report)
            with self.assertRaises(ValueError):store.save('b'*32,report)
    def test_unavailable_model_preserves_analysis_and_exported_fallback(self):
        class Unavailable:
            strategy='structured'
            decisions=[]
            def choose(self,*args):raise ConnectionError('simulated local model unavailable')
        baseline=investigate('INC-1004')
        report=investigate('INC-1004',planner=Unavailable())
        self.assertTrue(report['planner_notes'])
        for key in ('facts','hypotheses','evidence','source_hashes','root_cause_status','remediation'):
            self.assertEqual(report[key],baseline[key])
        self.assertEqual(len(report['audit']),4)
        exported=to_markdown(report)
        self.assertIn('ConnectionError',exported)
        self.assertIn('fallback',exported)
        self.assertNotIn('simulated local model unavailable',exported)

if __name__=='__main__':unittest.main()
