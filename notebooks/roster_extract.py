import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Main Launch Sequence
    """)
    return


@app.cell(disabled=True)
def _(
    PipelineState,
    handle_extract_rosters,
    handle_initialize_stream,
    handle_launch_dynasty,
    handle_launch_game,
    handle_recover_soft,
    handle_stabilize_main_menu,
    handle_verify_stream,
    logger,
    reset_pipeline_and_ps5,
    shutdown_pipeline,
):
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

    run_pipeline()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### State Handlers
    """)
    return


@app.cell
def _(
    Button,
    CFBMainMenuState,
    PipelineState,
    Templates,
    close_active_game,
    controller,
    focus_first_game_tile,
    focus_welcome_tile,
    is_home_screen_visible,
    launch_cfb_game,
    launch_ps5,
    logger,
    poll_main_menu_with_interrupts,
    return_to_home_screen,
    time,
):
    def handle_initialize_stream() -> PipelineState:
        """Launches chiaki-ng subprocess and ensures full screen mode."""
        with logger.contextualize(phase="initialize_stream"):
            logger.info("Entering State: INITIALIZE_STREAM")

            try:
                launch_ps5()
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
                    main_menu_config=Templates.CFB_MAIN_MENU_TOP,
                    hotfix_overlay_config=Templates.CFB_HOTFIX_OVERLAY,
                )

                if main_menu_state == CFBMainMenuState.HOTFIX:
                    logger.warning("Hotfix detected. Selecting 'No' to dismiss...")
                    controller.tap(Button.CROSS, rest_time=2.0)
                    return PipelineState.RECOVER_SOFT

                logger.success("Main menu stabilized.")
                return PipelineState.LAUNCH_DYNASTY

            except Exception as e:
                logger.error(f"Menu stabilization failed: {e}")
                return PipelineState.RECOVER_HARD

    def handle_launch_dynasty() -> PipelineState:
        """Navigates from a stable main menu into the Dynasty mode save."""
        with logger.contextualize(phase="launch_dynasty"):
            logger.info("Entering State: LAUNCH_DYNASTY")

            try:
                # 1. Navigate down to the 'Dynasty' option
                logger.debug("Navigating to Dynasty tile...")
                controller.tap(Button.DPAD_DOWN, rest_time=0.5)
                # ... add remaining D-pad movements ...
                controller.tap(Button.CROSS, rest_time=2.0)

                # 2. Select 'Continue' or load specific file
                logger.debug("Selecting save file...")
                controller.tap(Button.CROSS, rest_time=5.0)  # Wait for load

                # Optional: Add a quick visual verify here to confirm we are inside the Dynasty hub

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

    return (
        handle_extract_rosters,
        handle_initialize_stream,
        handle_launch_dynasty,
        handle_launch_game,
        handle_recover_soft,
        handle_stabilize_main_menu,
        handle_verify_stream,
    )


