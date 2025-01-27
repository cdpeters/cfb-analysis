import marimo

__generated_with = "0.10.17"
app = marimo.App(
    width="medium",
    css_file="C:\\Users\\cdpet\\Documents\\Post School Coursework\\dev-materials\\configs\\marimo\\theme\\custom-theme.css",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# College Football 25 Dynasty Roster Analysis""")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Read Roster Data
        ### Choose Team and Season
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    # Team being analyzed.
    _teams = {
        "Stanford": "stanford",
        # "Fresno State": "fresno_state",
        # "San Diego State": "san_diego_state",
    }
    team_dropdown = mo.ui.dropdown(options=_teams, value="Stanford", label="Team")

    # Season for analysis.
    _seasons = ["2027", "2028", "2029"]

    season_dropdown = mo.ui.dropdown(options=_seasons, value="2028", label="Season")

    mo.hstack([team_dropdown, season_dropdown], justify="start")
    return season_dropdown, team_dropdown


@app.cell
def _(data_path, pl, season_dropdown, team_dropdown):
    _roster_file_name = f"roster_{team_dropdown.value}.xlsx"
    _roster_file_name

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

    # Create the `roster` dataframe from the Excel file.
    roster = pl.read_excel(
        data_path / "datasets" / _roster_file_name,
        sheet_name=season_dropdown.value,
        schema_overrides=_schema_overrides,
    )
    return class_enum, dev_trait_enum, roster, team_enum


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Exploratory Analysis
        ### Shared Dataframes
        | dataframe          | description                                                                                                                              |
        |:-------------------|:-----------------------------------------------------------------------------------------------------------------------------------------|
        | `positions`        | the unique set of positions                                                                                                              |
        | `groups`           | the unique set of position groups                                                                                                        |
        | `secondary_groups` | the unique set of secondary position groups                                                                                              |
        | `dev_traits`       | the unique set of dev traits. An index column named `order` is assigned and will be used to order the stacking of the stacked bar charts |
        """
    )
    return


@app.cell
def _(dev_trait_enum, pl, roster):
    positions = roster.select("position").unique()
    groups = roster.select("group").unique()
    secondary_groups = roster.select("secondary_group").unique()

    dev_traits = pl.DataFrame(
        {"dev_trait": ["normal", "impact", "star", "elite"]},
        schema={"dev_trait": dev_trait_enum},
    ).with_row_index("order")
    return dev_traits, groups, positions, secondary_groups


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Player Class Distribution""")
    return


@app.cell(hide_code=True)
def _(class_enum, pl, roster):
    # Create the order that will be used to ensure class order is correct.
    _player_class_order = pl.DataFrame(
        {"class": ["FR", "SO", "JR", "SR"]}, schema={"class": class_enum}
    ).with_row_index("order")

    # Include grouping by `red_shirt` in order to capture the distribution
    # of red shirts for each class.
    player_classes = roster.group_by(["class", "red_shirt"]).len("count")

    # Enforce the class order in the `player_classes` dataframe.
    player_classes = player_classes.join(_player_class_order, on="class", how="left").sort(
        ["order", "red_shirt"]
    )
    player_classes
    return (player_classes,)


