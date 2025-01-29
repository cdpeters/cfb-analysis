import marimo

__generated_with = "0.10.17"
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
    _teams = {
        "Stanford": "stanford",
        # "Fresno State": "fresno_state",
        # "San Diego State": "san_diego_state",
    }

    _seasons = [str(year) for year in range(2027, 2041)]

    # Form creation. The team and year of next season must be selected and then submitted prior
    # to processing the roster file.
    team_season_form = (
        mo.md("""
        ### Select **Team** and **Current Season** to create next year's initial roster
        - This action removes seniors and advances all player's class value
        - The following roster changes are handled manually:
            - current season red shirts
            - transferring or drafted players
            - incoming recruits

        {team_dropdown}

        {current_season_dropdown}
    """)
        .batch(
            team_dropdown=mo.ui.dropdown(options=_teams, label="Team"),
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
    Workbook,
    find_project_path,
    mo,
    pl,
    roster_file_path,
    team_season_form,
):
    # Stop execution if the form has not been submitted.
    mo.stop(team_season_form.value is None, mo.md("**Submit the form above to continue.**"))

    team = team_season_form.value["team_dropdown"]
    current_season = team_season_form.value["season_dropdown"]
    next_season = str(int(current_season) + 1)

    # Stop execution if the form has been submitted but the team and/or season
    # has not been selected.
    mo.stop(
        any(x is None for x in (team, current_season)),
        mo.md(
            "**Either the team, the season, or both have not been selected. Please make sure both have been selected and then resubmit the form above to continue.**"
        ),
    )

    # Path to the project's `data` directory.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    # Path to the roster excel file based on the team chosen for analysis.
    _roster_file_path = data_path / "datasets" / f"roster_{team}.xlsx"

    class_enum = pl.Enum(["FR", "SO", "JR", "SR"])
    # This refers to either offense, defense, or special teams.
    team_enum = pl.Enum(["OFF", "DEF", "ST"])
    dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    # Set up the schema overrides for the columns that need it. The `overall_start`
    # and `overall_end` columns need an override because `polars` does not infer
    # the column as an integer for roster years that have this data missing.
    _schema_overrides = {
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

    # Create the `rosters` dictionary containing all roster sheets from the excel
    # file.
    rosters = pl.read_excel(
        _roster_file_path, sheet_id=0, schema_overrides=_schema_overrides
    )

    # Create a new dictionary entry containing a copy of the current season's roster
    # with the seniors removed. This forms the basis for next season's roster.
    rosters[next_season] = rosters[current_season].filter(pl.col("class") != "SR")

    # Progress the `class` value for each player in next season's roster.
    new_class_mapping = {"FR": "SO", "SO": "JR", "JR": "SR"}
    rosters[next_season] = rosters[next_season].with_columns(
        pl.col("class").replace(new_class_mapping)
    )

    # Write any previous rosters, the current season, and next season's roster to an
    # excel file of the same name.
    print(
        f"Writing roster dataframe to new sheet '{next_season}' within the excel file at:\n{roster_file_path}"
    )
    with Workbook(roster_file_path) as rfp:
        for season, season_roster in rosters.items():
            season_roster.write_excel(rfp, worksheet=season)
    return (
        class_enum,
        current_season,
        data_path,
        dev_trait_enum,
        new_class_mapping,
        next_season,
        rfp,
        rosters,
        season,
        season_roster,
        team,
        team_enum,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Appendix""")
    return


@app.cell
def _():
    import marimo as mo
    import polars as pl
    from pathlib import Path
    from xlsxwriter import Workbook

    from utilities import find_project_path
    return Path, Workbook, find_project_path, mo, pl


if __name__ == "__main__":
    app.run()
