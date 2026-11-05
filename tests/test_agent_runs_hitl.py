"""Tests for the human-in-the-loop suspend/resume primitive in agent_runs.

Stays light: agent_runs is stdlib-only (asyncio + json), so it loads without
the app stack. The agent_loop integration (gate insert point + human_check SSE)
is exercised by the server smoke test in the plan's Verification section.
"""
import asyncio
import sys

# Ensure project root is importable (conftest already inserts it, but be safe
# when this file is run standalone or in a sparse selection).
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import agent_runs


SID = "hitl-test-1"


def _start_dummy_run(holder=None):
    """A detached run that mimics the agent loop: emits an event, then pauses
    and consumes a human decision. If `holder` (a dict) is supplied, the
    decision is stashed there for the test to inspect."""
    async def _agen():
        yield 'data: {"delta":"hello"}\n\n'
        assert agent_runs.register_pause(SID)
        decision = await agent_runs.consume_pause(SID)
        if holder is not None:
            holder["decision"] = decision
        yield 'data: {"delta":"done"}\n\n'
    agent_runs.start(SID, _agen())
    return agent_runs._RUNS[SID]


def test_register_pause_sets_paused_status():
    async def main():
        run = _start_dummy_run()
        await asyncio.sleep(0.02)
        assert run.status == "paused"
        assert run.human_future is not None
        agent_runs.resolve_pause(SID, {"choice": "yes"})
        await asyncio.sleep(0.02)
        # After resolution the consumer cleared the future + restored status.
        assert run.human_future is None
        assert run.status in ("running", "done")
        # cleanup
        agent_runs.stop(SID)
    asyncio.get_event_loop().run_until_complete(main())


def test_resolve_pause_returns_false_when_not_paused():
    async def main():
        assert not agent_runs.resolve_pause("nope", {"choice": "yes"})
    asyncio.get_event_loop().run_until_complete(main())


def test_choices_yes_no_edit_delivered_to_loop():
    async def _run_choice(choice):
        holder = {}
        async def _agen():
            yield 'data: {"delta":"x"}\n\n'
            assert agent_runs.register_pause(SID)
            holder["decision"] = await agent_runs.consume_pause(SID)
            yield 'data: {"delta":"y"}\n\n'
        agent_runs.start(SID, _agen())
        await asyncio.sleep(0.02)
        agent_runs.resolve_pause(SID, {"choice": choice})
        await asyncio.sleep(0.02)
        assert holder.get("decision", {}).get("choice") == choice
        agent_runs.stop(SID)

    for c in ("yes", "no", "edit"):
        asyncio.get_event_loop().run_until_complete(_run_choice(c))


def test_stop_unblocks_paused_run_without_deadlock():
    async def main():
        run = _start_dummy_run()
        await asyncio.sleep(0.02)
        assert run.status == "paused"
        # Stop must resolve the pending future then cancel the drain task,
        # not wedge on the await.
        assert agent_runs.stop(SID)
        await asyncio.sleep(0.03)
        assert run.task.done()
    asyncio.get_event_loop().run_until_complete(main())


def test_is_active_false_while_paused_true_while_running():
    async def main():
        _start_dummy_run()
        await asyncio.sleep(0.02)
        assert agent_runs.is_active(SID) is False
        agent_runs.resolve_pause(SID, {"choice": "yes"})
        await asyncio.sleep(0.02)
        assert agent_runs.get_status(SID) in ("running", "done")
    asyncio.get_event_loop().run_until_complete(main())
