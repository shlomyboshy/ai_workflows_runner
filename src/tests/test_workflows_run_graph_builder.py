"""
Unit tests for workflows_run_graph_builder.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.workflows_run_graph_builder import (
    _create_workflow_state_schema,
    _start_graph_node_processing,
    _finish_graph_node_processing,
    _create_llm_step_node,
    _create_ml_model_step_node,
    _create_code_function_step_node,
    _create_db_read_step_node,
    _get_node_function_by_type,
    _create_routing_func,
    build_run_graph
)
from src.workflows_types import (
    Workflow,
    WorkflowStep,
    LlmStepTemplate,
    MlModelStepTemplate,
    CodeFunctionStepTemplate,
    DbReadStepTemplate
)


class TestCreateWorkflowStateSchema:
    """Tests for _create_workflow_state_schema function"""

    def test_create_state_schema_simple_workflow(self, sample_workflow):
        """Test creating state schema for simple workflow"""
        workflow = Workflow.model_validate(sample_workflow)
        schema = _create_workflow_state_schema(workflow)

        assert schema is not None
        assert hasattr(schema, '__annotations__')
        # Should have both input and output fields
        assert 'initial_input' in schema.__annotations__
        assert 'step1_output' in schema.__annotations__

    def test_create_state_schema_multiple_steps(self, sample_workflow_with_conditional):
        """Test creating state schema for workflow with multiple steps"""
        workflow = Workflow.model_validate(sample_workflow_with_conditional)
        schema = _create_workflow_state_schema(workflow)

        assert schema is not None
        # Should have fields from all steps
        assert 'initial_input' in schema.__annotations__
        assert 'decision' in schema.__annotations__
        assert 'final_output' in schema.__annotations__

    def test_create_state_schema_no_duplicate_fields(self, sample_workflow):
        """Test that schema doesn't duplicate fields"""
        workflow = Workflow.model_validate(sample_workflow)
        schema = _create_workflow_state_schema(workflow)

        # Count should match unique fields
        fields_set = set()
        for step in workflow.steps:
            fields_set.update(step.input_fields_mapping.values())
            fields_set.update(step.output_fields_mapping.values())

        assert len(schema.__annotations__) == len(fields_set)


class TestStartGraphNodeProcessing:
    """Tests for _start_graph_node_processing function"""

    def test_start_processing_no_conditions(self):
        """Test processing without input conditions"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"template_field": "state_field"},
            output_fields_mapping={"output_field": "state_output"}
        )
        state = {"state_field": "test_value"}

        result = _start_graph_node_processing(step, state)

        assert result == {"template_field": "test_value"}

    def test_start_processing_with_met_conditions(self):
        """Test processing with satisfied input conditions"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"template_field": "state_field"},
            output_fields_mapping={"output_field": "state_output"},
            input_conditions={"condition_field": "expected_value"}
        )
        state = {
            "state_field": "test_value",
            "condition_field": "expected_value"
        }

        result = _start_graph_node_processing(step, state)

        assert result == {"template_field": "test_value"}

    def test_start_processing_with_unmet_conditions(self):
        """Test processing with unsatisfied input conditions"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"template_field": "state_field"},
            output_fields_mapping={"output_field": "state_output"},
            input_conditions={"condition_field": "expected_value"}
        )
        state = {
            "state_field": "test_value",
            "condition_field": "wrong_value"  # Condition not met
        }

        result = _start_graph_node_processing(step, state)

        # Should return None for output fields
        assert result == {"state_output": None}

    def test_start_processing_missing_state_field(self):
        """Test processing when state field is missing"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"template_field": "missing_field"},
            output_fields_mapping={"output_field": "state_output"}
        )
        state = {}

        result = _start_graph_node_processing(step, state)

        assert result == {"template_field": None}


