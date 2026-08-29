import time
from enum import Enum, auto

from loguru import logger

from .capture import is_valid_frame
from .controller import Button
from .exceptions import (
    CFBGameTitleNotFoundError,
    EAConnectionTimeoutError,
    MainMenuPollingTimeoutError,
    TemplateMatchTimeoutError,
)
from .runtime import get_camera, get_controller
from .templates import (
    TemplateConfig,
    is_image_match,
    poll_for_template_match,
)
from .types import ImageArray


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
    controller = get_controller()
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

def poll_main_menu_with_interrupts(
    cfb_logo_config: TemplateConfig,
    dynasty_config: TemplateConfig,
    hotfix_overlay_config: TemplateConfig,
    sign_in_to_EA_config: TemplateConfig,
    connected_to_EA_config: TemplateConfig,
    featured_news_config: TemplateConfig,
    timeout: float = 60.0,
) -> MainMenuPollOutcome:
    """
    Poll for and stabilize the CFB main menu while handling known interrupts.

    The function progresses through three stages:

    1. Clear the introductory screens until the CFB logo is visible.
    2. Wait for the main menu while handling a possible hotfix overlay,
        Featured News popup, and/or EA sign-in interruptions.
    3. Verify that the Dynasty option remains continuously visible for the
        stabilization duration.

    A single global timeout budget is shared across all three stages.

    Parameters
    ----------
    cfb_logo_config : TemplateConfig
        Template configuration used to identify the CFB logo.
    dynasty_config : TemplateConfig
        Template configuration used to identify the Dynasty main menu option.
    hotfix_overlay_config : TemplateConfig
        Template configuration used to identify the hotfix overlay.
    sign_in_to_EA_config : TemplateConfig
        Template configuration used to identify the EA sign-in icon.
    connected_to_EA_config : TemplateConfig
        Template configuration used to verify an EA server connection.
    featured_news_config : TemplateConfig
        Template configuration used to identify the Featured News popup.
    timeout : float, optional
        Maximum total time allowed for the complete polling sequence.
        Default is 60.0 seconds.

    Returns
    -------
    MainMenuPollOutcome
        MAIN_MENU_CLEAN when the Dynasty menu remains stable, or
        HOTFIX_DETECTED when a hotfix overlay is encountered.

    Raises
    ------
    MainMenuPollingTimeoutError
        If the overall polling deadline is exceeded.
    EAConnectionTimeoutError
        If the EA reconnection fails.
    """

    POLL_INTERVAL = 0.1
    STABILIZATION_DURATION = 7.0
    EA_CONNECT_TIMEOUT = 20.0
    DYNASTY_CONFIDENCE_THRESHOLD = 0.87

    def get_frame() -> ImageArray | None:
        """
        Get the latest valid camera frame.

        Returns None when the camera has not yet produced usable image data.
        """
        camera = get_camera()
        frame = camera.get_latest_frame()

        if not is_valid_frame(frame=frame):
            return None

        return frame

    def is_target_visible(
        frame: ImageArray,
        target_config: TemplateConfig,
        confidence_threshold: float = 0.90,
    ) -> bool:
        """Return whether a configured template is visible within a frame."""
        left, top, right, bottom = target_config.region
        region = frame[top:bottom, left:right]

        is_match, confidence = is_image_match(
            frame=region,
            template=target_config.template,
            confidence_threshold=confidence_threshold,
        )

        if is_match:
            logger.debug(
                f"Successfully matched '{target_config.log_context}'! "
                f"(Confidence: {confidence:.2f})"
            )

        return is_match

    def detect_menu_event(frame: ImageArray) -> MenuEvent:
        """
        Identify the highest-priority menu event visible in the current frame.

        EA sign-in takes precedence because hotfix detection is only meaningful once
        the game is connected to EA servers. Other interrupts also take precedence
        over the Dynasty option because overlays may leave enough of the underlying
        main menu visible for the Dynasty template to continue matching.
        """
        if is_target_visible(frame=frame, target_config=sign_in_to_EA_config):
            return MenuEvent.EA_SIGN_IN

        if is_target_visible(frame=frame, target_config=hotfix_overlay_config):
            return MenuEvent.HOTFIX

        if is_target_visible(frame=frame, target_config=featured_news_config):
            return MenuEvent.FEATURED_NEWS

        if is_target_visible(
            frame=frame,
            target_config=dynasty_config,
            confidence_threshold=DYNASTY_CONFIDENCE_THRESHOLD,
        ):
            return MenuEvent.DYNASTY_VISIBLE

        return MenuEvent.NONE

    def wait_for_ea_connection(global_deadline: float) -> None:
        """Wait until the game reports a successful connection to EA servers."""
        logger.info("Waiting for connection to EA servers...")

        # If `global_deadline` is sooner than the "would be" EA deadline, then
        # that becomes `ea_deadline` to ensure respect of the global deadline.
        ea_deadline = min(
            global_deadline,
            time.monotonic() + EA_CONNECT_TIMEOUT,
        )

        while time.monotonic() < ea_deadline:
            frame = get_frame()

            if frame is not None and is_target_visible(
                frame=frame,
                target_config=connected_to_EA_config,
            ):
                logger.success("Connected to EA servers!")
                time.sleep(1.0)
                return

            time.sleep(POLL_INTERVAL)

        raise EAConnectionTimeoutError(
            "Timed out waiting for connection to EA servers."
        )

    def handle_interrupt(
        event: MenuEvent,
        global_deadline: float,
    ) -> MainMenuPollOutcome | None:
        """
        Handle an interrupting main menu event.

        Returns HOTFIX_DETECTED when a hotfix requires the outer pipeline to
        restart the game. Other handled interrupts return None.
        """
        controller = get_controller()

        match event:
            case MenuEvent.HOTFIX:
                logger.warning("Hotfix overlay detected!")
                return MainMenuPollOutcome.HOTFIX_DETECTED

            case MenuEvent.FEATURED_NEWS:
                logger.info("Featured News popup detected. Dismissing...")
                controller.tap(Button.CIRCLE, rest_time=1.0)

            case MenuEvent.EA_SIGN_IN:
                logger.info("EA Sign-In required. Pressing R2...")
                controller.tap(Button.R2)
                wait_for_ea_connection(global_deadline=global_deadline)

        return None

    def clear_intro(global_deadline: float) -> None:
        """Tap Circle periodically until the CFB logo becomes visible."""
        logger.info("Executing Phase 0: Intro Screen...")
        controller = get_controller()
        next_tap_time = time.monotonic()

        while time.monotonic() < global_deadline:
            frame = get_frame()

            if frame is not None and is_target_visible(
                frame=frame,
                target_config=cfb_logo_config,
            ):
                logger.info("CFB Logo detected. Phase 0 cleared.")
                return

            now = time.monotonic()

            if now >= next_tap_time:
                controller.tap(Button.CIRCLE, rest_time=0.0)
                next_tap_time = now + 1.0

            time.sleep(POLL_INTERVAL)

        raise MainMenuPollingTimeoutError("Timed out during Phase 0: Intro Screen.")

    def wait_for_main_menu(
        global_deadline: float,
    ) -> MainMenuPollOutcome | None:
        """
        Wait until the Dynasty option becomes visible.

        Known interruptions are handled while polling. A hotfix is propagated
        to the caller as a special outcome.
        """
        logger.info("Executing Phase 1: Main Menu Search...")

        while time.monotonic() < global_deadline:
            frame = get_frame()

            if frame is None:
                time.sleep(POLL_INTERVAL)
                continue

            event = detect_menu_event(frame=frame)

            if event is MenuEvent.DYNASTY_VISIBLE:
                logger.info("Dynasty option detected. Phase 1 cleared.")
                return None

            outcome = handle_interrupt(
                event=event,
                global_deadline=global_deadline,
            )

            if outcome is not None:
                return outcome

            time.sleep(POLL_INTERVAL)

        raise MainMenuPollingTimeoutError(
            "Timed out during Phase 1: Main Menu Search."
        )

    def stabilize_main_menu(
        global_deadline: float,
    ) -> MainMenuPollOutcome:
        """
        Require the Dynasty option to remain continuously visible.

        Any interruption or loss of the Dynasty template resets the
        stabilization timer.
        """
        logger.info("Executing Phase 2: Main Menu Stabilization...")

        stable_start: float | None = None

        while time.monotonic() < global_deadline:
            frame = get_frame()

            if frame is None:
                stable_start = None
                time.sleep(POLL_INTERVAL)
                continue

            event = detect_menu_event(frame=frame)

            if event is MenuEvent.DYNASTY_VISIBLE:
                now = time.monotonic()

                if stable_start is None:
                    stable_start = now
                    logger.debug("Main menu stabilization timer started.")

                if now - stable_start >= STABILIZATION_DURATION:
                    logger.success("CFB main menu is stabilized.")
                    return MainMenuPollOutcome.MAIN_MENU_CLEAN

                time.sleep(POLL_INTERVAL)
                continue

            # Anything other than a continuously visible Dynasty option breaks
            # the stabilization window.
            stable_start = None

            outcome = handle_interrupt(
                event=event,
                global_deadline=global_deadline,
            )

            if outcome is not None:
                return outcome

            time.sleep(POLL_INTERVAL)

        raise MainMenuPollingTimeoutError(
            "Timed out during Phase 2: Main Menu Stabilization."
        )

    # ==============
    # Main Sequence
    # ==============
    logger.info("Polling sequence initiated for CFB main menu...")
    camera = get_camera()
    global_deadline = time.monotonic() + timeout

    camera.start(target_fps=10, region=None)

    try:
        clear_intro(global_deadline=global_deadline)

        search_outcome = wait_for_main_menu(global_deadline=global_deadline)

        if search_outcome is MainMenuPollOutcome.HOTFIX_DETECTED:
            return search_outcome

        return stabilize_main_menu(global_deadline=global_deadline)

    finally:
        camera.stop()

def dismiss_hotfix_overlay() -> None:
    """Dismiss the hotfix overlay without applying the update."""
    logger.info("Selecting 'No' on hotfix overlay...")
    controller = get_controller()
    controller.tap(Button.CROSS, rest_time=2.0)
