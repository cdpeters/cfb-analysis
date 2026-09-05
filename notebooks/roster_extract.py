import marimo

__generated_with = "0.24.0"
app = marimo.App(width="columns")


@app.cell(column=0, hide_code=True)
def _(mo):
    mo.md(r"""
    ### Constants
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Constants
    """)
    return


@app.cell
def _():
    # Scrollbar detection.
    SCROLLBAR_BRIGHTNESS_THRESHOLD = 220
    SCROLLBAR_BOTTOM_THRESHOLD = 0.96

    # OCR.
    OCR_SCALE_FACTOR = 3.0

    OCR_CONFIRMATION_FRAMES = 3
    OCR_CONFIRMATION_REQUIRED = 2

    # Navigation/timing.
    FRAME_CAPTURE_TIMEOUT = 2.0
    DYNASTY_LOAD_TIMEOUT = 30.0

    END_OF_LIST_DIFF_THRESHOLD = 1.5
    return (
        DYNASTY_LOAD_TIMEOUT,
        END_OF_LIST_DIFF_THRESHOLD,
        OCR_CONFIRMATION_FRAMES,
        OCR_CONFIRMATION_REQUIRED,
        OCR_SCALE_FACTOR,
        SCROLLBAR_BOTTOM_THRESHOLD,
        SCROLLBAR_BRIGHTNESS_THRESHOLD,
    )


