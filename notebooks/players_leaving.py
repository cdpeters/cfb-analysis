import marimo

__generated_with = "0.10.13"
app = marimo.App(
    width="medium",
    css_file="C:\\Users\\cdpet\\Documents\\Post School Coursework\\dev-materials\\configs\\marimo\\theme\\custom-theme.css",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Read Excel File""")
    return


@app.cell(hide_code=True)
def _(mo):
    season = mo.ui.number(start=2028, value=2028, label="Year of Next Season").form()
    season
    return (season,)


@app.cell(hide_code=True)
def _(Path, data_path, mo, pl, season):
    mo.stop(season.value is None, mo.md("**Submit the form to continue.**"))

    input_file_path = Path(data_path / "datasets" / f"{season.value - 1}_team.xlsx")
    output_file_path = Path(data_path / "datasets" / f"{season.value}_team.xlsx")

    if output_file_path.exists():
        print("The file already exists!")
    elif not input_file_path.exists():
        print("The necessary input file does not exist!")
    else:
        # Read in excel file into a dataframe.
        roster = pl.read_excel(input_file_path)

        # Remove seniors.
        roster = roster.filter(pl.col("class") != "SR")

        # Update class value.
        new_class_mapping = {"FR": "SO", "SO": "JR", "JR": "SR"}
        roster = roster.with_columns(pl.col("class").replace(new_class_mapping))

        print(f"Writing dataframe to file\n{output_file_path}")
        roster.write_excel(output_file_path)
    return input_file_path, new_class_mapping, output_file_path, roster


@app.cell
def _():
    import marimo as mo
    import polars as pl
    from pathlib import Path
    return Path, mo, pl


@app.cell
def _(find_project_path):
    # Data directory path.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"
    return (data_path,)


@app.cell
def _(Path):
    def find_project_path(project_name: str) -> Path | None:
        marker_files = [".git", "pyproject.toml"]
        current_path = Path().cwd()
        index = 0

        try:
            # Check current directory.
            if current_path.name == project_name and any(
                (current_path / marker).exists() for marker in marker_files
            ):
                return current_path

            # Check parent directories.
            while True:
                parent = current_path.parents[index]
                if parent.name == project_name and any(
                    (parent / marker).exists() for marker in marker_files
                ):
                    return parent
                index += 1

        except IndexError:
            return None
    return (find_project_path,)


if __name__ == "__main__":
    app.run()
