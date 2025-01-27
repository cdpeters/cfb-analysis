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
def _(Path, Workbook, find_project_path, mo, pl, team_season_form):
    mo.stop(team_season_form.value is None, mo.md("**Submit the form above to continue.**"))

    # Data directory path.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    roster_file_path = Path(
        data_path / "datasets" / f"roster_{team_season_form.value['team_dropdown']}.xlsx"
    )

    current_season = team_season_form.value["current_season_dropdown"]
    next_season = str(int(current_season) + 1)

    class_enum = pl.Enum(["FR", "SO", "JR", "SR"])
    team_enum = pl.Enum(["OFF", "DEF", "ST"])
    dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    # Set up the schema overrides for the columns that need it. The `overall` column needs
    # an override because `polars` does not infer the column as an integer for the `2027`
    # season since all the values are #N/A in Excel.
    _schema_overrides = {
        "class": class_enum,
        "position": pl.Categorical,
        "group": pl.Categorical,
        "secondary_group": pl.Categorical,
        "team": team_enum,
        "archetype": pl.Categorical,
        "dev_trait": dev_trait_enum,
        "overall": pl.UInt8,
    }

    # Read in excel file into a dataframe.
    rosters = pl.read_excel(
        roster_file_path, sheet_id=0, schema_overrides=_schema_overrides
    )

    # Remove seniors.
    rosters[next_season] = rosters[current_season].filter(pl.col("class") != "SR")

    # Update class value.
    new_class_mapping = {"FR": "SO", "SO": "JR", "JR": "SR"}
    rosters[next_season] = rosters[next_season].with_columns(
        pl.col("class").replace(new_class_mapping)
    )

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
        roster_file_path,
        rosters,
        season,
        season_roster,
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
    return Path, Workbook, mo, pl


@app.cell(hide_code=True)
def _(mo):
    mo.md("""### Helper Functions""")
    return


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
            print(
                "Could not find a project directory containing either a .git or pyproject.toml file."
            )
    return (find_project_path,)


if __name__ == "__main__":
    app.run()
