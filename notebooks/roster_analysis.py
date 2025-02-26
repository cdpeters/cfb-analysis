import marimo

__generated_with = "0.11.9"
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
    _universities = {
        "Fresno State": "fresno_state",
        "San Diego State": "san_diego_state",
        "Stanford": "stanford",
    }

    # Season for analysis.
    _seasons = ["2027", "2028", "2029", "2030"]

    # Form creation. The university and year of next season must be selected and then submitted prior
    # to processing the roster file.
    university_season_form = (
        mo.md("""
        ### Select **University** and **Season** for roster analysis

        {university_dropdown}

        {season_dropdown}
    """)
        .batch(
            university_dropdown=mo.ui.dropdown(options=_universities, label="University"),
            season_dropdown=mo.ui.dropdown(options=_seasons, label="Season"),
        )
        .form()
    )
    university_season_form
    return (university_season_form,)


@app.cell(hide_code=True)
def _(find_project_path, mo, pl, schema_overrides, university_season_form):
    # Stop execution if the form has not been submitted.
    mo.stop(
        university_season_form.value is None,
        mo.md("**Submit the form above to continue.**"),
    )

    university = university_season_form.value["university_dropdown"]
    season = university_season_form.value["season_dropdown"]

    # Stop execution if the form has been submitted but the university and/or season
    # has not been selected.
    mo.stop(
        any(x is None for x in (university, season)),
        mo.md(
            "**Either the university, the season, or both have not been selected. Please make sure both have been selected and resubmit the form above to continue.**"
        ),
    )

    # Path to the project's `data` directory.
    _project_path = find_project_path("cfb-analysis")
    data_path = _project_path / "data"

    # Expected season directory path.
    season_path = data_path / "images" / f"{university}" / f"{season}"

    # Check if the `season` directory exists and create it if it doesn't.
    if not season_path.exists():
        season_path.mkdir(parents=True)
        print(
            f"Created directory: {season_path.name}",
            f"At location: {season_path}",
            sep="\n",
            end="\n\n",
        )

    # Path to the roster excel file based on the university chosen for analysis.
    _roster_file_path = data_path / "datasets" / f"roster_{university}.xlsx"

    # Create the `roster` dataframe from the excel file.
    try:
        roster = pl.read_excel(
            _roster_file_path,
            sheet_name=season,
            schema_overrides=schema_overrides,
        )

        print(
            f"The {season} roster for {' '.join(university.split('_')).title()} was loaded successfully."
        )
    except (ValueError, FileNotFoundError) as e:
        print(e)
        mo.stop(True, mo.md("**Execution halted.**"))
    return data_path, roster, season, season_path, university


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


@app.cell(hide_code=True)
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
    # player_classes
    return (player_classes,)


@app.cell(hide_code=True)
def _(
    alt,
    anchor,
    color_1,
    color_2,
    mo,
    player_classes,
    season,
    season_path,
    title_font_size,
    university,
):
    # Player class distribution chart.
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
                    range=[color_1, color_2],
                ),
                sort="descending",
            ),
            order=("red_shirt:O"),
        )
        .properties(
            width=250,
            height=250,
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Player Class Distribution",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the chart as an image.
    _player_classes_chart.save(
        season_path / f"{season}_player_classes_{university}.png", scale_factor=2.0
    )

    mo.vstack([mo.ui.altair_chart(_player_classes_chart)], align="center")
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
def _(dev_traits, pl, positions, roster):
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
        pl.col("dev_trait").is_in(["elite", "star"])
    )

    dev_per_position_pipeline = roster.filter(pl.col("dev_trait").is_not_null())
    dev_per_position_pipeline = dev_per_position_pipeline.group_by(
        ["position", "class", "dev_trait"]
    ).len("count")
    dev_per_position_pipeline = dev_per_position_pipeline.join(
        dev_traits, how="left", on="dev_trait"
    )

    # Vertical stack of all the dataframes created in this cell.
    # mo.vstack(
    #     [
    #         create_dataframe_markdown("_position_dev_combos"),
    #         _position_dev_combos,
    #         create_dataframe_markdown("dev_per_position"),
    #         dev_per_position,
    #         create_dataframe_markdown("star_elite_per_position"),
    #         star_elite_per_position,
    #         create_dataframe_markdown("dev_per_position_pipeline"),
    #         dev_per_position_pipeline,
    #     ]
    # )
    return dev_per_position, dev_per_position_pipeline, star_elite_per_position


