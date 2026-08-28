from enum import Enum, auto

from loguru import logger

from cfb_pipeline.controller import Button
from cfb_pipeline.exceptions import CFBGameTitleNotFoundError, TemplateMatchTimeoutError
from cfb_pipeline.templates import TemplateConfig


class MainMenuPollOutcome(Enum):
    """
    Enum tracking the identified state of the CFB game main menu.

    Attributes
    ----------
    MAIN_MENU_CLEAN : auto
        Indicates the main menu has been successfully identified and stabilized.
    HOTFIX_DETECTED : auto
        Indicates a hotfix overlay has been detected on the screen.
    """

    MAIN_MENU_CLEAN = auto()
    HOTFIX_DETECTED = auto()

class MenuEvent(Enum):
    """Visual states that can be detected while reaching the CFB main menu."""

    HOTFIX = auto()
    EA_SIGN_IN = auto()
    FEATURED_NEWS = auto()
    DYNASTY_VISIBLE = auto()
    NONE = auto()

def launch_cfb_game(target_config: TemplateConfig) -> None:
    """
    Navigates the PS5 home screen to find and launch CFB.

    Iterates through the recent games list on the PS5 home screen, checking
    each game tile's title against the provided template configuration. If
    found, it launches the game.

    Parameters
    ----------
    target_config : TemplateConfig
        The configuration object containing the visual template, capture
        region, and logging context used to identify the CFB game title.

    Raises
    ------
    CFBGameTitleNotFoundError
        If the target game title cannot be located after shifting through
        the specified maximum number of attempts.
    """
    max_attempts = 10

    for attempt in range(max_attempts):
        logger.debug(f"Evaluating game title {attempt + 1}...")

        try:
            poll_for_template_match(
                template=target_config.template,
                region=target_config.region,
                log_context=target_config.log_context,
                timeout=3.0,
                confidence_threshold=0.87,
            )
        except TemplateMatchTimeoutError:
            logger.debug("Target game not found. Shifting to next title...")
            controller.tap(Button.DPAD_RIGHT)
            continue

        logger.success("Target game located. Launching...")
        controller.tap(Button.CROSS)
        return

    raise CFBGameTitleNotFoundError(
        f"Target game could not be located after {max_attempts} title shifts."
    )
