import re
import time

import cv2
import numpy as np
import pytesseract
from loguru import logger

from cfb_pipeline.capture import capture_frame
from cfb_pipeline.config import (
    DYNASTY_LIST_REGION,
    DYNASTY_LOAD_TIMEOUT,
    END_OF_LIST_DIFF_THRESHOLD,
    OCR_CONFIRMATION_FRAMES,
    OCR_CONFIRMATION_REQUIRED,
    SCROLLBAR_REGION,
)
from cfb_pipeline.controller import Button
from cfb_pipeline.exceptions import (
    DynastyNotFoundError,
    DynastyOCRReadError,
    DynastySelectionNotFoundError,
)
from cfb_pipeline.types import ImageArray, Region


def find_selected_dynasty_card(frame: ImageArray) -> Region:
    """Locate the white highlighted dynasty card in a full-screen frame."""
    left, top, right, bottom = DYNASTY_LIST_REGION
    dynasty_list_frame = frame[top:bottom, left:right]

    gray_frame = cv2.cvtColor(dynasty_list_frame, cv2.COLOR_BGRA2GRAY)

    # The selected card has a very bright background compared with the
    # unselected dark-gray cards.
    _, mask = cv2.threshold(gray_frame, 200, 255, cv2.THRESH_BINARY)

    # Join text/logo holes into the surrounding white card.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 11))
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
        if width >= 450 and 90 <= height <= 180:
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
        fx=3.0,
        fy=3.0,
        interpolation=cv2.INTER_CUBIC,
    )

    blurred = cv2.GaussianBlur(enlarged, (3, 3), 0)

    _, thresholded = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    return thresholded

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
        220,
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
    bottom_threshold = int(region_height * 0.96)

    return lowest_white_pixel >= bottom_threshold

def load_dynasty_by_name(
    target_dynasty_name: str,
    timeout: float = DYNASTY_LOAD_TIMEOUT,
) -> None:
    """Search the dynasty save list and load the requested dynasty."""
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
