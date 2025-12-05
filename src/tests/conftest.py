"""
Pytest fixtures and configuration for workflow tests
"""
import json
import pytest
from pathlib import Path
from typing import Dict, Any
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_llm_step_template() -> Dict[str, Any]:
    """Sample LLM step template for testing"""
    return {
        "template_name": "test_llm_step",
        "type": "llm",
        "description": "Test LLM step",
        "input_fields": ["input_text"],
        "output_fields": ["output_text"],
        "prompt_name": "test_prompt",
        "llm_model_name": "gpt-4",
        "prompt_version": "v1.0"
    }


@pytest.fixture
def sample_code_step_template() -> Dict[str, Any]:
    """Sample code function step template for testing"""
    return {
        "template_name": "test_code_step",
        "type": "code_function",
        "description": "Test code function step",
        "input_fields": ["raw_input"],
        "output_fields": ["processed_output"],
        "function_name": "test_function"
    }


@pytest.fixture
def sample_ml_step_template() -> Dict[str, Any]:
    """Sample ML model step template for testing"""
    return {
        "template_name": "test_ml_step",
        "type": "ml_model",
        "description": "Test ML model step",
        "input_fields": ["features"],
        "output_fields": ["prediction", "confidence"],
        "ml_model_name": "test_model",
        "ml_model_version": "v1.0"
    }


@pytest.fixture
def sample_db_step_template() -> Dict[str, Any]:
    """Sample DB read step template for testing"""
    return {
        "template_name": "test_db_step",
        "type": "db_read",
        "description": "Test DB read step",
        "input_fields": ["user_id"],
        "output_fields": ["user_name", "user_email"],
        "db_name": "test_db",
        "query": "SELECT * FROM users WHERE id = {user_id}"
    }


@pytest.fixture
def sample_workflow(sample_llm_step_template) -> Dict[str, Any]:
    """Sample workflow definition for testing"""
    return {
        "workflow_name": "test_workflow",
        "version": "1.0.0",
        "steps": [
            {
                "step_name": "step1",
                "step_template_name": "test_llm_step",
                "input_fields_mapping": {
                    "input_text": "initial_input"
                },
                "output_fields_mapping": {
                    "output_text": "step1_output"
                }
            }
        ]
    }


@pytest.fixture
def sample_workflow_with_conditional(sample_llm_step_template, sample_code_step_template) -> Dict[str, Any]:
    """Sample workflow with conditional routing"""
    return {
        "workflow_name": "test_workflow_conditional",
        "version": "1.0.0",
        "steps": [
            {
                "step_name": "analyze",
                "step_template_name": "test_llm_step",
                "input_fields_mapping": {
                    "input_text": "initial_input"
                },
                "output_fields_mapping": {
                    "output_text": "decision"
                },
                "output_field_for_next_step_mapping": "output_text",
                "next_step_mapping": {
                    "yes": "process_yes",
                    "no": "__end__"
                }
            },
            {
                "step_name": "process_yes",
                "step_template_name": "test_code_step",
                "input_fields_mapping": {
                    "raw_input": "decision"
                },
                "output_fields_mapping": {
                    "processed_output": "final_output"
                }
            }
        ]
    }


@pytest.fixture
def create_temp_step_templates(temp_dir, sample_llm_step_template, sample_code_step_template):
    """Create temporary step template files"""
    steps_dir = temp_dir / "steps"
    steps_dir.mkdir()

    # Write LLM template
    (steps_dir / "llm_step.json").write_text(json.dumps(sample_llm_step_template))

    # Write code template
    (steps_dir / "code_step.json").write_text(json.dumps(sample_code_step_template))

    return steps_dir


@pytest.fixture
def create_temp_workflow(temp_dir, sample_workflow):
    """Create temporary workflow file"""
    workflows_dir = temp_dir / "workflows"
    workflows_dir.mkdir()

    (workflows_dir / "test_workflow.json").write_text(json.dumps(sample_workflow))

    return workflows_dir
