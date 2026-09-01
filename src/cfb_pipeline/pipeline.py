import time
from enum import Enum, auto

from loguru import logger

from .cfb import (
    MainMenuPollOutcome,
    dismiss_hotfix_overlay,
    launch_cfb_game,
    poll_main_menu_with_interrupts,
)
from .chiaki import launch_chiaki
from .config import TARGET_DYNASTY_NAME
from .dynasty import load_dynasty_by_name, navigate_to_dynasty_list
from .lifecycle import reset_pipeline_and_ps5, shutdown_pipeline
from .ps5 import (
    close_active_game,
    focus_first_game_tile,
    focus_welcome_tile,
    is_home_screen_visible,
    return_to_home_screen,
)
from .templates import Templates


class PipelineState(Enum):
    """States defining the distinct phases of the extraction pipeline."""

    INITIALIZE_STREAM = auto()
    VERIFY_STREAM = auto()
    LAUNCH_GAME = auto()
    STABILIZE_MAIN_MENU = auto()
    LAUNCH_DYNASTY = auto()
    EXTRACT_ROSTERS = auto()
    RECOVER_SOFT = auto()
    RECOVER_HARD = auto()
    SHUTDOWN = auto()
    DONE = auto()

def handle_initialize_stream() -> PipelineState:
    """Launches chiaki-ng subprocess and ensures full screen mode."""
    with logger.contextualize(phase="initialize_stream"):
        logger.info("Entering State: INITIALIZE_STREAM")

        try:
            launch_chiaki()
            return PipelineState.VERIFY_STREAM
        except Exception as e:
            logger.error(f"Stream initialization failed: {e}")
            return PipelineState.RECOVER_HARD

def handle_verify_stream() -> PipelineState:
    """Diagnoses stream health and handles unclosed game states."""
    with logger.contextualize(phase="verify_stream"):
        logger.info("Entering State: VERIFY_STREAM")

        # Check to see if we're already on the PS5 home screen.
        if is_home_screen_visible(target_config=Templates.PS5_SETTINGS_ICON):
            logger.info("Stream active. Clean home screen detected.")
            focus_first_game_tile()
            return PipelineState.LAUNCH_GAME

        # Assume an unclosed game: return to the PS5 home screen and focus the welcome tile for a PS5
        # settings icon template match attempt.
        logger.warning(
            "Home screen not visible. Attempting to exit potential unclosed game..."
        )
        return_to_home_screen()
        focus_welcome_tile()

        if is_home_screen_visible(target_config=Templates.PS5_SETTINGS_ICON):
            logger.info("Recovered to home screen. Closing the unclosed game...")
            focus_first_game_tile()
            close_active_game()
            return PipelineState.LAUNCH_GAME

        logger.error("Stream is completely unresponsive.")
        return PipelineState.RECOVER_HARD

def handle_launch_game() -> PipelineState:
    """Locates and launches CFB from the PS5 home screen."""
    with logger.contextualize(phase="launch_game"):
        logger.info("Entering State: LAUNCH_GAME")

        try:
            launch_cfb_game(target_config=Templates.CFB_GAME_TITLE)
            return PipelineState.STABILIZE_MAIN_MENU
        except Exception as e:
            logger.error(f"Failed to launch game: {e}")
            return PipelineState.RECOVER_HARD

