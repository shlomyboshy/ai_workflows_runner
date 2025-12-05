# Workflows Runner Tests

This directory contains unit tests for the workflows_runner module.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                              # Shared fixtures
├── test_workflows_definitions_loader.py     # Tests for workflow loading
├── test_workflows_run_graph_builder.py      # Tests for graph building
└── test_workflows_runner.py                 # Tests for workflow runner
```

## Running Tests

### Run all tests
```bash
cd ai_eng/workflows_runner
pytest
```

### Run specific test file
```bash
pytest tests/test_workflows_runner.py
```

### Run specific test class
```bash
pytest tests/test_workflows_runner.py::TestWorkflowRunner
```

### Run specific test
```bash
pytest tests/test_workflows_runner.py::TestWorkflowRunner::test_run_flow_success
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run with verbose output
```bash
pytest -v
```

### Run only unit tests
```bash
pytest -m unit
```

### Run tests matching a pattern
```bash
pytest -k "test_load"
```

## Test Coverage

View coverage report:
```bash
# Generate HTML report
pytest --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Writing Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>_<scenario>`

### Using Fixtures
Shared fixtures are defined in `conftest.py`:
```python
def test_my_function(sample_workflow, temp_dir):
    # Use fixtures in your test
    pass
```

### Mocking
Use pytest-mock for mocking:
```python
def test_with_mock(mocker):
    mock_func = mocker.patch('module.function')
    mock_func.return_value = "mocked"
```

## Test Categories

### Unit Tests
Test individual functions and methods in isolation.

**Example:**
```python
def test_create_state_schema():
    # Test a single function
    pass
```

### Integration Tests
Test interaction between components.

**Example:**
```python
@pytest.mark.integration
def test_end_to_end_workflow():
    # Test full workflow execution
    pass
```

## Continuous Integration

Tests are run automatically on:
- Pull requests
- Commits to main branch
- Pre-deployment

## Troubleshooting

### Import Errors
If you get import errors, ensure you're in the correct directory:
```bash
cd ai_eng/workflows_runner
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Missing Dependencies
Install test dependencies:
```bash
pip install -r requirements.txt
```

### Fixture Not Found
Make sure `conftest.py` is in the tests directory and properly loaded.

## Best Practices

1. **Test one thing at a time** - Each test should verify a single behavior
2. **Use descriptive names** - Test names should explain what they test
3. **Arrange-Act-Assert** - Structure tests with setup, execution, and verification
4. **Use fixtures** - Reuse common test setup
5. **Mock external dependencies** - Isolate code under test
6. **Test edge cases** - Include tests for error conditions
7. **Keep tests fast** - Unit tests should run quickly
8. **Don't test implementation details** - Test behavior, not internals

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Python Testing with pytest](https://pragprog.com/titles/bopytest2/python-testing-with-pytest-second-edition/)
