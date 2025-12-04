import webbrowser
from pathlib import Path


def display_mermaid_diagram(mermaid_code: str, workflow_name: str, output_dir: str = "workflow_diagrams", auto_open: bool = False) -> str:
    """
    Save Mermaid diagram code to an HTML file that can be opened in a browser.

    Args:
        mermaid_code: The Mermaid syntax diagram code
        workflow_name: Name of the workflow
        output_dir: Directory to save the HTML file
        auto_open: If True, automatically open the HTML file in the default browser

    Returns:
        Path to the saved HTML file
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # HTML template with Mermaid.js for rendering
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{workflow_name} - Workflow Diagram</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .mermaid {{
            background-color: white;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{workflow_name} Workflow</h1>
        <div class="mermaid">
{mermaid_code}
        </div>
    </div>
</body>
</html>"""

    # Save to file
    output_path = Path(output_dir) / f"{workflow_name}_diagram.html"
    output_path.write_text(html_content, encoding='utf-8')

    abs_path = str(output_path.absolute())

    # Optionally open in browser
    if auto_open:
        webbrowser.open(f'file://{abs_path}')

    return abs_path