@app.cell(hide_code=True)
def _(
    alt,
    anchor,
    data_path,
    font_size,
    mo,
    player_classes,
    red_1,
    red_2,
    season_dropdown,
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
                "text": f"{season_dropdown.value} Player Class Distribution",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the chart as an image.
    _player_classes_chart.save(
        data_path / "images" / f"{season_dropdown.value}_player_classes.png",
        scale_factor=2.0,
    )

    mo.ui.altair_chart(_player_classes_chart)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### Dev Traits per Position
        | dataframe                   | description                                                                                                                                 |
        |:--------------------------  |:--------------------------------------------------------------------------------------------------------------------------------------------|
        | `_position_dev_combos`      | dataframe of the cross join (cartesian product) of all positions with all dev traits                                                        |
        | `dev_per_position`          | all dev traits per position including rows where there are no players of a given position-dev combination                                   |
        | `star_elite_per_position`   | all star and elite dev traits per position including rows where there are no players of a given position-star or position-elite combination |
        | `dev_per_position_pipeline` | all dev traits per position per class                                                                                                       |
        """
    )
    return


@app.cell(hide_code=True)
def _(create_dataframe_md, dev_traits, mo, pl, positions, roster):
    # Create the cartesian product of positions and dev traits.
    _position_dev_combos = positions.join(dev_traits, how="cross")

    # Minimal set of dev traits per position (does not include dev trait and position combos that have a count of 0).
    dev_per_position = (
        roster.group_by(["position", "dev_trait"])
        .len("count")
        .sort(["position", "dev_trait"])
    )

    # Maximal set of dev traits per position (includes dev trait and position combos that have a count of 0).
    dev_per_position = _position_dev_combos.join(
        dev_per_position, how="left", on=["position", "dev_trait"]
    ).fill_null(0)

    star_elite_per_position = dev_per_position.filter(
        (pl.col("dev_trait") == "elite") | (pl.col("dev_trait") == "star")
    )

    dev_per_position_pipeline = roster.group_by(["position", "class", "dev_trait"]).len(
        "count"
    )
    dev_per_position_pipeline = dev_per_position_pipeline.join(
        dev_traits, how="left", on="dev_trait"
    )

    # Vertical stack of all the dataframes created in this cell.
    mo.vstack(
        [
            create_dataframe_md("_position_dev_combos"),
            _position_dev_combos,
            create_dataframe_md("dev_per_position"),
            dev_per_position,
            create_dataframe_md("star_elite_per_position"),
            star_elite_per_position,
            create_dataframe_md("dev_per_position_pipeline"),
            dev_per_position_pipeline,
        ]
    )
    return (
        dev_per_position,
        dev_per_position_pipeline,
        star_elite_per_position,
    )


@app.cell(hide_code=True)
def _(
    alt,
    anchor,
    data_path,
    dev_per_position,
    dev_per_position_pipeline,
    font_size,
    mo,
    positions,
    red_1,
    red_2,
    red_3,
    red_4,
    season_dropdown,
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
    _legend_title = "Development Trait"

    # -------------------------------------------------------------------------------
    _dev_trait_chart = (
        alt.Chart(dev_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=12, format="d"),
                scale=alt.Scale(domain=[0, 11]),
            ),
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
                "text": f"{season_dropdown.value} Player Development Traits per Position",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    _star_elite_chart = (
        alt.Chart(star_elite_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=8, format="d"),
                scale=alt.Scale(domain=[0, 7]),
            ),
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
            height=200,
            title={
                "text": f"{season_dropdown.value} Star and Elite Players per Position",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    _dev_per_position_pipeline_chart = (
        alt.Chart(dev_per_position_pipeline)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y("count:Q", title="Players"),
            color=alt.Color(
                "dev_trait:N",
                title="Development Trait",
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[red_1, red_2, red_3, red_4],
                ),
            ),
            order="order:O",
            tooltip=["position", "class", "dev_trait", "count"],
        )
        .properties(width=600, height=100)
        .facet(
            row=alt.Row("class:N", sort=["FR", "SO", "JR", "SR"], title="Class"),
            title={
                "text": f"{season_dropdown.value} Player Development Pipeline per Position",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the charts as images.
    _dev_trait_chart.save(
        data_path / "images" / f"{season_dropdown.value}_dev_per_position.png",
        scale_factor=2.0,
    )
    _star_elite_chart.save(
        data_path / "images" / f"{season_dropdown.value}_star_elite_per_position.png",
        scale_factor=2.0,
    )
    _dev_per_position_pipeline_chart.save(
        data_path / "images" / f"{season_dropdown.value}_dev_per_position_pipeline.png",
        scale_factor=2.0,
    )

    # Stack the charts for viewing.
    mo.vstack(
        [
            mo.ui.altair_chart(_dev_trait_chart),
            mo.ui.altair_chart(_star_elite_chart),
            mo.ui.altair_chart(_dev_per_position_pipeline_chart),
        ],
        align="center",
        gap=3.0,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
        ### Dev Traits per Group
        | dataframe              | description                                                                                                                           |
        |:-----------------------|:--------------------------------------------------------------------------------------------------------------------------------------|
        | `_group_dev_combos`    | dataframe of the cross join (cartesian product) of all groups with all dev traits                                                     |
        | `_dev_per_group_pre`   | all dev traits per group. This is the minimal set - does not include rows where there are no players of a given group-dev combination |
        | `dev_per_group`        | all dev traits per group including rows where there are no players of a given group-dev combination                                   |
        | `star_elite_per_group` | all star and elite dev traits per group including rows where there are no players of a given group-star or group-elite combination    |
        """
    )
    return


