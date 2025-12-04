from typing import Dict, Any, Callable, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

from src.workflows_definitions_loader import load_and_validate_workflows, load_and_validate_step_templates
from src.workflows_types import (Workflow, WorkflowStep, StepTemplate,
    LlmStepTemplate, MlModelStepTemplate, CodeFunctionStepTemplate, DbReadStepTemplate, ANY_VALUE, END_NODE)
from src.code_functions import clean_call_transcript
from src.graph_visualization import display_mermaid_diagram


def build_run_graph() -> Dict[str, StateGraph]:
    step_templates = load_and_validate_step_templates()
    flows = load_and_validate_workflows(step_templates)
    run_graph = _build_run_graph_for_flows(flows, step_templates)
    return run_graph


def _build_run_graph_for_flows(flows: Dict[str, Workflow], step_templates: Dict[str, StepTemplate]):
    return {flow_name: _build_run_graph_for_flow(flow, step_templates) for flow_name, flow in flows.items()}


def _build_run_graph_for_flow(flow: Workflow, step_templates: Dict[str, StepTemplate],
                              create_graphical_view: bool = False) -> StateGraph:
    """Build a LangGraph StateGraph for executing a workflow by the workflow definition and step templates."""

    # Create a dynamic State schema for this workflow's state
    workflow_state_schema = _create_workflow_state_schema(flow)

    # Use the TypedDict schema for the state graph
    graph_builder = StateGraph(workflow_state_schema)

    # Create nodes for each step in the workflow
    for step in flow.steps:
        template = step_templates[step.step_template_name]
        node_func = _get_node_function_by_type(template, step)
        graph_builder.add_node(step.step_name, node_func)

    # Set entry point to first step
    if flow.steps:
        graph_builder.set_entry_point(flow.steps[0].step_name)

    # Add edges between nodes
    for i, step in enumerate(flow.steps):
        if step.next_step_mapping:
            # Create conditional edges based on output field value
            routing_func = _create_routing_func(step)

            # Build edge mapping: map each possible next step to itself
            edge_mapping = {step_name: END if step_name == END_NODE else step_name
                            for step_name in step.next_step_mapping.values()}

            graph_builder.add_conditional_edges(step.step_name, routing_func, edge_mapping)
        else: # Default edge to next step or END
            if i + 1 < len(flow.steps):
                graph_builder.add_edge(step.step_name, flow.steps[i + 1].step_name)
            else:
                graph_builder.add_edge(step.step_name, END)

    result_graph = graph_builder.compile()

    if create_graphical_view:
        mermaid = result_graph.get_graph().draw_mermaid()
        display_mermaid_diagram(mermaid, flow.workflow_name, auto_open=True)

    return result_graph

# =======================================================================


def _create_workflow_state_schema(flow: Workflow) -> type:
    """
    Dynamically create a TypedDict schema for the workflow state based on all fields used in the workflow.
    This ensures LangGraph can properly handle state updates.
    """
    # Collect all unique field names from input and output mappings
    fields = set()
    for step in flow.steps:
        fields.update(step.input_fields_mapping.values())
        fields.update(step.output_fields_mapping.values())

    # Create a dictionary mapping field names to Any type
    # TODO in future maybe create a few views for different nodes
    field_dict = {field: Any for field in fields}

    # Dynamically create a TypedDict with all fields optional (total=False)
    # This allows fields to be added incrementally as the workflow executes
    state_class = TypedDict('state_class', field_dict, total=False)
    return state_class


def _start_graph_node_processing(step: WorkflowStep, state: Dict[str, Any]) -> Dict[str, Any]:
    # Check input conditions
    print("Started step: ", step.step_name)  # TODO we can trace using @traceable and/or log with DataDog
    if step.input_conditions:
        for field, expected_value in step.input_conditions.items():
            if state.get(field) != expected_value:
                # Return None for all output fields
                return {workflow_field: None for workflow_field in step.output_fields_mapping.values()}

    # Map input fields from workflow state to template fields
    inputs = {}
    for template_field, workflow_field in step.input_fields_mapping.items():
        inputs[template_field] = state.get(workflow_field)
    return inputs