def handle_stabilize_main_menu() -> PipelineState:
    """Handles post-launch loading screens, pop-ups, and hotfixes."""

    with logger.contextualize(phase="stabilize_menu"):
        logger.info("Entering State: STABILIZE_MAIN_MENU")

        try:
            main_menu_state = poll_main_menu_with_interrupts(
                cfb_logo_config=Templates.CFB_LOGO,
                dynasty_config=Templates.DYNASTY_OPTION,
                hotfix_overlay_config=Templates.HOTFIX_OVERLAY_YES_OPTION,
                sign_in_to_EA_config=Templates.SIGN_IN_TO_EA_ICON,
                connected_to_EA_config=Templates.CONNECTED_TO_EA_ICON,
                featured_news_config=Templates.FEATURED_NEWS_CLOSE_ICON,
            )

            if main_menu_state == MainMenuPollOutcome.HOTFIX_DETECTED:
                dismiss_hotfix_overlay()
                return PipelineState.RECOVER_SOFT

            logger.success("Main menu stabilized.")
            return PipelineState.LAUNCH_DYNASTY

        except Exception as e:
            logger.error(f"Menu stabilization failed: {e}")
            return PipelineState.RECOVER_HARD

def handle_launch_dynasty() -> PipelineState:
    """Navigate from the stable main menu into the target Dynasty save."""
    with logger.contextualize(phase="launch_dynasty"):
        logger.info("Entering State: LAUNCH_DYNASTY")

        try:
            navigate_to_dynasty_list()
            load_dynasty_by_name(TARGET_DYNASTY_NAME)

            return PipelineState.EXTRACT_ROSTERS

        except Exception as e:
            logger.error(f"Failed to launch Dynasty mode: {e}")
            return PipelineState.RECOVER_HARD

def handle_extract_rosters() -> PipelineState:
    """Executes the core data extraction sequence."""
    with logger.contextualize(phase="extract_rosters"):
        logger.info("Entering State: EXTRACT_ROSTERS")

        # ... Simulate extraction ...
        time.sleep(15)
        logger.success("Data extraction complete!")
        return PipelineState.DONE

def handle_recover_soft() -> PipelineState:
    """Closes the game to clear state, leaving the stream active."""
    with logger.contextualize(phase="recover_soft"):
        logger.info("Entering State: RECOVER_SOFT")

        try:
            return_to_home_screen()
            close_active_game()
            # The cursor is still on the CFB game tile so we can move directly to `LAUNCH_GAME`.
            return PipelineState.LAUNCH_GAME
        except Exception as e:
            logger.error(f"Soft recovery failed: {e}")
            return PipelineState.RECOVER_HARD

def run_pipeline(max_hard_retries: int = 2) -> None:
    """Orchestrates the state machine loop."""
    current_state = PipelineState.INITIALIZE_STREAM
    hard_retries = 0

    # Map the enums directly to their handler functions
    state_machine = {
        PipelineState.INITIALIZE_STREAM: handle_initialize_stream,
        PipelineState.VERIFY_STREAM: handle_verify_stream,
        PipelineState.LAUNCH_GAME: handle_launch_game,
        PipelineState.STABILIZE_MAIN_MENU: handle_stabilize_main_menu,
        PipelineState.LAUNCH_DYNASTY: handle_launch_dynasty,
        PipelineState.EXTRACT_ROSTERS: handle_extract_rosters,
        PipelineState.RECOVER_SOFT: handle_recover_soft,
    }

    try:
        while current_state not in (PipelineState.DONE, PipelineState.SHUTDOWN):
            # RECOVER_HARD is handled directly in the runner to manage the retry budget.
            if current_state == PipelineState.RECOVER_HARD:
                with logger.contextualize(phase="recover_hard"):
                    hard_retries += 1
                    if hard_retries > max_hard_retries:
                        logger.critical(
                            f"Max hard retries ({max_hard_retries}) reached. Aborting pipeline."
                        )
                        current_state = PipelineState.SHUTDOWN
                    else:
                        logger.warning(
                            f"Executing hard reset (Attempt {hard_retries}/{max_hard_retries})..."
                        )
                        reset_pipeline_and_ps5()
                        current_state = PipelineState.INITIALIZE_STREAM
                continue

            # Execute the current state and transition to the returned state.
            state_handler = state_machine[current_state]
            current_state = state_handler()

    finally:
        with logger.contextualize(phase="shutdown"):
            logger.info("Pipeline terminating. Executing final cleanup...")
            shutdown_pipeline()
