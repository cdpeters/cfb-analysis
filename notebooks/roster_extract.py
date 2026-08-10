import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell
def _(
    Buttons,
    Templates,
    controller,
    logger,
    poll_for_template_match,
    shutdown_pipeline_resources,
    time,
):
    def is_stream_active() -> bool:
        """
        Forces the PS5 home screen and checks if the video stream is live.

        Returns
        -------
        bool
            True if the PS5 settings icon is successfully matched within the
            timeout, or False if a TimeoutError is caught.
        """
        controller.tap_special(special_button=Buttons.PS, hold_time=1.2, rest_time=2.0)
        try:
            poll_for_template_match(
                template=Templates.PS5_SETTINGS_ICON.template,
                region=Templates.PS5_SETTINGS_ICON.region,
                log_context="Verify Stream Active",
                timeout=5.0,
            )
            return True
        except TimeoutError:
            return False

    def close_active_game() -> None:
        """Executes the button sequence to close an active game from the home screen."""
        controller.tap_button(button=Buttons.OPTIONS, rest_time=0.5)
        controller.tap_button(button=Buttons.CROSS, rest_time=2.0)

    def execute_retry_delay(attempt: int, max_attempts: int) -> bool:
        """
        Shuts down resources and waits for the PS5 to enter rest mode.

        Parameters
        ----------
        attempt : int
            The current attempt index (0-indexed).
        max_attempts : int
            The maximum number of retry attempts allowed before aborting.

        Returns
        -------
        bool
            True if the pipeline should retry the launch sequence, or False if
            the maximum connection attempts have been reached.
        """
        shutdown_pipeline_resources()
        if attempt < max_attempts - 1:
            logger.info("Waiting for PS5 to fully enter rest mode...")
            time.sleep(30.0)
            logger.info("Retrying PS5 launch sequence...")
            return True
        else:
            logger.error("Max connection attempts reached. Aborting pipeline.")
            return False

    return close_active_game, execute_retry_delay, is_stream_active


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Main Launch Sequence
    """)
    return


@app.cell
def _(
    Buttons,
    ChiakiWindowNotFoundError,
    PS5SettingsIconNotFoundError,
    Templates,
    close_active_game,
    controller,
    execute_retry_delay,
    is_stream_active,
    launch_cfb_game,
    launch_ps5,
    logger,
    shutdown_pipeline_resources,
    time,
):
    max_attempts = 2

    try:
        for attempt in range(max_attempts):
            try:
                launch_ps5(target_config=Templates.PS5_SETTINGS_ICON)
                logger.info("Moving from welcome tile to the first game tile...")
                controller.tap_dpad(Buttons.DPAD_RIGHT)
                launch_cfb_game(target_config=Templates.CFB_GAME_TILE)
                # Simulate pipeline work and then completion with a delay.
                time.sleep(15)
                # launch_dynasty()
                # navigate_to_rosters()

                logger.success("Main launch sequence completed successfully!")
                break  # Triggers the finally block, then exits

            except PS5SettingsIconNotFoundError:
                logger.info(
                    "Settings icon not found. Verifying if connection is hung or a game is open..."
                )

                if is_stream_active():
                    logger.info(
                        "Stream is active. Initiating recovery sequence for unclosed game..."
                    )
                    close_active_game()
                    launch_cfb_game(target_config=Templates.CFB_GAME_TILE)
                    # Simulate pipeline work and then completion with a delay.
                    time.sleep(15)
                    logger.success("Recovery sequence completed successfully!")
                    break

                else:
                    logger.error(
                        f"Stream is unresponsive (connection failed on attempt {attempt + 1})."
                    )
                    if execute_retry_delay(attempt, max_attempts):
                        continue
                    break

            except ChiakiWindowNotFoundError:
                logger.error(
                    "Local chiaki-ng window failed to launch. Aborting pipeline."
                )
                break

    finally:
        logger.info("Executing final pipeline teardown...")
        shutdown_pipeline_resources()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### To-Do
    #### Replace template match in the CFB game launch sequence with an easier one
    - [ ] grab an image of the "EA SPORTS College Football 27" text
    - [ ] convert that image to grayscale
    - [ ] adjust the template matching region (`Templates.CFB_GAME_TILE.region`) to be in the area where the text to the bottom right of the game tile shows up
    - [ ] replace the previous template match in `launch_cfb_game` with this template match. It will be much less button clicks and animation wait times.

    #### Retry Logic: Handling unclosed game upon PS5 launch
    - [x] Create new exception: `PS5SettingsIconNotFoundError`:
        - [x] Create the `PS5SettingsIconNotFoundError` class
        - [x] Except this if `launch_ps5` fails because it doesn't find the settings icon
    - [x] Encapsulate the template match game tile sequence as a function to separate it from the very first step of moving one step to the right from the welcome screen. This is because it can be reused below since holding the PS button returns to the home screen but specifically places the cursor on the first game tile, not the welcome tile.
    - [x] Implement retry logic as follows
        - [x] hold PS button to return to home screen
        - [x] initiate the template match game tile sequence, the one just encapsulated as a function

    #### Retry Logic: Handling `TimeoutError` in `launch_ps5` due to remote play fails to connect
    - [x] If the `TimeoutError` is raised in `launch_ps5`, shutdown the pipeline
    - [x] wait to allow for the ps5 to get fully into rest mode
    - [x] retry the PS5 launch sequence.
    - [x] Add `max_attempts` for the retry logic and default it to 1. Possibly change it to 2 if hanging a second time is common.
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
    from collections.abc import Callable
    from enum import IntEnum
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
    logger.remove()

    _log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    _notebook_log_level = "DEBUG"
    _file_log_level = "DEBUG"

    logger.add(sys.stdout, format=_log_format, level=_notebook_log_level, colorize=True)
    logger.add(
        "logs/cfb_pipeline_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="7 days",
        level=_file_log_level,
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

    _make_dpi_aware()

    # Delayed iumports (GUI/Display Dependent).
    import cv2
    import dxcam_cpp as dxcam
    import win32api
    import win32con
    import win32gui

    return (
        Callable,
        Image,
        IntEnum,
        NamedTuple,
        Path,
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
    ### Constants and Custom Exceptions
    """)
    return