@app.cell
def _(Enum, auto):
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

    return (PipelineState,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### To-Do
    #### Check `poll_main_menu_with_interrupts`
    - [ ] Review the logic and make sure it is correct.
    #### Main Menu, Featured News Popup, and Hotfix Overlay Templates
    - [x] Capture main menu template image and choose the region for matching.
    - [x] Capture featured news popup circle button template image and choose the region for matching.
    - [ ] Capture hotfix overlay template image and choose the region for matching.
    #### Complete the `handle_launch_dynasty` function
    - [ ] Complete the button sequence to get to the list of dynasties.
    - [ ] Use OCR to select the dynasty by name.
    - [ ] Create semantic wrapper functions for easier readability.
    - [ ] Handle the possibility that the connection to EA Servers has been lost and you need to reconnect via `Button.R2` at the main menu.
    #### Build the `navigate_to_rosters` function
    - [ ] Build `navigate_to_rosters` to get from the dynasty home screen to the "View Rosters" screen.
    #### Optimize timeouts
    - [ ] add timers to everything to see how long the actions are taking.
    - [ ] run the pipeline several times and collect and average the times.
    - [ ] create a table that shows the name of the timer, the average execution time, and the assigned timeout value.
    - [ ] reduce timeouts where there is a large discrepancy between the timeout and the actual time a given task is taking.
    #### Split code into modules
    - [ ] decide on number of modules and module names for the current pipeline code
    - [ ] split each piece of functionality into their corresponding modules
    - [ ] re-organize the `roster_extract.py` to just contain the main launch sequence and appropriate module imports including the new first-party modules.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ___
    ## Appendix
    ### Imports, Logging Configuration, and Dots Per Inch (DPI) Awareness
    """)
    return


@app.cell
def _():
    import ctypes
    import platform
    import subprocess
    import sys
    import time
    from enum import Enum, auto
    from pathlib import Path
    from typing import NamedTuple

    import marimo as mo
    import numpy as np
    import vgamepad as vg
    from loguru import logger
    from PIL import Image

    # ======================
    # Logging Configuration
    # ======================
    def _configure_logging(
        log_dir: str = "logs",
        console_level: str = "DEBUG",
        file_level: str = "DEBUG",
        rotation: str = "10 MB",
        retention: str = "7 days",
    ) -> None:
        """
        Configures global Loguru logging sinks and phase-based file routing.

        This function removes default handlers and establishes a centralized
        logging architecture. It routes all logs to the console and sets up
        specific file sinks to separate logs based on the 'phase' bound to the
        logger (e.g., 'launch', 'extraction', 'analysis'). If no phase is
        bound, it falls back to a default 'global' value for formatting.

        Parameters
        ----------
        log_dir : str, optional
            The base directory where log files will be saved. Default is
            "logs".
        console_level : str, optional
            The minimum log level to display in the standard output (console).
            Default is "DEBUG".
        file_level : str, optional
            The minimum log level to write to the file sinks. Default is
            "DEBUG".
        rotation : str, optional
            The condition for rotating log files (e.g., file size threshold).
            Default is "10 MB".
        retention : str, optional
            The duration to keep rotated log files before automatic deletion.
            Default is "7 days".
        """
        # Create 'logs' directory.
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Reset Loguru's default state.
        logger.remove()

        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<magenta>{extra[phase]}</magenta> | "
            "<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        # Inject a default phase so {extra[phase]} never throws a KeyError.
        logger.configure(extra={"phase": "global"})

        # Console output sink.
        logger.add(sys.stdout, format=log_format, level=console_level, colorize=True)

        # File sink.
        logger.add(
            log_path / "cfb_pipeline_{time:YYYY-MM-DD}.log",
            format=log_format,
            rotation=rotation,
            retention=retention,
            level=file_level,
        )

    # ===============================================
    # DPI Awareness (prevent display scaling issues)
    # ===============================================
    def _make_dpi_aware() -> None:
        """
        Force Windows to treat logical pixels as 1:1 physical pixels.

        This ensures that display scaling does not make window sizing or screen
        capture coordinates inaccurate. It must run before importing libraries
        that interface with the Windows GUI.

        Raises
        ------
        OSError
            If the pipeline is executed on a non-Windows operating system
            (checked first).
        RuntimeError
            If both the primary (shcore) and fallback (user32) Windows API
            calls fail to lock the DPI scaling.
        """
        if platform.system() != "Windows":
            logger.critical(
                "OS Check Failed: Pipeline attempted to run on non-Windows OS."
            )
            raise OSError("This pipeline requires Windows.")

        logger.info("Initializing Windows DPI awareness...")

        try:
            # For Windows 8.1 and Windows 10/11
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            logger.debug("Successfully set DPI awareness using shcore (Windows 8.1+).")
        except (AttributeError, OSError) as _:
            try:
                # Fallback for Windows Vista/7
                ctypes.windll.user32.SetProcessDPIAware()
                logger.debug("Successfully set DPI awareness using user32 fallback.")
            except (AttributeError, OSError) as e:
                logger.critical(
                    "Could not lock Windows DPI scaling. Screen capture coordinates will fail."
                )
                raise RuntimeError(
                    "Critical: Could not lock Windows DPI scaling."
                ) from e

    _configure_logging()
    _make_dpi_aware()

    # Delayed iumports (GUI/Display Dependent).
    import cv2
    import dxcam_cpp as dxcam
    import win32api
    import win32con
    import win32gui

    return (
        Enum,
        Image,
        NamedTuple,
        Path,
        auto,
        cv2,
        dxcam,
        logger,
        mo,
        np,
        subprocess,
        time,
        vg,
        win32api,
        win32con,
        win32gui,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Constants, Classes, and Custom Exceptions
    """)
    return


