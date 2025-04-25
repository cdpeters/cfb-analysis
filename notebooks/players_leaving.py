import marimo

__generated_with = "0.11.21"
app = marimo.App(
    width="medium",
    css_file="",
    html_head_file="",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Process Players Leaving on Next Season's Roster""")
    return


@app.cell(hide_code=True)
def _(mo):
    _seasons = [str(year) for year in range(2027, 2041)]

    # Form creation. The year of the current season must be selected and then submitted
    # prior to processing the roster files.
    current_season_form = (
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
    current_season_form
    return (current_season_form,)


@app.cell(hide_code=True)
def _(
    create_next_season_initial_roster,
    current_season_form,
    find_project_path,
    mo,
    schema_overrides,
):
    # Stop execution if the form has not been submitted.
    mo.stop(
        current_season_form.value is None, mo.md("**Submit the form above to continue.**")
    )

    _current_season = current_season_form.value["current_season_dropdown"]

    # Stop execution if the form has been submitted but the current season has
    # not been selected.
    mo.stop(
        not _current_season,
        mo.md(
            "**The current season has not been selected. Please make sure to select the current season and then resubmit the form above to continue.**"
        ),
    )

    # Path to the project's `data` directory.
    _project_path = find_project_path("cfb-analysis")
    _data_path = _project_path / "data"

    for university in ("fresno_state", "san_diego_state", "stanford"):
        create_next_season_initial_roster(
            data_path=_data_path,
            university=university,
            current_season=_current_season,
            schema_overrides=schema_overrides,
        )
    return (university,)


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
        university: str,
        current_season: int,
        schema_overrides: dict[str, PolarsDataType],
    ) -> None:
        """Create next season's intial roster for `university`.

        Process players leaving due to graduation and also advance the class standing of
        each player remaining.

        Parameters
        ----------
        data_path : Path
            Path to the project's data directory.
        university : str
            The university being processed. Underscore separated.
        current_season : int
            Current season integer.
        schema_overrides : dict[str, PolarsDataType]
            Data types for each column.
        """
        roster_file_path = data_path / "datasets" / f"roster_{university}.xlsx"

        # Create the `rosters` dictionary containing all roster sheets from the excel
        # file.
        rosters = pl.read_excel(
            roster_file_path, sheet_id=0, schema_overrides=schema_overrides
        )

        next_season = str(int(current_season) + 1)

        # Create `next_season` initial roster from `current_season` roster with the
        # seniors filtered out.
        rosters[next_season] = rosters[current_season].filter(pl.col("class") != "SR")

        # Progress the `class` standing for each player.
        new_class_mapping = {"FR": "SO", "SO": "JR", "JR": "SR"}
        rosters[next_season] = rosters[next_season].with_columns(
            pl.col("class").replace(new_class_mapping)
        )

        # Reset `overall_start` and `overall_end` columns to empty.
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
