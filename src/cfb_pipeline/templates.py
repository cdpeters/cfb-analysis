import time
from pathlib import Path
from typing import NamedTuple, cast

import cv2
import numpy as np
from loguru import logger

from .capture import is_valid_frame
from .config import TEMPLATES_DIR
from .exceptions import TemplateFileNotFoundError, TemplateMatchTimeoutError
from .runtime import get_camera
from .types import ImageArray, Region


def _load_template(path: Path) -> ImageArray:
    """
    Loads a grayscale image from disk and validates it.

    Parameters
    ----------
    path : Path
        The file path to the image.

    Returns
    -------
    np.ndarray
        The loaded grayscale image array.

    Raises
    ------
    TemplateFileNotFoundError
        If OpenCV fails to load the image (returning None).
    """
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise TemplateFileNotFoundError(
            f"Critical: Failed to load template at {path}"
        )

    if image.dtype != np.uint8:
        raise TypeError(
            f"Expected uint8 template image, got {image.dtype} at {path}"
        )

    return cast(ImageArray, image)

class _TemplatePaths:
    """
    Centralized file paths for all OpenCV image templates.

    Attributes
    ----------
    TEMPLATES_DIR : Path
        The root directory containing the template image assets.
    PS5_SETTINGS_ICON : Path
        The file path to the PS5 home screen settings icon template.
    CFB_GAME_TITLE : Path
        The file path to the College Football game title template.
    """

    # PS5 UI template paths.
    PS5_SETTINGS_ICON = TEMPLATES_DIR / "ps5_settings_icon.png"
    CFB_GAME_TITLE = TEMPLATES_DIR / "cfb_game_title.png"
    # CFB UI template paths.
    FEATURED_NEWS_CLOSE_ICON = TEMPLATES_DIR / "featured_news_close_icon.png"
    CFB_LOGO = TEMPLATES_DIR / "cfb_logo.png"
    DYNASTY_OPTION = TEMPLATES_DIR / "dynasty_option.png"
    SIGN_IN_TO_EA_ICON = TEMPLATES_DIR / "sign_in_to_EA_icon.png"
    CONNECTED_TO_EA_ICON = TEMPLATES_DIR / "connected_to_EA_icon.png"
    HOTFIX_OVERLAY_YES_OPTION = TEMPLATES_DIR / "hotfix_overlay_yes_option.png"

class TemplateConfig(NamedTuple):
    """
    A structured configuration for a visual template matching target.

    Attributes
    ----------
    template : np.ndarray
        The grayscale image array loaded into memory for matching.
    region : tuple[int, int, int, int]
        The screen coordinates (left, top, right, bottom) defining the
        bounding box to capture and search within.
    log_context : str
        A descriptive string identifying the target, utilized for context
        in logging output.
    """

    template: ImageArray
    region: Region
    log_context: str

class Templates:
    """
    Pre-configured visual templates used throughout the pipeline.

    This class acts as a namespace to hold instantiated `TemplateConfig`
    objects, ensuring templates are loaded into memory once and their
    search regions are standardized.

    Attributes
    ----------
    PS5_SETTINGS_ICON : TemplateConfig
        Configuration for detecting the settings icon on the PS5 home
        screen.
    CFB_GAME_TITLE : TemplateConfig
        Configuration for detecting the College Football game title.
    """

    PS5_SETTINGS_ICON = TemplateConfig(
        template=_load_template(_TemplatePaths.PS5_SETTINGS_ICON),
        region=(1430, 20, 1520, 105),
        log_context="PS5 Home Screen",
    )
    CFB_GAME_TITLE = TemplateConfig(
        template=_load_template(_TemplatePaths.CFB_GAME_TITLE),
        region=(330, 225, 880, 300),
        log_context="CFB Game Title",
    )
    FEATURED_NEWS_CLOSE_ICON = TemplateConfig(
        template=_load_template(_TemplatePaths.FEATURED_NEWS_CLOSE_ICON),
        region=(161, 1020, 269, 1072),
        log_context="Featured News Close Icon",
    )
    CFB_LOGO = TemplateConfig(
        template=_load_template(_TemplatePaths.CFB_LOGO),
        region=(1620, 1018, 1880, 1077),
        log_context="CFB Logo",
    )
    DYNASTY_OPTION = TemplateConfig(
        template=_load_template(_TemplatePaths.DYNASTY_OPTION),
        region=(228, 690, 518, 770),
        log_context="Dynasty Option",
    )
    SIGN_IN_TO_EA_ICON = TemplateConfig(
        template=_load_template(_TemplatePaths.SIGN_IN_TO_EA_ICON),
        region=(161, 1020, 325, 1073),
        log_context="Sign In To EA Icon",
    )
    CONNECTED_TO_EA_ICON = TemplateConfig(
        template=_load_template(_TemplatePaths.CONNECTED_TO_EA_ICON),
        region=(1120, 1020, 1400, 1075),
        log_context="Connected To EA Icon",
    )
    HOTFIX_OVERLAY_YES_OPTION = TemplateConfig(
        template=_load_template(_TemplatePaths.HOTFIX_OVERLAY_YES_OPTION),
        region=(640, 520, 1280, 1030),
        log_context="Hotfix Overlay Yes Option",
    )

