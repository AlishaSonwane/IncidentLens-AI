"""Windows-compatible CLI; reports go to stdout, not automatic disk writes."""
import argparse
import json
import sys

from .engine import investigate, to_markdown
from .tools import SampleTools


def main():
    parser = argparse.ArgumentParser(description="IncidentLens AI — local sample incident triage")
    parser.add_argument("incident_id", nargs="?", help="Sample ID such as INC-1001")
    parser.add_argument("--list", action="store_true", help="List synthetic sample incidents")
    parser.add_argument("--json", action="store_true", help="Print the evidence report as JSON")
    parser.add_argument("--ollama-model", help="Opt in to an already-installed LOCAL tool-calling model. No pulls.")
    parser.add_argument("--planner-mode", choices=("structured", "native"), default="structured",
                        help="Structured mode binds incident identity in the controller (default).")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tools = SampleTools()
    if args.list or not args.incident_id:
        for incident in tools.catalog():
            print(incident["id"] + " — " + incident["title"])
        return
    try:
        planner = None
        if args.ollama_model:
            from .ollama import OllamaPlanner
            planner = OllamaPlanner(args.ollama_model, strategy=args.planner_mode)
        report = investigate(args.incident_id, tools, planner)
        print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else to_markdown(report))
        for note in report["planner_notes"]:
            print(note, file=sys.stderr)
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
