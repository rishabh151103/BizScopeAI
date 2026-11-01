"""LangGraph entry point for the existing V2 chat investigation workflow.

The graph deliberately delegates business logic to the established V2
orchestrator. This keeps the public API and persistence behavior stable while
providing an explicit graph boundary for the current workflow.
"""

from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph


class ChatWorkflowState(TypedDict, total=False):
    request: dict[str, Any]
    runner: Callable[..., Any]
    result: Any


class EvidenceLoopState(TypedDict):
    cycle_index: int
    max_cycles: int
    should_continue: bool
    cycle_runner: Callable[[int], bool]
    stage_callbacks: dict[str, Callable[[dict[str, Any]], dict[str, Any]]]
    evidence_request: str
    analysis_plan: Any
    dataset_frame: Any
    execution_results: list
    evidence_results: list
    update_ok: bool
    stop: bool


def _run_existing_workflow(state: ChatWorkflowState) -> dict[str, Any]:
    runner = state.get("runner")
    if not callable(runner):
        raise TypeError("Chat workflow requires a callable V2 runner.")
    return {"result": runner(**state["request"])}


def build_chat_workflow():
    """Compile a minimal graph that preserves the established V2 workflow."""
    graph = StateGraph(ChatWorkflowState)
    graph.add_node("run_v2_investigation", _run_existing_workflow)
    graph.add_edge(START, "run_v2_investigation")
    graph.add_edge("run_v2_investigation", END)
    return graph.compile()


CHAT_WORKFLOW = build_chat_workflow()


def invoke_chat_workflow(runner: Callable[..., Any], **request) -> Any:
    """Run one chat request through the graph and return the legacy result."""
    state = CHAT_WORKFLOW.invoke({"runner": runner, "request": request})
    return state["result"]


def _execute_evidence_cycle(state: EvidenceLoopState) -> dict[str, Any]:
    keep_going = bool(state["cycle_runner"](state["cycle_index"]))
    return {
        "cycle_index": state["cycle_index"] + 1,
        "should_continue": keep_going,
    }


def _continue_evidence_loop(state: EvidenceLoopState) -> str:
    if state["should_continue"] and state["cycle_index"] < state["max_cycles"]:
        return "next_cycle"
    return "finish"


def build_evidence_loop():
    """A bounded graph loop; each analysis cycle is a graph invocation."""
    graph = StateGraph(EvidenceLoopState)
    graph.add_node("analysis_and_evidence_update", _execute_evidence_cycle)
    graph.add_edge(START, "analysis_and_evidence_update")
    graph.add_conditional_edges(
        "analysis_and_evidence_update",
        _continue_evidence_loop,
        {"next_cycle": "analysis_and_evidence_update", "finish": END},
    )
    return graph.compile()


EVIDENCE_LOOP = build_evidence_loop()


def run_bounded_evidence_loop(cycle_runner, max_cycles: int) -> int:
    if max_cycles < 1:
        return 0
    state = EVIDENCE_LOOP.invoke({
        "cycle_index": 0,
        "max_cycles": max_cycles,
        "should_continue": True,
        "cycle_runner": cycle_runner,
    }, config={"recursion_limit": max_cycles + 2})
    return state["cycle_index"]


def build_staged_investigation_graph():
    """Create the full bounded decision→plan→execute→persist→update loop."""
    graph = StateGraph(EvidenceLoopState)

    def stage(name):
        def run(state):
            callback = state["stage_callbacks"][name]
            return callback(state)
        return run

    for name in ("decision", "planning", "execution", "persistence", "hypothesis_update"):
        graph.add_node(name, stage(name))
    graph.add_edge(START, "decision")
    graph.add_conditional_edges(
        "decision",
        lambda state: "planning" if state.get("evidence_request") else "finish",
        {"planning": "planning", "finish": END},
    )
    graph.add_edge("planning", "execution")
    graph.add_conditional_edges(
        "execution",
        lambda state: "persist" if state.get("execution_results") else "finish",
        {"persist": "persistence", "finish": END},
    )
    graph.add_edge("persistence", "hypothesis_update")
    graph.add_conditional_edges(
        "hypothesis_update",
        lambda state: (
            "decision"
            if state.get("update_ok")
            and not state.get("stop")
            and state["cycle_index"] < state["max_cycles"]
            else "finish"
        ),
        {"decision": "decision", "finish": END},
    )
    return graph.compile()


def invoke_staged_investigation_graph(stage_callbacks, max_cycles: int):
    if max_cycles < 1:
        return {
            "cycle_index": 0,
            "max_cycles": max_cycles,
            "evidence_request": "",
            "execution_results": [],
            "evidence_results": [],
        }
    graph = build_staged_investigation_graph()
    return graph.invoke({
        "cycle_index": 0,
        "max_cycles": max_cycles,
        "should_continue": True,
        "cycle_runner": lambda _index: True,
        "stage_callbacks": stage_callbacks,
        "evidence_request": "",
        "execution_results": [],
        "evidence_results": [],
        "update_ok": True,
        "stop": False,
    }, config={"recursion_limit": max_cycles * 6 + 5})