@app.cell
def _():
    tuning_params = {
        "scale_factor": 6.92,
        "blur_kernel": None,
        "use_otsu_threshold": True,
    }
    return (tuning_params,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch Dynasty Functions
    """)
    return


@app.cell
def _(
    Button,
    DYNASTY_LIST_REGION,
    DYNASTY_LOAD_TIMEOUT,
    DynastyNotFoundError,
    DynastyOCRReadError,
    END_OF_LIST_DIFF_THRESHOLD,
    ImageArray,
    OCR_CONFIRMATION_FRAMES,
    OCR_CONFIRMATION_REQUIRED,
    OCR_SCALE_FACTOR,
    Region,
    SCROLLBAR_BOTTOM_THRESHOLD,
    SCROLLBAR_BRIGHTNESS_THRESHOLD,
    SCROLLBAR_REGION,
    capture_frame,
    cast,
    cv2,
    find_selected_dynasty_card,
    get_controller,
    get_dynasty_name_region,
    logger,
    np,
    pytesseract,
    re,
    time,
):
    def preprocess_dynasty_name_image(frame: ImageArray) -> ImageArray:
        """Prepare a dynasty-name crop for OCR."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

        enlarged = cv2.resize(
            gray,
            None,
            fx=OCR_SCALE_FACTOR,
            fy=OCR_SCALE_FACTOR,
            interpolation=cv2.INTER_CUBIC,
        )

        blurred = cv2.GaussianBlur(enlarged, (3, 3), 0)

        _, thresholded = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        return cast(ImageArray, thresholded)

    def read_dynasty_name(
        frame: ImageArray,
        card_region: Region,
    ) -> str:
        """OCR and return the dynasty name from the selected dynasty card."""
        left, top, right, bottom = get_dynasty_name_region(card_region)
        name_frame = frame[top:bottom, left:right]

        processed = preprocess_dynasty_name_image(name_frame)

        text = pytesseract.image_to_string(
            processed,
            config="--psm 7",
        )

        dynasty_name, _, _ = text.partition("|")

        return normalize_dynasty_name(dynasty_name)

    def read_dynasty_name_with_retries(
        max_attempts: int = 3,
    ) -> str:
        """Retry multi-frame OCR before declaring the selected card unreadable."""
        last_error: DynastyOCRReadError | None = None

        for attempt in range(max_attempts):
            try:
                return read_confirmed_dynasty_name()
            except DynastyOCRReadError as e:
                last_error = e
                logger.debug(
                    f"Dynasty OCR attempt {attempt + 1}/{max_attempts} failed."
                )

        raise DynastyOCRReadError(
            f"Unable to reliably read selected dynasty after {max_attempts} attempts."
        ) from last_error

    def normalize_dynasty_name(name: str) -> str:
        """Normalize OCR text without erasing meaningful name differences."""
        name = name.strip()
        name = re.sub(r"\s+", " ", name)

        return name.casefold()

    def read_confirmed_dynasty_name(
        *,
        samples: int = OCR_CONFIRMATION_FRAMES,
        required_matches: int = OCR_CONFIRMATION_REQUIRED,
    ) -> str:
        """Return a dynasty name only when repeated OCR readings agree."""
        readings: list[str] = []

        for _ in range(samples):
            frame = capture_frame()
            card_region = find_selected_dynasty_card(frame)
            name = read_dynasty_name(
                frame=frame,
                card_region=card_region,
            )

            if name:
                readings.append(name)

            time.sleep(0.1)

        for name in set(readings):
            if readings.count(name) >= required_matches:
                return name

        raise DynastyOCRReadError(f"OCR readings did not reach consensus: {readings!r}")

    def calculate_frame_difference(
        before: ImageArray,
        after: ImageArray,
    ) -> float:
        """Return a normalized visual-difference score between two list images."""
        before_gray = cv2.cvtColor(before, cv2.COLOR_BGRA2GRAY)
        after_gray = cv2.cvtColor(after, cv2.COLOR_BGRA2GRAY)

        before_gray = cv2.GaussianBlur(before_gray, (7, 7), 0)
        after_gray = cv2.GaussianBlur(after_gray, (7, 7), 0)

        difference = cv2.absdiff(before_gray, after_gray)

        return float(np.mean(difference))

    def move_to_next_dynasty() -> bool:
        """
        Move to the next dynasty.

        Return True if the list changed and False if the cursor remained on
        the final dynasty.
        """
        controller = get_controller()
        before = capture_frame(region=DYNASTY_LIST_REGION)

        controller.tap(
            Button.DPAD_DOWN,
            rest_time=0.5,
        )

        after = capture_frame(region=DYNASTY_LIST_REGION)

        difference = calculate_frame_difference(before, after)

        logger.debug(f"Dynasty-list difference after DPAD_DOWN: {difference:.2f}")

        return difference > END_OF_LIST_DIFF_THRESHOLD

    def is_scrollbar_at_bottom(frame: ImageArray) -> bool:
        """Return whether the white scrollbar appears to have reached its bottom."""
        left, top, right, bottom = SCROLLBAR_REGION
        scrollbar = frame[top:bottom, left:right]

        gray = cv2.cvtColor(scrollbar, cv2.COLOR_BGRA2GRAY)

        _, mask = cv2.threshold(
            gray,
            SCROLLBAR_BRIGHTNESS_THRESHOLD,
            255,
            cv2.THRESH_BINARY,
        )

        ys, _ = np.where(mask > 0)

        if ys.size == 0:
            return False

        lowest_white_pixel = int(ys.max())

        # Consider the scrollbar at its bottom when white pixels extend into the
        # final few percent of the calibrated scrollbar region.
        region_height = bottom - top
        bottom_threshold = int(region_height * SCROLLBAR_BOTTOM_THRESHOLD)

        return lowest_white_pixel >= bottom_threshold

    def load_dynasty_by_name(
        target_dynasty_name: str,
        timeout: float = DYNASTY_LOAD_TIMEOUT,
    ) -> None:
        """Search the dynasty save list and load the requested dynasty."""
        controller = get_controller()
        target_name = normalize_dynasty_name(target_dynasty_name)
        deadline = time.monotonic() + timeout
        position = 1

        # CREATE NEW DYNASTY is currently selected. Move onto the first save.
        controller.tap(
            Button.DPAD_DOWN,
            rest_time=0.5,
        )

        while time.monotonic() < deadline:
            logger.debug(f"Evaluating dynasty save {position}...")

            try:
                displayed_name = read_confirmed_dynasty_name()
            except DynastyOCRReadError as e:
                logger.warning(
                    f"Could not obtain stable OCR reading for save {position}: {e}"
                )
            else:
                logger.debug(f"Dynasty save {position}: {displayed_name!r}")

                if displayed_name == target_name:
                    logger.success(f"Target dynasty located: {target_dynasty_name!r}.")

                    controller.tap(
                        Button.CROSS,
                        rest_time=5.0,
                    )
                    return

            # OCR either produced a non-match or couldn't reach consensus.
            # Navigation itself does not depend on OCR.
            moved = move_to_next_dynasty()

            if not moved:
                frame = capture_frame()
                scrollbar_at_bottom = is_scrollbar_at_bottom(frame)

                logger.debug(
                    "DPAD_DOWN produced no meaningful list change. "
                    f"Scrollbar-at-bottom={scrollbar_at_bottom}."
                )

                raise DynastyNotFoundError(
                    f"Dynasty {target_dynasty_name!r} was not found."
                )

            position += 1

        raise DynastyNotFoundError(
            f"Timed out while searching for dynasty "
            f"{target_dynasty_name!r} after {timeout:.1f}s."
        )

    def navigate_to_dynasty_list() -> None:
        """Navigate from the stabilized main menu to the dynasty save list."""
        logger.debug("Navigating to Dynasty mode...")
        controller = get_controller()

        for _ in range(6):
            controller.tap(Button.DPAD_DOWN)

        controller.tap(
            Button.CROSS,
            rest_time=2.0,
        )

        for _ in range(3):
            controller.tap(Button.DPAD_DOWN)

        controller.tap(
            Button.CROSS,
            rest_time=7.0,
        )

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Imports
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### To-Do
    #### Complete the `handle_launch_dynasty` function
    - [x] Complete the button sequence to get to the list of dynasties.
    - [ ] Use OCR to select the dynasty by name.
    - [ ] When the list of dynasties on the "load dynasty" screen is small enough, does the scoll bar still show up? Handle this edge case when the scroll bar is not visible.
    #### Edge Case:
    - [ ] If CFB is running and I go to the PS5 home screen without closing CFB, CFB will still be running. While on the PS5 home screen, if I shut down the PS5 or enter rest mode without closing CFB, CFB will now be in a suspended state. When I turn on the PS5 again, since I wasn't in CFB when I chose to shut down or enter rest mode, the PS5 will land on the home screen. The script will see this as a normal launch sequence as the PS5 settings icon is found. However, when I launch CFB it will resume from its suspended state on whatever screen I was last on. Because this could be any screen and there are no assumptions I can make about it I'm not sure what to do.
    - [ ] for this "suspended state" scenario, it seems that every time I click on CFB from the PS5 home screen I'm immediately taken to the last screen I was on and I see that screen for a second or two before the "Connection Lost" overlay pops up prompting me to sign back in to EA servers. I think this will happen every single time because I don't think EA has an automatic reconnect to EA servers feature when launching from a suspended state. If so, this is what I can look for as another "menu event". Although I did just see a "Connection Error" overlay pop up over the "Connection Lost" overlay, so maybe it is best to just to let the `poll_main_menu_with_interrupts` timeout once, then assume it is the "suspended state" scenario, treat that scenario like an "unclosed game" scenario, attempt to return to the main menu, attempt to close the game and then launch the game. Because we are not 100% certain this would be a "suspended state" scenario, we might have to look for the "Close Game" option on the CFB game tile's options to see if it needs closing. This is assuming the `return_to_home_screen` function does find the PS5 settings icon.
    #### Build the `navigate_to_rosters` function
    - [ ] Build `navigate_to_rosters` to get from the dynasty home screen to the "View Rosters" screen.
    #### Optimize timeouts
    - [ ] add timers to everything to see how long the actions are taking.
    - [ ] run the pipeline several times and collect and average the times.
    - [ ] create a table that shows the name of the timer, the average execution time, and the assigned timeout value.
    - [ ] reduce timeouts where there is a large discrepancy between the timeout and the actual time a given task is taking.
    """)
    return


@app.cell
def _():
    import marimo as mo

    from cfb_pipeline.bootstrap import bootstrap

    bootstrap()

    import re
    import time
    from pathlib import Path
    from typing import cast

    import cv2
    import numpy as np
    import pytesseract
    from loguru import logger

    from cfb_pipeline.capture import capture_frame
    from cfb_pipeline.cfb import launch_cfb_game
    from cfb_pipeline.chiaki import launch_chiaki
    from cfb_pipeline.config import (
        DYNASTY_LIST_REGION,
        SCROLLBAR_REGION,
        BRIGHTNESS_THRESHOLD,
        MORPH_KERNEL_WIDTH,
        MORPH_KERNEL_HEIGHT,
        DYNASTY_LIST_IMAGES_DIR,
        MAX_CARD_HEIGHT,
        MAX_CARD_WIDTH,
        MIN_CARD_WIDTH,
        MIN_CARD_HEIGHT,
        DYNASTY_LIST_IMAGES_DIR,
        DYNASTY_NAME_LEFT_OFFSET,
        DYNASTY_NAME_TOP_OFFSET,
        DYNASTY_NAME_RIGHT_OFFSET,
        DYNASTY_NAME_BOTTOM_OFFSET,
    )
    from cfb_pipeline.controller import Button
    from cfb_pipeline.dynasty import find_selected_dynasty_card, get_dynasty_name_region
    from cfb_pipeline.exceptions import (
        DynastyNotFoundError,
        DynastyOCRReadError,
        DynastySelectionNotFoundError,
    )
    from cfb_pipeline.lifecycle import shutdown_chiaki
    from cfb_pipeline.ps5 import (
        focus_first_game_tile,
        close_active_game,
        return_to_home_screen,
    )
    from cfb_pipeline.runtime import get_controller
    from cfb_pipeline.templates import Templates
    from cfb_pipeline.types import ImageArray, Region
    from cfb_pipeline.devtools.capture import (
        cv2_to_pil,
        load_frames,
        save_frame,
        show_full_frame,
        show_region,
        show_region_overlay,
        show_regions,
    )
    from cfb_pipeline.devtools.image_diagnostics import (
        create_frame_slider,
        show_tuning_result,
        measure_frame_contours,
    )
    from cfb_pipeline.devtools.dynasty import (
        build_selected_dynasty_card_diagnostics,
        build_dynasty_name_ocr_diagnostics,
        measure_dynasty_name_ocr,
    )
    from cfb_pipeline.devtools.geometry import global_to_local_region

    mo.Html("""
    <style>
    .output-area {
        max-height: none !important;
    }
    </style>
    """)
    return (
        Button,
        DYNASTY_LIST_IMAGES_DIR,
        DYNASTY_LIST_REGION,
        DynastyNotFoundError,
        DynastyOCRReadError,
        ImageArray,
        Path,
        Region,
        SCROLLBAR_REGION,
        Templates,
        build_dynasty_name_ocr_diagnostics,
        build_selected_dynasty_card_diagnostics,
        capture_frame,
        cast,
        close_active_game,
        create_frame_slider,
        cv2,
        find_selected_dynasty_card,
        focus_first_game_tile,
        get_controller,
        get_dynasty_name_region,
        launch_cfb_game,
        launch_chiaki,
        load_frames,
        logger,
        measure_dynasty_name_ocr,
        measure_frame_contours,
        mo,
        np,
        pytesseract,
        re,
        return_to_home_screen,
        save_frame,
        show_tuning_result,
        time,
    )


@app.cell(column=1, hide_code=True)
def _(mo):
    mo.md(r"""
    #### Dynasty Name OCR Tuning
    """)
    return


@app.cell
def _(
    build_dynasty_name_ocr_diagnostics,
    dynasty_test_frames,
    frame_index,
    show_tuning_result,
    tuning_params,
):
    _path, _frame = dynasty_test_frames[frame_index.value]

    _result = build_dynasty_name_ocr_diagnostics(_frame, **tuning_params)

    show_tuning_result(
        slider=frame_index,
        frame_path=_path,
        result=_result,
    )
    return


@app.cell
def _(
    dynasty_test_frames,
    expected_names,
    measure_dynasty_name_ocr,
    tuning_params,
):
    dynasty_name_frame = measure_dynasty_name_ocr(
        dynasty_test_frames,
        expected_names,
        **tuning_params,
        tesseract_config=(
            "--psm 7 "
            "-c load_system_dawg=0 "
            "-c load_freq_dawg=0"
        ),
    )
    dynasty_name_frame
    return


@app.cell
def _(Path):
    expected_names = {
        "dynasty_card_position_00.png": "SOCKS SHIRTS DYNASTY",
        "dynasty_card_position_01.png": "CDP0089_19",
        "dynasty_card_position_02.png": "CDP0089_21_APPLE_ORA",
        "dynasty_card_position_03.png": "DYNASTY-NAME",
        "dynasty_card_position_04.png": "CDP0089_18",
        "dynasty_card_position_05.png": "DYNASTY-AUG23-11H44M20-AUTOSAVE",
        "dynasty_card_position_06.png": "ILLINOIS-DYNASTY",
        "dynasty_card_position_07.png": "CDP0089_13",
    }

    TUNING_RESULTS_DIR = Path.cwd() / "tuning_results"
    TUNING_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    return (expected_names,)


@app.cell
def _():
    # dynasty_name_frame.write_csv(
    #     TUNING_RESULTS_DIR
    #     / f"dynasty_name_baseline_grayscale.csv"
    # )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ___

    ### Launch CFB
    """)
    return


