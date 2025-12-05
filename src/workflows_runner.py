from src.workflows_run_graph_builder import build_run_graph


class WorkflowRunner(object):

    def __init__(self):
        self.workflow_graphs = build_run_graph()

    def run_flow(self, flow_name: str, initial_state: dict):
        try:
            if flow_name in self.workflow_graphs:
                graph = self.workflow_graphs[flow_name]
                flow_output = graph.invoke(initial_state) # we can add: @traceable(name="agents_executor") for trace in LangSmith for example
                return flow_output
            else:
                print(f"Workflow '{flow_name}' not found. Available workflows: {list(self.workflow_graphs.keys())}")
                return None
        except Exception as ex:
            print(f"Error running workflow '{flow_name}': {str(ex)}")


if __name__ == "__main__":
    runner = WorkflowRunner()

    # Example call transcript
    sample_call_transcript = """
    Nurse: Hello, this is Nurse Sarah calling from the clinic. May I speak with the patient?
    Patient: Yes, this is John speaking. Patient ID 12345.
    Nurse: Thank you John. I'm calling to follow up on your recent appointment. How are you feeling?
    Patient: I'm still having some pain, it's quite frustrating actually.
    Nurse: I understand. Based on what you're describing, I think we should schedule a home visit for a more thorough examination.
    Patient: That would be helpful, thank you.
    Nurse: Great, we'll arrange that. Is there anything else I can help you with today?
    Patient: No, that's all. Thank you for calling.
    Nurse: You're welcome. Take care!
    """

    # Run the patient call analysis workflow
    flow_initial_state = {"call_transcript": sample_call_transcript}
    # possibly add Input sanitization, authentication,...
    result = runner.run_flow("patient_call_analysis_flow", flow_initial_state)
    print(result)