@app.cell(hide_code=True)
def _(create_dataframe_md, dev_traits, groups, mo, pl, roster):
    # Create the cartesian product of groups and dev traits.
    _group_dev_combos = groups.join(dev_traits, how="cross")

    # Minimal set of dev traits per group (does not include dev trait and group combos that have a count of 0).
    dev_per_group = (
        roster.group_by(["group", "dev_trait"]).len("count").sort(["group", "dev_trait"])
    )

    # Maximal set of dev traits per group (includes dev trait and group combos that have a count of 0).
    dev_per_group = _group_dev_combos.join(
        dev_per_group, how="left", on=["group", "dev_trait"]
    ).fill_null(0)

    star_elite_per_group = dev_per_group.filter(
        (pl.col("dev_trait") == "elite") | (pl.col("dev_trait") == "star")
    )

    dev_per_group_pipeline = roster.group_by(["group", "class", "dev_trait"]).len("count")
    dev_per_group_pipeline = dev_per_group_pipeline.join(
        dev_traits, how="left", on="dev_trait"
    )

    # Vertical stack of all the dataframes created in this cell.
    mo.vstack(
        [
            create_dataframe_md("_group_dev_combos"),
            _group_dev_combos,
            create_dataframe_md("dev_per_group"),
            dev_per_group,
            create_dataframe_md("star_elite_per_group"),
            star_elite_per_group,
            create_dataframe_md("dev_per_group_pipeline"),
            dev_per_group_pipeline,
        ]
    )
    return dev_per_group, dev_per_group_pipeline, star_elite_per_group


