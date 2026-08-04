import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch the `chiaki-ng` Client and Wait for Window to be Drawn
    """)


@app.cell
def _(Path, logger, subprocess, time, win32gui):
    def launch_chiaki_process() -> None:
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

    def wait_and_focus_window(window_title: str, timeout: float = 30.0) -> int:
        """
        Waits for the `window_title` window to be ready.

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
        TimeoutError
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
        raise TimeoutError(
            f"Window '{window_title}' failed to launch within the timeout period."
        )

    return launch_chiaki_process, wait_and_focus_window


@app.cell
def _(camera, cv2, logger, np, time):
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
            "PS5 Home Screen" or "CFB 27 Game Tile") to provide context in
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
                    is_match, confidence = is_image_match(
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
    ### Main Launch Sequence
    """)


@app.cell(disabled=True)
def _(
    Templates,
    VirtualController,
    launch_chiaki_process,
    logger,
    poll_for_template_match,
    wait_and_focus_window,
    window_title,
):
    # Execute the startup sequence.
    launch_chiaki_process()
    wait_and_focus_window(window_title=window_title)
    # Look for the PS5 settings icon to be present. This indicates the
    # connection is ready to start accepting controller inputs.
    is_ready = poll_for_template_match(
        template=Templates.PS5_SETTINGS_ICON.template,
        region=Templates.PS5_SETTINGS_ICON.region,
        log_context=Templates.PS5_SETTINGS_ICON.log_context,
        timeout=45.0,
    )

    if is_ready:
        logger.info("Initializing DS4 gamepad emulation...")
        # Emulating a DualShock 4 is standard for remote play clients
        controller = VirtualController()
    return (controller,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### UI Manipulation Controller Functions
    """)


@app.cell
def _(Callable, Controller, time, vg):
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
                    direction=Controller.DPAD_NEUTRAL
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

    return (VirtualController,)


@app.cell
def _(Controller, controller, logger, np, poll_for_template_match):
    def launch_target_game(
        template: np.ndarray,
        region: tuple[int, int, int, int],
        log_context: str,
        max_attempts: int = 10,
    ) -> None:
        """Navigate the PS5 home screen to find and launch the game."""
        logger.info("Moving from welcome tile to the first game tile...")
        controller.tap_dpad(Controller.DPAD_RIGHT)

        for attempt in range(max_attempts):
            logger.info(f"Evaluating game tile {attempt + 1}...")
            # Bring up the options for the current game tile's game.
            controller.tap_button(Controller.OPTIONS, rest_time=0.5)

            # D-Pad down x5 to get to the "Information" option.
            for _ in range(5):
                controller.tap_dpad(Controller.DPAD_DOWN, rest_time=0.15)

            # Cross to select the "Information" option.
            controller.tap_button(Controller.CROSS, rest_time=1.5)

            # Look for a match with the CFB27 game tile template.
            is_target_game = poll_for_template_match(
                template=template,
                region=region,
                log_context=log_context,
                timeout=5.0,
            )

            # Circle to back out.
            controller.tap_button(Controller.CIRCLE, rest_time=1.0)

            # If a match is found, launch the game. Otherwise move to the next
            # game tile.
            if is_target_game:
                logger.success("Target game located. Launching...")
                controller.tap_button(Controller.CROSS)
                return
            else:
                logger.info("Target game not found. Shifting to next tile...")
                controller.tap_dpad(Controller.DPAD_RIGHT)

        logger.error(f"Failed to locate the game after {max_attempts} tiles.")
        raise RuntimeError(f"Target game could not be located after {max_attempts} tile shifts.")

    return (launch_target_game,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Find and Launch College Football 27
    """)


@app.cell(disabled=True)
def _(Templates, launch_target_game):
    launch_target_game(
        template=Templates.CFB27_GAME_TILE.template,
        region=Templates.CFB27_GAME_TILE.region,
        log_context=Templates.CFB27_GAME_TILE.log_context,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Close Game Function
    """)


@app.cell
def _(Controller, controller):
    def close_game() -> None:
        controller.tap_special_button(Controller.PS)



@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Appendix
    ### Imports, Logging Configuration, and Dots Per Inch (DPI) Awareness
    """)


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
        win32gui,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Constants
    """)


@app.cell
def _(IntEnum, NamedTuple, Path, cv2, dxcam, np, vg):
    _project_dir = Path.cwd().parent

    class TemplatePaths:
        BASE_DIR: Path = _project_dir / "assets" / "templates"
        PS5_SETTINGS_ICON = BASE_DIR / "ps5_settings_icon.png"
        CFB27_GAME_TILE = BASE_DIR / "cfb27_game_tile.png"

    class TemplateConfig(NamedTuple):
        template: np.ndarray
        region: tuple[int, int, int, int]  # (left, top, right, bottom)
        log_context: str

    class Templates:
        PS5_SETTINGS_ICON = TemplateConfig(
            template=cv2.imread(TemplatePaths.PS5_SETTINGS_ICON, cv2.IMREAD_GRAYSCALE),  # ty: ignore
            region=(1430, 20, 1520, 105),
            log_context="PS5 Home Screen",
        )
        CFB27_GAME_TILE = TemplateConfig(
            template=cv2.imread(TemplatePaths.CFB27_GAME_TILE, cv2.IMREAD_GRAYSCALE),  # ty: ignore
            region=(100, 140, 600, 600),
            log_context="CFB27 Game Tile Search",
        )

    class Controller(IntEnum):
        # D-Pad Directions
        DPAD_UP = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
        DPAD_DOWN = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
        DPAD_LEFT = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
        DPAD_RIGHT = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
        DPAD_NEUTRAL = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE

        # Face Buttons
        SQUARE = vg.DS4_BUTTONS.DS4_BUTTON_SQUARE
        TRIANGLE = vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE
        CROSS = vg.DS4_BUTTONS.DS4_BUTTON_CROSS
        CIRCLE = vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE

        # Menu Buttons
        PS = vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS
        OPTIONS = vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS

    window_title = "chiaki-ng"
    camera = dxcam.create(device_idx=0, output_idx=0, output_color="BGRA")  # ty: ignore
    return Controller, Templates, camera, window_title


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Preview Image Capture (for prototyping)
    """)


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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Convert Image Templates to Grayscale
    """)


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



if __name__ == "__main__":
    app.run()
