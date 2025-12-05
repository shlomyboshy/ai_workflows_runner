from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, field_validator, model_validator

# Workflows, StepTemplates and Steps in a workflow definition.
# Validation is applied within the object definitions and more validations (between objects) are added in loading code.
# Various validations include (only some of them implemented now):
# - Steps mentioned in inputs/outputs of other steps exist / no orphan steps
# - No cycles (DAG)
# - Fields in inputs are created by initial input or output of previous steps
# - Type checking - output of step has compatible type to input of next step
# - Ensure all possible paths end in a terminal step
# (we can use topological sort of steps by dependencies to ensure steps DAG is valid)

ANY_VALUE = "__any__"
END_NODE = "__end__"


class StepTypes(str, Enum):
    LLM = "llm"
    ML_MODEL = "ml_model"
    CODE_FUNCTION = "code_function"
    DB_READ = "db_read"


class StepTemplateBase(BaseModel):
    """
    Common fields for all step templates.
    """
    template_name: str
    type: StepTypes
    description: Optional[str] = None
    input_fields: List[str]
    output_fields: List[str]

    @field_validator("template_name")
    @classmethod
    def template_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("template_name must not be empty")
        return v

    @field_validator("input_fields", "output_fields")
    @classmethod
    def fields_non_empty(cls, v: List[str], info) -> List[str]:
        if not v:
            raise ValueError(f"{info.field_name} must contain at least one item")
        if len(set(v)) != len(v):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return v

    @model_validator(mode="after")
    def no_overlap_between_input_and_output(self) -> "StepTemplateBase":
        overlap = set(self.input_fields) & set(self.output_fields)
        if overlap:
            raise ValueError(
                f"input_fields and output_fields must not overlap; got duplicates: {overlap}"
            )
        return self


# =======================================================================


class LlmStepTemplate(StepTemplateBase):
    prompt_name: str
    llm_model_name: str
    prompt_version: str

    @field_validator("prompt_name", "llm_model_name", "prompt_version")
    @classmethod
    def non_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v


class MlModelStepTemplate(StepTemplateBase):
    ml_model_name: str
    ml_model_version: str

    @field_validator("ml_model_name", "ml_model_version")
    @classmethod
    def non_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v


class CodeFunctionStepTemplate(StepTemplateBase):
    function_name: str

    @field_validator("function_name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("function_name must not be empty")
        return v


class DbReadStepTemplate(StepTemplateBase):
    db_name: str
    query: str

    @field_validator("db_name", "query")
    @classmethod
    def non_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v

StepTemplate = Union[LlmStepTemplate, MlModelStepTemplate, CodeFunctionStepTemplate, DbReadStepTemplate]

TEMPLATE_TYPE_MAP = {
    StepTypes.LLM: LlmStepTemplate,
    StepTypes.ML_MODEL: MlModelStepTemplate,
    StepTypes.CODE_FUNCTION: CodeFunctionStepTemplate,
    StepTypes.DB_READ: DbReadStepTemplate,
}

# =======================================================================


def parse_and_validate_step_template(raw: dict) -> StepTemplate:
    t = raw.get("type")
    if t not in TEMPLATE_TYPE_MAP:
        raise ValueError(f"Unknown step template type: {t!r}")
    cls = TEMPLATE_TYPE_MAP[t]
    return cls.model_validate(raw)

# =======================================================================

class WorkflowStep(BaseModel):
    """
    A single step instance in a workflow.
    Ties a step_template_name + wiring of inputs/outputs + routing.
    """
    step_name: str  # name in this flow
    step_template_name: str

    input_fields_mapping: Dict[str, str]  # map from concrete fields in this flow to the logical fields in the step template
    output_fields_mapping: Dict[str, str]  # map back from logical step fields to concrete fields in this flow

    # Simple condition map; you can later extend this to richer conditions.
    # Example: {"x": "4", "y": "5"} — only run if those fields have these values.
    input_conditions: Optional[Dict[str, Any]] = None

    output_field_for_next_step_mapping: Optional[str] = None
    next_step_mapping: Optional[Dict[str, str]] = None  # output_field_for_next_step_mapping value -> step_name

    @field_validator("step_name", "step_template_name")
    @classmethod
    def non_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v

    @field_validator("input_fields_mapping", "output_fields_mapping")
    @classmethod
    def fields_non_empty(cls, v: List[str], info) -> Dict[str]:
        if not v:
            raise ValueError(f"{info.field_name} must contain at least one item")
        if len(set(v)) != len(v):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return v

    @model_validator(mode="after")
    def validate_next_step_mapping(self) -> "WorkflowStep":
        if self.next_step_mapping:
            if self.output_field_for_next_step_mapping:
                # check the routing field exists in the node output
                if self.output_field_for_next_step_mapping not in self.output_fields_mapping.keys():
                    raise ValueError(
                        f"output_field_for_next_step_mapping='{self.output_field_for_next_step_mapping}' "
                        f"must be one of output_fields_mapping={self.output_fields_mapping}")
            else:
                # no routing field -> will work by ANY_VALUE - just verify there is routing for ANY_VALUE
                if ANY_VALUE not in self.next_step_mapping:
                    raise ValueError("output_field_for_next_step_mapping is required when next_step_mapping is provided with __any__ value option")

        return self

# =======================================================================


class Workflow(BaseModel):
    workflow_name: str
    version: str
    steps: List[WorkflowStep]

    @field_validator("workflow_name", "version")
    @classmethod
    def non_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v

    @field_validator("steps")
    @classmethod
    def non_empty_steps(cls, v: List[WorkflowStep]) -> List[WorkflowStep]:
        if not v:
            raise ValueError("Workflow must contain at least one step")
        return v

    @model_validator(mode="after")
    def validate_steps(self) -> "Workflow":
        # 1. step_name uniqueness
        step_names = [s.step_name for s in self.steps]
        if len(set(step_names)) != len(step_names):
            raise ValueError("step_name values within a workflow must be unique")

        # 2. next_step_mapping targets must exist
        name_set = set(step_names) | {END_NODE}
        for step in self.steps:
            if step.next_step_mapping:
                for value, target in step.next_step_mapping.items():
                    if target not in name_set:
                        raise ValueError(
                            f"Step '{step.step_name}' has next_step_mapping[{value!r}] -> {target!r}, "
                            f"but no such step_name exists in workflow"
                        )
        return self
