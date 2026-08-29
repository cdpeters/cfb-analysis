from loguru import logger

from .controller import Button
from .exceptions import TemplateMatchTimeoutError
from .runtime import get_controller
from .templates import TemplateConfig, poll_for_template_match


def focus_first_game_tile() -> None:
    """Move PS5 home screen cursor from welcome tile to first game tile."""
    logger.info("Moving from welcome tile to the first game tile...")
    controller = get_controller()
    controller.tap(Button.DPAD_RIGHT)

def focus_welcome_tile() -> None:
    """Move PS5 home screen cursor from first game tile to welcome tile."""
    logger.info("Moving cursor to the welcome tile...")
    controller = get_controller()
    controller.tap(Button.DPAD_LEFT)

def is_home_screen_visible(target_config: TemplateConfig) -> bool:
    """
    Evaluates if the PS5 home screen is currently rendered.

    Parameters
    ----------
    target_config : TemplateConfig
        The configuration object containing the visual template, capture
        region, and logging context used to verify the PS5 home screen.

    Returns
    -------
    bool
        True if the PS5 settings icon is successfully matched within the
        timeout, or False if a TemplateMatchTimeoutError is caught.
    """
    try:
        poll_for_template_match(
            template=target_config.template,
            region=target_config.region,
            log_context="Verify Home Screen Visible",
        )
        return True
    except TemplateMatchTimeoutError:
        return False

def return_to_home_screen() -> None:
    """Force PS5 to return to the home screen by holding the PS button."""
    logger.info("Holding PS button to return to the home screen...")
    controller = get_controller()
    controller.hold(Button.PS, rest_time=1.0)

def close_active_game() -> None:
    """
    Executes sequence to close active game from home screen.

    This function requires that the PS5 cursor is currently on the active
    game's tile on the home screen prior to executing the button sequence
    for closing the game.
    """
    logger.info("Executing sequence to close the active game...")
    controller = get_controller()
    controller.tap(Button.OPTIONS, rest_time=0.5)
    controller.tap(Button.CROSS, rest_time=3.0)
