import marimo

__generated_with = "0.11.14"
app = marimo.App(
    width="medium",
    css_file="",
    html_head_file="public/head.html",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        # 🏈 College Football 25 Dynasty Roster Analysis 🏈

        The following app can be used to explore your College Football 25 (CFB 25) dynasty roster. The UI elements are interactive, feel free to interact with an element's controls to see new views of the data.

        ## Overview

        ### Roster Viewer
        The **Roster Viewer** allows you to transform the view of the full roster. Transformations include filtering, grouping, aggregating, and sorting among other operations.

        ### Exploratory Analysis
        This section contains charts as well as specific views of the roster (preapplied transformations).

        #### Sections include:
        - **Player Class Distribution and Dev Trait per Position/Group**
        - **Potential Non-Senior Drafted Players**
        - **Young Player Quality**
        - **Players to Cut**
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    _universities = {
        "Fresno State": "fresno_state",
        "San Diego State": "san_diego_state",
        "Stanford": "stanford",
    }

    # Season for analysis.
    _seasons = ["2029", "2030"]

    # Form creation. The university and year of next season must be selected and then submitted prior
    # to processing the roster file.
    university_season_form = (
        mo.md("""
        ### Select the **University** and **Season** for analysis.

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
def _(
    find_project_path,
    load_roster_from_github_repo,
    load_roster_locally,
    mo,
    running_locally,
    schema_overrides,
    university_season_form,
):
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

    if running_locally:
        # Path to the project's `data` directory and the expected season directory (it might not exist).
        _project_path = find_project_path("cfb-analysis")
        _data_path = _project_path / "data"
        season_path = _data_path / "images" / f"{university}" / f"{season}"
        roster = load_roster_locally(
            data_path=_data_path,
            university=university,
            season=season,
            schema_overrides=schema_overrides,
        )
        # Check if the `season` directory exists and create it if it doesn't.
        if not season_path.exists():
            season_path.mkdir(parents=True)
            print(
                f"Created new season directory for {university}: {season_path.name}",
                f"At location: {season_path}",
                sep="\n",
            )
    else:
        roster = load_roster_from_github_repo(
            university=university, season=season, schema_overrides=schema_overrides
        )
    return roster, season, season_path, university


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Roster Viewer
        The standard view of the roster is shown. Transformations can be applied to create alternate views. Additionally, the column names can be clicked on for further transformation options.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo, roster):
    mo.ui.dataframe(roster, page_size=17)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Exploratory Analysis

        ### Player Class Distribution and Dev Trait per Position/Group

        #### Player Class Distribution
        - There are four classes:
            - **FR** (freshman)
            - **SO** (sophomore)
            - **JR** (junior)
            - **SR** (senior)
        - Red shirt status: earned by playing a snap in 4 games or less within a given season.

        #### Dev Trait per Position/Group
        - There are four dev traits: **normal**, **impact**, **star**, and **elite**.

        > Note: there are three tabs below containing visualizations. The Dev Traits per Position and Dev Traits per Group tabs are carousel UI elements containing three charts each. Click on the left or right arrows on the sides of the carousel (you have to hover over them to see them) or click on any of the three dots at the bottom, one at a time, to move through the images on those tabs.
        """
    )
    return


@app.cell
def _(pl, roster):
    classes = roster.select("class").unique().sort("class")
    red_shirts = roster.select("red_shirt").unique().sort("red_shirt")
    dev_traits = roster.select("dev_trait").unique().sort("dev_trait")
    positions = roster.select("position").unique().sort("position")
    groups = roster.select("group").unique().sort("group")
    secondary_groups = roster.select("secondary_group").unique().sort("secondary_group")

    # Assign integer ordering in order to preserve class, position, and group ordering
    # without having to rely on a string sequence (there was an issue where locally the
    # order was correct but the deployed WASM app had random ordering when relying on a
    # string sequence instead of an integer sequence).
    class_order = {cls: index for index, cls in enumerate(classes["class"])}
    red_shirt_order = {
        red_shirt: index for index, red_shirt in enumerate(red_shirts["red_shirt"])
    }
    dev_trait_order = {
        dev_trait: index for index, dev_trait in enumerate(dev_traits["dev_trait"])
    }

    position_order = {
        position: index for index, position in enumerate(positions["position"])
    }
    group_order = {group: index for index, group in enumerate(groups["group"])}

    # Add the ordering columns to the roster dataframe.
    roster_with_order = roster.with_columns(
        pl.col("position").replace_strict(position_order).alias("position_order"),
        pl.col("group").replace_strict(group_order).alias("group_order"),
        pl.col("class").replace_strict(class_order).alias("class_order"),
        pl.col("dev_trait").replace_strict(dev_trait_order).alias("dev_trait_order"),
        pl.col("red_shirt").replace_strict(red_shirt_order).alias("red_shirt_order"),
    )
    return (
        class_order,
        classes,
        dev_trait_order,
        dev_traits,
        group_order,
        groups,
        position_order,
        positions,
        red_shirt_order,
        red_shirts,
        roster_with_order,
        secondary_groups,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r""" """)
    return


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""#### Player Class Distribution""") if running_locally else None
    return


@app.cell
def _(roster_with_order):
    # Include grouping by `red_shirt` in order to capture the distribution
    # of red shirts for each class.
    player_classes = roster_with_order.group_by(["class", "red_shirt", "class_order"]).len(
        "count"
    )
    return (player_classes,)


@app.cell
def _(
    alt,
    anchor,
    color_1,
    color_2,
    player_classes,
    running_locally,
    season,
    season_path,
    title_font_size,
    university,
):
    # Player class distribution chart.
    player_classes_chart = (
        alt.Chart(player_classes)
        .mark_bar()
        .encode(
            x=alt.X(
                "class:N",
                title="Player Class",
                axis=alt.Axis(labelAngle=0),
                sort={"field": "class_order"},
            ),
            y=alt.Y("count:Q", title="Players"),
            color=alt.Color(
                "red_shirt:N",
                title="Red Shirt Status",
                scale=alt.Scale(
                    domain=[True, False],
                    range=[color_1, color_2],
                ),
                sort={"field": "red_shirt_order"},
            ),
            order="red_shirt:O",
            tooltip=[
                alt.Tooltip("class:N", title="Player Class"),
                alt.Tooltip("count:Q", title="Players"),
                alt.Tooltip("red_shirt:N", title="Red Shirt Status"),
            ],
        )
        .properties(
            width=250,
            height=300,
            title={
                "text": f"{season} Player Class Distribution",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    if running_locally:
        # Save the chart as an image.
        player_classes_chart.save(
            season_path / f"{season}_player_classes_{university}.png", scale_factor=2.0
        )
    else:
        print("Skipped saving chart as an image since app is running as a WASM app.")
    return (player_classes_chart,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r""" """)
    return


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""#### Dev Traits per Position""") if running_locally else None
    return


@app.cell
def _(
    class_order,
    classes,
    dev_trait_order,
    dev_traits,
    pl,
    position_order,
    positions,
    roster_with_order,
):
    # dev_per_position and star_elite_per_position -----------------------------------------
    # All possible combinations of positions and dev traits via cartesian product (cross
    # join).
    _position_dev_combos = positions.join(dev_traits, how="cross")

    # Counts of dev traits per position, the minimal set (i.e. does not include dev trait
    # and position combos that have a count of 0).
    _min_dev_per_position = roster_with_order.group_by(["position", "dev_trait"]).len(
        "count"
    )

    # Counts of dev traits per position including rows where there are no players of a given
    # position dev trait combination, the maximal set.
    dev_per_position = (
        _position_dev_combos.join(
            _min_dev_per_position, how="left", on=["position", "dev_trait"]
        )
        .with_columns(
            pl.col("count").fill_null(0),
            pl.col("position").replace_strict(position_order).alias("position_order"),
            pl.col("dev_trait").replace_strict(dev_trait_order).alias("dev_trait_order"),
        )
        .sort(["position_order", "dev_trait_order"])
    )

    # Counts of star and elite dev traits per position including rows where there are no
    # players of a given position-star or position-elite combination.
    star_elite_per_position = dev_per_position.filter(
        pl.col("dev_trait").is_in(["elite", "star"])
    )

    # dev_per_position_pipeline ------------------------------------------------------------
    # All possible combinations of positions, dev traits, and classes via cartesian product
    # (cross join). The product is formed via cross join of `_position_dev_combos` with
    # `classes`.
    _position_dev_class_combos = _position_dev_combos.join(classes, how="cross")

    # Counts of dev traits per position per class, the minimal set (i.e. does not include
    # dev trait, position, and class combos that have a count of 0).
    _min_dev_per_position_pipeline = roster_with_order.group_by(
        ["position", "dev_trait", "class"]
    ).len("count")

    # Counts of dev traits per position per class including rows where there are no players
    # of a given position, dev trait, and class combination; the maximal set.
    dev_per_position_pipeline = (
        _position_dev_class_combos.join(
            _min_dev_per_position_pipeline,
            how="left",
            on=["position", "dev_trait", "class"],
        )
        .with_columns(
            pl.col("count").fill_null(0),
            pl.col("position").replace_strict(position_order).alias("position_order"),
            pl.col("dev_trait").replace_strict(dev_trait_order).alias("dev_trait_order"),
            pl.col("class").replace_strict(class_order).alias("class_order"),
        )
        .sort(["position_order", "dev_trait_order", "class_order"])
    )
    return dev_per_position, dev_per_position_pipeline, star_elite_per_position


@app.cell
def _(
    alt,
    anchor,
    color_1,
    color_2,
    color_3,
    color_4,
    dev_per_position,
    dev_per_position_pipeline,
    height_pipeline,
    mo,
    running_locally,
    season,
    season_path,
    star_elite_per_position,
    title_font_size,
    university,
    width_position,
):
    # Define shared plot properties.
    _x_axis = alt.X(
        "position:N",
        title="Position",
        axis=alt.Axis(labelAngle=0),
        sort={"field": "position_order"},
    )
    _y_axis_title = "Players"
    _legend_title = "Dev Trait"

    # Dev traits per position chart --------------------------------------------------------
    _dev_trait_chart = (
        alt.Chart(dev_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(format="d"),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[color_1, color_2, color_3, color_4],
                ),
                sort={"field": "dev_trait_order"},
            ),
            order="dev_trait_order:O",
            tooltip=[
                alt.Tooltip("position:N", title="Position"),
                alt.Tooltip("count:Q", title="Players"),
                alt.Tooltip("dev_trait:N", title="Dev Trait"),
            ],
        )
        .properties(
            width=width_position,
            height=300,
            title={
                "text": f"{season} Player Dev Traits per Position",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Star and elite players per position chart --------------------------------------------
    _star_elite_chart = (
        alt.Chart(star_elite_per_position)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(format="d"),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star"],
                    range=[color_1, color_2],
                ),
                sort={"field": "dev_trait_order"},
            ),
            order="dev_trait_order:O",
            tooltip=[
                alt.Tooltip("position:N", title="Position"),
                alt.Tooltip("count:Q", title="Players"),
                alt.Tooltip("dev_trait:N", title="Dev Trait"),
            ],
        )
        .properties(
            width=width_position,
            height=200,
            title={
                "text": f"{season} Star / Elite Players per Position",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Dev traits per position pipeline chart -----------------------------------------------
    # Build the pipeline chart in stages due to issues with ordering. Apply ordering in both
    # the encode and facet steps to ensure the correct ordering is kept in the final chart.
    _dev_trait_pipeline_base = alt.Chart(dev_per_position_pipeline).mark_bar()

    # Apply the encoding with the correct ordering.
    _dev_trait_pipeline_encode = _dev_trait_pipeline_base.encode(
        x=_x_axis,
        y=alt.Y("count:Q", title="Players"),
        color=alt.Color(
            "dev_trait:N",
            title="Dev Trait",
            scale=alt.Scale(
                domain=["elite", "star", "impact", "normal"],
                range=[color_1, color_2, color_3, color_4],
            ),
            sort={"field": "dev_trait_order"},
        ),
        order="dev_trait_order:O",
        tooltip=[
            alt.Tooltip("position:N", title="Position"),
            alt.Tooltip("count:Q", title="Players"),
            alt.Tooltip("dev_trait:N", title="Dev Trait"),
            alt.Tooltip("class:N", title="Class"),
        ],
    ).properties(width=width_position, height=height_pipeline)

    # Apply the faceting with the correct ordering.
    _dev_trait_pipeline_chart = (
        _dev_trait_pipeline_encode.facet(
            row=alt.Row(
                "class:N",
                sort={"field": "class_order"},
                title="Class",
            ),
        )
        .properties(
            title={
                "text": f"{season} Player Dev Trait Pipeline per Position",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
        .configure_view(stroke=None)
    )

    if running_locally:
        # Save the charts as images.
        _dev_trait_chart.save(
            season_path / f"{season}_dev_per_position_{university}.png", scale_factor=2.0
        )
        _star_elite_chart.save(
            season_path / f"{season}_star_elite_per_position_{university}.png",
            scale_factor=2.0,
        )
        _dev_trait_pipeline_chart.save(
            season_path / f"{season}_dev_per_position_pipeline_{university}.png",
            scale_factor=2.0,
        )
    else:
        print("Skipped saving chart as an image since app is running as a WASM app.")

    # Create list of charts for a carousel UI element.
    carousel_per_position = [
        mo.ui.altair_chart(_dev_trait_chart),
        mo.ui.altair_chart(_star_elite_chart),
        mo.ui.altair_chart(_dev_trait_pipeline_chart),
    ]
    return (carousel_per_position,)


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""#### Dev Traits per Group""") if running_locally else None
    return


@app.cell
def _(
    class_order,
    classes,
    dev_trait_order,
    dev_traits,
    group_order,
    groups,
    pl,
    roster_with_order,
):
    # dev_per_group and star_elite_per_group -----------------------------------------
    # All possible combinations of groups and dev traits via cartesian product (cross
    # join).
    _group_dev_combos = groups.join(dev_traits, how="cross")

    # Counts of dev traits per group, the minimal set (i.e. does not include dev trait
    # and group combos that have a count of 0).
    _min_dev_per_group = roster_with_order.group_by(["group", "dev_trait"]).len("count")

    # Counts of dev traits per group including rows where there are no players of a given
    # group dev trait combination, the maximal set.
    dev_per_group = (
        _group_dev_combos.join(_min_dev_per_group, how="left", on=["group", "dev_trait"])
        .with_columns(
            pl.col("count").fill_null(0),
            pl.col("group").replace_strict(group_order).alias("group_order"),
            pl.col("dev_trait").replace_strict(dev_trait_order).alias("dev_trait_order"),
        )
        .sort(["group_order", "dev_trait_order"])
    )

    # Counts of star and elite dev traits per group including rows where there are no
    # players of a given group-star or group-elite combination.
    star_elite_per_group = dev_per_group.filter(
        pl.col("dev_trait").is_in(["elite", "star"])
    )

    # dev_per_group_pipeline ------------------------------------------------------------
    # All possible combinations of groups, dev traits, and classes via cartesian product
    # (cross join). The product is formed via cross join of `_group_dev_combos` with
    # `classes`.
    _group_dev_class_combos = _group_dev_combos.join(classes, how="cross")

    # Counts of dev traits per group per class, the minimal set (i.e. does not include
    # dev trait, group, and class combos that have a count of 0).
    _min_dev_per_group_pipeline = roster_with_order.group_by(
        ["group", "dev_trait", "class"]
    ).len("count")

    # Counts of dev traits per group per class including rows where there are no players
    # of a given group, dev trait, and class combination; the maximal set.
    dev_per_group_pipeline = (
        _group_dev_class_combos.join(
            _min_dev_per_group_pipeline,
            how="left",
            on=["group", "dev_trait", "class"],
        )
        .with_columns(
            pl.col("count").fill_null(0),
            pl.col("group").replace_strict(group_order).alias("group_order"),
            pl.col("dev_trait").replace_strict(dev_trait_order).alias("dev_trait_order"),
            pl.col("class").replace_strict(class_order).alias("class_order"),
        )
        .sort(["group_order", "dev_trait_order", "class_order"])
    )
    return dev_per_group, dev_per_group_pipeline, star_elite_per_group


@app.cell
def _(
    alt,
    anchor,
    color_1,
    color_2,
    color_3,
    color_4,
    dev_per_group,
    dev_per_group_pipeline,
    height_pipeline,
    mo,
    running_locally,
    season,
    season_path,
    star_elite_per_group,
    title_font_size,
    university,
    width_group,
):
    # Define shared plot properties.
    _x_axis = alt.X(
        "group:N",
        title="Group",
        axis=alt.Axis(labelAngle=0),
        sort={"field": "group_order"},
    )
    _y_axis_title = "Players"
    _legend_title = "Dev Trait"

    # Dev traits per group chart -----------------------------------------------------------
    _dev_trait_chart = (
        alt.Chart(dev_per_group)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(format="d"),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star", "impact", "normal"],
                    range=[color_1, color_2, color_3, color_4],
                ),
                sort={"field": "dev_trait_order"},
            ),
            order="dev_trait_order:O",
            tooltip=[
                alt.Tooltip("group:N", title="Group"),
                alt.Tooltip("count:Q", title="Players"),
                alt.Tooltip("dev_trait:N", title="Dev Trait"),
            ],
        )
        .properties(
            width=width_group,
            height=330,
            title={
                "text": f"{season} Player Dev Traits per Group",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Star and elite players per group chart -----------------------------------------------
    _star_elite_chart = (
        alt.Chart(star_elite_per_group)
        .mark_bar()
        .encode(
            x=_x_axis,
            y=alt.Y(
                "count:Q",
                title=_y_axis_title,
                axis=alt.Axis(format="d"),
            ),
            color=alt.Color(
                "dev_trait:N",
                title=_legend_title,
                scale=alt.Scale(
                    domain=["elite", "star"],
                    range=[color_1, color_2],
                ),
                sort={"field": "dev_trait_order"},
            ),
            order="dev_trait_order:O",
            tooltip=[
                alt.Tooltip("group:N", title="Group"),
                alt.Tooltip("count:Q", title="Players"),
                alt.Tooltip("dev_trait:N", title="Dev Trait"),
            ],
        )
        .properties(
            width=width_group,
            height=260,
            title={
                "text": f"{season} Star / Elite Players per Group",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
    )

    # Dev traits per group pipeline chart --------------------------------------------------
    # Build the pipeline chart in stages due to issues with ordering. Apply ordering in both
    # the encode and facet steps to ensure the correct ordering is kept in the final chart.
    _dev_trait_pipeline_base = alt.Chart(dev_per_group_pipeline).mark_bar()

    # Apply the encoding with the correct ordering.
    _dev_trait_pipeline_encode = _dev_trait_pipeline_base.encode(
        x=_x_axis,
        y=alt.Y("count:Q", title="Players"),
        color=alt.Color(
            "dev_trait:N",
            title="Dev Trait",
            scale=alt.Scale(
                domain=["elite", "star", "impact", "normal"],
                range=[color_1, color_2, color_3, color_4],
            ),
            sort={"field": "dev_trait_order"},
        ),
        order="dev_trait_order:O",
        tooltip=[
            alt.Tooltip("group:N", title="Group"),
            alt.Tooltip("count:Q", title="Players"),
            alt.Tooltip("dev_trait:N", title="Dev Trait"),
            alt.Tooltip("class:N", title="Class"),
        ],
    ).properties(width=width_group, height=height_pipeline)

    # Apply the faceting with the correct ordering.
    _dev_trait_pipeline_chart = (
        _dev_trait_pipeline_encode.facet(
            row=alt.Row(
                "class:N",
                sort={"field": "class_order"},
                title="Class",
            ),
            # spacing=40,
        ).properties(
            title={
                "text": f"{season} Player Dev Trait Pipeline per Group",
                "fontSize": title_font_size,
                "anchor": anchor,
            },
        )
        # .configure_view(stroke=None)
    )

    if running_locally:
        # Save the charts as images.
        _dev_trait_chart.save(
            season_path / f"{season}_dev_per_group_{university}.png", scale_factor=2.0
        )
        _star_elite_chart.save(
            season_path / f"{season}_star_elite_per_group_{university}.png",
            scale_factor=2.0,
        )
        _dev_trait_pipeline_chart.save(
            season_path / f"{season}_dev_per_group_pipeline_{university}.png",
            scale_factor=2.0,
        )
    else:
        print("Skipped saving chart as an image since app is running as a WASM app.")

    # Create list of charts for a carousel UI element.
    carousel_per_group = [
        mo.ui.altair_chart(_dev_trait_chart),
        mo.ui.altair_chart(_star_elite_chart),
        mo.ui.altair_chart(_dev_trait_pipeline_chart),
    ]
    return (carousel_per_group,)


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""#### Display Dev Trait Charts""") if running_locally else None
    return


@app.cell
def _(carousel_per_group, carousel_per_position, mo, player_classes_chart):
    mo.ui.tabs(
        {
            "Class Distribution": mo.carousel(
                [mo.hstack([player_classes_chart], justify="center")]
            ),
            "Dev Traits per Position": mo.carousel(
                [mo.hstack([chart], justify="center") for chart in carousel_per_position]
            ),
            "Dev Traits per Group": mo.carousel(
                [mo.hstack([chart], justify="center") for chart in carousel_per_group]
            ),
        }
    )
    return


@app.cell
def _(mo):
    overall_slider = mo.ui.slider(start=80, stop=99, step=1, value=85)
    return (overall_slider,)


@app.cell(hide_code=True)
def _(mo, overall_slider):
    mo.md(
        f"""
        ### Potential Non-Senior Drafted Players
        Each season, in addition to the seniors leaving the roster via graduation, there is the potential to lose strongly performing underclassman to the NFL draft. In this analysis, the stand in for performance will be the player's overall rating, specifically the `overall_start` rating which is collected in the preseason. The player's class also matters as the player needs to be in their third year of eligibility in order to declare for the draft.

        In CFB 25, overall ratings in the high 80s are where players start to declare for the draft if eligible. Since the ratings used in the dataframe are from the preseason, and player development during the season (an increase in their overall) is common, a slider is provided to adjust the minimum rating cutoff. The bullet points below summarize the filters that are applied to get the dataframe of potential non-senior drafted players.

        - non-senior
        - draft eligible - true junior, redshirt junior, or redshirt sophomore
        - {overall_slider} **{overall_slider.value} `overall_start` or higher**

        > Note: the dataframe is sorted first by `group`, then `position`, then `overall_start`.
        """
    )
    return


@app.cell(hide_code=True)
def _(overall_slider, pl, roster):
    _draft_eligible_non_senior = (pl.col("class") == "JR") | (
        (pl.col("class") == "SO") & (pl.col("red_shirt") == True)
    )

    roster.filter(
        _draft_eligible_non_senior & (pl.col("overall_start") >= overall_slider.value)
    ).drop(["secondary_group", "overall_end"]).sort(
        ["group", "position", "overall_start"], descending=[False, False, True]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### Young Player Quality
        To help with recruiting, it is useful to have an idea of which areas of the team are currently weak. The focus here is on younger players since they are lower on the depth chart and assessing if certain positions or position groups need a boost of talent via recruiting. The list below details the approach for this analysis.

        - A young player will be defined as a freshman or sophomore including redshirted players.
        - The average overall (`overall_start`) of all young players in a given position group is used to assess young player quality at that position group. Position groups are used because this mirrors how recruits are categorized in CFB 25 in the recruiting screen.

        > Note: the dataframe is sorted by `avg_overall_start` from weakest to strongest positions.
        """
    )
    return


@app.cell
def _(mo, pl, roster):
    _young_players = roster.filter(pl.col("class").is_in(["FR", "SO"]))

    mo.ui.table(
        _young_players.group_by("group")
        .agg(
            pl.col("overall_start").mean().round(1).alias("avg_overall_start"),
            pl.len().alias("count"),
        )
        .sort(["avg_overall_start", "count"]),
        pagination=False,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### Players to Cut
        College football teams need to have 85 players rostered at the start of the preseason. Because the number of players leaving at the end of each season is normally less than the number of incoming recruits, cuts have to be made. The `marimo` table below contains the roster with the seniors removed since they will already be leaving due to graduation (unless of course they are redshirted as a senior which is rare in CFB 25).

        > Note: to create the selection of cuts, click the checkbox of any players you plan on cutting. Then use the **Download** button in the bottom right to save the selection as a CSV or JSON file for reference later when doing the actual cuts.
        """
    )
    return


@app.cell
def _(mo, pl, roster):
    potential_cut_roster = roster.filter(pl.col("class") != "SR").drop(
        ["secondary_group", "team", "overall_end"]
    )
    mo.ui.table(potential_cut_roster)
    return (potential_cut_roster,)


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""## Appendix""") if running_locally else None
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    # Check if the notebook is running locally.
    running_locally = mo.notebook_dir() == mo.notebook_location()
    print(f"Running WASM version of app: {not running_locally}")

    # If this is the WASM version of the app then `micropip` will need to be imported to
    # install `openpyxl`.
    if not running_locally:
        import micropip
    return micropip, running_locally


@app.cell(hide_code=True)
async def _(micropip, running_locally):
    from io import BytesIO
    from pathlib import Path

    import altair as alt
    import httpx
    import polars as pl

    # `openpyxl` is needed as the engine to read excel files with `pl.read_excel()`.
    if not running_locally:
        await micropip.install("openpyxl")

    # Set polars to show all rows of a dataframe. Assignment is used to suppress output.
    _ = pl.Config(tbl_rows=-1)
    return BytesIO, Path, alt, httpx, pl


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""### Plot Constants""") if running_locally else None
    return


@app.cell(hide_code=True)
def _(mo, university, university_season_form):
    # Stop execution if the form has not been submitted.
    mo.stop(
        university_season_form.value is None,
        mo.md("**Submit the form above to continue.**"),
    )

    # University color schemes.
    _university_colors = {
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

    # Color variables actually used for plotting.
    color_1 = _university_colors[university]["color_1"]
    color_2 = _university_colors[university]["color_2"]
    color_3 = _university_colors[university]["color_3"]
    color_4 = _university_colors[university]["color_4"]

    # Plot constants.
    width_position = 650
    width_group = 500
    height_pipeline = 90
    title_font_size = 14
    anchor = "middle"
    gap = 3
    return (
        anchor,
        color_1,
        color_2,
        color_3,
        color_4,
        gap,
        height_pipeline,
        title_font_size,
        width_group,
        width_position,
    )


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""### Roster Loading Functions""") if running_locally else None
    return


@app.cell(hide_code=True)
def _(BytesIO, Path, httpx, mo, pl):
    PolarsDataType = pl.DataType | type[pl.DataType]


    def load_roster_locally(
        data_path: Path,
        university: str,
        season: str,
        schema_overrides: dict[str, PolarsDataType],
    ) -> pl.DataFrame:
        """Load the roster excel file for `university` and `season` in a local environment.

        Parameters
        ----------
        data_path : Path
            Path to the project's data directory.
        university : str
            Name of the university being processed.
        season : str
            Season being processed.
        schema_overrides : dict[str, PolarsDataType]
            Dataframe schema.

        Returns
        -------
        pl.DataFrame
            Roster as a dataframe.
        """
        # Path to the roster excel file based on the university chosen for analysis.
        roster_file_path = data_path / "datasets" / f"roster_{university}.xlsx"

        # Create the `roster` dataframe from the local excel file.
        try:
            roster = pl.read_excel(
                roster_file_path,
                sheet_name=season,
                schema_overrides=schema_overrides,
            )

            print(
                f"The {season} roster for {' '.join(university.split('_')).title()} was loaded successfully."
            )

            return roster

        except (ValueError, FileNotFoundError) as e:
            print(e)
            mo.stop(
                True,
                mo.md("**Failed to load roster data from local file. Execution halted.**"),
            )


    def load_roster_from_github_repo(
        university: str,
        season: str,
        schema_overrides: dict[str, PolarsDataType],
    ) -> pl.DataFrame:
        """Load the roster excel file for `university` and `season` in a deployed env.

        Parameters
        ----------
        university : str
            Name of the university being processed.
        season : str
            Season being processed
        schema_overrides : dict[str, PolarsDataType]
            Dataframe schema.

        Returns
        -------
        pl.DataFrame
            Roster as a dataframe.
        """
        # Create the `roster` dataframe from the github repo excel file.
        try:
            # Github repo information.
            gh_user = "cdpeters"
            gh_repo = "cfb-analysis"
            gh_branch = "main"
            gh_domain = "raw.githubusercontent.com"

            # Construct the github url.
            gh_url = f"https://{gh_domain}/{gh_user}/{gh_repo}/{gh_branch}/data/datasets/roster_{university}.xlsx"

            # Retrieve the excel file.
            response = httpx.get(gh_url)
            response.raise_for_status()

            # Load the data from the response.
            excel_data = BytesIO(response.content)
            roster = pl.read_excel(
                excel_data,
                sheet_name=season,
                schema_overrides=schema_overrides,
                engine="openpyxl",
            )

            print(
                f"The {season} roster for {' '.join(university.split('_')).title()} was loaded successfully from the github repo '{gh_repo}'."
            )

            return roster

        except (ValueError, FileNotFoundError, httpx.HTTPStatusError) as e:
            print(e)
            mo.stop(
                True,
                mo.md(
                    f"**Failed to load roster data from the github repo '{gh_repo}'. Execution halted.**"
                ),
            )
    return PolarsDataType, load_roster_from_github_repo, load_roster_locally


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""### Schema""") if running_locally else None
    return


@app.cell(hide_code=True)
def _(pl):
    # Enums for the `class`, `team`, and `dev_trait` columns.
    class_enum = pl.Enum(["FR", "SO", "JR", "SR"])
    # `team_enum` refers to either offense, defense, or special teams.
    team_enum = pl.Enum(["OFF", "DEF", "ST"])
    dev_trait_enum = pl.Enum(["normal", "impact", "star", "elite"])

    # Set up the schema overrides for the columns that need it. The `overall_start` and
    # `overall_end` columns need an override because `polars` does not infer the column as
    # an integer for roster years that have this data missing.
    schema_overrides = {
        "class": class_enum,
        "position": pl.Categorical(),
        "group": pl.Categorical(),
        "secondary_group": pl.Categorical(),
        "team": team_enum,
        "archetype": pl.Categorical(),
        "dev_trait": dev_trait_enum,
        "overall_start": pl.UInt8,
        "overall_end": pl.UInt8,
    }
    return class_enum, dev_trait_enum, schema_overrides, team_enum


@app.cell(hide_code=True)
def _(mo, running_locally):
    mo.md(r"""### Find Project Path Function""") if running_locally else None
    return


@app.cell(hide_code=True)
def _(Path):
    def find_project_path(project_name: str) -> Path:
        """Find the project path based on the presence of a .git or pyproject.toml file.

        Parameters
        ----------
        project_name : str
            Name of the project directory.

        Returns
        -------
        Path
            Project path.

        Raises
        ------
        FileNotFoundError
            If a project directory with the mark files is not found.
        """
        marker_files = [".git", "pyproject.toml"]
        current_path = Path().cwd()

        # Check current directory.
        if current_path.name == project_name and any(
            (current_path / marker).exists() for marker in marker_files
        ):
            return current_path

        # Check parent directories.
        for parent in current_path.parents:
            if parent.name == project_name and any(
                (parent / marker).exists() for marker in marker_files
            ):
                return parent

        raise FileNotFoundError(
            "Could not find a project directory containing either a .git or pyproject.toml file."
        )
    return (find_project_path,)


if __name__ == "__main__":
    app.run()
