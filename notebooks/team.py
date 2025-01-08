import marimo

__generated_with = "0.10.9"
app = marimo.App(
    width="medium",
    css_file="C:\\Users\\cdpet\\Documents\\Post School Coursework\\dev-materials\\configs\\marimo\\theme\\custom-theme.css",
    auto_download=["html", "ipynb"],
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# College Football 25 Dynasty Roster Analysis""")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Read Roster Data""")
    return


@app.cell
def _(data_path, pl):
    team = pl.read_csv(data_path / "csv" / "cfb_team.csv")

    class_enum = pl.Enum(["SR", "JR", "SO", "FR"])
    team_enum = pl.Enum(["OFF", "DEF", "ST"])
    dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    team = team.cast(
        {
            "class": class_enum,
            "position": pl.Categorical,
            "group": pl.Categorical,
            "secondary_group": pl.Categorical,
            "team": team_enum,
            "archetype": pl.Categorical,
            "dev_trait": dev_trait_enum,
        }
    )
    team
    return class_enum, dev_trait_enum, team, team_enum


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Exploratory Analysis
        ### Dev Traits per Position
        #### Create the Dataframes
        | dataframe                 | description                                                                                                                                 |
        |:--------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------|
        | `positions`               | the unique set of positions                                                                                                                 |
        | `groups`               | the unique set of position groups                                                                                                           |
        | `dev_traits`              | the unique set of dev traits. An index column named `order` is assigned and will be used to order the stacking of the stacked bar chart     |
        | `position_dev_combos`     | dataframe of the cross join (cartesian product) of all positions with all dev traits                                                        |
        | `dev_per_position_pre`    | all dev traits per position. This is the minimal set - does not include rows where there are no players of a given position-dev combination |
        | `dev_per_position`        | all dev traits per position including rows where there are no players of a given position-dev combination                                   |
        | `star_elite_per_position` | all star and elite dev traits per position including rows where there are no players of a given position-star or position-elite combination |
        """
    )
    return


@app.cell
def _(create_dataframe_md, dev_trait_enum, mo, pl, team):
    # Create a dataframe of the unique positions.
    positions = team.select("position").unique()

    # Create a dataframe of the unique position groups.
    groups = team.select("group").unique()

    # Create a dataframe of just the dev traits with an index column named
    # `order` to be used as the order for the stacked bar chart.
    dev_traits = pl.DataFrame(
        {"dev_trait": ["normal", "impact", "star", "elite"]},
        schema={"dev_trait": dev_trait_enum},
    ).with_row_index("order")

    # Create the cartesian product of positions and dev traits.
    position_dev_combos = positions.join(dev_traits, how="cross")

    # all dev traits per position, a minimal set
    dev_per_position_pre = (
        team.group_by(["position", "dev_trait"])
        .len("count")
        .sort(["position", "dev_trait"])
    )

    # all dev traits per position, the minimal set (doesn't have rows with
    # 0 for positions that don't have thos dev traits)
    dev_per_position = position_dev_combos.join(
        dev_per_position_pre, how="left", on=["position", "dev_trait"]
    ).fill_null(0)

    # star and elite dev traits per position.
    star_elite_per_position = dev_per_position.filter(
        (pl.col("dev_trait") == "elite") | (pl.col("dev_trait") == "star")
    )

    # Vertical stack of all the dataframes created in this cell.
    mo.vstack(
        [
            create_dataframe_md("positions"),
            positions,
            create_dataframe_md("groups"),
            groups,
            create_dataframe_md("dev_traits"),
            dev_traits,
            create_dataframe_md("position_dev_combos"),
            position_dev_combos,
            create_dataframe_md("dev_per_position_pre"),
            dev_per_position_pre,
            create_dataframe_md("dev_per_position"),
            dev_per_position,
            create_dataframe_md("star_elite_per_position"),
            star_elite_per_position,
        ]
    )
    return (
        dev_per_position,
        dev_per_position_pre,
        dev_traits,
        groups,
        position_dev_combos,
        positions,
        star_elite_per_position,
    )


@app.cell
def _(
    alt,
    anchor,
    data_path,
    dev_per_position,
    font_size,
    mo,
    positions,
    red_1,
    red_2,
    red_3,
    red_4,
    season,
    star_elite_per_position,
    width,
):
    # define shared plot properties.
    _x_axis = alt.X(
        "position:N",
        title="Position",
        axis=alt.Axis(labelAngle=0),
        sort=positions["position"].to_list(),
    )
    _y_axis_title = "Players"
    _legend_title = "Dev. Trait"

    # dev traits per position chart.
    _dev_trait_chart = (
        alt.Chart(dev_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y("count:Q", title=_y_axis_title),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[red_1, red_2, red_3, red_4],
                ),
            ),
            order="order:O",
        )
        .properties(
            width=width,
            height=350,
            title={
                "text": f"{season} Player Development Traits per Position",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # "star" and "elite" players per position chart.
    _star_elite_chart = (
        alt.Chart(star_elite_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y("count:Q", title=_y_axis_title, axis=alt.Axis(tickCount=2, format="d")),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star"],
                    range=[red_1, red_2],
                ),
            ),
            order="order:O",
        )
        .properties(
            width=width,
            height=75,
            title={
                "text": f"{season} Star and Elite Players per Position",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the charts as images.
    _dev_trait_chart.save(data_path / "images" / "dev_per_position.png", scale_factor=2.0)
    _star_elite_chart.save(
        data_path / "images" / "star_elite_per_position.png", scale_factor=2.0
    )

    # Stack the charts for viewing.
    mo.vstack([mo.ui.altair_chart(_dev_trait_chart), mo.ui.altair_chart(_star_elite_chart)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Class Distribution""")
    return


