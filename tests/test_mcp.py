import json
import subprocess
import sys
from pathlib import Path

from apodix.mcp import LATEST, handle

ROOT = Path(__file__).resolve().parents[1]


def test_initialize_answers_with_a_version_the_client_asked_for():
    reply = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
    assert reply["result"]["protocolVersion"] == "2024-11-05"
    assert reply["result"]["serverInfo"]["name"] == "apodix"
    assert "tools" in reply["result"]["capabilities"]


def test_initialize_falls_back_to_the_latest_version_it_knows():
    reply = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2999-01-01"}})
    assert reply["result"]["protocolVersion"] == LATEST


def test_notifications_get_no_answer():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_lists_both_tools_with_schemas():
    tools = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert [t["name"] for t in tools] == ["verify_done", "suggest_tests"]
    assert all(t["inputSchema"]["type"] == "object" and t["description"] for t in tools)


def test_unknown_method_and_tool_are_errors():
    assert handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})["error"]["code"] == -32601
    reply = handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope"}})
    assert reply["error"]["code"] == -32602


def test_a_bad_project_is_reported_as_a_tool_error_not_a_crash(tmp_path):
    reply = handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                    "params": {"name": "verify_done", "arguments": {"project": str(tmp_path)}}})
    assert reply["result"]["isError"] is True
    assert "criteria" in reply["result"]["content"][0]["text"]


def test_suggest_tests_through_the_protocol(tmp_path):
    (tmp_path / "criteria.md").write_text("- R1: slugify lowercases the title\n")
    (tmp_path / "test_slug.py").write_text("def test_slugify_lowercases():\n    assert 'a' == 'a'\n")
    reply = handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                    "params": {"name": "suggest_tests", "arguments": {"project": str(tmp_path)}}})
    text = reply["result"]["content"][0]["text"]
    assert reply["result"]["isError"] is False
    assert "test_slug.py::test_slugify_lowercases" in text


def test_end_to_end_over_stdio_on_the_broken_demo():
    """A real server process: handshake, list tools, then verify_done says the work is not done."""
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": LATEST}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "verify_done", "arguments": {"project": "demo/cart", "max_mutants": 20}}},
    ]
    done = subprocess.run(
        [sys.executable, "-m", "apodix", "mcp"], cwd=ROOT, input="\n".join(map(json.dumps, messages)) + "\n",
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    replies = [json.loads(line) for line in done.stdout.splitlines() if line.strip()]

    assert [r["id"] for r in replies] == [1, 2, 3]        # one answer per request, none for the notification
    text = replies[2]["result"]["content"][0]["text"]
    assert text.startswith("NOT DONE YET")
    assert "1 of 3 proven" in text