class TestFinishGraphNodeProcessing:
    """Tests for _finish_graph_node_processing function"""

    def test_finish_processing_simple_mapping(self):
        """Test finishing with simple field mapping"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"template_output": "state_output"}
        )
        outputs = {"template_output": "result_value"}

        result = _finish_graph_node_processing(step, outputs)

        assert result == {"state_output": "result_value"}

    def test_finish_processing_multiple_outputs(self):
        """Test finishing with multiple output fields"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={
                "template_output1": "state_output1",
                "template_output2": "state_output2"
            }
        )
        outputs = {
            "template_output1": "value1",
            "template_output2": "value2"
        }

        result = _finish_graph_node_processing(step, outputs)

        assert result == {
            "state_output1": "value1",
            "state_output2": "value2"
        }

    def test_finish_processing_missing_output(self):
        """Test finishing when output is missing"""
        step = WorkflowStep(
            step_name="test_step",
            step_template_name="test_template",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"template_output": "state_output"}
        )
        outputs = {}  # Missing output

        result = _finish_graph_node_processing(step, outputs)

        assert result == {"state_output": None}


class TestCreateStepNodes:
    """Tests for node creation functions"""

    def test_create_llm_step_node(self):
        """Test creating LLM step node"""
        step = WorkflowStep(
            step_name="llm_step",
            step_template_name="llm_template",
            input_fields_mapping={"input_text": "state_input"},
            output_fields_mapping={"output_text": "state_output"}
        )
        template = LlmStepTemplate(
            template_name="llm_template",
            type="llm",
            input_fields=["input_text"],
            output_fields=["output_text"],
            prompt_name="test_prompt",
            llm_model_name="gpt-4",
            prompt_version="v1.0"
        )

        node_func = _create_llm_step_node(step, template)

        assert callable(node_func)

        # Test execution
        state = {"state_input": "test input"}
        result = node_func(state)

        assert "state_output" in result
        assert result["state_output"] is not None  # Should return something

    def test_create_ml_model_step_node(self):
        """Test creating ML model step node"""
        step = WorkflowStep(
            step_name="ml_step",
            step_template_name="ml_template",
            input_fields_mapping={"features": "state_features"},
            output_fields_mapping={"prediction": "state_prediction"}
        )
        template = MlModelStepTemplate(
            template_name="ml_template",
            type="ml_model",
            input_fields=["features"],
            output_fields=["prediction"],
            ml_model_name="test_model",
            ml_model_version="v1.0"
        )

        node_func = _create_ml_model_step_node(step, template)

        assert callable(node_func)

        # Test execution
        state = {"state_features": [1, 2, 3]}
        result = node_func(state)

        assert "state_prediction" in result

    def test_create_code_function_step_node(self):
        """Test creating code function step node"""
        step = WorkflowStep(
            step_name="code_step",
            step_template_name="code_template",
            input_fields_mapping={"raw_input": "state_input"},
            output_fields_mapping={"processed_output": "state_output"}
        )
        template = CodeFunctionStepTemplate(
            template_name="code_template",
            type="code_function",
            input_fields=["raw_input"],
            output_fields=["processed_output"],
            function_name="test_function"
        )

        node_func = _create_code_function_step_node(step, template)

        assert callable(node_func)

    def test_create_db_read_step_node(self):
        """Test creating DB read step node"""
        step = WorkflowStep(
            step_name="db_step",
            step_template_name="db_template",
            input_fields_mapping={"user_id": "state_user_id"},
            output_fields_mapping={"user_name": "state_user_name"}
        )
        template = DbReadStepTemplate(
            template_name="db_template",
            type="db_read",
            input_fields=["user_id"],
            output_fields=["user_name"],
            db_name="test_db",
            query="SELECT * FROM users WHERE id = {user_id}"
        )

        node_func = _create_db_read_step_node(step, template)

        assert callable(node_func)


