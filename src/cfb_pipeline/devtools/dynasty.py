from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import cv2
import polars as pl
import pytesseract

from cfb_pipeline.config import (
    BRIGHTNESS_THRESHOLD,
    DYNASTY_LIST_REGION,
    MAX_CARD_HEIGHT,
    MAX_CARD_WIDTH,
    MIN_CARD_HEIGHT,
    MIN_CARD_WIDTH,
    MORPH_KERNEL_HEIGHT,
    MORPH_KERNEL_WIDTH,
    OCR_BLUR_KERNEL,
    OCR_SCALE_FACTOR,
    OCR_USE_OTSU_THRESHOLD, OCR_TESSERACT_CONFIG,
)
from cfb_pipeline.devtools.geometry import global_to_local_region
from cfb_pipeline.devtools.image_diagnostics import (
    TuningResult,
    TuningStage,
    draw_contour_candidates,
    draw_contours,
)
from cfb_pipeline.dynasty import (
    find_selected_dynasty_card,
    get_dynasty_name_region,
    normalize_dynasty_name,
)
from cfb_pipeline.types import ImageArray


@dataclass(slots=True)
class DynastyNameOCRStages:
    raw: ImageArray
    gray: ImageArray
    enlarged: ImageArray
    blurred: ImageArray
    thresholded: ImageArray
    otsu_threshold: float | None

def _build_dynasty_name_ocr_stages(
    frame: ImageArray,
    *,
    scale_factor: float = OCR_SCALE_FACTOR,
    blur_kernel: tuple[int, int] | None = OCR_BLUR_KERNEL,
    use_otsu_threshold: bool = OCR_USE_OTSU_THRESHOLD,
) -> DynastyNameOCRStages:
    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGRA2GRAY,
    )

    if scale_factor == 1.0:
        enlarged = gray
    else:
        enlarged = cv2.resize(
            gray,
            None,
            fx=scale_factor,
            fy=scale_factor,
            interpolation=cv2.INTER_CUBIC,
        )

    if blur_kernel is None:
        blurred = enlarged
    else:
        blurred = cv2.GaussianBlur(
            enlarged,
            blur_kernel,
            0,
        )

    if use_otsu_threshold:
        otsu_threshold, thresholded = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
    else:
        otsu_threshold = None
        thresholded = blurred

    return DynastyNameOCRStages(
        raw=frame,
        gray=cast(ImageArray, gray),
        enlarged=cast(ImageArray, enlarged),
        blurred=cast(ImageArray, blurred),
        thresholded=cast(ImageArray, thresholded),
        otsu_threshold=otsu_threshold,
    )