def is_image_match(
    frame: ImageArray, template: ImageArray, confidence_threshold: float = 0.90
) -> tuple[bool, float]:
    """
    Evaluates a single image frame against a template using OpenCV.

    Converts the provided color frame to grayscale and performs template
    matching to determine if the target template is present within the
    frame.

    Parameters
    ----------
    frame : np.ndarray
        The BGRA color image array (captured frame) to be evaluated.
    template : np.ndarray
        The grayscale image array used as the template for matching.
    confidence_threshold : float, optional
        The minimum match value (0.0 to 1.0) required to consider it a
        successful match. Default is 0.90.

    Returns
    -------
    tuple[bool, float]
        A tuple containing:
        - A boolean indicating if the best match exceeds the confidence
        threshold.
        - A float representing the maximum confidence score found in the
        frame.
    """
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    return max_val > confidence_threshold, max_val

def poll_for_template_match(
    template: ImageArray,
    region: Region,
    log_context: str,
    timeout: float = 5.0,
    confidence_threshold: float = 0.90,
) -> None:
    """
    Manages the camera polling loop to wait for a visual match.

    Starts a background capture thread and continuously checks the
    specified screen region. It delegates the actual visual evaluation to
    `is_image_match`. The loop runs until a match exceeding the
    confidence threshold is found or the timeout is reached.

    Parameters
    ----------
    template : np.ndarray
        A grayscale image array used as the template for OpenCV matching.
    region : tuple[int, int, int, int]
        The bounding box coordinates (left, top, right, bottom) of the
        screen region to capture.
    log_context : str
        A descriptive string detailing what is being matched (e.g.,
        "PS5 Home Screen" or "CFB Game Title") to provide context in
        the logs.
    timeout : float, optional
        The maximum time in seconds to wait for a successful match.
        Default is 5.0.
    confidence_threshold : float, optional
        The minimum match value (0.0 to 1.0) required to register a
        success. Default is 0.90.

    Raises
    ------
    TemplateMatchTimeoutError
        If a match exceeding the confidence threshold is not found within
        the timeout period.
    """
    logger.info(
        f"Starting background capture thread: Polling for '{log_context}'..."
    )
    # Start a background camera thread to continuously capture frames.
    camera = get_camera()
    camera.start(target_fps=10, region=region)
    deadline = time.monotonic() + timeout
    highest_confidence_seen = 0.0

    try:
        while time.monotonic() < deadline:
            frame = camera.get_latest_frame()

            if is_valid_frame(frame=frame):
                is_match, confidence = is_image_match(
                    frame=frame,
                    template=template,
                    confidence_threshold=confidence_threshold,
                )

                highest_confidence_seen = max(highest_confidence_seen, confidence)

                if is_match:
                    logger.success(
                        f"Successfully matched '{log_context}'! (Confidence: {confidence:.2f})"
                    )
                    return

            # Sync with the 10 FPS background camera thread to prevent
            # redundant cv2 processing.
            time.sleep(0.1)

        logger.debug(
            f"Polling for '{log_context}' timed out after {timeout} seconds "
            f"(Max confidence seen: {highest_confidence_seen:.2f})."
        )

        raise TemplateMatchTimeoutError(
            f"Failed to match '{log_context}' within {timeout}s."
        )

    finally:
        camera.stop()