@app.cell(hide_code=True)
def _(
    alt,
    anchor,
    data_path,
    dev_per_group,
    dev_per_group_pipeline,
    font_size,
    groups,
    mo,
    red_1,
    red_2,
    red_3,
    red_4,
    season_dropdown,
    star_elite_per_group,
    width,
):
    # define shared plot properties.
    _x_axis = alt.X(
        "group:N",
        title="Group",
        axis=alt.Axis(labelAngle=0),
        sort=groups["group"].to_list(),
    )
    _y_axis_title = "Players"
    _legend_title = "Development Trait"

    # -------------------------------------------------------------------------------
    _dev_trait_chart = (
        alt.Chart(dev_per_group)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=12, format="d"),
                scale=alt.Scale(domain=[0, 11]),
            ),
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
                "text": f"{season_dropdown.value} Player Development Traits per Group",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    _star_elite_chart = (
        alt.Chart(star_elite_per_group)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=8, format="d"),
                scale=alt.Scale(domain=[0, 7]),
            ),
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
            height=200,
            title={
                "text": f"{season_dropdown.value} Star and Elite Players per Group",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    _dev_per_group_pipeline_chart = (
        alt.Chart(dev_per_group_pipeline)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y("count:Q", title="Players"),
            color=alt.Color(
                "dev_trait:N",
                title="Development Trait",
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[red_1, red_2, red_3, red_4],
                ),
            ),
            order="order:O",
            tooltip=["group", "class", "dev_trait", "count"],
        )
        .properties(width=500, height=100)
        .facet(
            row=alt.Row("class:N", sort=["FR", "SO", "JR", "SR"], title="Class"),
            title={
                "text": f"{season_dropdown.value} Player Development Pipeline per Group",
                "fontSize": font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the charts as images.
    _dev_trait_chart.save(
        data_path / "images" / f"{season_dropdown.value}_dev_per_group.png",
        scale_factor=2.0,
    )
    _star_elite_chart.save(
        data_path / "images" / f"{season_dropdown.value}_star_elite_per_group.png",
        scale_factor=2.0,
    )
    _dev_per_group_pipeline_chart.save(
        data_path / "images" / f"{season_dropdown.value}_dev_per_group_pipeline.png",
        scale_factor=2.0,
    )

    # Stack the charts for viewing.
    mo.vstack(
        [
            mo.ui.altair_chart(_dev_trait_chart),
            mo.ui.altair_chart(_star_elite_chart),
            mo.ui.altair_chart(_dev_per_group_pipeline_chart),
        ],
        align="center",
        gap=3.0,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Possible Non-Senior Players Leaving""")
    return


@app.cell
def _(pl, roster):
    roster.filter((pl.col("overall") >= 87) & (pl.col("class") != "SR")).sort(
        "overall", descending=True
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### Young Player Quality
        - young player - a freshman or sophomore including redshirted players
        - the average overall of the young players at each position group is used to assess quality
        """
    )
    return


@app.cell
def _(pl, roster):
    young_players = roster.filter((pl.col("class") == "FR") | (pl.col("class") == "SO"))

    young_players.group_by("group").mean().select(
        pl.col("group"), pl.col("overall").round(0).alias("avg_overall")
    ).sort("avg_overall")
    return (young_players,)


@app.cell
def _(pl, roster):
    roster.filter(pl.col("group") == "OLB")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Archetypes""")
    return


@app.cell(hide_code=True)
def _(mo, positions):
    _position_options = ["Offense", "Defense"]
    _position_options = _position_options + positions["position"].to_list()

    team_position_dropdown = mo.ui.dropdown(
        options=_position_options, value="Offense", label="Team/Positions"
    )
    team_position_dropdown
    return (team_position_dropdown,)


@app.cell
def _(pl, roster, team_position_dropdown):
    _team_mapping = {"Offense": "OFF", "Defense": "DEF"}
    _team_value = _team_mapping.get(team_position_dropdown.value)
    print(_team_value)
    if _team_value:
        team_archetypes = roster.filter(pl.col("team") == _team_value)
        team_archetypes = team_archetypes.group_by(["position", "archetype"]).agg(
            pl.col("secondary_group").first(), pl.len().alias("count")
        )
    else:
        position_archetypes = roster.filter(
            pl.col("position") == team_position_dropdown.value
        )

    team_archetypes.sort(["position", "archetype"])
    return position_archetypes, team_archetypes


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
def _(alt, anchor, db_archetypes, font_size, mo, season_dropdown):
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
                "text": f"{season_dropdown.value} DB Archetypes",
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
    # Data directory path.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    # Shared color scheme.
    red_1 = "#991b1b"
    red_2 = "#ef4444"
    red_3 = "#fca5a5"
    red_4 = "#fecaca"

    # Plot properties.
    width = 600
    font_size = 16
    anchor = "middle"
    return anchor, data_path, font_size, red_1, red_2, red_3, red_4, width


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
    def create_dataframe_md(frame_name: str) -> mo._output.md._md:
        return mo.md(
            f"""<br>
            *`{frame_name}`*
        """
        )
    return (create_dataframe_md,)


if __name__ == "__main__":
    app.run()
