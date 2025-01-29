from pathlib import Path
import marimo as mo
from marimo._output.md import _md

def find_project_path(project_name: str) -> Path:
    marker_files = [".git", "pyproject.toml"]
    current_path = Path().cwd()

    # Check current directory
    if current_path.name == project_name and any(
        (current_path / marker).exists() for marker in marker_files
    ):
        return current_path

    # Check parent directories
    for parent in current_path.parents:
        if parent.name == project_name and any(
            (parent / marker).exists() for marker in marker_files
        ):
            return parent

    raise FileNotFoundError(
        "Could not find a project directory containing either a .git or pyproject.toml file."
    )

def create_dataframe_markdown(frame_name: str) -> _md:
    return mo.md(
        f"""<br>
        *`{frame_name}`*
    """
    )
