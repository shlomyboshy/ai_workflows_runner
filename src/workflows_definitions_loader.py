from __future__ import annotations
from typing import Dict
import json
from pathlib import Path

from src.workflows_types import StepTemplate, Workflow, parse_and_validate_step_template

DEFAULT_STEPS_DIR = Path(__file__).resolve().parent / "steps"
DEFAULT_WORKFLOWS_DIR = Path(__file__).resolve().parent / "workflows"


def load_and_validate_step_templates(directory: Path | str = DEFAULT_STEPS_DIR) -> Dict[str, StepTemplate]:
    """
    Load and validates all step templates from JSON files in a directory
    Returns:
        dict[template_name, StepTemplate]
    """
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Step templates directory does not exist: {path}")
    templates: Dict[str, StepTemplate] = {}
    for json_path in sorted(path.glob("*.json")):
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        tmpl = parse_and_validate_step_template(raw)
        if tmpl.template_name in templates:
            raise ValueError(f"Duplicate step template_name={tmpl.template_name!r} found in {json_path} (already defined)")
        templates[tmpl.template_name] = tmpl
    return templates


def validate_workflow_against_templates(workflow: Workflow, step_templates: Dict[str, StepTemplate]) -> None:
    """
        validate workflow against step templates.

    Checks:
    - Every step.step_template_name exists in *templates*.
    - step.input_fields_mapping includes exactly the fields needed for template.input_fields
    - step.output_fields_mapping includes exactly the fields needed for template.output_fields
    """
    for step in workflow.steps:
        if step.step_template_name not in step_templates:
            raise ValueError(
                f"Workflow {workflow.workflow_name!r} step {step.step_name!r} "
                f"references unknown step_template_name={step.step_template_name!r}"
            )

        tmpl = step_templates[step.step_template_name]
        if set(step.input_fields_mapping.keys()) != set(tmpl.input_fields):
            raise ValueError(f"Workflow {workflow.workflow_name!r} step {step.step_name!r}: Mismatched input_fields_mapping keys for template {tmpl.template_name!r}. ")

        if set(step.output_fields_mapping.keys()) != set(tmpl.output_fields):
            raise ValueError(f"Workflow {workflow.workflow_name!r} step {step.step_name!r}: Mismatched output_fields_mapping keys for template {tmpl.template_name!r}. ")


def load_and_validate_workflows(templates: Dict[str, StepTemplate], directory: Path | str = DEFAULT_WORKFLOWS_DIR) -> Dict[str, Workflow]:
    """
    Load and validate all workflows from JSON files in *directory*.

    Returns:
        dict[workflow_name, Workflow]
    Also cross-validates each workflow against the given step templates.
    """
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Workflows directory does not exist: {path}")
    workflows: Dict[str, Workflow] = {}
    for json_path in sorted(path.glob("*.json")):
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        wf = Workflow.model_validate(raw)
        if wf.workflow_name in workflows:
            raise ValueError(f"Duplicate workflow_name={wf.workflow_name!r} found in {json_path} (already defined)")

        validate_workflow_against_templates(wf, templates)
        workflows[wf.workflow_name] = wf

    return workflows
