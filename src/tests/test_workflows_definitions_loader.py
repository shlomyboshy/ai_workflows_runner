"""
Unit tests for workflows_definitions_loader.py
"""
import json
import pytest

from src.workflows_definitions_loader import (
    load_and_validate_step_templates,
    load_and_validate_workflows,
    validate_workflow_against_templates
)
from src.workflows_types import (
    LlmStepTemplate,
    CodeFunctionStepTemplate,
    Workflow
)


class TestLoadAndValidateStepTemplates:
    """Tests for load_and_validate_step_templates function"""

    def test_load_valid_step_templates(self, create_temp_step_templates):
        """Test loading valid step templates from directory"""
        templates = load_and_validate_step_templates(create_temp_step_templates)

        assert len(templates) == 2
        assert "test_llm_step" in templates
        assert "test_code_step" in templates
        assert isinstance(templates["test_llm_step"], LlmStepTemplate)
        assert isinstance(templates["test_code_step"], CodeFunctionStepTemplate)

    def test_load_step_templates_directory_not_exists(self, temp_dir):
        """Test error when directory doesn't exist"""
        non_existent_dir = temp_dir / "non_existent"

        with pytest.raises(FileNotFoundError, match="Step templates directory does not exist"):
            load_and_validate_step_templates(non_existent_dir)

    def test_load_step_templates_duplicate_names(self, temp_dir, sample_llm_step_template):
        """Test error when duplicate template names exist"""
        steps_dir = temp_dir / "steps"
        steps_dir.mkdir()

        # Create two files with same template_name
        (steps_dir / "template1.json").write_text(json.dumps(sample_llm_step_template))
        (steps_dir / "template2.json").write_text(json.dumps(sample_llm_step_template))

        with pytest.raises(ValueError, match="Duplicate step template_name"):
            load_and_validate_step_templates(steps_dir)

    def test_load_step_templates_invalid_json(self, temp_dir):
        """Test error when JSON is invalid"""
        steps_dir = temp_dir / "steps"
        steps_dir.mkdir()

        (steps_dir / "invalid.json").write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_and_validate_step_templates(steps_dir)

    def test_load_step_templates_invalid_type(self, temp_dir):
        """Test error when step type is invalid"""
        steps_dir = temp_dir / "steps"
        steps_dir.mkdir()

        invalid_template = {
            "template_name": "invalid",
            "type": "invalid_type",
            "input_fields": ["input"],
            "output_fields": ["output"]
        }

        (steps_dir / "invalid_type.json").write_text(json.dumps(invalid_template))

        with pytest.raises(ValueError, match="Unknown step template type"):
            load_and_validate_step_templates(steps_dir)

    def test_load_step_templates_missing_required_fields(self, temp_dir):
        """Test error when required fields are missing"""
        steps_dir = temp_dir / "steps"
        steps_dir.mkdir()

        incomplete_template = {
            "template_name": "incomplete",
            "type": "llm",
            "input_fields": ["input"],
            "output_fields": ["output"]
            # Missing: prompt_name, llm_model_name, prompt_version
        }

        (steps_dir / "incomplete.json").write_text(json.dumps(incomplete_template))

        with pytest.raises(Exception):  # Pydantic validation error
            load_and_validate_step_templates(steps_dir)

    def test_load_step_templates_empty_directory(self, temp_dir):
        """Test loading from empty directory"""
        steps_dir = temp_dir / "steps"
        steps_dir.mkdir()

        templates = load_and_validate_step_templates(steps_dir)
        assert len(templates) == 0


class TestValidateWorkflowAgainstTemplates:
    """Tests for validate_workflow_against_templates function"""

    def test_validate_valid_workflow(self, sample_workflow, sample_llm_step_template):
        """Test validation of valid workflow against templates"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }
        workflow = Workflow.model_validate(sample_workflow)

        # Should not raise
        validate_workflow_against_templates(workflow, templates)

    def test_validate_workflow_unknown_template(self, sample_workflow):
        """Test error when workflow references unknown template"""
        workflow = Workflow.model_validate(sample_workflow)
        templates = {}  # Empty templates

        with pytest.raises(ValueError, match="references unknown step_template_name"):
            validate_workflow_against_templates(workflow, templates)

    def test_validate_workflow_mismatched_input_fields(self, sample_workflow, sample_llm_step_template):
        """Test error when input fields don't match"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }

        # Modify workflow to have wrong input fields
        sample_workflow["steps"][0]["input_fields_mapping"] = {
            "wrong_field": "initial_input"
        }

        workflow = Workflow.model_validate(sample_workflow)

        with pytest.raises(ValueError, match="Mismatched input_fields_mapping keys"):
            validate_workflow_against_templates(workflow, templates)

    def test_validate_workflow_mismatched_output_fields(self, sample_workflow, sample_llm_step_template):
        """Test error when output fields don't match"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }

        # Modify workflow to have wrong output fields
        sample_workflow["steps"][0]["output_fields_mapping"] = {
            "wrong_field": "step1_output"
        }

        workflow = Workflow.model_validate(sample_workflow)

        with pytest.raises(ValueError, match="Mismatched output_fields_mapping keys"):
            validate_workflow_against_templates(workflow, templates)


class TestLoadAndValidateWorkflows:
    """Tests for load_and_validate_workflows function"""

    def test_load_valid_workflows(self, create_temp_workflow, sample_llm_step_template):
        """Test loading valid workflows"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }

        workflows = load_and_validate_workflows(templates, create_temp_workflow)

        assert len(workflows) == 1
        assert "test_workflow" in workflows
        assert isinstance(workflows["test_workflow"], Workflow)

    def test_load_workflows_directory_not_exists(self, temp_dir, sample_llm_step_template):
        """Test error when workflows directory doesn't exist"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }
        non_existent_dir = temp_dir / "non_existent"

        with pytest.raises(FileNotFoundError, match="Workflows directory does not exist"):
            load_and_validate_workflows(templates, non_existent_dir)

    def test_load_workflows_duplicate_names(self, temp_dir, sample_workflow, sample_llm_step_template):
        """Test error when duplicate workflow names exist"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }

        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()

        # Create two workflows with same name
        (workflows_dir / "workflow1.json").write_text(json.dumps(sample_workflow))
        (workflows_dir / "workflow2.json").write_text(json.dumps(sample_workflow))

        with pytest.raises(ValueError, match="Duplicate workflow_name"):
            load_and_validate_workflows(templates, workflows_dir)

    def test_load_workflows_invalid_json(self, temp_dir, sample_llm_step_template):
        """Test error when workflow JSON is invalid"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }

        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()

        (workflows_dir / "invalid.json").write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_and_validate_workflows(templates, workflows_dir)

    def test_load_workflows_empty_directory(self, temp_dir, sample_llm_step_template):
        """Test loading from empty workflows directory"""
        from ai_eng.workflows_runner.workflows_types import parse_and_validate_step_template

        templates = {
            "test_llm_step": parse_and_validate_step_template(sample_llm_step_template)
        }

        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()

        workflows = load_and_validate_workflows(templates, workflows_dir)
        assert len(workflows) == 0
