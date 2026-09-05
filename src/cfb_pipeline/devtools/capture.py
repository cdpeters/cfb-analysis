from pathlib import Path
from typing import cast

import cv2
import marimo as mo
from PIL import Image

from cfb_pipeline.types import ImageArray, Region


def cv2_to_pil(frame: ImageArray) -> Image.Image:
    """Convert an OpenCV image array to a Pillow image for display."""
    if frame.ndim == 2:
        return Image.fromarray(frame)

    if frame.shape[2] == 4:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
    else:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    return Image.fromarray(rgb)

def load_frames(
    directory: Path,
    *,
    pattern: str = "*.png",
) -> list[tuple[Path, ImageArray]]:
    """Load image files from a directory for visual tuning."""
    frames: list[tuple[Path, ImageArray]] = []

    for path in sorted(directory.glob(pattern)):
        frame = cv2.imread(
            path,
            cv2.IMREAD_UNCHANGED,
        )

        if frame is None:
            raise RuntimeError(
                f"Failed to load test frame: {path}"
            )

        frame = cast(ImageArray, frame)
        frames.append((path, frame))

    if not frames:
        raise RuntimeError(
            f"No test frames matching {pattern!r} found in {directory}"
        )

    return frames

def save_frame(
    frame: ImageArray,
    path: Path,
) -> None:
    """Save an image frame to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(path, frame):
        raise RuntimeError(f"Failed to save frame: {path}")

def show_full_frame(frame: ImageArray) -> mo.Html:
    """Capture and display the complete remote-play frame."""

    return mo.image(
        cv2_to_pil(frame),
        caption="Full screen",
    )

def show_region(
    frame: ImageArray,
    region: Region,
) -> mo.Html:
    """Capture and display only the requested screen region."""
    left, top, right, bottom = region

    region_frame = frame[
        top:bottom,
        left:right,
    ]

    return mo.image(
        cv2_to_pil(region_frame),
        caption=f"Region: {region}",
    )

def show_regions(
    frame: ImageArray,
    regions: dict[str, tuple[Region, tuple[int, int, int, int]]],
) -> mo.Html:
    """Display a full-screen frame with multiple labeled regions."""
    preview = frame.copy()

    for label, (region, color) in regions.items():
        left, top, right, bottom = region

        cv2.rectangle(
            preview,
            (left, top),
            (right, bottom),
            color,
            3,
        )

        cv2.putText(
            preview,
            label,
            (left, max(top - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    return mo.image(
        cv2_to_pil(preview),
        caption="Screen regions",
    )

def show_region_overlay(
    frame: ImageArray,
    region: Region,
    *,
    label: str | None = None,
) -> mo.Html:
    """Display a full-screen frame with one region outlined."""
    preview = frame.copy()

    left, top, right, bottom = region

    cv2.rectangle(
        preview,
        (left, top),
        (right, bottom),
        (0, 255, 0, 255),
        3,
    )

    if label is not None:
        cv2.putText(
            preview,
            label,
            (left, max(top - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return mo.image(
        cv2_to_pil(preview),
        caption=label or "Region overlay",
    )