@app.cell
def _(IntEnum, NamedTuple, Path, cv2, dxcam, np, vg):
    WINDOW_TITLE = "chiaki-ng"
    camera = dxcam.create(device_idx=0, output_idx=0, output_color="BGRA")  # ty: ignore
    _PROJECT_DIR = Path.cwd().parent

    class _TemplatePaths:
        """
        Centralized file paths for all OpenCV image templates.

        Attributes
        ----------
        BASE_DIR : pathlib.Path
            The root directory containing the template image assets.
        PS5_SETTINGS_ICON : pathlib.Path
            The file path to the PS5 home screen settings icon template.
        CFB_GAME_TILE : pathlib.Path
            The file path to the College Football game tile template.
        """

        BASE_DIR: Path = _PROJECT_DIR / "assets" / "templates"
        PS5_SETTINGS_ICON = BASE_DIR / "ps5_settings_icon.png"
        CFB_GAME_TILE = BASE_DIR / "cfb_game_tile.png"

    class _TemplateConfig(NamedTuple):
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

        This class acts as a namespace to hold instantiated `_TemplateConfig`
        objects, ensuring templates are loaded into memory once and their
        search regions are standardized.

        Attributes
        ----------
        PS5_SETTINGS_ICON : _TemplateConfig
            Configuration for detecting the settings icon on the PS5 home
            screen.
        CFB_GAME_TILE : _TemplateConfig
            Configuration for detecting the College Football game tile.
        """

        PS5_SETTINGS_ICON = _TemplateConfig(
            template=cv2.imread(_TemplatePaths.PS5_SETTINGS_ICON, cv2.IMREAD_GRAYSCALE),  # ty: ignore
            region=(1430, 20, 1520, 105),
            log_context="PS5 Home Screen",
        )
        CFB_GAME_TILE = _TemplateConfig(
            template=cv2.imread(_TemplatePaths.CFB_GAME_TILE, cv2.IMREAD_GRAYSCALE),  # ty: ignore
            region=(100, 140, 600, 600),
            log_context="CFB Game Tile Search",
        )

    class Buttons(IntEnum):
        """
        Mappings for virtual DualShock 4 (DS4) controller inputs.

        This enumeration maps simplified, readable button names to the
        underlying integer bitmasks and constants required by the `vgamepad`
        library.

        Attributes
        ----------
        DPAD_UP : int
            The bitmask for the D-Pad North (Up) direction.
        DPAD_DOWN : int
            The bitmask for the D-Pad South (Down) direction.
        DPAD_LEFT : int
            The bitmask for the D-Pad West (Left) direction.
        DPAD_RIGHT : int
            The bitmask for the D-Pad East (Right) direction.
        DPAD_NEUTRAL : int
            The value representing a released or neutral D-Pad state.
        SQUARE : int
            The bitmask for the Square face button.
        TRIANGLE : int
            The bitmask for the Triangle face button.
        CROSS : int
            The bitmask for the Cross (X) face button.
        CIRCLE : int
            The bitmask for the Circle face button.
        L1 : int
            The bitmask for the L1 button.
        R1 : int
            The bitmask for the R1 button.
        L2 : int
            The bitmask for the L2 button.
        R2 : int
            The bitmask for the R2 button.
        PS : int
            The bitmask for the PlayStation (PS) special menu button.
        OPTIONS : int
            The bitmask for the Options menu button.
        """

        # D-Pad Directions.
        DPAD_UP = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
        DPAD_DOWN = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
        DPAD_LEFT = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
        DPAD_RIGHT = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
        DPAD_NEUTRAL = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE

        # Face Buttons.
        SQUARE = vg.DS4_BUTTONS.DS4_BUTTON_SQUARE
        TRIANGLE = vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE
        CROSS = vg.DS4_BUTTONS.DS4_BUTTON_CROSS
        CIRCLE = vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE

        # Bumpers and Triggers.
        L1 = vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT
        R1 = vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT
        L2 = vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT
        R2 = vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT

        # Menu Buttons.
        PS = vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS
        OPTIONS = vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS

    class ChiakiWindowNotFoundError(Exception):
        """Raised when the local chiaki-ng window fails to appear or become visible."""

    class PS5SettingsIconNotFoundError(Exception):
        """Raised when the PS5 Settings Icon is not found on the PS5 home screen."""

    class CFBGameTileNotFoundError(Exception):
        """Raised when the CFB game tile is not found on the PS5 home screen."""

    return (
        Buttons,
        CFBGameTileNotFoundError,
        ChiakiWindowNotFoundError,
        PS5SettingsIconNotFoundError,
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
def _(Buttons, Callable, logger, time, vg):
    class VirtualController:
        """
        A wrapper class to manage controller emulation and input sequences.

        This class encapsulates a virtual DualShock 4 (DS4) gamepad and
        provides standardized methods for executing button presses, D-pad
        movements, and special button interactions with appropriate timing
        buffers.

        Attributes
        ----------
        gamepad : vg.VDS4Gamepad
            The underlying virtual gamepad instance used to send inputs to the
            OS.
        default_hold : float
            The standard duration in seconds to hold an input if a specific
            time is not provided.
        default_rest : float
            The standard duration in seconds to wait after an input if a
            specific time is not provided.
        """

        def __init__(
            self, default_hold: float = 0.1, default_rest: float = 0.3
        ) -> None:
            """
            Initializes the virtual gamepad and default timing parameters.

            Parameters
            ----------
            default_hold : float, optional
                The base duration in seconds to hold a button. Default is 0.1.
            default_rest : float, optional
                The base duration in seconds to wait after releasing a button.
                Default is 0.3.
            """
            self.gamepad = vg.VDS4Gamepad()
            self.default_hold = default_hold
            self.default_rest = default_rest
            time.sleep(1.0)

        def _execute_tap_sequence(
            self,
            press_action: Callable[[], None],
            release_action: Callable[[], None],
            hold_time: float | None = None,
            rest_time: float | None = None,
        ) -> None:
            """
            Executes the central sequence of pressing, updating, and releasing.

            This engine standardizes the required delays between sending a
            state change to the virtual controller and resetting it.

            Parameters
            ----------
            press_action : Callable[[], None]
                A parameterless function that triggers the button press state.
            release_action : Callable[[], None]
                A parameterless function that triggers the button release
                state.
            hold_time : float, optional
                The duration in seconds to wait while the button is pressed.
                Falls back to `default_hold` if None.
            rest_time : float, optional
                The duration in seconds to wait after the button is released.
                Falls back to `default_rest` if None.
            """
            actual_hold = hold_time if hold_time is not None else self.default_hold
            actual_rest = rest_time if rest_time is not None else self.default_rest

            press_action()
            self.gamepad.update()
            time.sleep(actual_hold)

            release_action()
            self.gamepad.update()
            time.sleep(actual_rest)

        def tap_button(
            self,
            button: int,
            hold_time: float | None = None,
            rest_time: float | None = None,
        ) -> None:
            """
            Simulates pressing and releasing a standard DS4 face button.

            Parameters
            ----------
            button : int
                The integer bitmask representing the specific face button to
                press (e.g., Cross, Circle, Options).
            hold_time : float, optional
                The duration in seconds to hold the button down. Default is
                self.default_hold.
            rest_time : float, optional
                The duration in seconds to wait after releasing the button.
                Default is self.default_rest.
            """
            self._execute_tap_sequence(
                press_action=lambda: self.gamepad.press_button(button=button),
                release_action=lambda: self.gamepad.release_button(button=button),
                hold_time=hold_time,
                rest_time=rest_time,
            )

        def tap_dpad(
            self,
            direction: int,
            hold_time: float | None = None,
            rest_time: float | None = None,
        ) -> None:
            """
            Simulates pressing and releasing a DS4 D-Pad direction.

            Unlike standard buttons, the D-Pad requires resetting to a specific
            neutral state rather than just a general release function.

            Parameters
            ----------
            direction : int
                The integer value representing the specific D-Pad direction to
                press (e.g., North, South, East, West).
            hold_time : float, optional
                The duration in seconds to hold the direction down. Default is
                self.default_hold.
            rest_time : float, optional
                The duration in seconds to wait after resetting to neutral.
                Default is self.default_rest.
            """
            self._execute_tap_sequence(
                press_action=lambda: self.gamepad.directional_pad(direction=direction),
                release_action=lambda: self.gamepad.directional_pad(
                    direction=Buttons.DPAD_NEUTRAL
                ),
                hold_time=hold_time,
                rest_time=rest_time,
            )

        def tap_special(
            self,
            special_button: int,
            hold_time: float | None = None,
            rest_time: float | None = None,
        ) -> None:
            """
            Simulates pressing and releasing a DS4 special button.

            Special buttons include inputs like the PlayStation (PS) button or
            the Touchpad click.

            Parameters
            ----------
            special_button : int
                The integer value representing the specific special button to
                press.
            hold_time : float, optional
                The duration in seconds to hold the button down. Default is
                self.default_hold.
            rest_time : float, optional
                The duration in seconds to wait after releasing the button.
                Default is self.default_rest.
            """
            self._execute_tap_sequence(
                press_action=lambda: self.gamepad.press_special_button(
                    special_button=special_button
                ),
                release_action=lambda: self.gamepad.release_special_button(
                    special_button=special_button
                ),
                hold_time=hold_time,
                rest_time=rest_time,
            )

    logger.info("Initializing DS4 gamepad emulation...")
    controller = VirtualController()
    return (controller,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Template Matching Functions
    #### `_is_image_match`
    #### `poll_for_template_match`
    """)
    return