@app.cell
def _(class_enum, pl, team):
    # Create the order that will be used to ensure class order is correct.
    player_class_order = pl.DataFrame(
        {"class": ["FR", "SO", "JR", "SR"]}, schema={"class": class_enum}
    ).with_row_index("order")

    # Include grouping by `red_shirt` in order to capture the distribution
    # of red shirts for each class.
    player_classes = team.group_by(["class", "red_shirt"]).len("count")

    # Enforce the class order in the `player_classes` dataframe.
    player_classes = player_classes.join(player_class_order, on="class", how="left").sort(
        ["order", "red_shirt"]
    )
    player_classes
    return player_class_order, player_classes


@app.cell
def _(
    alt,
    anchor,
    data_path,
    font_size,
    mo,
    player_classes,
    red_1,
    red_2,
    season,
):
    # player classes chart.
    _player_classes_chart = (
        alt.Chart(player_classes)
        .mark_bar()
        .encode(
            x=alt.X(
                "class:N",
                title="Player Class",
                axis=alt.Axis(labelAngle=0),
                sort=["FR", "SO", "JR", "SR"],
            ),
            y=alt.Y("count:Q", title="Players"),
            color=alt.Color(
                "red_shirt:N",
                title="Red Shirt Status",
                scale=alt.Scale(
                    domain=[True, False],
                    range=[red_1, red_2],
                ),
                sort="descending",
            ),
            order=("red_shirt:O"),
        )
        .properties(
            width=250,
            height=250,
            title={
                "text": f"{season} Player Class Distribution",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the chart as an image.
    _player_classes_chart.save(
        data_path / "images" / "player_classes.png", scale_factor=2.0
    )

    mo.ui.altair_chart(_player_classes_chart)
    return


@app.cell
def _(team):
    positions_groups = team.group_by(["group", "position"]).len("count")
    positions_groups
    return (positions_groups,)


@app.cell
def _(
    alt,
    anchor,
    font_size,
    groups,
    mo,
    positions,
    positions_groups,
    season,
):
    _heatmap = (
        alt.Chart(positions_groups)
        .mark_rect()
        .encode(
            x=alt.X("position:N", title="Position", sort=positions["position"].to_list()),
            y=alt.Y("group:N", title="Position Group", sort=groups["group"].to_list()),
            color=alt.Color("count:Q", title="Players", scale=alt.Scale(scheme="viridis")),
            tooltip=["position", "group", "count"],
        )
        .properties(
            width=600,
            height=400,
            title={
                "text": f"{season} Position Distribution by Group",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    _text = _heatmap.mark_text().encode(
        text="count:Q",
        color=alt.condition(alt.datum.count < 7, alt.value("white"), alt.value("black")),
    )

    mo.ui.altair_chart(_heatmap + _text)
    return


@app.cell
def _(team):
    dev_pipeline = team.group_by(["position", "class", "dev_trait"]).len("count")
    dev_pipeline
    return (dev_pipeline,)


@app.cell
def _(
    alt,
    anchor,
    data_path,
    dev_pipeline,
    font_size,
    mo,
    positions,
    red_1,
    red_2,
    red_3,
    red_4,
    season,
):
    _dev_pipeline_chart = (
        alt.Chart(dev_pipeline)
        .mark_bar()
        .encode(
            x=alt.X("position:N", title="Position", sort=positions["position"].to_list()),
            y=alt.Y("count:Q", title="Players"),
            color=alt.Color(
                "dev_trait:N",
                title="Development Trait",
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[red_1, red_2, red_3, red_4],
                ),
            ),
            tooltip=["position", "class", "dev_trait", "count"],
        )
        .properties(width=600, height=100)
        .facet(
            row=alt.Row("class:N", sort=["FR", "SO", "JR", "SR"], title="Class"),
            title={
                "text": f"{season} Player Development Pipeline",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the chart as an image.
    _dev_pipeline_chart.save(data_path / "images" / "dev_pipeline.png", scale_factor=2.0)

    mo.ui.altair_chart(_dev_pipeline_chart)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Archetypes""")
    return


@app.cell(hide_code=True)
def _(mo, positions):
    position_options = ["Offense", "Defense"]
    position_options = position_options + positions["position"].to_list()

    team_position_dropdown = mo.ui.dropdown(
        options=position_options, value="Offense", label="Team/Positions"
    )
    team_position_dropdown
    return position_options, team_position_dropdown


@app.cell
def _(pl, team, team_position_dropdown):
    team_mapping = {"Offense": "OFF", "Defense": "DEF"}
    team_value = team_mapping.get(team_position_dropdown.value)
    print(team_value)
    if team_value:
        team_archetypes = team.filter(pl.col("team") == team_value)
        team_archetypes = team_archetypes.group_by(["position", "archetype"]).agg(
            pl.col("secondary_group").first(), pl.len().alias("count")
        )
    else:
        position_archetypes = team.filter(
            pl.col("position") == team_position_dropdown.value
        )

    team_archetypes.sort(["position", "archetype"])
    return position_archetypes, team_archetypes, team_mapping, team_value


@app.cell
def _(pl, team_archetypes):
    db_archetypes = team_archetypes.filter(pl.col("secondary_group") == "DB")

    db_archetypes = db_archetypes.with_columns(
        [
            pl.concat_str([pl.col("position"), pl.col("archetype")], separator="_").alias(
                "position_archetype"
            )
        ]
    )
    db_archetypes
    return (db_archetypes,)


@app.cell
def _(alt, anchor, db_archetypes, font_size, mo, season):
    _base_chart = (
        alt.Chart(db_archetypes)
        .mark_bar()
        .encode(
            x=alt.X("archetype:N"),
            # xOffset="position:N",
            y=alt.Y("count:Q", title="Players"),
            color=alt.value("steelblue"),
        )
        .properties(
            width=400,
            title={
                "text": f"{season} DB Archetypes",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    _position_labels = (
        alt.Chart(db_archetypes)
        .mark_text(dy=25, fontSize=12)
        .encode(
            x=alt.X("position:N", axis=None, scale=alt.Scale(paddingInner=0.1)),
            y=alt.value(0),
            text="position:N",
        )
    )

    _archetype_chart = (
        (_base_chart + _position_labels)
        .configure_view(strokeWidth=0)
        .configure_axis(grid=False)
    )

    mo.ui.altair_chart(_base_chart)
    return


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
    return Path, alt, mo, pl


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Shared Analysis Data""")
    return


@app.cell
def _(find_project_path):
    # Current dynasty season.
    season = 2027

    # Shared color scheme.
    red_1 = "#991b1b"
    red_2 = "#ef4444"
    red_3 = "#fca5a5"
    red_4 = "#fecaca"

    # Plot properties.
    width = 600
    font_size = 16
    anchor = "middle"

    # Data directory path.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"
    return (
        anchor,
        data_path,
        font_size,
        red_1,
        red_2,
        red_3,
        red_4,
        season,
        width,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### Helper Functions
        #### Find Project Path
        """
    )
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
            return None
    return (find_project_path,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""#### Dataframe Markdown""")
    return


@app.cell
def _(mo):
    def create_dataframe_md(frame_name):
        return mo.md(
            f"""<br>
            ### *`{frame_name}`*
        """
        )
    return (create_dataframe_md,)


if __name__ == "__main__":
    app.run()
