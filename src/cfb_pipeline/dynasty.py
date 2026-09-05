import re
import time
from typing import cast

import cv2
import numpy as np
import pytesseract
from loguru import logger

from .capture import capture_frame
from .config import (
    BRIGHTNESS_THRESHOLD,
    DYNASTY_LIST_REGION,
    DYNASTY_LOAD_TIMEOUT,
    DYNASTY_NAME_BOTTOM_OFFSET,
    DYNASTY_NAME_LEFT_OFFSET,
    DYNASTY_NAME_RIGHT_OFFSET,
    DYNASTY_NAME_TOP_OFFSET,
    END_OF_LIST_DIFF_THRESHOLD,
    MAX_CARD_HEIGHT,
    MAX_CARD_WIDTH,
    MIN_CARD_HEIGHT,
    MIN_CARD_WIDTH,
    MORPH_KERNEL_HEIGHT,
    MORPH_KERNEL_WIDTH,
    OCR_CONFIRMATION_FRAMES,
    OCR_CONFIRMATION_REQUIRED,
    OCR_SCALE_FACTOR,
    SCROLLBAR_BOTTOM_THRESHOLD,
    SCROLLBAR_BRIGHTNESS_THRESHOLD,
    SCROLLBAR_REGION,
)
from .controller import Button
from .exceptions import (
    DynastyNotFoundError,
    DynastyOCRReadError,
    DynastySelectionNotFoundError,
)
from .runtime import get_controller
from .types import ImageArray, Region


def find_selected_dynasty_card(frame: ImageArray) -> Region:
    """Locate the currently highlighted dynasty card."""

    # ==========================================
    # 1. Crop to the dynasty-list screen region
    # ==========================================
    # Limit image processing to the portion of the screen where dynasty
    # cards can appear. This reduces noise from unrelated UI elements.
    left, top, right, bottom = DYNASTY_LIST_REGION
    list_frame = frame[top:bottom, left:right]

    # ======================================
    # 2. Convert the list image to grayscale
    # ======================================
    # Brightness is what distinguishes the selected white card from the
    # darker unselected cards, so color information is unnecessary here.
    gray_frame = cv2.cvtColor(list_frame, cv2.COLOR_BGRA2GRAY)

    # ==========================================
    # 3. Create a binary mask of bright regions
    # ==========================================
    # Pixels brighter than BRIGHTNESS_THRESHOLD become white (255);
    # all others become black (0). The selected card should therefore
    # appear as a large white region in the resulting mask.
    _, mask_frame = cv2.threshold(
        gray_frame, BRIGHTNESS_THRESHOLD, 255, cv2.THRESH_BINARY
    )

    # ============================================
    # 4. Join gaps within the selected card region
    # ============================================
    # Text, logos, and icons create dark holes inside the white card.
    # Morphological closing fills/bridges small gaps so the selected card
    # is more likely to be detected as one contiguous white object.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (MORPH_KERNEL_WIDTH, MORPH_KERNEL_HEIGHT)
    )

    closed_frame = cv2.morphologyEx(mask_frame, cv2.MORPH_CLOSE, kernel)

    # ==================================
    # 5. Find the outer white boundaries
    # ==================================
    # Each contour represents the outline of a connected white object in
    # the processed mask. RETR_EXTERNAL ignores nested/internal contours
    # because only the outer boundary of each object matters here.
    contours, _ = cv2.findContours(
        closed_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # ==========================================
    # 6. Filter contours by dynasty-card geometry
    # ==========================================
    # Convert each contour to a rectangular bounding box and keep only
    # objects whose width and height fall within the expected card range.
    #
    # OpenCV bounding rectangles use:
    #     (x, y, width, height)
    #
    # where x/y are relative to `list_frame`, not the full screen.
    candidates: list[tuple[int, int, int, int]] = []

    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)

        if (
            MIN_CARD_WIDTH <= width <= MAX_CARD_WIDTH
            and MIN_CARD_HEIGHT <= height <= MAX_CARD_HEIGHT
        ):
            candidates.append((x, y, width, height))

    # ==============================================
    # 7. Require exactly one selected-card candidate
    # ==============================================
    # The UI guarantees that exactly one dynasty card is selected at a
    # time. Zero candidates means detection failed; multiple candidates
    # means the filtering criteria are ambiguous and should not be trusted.
    if len(candidates) != 1:
        raise DynastySelectionNotFoundError(
            f"Expected exactly one selected dynasty card; found {len(candidates)}."
        )

    x, y, width, height = candidates[0]

    # =========================================
    # 8. Convert back to full-screen coordinates
    # =========================================
    # Candidate coordinates are relative to the cropped dynasty-list
    # frame. Add the list-region offsets to return the card's full screen
    # (left, top, right, bottom) coordinates.
    return (
        left + x,
        top + y,
        left + x + width,
        top + y + height,
    )

def get_dynasty_name_region(card_region: Region) -> Region:
    """Return the dynasty-name-line region within a selected save card."""
    left, top, _, _ = card_region

    return (
        left + DYNASTY_NAME_LEFT_OFFSET,
        top + DYNASTY_NAME_TOP_OFFSET,
        left + DYNASTY_NAME_RIGHT_OFFSET,
        top + DYNASTY_NAME_BOTTOM_OFFSET,
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
        rest_time=1.2,
    )

    for _ in range(3):
        controller.tap(Button.DPAD_DOWN)

    controller.tap(
        Button.CROSS,
        rest_time=7.0,
    )
