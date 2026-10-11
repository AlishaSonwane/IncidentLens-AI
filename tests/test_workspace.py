import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from incidentlens.workspace import Store, WorkspaceTools, parse_import
from incidentlens.engine import investigate, validate_report
from incidentlens.server import make_handler

LOG = "2026-10-11T10:00:00Z | checkout | ERROR | pool_exhausted token=private123 user@example.com | req-1"

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'db.sqlite3'
        self.store = Store(self.path)
    def tearDown(self): self.temp.cleanup()
    def test_reads_do_not_create_database(self):
        self.assertEqual(self.store.history(),[])
        self.assertEqual(self.store.imports(),[])
        self.assertFalse(self.path.exists())
    def test_sanitized_persistence_provenance_and_custom_analysis(self):
        i=self.store.add_import('Checkout', '\n'+LOG)
        reopened=Store(self.path)
        tools=WorkspaceTools(reopened)
        report=investigate(i['id'],tools)
        self.assertTrue(validate_report(report))
        self.assertIn('Imported sanitized logs',report['mode'])
        self.assertEqual(report['timeline'][0]['line'],2)
        self.assertEqual(report['likely_failure_mechanism']['confidence'],'Medium')
        self.assertIn(i['source'],report['source_hashes'])
        raw=self.path.read_bytes()
        self.assertNotIn(b'private123',raw)
        self.assertNotIn(b'user@example.com',raw)
        self.assertEqual(len(tools.catalog()),5)
    def test_jsonl_matches_pipe_format(self):
        row={'timestamp':'2026-10-11T10:00:00Z','service':'api','level':'error','message':'connection_refused'}
        incident=parse_import('JSON',json.dumps(row))
        self.assertEqual(incident['events'][0]['level'],'ERROR')
    def test_reject_invalid_and_oversized_input(self):
        for text in (LOG.replace('00Z','00'),LOG.replace('ERROR','PANIC'),LOG+' | extra',
                     LOG.replace('checkout','../../x'),LOG.replace('pool_exhausted','x'*4001),
                     '\n'.join([LOG]*201),'x'*512001,'',json.dumps({'timestamp':'x'})):
            with self.subTest(text=text[:30]):
                with self.assertRaises(ValueError): parse_import('test',text)
    def test_immutable_idempotent_report_snapshot(self):
        report=investigate('INC-1001')
        ident='a'*32
        self.store.save(ident,report)
        report['title']='tampered'
        self.store.save(ident,report)
        self.assertNotEqual(Store(self.path).report(ident)['title'],'tampered')
        self.assertEqual(len(self.store.history()),1)
        with self.assertRaises(ValueError): self.store.report("' OR 1=1")
    def test_ranking_synonyms_unknown_query_and_custom_service(self):
        i=self.store.add_import('checkout',LOG)
        tools=WorkspaceTools(self.store)
        ranked=tools.search_runbooks(i['id'],'db pool exhaustion')['sections']
        self.assertEqual(ranked[0]['id'],'RB-POOL-1')
        self.assertIn('database',ranked[0]['matched_terms'])
        self.assertEqual(tools.search_runbooks(i['id'],'zzzxxyy')['sections'],[])

class WorkspaceHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temp.name)/'db.sqlite3')
        self.tools=WorkspaceTools(self.store)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.tools,0,self.store))
        port=self.server.server_address[1]
        self.server.RequestHandlerClass=make_handler(self.tools,port,self.store)
        self.base=f'http://127.0.0.1:{port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,data=None,headers=None,method=None):
        h={'Content-Type':'application/json','X-IncidentLens-Action':'1'}
        if headers is not None:h=headers
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=h,method=method)
        try:
            with self.opener.open(req,timeout=5) as res:return res.status,json.load(res)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_import_investigate_save_reopen(self):
        status,item=self.request('/api/import',{'title':'Custom test','content':LOG})
        self.assertEqual(status,201)
        status,report=self.request('/api/report?incident_id='+item['incident_id'])
        self.assertEqual(status,200)
        ident=report['snapshot_id']
        self.assertEqual(self.request('/api/history/save',{'snapshot_id':ident})[0],200)
        self.assertEqual(self.request('/api/history/report?id='+ident)[1],report)
        self.assertEqual(len(self.request('/api/history')[1]),1)
    def test_untrusted_actions_and_forged_reports_rejected(self):
        data={'title':'test','content':LOG}
        for headers in ({'Content-Type':'application/json'},
                        {'Content-Type':'application/json','X-IncidentLens-Action':'1','Origin':'https://evil.example'},
                        {'Content-Type':'application/json','X-IncidentLens-Action':'1','Host':'evil.example'}):
            self.assertEqual(self.request('/api/import',data,headers)[0],403)
        self.assertEqual(self.request('/api/history/save',{'snapshot_id':'b'*32})[0],400)
        self.assertEqual(self.request('/api/history/save',{'snapshot_id':'b'*32,'report':{}})[0],400)
        self.assertEqual(self.request('/api/import',data,method='DELETE')[0],405)
        self.assertEqual(self.store.imports(),[])

if __name__=='__main__':unittest.main()