@app.cell
def _(Enum, NamedTuple, Path, auto, cv2, dxcam, np, vg):
    MAX_ATTEMPTS_LAUNCH = 2
    WINDOW_TITLE = "chiaki-ng"
    camera: dxcam.DXCamera = dxcam.create(  # ty: ignore
        device_idx=0, output_idx=0, output_color="BGRA"
    )
    _PROJECT_DIR = Path.cwd().parent

    class TemplateFileNotFoundError(Exception):
        """Raised when the image template file is not found."""

    class TemplateMatchTimeoutError(Exception):
        """Raised when the timeout is exceeded during polling for a template match."""

    class ChiakiExecutableNotFoundError(Exception):
        """Raised when the `chiaki-ng` executable is not found."""

    class ChiakiWindowNotFoundError(Exception):
        """Raised when the local chiaki-ng window fails to appear or become visible."""

    class ChiakiFullscreenError(Exception):
        """Raised when forcing chiaki to fullscreen fails."""

    class PS5SettingsIconNotFoundError(Exception):
        """Raised when the PS5 Settings Icon is not found on the PS5 home screen."""

    class CFBGameTitleNotFoundError(Exception):
        """Raised when the CFB game title is not found on the PS5 home screen."""

    class HotfixAppliedError(Exception):
        """Raised when a hotfix is detected and dismissed, requiring a clean game restart."""

    def _load_template(path: Path) -> np.ndarray:
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

        TEMPLATES_DIR = _PROJECT_DIR / "assets" / "templates"
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

        template: np.ndarray
        region: tuple[int, int, int, int]  # (left, top, right, bottom)
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

    class InputType(Enum):
        """
        Categorizes the types of virtual controller inputs.

        This enumeration ensures that each button press is routed to the
        correct underlying `vgamepad` method, as standard buttons, D-Pad
        directions, and special buttons require different API calls.

        Attributes
        ----------
        STANDARD : InputType
            Represents standard face buttons, options button, bumpers, and
            triggers.
        DPAD : InputType
            Represents directional pad inputs.
        SPECIAL : InputType
            Represents special buttons, such as the PlayStation button.
        """

        DPAD = auto()
        SPECIAL = auto()
        STANDARD = auto()

    class Button(Enum):
        """
        Mappings for virtual DualShock 4 (DS4) controller inputs.

        This enumeration maps readable button names to their corresponding
        input categories and vgamepad bitmasks. The `.value` property of each
        member returns a `tuple[InputType, int]`.

        Attributes
        ----------
        DPAD_UP : Button
            The D-Pad North (Up) direction.
        DPAD_DOWN : Button
            The D-Pad South (Down) direction.
        DPAD_LEFT : Button
            The D-Pad West (Left) direction.
        DPAD_RIGHT : Button
            The D-Pad East (Right) direction.
        DPAD_NEUTRAL : Button
            The state representing a released or neutral D-Pad.
        SQUARE : Button
            The Square face button.
        TRIANGLE : Button
            The Triangle face button.
        CROSS : Button
            The Cross (X) face button.
        CIRCLE : Button
            The Circle face button.
        L1 : Button
            The L1 bumper button.
        R1 : Button
            The R1 bumper button.
        L2 : Button
            The L2 trigger button.
        R2 : Button
            The R2 trigger button.
        PS : Button
            The PlayStation (PS) special menu button.
        OPTIONS : Button
            The Options menu button.
        """

        # D-Pad Directions.
        DPAD_UP = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
        DPAD_DOWN = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        DPAD_LEFT = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST)
        DPAD_RIGHT = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST)
        DPAD_NEUTRAL = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)

        # Face Buttons.
        SQUARE = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
        TRIANGLE = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
        CROSS = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
        CIRCLE = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)

        # Bumpers and Triggers.
        L1 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
        R1 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
        L2 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)
        R2 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)

        # Menu Buttons.
        PS = (InputType.SPECIAL, vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
        OPTIONS = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)

    class CFBMainMenuState(Enum):
        """
        Enum tracking the identified state of the CFB game main menu.

        Attributes
        ----------
        MAIN_MENU : auto
            Indicates the main menu has been successfully identified and stabilized.
        HOTFIX : auto
            Indicates a hotfix overlay has been detected on the screen.
        """

        MAIN_MENU = auto()
        HOTFIX = auto()

    return (
        Button,
        CFBGameTitleNotFoundError,
        CFBMainMenuState,
        ChiakiExecutableNotFoundError,
        ChiakiFullscreenError,
        ChiakiWindowNotFoundError,
        HotfixAppliedError,
        InputType,
        TemplateConfig,
        TemplateMatchTimeoutError,
        Templates,
        WINDOW_TITLE,
        camera,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Controller Actions
    #### `VirtualController`
    """)
    return


@app.cell
def _(Button, InputType, logger, time, vg):
    class VirtualController:
        """
        A wrapper class to manage controller emulation and input sequences.

        This class encapsulates a virtual DualShock 4 (DS4) gamepad and
        provides standardized methods for executing button presses, D-pad
        movements, and special button interactions with appropriate timing
        buffers.

        Attributes
        ----------
        DEFAULT_TAP_TIME : float
            The standard duration in seconds for a button tap.
        DEFAULT_HOLD_TIME : float
            The standard duration in seconds for a button hold.
        DEFAULT_REST_TIME : float
            The standard duration in seconds to wait after an input is
            released, allowing the corresponding UI animation to finish.
        gamepad : vg.VDS4Gamepad
            The underlying virtual gamepad instance used to send inputs to the
            OS.
        """

        DEFAULT_TAP_TIME = 0.1
        DEFAULT_HOLD_TIME = 1.2
        DEFAULT_REST_TIME = 0.3

        def __init__(self) -> None:
            """Initializes the virtual gamepad."""
            self.gamepad = vg.VDS4Gamepad()

            # Allow the OS time to mount the virtual controller before sending
            # inputs.
            time.sleep(1.0)

        def _execute_action(
            self,
            button: Button,
            action_time: float,
            rest_time: float,
        ) -> None:
            """
            Executes the central sequence of pressing, updating, and releasing.

            This engine standardizes the required delays between sending a
            state change to the virtual controller and resetting it, routing
            the input to the correct vgamepad method based on the input type.

            Parameters
            ----------
            button : Button
                The specific Button enum member to be pressed and released.
            action_time : float
                The duration in seconds to wait while the button is pressed.
            rest_time : float
                The duration in seconds to wait after the button is released.
            """
            input_type, button_val = button.value

            # Press button.
            if input_type == InputType.STANDARD:
                self.gamepad.press_button(button=button_val)
            elif input_type == InputType.SPECIAL:
                self.gamepad.press_special_button(special_button=button_val)
            elif input_type == InputType.DPAD:
                self.gamepad.directional_pad(direction=button_val)

            self.gamepad.update()
            time.sleep(action_time)

            # Release button.
            if input_type == InputType.STANDARD:
                self.gamepad.release_button(button=button_val)
            elif input_type == InputType.SPECIAL:
                self.gamepad.release_special_button(special_button=button_val)
            elif input_type == InputType.DPAD:
                neutral_val = Button.DPAD_NEUTRAL.value[1]
                self.gamepad.directional_pad(direction=neutral_val)

            self.gamepad.update()
            time.sleep(rest_time)

            action_type = "tap" if action_time == self.DEFAULT_TAP_TIME else "hold"

            logger.trace(
                f"Controller input executed: {action_type} {button.name} (rest time: {rest_time}s)"
            )

        def tap(
            self,
            button: Button,
            /,
            *,
            rest_time: float | None = None,
        ) -> None:
            """
            A quick press and release of a controller button.

            Parameters
            ----------
            button : Button
                The specific button to tap.
            rest_time : float, optional
                The duration in seconds to wait after releasing the button.
                Falls back to `DEFAULT_REST_TIME` if None.
            """
            actual_rest = rest_time if rest_time is not None else self.DEFAULT_REST_TIME

            self._execute_action(
                button=button, action_time=self.DEFAULT_TAP_TIME, rest_time=actual_rest
            )

        def hold(
            self,
            button: Button,
            /,
            *,
            rest_time: float | None = None,
        ) -> None:
            """
            A prolonged press and release of a controller button.

            Parameters
            ----------
            button : Button
                The specific button to hold.
            rest_time : float, optional
                The duration in seconds to wait after releasing the button.
                Falls back to `DEFAULT_REST_TIME` if None.
            """
            actual_rest = rest_time if rest_time is not None else self.DEFAULT_REST_TIME

            self._execute_action(
                button=button, action_time=self.DEFAULT_HOLD_TIME, rest_time=actual_rest
            )

    logger.info("Initializing DS4 gamepad emulation...")
    controller = VirtualController()
    return (controller,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Template Matching Functions
    #### `is_image_match`
    #### `poll_for_template_match`
    """)
    return