def build_selected_dynasty_card_diagnostics(
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

def build_dynasty_name_ocr_diagnostics(
    frame: ImageArray,
    *,
    scale_factor: float = OCR_SCALE_FACTOR,
    blur_kernel: tuple[int, int] | None = OCR_BLUR_KERNEL,
    use_otsu_threshold: bool = OCR_USE_OTSU_THRESHOLD,
) -> TuningResult:
    """Build visual diagnostics for dynasty-name OCR processing."""
    card_region = find_selected_dynasty_card(frame)
    name_region = get_dynasty_name_region(card_region)

    card_left, card_top, card_right, card_bottom = card_region
    card_frame = frame[
        card_top:card_bottom,
        card_left:card_right,
    ]

    local_name_region = global_to_local_region(
        name_region,
        card_region,
    )

    name_region_preview = card_frame.copy()

    left, top, right, bottom = local_name_region

    cv2.rectangle(
        name_region_preview,
        (left, top),
        (right, bottom),
        (0, 255, 0, 255),
        2,
    )

    # Crop the dynasty-name region from the full frame.
    left, top, right, bottom = name_region

    name_frame = frame[
        top:bottom,
        left:right,
    ]

    # Build all OCR preprocessing intermediates.
    stages = _build_dynasty_name_ocr_stages(
        name_frame,
        scale_factor=scale_factor,
        blur_kernel=blur_kernel,
        use_otsu_threshold=use_otsu_threshold,
    )

    return TuningResult(
        stages=[
            TuningStage(
                name="Name Region",
                image=name_region_preview,
                caption=(
                    "Dynasty-name region within selected card "
                    f"{local_name_region}"
                ),
            ),
            TuningStage(
                name="Raw Crop",
                image=stages.raw,
                caption=(
                    f"Raw dynasty-name crop "
                    f"({stages.raw.shape[1]}x{stages.raw.shape[0]})"
                ),
            ),
            TuningStage(
                name="Grayscale",
                image=stages.gray,
                caption="Dynasty-name crop converted to grayscale",
            ),
            TuningStage(
                name="Enlarged",
                image=stages.enlarged,
                caption=f"OCR scale factor: {scale_factor}",
            ),
            TuningStage(
                name="Blurred",
                image=stages.blurred,
                caption=(
                    "Gaussian blur: none"
                    if blur_kernel is None
                    else f"Gaussian blur: {blur_kernel[0]}x{blur_kernel[1]}"
                ),
            ),
            TuningStage(
                name="Thresholded",
                image=stages.thresholded,
                caption=(
                    f"Otsu threshold: {stages.otsu_threshold:.1f}"
                    if stages.otsu_threshold is not None
                    else "Otsu threshold: disabled"
                ),
            ),
        ],
    )

def _format_character_count_mismatches(
    actual: str,
    expected: str,
) -> str:
    """Format characters whose occurrence counts differ."""
    actual_counts = Counter(actual)
    expected_counts = Counter(expected)

    mismatches = []

    for character in sorted(actual_counts | expected_counts):
        actual_count = actual_counts[character]
        expected_count = expected_counts[character]

        if actual_count != expected_count:
            mismatches.append(
                f"{character!r}: {actual_count}/{expected_count}"
            )

    return ", ".join(mismatches)

def _classify_dynasty_name_ocr_errors(
    actual: str,
    expected: str,
) -> tuple[bool, bool]:
    """Return whether OCR has whitespace and/or character errors."""
    whitespace_error = actual.count(" ") != expected.count(" ")

    character_error = (
        actual.replace(" ", "")
        != expected.replace(" ", "")
    )

    return whitespace_error, character_error

def measure_dynasty_name_ocr(
    frames: list[tuple[Path, ImageArray]],
    expected_names: dict[str, str],
    *,
    scale_factor: float = OCR_SCALE_FACTOR,
    blur_kernel: tuple[int, int] | None = OCR_BLUR_KERNEL,
    use_otsu_threshold: bool = OCR_USE_OTSU_THRESHOLD,
    tesseract_config: str = OCR_TESSERACT_CONFIG,
) -> pl.DataFrame:
    """Measure dynasty-name OCR results across test frames."""
    rows = []

    for path, frame in frames:
        card_region = find_selected_dynasty_card(frame)
        name_region = get_dynasty_name_region(card_region)

        left, top, right, bottom = name_region

        name_frame = frame[
            top:bottom,
            left:right,
        ]

        stages = _build_dynasty_name_ocr_stages(
            name_frame,
            scale_factor=scale_factor,
            blur_kernel=blur_kernel,
            use_otsu_threshold=use_otsu_threshold,
        )

        raw_text = pytesseract.image_to_string(
            stages.thresholded,
            config=tesseract_config,
        )

        dynasty_name, separator, trailing_text = raw_text.partition("|")

        expected_name = normalize_dynasty_name(
            expected_names[path.name]
        )

        normalized_name = normalize_dynasty_name(
            dynasty_name
        )

        whitespace_error, character_error = (
            _classify_dynasty_name_ocr_errors(
                normalized_name,
                expected_name,
            )
        )

        character_count_mismatches = (
            _format_character_count_mismatches(
                normalized_name,
                expected_name,
            )
        )

        rows.append(
            {
                "expected_name": expected_name,
                "normalized_name": normalized_name,
                "count_mismatches": character_count_mismatches,
                "space_err": whitespace_error,
                "char_err": character_error,
                "raw_ocr": raw_text.strip(),
                "exact_match": normalized_name == expected_name,
                "frame": path.name,
                "pipe_found": bool(separator),
                "trailing_text": trailing_text.strip(),
                "region_width": right - left,
                "region_height": bottom - top,
                "otsu_threshold": stages.otsu_threshold,
            }
        )

    return pl.DataFrame(rows)