class TestGetNodeFunctionByType:
    """Tests for _get_node_function_by_type function"""

    def test_get_llm_node_function(self):
        """Test getting LLM node function"""
        step = WorkflowStep(
            step_name="test",
            step_template_name="test",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"output": "state_output"}
        )
        template = LlmStepTemplate(
            template_name="test",
            type="llm",
            input_fields=["input"],
            output_fields=["output"],
            prompt_name="test",
            llm_model_name="gpt-4",
            prompt_version="v1.0"
        )

        func = _get_node_function_by_type(template, step)

        assert callable(func)

    def test_get_unknown_node_function(self):
        """Test error for unknown template type"""
        step = WorkflowStep(
            step_name="test",
            step_template_name="test",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"output": "state_output"}
        )

        # Create a mock template with unknown type
        template = Mock()

        with pytest.raises(ValueError, match="Unknown template type"):
            _get_node_function_by_type(template, step)


class TestCreateRoutingFunc:
    """Tests for _create_routing_func function"""

    def test_routing_with_output_field(self):
        """Test routing based on output field value"""
        step = WorkflowStep(
            step_name="test",
            step_template_name="test",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"decision": "state_decision"},
            output_field_for_next_step_mapping="decision",
            next_step_mapping={
                "yes": "step_yes",
                "no": "step_no"
            }
        )

        routing_func = _create_routing_func(step)

        # Test routing to "yes" branch
        state = {"state_decision": "yes"}
        assert routing_func(state) == "step_yes"

        # Test routing to "no" branch
        state = {"state_decision": "no"}
        assert routing_func(state) == "step_no"

    def test_routing_to_end_when_no_match(self):
        """Test routing to END when no mapping matches"""
        step = WorkflowStep(
            step_name="test",
            step_template_name="test",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"decision": "state_decision"},
            output_field_for_next_step_mapping="decision",
            next_step_mapping={
                "yes": "step_yes",
                "no": "step_no"
            }
        )

        routing_func = _create_routing_func(step)

        # Test with unmapped value
        state = {"state_decision": "maybe"}
        assert routing_func(state) == "__end__"

    def test_routing_without_output_field(self):
        """Test routing when output_field_for_next_step_mapping is None"""
        step = WorkflowStep(
            step_name="test",
            step_template_name="test",
            input_fields_mapping={"input": "state_input"},
            output_fields_mapping={"output": "state_output"},
            next_step_mapping={
                "__any__": "next_step"
            }
        )

        routing_func = _create_routing_func(step)

        # Should route to __any__ mapping
        state = {"state_output": "anything"}
        assert routing_func(state) == "next_step"


class TestBuildRunGraph:
    """Tests for build_run_graph function"""

    @patch('ai_eng.workflows_runner.workflows_run_graph_builder.load_and_validate_step_templates')
    @patch('ai_eng.workflows_runner.workflows_run_graph_builder.load_and_validate_workflows')
    def test_build_run_graph_success(self, mock_load_workflows, mock_load_templates,
                                     sample_workflow, sample_llm_step_template):
        """Test successful graph building"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        # Setup mocks
        mock_load_templates.return_value = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }
        mock_load_workflows.return_value = {
            "test_workflow": Workflow.model_validate(sample_workflow)
        }

        graphs = build_run_graph()

        assert len(graphs) == 1
        assert "test_workflow" in graphs
        assert graphs["test_workflow"] is not None

    @patch('ai_eng.workflows_runner.workflows_run_graph_builder.load_and_validate_step_templates')
    def test_build_run_graph_no_templates(self, mock_load_templates):
        """Test error when no templates are loaded"""
        mock_load_templates.side_effect = FileNotFoundError("No templates found")

        with pytest.raises(FileNotFoundError):
            build_run_graph()

    @patch('ai_eng.workflows_runner.workflows_run_graph_builder.load_and_validate_step_templates')
    @patch('ai_eng.workflows_runner.workflows_run_graph_builder.load_and_validate_workflows')
    def test_build_run_graph_empty_workflows(self, mock_load_workflows, mock_load_templates,
                                             sample_llm_step_template):
        """Test building graph with no workflows"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        mock_load_templates.return_value = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }
        mock_load_workflows.return_value = {}

        graphs = build_run_graph()

        assert len(graphs) == 0