@app.cell
def _(
    TemplateMatchTimeoutError,
    camera: "dxcam.DXCamera",
    cv2,
    logger,
    np,
    time,
):
    def is_image_match(
        frame: np.ndarray, template: np.ndarray, confidence_threshold: float = 0.90
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
        template: np.ndarray,
        region: tuple[int, int, int, int],
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
        camera.start(target_fps=10, region=region)
        start_time = time.time()

        # Use try-finally block to ensure the background camera thread is
        # stopped even if an error occurs.
        highest_confidence_seen = 0.0
        try:
            while time.time() - start_time < timeout:
                frame: np.ndarray | None = camera.get_latest_frame()

                if frame is not None and frame.max() > 0:
                    is_match, confidence = is_image_match(
                        frame=frame,
                        template=template,
                        confidence_threshold=confidence_threshold,
                    )

                    if confidence > highest_confidence_seen:
                        highest_confidence_seen = confidence

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

    return is_image_match, poll_for_template_match


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### UI Navigation/Evaluation Functions
    #### `focus_first_game_tile`
    #### `focus_welcome_tile`
    #### `is_home_screen_visible`
    #### `return_to_home_screen`
    #### `close_active_game`
    """)
    return


@app.cell
def _(
    Button,
    TemplateConfig,
    TemplateMatchTimeoutError,
    controller,
    logger,
    poll_for_template_match,
):
    def focus_first_game_tile() -> None:
        """Move PS5 home screen cursor from welcome tile to first game tile."""
        logger.info("Moving from welcome tile to the first game tile...")
        controller.tap(Button.DPAD_RIGHT)

    def focus_welcome_tile() -> None:
        """Move PS5 home screen cursor from first game tile to welcome tile."""
        logger.info("Moving cursor to the welcome tile...")
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
        controller.hold(Button.PS, rest_time=1.0)

    def close_active_game() -> None:
        """
        Executes sequence to close active game from home screen.

        This function requires that the PS5 cursor is currently on the active
        game's tile on the home screen prior to executing the button sequence
        for closing the game.
        """
        logger.info("Executing sequence to close the active game...")
        controller.tap(Button.OPTIONS, rest_time=0.5)
        controller.tap(Button.CROSS, rest_time=3.0)

    return (
        close_active_game,
        focus_first_game_tile,
        focus_welcome_tile,
        is_home_screen_visible,
        return_to_home_screen,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch PS5 Functions
    #### `_launch_chiaki_process`
    #### `_find_and_focus_window`
    #### `_ensure_fullscreen`
    #### `launch_ps5`
    """)
    return


