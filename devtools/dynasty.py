from typing import cast

import cv2

from cfb_pipeline.config import (
    BRIGHTNESS_THRESHOLD,
    DYNASTY_LIST_REGION,
    MAX_CARD_HEIGHT,
    MAX_CARD_WIDTH,
    MIN_CARD_HEIGHT,
    MIN_CARD_WIDTH,
    MORPH_KERNEL_HEIGHT,
    MORPH_KERNEL_WIDTH,
)
from cfb_pipeline.types import ImageArray
from devtools.cv2_tuning import (
    TuningResult,
    TuningStage,
    draw_contour_candidates,
    draw_contours,
)


def process_dynasty_test_frame(
    frame: ImageArray,
) -> TuningResult:
    """Process a dynasty test frame and return diagnostic tuning stages."""
    left, top, right, bottom = DYNASTY_LIST_REGION

    dynasty_list_frame = frame[
        top:bottom,
        left:right,
    ]

    dynasty_list_gray = cv2.cvtColor(
        dynasty_list_frame,
        cv2.COLOR_BGRA2GRAY,
    )

    _, dynasty_list_mask = cv2.threshold(
        dynasty_list_gray,
        BRIGHTNESS_THRESHOLD,
        255,
        cv2.THRESH_BINARY,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (
            MORPH_KERNEL_WIDTH,
            MORPH_KERNEL_HEIGHT,
        ),
    )

    dynasty_list_closed = cv2.morphologyEx(
        dynasty_list_mask,
        cv2.MORPH_CLOSE,
        kernel,
    )

    contours, _ = cv2.findContours(
        dynasty_list_closed,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    contour_preview = draw_contours(
        dynasty_list_frame,
        contours,
        min_width=100,
        min_height=40,
    )

    candidate_preview = draw_contour_candidates(
        dynasty_list_frame,
        contours,
        min_width=MIN_CARD_WIDTH,
        max_width=MAX_CARD_WIDTH,
        min_height=MIN_CARD_HEIGHT,
        max_height=MAX_CARD_HEIGHT,
    )

    dynasty_list_mask = cast(ImageArray, dynasty_list_mask)
    dynasty_list_closed = cast(ImageArray, dynasty_list_closed)

    return TuningResult(
        stages=[
            TuningStage(
                name="Raw Region",
                image=dynasty_list_frame,
                caption="Raw dynasty list region",
            ),
            TuningStage(
                name="Brightness Threshold",
                image=dynasty_list_mask,
                caption=(
                    "Brightness threshold "
                    f"({BRIGHTNESS_THRESHOLD})"
                ),
            ),
            TuningStage(
                name="Morphological Closing",
                image=dynasty_list_closed,
                caption=(
                    "Morphological closing "
                    f"({MORPH_KERNEL_WIDTH}x{MORPH_KERNEL_HEIGHT})"
                ),
            ),
            TuningStage(
                name="Contours",
                image=contour_preview,
                caption="Large external contours",
            ),
            TuningStage(
                name="Candidates",
                image=candidate_preview,
                caption="Contours matching dynasty-card dimensions",
            ),
        ],
        contours=contours,
    )
