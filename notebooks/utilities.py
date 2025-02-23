from pathlib import Path

import marimo as mo
from marimo._output.md import _md
import polars as pl

class_enum = pl.Enum(["FR", "SO", "JR", "SR"])
# This refers to either offense, defense, or special teams.
team_enum = pl.Enum(["OFF", "DEF", "ST"])
dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

# Set up the schema overrides for the columns that need it. The `overall_start`
# and `overall_end` columns need an override because `polars` does not infer
# the column as an integer for roster years that have this data missing.
schema_overrides = {
    "class": class_enum,
    "position": pl.Categorical,
    "group": pl.Categorical,
    "secondary_group": pl.Categorical,
    "team": team_enum,
    "archetype": pl.Categorical,
    "dev_trait": dev_trait_enum,
    "overall_start": pl.UInt8,
    "overall_end": pl.UInt8,
}

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
