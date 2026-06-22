"""Per-trace isolation for the process-wide EventBus / TaskStateTracker singletons.

These tests pin the concurrency fix: two runs sharing the same singleton must not
overwrite each other's task state, ``reset()`` must only clear the current run,
and a streaming subscriber must only see events from its own run.
"""

import asyncio

import pytest

from app.core.agent_status import (
    AgentEvent,
    EventBus,
    TaskStateTracker,
    TaskStatus,
    set_current_trace_id,
)


async def _run_in_trace(trace_id, coro_fn):
    """Run coro_fn() inside its own contextvars context bound to trace_id.

    A fresh ``asyncio.Task`` copies the current context at creation, mirroring how
    each FastAPI request handler gets its own isolated context.
    """

    async def _wrapped():
        set_current_trace_id(trace_id)
        return await coro_fn()

    return await asyncio.create_task(_wrapped())


@pytest.mark.asyncio
async def test_state_tracker_isolated_per_trace():
    tracker = TaskStateTracker.get_instance()

    async def run_a():
        tracker.set_status("task_1", TaskStatus.RUNNING)
        tracker.set_status("task_2", TaskStatus.SUCCESS)
        return tracker.get_all_states()

    async def run_b():
        tracker.set_status("task_1", TaskStatus.FAILED)
        return tracker.get_all_states()

    states_a, states_b = await asyncio.gather(
        _run_in_trace("iso-a", run_a),
        _run_in_trace("iso-b", run_b),
    )

    assert states_a == {"task_1": "running", "task_2": "success"}
    assert states_b == {"task_1": "failed"}


@pytest.mark.asyncio
async def test_reset_only_clears_current_trace():
    tracker = TaskStateTracker.get_instance()

    async def seed_a():
        tracker.set_status("task_1", TaskStatus.SUCCESS)

    async def reset_b_then_check_a():
        # B seeds its own state then resets B; A must remain intact.
        tracker.set_status("task_9", TaskStatus.SUCCESS)
        tracker.reset()
        return tracker.get_all_states()

    await _run_in_trace("reset-a", seed_a)
    states_b_after_reset = await _run_in_trace("reset-b", reset_b_then_check_a)

    async def read_a():
        return tracker.get_all_states()

    states_a = await _run_in_trace("reset-a", read_a)

    assert states_b_after_reset == {}
    assert states_a == {"task_1": "success"}


@pytest.mark.asyncio
async def test_emit_stamps_current_trace_id():
    bus = EventBus.get_instance()
    seen: list[str] = []

    async def collector(event: AgentEvent):
        seen.append(event.trace_id)

    bus.subscribe("probe", collector)
    try:

        async def emit_in_trace():
            await bus.emit(AgentEvent(event_type="probe", agent_name="t"))

        await _run_in_trace("trace-xyz", emit_in_trace)
    finally:
        bus.unsubscribe("probe", collector)

    assert "trace-xyz" in seen


@pytest.mark.asyncio
async def test_explicit_trace_id_is_not_overwritten():
    bus = EventBus.get_instance()
    seen: list[str] = []

    async def collector(event: AgentEvent):
        seen.append(event.trace_id)

    bus.subscribe("probe2", collector)
    try:

        async def emit_in_trace():
            # An event that already carries a trace_id keeps it.
            await bus.emit(
                AgentEvent(event_type="probe2", agent_name="t", trace_id="explicit")
            )

        await _run_in_trace("trace-ctx", emit_in_trace)
    finally:
        bus.unsubscribe("probe2", collector)

    assert seen == ["explicit"]


@pytest.mark.asyncio
async def test_subscriber_can_filter_foreign_run_events():
    """Mirrors the orchestrator streaming filter: only collect own-run events."""
    bus = EventBus.get_instance()
    own_trace = "run-own"
    collected: list[str] = []

    async def own_subscriber(event: AgentEvent):
        if event.trace_id and event.trace_id != own_trace:
            return
        collected.append(event.data["task_id"])

    bus.subscribe("task_complete", own_subscriber)
    try:

        async def own_run():
            await bus.emit(
                AgentEvent(
                    event_type="task_complete",
                    agent_name="executor",
                    data={"task_id": "mine"},
                )
            )

        async def foreign_run():
            await bus.emit(
                AgentEvent(
                    event_type="task_complete",
                    agent_name="executor",
                    data={"task_id": "theirs"},
                )
            )

        await asyncio.gather(
            _run_in_trace(own_trace, own_run),
            _run_in_trace("run-foreign", foreign_run),
        )
    finally:
        bus.unsubscribe("task_complete", own_subscriber)

    assert "mine" in collected
    assert "theirs" not in collected
