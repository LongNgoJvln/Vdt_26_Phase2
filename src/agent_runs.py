"""Detached agent-run manager.

Keeps an agent/chat stream running server-side after the SSE client disconnects
(tab close, navigate away, refresh). The streaming generator is drained by a
background asyncio task into a per-session replay buffer; SSE clients SUBSCRIBE
to that buffer (replay everything so far, then live). Closing the SSE only drops
the subscriber — the drain task keeps going.

The wrapped generator already persists the assistant message to the session on
completion, so reopening the session shows the finished result even if nobody
was connected when it finished. Reconnecting mid-run replays the buffer + streams
live (pick up where it is).

Durability scope: in-memory, survives as long as the server process runs (tab
close / navigation / refresh). It does NOT survive a server restart.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)


class _Run:
    __slots__ = ("buffer", "subscribers", "status", "task", "evict_task", "human_future")

    def __init__(self) -> None:
        self.buffer: list = []          # ordered SSE event strings (replay log)
        self.subscribers: set = set()   # one asyncio.Queue per connected client
        self.status: str = "running"    # running | paused | done | error | stopped
        self.task: Optional[asyncio.Task] = None
        self.evict_task: Optional[asyncio.Task] = None
        # HITL: when not None, the running agent is suspended awaiting this
        # future. Resolved by resolve_pause(); awaited (and consumed) by the
        # agent loop via consume_pause(). A paused run is NOT cancelled — it
        # keeps its replay buffer and survives tab close/reopen.
        self.human_future: Optional[asyncio.Future] = None


_RUNS: Dict[str, _Run] = {}

# How long a FINISHED run (and its full replay buffer) is retained after the
# last subscriber disconnects, so a reconnect within the window can still
# replay the result. After this, the run is evicted to bound memory — without
# it, every session that ever streamed kept its entire event log forever.
_EVICT_GRACE_S = 180


def _publish(run: _Run, ev: str) -> None:
    """Append one SSE event and fan it out to every live subscriber."""
    run.buffer.append(ev)
    seq = len(run.buffer) - 1
    for q in list(run.subscribers):
        try:
            q.put_nowait((seq, ev))
        except Exception:
            pass


def _schedule_evict(session_id: str) -> None:
    """(Re)arm a grace-period eviction for a terminal run with no subscribers.
    Identity-checked so a run that gets replaced/reused is never evicted by a
    stale timer."""
    run = _RUNS.get(session_id)
    if run is None:
        return
    if run.evict_task and not run.evict_task.done():
        run.evict_task.cancel()

    async def _evict(run_ref: _Run) -> None:
        try:
            await asyncio.sleep(_EVICT_GRACE_S)
        except asyncio.CancelledError:
            return
        cur = _RUNS.get(session_id)
        if cur is run_ref and cur.status != "running" and not cur.subscribers:
            _RUNS.pop(session_id, None)

    run.evict_task = asyncio.create_task(_evict(run))


def is_active(session_id: str) -> bool:
    r = _RUNS.get(session_id)
    return bool(r and r.status == "running")


def get_status(session_id: str) -> Optional[str]:
    r = _RUNS.get(session_id)
    return r.status if r else None


async def _drain(session_id: str, agen: AsyncGenerator[str, None],
                 prev_task: Optional[asyncio.Task] = None) -> None:
    """Pull every event from the wrapped generator into the run buffer, fanning
    each out to live subscribers. Runs to completion regardless of subscribers."""
    run = _RUNS.get(session_id)
    if run is None:
        return
    # If this run replaced an in-flight one (rapid double-send), wait for that
    # one to fully finish first. Its CancelledError handler calls aclose(), which
    # persists its partial response — letting it complete before we start writing
    # keeps the two runs' session saves sequential instead of interleaved.
    if prev_task is not None and not prev_task.done():
        try:
            await asyncio.wait({prev_task})
        except asyncio.CancelledError:
            raise            # our own cancellation — propagate
        except Exception:
            pass
    try:
        async for ev in agen:
            _publish(run, ev)
        if run.status == "running":
            run.status = "done"
    except asyncio.CancelledError:
        run.status = "stopped"
        # Let the wrapped generator's own CancelledError handler run (it saves
        # the partial response to the session).
        try:
            await agen.aclose()
        except Exception:
            pass
    except Exception as e:
        logger.error("[agent-run] %s failed: %s", session_id, e, exc_info=True)
        run.status = "error"
        _publish(
            run,
            "event: error\n"
            f"data: {json.dumps({'error': 'Agent run failed before completion.', 'status': 500})}\n\n",
        )
        _publish(run, "data: [DONE]\n\n")
    finally:
        # Wake every subscriber with the end sentinel so their SSE closes.
        for q in list(run.subscribers):
            try:
                q.put_nowait((None, None))
            except Exception:
                pass
        # Run is terminal — arm the grace timer so it (and its buffer) is
        # eventually freed even if nobody ever reconnects. subscribe() cancels
        # this on connect and re-arms on disconnect.
        _schedule_evict(session_id)


def start(session_id: str, agen: AsyncGenerator[str, None]) -> _Run:
    """Start a detached run draining `agen` for a session. If a run is already in
    flight for this session (e.g. a rapid double-send), it's cancelled first."""
    prev = _RUNS.get(session_id)
    prev_task: Optional[asyncio.Task] = None
    if prev:
        if prev.task and not prev.task.done():
            prev.task.cancel()
            prev_task = prev.task   # new run awaits this before it starts writing
        if prev.evict_task and not prev.evict_task.done():
            prev.evict_task.cancel()
    run = _Run()
    _RUNS[session_id] = run
    run.task = asyncio.create_task(_drain(session_id, agen, prev_task))
    return run


