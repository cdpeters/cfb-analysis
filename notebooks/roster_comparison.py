import marimo

__generated_with = "0.11.6"
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

    # Form creation. The year of the current season must be selected prior to
    # processing the roster files.
    season_form = (
        mo.md("""
        ### Select **Season** for roster comparison

        {season_dropdown}
    """)
        .batch(
            season_dropdown=mo.ui.dropdown(options=_seasons, label="Season"),
        )
        .form(bordered=False)
    )
    season_form
    return (season_form,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Load Rosters""")
    return


@app.cell
def _(find_project_path, mo, pl, roster, season_form):
    # Stop execution if the form has not been submitted.
    mo.stop(season_form.value is None, mo.md("**Submit the form above to continue.**"))

    season = season_form.value["season_dropdown"]

    # Stop execution if the form has been submitted but the season has not been
    # selected.
    mo.stop(
        season is None,
        mo.md(
            "**A season has not been selected. Please select a season and resubmit the form above to continue.**"
        ),
    )

    class_enum = pl.Enum(["FR", "SO", "JR", "SR"])
    # `team_enum` refers to either offense, defense, or special teams.
    team_enum = pl.Enum(["OFF", "DEF", "ST"])
    dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    # Set up the schema overrides for the columns that need it. The `overall_start`
    # and `overall_end` columns need an override because `polars` does not infer
    # the column as an integer for roster years that have this data missing.
    _schema_overrides = {
        "class": class_enum,
        "team": team_enum,
        "dev_trait": dev_trait_enum,
        "overall_start": pl.UInt8,
        "overall_end": pl.UInt8,
    }

    # Path to the project's `data` directory.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    # University names.
    _universities = ("fresno_state", "san_diego_state", "stanford")

    # Create the `rosters` dictionary containing all the roster dataframes.
    try:
        rosters = {}

        for university in _universities:
            # Path to the roster excel file for `university`.
            _roster_file_path = data_path / "datasets" / f"roster_{university}.xlsx"

            _roster = pl.read_excel(
                _roster_file_path,
                sheet_name=season,
                schema_overrides=_schema_overrides,
            )
            _roster = _roster.with_columns(pl.lit(university).alias("university"))
            rosters = rosters.append(roster)
    except (ValueError, FileNotFoundError) as e:
        print(e)
        mo.stop(True, mo.md("**Execution halted.**"))
    return (
        class_enum,
        data_path,
        dev_trait_enum,
        rosters,
        season,
        team_enum,
        university,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Combine the Rosters""")
    return


@app.cell
def _(pl, rosters):
    combined_roster = pl.concat([*rosters.values()])

    combined_roster = combined_roster.with_columns(
        [pl.col(["position", "group", "secondary_group", "archetype"]).cast(pl.Categorical)]
    )

    combined_roster
    return (combined_roster,)


@app.cell
def _(alt, pl, university_colors):
    def _create_dev_by_class_df(
        df: pl.DataFrame, dev_trait: str, position: str
    ) -> pl.DataFrame:
        # Filter by `dev_trait` and `position`.
        df = df.filter(
            (pl.col("dev_trait") == dev_trait) & (pl.col("position") == position)
        )

        # Group by class and university and calculate the mean of the `overall_start` column
        # and the count of players.
        df = (
            df.group_by(["class", "university"])
            .agg(
                pl.col("overall_start").mean().alias("avg_overall"),
                pl.len().alias("player_count"),
            )
            .sort("class")
        )
        return df


    def plot_dev_by_class(df: pl.DataFrame, dev_trait: str, position: str = None):
        processed_df = _create_dev_by_class_df(
            df=df, dev_trait=dev_trait, position=position
        )

        custom_colors = {
            university: university_color_dict["color_2"]
            for university, university_color_dict in university_colors.items()
        }

        # Create scatter plot
        chart = (
            alt.Chart(processed_df.to_pandas())
            .mark_circle(opacity=0.6)
            .encode(
                x=alt.X("class:N", title="Class Standing", sort=["FR", "SO", "JR", "SR"]),
                y=alt.Y(
                    "avg_overall:Q",
                    title="Average Overall Rating",
                    scale=alt.Scale(domain=[50, 100]),
                ),
                color=alt.Color(
                    "university:N",
                    title="University",
                    scale=alt.Scale(
                        domain=list(custom_colors.keys()),
                        range=list(custom_colors.values()),
                    ),
                ),
                size=alt.Size(
                    "player_count:Q",
                    title="Number of Players",
                    scale=alt.Scale(range=[100, 400]),
                    legend=alt.Legend(format="d"),
                ),
                tooltip=[
                    "university",
                    "class",
                    alt.Tooltip("avg_overall:Q", format=".1f"),
                    alt.Tooltip("player_count:Q", format="d", title="Number of Players"),
                ],
            )
            .properties(
                width=500,
                height=300,
                title=f"Average Overall Rating by Class - {dev_trait.title()} Development"
                + (f" ({position})" if position else ""),
            )
        )

        return chart
    return (plot_dev_by_class,)


@app.cell
def _(combined_roster, mo, plot_dev_by_class):
    chart = plot_dev_by_class(combined_roster, dev_trait="star", position="WR")
    mo.ui.altair_chart(chart)
    return (chart,)


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


@app.cell
def _():
    university_colors = {
        "fresno_state": {
            "color_1": "#1e40af",
            "color_2": "#3b82f6",
            "color_3": "#93c5fd",
            "color_4": "#dbeafe",
        },
        "san_diego_state": {
            "color_1": "#09090b",
            "color_2": "#52525b",
            "color_3": "#a1a1aa",
            "color_4": "#e4e4e7",
        },
        "stanford": {
            "color_1": "#991b1b",
            "color_2": "#ef4444",
            "color_3": "#fca5a5",
            "color_4": "#fee2e2",
        },
    }
    return (university_colors,)


if __name__ == "__main__":
    app.run()
