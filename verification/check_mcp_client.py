"""Independent MCP protocol client; no server imports and no extra dependencies."""
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def main():
    # Complete ordered exchange; stderr stays separate from protocol stdout.
    requests = [
      {"id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"independent-client","version":"1"}}},
      {"method":"notifications/initialized"},
      {"id":2,"method":"ping"},
      {"id":3,"method":"tools/list"}]
    names = ["search_logs","get_incident_timeline","search_runbooks","get_sample_service_status"]
    for number,name in enumerate(names,4):
        requests.append({"id":number,"method":"tools/call","params":{"name":name,"arguments":{"incident_id":"INC-1001"}}})
    requests.extend([
      {"id":8,"method":"tools/call","params":{"name":"restart","arguments":{"incident_id":"INC-1001"}}},
      {"id":9,"method":"tools/call","params":{"name":"search_logs","arguments":{"incident_id":"../LICENSE"}}}])
    payload = "\n".join(json.dumps({"jsonrpc":"2.0",**r}) for r in requests)+"\n"
    result = subprocess.run([sys.executable,"-B",str(ROOT/"mcp_server.py")],cwd=ROOT,
           input=payload.encode("utf-8"),capture_output=True,timeout=10)
    assert result.returncode == 0, result.stderr.decode("utf-8")
    responses = [json.loads(line) for line in result.stdout.decode("utf-8").splitlines()]
    assert len(responses)==9 and [r["id"] for r in responses]==list(range(1,10))
    assert all(r["jsonrpc"]=="2.0" for r in responses)
    assert responses[0]["result"]["protocolVersion"]=="2025-06-18"
    assert responses[1]["result"]=={}
    tools=responses[2]["result"]["tools"]
    assert {t["name"] for t in tools}==set(names)
    assert all(t["annotations"]["readOnlyHint"] and not t["annotations"]["destructiveHint"] for t in tools)
    checks=["Protocol negotiation and matching response IDs","No response to initialized notification; ping works","Four read-only tools discovered"]
    for name,response in zip(names,responses[3:7]):
        tool_result=response["result"]
        assert tool_result["isError"] is False
        assert json.loads(tool_result["content"][0]["text"])==tool_result["structuredContent"]
        checks.append("Client called "+name+"; structured/text results agree")
    assert responses[7]["error"]["code"]==-32602
    assert responses[8]["result"]["isError"] is True
    checks += ["Destructive tool rejected","Path-like incident ID rejected"]
    summary={"status":"passed","protocol":"2025-06-18","checks":checks,
      "client":"Independent standard-library subprocess client",
      "limitation":"Not external SDK/MCP Inspector certification."}
    (Path(__file__).parent/"mcp-client-result.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()