@app.cell(hide_code=True)
def _(
    alt,
    anchor,
    color_1,
    color_2,
    color_3,
    color_4,
    dev_per_position,
    dev_per_position_pipeline,
    dev_y_scale_max,
    mo,
    positions,
    season,
    season_path,
    star_elite_per_position,
    star_elite_y_scale_max,
    title_font_size,
    university,
    width,
):
    # Define shared plot properties.
    _x_axis = alt.X(
        "position:N",
        title="Position",
        axis=alt.Axis(labelAngle=0),
        sort=positions["position"].to_list(),
    )
    _y_axis_title = "Players"
    _legend_title = "Development Trait"

    # -------------------------------------------------------------------------------
    # Dev traits per position chart.
    _dev_trait_chart = (
        alt.Chart(dev_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=dev_y_scale_max + 1, format="d"),
                scale=alt.Scale(domain=[0, dev_y_scale_max]),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[color_1, color_2, color_3, color_4],
                ),
            ),
            order="order:O",
        )
        .properties(
            width=width,
            height=350,
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Player Development Traits per Position",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    # Star and elite players per position chart.
    _star_elite_chart = (
        alt.Chart(star_elite_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=star_elite_y_scale_max + 1, format="d"),
                scale=alt.Scale(domain=[0, star_elite_y_scale_max]),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star"],
                    range=[color_1, color_2],
                ),
            ),
            order="order:O",
        )
        .properties(
            width=width,
            height=200,
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Star and Elite Players per Position",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    # Player development pipeline per position chart.
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
                    range=[color_1, color_2, color_3, color_4],
                ),
            ),
            order="order:O",
            tooltip=["position", "class", "dev_trait", "count"],
        )
        .properties(width=600, height=100)
        .facet(
            row=alt.Row("class:N", sort=["FR", "SO", "JR", "SR"], title="Class"),
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Player Development Pipeline per Position",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the charts as images.
    _dev_trait_chart.save(
        season_path / f"{season}_dev_per_position_{university}.png", scale_factor=2.0
    )
    _star_elite_chart.save(
        season_path / f"{season}_star_elite_per_position_{university}.png", scale_factor=2.0
    )
    _dev_per_position_pipeline_chart.save(
        season_path / f"{season}_dev_per_position_pipeline_{university}.png",
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
def _(dev_traits, groups, pl, roster):
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
        pl.col("dev_trait").is_in(["elite", "star"])
    )

    dev_per_group_pipeline = roster.filter(pl.col("dev_trait").is_not_null())
    dev_per_group_pipeline = dev_per_group_pipeline.group_by(
        ["group", "class", "dev_trait"]
    ).len("count")
    dev_per_group_pipeline = dev_per_group_pipeline.join(
        dev_traits, how="left", on="dev_trait"
    )

    # Vertical stack of all the dataframes created in this cell.
    # mo.vstack(
    #     [
    #         create_dataframe_markdown("_group_dev_combos"),
    #         _group_dev_combos,
    #         create_dataframe_markdown("dev_per_group"),
    #         dev_per_group,
    #         create_dataframe_markdown("star_elite_per_group"),
    #         star_elite_per_group,
    #         create_dataframe_markdown("dev_per_group_pipeline"),
    #         dev_per_group_pipeline,
    #     ]
    # )
    return dev_per_group, dev_per_group_pipeline, star_elite_per_group


@app.cell(hide_code=True)
def _(
    alt,
    anchor,
    color_1,
    color_2,
    color_3,
    color_4,
    dev_per_group,
    dev_per_group_pipeline,
    dev_y_scale_max,
    groups,
    mo,
    season,
    season_path,
    star_elite_per_group,
    star_elite_y_scale_max,
    title_font_size,
    university,
    width,
):
    # Define shared plot properties.
    _x_axis = alt.X(
        "group:N",
        title="Group",
        axis=alt.Axis(labelAngle=0),
        sort=groups["group"].to_list(),
    )
    _y_axis_title = "Players"
    _legend_title = "Development Trait"

    # -------------------------------------------------------------------------------
    # Dev traits per group chart.
    _dev_trait_chart = (
        alt.Chart(dev_per_group)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=dev_y_scale_max + 1, format="d"),
                scale=alt.Scale(domain=[0, dev_y_scale_max]),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[color_1, color_2, color_3, color_4],
                ),
            ),
            order="order:O",
        )
        .properties(
            width=width,
            height=350,
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Player Development Traits per Group",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    # Star and elite players per group chart.
    _star_elite_chart = (
        alt.Chart(star_elite_per_group)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(tickCount=star_elite_y_scale_max + 1, format="d"),
                scale=alt.Scale(domain=[0, star_elite_y_scale_max]),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star"],
                    range=[color_1, color_2],
                ),
            ),
            order="order:O",
        )
        .properties(
            width=width,
            height=200,
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Star and Elite Players per Group",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # -------------------------------------------------------------------------------
    # Player development pipeline per group chart.
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
                    range=[color_1, color_2, color_3, color_4],
                ),
            ),
            order="order:O",
            tooltip=["group", "class", "dev_trait", "count"],
        )
        .properties(width=500, height=100)
        .facet(
            row=alt.Row("class:N", sort=["FR", "SO", "JR", "SR"], title="Class"),
            title={
                "text": f"{university.replace('_', ' ').title()} {season} Player Development Pipeline per Group",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Save the charts as images.
    _dev_trait_chart.save(
        season_path / f"{season}_dev_per_group_{university}.png", scale_factor=2.0
    )
    _star_elite_chart.save(
        season_path / f"{season}_star_elite_per_group_{university}.png", scale_factor=2.0
    )
    _dev_per_group_pipeline_chart.save(
        season_path / f"{season}_dev_per_group_pipeline_{university}.png", scale_factor=2.0
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
    mo.md(
        r"""
        ### Possible Non-Senior Drafted Players
        #### Qualifications
        - non-senior
        - draft eligible - a true junior, redshirt junior, or a redshirt sophomore
        - 85 overall (`overall_start`) or higher
        """
    )
    return


@app.cell
def _(pl, roster):
    draft_eligible_non_senior = (pl.col("class") == "JR") | (
        (pl.col("class") == "SO") & (pl.col("red_shirt") == True)
    )

    roster.filter(draft_eligible_non_senior & (pl.col("overall_start") >= 85)).sort(
        "overall_start", descending=True
    )
    return (draft_eligible_non_senior,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### Young Player Quality
        - young player - a freshman or sophomore including redshirted players
        - the average overall of young players at each position group is used to assess young player quality
        """
    )
    return


@app.cell
def _(mo, pl, roster):
    young_players = roster.filter(pl.col("class").is_in(["FR", "SO"]))

    mo.plain(
        young_players.group_by("group")
        .agg(
            pl.col("overall_start").mean().round(1).alias("avg_overall_start"),
            pl.len().alias("count"),
        )
        .sort(["avg_overall_start", "count"])
    )
    return (young_players,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Roster Viewer""")
    return


@app.cell(hide_code=True)
def _(mo, roster):
    mo.ui.dataframe(roster, page_size=85)
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

    from utilities import (
        create_dataframe_markdown,
        find_project_path,
        schema_overrides,
        class_enum,
        dev_trait_enum,
    )

    # Set polars to show enough rows for the young player quality dataframe.
    pl.Config(tbl_rows=-1)
    return (
        Path,
        alt,
        class_enum,
        create_dataframe_markdown,
        dev_trait_enum,
        find_project_path,
        mo,
        pl,
        schema_overrides,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Shared Analysis Data""")
    return


@app.cell
def _(mo, university, university_season_form):
    mo.stop(
        university_season_form.value is None,
        mo.md("**Submit the form above to continue.**"),
    )

    # University color schemes.
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

    # Shared color scheme.
    color_1 = university_colors[university]["color_1"]
    color_2 = university_colors[university]["color_2"]
    color_3 = university_colors[university]["color_3"]
    color_4 = university_colors[university]["color_4"]

    # Plot related constants.
    dev_y_scale_max = 11
    star_elite_y_scale_max = 8
    width = 600
    title_font_size = 16
    anchor = "middle"
    return (
        anchor,
        color_1,
        color_2,
        color_3,
        color_4,
        dev_y_scale_max,
        star_elite_y_scale_max,
        title_font_size,
        university_colors,
        width,
    )


@app.cell
def _(Path):
    def ensure_season_pathectory(season_path: Path) -> Path:
        """
        Check if a directory for the specified season exists.
        If it doesn't exist, create it.

        Parameters:
        -----------
        season_path : Path
            Expected path of season directory.

        Returns:
        -----------
        Path
            Path to the season directory
        """

        return season_path
    return (ensure_season_pathectory,)


if __name__ == "__main__":
    app.run()
