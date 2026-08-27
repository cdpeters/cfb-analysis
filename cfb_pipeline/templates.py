from pathlib import Path
from typing import NamedTuple

import cv2

from cfb_pipeline.config import TEMPLATES_DIR
from cfb_pipeline.exceptions import TemplateFileNotFoundError
from cfb_pipeline.types import ImageArray, Region


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

    return image

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
