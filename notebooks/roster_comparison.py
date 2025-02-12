import marimo

__generated_with = "0.11.2"
app = marimo.App(
    width="medium",
    css_file="C:\\Users\\cdpet\\Documents\\Post School Coursework\\dev-materials\\configs\\marimo\\theme\\custom-theme.css",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# Roster Comparison""")
    return


@app.cell(hide_code=True)
def _(mo):
    # Season for analysis.
    _seasons = ["2029"]

    # Form creation. The team and year of next season must be selected and then submitted prior
    # to processing the roster file.
    team_season_form = (
        mo.md("""
        ### Select **Season** for roster comparison

        {season_dropdown}
    """)
        .batch(
            season_dropdown=mo.ui.dropdown(options=_seasons, label="Season"),
        )
        .form(bordered=False)
    )
    team_season_form
    return (team_season_form,)


@app.cell
def _(find_project_path, mo, team_season_form):
    # Stop execution if the form has not been submitted.
    mo.stop(team_season_form.value is None, mo.md("**Submit the form above to continue.**"))

    season = team_season_form.value["season_dropdown"]

    # Stop execution if the form has been submitted but the team and/or season
    # has not been selected.
    mo.stop(
        season is None,
        mo.md(
            "**A season has not been selected. Please select a season and resubmit the form above to continue.**"
        ),
    )

    # Path to the project's `data` directory.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    # Path to the roster excel file based on the team chosen for analysis.
    _roster_file_paths = {
        team: data_path / "datasets" / f"roster_{team}.xlsx"
        for team in ("fresno_state", "san_diego_state", "stanford")
    }

    _roster_file_paths

    # class_enum = pl.Enum(["FR", "SO", "JR", "SR"])
    # # `team_enum` refers to either offense, defense, or special teams.
    # team_enum = pl.Enum(["OFF", "DEF", "ST"])
    # dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    # # Set up the schema overrides for the columns that need it. The `overall_start`
    # # and `overall_end` columns need an override because `polars` does not infer
    # # the column as an integer for roster years that have this data missing.
    # _schema_overrides = {
    #     "class": class_enum,
    #     "position": pl.Categorical,
    #     "group": pl.Categorical,
    #     "secondary_group": pl.Categorical,
    #     "team": team_enum,
    #     "archetype": pl.Categorical,
    #     "dev_trait": dev_trait_enum,
    #     "overall_start": pl.UInt8,
    #     "overall_end": pl.UInt8,
    # }

    # # Create the `roster` dataframe from the excel file.
    # try:
    #     roster = pl.read_excel(
    #         _roster_file_path,
    #         sheet_name=season,
    #         schema_overrides=_schema_overrides,
    #     )
    # except ValueError as e:
    #     print(e)
    #     mo.stop(True, mo.md("**Execution halted.**"))
    return data_path, season


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Appendix""")
    return


@app.cell
def _():
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import polars as pl

    from utilities import find_project_path

    pl.Config.set_tbl_rows(20)
    return Path, alt, find_project_path, mo, pl


if __name__ == "__main__":
    app.run()
