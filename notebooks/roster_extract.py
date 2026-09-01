import marimo

__generated_with = "0.24.0"
app = marimo.App(width="columns")


@app.cell(column=0)
def _():
    # Dynasty screen regions.

    # Dynasty card detection.

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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch Dynasty Functions
    """)
    return


@app.cell
def _(
    BRIGHTNESS_THRESHOLD,
    Button,
    DYNASTY_LIST_REGION,
    DYNASTY_LOAD_TIMEOUT,
    DynastyNotFoundError,
    DynastyOCRReadError,
    DynastySelectionNotFoundError,
    END_OF_LIST_DIFF_THRESHOLD,
    ImageArray,
    MAX_CARD_HEIGHT,
    MAX_CARD_WIDTH,
    MIN_CARD_HEIGHT,
    MIN_CARD_WIDTH,
    MORPH_KERNEL_HEIGHT,
    MORPH_KERNEL_WIDTH,
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
    get_controller,
    logger,
    np,
    pytesseract,
    re,
    time,
):
    def find_selected_dynasty_card(frame: ImageArray) -> Region:
        """Locate the white highlighted dynasty card in a full-screen frame."""
        left, top, right, bottom = DYNASTY_LIST_REGION
        dynasty_list_frame = frame[top:bottom, left:right]

        gray_frame = cv2.cvtColor(dynasty_list_frame, cv2.COLOR_BGRA2GRAY)

        # The selected card has a very bright background compared with the
        # unselected dark-gray cards.
        _, mask = cv2.threshold(
            gray_frame, BRIGHTNESS_THRESHOLD, 255, cv2.THRESH_BINARY
        )

        # Join text/logo holes into the surrounding white card.
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (MORPH_KERNEL_WIDTH, MORPH_KERNEL_HEIGHT)
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates: list[tuple[int, int, int, int]] = []

        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)

            # Intentionally broad ranges initially. Tune from actual captures.
            if (
                MIN_CARD_WIDTH <= width <= MAX_CARD_WIDTH
                and MIN_CARD_HEIGHT <= height <= MAX_CARD_HEIGHT
            ):
                candidates.append((x, y, width, height))

        if not candidates:
            raise DynastySelectionNotFoundError(
                "Could not locate the highlighted dynasty card."
            )

        # The real card should normally be the largest qualifying bright rectangle.
        x, y, width, height = max(
            candidates,
            key=lambda box: box[2] * box[3],
        )

        return (
            left + x,
            top + y,
            left + x + width,
            top + y + height,
        )

    def get_dynasty_name_region(card_region: Region) -> Region:
        """Return the dynasty-name-line region within a selected save card."""
        left, top, right, bottom = card_region

        width = right - left
        height = bottom - top

        return (
            left + int(width * 0.10),
            top + int(height * 0.66),
            left + int(width * 0.82),
            top + int(height * 0.95),
        )

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
    - [ ] Complete the button sequence to get to the list of dynasties.
    - [ ] Use OCR to select the dynasty by name.
    - [ ] When the list of dynasties on the "load dynasty" screen is small enough, does the scoll bar still show up? Handle this edge case when the scroll bar is not visible.
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
    )
    from cfb_pipeline.controller import Button
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
    from cfb_pipeline.devtools.cv2_tuning import (
        create_frame_slider,
        show_tuning_result,
        measure_frame_contours,
    )
    from cfb_pipeline.devtools.dynasty import process_dynasty_test_frame

    mo.Html("""
    <style>
    .output-area {
        max-height: none !important;
    }
    </style>
    """)
    return (
        BRIGHTNESS_THRESHOLD,
        Button,
        DYNASTY_LIST_IMAGES_DIR,
        DYNASTY_LIST_REGION,
        DynastyNotFoundError,
        DynastyOCRReadError,
        DynastySelectionNotFoundError,
        ImageArray,
        MAX_CARD_HEIGHT,
        MAX_CARD_WIDTH,
        MIN_CARD_HEIGHT,
        MIN_CARD_WIDTH,
        MORPH_KERNEL_HEIGHT,
        MORPH_KERNEL_WIDTH,
        Region,
        SCROLLBAR_REGION,
        Templates,
        capture_frame,
        cast,
        create_frame_slider,
        cv2,
        cv2_to_pil,
        focus_first_game_tile,
        get_controller,
        launch_cfb_game,
        launch_chiaki,
        load_frames,
        logger,
        measure_frame_contours,
        mo,
        np,
        process_dynasty_test_frame,
        pytesseract,
        re,
        show_tuning_result,
        time,
    )


@app.cell(column=1, hide_code=True)
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
    controller.tap(Button.DPAD_DOWN)
    # controller.tap(Button.DPAD_UP)
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
    dynasty_test_frames,
    frame_index,
    process_dynasty_test_frame,
    show_tuning_result,
):
    path, frame = dynasty_test_frames[frame_index.value]

    result = process_dynasty_test_frame(frame)

    show_tuning_result(
        slider=frame_index,
        frame_path=path,
        result=result,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Measurements Table
    """)
    return


@app.cell
def _(dynasty_test_frames, measure_frame_contours, process_dynasty_test_frame):
    contour_measurements = measure_frame_contours(
        dynasty_test_frames,
        process_dynasty_test_frame,
        min_width=100,
        min_height=40,
    )

    contour_measurements
    return


@app.cell
def _(DYNASTY_LIST_REGION):
    DYNASTY_LIST_REGION
    return


@app.cell
def _(DYNASTY_LIST_REGION, cv2_to_pil, dynasty_test_frames, mo):
    left, top, right, bottom = DYNASTY_LIST_REGION
    selected_card_frame = dynasty_test_frames[5][1][top+473:top+473+135, left+23:left+23+592]

    mo.image(
        cv2_to_pil(selected_card_frame),
        caption=f"Selected dynasty card — {592}x{135}",
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
