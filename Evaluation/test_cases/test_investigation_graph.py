from Backend.investigation_graph import (
    invoke_chat_workflow,
    invoke_staged_investigation_graph,
)


def test_chat_graph_passes_request_to_existing_v2_runner():
    received = {}

    def runner(**kwargs):
        received.update(kwargs)
        return {"response": "grounded", "visualizations": []}

    result = invoke_chat_workflow(
        runner,
        user_input="Summarize the results",
        investigation_id=17,
        dataset_id=4,
    )

    assert result == {"response": "grounded", "visualizations": []}
    assert received == {
        "user_input": "Summarize the results",
        "investigation_id": 17,
        "dataset_id": 4,
    }


def test_chat_graph_propagates_workflow_errors():
    def runner(**_kwargs):
        raise RuntimeError("analysis failed")

    try:
        invoke_chat_workflow(runner, user_input="Analyze revenue")
    except RuntimeError as exc:
        assert str(exc) == "analysis failed"
    else:
        raise AssertionError("Graph must propagate V2 workflow failures")


def test_staged_graph_runs_and_routes_each_investigation_stage():
    seen = []

    def stage(name, patch=None):
        def run(state):
            seen.append((name, state["cycle_index"]))
            return patch or {}
        return run

    invoke_staged_investigation_graph({
        "decision": stage("decision", {"evidence_request": "compute metric", "stop": False}),
        "planning": stage("planning"),
        "execution": stage("execution", {"execution_results": ["ok"]}),
        "persistence": stage("persistence", {"evidence_results": ["saved"]}),
        "hypothesis_update": stage("hypothesis_update", {"update_ok": False, "stop": True, "cycle_index": 1}),
    }, max_cycles=2)

    assert [name for name, _ in seen] == [
        "decision", "planning", "execution", "persistence", "hypothesis_update"
    ]


def test_staged_graph_passes_planning_outputs_into_execution():
    observed = {}

    def decision(_state):
        return {"evidence_request": "total profit by category"}

    def planning(_state):
        return {"analysis_plan": "plan", "dataset_frame": "frame"}

    def execution(state):
        observed["plan"] = state["analysis_plan"]
        observed["frame"] = state["dataset_frame"]
        return {"execution_results": ["measured result"]}

    callbacks = {
        "decision": decision,
        "planning": planning,
        "execution": execution,
        "persistence": lambda state: {"evidence_results": state["execution_results"]},
        "hypothesis_update": lambda state: {
            "cycle_index": state["cycle_index"] + 1,
            "update_ok": False,
            "stop": True,
        },
    }

    result = invoke_staged_investigation_graph(callbacks, max_cycles=1)

    assert observed == {"plan": "plan", "frame": "frame"}
    assert result["evidence_results"] == ["measured result"]


def test_staged_graph_stops_when_decision_requests_no_evidence():
    seen = []

    def record(name):
        def run(_state):
            seen.append(name)
            return {"evidence_request": ""} if name == "decision" else {}
        return run

    invoke_staged_investigation_graph(
        {name: record(name) for name in (
            "decision", "planning", "execution", "persistence", "hypothesis_update"
        )},
        max_cycles=2,
    )

    assert seen == ["decision"]


def test_staged_graph_does_not_reuse_prior_plan_when_followup_planning_fails():
    executed = []
    planning_count = 0

    def planning(_state):
        nonlocal planning_count
        planning_count += 1
        if planning_count == 1:
            return {"analysis_plan": "first plan", "dataset_frame": "first frame"}
        return {"analysis_plan": None, "dataset_frame": None, "stop": True}

    def execution(state):
        plan = state.get("analysis_plan")
        executed.append(plan)
        return {"execution_results": ["result"] if plan else []}

    def hypothesis_update(state):
        return {
            "cycle_index": state["cycle_index"] + 1,
            "update_ok": True,
            "stop": False,
        }

    invoke_staged_investigation_graph({
        "decision": lambda state: {"evidence_request": f"request {state['cycle_index']}"},
        "planning": planning,
        "execution": execution,
        "persistence": lambda state: {"evidence_results": state["execution_results"]},
        "hypothesis_update": hypothesis_update,
    }, max_cycles=2)

    assert executed == ["first plan", None]