@app.cell
def _(camera, cv2, logger, np, time):
    def _is_image_match(
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
            The BGR color image array (captured frame) to be evaluated.
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
            "PS5 Home Screen" or "CFB Game Tile") to provide context in
            the logs.
        timeout : float, optional
            The maximum time in seconds to wait for a successful match.
            Default is 5.0.
        confidence_threshold : float, optional
            The minimum match value (0.0 to 1.0) required to register a
            success. Default is 0.90.

        Raises
        ------
        TimeoutError
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
        try:
            while time.time() - start_time < timeout:
                frame = camera.get_latest_frame()

                if frame is not None and frame.max() > 0:
                    is_match, confidence = _is_image_match(
                        frame, template, confidence_threshold
                    )

                    if is_match:
                        logger.success(
                            f"Successfully matched '{log_context}'! (Confidence: {confidence:.2f})"
                        )
                        return

                # Sync with the 10 FPS background camera thread to prevent
                # redundant cv2 processing.
                time.sleep(0.1)

            logger.error(
                f"Polling for '{log_context}' timed out after {timeout} seconds."
            )
            raise TimeoutError(f"Failed to match '{log_context}' within {timeout}s.")

        finally:
            camera.stop()

    return (poll_for_template_match,)


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
    ChiakiWindowNotFoundError,
    PS5SettingsIconNotFoundError,
    Path,
    WINDOW_TITLE,
    logger,
    poll_for_template_match,
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
        FileNotFoundError
            If the chiaki-ng executable cannot be found at the specified path.
        Exception
            If the underlying subprocess fails to execute.
        """
        logger.info("Starting chiaki-ng launch sequence...")
        chiaki_path = Path(r"C:\Program Files\chiaki-ng\chiaki.exe")

        if not chiaki_path.exists():
            logger.error(f"Executable not found at: {chiaki_path}")
            raise FileNotFoundError(f"Could not find chiaki-ng at {chiaki_path}")

        try:
            subprocess.Popen([chiaki_path])
            logger.debug(f"Executed subprocess: {chiaki_path}")
        except Exception:
            logger.exception("Failed to execute chiaki-ng subprocess.")
            raise

    def _find_and_focus_window(window_title: str, timeout: float = 30.0) -> int:
        """
        Finds and readies the `window_title` window.

        Polls the OS for a specific window, waits for it to become visible,
        and brings it to the foreground.

        Parameters
        ----------
        window_title : str
            The exact exact title of the window to search for.
        timeout : float, optional
            The maximum time in seconds to poll for the window. Default is
            30.0.

        Returns
        -------
        int
            The window handle (HWND) of the found window.

        Raises
        ------
        ChiakiWindowNotFoundError
            If the window is not found or visible within the timeout period.
        """
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

        logger.error(f"Window polling timed out after {timeout} seconds.")
        raise ChiakiWindowNotFoundError(
            f"Window '{window_title}' failed to launch within the timeout period."
        )

    def ensure_fullscreen(hwnd: int, max_attempts: int = 3) -> None:
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
            The window handle (HWND) of the application to check and modify.
        max_attempts : int, optional
            The maximum number of times to attempt toggling full screen before
            failing. Default is 3.

        Raises
        ------
        RuntimeError
            If the window fails to enter full screen mode after the specified
            maximum number of attempts.
        """
        for attempt in range(max_attempts):
            # 1. Get the handle for the monitor that currently contains the window
            # MONITOR_DEFAULTTONEAREST (2) ensures it grabs the closest screen if the window is between two
            monitor_handle = win32api.MonitorFromWindow(hwnd, 2)

            # 2. Get the exact coordinate boundaries of that specific monitor
            monitor_info = win32api.GetMonitorInfo(monitor_handle)
            mon_left, mon_top, mon_right, mon_bottom = monitor_info["Monitor"]

            # 3. Get the current window bounding box
            win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(hwnd)

            # 4. Check if the window perfectly covers its assigned monitor
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

            # Ensure the window is focused before sending keystrokes
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)

            # Simulate pressing F11 to trigger the chiaki-ng native fullscreen toggle
            win32api.keybd_event(win32con.VK_F11, 0, 0, 0)
            win32api.keybd_event(win32con.VK_F11, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Allow time for the rendering engine to transition
            time.sleep(1.5)

        logger.error("Failed to force chiaki-ng into full screen mode.")
        raise RuntimeError("chiaki-ng fullscreen correction failed.")

    def launch_ps5(target_config: _TemplateConfig) -> None:
        """
        Executes the startup sequence to establish a remote play connection.

        This function coordinates the initial pipeline steps: it launches the
        chiaki-ng client, forces the application window to the foreground, and
        polls the capture region until the PS5 home screen is verified. Upon
        successful completion, the stream is active and ready for virtual
        controller inputs.

        Parameters
        ----------
        target_config : _TemplateConfig
            The configuration object containing the visual template, capture
            region, and logging context used to verify the PS5 home screen.

        Raises
        ------
        FileNotFoundError
            If the chiaki-ng executable cannot be found during the launch
            process.
        ChiakiWindowNotFoundError
            If the chiaki-ng window fails to appear or become visible within
            the timeout period.
        PS5SettingsIconNotFoundError
            If the PS5 settings icon is not detected on the screen within the
            45.0-second polling timeout (e.g., if a game was left unclosed
            and the console did not boot to the home screen).
        Exception
            If the underlying subprocess fails to execute chiaki-ng.
        """
        _launch_chiaki_process()
        hwnd = _find_and_focus_window(window_title=WINDOW_TITLE)
        # Force full screen before initiating any template matching
        _ensure_fullscreen(hwnd)

        try:
            # Check to see if the PS5 homescreen is showing.
            poll_for_template_match(
                template=target_config.template,
                region=target_config.region,
                log_context=target_config.log_context,
                timeout=45.0,
            )
        except TimeoutError as e:
            logger.warning("Settings icon not found. A game may have been left open.")
            raise PS5SettingsIconNotFoundError(
                "PS5 Settings Icon not found on the home screen."
            ) from e

    return (launch_ps5,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch CFB Function
    #### `launch_cfb_game`
    """)
    return


@app.cell
def _(
    Buttons,
    CFBGameTileNotFoundError,
    controller,
    logger,
    poll_for_template_match,
):
    def launch_cfb_game(target_config: _TemplateConfig, max_attempts: int = 10) -> None:
        """
        Navigates the PS5 home screen to find and launch College Football.

        Iterates through the recent games list on the PS5 home screen, opening
        the "Information" menu for each tile to reliably check the game's icon
        against the provided template configuration. If found, it launches the
        game.

        Parameters
        ----------
        target_config : _TemplateConfig
            The configuration object containing the visual template, capture
            region, and logging context used to identify the CFB game tile.
        max_attempts : int, optional
            The maximum number of game tiles to shift through before failing.
            Default is 10.

        Raises
        ------
        CFBGameTileNotFoundError
            If the target game tile cannot be located after shifting through the
            specified maximum number of attempts.
        """
        for attempt in range(max_attempts):
            logger.info(f"Evaluating game tile {attempt + 1}...")
            # Bring up the options for the current game tile's game.
            controller.tap_button(Buttons.OPTIONS, rest_time=0.5)

            # D-Pad down x5 to get to the "Information" option.
            for _ in range(5):
                controller.tap_dpad(Buttons.DPAD_DOWN, rest_time=0.15)

            # Cross to select the "Information" option.
            controller.tap_button(Buttons.CROSS, rest_time=1.5)

            # Look for a match with the CFB game tile template.
            try:
                poll_for_template_match(
                    template=target_config.template,
                    region=target_config.region,
                    log_context=target_config.log_context,
                    timeout=5.0,
                )
            except TimeoutError:
                # Circle to back out of "Information" screen.
                controller.tap_button(Buttons.CIRCLE, rest_time=1.0)
                logger.info("Target game not found. Shifting to next tile...")
                controller.tap_dpad(Buttons.DPAD_RIGHT)
                continue

            # Circle to back out of "Information" screen.
            controller.tap_button(Buttons.CIRCLE, rest_time=1.0)
            logger.success("Target game located. Launching...")
            controller.tap_button(Buttons.CROSS)
            return

        logger.error(f"Failed to locate the game after {max_attempts} tiles.")
        raise CFBGameTileNotFoundError(
            f"Target game could not be located after {max_attempts} tile shifts."
        )

    return (launch_cfb_game,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Shutdown Pipeline Functions
    #### `shutdown_chiaki_process`
    #### `shutdown_pipeline_resources`
    """)
    return


@app.cell
def _(camera, controller, logger, subprocess, time):
    def _shutdown_chiaki_process() -> None:
        """
        Terminates the chiaki-ng application, prioritizing a graceful shutdown.

        Attempts a standard termination to allow chiaki-ng to execute its
        'action on disconnect' (e.g., putting the PS5 in rest mode). If the
        process does not close gracefully within a short timeout, it forcefully
        kills the executable to ensure the stream is disconnected.

        Raises
        ------
        Exception
            If a critical error occurs during the `subprocess.run` executions
            (the exception is caught and logged internally).
        """
        logger.info("Initiating chiaki-ng shutdown...")
        try:
            # 1. Attempt graceful shutdown first (no /F flag).
            # This sends a close signal, allowing the app to run cleanup routines.
            logger.debug("Sending graceful close signal to chiaki-ng...")
            subprocess.run(
                ["taskkill", "/IM", "chiaki.exe"], capture_output=True, text=True
            )

            # Give the application time to send the sleep command and close.
            time.sleep(10.0)

            # 2. Follow up with a force kill to ensure it isn't hanging.
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

    def shutdown_pipeline_resources() -> None:
        """
        Releases hardware resources and forcefully stops external applications.

        Acts as the master cleanup routine for the data pipeline. It resets
        the virtual gamepad to a neutral state to prevent stuck inputs on the
        OS level, stops the global background camera capture thread if it
        remains active, and terminates the remote play stream process.
        """
        logger.info("Executing global pipeline shutdown...")

        # 1. Reset the Virtual Controller
        try:
            controller.gamepad.reset()
            controller.gamepad.update()
            logger.debug("Virtual DS4 controller reset to neutral state.")
        except Exception:
            logger.warning("Failed to reset virtual controller.")

        # 2. Stop the dxcam Capture
        try:
            if camera.is_capturing:
                camera.stop()
                logger.debug("Global dxcam capture thread stopped.")
        except Exception:
            logger.warning("Failed to stop dxcam globally.")

        # 3. Kill the Stream
        _shutdown_chiaki_process()

    return (shutdown_pipeline_resources,)


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
def _(Image, camera, cv2, mo, time):
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
