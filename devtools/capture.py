import time

import cv2
import marimo as mo
from PIL import Image

from cfb_pipeline.capture import is_valid_frame
from cfb_pipeline.runtime import get_camera
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

def capture_test_frame(
    region: Region | None = None,
    timeout: float = 3.0,
) -> ImageArray:
    """Capture a valid frame for prototyping and visual tuning."""
    camera = get_camera()
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        frame = camera.grab(region=region)

        if is_valid_frame(frame=frame):
            return frame

        time.sleep(0.1)

    raise RuntimeError(f"Failed to capture a valid frame within {timeout:.1f}s.")

def show_full_frame() -> mo.Html:
    """Capture and display the complete remote-play frame."""
    frame = capture_test_frame()

    return mo.image(
        cv2_to_pil(frame),
        caption="Full screen",
    )

def show_region(
    region: Region,
    *,
    caption: str = "Region",
) -> mo.Html:
    """Capture and display only the requested screen region."""
    frame = capture_test_frame(region=region)

    return mo.image(
        cv2_to_pil(frame),
        caption=caption,
    )

def show_regions(
    regions: dict[str, Region],
) -> mo.Html:
    """Display a full-screen frame with multiple labeled regions."""
    frame = capture_test_frame()
    preview = frame.copy()

    for label, region in regions.items():
        left, top, right, bottom = region

        cv2.rectangle(
            preview,
            (left, top),
            (right, bottom),
            (0, 255, 0, 255),
            3,
        )

        cv2.putText(
            preview,
            label,
            (left, max(top - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return mo.image(
        cv2_to_pil(preview),
        caption="Screen regions",
    )

def show_region_overlay(
    region: Region,
    *,
    label: str | None = None,
) -> mo.Html:
    """Display a full-screen frame with one region outlined."""
    frame = capture_test_frame()
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
