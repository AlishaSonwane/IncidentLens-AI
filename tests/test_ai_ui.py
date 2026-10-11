import json
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from incidentlens.server import make_handler
from incidentlens.tools import SampleTools
from incidentlens.engine import investigate

class AIUITests(unittest.TestCase):
    def setUp(self):
        self.server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(SampleTools(),0))
        port=self.server.server_address[1]
        self.server.RequestHandlerClass=make_handler(SampleTools(),port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{port}"
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)
    def get(self,path,headers=None):
        return self.opener.open(urllib.request.Request(self.base+path,headers=headers or {}),timeout=5)
    def test_ai_requires_explicit_action_header(self):
        with patch("incidentlens.server.OllamaPlanner") as planner:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.get("/api/ai-report?incident_id=INC-1001")
            self.assertEqual(error.exception.code,403)
            planner.assert_not_called()
    def test_invalid_incident_never_calls_model(self):
        with patch("incidentlens.server.OllamaPlanner") as planner:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.get("/api/ai-report?incident_id=../LICENSE",{"X-IncidentLens-AI":"1"})
            self.assertEqual(error.exception.code,400)
            planner.assert_not_called()
    def test_ai_report_export_preserves_model_trace(self):
        report=investigate("INC-1001")
        report["planner_strategy"]="structured"
        report["planner_decisions"]=["search_logs"]
        with patch("incidentlens.server.OllamaPlanner"),patch("incidentlens.server.investigate",return_value=report):
            with self.get("/api/ai-report?incident_id=INC-1001",{"X-IncidentLens-AI":"1"}) as response:
                data=json.load(response)
            self.assertIn("Planner: structured",data["markdown"])
            self.assertIn("Model-selected tools: search_logs",data["markdown"])
            self.assertFalse(data["remediation"]["execution_enabled"])
    def test_default_view_never_constructs_model(self):
        with patch("incidentlens.server.OllamaPlanner") as planner:
            with self.get("/api/report?incident_id=INC-1001") as response:
                self.assertEqual(json.load(response)["planner_strategy"],"deterministic")
            planner.assert_not_called()


    def test_concurrent_ai_run_is_rejected(self):
        entered=threading.Event()
        release=threading.Event()
        report=investigate("INC-1001")
        statuses=[]
        def fake_investigate(*args,**kwargs):
            entered.set()
            release.wait(3)
            return report
        def first_request():
            with self.get("/api/ai-report?incident_id=INC-1001",
                         {"X-IncidentLens-AI":"1"}) as response:
                statuses.append(response.status)
        with patch("incidentlens.server.OllamaPlanner"),patch(
                "incidentlens.server.investigate",side_effect=fake_investigate):
            worker=threading.Thread(target=first_request)
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(urllib.error.HTTPError) as error:
                    self.get("/api/ai-report?incident_id=INC-1001",
                             {"X-IncidentLens-AI":"1"})
                self.assertEqual(error.exception.code,429)
            finally:
                release.set()
                worker.join(4)
            self.assertEqual(statuses,[200])

if __name__=="__main__":
    unittest.main()