@app.cell
def _(
    ChiakiExecutableNotFoundError,
    ChiakiFullscreenError,
    ChiakiWindowNotFoundError,
    Path,
    WINDOW_TITLE,
    logger,
    subprocess,
    time,
    win32api,
    win32con,
    win32gui,
):
    def _launch_chiaki_process() -> None:
        """
        Launches the chiaki-ng application subprocess.

        Raises
        ------
        ChiakiExecutableNotFoundError
            If the chiaki-ng executable cannot be found at the specified path.
        """
        logger.info("Starting chiaki-ng launch sequence...")
        chiaki_path = Path(r"C:\Program Files\chiaki-ng\chiaki.exe")

        if not chiaki_path.exists():
            raise ChiakiExecutableNotFoundError(
                f"Could not find chiaki-ng at {chiaki_path}"
            )

        subprocess.Popen([chiaki_path])
        logger.debug(f"Executed subprocess: {chiaki_path}")

    def _find_and_focus_window(window_title: str) -> int:
        """
        Finds and readies the `window_title` window.

        Polls the OS for a specific window, waits for it to become visible,
        and brings it to the foreground.

        Parameters
        ----------
        window_title : str
            The exact title of the window to search for.

        Returns
        -------
        int
            The window handle (hwnd) of the found window.

        Raises
        ------
        ChiakiWindowNotFoundError
            If the window is not found or visible within the timeout period.
        """
        timeout = 30.0
        start_time = time.time()

        logger.info(f"Polling OS for window '{window_title}' (Timeout: {timeout}s)...")

        while time.time() - start_time < timeout:
            hwnd = win32gui.FindWindow(None, window_title)

            if hwnd and win32gui.IsWindowVisible(hwnd):
                elapsed = round(time.time() - start_time, 2)
                logger.success(
                    f"Window '{window_title}' found and visible after {elapsed}s."
                )
                # Ensure the window is active and focused.
                win32gui.SetForegroundWindow(hwnd)
                return hwnd

            # Pause briefly to prevent CPU thrashing while polling the OS for
            # the window.
            time.sleep(0.1)

        raise ChiakiWindowNotFoundError(
            f"Window '{window_title}' failed to launch within the timeout period."
        )

    def _ensure_fullscreen(hwnd: int, max_attempts: int = 4) -> None:
        """
        Verifies the window is in true full screen and attempts to correct it
        if not.

        This function dynamically identifies which monitor the target window
        is currently on and compares the window's bounding box against that
        specific monitor's coordinates. If they do not match, it brings the
        window to the foreground and simulates an F11 keypress to toggle full
        screen.

        Parameters
        ----------
        hwnd : int
            The window handle (hwnd) of the application to check and modify.
        max_attempts : int, optional
            The maximum number of times to attempt toggling full screen before
            failing. Default is 3.

        Raises
        ------
        ChiakiFullscreenError
            If the window fails to enter full screen mode after the specified
            maximum number of attempts.
        """
        for attempt in range(max_attempts):
            # Get the handle for monitor that currently contains the window.
            # MONITOR_DEFAULTTONEAREST (2) ensures it grabs the closest screen
            # if the window is between two.
            monitor_handle = win32api.MonitorFromWindow(hwnd, 2)

            # Get the exact coordinate boundaries of that specific monitor.
            monitor_info = win32api.GetMonitorInfo(monitor_handle)
            mon_left, mon_top, mon_right, mon_bottom = monitor_info["Monitor"]

            # Get the current window bounding box.
            win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(hwnd)

            # Check if the window perfectly covers its assigned monitor.
            if (
                win_left == mon_left
                and win_top == mon_top
                and win_right == mon_right
                and win_bottom == mon_bottom
            ):
                logger.success("chiaki-ng is in true full screen mode.")
                return

            logger.warning(
                f"Fullscreen check failed (Attempt {attempt + 1}).\n"
                f"Window rect:  {(win_left, win_top, win_right, win_bottom)}\n"
                f"Monitor rect: {(mon_left, mon_top, mon_right, mon_bottom)}\n"
                f"Sending F11 toggle..."
            )

            # Ensure the window is focused before sending keystrokes.
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)

            # Simulate pressing F11 to trigger the chiaki-ng native fullscreen
            # toggle.
            win32api.keybd_event(win32con.VK_F11, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(win32con.VK_F11, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Allow time for the rendering engine to transition.
            time.sleep(1.5)

        raise ChiakiFullscreenError("chiaki-ng fullscreen correction failed.")

    def launch_ps5() -> None:
        """Needs documentation."""
        _launch_chiaki_process()
        hwnd = _find_and_focus_window(window_title=WINDOW_TITLE)
        _ensure_fullscreen(hwnd)

    return (launch_ps5,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch CFB Functions
    #### `launch_cfb_game`
    """)
    return


@app.cell
def _(
    Button,
    CFBGameTitleNotFoundError,
    TemplateConfig,
    TemplateMatchTimeoutError,
    controller,
    logger,
    poll_for_template_match,
):
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

    return (launch_cfb_game,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch Dynasty Functions
    #### `_poll_main_menu_with_interrupts`
    #### `launch_dynasty`
    """)
    return


@app.cell
def _(
    Button,
    CFBMainMenuState,
    HotfixAppliedError,
    TemplateConfig,
    TemplateMatchTimeoutError,
    camera: "dxcam.DXCamera",
    controller,
    is_image_match,
    logger,
    time,
):
    def poll_main_menu_with_interrupts(
        main_menu_config: TemplateConfig,
        hotfix_overlay_config: TemplateConfig,
        timeout: float = 60.0,
    ) -> CFBMainMenuState:
        """
        Polls for the main menu while dismissing pop-ups and checking for hotfixes.

        This function actively captures the screen to identify either the top-half
        main menu template or a hotfix overlay. It continuously taps the circle
        button to dismiss "Featured News" or "Press any button" prompts until the
        main menu is found. Once the main menu is detected, it enters a brief
        stabilization phase to ensure a delayed hotfix overlay does not appear.

        Parameters
        ----------
        top_menu_config : TemplateConfig
            The configuration object containing the visual template and capture
            region for a stable main menu UI element.
        hotfix_config : TemplateConfig
            The configuration object containing the visual template and capture
            region for the hotfix overlay "Yes/No" button prompt.
        timeout : float, optional
            The maximum time in seconds to poll for the menu or hotfix before
            timing out. Default is 60.0.

        Returns
        -------
        CFBMainMenuState
            The final evaluated state of the UI, returning either MAIN_MENU or
            HOTFIX.

        Raises
        ------
        TemplateMatchTimeoutError
            If neither the main menu nor the hotfix overlay is detected within
            the specified timeout period.
        """
        logger.info("Polling for CFB main menu while handling potential pop-ups...")

        camera.start(target_fps=10, region=None)
        start_time = time.time()
        main_menu_found = False
        stabilization_start = 0.0

        try:
            while time.time() - start_time < timeout:
                frame = camera.get_latest_frame()

                if frame is not None and frame.max() > 0:
                    # Check for the hotfix overlay first.
                    h_left, h_top, h_right, h_bottom = hotfix_overlay_config.region
                    hotfix_overlay_region = frame[h_top:h_bottom, h_left:h_right]
                    is_hotfix_overlay, confidence_hotfix_overlay = is_image_match(
                        frame=hotfix_overlay_region,
                        template=hotfix_overlay_config.template,
                    )

                    if is_hotfix_overlay:
                        logger.warning(
                            f"Hotfix overlay detected! (Confidence: {confidence_hotfix_overlay:.2f})"
                        )
                        return CFBMainMenuState.HOTFIX

                    # Check for the Top-Half Main Menu item.
                    if not main_menu_found:
                        m_left, m_top, m_right, m_bottom = main_menu_config.region
                        main_menu_region = frame[m_top:m_bottom, m_left:m_right]
                        is_main_menu, confidence_main_menu = is_image_match(
                            frame=main_menu_region,
                            template=main_menu_config.template,
                            confidence_threshold=0.80,  # Lowered for potential dimming
                        )

                        if is_main_menu:
                            logger.info(
                                f"CFB main menu located! (Confidence: {confidence_main_menu:.2f}). Stabilizing..."
                            )
                            main_menu_found = True
                            stabilization_start = time.time()

                # State actions.
                if main_menu_found:
                    # Wait 10 seconds to ensure a late hotfix overlay doesn't slide in.
                    if time.time() - stabilization_start > 10.0:
                        logger.success(
                            "CFB main menu stabilized. No hotfix overlays detected."
                        )
                        return CFBMainMenuState.MAIN_MENU
                    # Sync with the background camera thread.
                    time.sleep(0.1)
                else:
                    # Keep mashing CIRCLE to get to the main menu.
                    controller.tap(Button.CIRCLE, rest_time=1.0)

            raise TemplateMatchTimeoutError(
                "Failed to reach CFB main menu within the timeout."
            )

        finally:
            camera.stop()

    def launch_dynasty(
        top_menu_config: TemplateConfig, hotfix_config: TemplateConfig
    ) -> None:
        """
        Navigates to the Dynasty mode hub, handling potential hotfixes.

        This function coordinates the transition from the initial load screen
        to the main menu. It evaluates the current menu state via the polling
        function. If a hotfix overlay is detected, it selects "No" to dismiss
        the prompt and raises an error to trigger a clean pipeline restart.

        Parameters
        ----------
        top_menu_config : TemplateConfig
            The configuration object containing the visual template and capture
            region for the top-half main menu target.
        hotfix_config : TemplateConfig
            The configuration object containing the visual template and capture
            region for the hotfix overlay target.

        Raises
        ------
        HotfixAppliedError
            If a hotfix overlay is detected and dismissed, signaling the error
            router to restart the game.
        """
        logger.info("Executing sequence to reach Dynasty mode...")

        menu_state = poll_main_menu_with_interrupts(
            main_menu_config=top_menu_config, hotfix_overlay_config=hotfix_config
        )

        if menu_state == CFBMainMenuState.HOTFIX:
            logger.info(
                "Hotfix overlay detected. Selecting 'No' to dismiss and force restart..."
            )
            controller.tap(Button.CROSS, rest_time=2.0)

            # Throw the error so the router can close and relaunch the game.
            raise HotfixAppliedError("Hotfix dismissed. Game requires a clean restart.")

        logger.info("Entering Dynasty mode...")
        # Logic to navigate from the top menu item down to Dynasty and click Continue.
    return (poll_main_menu_with_interrupts,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Shutdown Pipeline Functions
    #### `_shutdown_chiaki_process`
    #### `shutdown_pipeline`
    #### `reset_pipeline_and_ps5`
    """)
    return


@app.cell
def _(camera: "dxcam.DXCamera", controller, logger, subprocess, time):
    def _shutdown_chiaki_process() -> None:
        """
        Terminates the chiaki-ng application, prioritizing a graceful shutdown.

        Attempts a standard termination to allow chiaki-ng to execute its
        'action on disconnect' (e.g., putting the PS5 in rest mode). If the
        process does not close gracefully within a short timeout, it forcefully
        kills the executable to ensure the stream is disconnected.
        """
        logger.info("Initiating chiaki-ng shutdown...")
        try:
            # Attempt graceful shutdown first (no /F flag).
            logger.debug("Sending graceful close signal to chiaki-ng...")
            subprocess.run(
                ["taskkill", "/IM", "chiaki.exe"],
                capture_output=True,
                text=True,
            )

            # Give the application time to send the sleep command and close.
            time.sleep(5.0)

            # Follow up with a force kill to ensure it isn't hanging.
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/IM", "chiaki.exe"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.warning("chiaki-ng hung and required a force kill to terminate.")
            elif "not found" in result.stderr.lower():
                logger.success("chiaki-ng shut down gracefully.")
            else:
                logger.warning(
                    f"Taskkill returned an unexpected result: {result.stderr.strip()}"
                )

        except Exception:
            logger.exception(
                "Critical error occurred while attempting to terminate chiaki-ng."
            )

    def _reset_virtual_controller() -> None:
        """Resets the virtual gamepad to a neutral state."""
        try:
            controller.gamepad.reset()
            controller.gamepad.update()
            logger.debug("Virtual DS4 controller reset to neutral state.")
        except Exception:
            logger.exception("Failed to reset virtual controller.")

    def _stop_camera_capture() -> None:
        """Safely terminates the background dxcam capture thread if active."""
        try:
            if camera.is_capturing:
                camera.stop()
                logger.debug("Global dxcam capture thread stopped.")
        except Exception:
            logger.exception("Failed to stop dxcam globally.")

    def shutdown_pipeline() -> None:
        """
        Releases hardware resources and forcefully stops external applications.

        Acts as the master cleanup routine for the data pipeline. It resets
        the virtual gamepad to a neutral state to prevent stuck inputs on the
        OS level, stops the global background camera capture thread if it
        remains active, and terminates the remote play stream process.
        """
        logger.info("Executing global pipeline shutdown...")

        _reset_virtual_controller()
        _stop_camera_capture()
        _shutdown_chiaki_process()

    def reset_pipeline_and_ps5() -> None:
        """Shuts down the pipeline and waits for the PS5 to enter rest mode."""
        logger.info(
            "Shutting down pipeline and waiting for PS5 to fully enter rest mode before retrying..."
        )
        shutdown_pipeline()
        time.sleep(30.0)

    return reset_pipeline_and_ps5, shutdown_pipeline


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Convert Image Templates to Grayscale
    #### `convert_template_image_to_grayscale`
    """)
    return


@app.cell
def _(Path, cv2, logger):
    def convert_template_image_to_grayscale(template_path: Path) -> None:
        """
        Reads an image and overwrites it as a 1-channel grayscale image.

        This function takes a specific file path, reads the image using
        OpenCV's grayscale flag, automatically converts it to grayscale, and
        then overwrites the original file on disk with the new single channel
        data.

        Parameters
        ----------
        template_path : pathlib.Path
            The full file path to the specific template image to be converted.
        """
        if not template_path.exists() or not template_path.is_file():
            logger.error(f"File not found: {template_path}")
            return

        logger.info(f"Converting '{template_path.name}' to grayscale...")
        gray_template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

        # Ensure the image loaded successfully to prevent overwriting with a
        # corrupted file.
        if gray_template is not None:
            # Overwrite the original file with the 1-channel grayscale image.
            cv2.imwrite(template_path, gray_template)
            logger.success(
                f"Successfully converted and overwritten: {template_path.name}"
            )
        else:
            logger.error(f"Failed to read or convert: {template_path.name}")

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Preview Image Capture (for prototyping)
    #### `preview_capture`
    """)
    return


@app.cell
def _(Image, camera: "dxcam.DXCamera", cv2, mo, time):
    def preview_capture(
        region: tuple[int, int, int, int], timeout: float = 3.0
    ) -> mo.Html:
        """
        Captures a frame using grab() and outputs it via mo.image().

        This function polls the camera for a specified duration until a valid,
        non-black frame is captured. If successful, it returns the frame as a
        Marimo image component. If the timeout is reached before a valid frame
        is captured, it returns a Marimo markdown component with an error
        message.

        Parameters
        ----------
        region : tuple[int, int, int, int]
            The bounding box coordinates for the capture area in the format
            (left, top, right, bottom).
        timeout : float, optional
            The maximum time in seconds to poll for a valid frame before
            timing out. Default is 3.0 seconds.

        Returns
        -------
        mo.Html
            A Marimo HTML component containing either the captured image or
            a markdown-formatted error message.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            frame = camera.grab(region=region)

            # Check that the frame is populated and not completely black.
            if frame is not None and frame.max() > 0:
                # Convert from dxcam native BGRA to RGB for correct Pillow
                # rendering.
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                image = Image.fromarray(rgb_frame)

                return mo.image(src=image)

            # Hold captures at ~10 FPS to prevent a CPU-hogging tight loop.
            time.sleep(0.1)

        return mo.md("**Error:** Polling timed out. Failed to capture a valid frame.")

    # _test_region = (
    #     100,
    #     140,
    #     600,
    #     600,
    # )
    # preview_capture(region=_test_region)
    return


if __name__ == "__main__":
    app.run()
