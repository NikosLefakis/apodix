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


def test_a_ping_is_answered_while_a_long_check_is_still_running(tmp_path):
    """Clients ping to see the server is alive. During a check that takes a while it must still answer.

    The project's test sleeps, so the check lasts several seconds on any machine, however fast."""
    import threading
    import time

    (tmp_path / "lib.py").write_text("def f(x):\n    return x + 1\n")
    (tmp_path / "test_lib.py").write_text(
        "import time\nimport pytest\nfrom lib import f\n\n"
        "@pytest.mark.covers('R1')\ndef test_f():\n    time.sleep(2)\n    assert f(1) == 2\n")
    (tmp_path / "criteria.md").write_text("- R1: f adds one\n")

    proc = subprocess.Popen(
        [sys.executable, "-m", "apodix", "mcp"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
    )
    arrived: list[int] = []

    def read():
        for line in proc.stdout:
            if line.strip():
                arrived.append(json.loads(line)["id"])

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    send = lambda m: (proc.stdin.write(json.dumps(m) + "\n"), proc.stdin.flush())

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": LATEST}})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "verify_done", "arguments": {"project": str(tmp_path), "max_mutants": 2}}})
    time.sleep(1)                                           # the check is running now: it needs at least 4 seconds
    send({"jsonrpc": "2.0", "id": 3, "method": "ping"})
    proc.stdin.close()
    proc.wait(timeout=180)
    reader.join(timeout=5)

    assert arrived.index(3) < arrived.index(2), arrived    # the ping came back before the check finished


def test_done_with_a_barely_proven_criterion_says_so():
    from apodix.mcp import _headline
    from apodix.verify import CriterionResult, MutantOutcome, Report

    weak = CriterionResult("R2", "x", "proven", "", score=0.6,
                           survived=[MutantOutcome("cart.py", 5, "100 became 101", False)])
    strong = CriterionResult("R1", "y", "proven", "", score=0.95)
    assert _headline(Report("p", "c.md", [strong], 1, 1)) == "DONE"
    text = _headline(Report("p", "c.md", [strong, weak], 2, 2))
    assert text.startswith("DONE, WITH WEAK SPOTS") and "R2" in text and "cart.py:5" in text
    assert _headline(Report("p", "c.md", [strong, weak], 2, 1)) == "NOT DONE YET"   # a failing test is never DONE


def test_a_check_finishes_while_the_clients_stdin_stays_open(tmp_path):
    """A real client keeps stdin open and waits for the answer. On Windows the test runs used to hang here,
    because the child process inherited the server's stdin pipe while the server was blocked reading it."""
    import queue
    import threading

    (tmp_path / "lib.py").write_text("def f(x):\n    return x + 1\n")
    (tmp_path / "test_lib.py").write_text(
        "import pytest\nfrom lib import f\n\n@pytest.mark.covers('R1')\ndef test_f():\n    assert f(1) == 2\n")
    (tmp_path / "criteria.md").write_text("- R1: f adds one\n")

    proc = subprocess.Popen(
        [sys.executable, "-m", "apodix", "mcp"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
    )
    lines: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout], daemon=True).start()
    try:
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "verify_done", "arguments": {"project": str(tmp_path), "max_mutants": 3}}}) + "\n")
        proc.stdin.flush()                                  # and keep stdin open: do not close it
        reply = json.loads(lines.get(timeout=90))           # a hang shows up as queue.Empty
        assert reply["id"] == 1 and "R1" in reply["result"]["content"][0]["text"]
    finally:
        proc.kill()
