import marimo

__generated_with = "0.11.13"
app = marimo.App(
    width="medium",
    css_file="C:\\Users\\cdpet\\Documents\\Post School Coursework\\dev-materials\\configs\\marimo\\theme\\custom-theme.css",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        # 🏈 College Football 25 Dynasty Roster Analysis 🏈

        The following app can be used to explore your College Football 25 dynasty roster. The UI elements are interactive, feel free to interact with an element's controls to see new views of the data.

        ### Analysis Sections
        #### Roster Viewer
        - The **Roster Viewer** allows you to transform the view of the roster including filtering, grouping, aggregating, and sorting among other operations. 
        #### Exploratory Analysis
        - This section contains charts as well as tables with specific filters and/or aggregations applied and includes:
            - Charts:
                - **Player Class Distribution**
                - **Dev Traits per Position**
                - **Dev Traits per Group**
            - Tables:
                - **Possible Non-Senior Drafted Players**
                - **Young Player Quality**
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


@app.cell
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
    mo.md(r"""## Roster Viewer""")
    return


@app.cell(hide_code=True)
def _(mo, roster):
    mo.ui.dataframe(roster, page_size=17)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Exploratory Analysis""")
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
    running_locally,
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

    if running_locally:
        # Save the chart as an image.
        _player_classes_chart.save(
            season_path / f"{season}_player_classes_{university}.png", scale_factor=2.0
        )
    else:
        print(
            "Skipped saving chart as an image since app is running as a static github page."
        )

    mo.vstack([mo.ui.altair_chart(_player_classes_chart)], align="center")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Dev Traits per Position""")
    return


@app.cell
def _(dev_traits, pl, positions, roster):
    # Dataframe of the cross join (cartesian product) of all positions with all dev traits.
    _position_dev_combos = positions.join(dev_traits, how="cross")

    # Minimal set of dev traits per position (does not include dev trait and position combos
    # that have a count of 0).
    min_dev_per_position = (
        roster.group_by(["position", "dev_trait"])
        .len("count")
        .sort(["position", "dev_trait"])
    )

    # All dev traits per position including rows where there are no players of a given
    # position-dev combination. This is the maximal set of dev traits per position.
    dev_per_position = _position_dev_combos.join(
        min_dev_per_position, how="left", on=["position", "dev_trait"]
    ).fill_null(0)

    # All star and elite dev traits per position including rows where there are no players
    # of a given position-star or position-elite combination.
    star_elite_per_position = dev_per_position.filter(
        pl.col("dev_trait").is_in(["elite", "star"])
    )

    # All dev traits per position per class.
    dev_per_position_pipeline = roster.filter(pl.col("dev_trait").is_not_null())
    dev_per_position_pipeline = dev_per_position_pipeline.group_by(
        ["position", "class", "dev_trait"]
    ).len("count")
    dev_per_position_pipeline = dev_per_position_pipeline.join(
        dev_traits, how="left", on="dev_trait"
    )
    return (
        dev_per_position,
        dev_per_position_pipeline,
        min_dev_per_position,
        star_elite_per_position,
    )


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
    running_locally,
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

    if running_locally:
        # Save the charts as images.
        _dev_trait_chart.save(
            season_path / f"{season}_dev_per_position_{university}.png", scale_factor=2.0
        )
        _star_elite_chart.save(
            season_path / f"{season}_star_elite_per_position_{university}.png",
            scale_factor=2.0,
        )
        _dev_per_position_pipeline_chart.save(
            season_path / f"{season}_dev_per_position_pipeline_{university}.png",
            scale_factor=2.0,
        )
    else:
        print(
            "Skipped saving chart as an image since app is running as a static github page."
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
    mo.md("""### Dev Traits per Group""")
    return


@app.cell
def _(dev_traits, groups, pl, roster):
    # Dataframe of the cross join (cartesian product) of all groups with all dev traits.
    _group_dev_combos = groups.join(dev_traits, how="cross")

    # Minimal set of dev traits per group (does not include dev trait and group combos that
    # have a count of 0).
    dev_per_group = (
        roster.group_by(["group", "dev_trait"]).len("count").sort(["group", "dev_trait"])
    )

    # All dev traits per group including rows where there are no players of a given
    # group-dev combination. This is the maximal set of dev traits per group.
    dev_per_group = _group_dev_combos.join(
        dev_per_group, how="left", on=["group", "dev_trait"]
    ).fill_null(0)

    # All star and elite dev traits per group including rows where there are no players of a
    # given group-star or group-elite combination.
    star_elite_per_group = dev_per_group.filter(
        pl.col("dev_trait").is_in(["elite", "star"])
    )

    # All dev traits per group per class.
    dev_per_group_pipeline = roster.filter(pl.col("dev_trait").is_not_null())
    dev_per_group_pipeline = dev_per_group_pipeline.group_by(
        ["group", "class", "dev_trait"]
    ).len("count")
    dev_per_group_pipeline = dev_per_group_pipeline.join(
        dev_traits, how="left", on="dev_trait"
    )
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
    running_locally,
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

    if running_locally:
        # Save the charts as images.
        _dev_trait_chart.save(
            season_path / f"{season}_dev_per_group_{university}.png", scale_factor=2.0
        )
        _star_elite_chart.save(
            season_path / f"{season}_star_elite_per_group_{university}.png",
            scale_factor=2.0,
        )
        _dev_per_group_pipeline_chart.save(
            season_path / f"{season}_dev_per_group_pipeline_{university}.png",
            scale_factor=2.0,
        )
    else:
        print(
            "Skipped saving chart as an image since app is running as a static github page."
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
    overall_slider = mo.ui.slider(start=80, stop=99, step=1, value=85)
    return (overall_slider,)


@app.cell(hide_code=True)
def _(mo, overall_slider):
    mo.md(
        f"""
        ### Possible Non-Senior Drafted Players
        #### Qualifications
        - non-senior
        - draft eligible - a true junior, redshirt junior, or a redshirt sophomore
        - {overall_slider} **{overall_slider.value} `overall_start` or higher**
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
    ).sort("overall_start", descending=True)
    return


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


@app.cell(hide_code=True)
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
    mo.md(r"""## Appendix""")
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    # Check if the notebook is running locally.
    running_locally = mo.notebook_dir() == mo.notebook_location()
    print(f"Running WASM version of app: {not running_locally}")

    # If this is the WASM version of the app then `micropip` will need to be imported to
    # install `openpyxl`.
    if not running_locally:
        import micropip
    return micropip, running_locally


@app.cell
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
def _(mo):
    mo.md(r"""### Plot Constants""")
    return


@app.cell
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
        width,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Roster Loading Functions""")
    return


@app.cell
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
def _(mo):
    mo.md(r"""### Schema""")
    return


@app.cell
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
def _(mo):
    mo.md(r"""### Find Project Path Function""")
    return


@app.cell
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