def _finish_graph_node_processing(step: WorkflowStep, outputs: Dict[str, Any]):
    # Map output fields from template fields to workflow state fields
    result = {}
    for template_field, workflow_field in step.output_fields_mapping.items():
        result[workflow_field] = outputs.get(template_field)
    return result

# =======================================================================


def _create_llm_step_node(step: WorkflowStep, template: LlmStepTemplate) -> Callable:
    def llm_node(state: Dict[str, Any]) -> Dict[str, Any]:
        inputs = _start_graph_node_processing(step, state)

        # TODO: Actual LLM execution logic here - llm.invoke(...) - for now it is just a stub
        if template.prompt_name == "extract_patient_identification":
            outputs = {"patient_id": "1243", "extraction_confidence": 0.9}
        elif template.prompt_name == "analyze_patient_call":
            outputs = {"call_succeeded": "yes", "call_type": "Talk", "home_visit_suggested": "yes", "patient_frustrated": "no"}
        elif template.prompt_name == "create_patient_call_summary":
            outputs = {"call_summary": "Call was very successful. Patient agreed to a home visit."}
        elif template.prompt_name == "create_escalation_summary":
            outputs = {"escalation_summary": "Patient is frustrated and needs urgent attention.", "urgency_level": 1}
        else:
            outputs = {field: "Yes" for field in template.output_fields}

        return _finish_graph_node_processing(step, outputs)
    return llm_node


def _create_ml_model_step_node(step: WorkflowStep, template: MlModelStepTemplate) -> Callable:
    def ml_model_node(state: Dict[str, Any]) -> Dict[str, Any]:
        inputs = _start_graph_node_processing(step, state)

        # TODO: Actual ML model execution logic here - for now its a Stub: return None for all output fields
        outputs = {field: None for field in template.output_fields}

        return _finish_graph_node_processing(step, outputs)

    return ml_model_node


def _create_code_function_step_node(step: WorkflowStep, template: CodeFunctionStepTemplate) -> Callable:
    def code_function_node(state: Dict[str, Any]) -> Dict[str, Any]:
        inputs = _start_graph_node_processing(step, state)

        # TODO: Actual code function execution logic here - for now it is just a stub
        if template.function_name == "clean_call_transcript":
            outputs = clean_call_transcript(inputs)
        else:
            outputs =  {field: None for field in template.output_fields}

        return _finish_graph_node_processing(step, outputs)

    return code_function_node


def _create_db_read_step_node(step: WorkflowStep, template: DbReadStepTemplate) -> Callable:
    """Create a node function for DB read step"""
    def db_read_node(state: Dict[str, Any]) -> Dict[str, Any]:
        inputs = _start_graph_node_processing(step, state)

        # TODO: Actual DB read execution logic here - for now its just a stub
        if template.template_name == "db_fetch_patient_data":
            outputs = {"patient_name": "Dao Tao", "patient_email": "daotao@xy.com", "patient_history": "bla bla bla"}
        else:
            outputs = {field: None for field in template.output_fields}

        return _finish_graph_node_processing(step, outputs)

    return db_read_node

# =======================================================================

def _get_node_function_by_type(template: StepTemplate, step: WorkflowStep) -> Callable:
    if isinstance(template, LlmStepTemplate):
        return _create_llm_step_node(step, template)
    elif isinstance(template, MlModelStepTemplate):
        return _create_ml_model_step_node(step, template)
    elif isinstance(template, CodeFunctionStepTemplate):
        return _create_code_function_step_node(step, template)
    elif isinstance(template, DbReadStepTemplate):
        return _create_db_read_step_node(step, template)
    else:
        raise ValueError(f"Unknown template type: {type(template)}")


def _create_routing_func(step: WorkflowStep) -> Callable:
    def route(state: Dict[str, Any]) -> str:
        if step.output_field_for_next_step_mapping is not None:
            # Map from template field to state field
            state_field = step.output_fields_mapping[step.output_field_for_next_step_mapping]
            decision_field_value = str(state.get(state_field, ""))
        else:
            decision_field_value = ANY_VALUE
        next_step = step.next_step_mapping.get(decision_field_value) or END_NODE
        return next_step
    return route
