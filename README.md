# ai_workflows_runner
Platform for running AI and code based workflows created dynamically 

Implementation of a platform for running AI workflows (with some stubs).
The platform is designed to manage and execute complex workflows that involve multiple AI models and data processing steps.

The main to run is in workflows_runner.py, which provides the core functionality for executing workflows.

The most interesting files are:
workflows_runner.py
workflows_definitions_loader.py
workflows_run_graph_builder.py
workflow_types.py
and the workflows/ and step_templates/ folders

The platform reads json files for workflows and step templates (in workflows_definitions_loader.py)
dynamically builds a LangGraph graph for each flow (in workflows_run_graph_builder.py)
(including a visual display of the graph done in graph_visualization.py)
and runs the graph over the input data provided.

Its nice to view the workflow and step templates json files in their directories
(and see how they can easily be created dynamically from a UI).
Start with:
workflows/patient_call_analysis_flow.json

flow_request_handler.py - a rabbit queue message handler that runs a flow
you can test it with: message_queue/send_workflow_request.py

Technically:

requirements.txt lists the dependencies (libraries) needed to run the platform.

To run it:
Create a virtual environment
run: pip install -r requirements.txt
run: python workflows_runner.py

unit tests exists in the tests/ folder

I used claude-code and gpt5 interface to help me write this code.

To add in the future:
- Replace stubs with real implementations
- Add input sanitization, authentication, more error handling, more validations on the workflow, configuration management
- Store the data in a DB (workflows, steps, prompts etc)
