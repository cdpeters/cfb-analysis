import time

from cfb_pipeline.config import FRAME_CAPTURE_TIMEOUT
from cfb_pipeline.exceptions import FrameCaptureTimeoutError
from cfb_pipeline.types import ImageArray, Region


def is_valid_frame(frame: ImageArray | None) -> bool:
    """Return whether a captured frame contains usable image data."""
    return frame is not None and bool(frame.max() > 0)

def capture_frame(
    region: Region | None = None,
    timeout: float = FRAME_CAPTURE_TIMEOUT,
) -> ImageArray:
    """Capture and return a valid frame from the remote-play stream."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        frame = camera.grab(region=region)

        if is_valid_frame(frame=frame):
            return frame

        time.sleep(0.1)

    raise FrameCaptureTimeoutError(
        f"Failed to capture a valid frame within {timeout:.1f}s."
    )