@app.cell(disabled=True)
def _(launch_chiaki):
    launch_chiaki()
    return


@app.cell(disabled=True)
def _(Templates, focus_first_game_tile, launch_cfb_game):
    focus_first_game_tile()
    launch_cfb_game(target_config=Templates.CFB_GAME_TITLE)
    return


@app.cell(disabled=True)
def _(get_controller):
    controller = get_controller()
    return (controller,)


@app.cell(disabled=True)
def _(Button, controller):
    controller.tap(Button.CIRCLE)
    return


@app.cell(disabled=True)
def _(Button, controller):
    # controller.tap(Button.DPAD_DOWN)
    controller.tap(Button.DPAD_UP)
    return


@app.cell(disabled=True)
def _(close_active_game, return_to_home_screen):
    return_to_home_screen()
    close_active_game()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Move to load dynasty screen.
    """)
    return


@app.cell(disabled=True)
def _(Button, controller):
    for _ in range(6):
        controller.tap(Button.DPAD_DOWN)

    controller.tap(Button.CROSS, rest_time=1.2)

    for _ in range(3):
        controller.tap(Button.DPAD_DOWN)

    controller.tap(Button.CROSS)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Save Dynasty List Frames
    """)
    return


@app.cell(disabled=True)
def _(Button, DYNASTY_LIST_IMAGES_DIR, capture_frame, controller, save_frame):
    for index in range(8):
        controller.tap(Button.DPAD_DOWN, rest_time=1.5)
        frame = capture_frame()
        save_frame(
            frame, DYNASTY_LIST_IMAGES_DIR / f"dynasty_card_position_0{index}.png"
        )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Tuning CV2 Parameters for Finding Dynasty Save Cards
    """)
    return


@app.cell
def _(DYNASTY_LIST_IMAGES_DIR, create_frame_slider, load_frames):
    dynasty_test_frames = load_frames(DYNASTY_LIST_IMAGES_DIR)

    frame_index = create_frame_slider(
        len(dynasty_test_frames),
        label="Dynasty card position",
    )
    return dynasty_test_frames, frame_index


@app.cell
def _(
    build_selected_dynasty_card_diagnostics,
    dynasty_test_frames,
    frame_index,
    show_tuning_result,
):
    _path, _frame = dynasty_test_frames[frame_index.value]

    _result = build_selected_dynasty_card_diagnostics(_frame)

    show_tuning_result(
        slider=frame_index,
        frame_path=_path,
        result=_result,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Measurements Table
    """)
    return


@app.cell
def _(
    build_selected_dynasty_card_diagnostics,
    dynasty_test_frames,
    measure_frame_contours,
):
    contour_measurements = measure_frame_contours(
        dynasty_test_frames,
        build_selected_dynasty_card_diagnostics,
        min_width=100,
        min_height=40,
    )

    contour_measurements
    return


if __name__ == "__main__":
    app.run()
