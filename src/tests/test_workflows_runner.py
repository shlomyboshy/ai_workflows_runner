"""
Unit tests for workflows_runner.py
"""
import pytest
from unittest.mock import Mock, patch

from ai_eng.workflows_runner.workflows_runner import WorkflowRunner


class TestWorkflowRunner:
    """Tests for WorkflowRunner class"""

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_init_loads_workflows(self, mock_build_graph):
        """Test that initialization loads workflow graphs"""
        mock_build_graph.return_value = {
            "test_workflow": Mock()
        }

        runner = WorkflowRunner()

        assert runner.workflow_graphs is not None
        assert len(runner.workflow_graphs) == 1
        assert "test_workflow" in runner.workflow_graphs
        mock_build_graph.assert_called_once()

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_init_handles_empty_workflows(self, mock_build_graph):
        """Test initialization with no workflows"""
        mock_build_graph.return_value = {}

        runner = WorkflowRunner()

        assert runner.workflow_graphs is not None
        assert len(runner.workflow_graphs) == 0

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_success(self, mock_build_graph):
        """Test successful workflow execution"""
        # Setup mock graph
        mock_graph = Mock()
        mock_graph.invoke.return_value = {"result": "success"}
        mock_build_graph.return_value = {
            "test_workflow": mock_graph
        }

        runner = WorkflowRunner()
        initial_state = {"input": "test"}

        result = runner.run_flow("test_workflow", initial_state)

        assert result == {"result": "success"}
        mock_graph.invoke.assert_called_once_with(initial_state)

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_not_found(self, mock_build_graph, capsys):
        """Test running non-existent workflow"""
        mock_build_graph.return_value = {
            "existing_workflow": Mock()
        }

        runner = WorkflowRunner()

        result = runner.run_flow("non_existent_workflow", {})

        assert result is None

        # Check that error message was printed
        captured = capsys.readouterr()
        assert "Workflow 'non_existent_workflow' not found" in captured.out
        assert "existing_workflow" in captured.out

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_with_complex_state(self, mock_build_graph):
        """Test workflow execution with complex initial state"""
        mock_graph = Mock()
        mock_graph.invoke.return_value = {
            "output1": "value1",
            "output2": "value2",
            "output3": 123
        }
        mock_build_graph.return_value = {
            "test_workflow": mock_graph
        }

        runner = WorkflowRunner()
        initial_state = {
            "field1": "value1",
            "field2": [1, 2, 3],
            "field3": {"nested": "data"}
        }

        result = runner.run_flow("test_workflow", initial_state)

        assert result is not None
        assert "output1" in result
        assert "output2" in result
        assert "output3" in result
        mock_graph.invoke.assert_called_once_with(initial_state)

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_empty_state(self, mock_build_graph):
        """Test workflow execution with empty initial state"""
        mock_graph = Mock()
        mock_graph.invoke.return_value = {"result": "executed"}
        mock_build_graph.return_value = {
            "test_workflow": mock_graph
        }

        runner = WorkflowRunner()

        result = runner.run_flow("test_workflow", {})

        assert result == {"result": "executed"}
        mock_graph.invoke.assert_called_once_with({})

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_graph_execution_error(self, mock_build_graph):
        """Test handling of errors during workflow execution"""
        mock_graph = Mock()
        mock_graph.invoke.side_effect = Exception("Execution error")
        mock_build_graph.return_value = {
            "test_workflow": mock_graph
        }

        runner = WorkflowRunner()

        with pytest.raises(Exception, match="Execution error"):
            runner.run_flow("test_workflow", {"input": "test"})

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_multiple_workflows(self, mock_build_graph):
        """Test runner with multiple workflows"""
        mock_graph1 = Mock()
        mock_graph1.invoke.return_value = {"result": "workflow1"}

        mock_graph2 = Mock()
        mock_graph2.invoke.return_value = {"result": "workflow2"}

        mock_build_graph.return_value = {
            "workflow1": mock_graph1,
            "workflow2": mock_graph2
        }

        runner = WorkflowRunner()

        # Run first workflow
        result1 = runner.run_flow("workflow1", {"input": "test1"})
        assert result1 == {"result": "workflow1"}

        # Run second workflow
        result2 = runner.run_flow("workflow2", {"input": "test2"})
        assert result2 == {"result": "workflow2"}

        # Verify both were called
        mock_graph1.invoke.assert_called_once()
        mock_graph2.invoke.assert_called_once()

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_run_flow_returns_none_on_error(self, mock_build_graph):
        """Test that run_flow returns None for non-existent workflow"""
        mock_build_graph.return_value = {}

        runner = WorkflowRunner()
        result = runner.run_flow("missing_workflow", {})

        assert result is None

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_workflow_graphs_attribute(self, mock_build_graph):
        """Test that workflow_graphs attribute is accessible"""
        mock_graphs = {
            "wf1": Mock(),
            "wf2": Mock(),
            "wf3": Mock()
        }
        mock_build_graph.return_value = mock_graphs

        runner = WorkflowRunner()

        assert hasattr(runner, 'workflow_graphs')
        assert runner.workflow_graphs == mock_graphs
        assert len(runner.workflow_graphs) == 3

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_init_with_build_graph_exception(self, mock_build_graph):
        """Test initialization when build_run_graph raises exception"""
        mock_build_graph.side_effect = FileNotFoundError("Templates not found")

        with pytest.raises(FileNotFoundError):
            WorkflowRunner()


class TestWorkflowRunnerIntegration:
    """Integration-style tests for WorkflowRunner"""

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_sequential_workflow_execution(self, mock_build_graph):
        """Test executing the same workflow multiple times"""
        execution_count = 0

        def mock_invoke(state):
            nonlocal execution_count
            execution_count += 1
            return {"execution_number": execution_count, "input": state.get("input")}

        mock_graph = Mock()
        mock_graph.invoke = mock_invoke
        mock_build_graph.return_value = {
            "test_workflow": mock_graph
        }

        runner = WorkflowRunner()

        # Execute multiple times
        result1 = runner.run_flow("test_workflow", {"input": "first"})
        result2 = runner.run_flow("test_workflow", {"input": "second"})
        result3 = runner.run_flow("test_workflow", {"input": "third"})

        assert result1["execution_number"] == 1
        assert result2["execution_number"] == 2
        assert result3["execution_number"] == 3
        assert execution_count == 3

    @patch('ai_eng.workflows_runner.workflows_runner.build_run_graph')
    def test_state_isolation_between_runs(self, mock_build_graph):
        """Test that state is isolated between workflow runs"""
        mock_graph = Mock()
        mock_graph.invoke.side_effect = lambda state: state.copy()
        mock_build_graph.return_value = {
            "test_workflow": mock_graph
        }

        runner = WorkflowRunner()

        # Run with different states
        state1 = {"key": "value1"}
        state2 = {"key": "value2"}

        result1 = runner.run_flow("test_workflow", state1)
        result2 = runner.run_flow("test_workflow", state2)

        # Results should be different
        assert result1["key"] == "value1"
        assert result2["key"] == "value2"

        # Original states should not be modified
        assert state1 == {"key": "value1"}
        assert state2 == {"key": "value2"}
