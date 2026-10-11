"""Minimal MCP stdio server: JSON-RPC lifecycle and four read-only tools."""
import json
import sys

from . import __version__
from .tools import SampleTools, TOOL_SCHEMAS

VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_MESSAGE = 64_000


def error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class MCPServer:
    def __init__(self, tools=None):
        self.tools = tools or SampleTools()
        self.initialized = False
        self.ready = False

    def handle(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return error(None, -32600, "Invalid JSON-RPC request.")
        request_id = request.get("id")
        if "id" in request and (not isinstance(request_id, (str, int)) or isinstance(request_id, bool)):
            return error(None, -32600, "Invalid request ID.")
        method = request["method"]
        params = request.get("params", {})
        if not isinstance(params, dict):
            return error(request_id, -32602, "Parameters must be an object.") if "id" in request else None
        if "id" not in request:
            if method == "notifications/initialized" and self.initialized:
                self.ready = True
            # MCP notifications do not receive responses.
            return None
        if method == "initialize":
            if self.initialized:
                return error(request_id, -32600, "Already initialized.")
            if not isinstance(params.get("protocolVersion"), str):
                return error(request_id, -32602, "protocolVersion is required.")
            self.initialized = True
            version = params["protocolVersion"]
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": version if version in VERSIONS else VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "incidentlens-ai", "version": __version__},
                "instructions": "Synthetic sample evidence only. All four tools are read-only. No remediation."}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if not self.ready:
            return error(request_id, -32002, "Initialize and send notifications/initialized first.")
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "tools": [{"name": name, **schema, "annotations": {
                        "readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}}
                        for name, schema in TOOL_SCHEMAS.items()]}}
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or name not in TOOL_SCHEMAS:
                return error(request_id, -32602, "Unknown read-only tool.")
            try:
                result = self.tools.call(name, params.get("arguments", {}))
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                        "structuredContent": result, "isError": False}}
            except (ValueError, TypeError, KeyError):
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                        "content": [{"type": "text", "text": "Invalid or unsupported sample tool arguments."}],
                        "isError": True}}
        return error(request_id, -32601, "Method not found.")


def main():
    server = MCPServer()
    incoming = sys.stdin.buffer
    outgoing = sys.stdout.buffer
    while True:
        raw = incoming.readline(MAX_MESSAGE + 1)
        if not raw:
            break
        if len(raw) > MAX_MESSAGE:
            # Drain the remainder of this oversized message, keeping the next frame intact.
            while raw and not raw.endswith(b"\n"):
                raw = incoming.readline(MAX_MESSAGE + 1)
            response = error(None, -32600, "Message too large.")
        else:
            try:
                response = server.handle(json.loads(raw.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                response = error(None, -32700, "Invalid JSON.")
            except Exception:
                response = error(None, -32603, "Internal sample tool error.")
        if response is not None:
            outgoing.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
            outgoing.flush()


if __name__ == "__main__":
    main()
