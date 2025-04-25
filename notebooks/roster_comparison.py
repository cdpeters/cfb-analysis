import marimo

__generated_with = "0.11.21"
app = marimo.App(
    width="medium",
    css_file="",
    html_head_file="",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# Roster Comparison""")
    return


@app.cell(hide_code=True)
def _(mo):
    # Season for analysis.
    _seasons = ["2029", "2030"]

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
    mo.md(r"""### Load Rosters and Combine Them""")
    return


@app.cell
def _(find_project_path, mo, pl, season_form):
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
    # teameνmteam_enum refers to either offense, defense, or special teams.
    team_enum = pl.Enum(["OFF", "DEF", "ST"])
    dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    # Set up the schema overrides for the columns that need it. The overall⋆toverall_start
    # and overallendoverall_end columns need an override because polarspolars does not infer
    # the column as an integer for roster years that have this data missing.
    _schema_overrides = {
        "class": class_enum,
        "team": team_enum,
        "dev_trait": dev_trait_enum,
        "overall_start": pl.UInt8,
        "overall_end": pl.UInt8,
    }

    # Path to the project's datadata directory.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    # Create the rostersrosters dictionary containing all the roster dataframes.
    try:
        combined_roster = pl.DataFrame()

        for university in ("fresno_state", "san_diego_state", "stanford"):
            # Path to the roster excel file for universityuniversity.
            _roster_file_path = data_path / "datasets" / f"roster_{university}.xlsx"

            if combined_roster.is_empty():
                combined_roster = pl.read_excel(
                    _roster_file_path,
                    sheet_name=season,
                    schema_overrides=_schema_overrides,
                )
                combined_roster = combined_roster.with_columns(
                    pl.lit(university).alias("university")
                )
            else:
                _roster = pl.read_excel(
                    _roster_file_path,
                    sheet_name=season,
                    schema_overrides=_schema_overrides,
                )
                _roster = _roster.with_columns(pl.lit(university).alias("university"))
                combined_roster = pl.concat([combined_roster, _roster])
    except (ValueError, FileNotFoundError) as e:
        print(e)
        mo.stop(True, mo.md("**Execution halted.**"))

    combined_roster = combined_roster.with_columns(
        [pl.col(["position", "group", "secondary_group", "archetype"]).cast(pl.Categorical)]
    )

    combined_roster
    return (
        class_enum,
        combined_roster,
        data_path,
        dev_trait_enum,
        season,
        team_enum,
        university,
    )


@app.cell
def _(combined_roster, pl):
    # df = combined_roster.filter((pl.col("class") == "FR") & (~pl.col("red_shirt")))
    # df = df.group_by(["university", "dev_trait"]).agg(pl.len().alias("count"))
    df = combined_roster.group_by(["university", "dev_trait"]).agg(pl.len().alias("count"))
    df = df.pivot(on="dev_trait", values="count")
    df = df.select(["university", "normal", "impact", "star", "elite"])
    df = df.with_columns(
        pl.sum_horizontal(["normal", "impact", "star", "elite"]).alias("total")
    ).sort("university")
    df
    return (df,)


@app.cell
def _(create_dev_trait_breakdown, data_path, df, season):
    fig = create_dev_trait_breakdown(df=df, season=season)
    fig.write_image(data_path / "images" / f"{season}_dev_trait_breakdown.png", scale=2)
    fig.show()
    return (fig,)


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
    import plotly.graph_objects as go
    import plotly.io as pio

    pl.Config.set_tbl_rows(20)
    return Path, alt, find_project_path, go, mo, pio, pl


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


@app.cell
def _(go, pl):
    def create_dev_trait_breakdown(df: pl.DataFrame, season: str, template_name="plotly"):
        # Determine alignment for each column (left for text, right for numbers).
        alignments = []
        for col in df.columns:
            col_type = df.schema[col]
            # Check if the column type is numeric
            if col_type == pl.UInt32:
                alignments.append("right")
            else:
                alignments.append("left")

        # Create the table
        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=df.columns,
                        font=dict(size=13, weight="bold"),
                        height=27,
                    ),
                    cells=dict(
                        values=[df[col] for col in df.columns],
                        align=alignments,
                        height=26,
                        font=dict(size=12),
                    ),
                )
            ]
        )

        fig.update_layout(
            title=dict(
                text=f"{season} Development Trait Breakdown",
                font=dict(size=14, color="white"),
                x=0.5,
                y=0.95,
            ),
            template=template_name,
            margin=dict(l=0, r=0, t=25, b=0, pad=0),
            paper_bgcolor="#1E3A8A",
            plot_bgcolor="rgba(0,0,0,0)",
            height=24.9 + 26 + (26 * len(df)),
            autosize=False,
        )

        return fig
    return (create_dev_trait_breakdown,)


if __name__ == "__main__":
    app.run()