async def subscribe(session_id: str) -> AsyncGenerator[str, None]:
    """Replay the run's buffer from the start, then stream live until it ends.
    Safe to call repeatedly (reconnect) and from multiple clients at once."""
    run = _RUNS.get(session_id)
    if run is None:
        return
    q: asyncio.Queue = asyncio.Queue()
    run.subscribers.add(q)            # register BEFORE replaying so nothing is missed
    # A live subscriber is connected — don't let a pending grace timer evict
    # the run out from under it mid-replay.
    if run.evict_task and not run.evict_task.done():
        run.evict_task.cancel()
    try:
        next_seq = 0
        while next_seq < len(run.buffer):
            yield run.buffer[next_seq]
            next_seq += 1
        if run.status != "running":
            return
        while True:
            seq, ev = await q.get()
            if seq is None:            # end sentinel
                while next_seq < len(run.buffer):   # flush any tail the sentinel raced
                    yield run.buffer[next_seq]
                    next_seq += 1
                break
            if seq >= next_seq:        # skip events already replayed from the buffer
                yield ev
                next_seq = seq + 1
    finally:
        run.subscribers.discard(q)
        # Last subscriber gone on a finished run — (re)arm eviction so the
        # buffer doesn't linger indefinitely.
        if not run.subscribers and run.status != "running":
            _schedule_evict(session_id)


def stop(session_id: str) -> bool:
    """Cancel an in-flight run (the wrapped generator saves its partial).

    If the run is paused awaiting a human decision, resolve that future first
    (as "cancel") so the suspended agent loop resumes and can be cancelled
    cleanly — otherwise the cancel target (the task) is parked on the await
    and the CancelledError never lands.
    """
    run = _RUNS.get(session_id)
    if not run:
        return False
    # Unblock a paused (HITL) run before cancelling.
    if run.human_future is not None and not run.human_future.done():
        try:
            run.human_future.set_result({"choice": "cancel"})
        except asyncio.InvalidStateError:
            pass
    if run.task and not run.task.done():
        run.task.cancel()
        return True
    return False


# ── Human-in-the-loop suspend/resume ────────────────────────────────────
def register_pause(session_id: str) -> bool:
    """Mark a running run as paused awaiting a human decision.

    Creates the future the agent loop will await. Returns False if no run
    exists or it isn't in a pausable state (already done/stopped/paused)."""
    run = _RUNS.get(session_id)
    if run is None or run.status != "running":
        return False
    if run.human_future is None or run.human_future.done():
        run.human_future = asyncio.Future()
    run.status = "paused"
    return True


async def consume_pause(session_id: str) -> Optional[dict]:
    """Await the human decision for a paused run. Returns the decision dict
    ({"choice": "yes"|"no"|"chat"|"edit"|"cancel", ...}) or None if no pause
    is registered for this session."""
    run = _RUNS.get(session_id)
    if run is None or run.human_future is None:
        return None
    future = run.human_future
    try:
        decision = await future
    finally:
        # The agent loop is the sole consumer; clear + resume status once it
        # has the answer so is_active()/status reflect a running run again.
        cur = _RUNS.get(session_id)
        if cur is not None:
            cur.human_future = None
            if cur.status == "paused":
                cur.status = "running"
    return decision


def resolve_pause(session_id: str, decision: dict) -> bool:
    """Provide the human decision to a paused run. Called by the HITL route.
    No-op (returns False) if nothing is paused."""
    run = _RUNS.get(session_id)
    if run is None or run.human_future is None or run.human_future.done():
        return False
    try:
        run.human_future.set_result(decision)
    except asyncio.InvalidStateError:
        return False
    # Status is restored to "running" by consume_pause() once the agent loop
    # has drained the answer; setting it here would briefly lie to
    # is_active() while the loop is still suspended.
    return True
