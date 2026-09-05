from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import marimo as mo
import polars as pl

from cfb_pipeline.devtools.capture import cv2_to_pil
from cfb_pipeline.types import ImageArray


@dataclass(slots=True)
class TuningStage:
    name: str
    image: ImageArray
    caption: str | None = None

@dataclass(slots=True)
class TuningResult:
    stages: list[TuningStage]
    contours: Sequence[cv2.typing.MatLike] = field(default_factory=list)

def create_frame_slider(
    frame_count: int,
    *,
    label: str = "Test frame",
) -> mo.ui.slider:
    """Create a slider for selecting a test frame."""
    if frame_count < 1:
        raise ValueError("frame_count must be at least 1.")

    return mo.ui.slider(
        start=0,
        stop=frame_count - 1,
        step=1,
        value=0,
        label=label,
    )

def contour_within_dimension_bounds(
    contour: cv2.typing.MatLike,
    *,
    min_width: int | None = None,
    max_width: int | None = None,
    min_height: int | None = None,
    max_height: int | None = None,
) -> bool:
    """Return whether a contour's bounding box matches the given dimensions."""
    _, _, width, height = cv2.boundingRect(contour)

    if min_width is not None and width < min_width:
        return False

    if max_width is not None and width > max_width:
        return False

    if min_height is not None and height < min_height:
        return False

    return max_height is None or height <= max_height

def draw_contours(
    frame: ImageArray,
    contours: Sequence[cv2.typing.MatLike],
    *,
    min_width: int = 0,
    min_height: int = 0,
) -> ImageArray:
    """Draw contour bounding boxes and dimensions on a copy of a color image."""
    preview = frame.copy()

    for index, contour in enumerate(contours):
        x, y, width, height = cv2.boundingRect(contour)

        if width < min_width or height < min_height:
            continue

        cv2.rectangle(
            preview,
            (x, y),
            (x + width, y + height),
            (0, 255, 255, 255),
            2,
        )

        cv2.putText(
            preview,
            f"{index}: {width}x{height}",
            (x, max(y - 8, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return preview

def draw_contour_candidates(
    frame: ImageArray,
    contours: Sequence[cv2.typing.MatLike],
    *,
    min_width: int = 0,
    max_width: int | None = None,
    min_height: int = 0,
    max_height: int | None = None,
) -> ImageArray:
    """Draw contours whose bounding boxes match the given dimensions on a copy of a color image."""
    preview = frame.copy()

    for index, contour in enumerate(contours):
        if not contour_within_dimension_bounds(
            contour,
            min_width=min_width,
            max_width=max_width,
            min_height=min_height,
            max_height=max_height,
        ):
            continue

        x, y, width, height = cv2.boundingRect(contour)

        cv2.rectangle(
            preview,
            (x, y),
            (x + width, y + height),
            (0, 255, 0, 255),
            2,
        )

        cv2.putText(
            preview,
            f"{index}: ({x}, {y}) {width}x{height}",
            (x, max(y - 8, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0, 255),
            1,
            cv2.LINE_AA,
        )

    return preview

def measure_frame_contours(
    frames: list[tuple[Path, ImageArray]],
    processor: Callable[[ImageArray], TuningResult],
    *,
    min_width: int = 0,
    max_width: int | None = None,
    min_height: int = 0,
    max_height: int | None = None,
) -> pl.DataFrame:
    """Process frames and return contour bounding-box measurements."""
    rows = []

    for path, frame in frames:
        result = processor(frame)

        for index, contour in enumerate(result.contours):
            if not contour_within_dimension_bounds(
                contour,
                min_width=min_width,
                max_width=max_width,
                min_height=min_height,
                max_height=max_height,
            ):
                continue

            x, y, width, height = cv2.boundingRect(contour)

            rows.append(
                {
                    "frame": path.name,
                    "contour_index": index,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "area": width * height,
                }
            )

    return pl.DataFrame(
        rows,
        schema={
            "frame": pl.String,
            "contour_index": pl.Int64,
            "x": pl.Int64,
            "y": pl.Int64,
            "width": pl.Int64,
            "height": pl.Int64,
            "area": pl.Int64,
        },
    )

def show_tuning_result(
    *,
    slider: mo.ui.slider,
    frame_path: Path,
    result: TuningResult,
    image_width: str = "60%",
) -> mo.Html:
    """Display a slider and processed image stages as tabs."""
    tabs = mo.ui.tabs(
        {
            stage.name: mo.image(
                cv2_to_pil(stage.image),
                caption=stage.caption or frame_path.name,
            ).style(
                {
                    "width": image_width,
                    "margin": "0 auto",
                }
            )
            for stage in result.stages
        }
    )

    return mo.vstack(
        [
            slider,
            mo.md(f"**{frame_path.name}**"),
            tabs,
        ],
        gap=1.0,
    )
