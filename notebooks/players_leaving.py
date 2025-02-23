import marimo

__generated_with = "0.11.8"
app = marimo.App(
    width="medium",
    css_file="C:\\Users\\cdpet\\Documents\\Post School Coursework\\dev-materials\\configs\\marimo\\theme\\custom-theme.css",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Process Players Leaving on Next Season's Roster""")
    return


@app.cell(hide_code=True)
def _(mo):
    _seasons = [str(year) for year in range(2027, 2041)]

    # Form creation. The team and year of next season must be selected and then submitted prior
    # to processing the roster file.
    team_season_form = (
        mo.md("""
        ### Select the **Current Season** to create next year's initial rosters
        - All 3 university team rosters will be processed at the same time
        - This action removes seniors and advances all player's `class` value
        - The following roster changes are handled manually:
            - current season red shirts
            - transferring or drafted players
            - incoming recruits

        {current_season_dropdown}
    """)
        .batch(
            current_season_dropdown=mo.ui.dropdown(
                options=_seasons, label="Current Season"
            ),
        )
        .form(bordered=False)
    )
    team_season_form
    return (team_season_form,)


@app.cell
def _(
    create_next_season_initial_roster,
    find_project_path,
    mo,
    schema_overrides,
    team_season_form,
):
    # Stop execution if the form has not been submitted.
    mo.stop(team_season_form.value is None, mo.md("**Submit the form above to continue.**"))

    _current_season = team_season_form.value["current_season_dropdown"]

    # Stop execution if the form has been submitted but the current season has
    # not been selected.
    mo.stop(
        not _current_season,
        mo.md(
            "**The current season has not been selected. Please make sure to select the current season and then resubmit the form above to continue.**"
        ),
    )

    _next_season = str(int(_current_season) + 1)

    # Path to the project's `data` directory.
    _project_path = find_project_path("cfb-analysis")
    _data_path = _project_path / "data"

    for team in ("fresno_state", "san_diego_state", "stanford"):
        create_next_season_initial_roster(
            data_path=_data_path,
            team=team,
            current_season=_current_season,
            next_season=_next_season,
            schema_overrides=schema_overrides,
        )
    return (team,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Appendix""")
    return


@app.cell
def _():
    from pathlib import Path

    import marimo as mo
    import polars as pl
    from xlsxwriter import Workbook

    from utilities import find_project_path, schema_overrides
    return Path, Workbook, find_project_path, mo, pl, schema_overrides


@app.cell
def _(Path, Workbook, pl):
    PolarsDataType = pl.DataType | type[pl.DataType]


    def create_next_season_initial_roster(
        data_path: Path,
        team: str,
        current_season: int,
        next_season: int,
        schema_overrides: dict[str, PolarsDataType],
    ) -> None:
        # Path to the roster excel file based on the team chosen for analysis.
        roster_file_path = data_path / "datasets" / f"roster_{team}.xlsx"

        # Create the `rosters` dictionary containing all roster sheets from the excel
        # file.
        rosters = pl.read_excel(
            roster_file_path, sheet_id=0, schema_overrides=schema_overrides
        )

        # Create a new dictionary entry containing a copy of the current season's roster
        # with the seniors removed. This forms the basis for next season's roster.
        rosters[next_season] = rosters[current_season].filter(pl.col("class") != "SR")

        # Progress the `class` value for each player in next season's roster.
        new_class_mapping = {"FR": "SO", "SO": "JR", "JR": "SR"}
        rosters[next_season] = rosters[next_season].with_columns(
            pl.col("class").replace(new_class_mapping)
        )

        rosters[next_season] = rosters[next_season].with_columns(
            pl.lit(None).cast(pl.Int64).alias("overall_start"),
            pl.lit(None).cast(pl.Int64).alias("overall_end"),
        )

        # Write any previous rosters, the current season, and next season's roster to an
        # excel file of the same name.
        print(
            f"Writing roster dataframe to new sheet '{next_season}' within the excel file at:\n{roster_file_path}",
            end="\n\n",
        )
        with Workbook(roster_file_path) as rfp:
            for season, season_roster in rosters.items():
                season_roster.write_excel(rfp, worksheet=season)
    return PolarsDataType, create_next_season_initial_roster


if __name__ == "__main__":
    app.run()
