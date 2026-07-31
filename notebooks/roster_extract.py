import marimo

__generated_with = "0.23.15"
app = marimo.App()


@app.cell
def _():
    import ctypes
    import platform
    import subprocess
    from pathlib import Path
    import sys
    import time

    from loguru import logger

    # ======================
    # Logging Configuration
    # ======================
    logger.remove()

    LOG_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(sys.stdout, format=LOG_FORMAT, level="DEBUG")
    logger.add(
        "logs/cfb_pipeline_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )

    # ===============================================
    # DPI Awareness (prevent display scaling issues)
    # ===============================================
    def make_dpi_aware():
        """Force Windows to treat logical pixels as 1:1 physical pixels."""
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

    # Make sure this script is DPI (Dots Per Inch) aware so that display scaling will not make window sizing inaccurate. This MUST run before importing libraries that interface with the Windows GUI.
    make_dpi_aware()

    # --- Delayed Imports (GUI/Display Dependent) ---
    import dxcam_cpp as dxcam
    import marimo as mo
    import vgamepad as vg  # noqa: F401
    import win32gui
    import cv2

    return Path, cv2, dxcam, logger, mo, subprocess, time, win32gui


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Launch Chiaki-NG
    """)
    return


@app.cell
def _(logger, subprocess, time, win32gui):
    def launch_remote_play_stream(timeout=30):
        logger.info("Starting chiaki-ng launch sequence...")
        chiaki_path = r"C:\Program Files\chiaki-ng\chiaki.exe"

        try:
            subprocess.Popen([chiaki_path])
            logger.debug(f"Executed subprocess: {chiaki_path}")
        except Exception:
            logger.exception("Failed to execute chiaki-ng subprocess.")
            raise

        start_time = time.time()
        hwnd = 0
        window_title = "chiaki-ng"

        logger.info(f"Polling OS for window '{window_title}' (Timeout: {timeout}s)...")

        while time.time() - start_time < timeout:
            hwnd = win32gui.FindWindow(None, window_title)

            if hwnd and win32gui.IsWindowVisible(hwnd):
                elapsed = round(time.time() - start_time, 2)
                logger.success(
                    f"Window '{window_title}' found and visible after {elapsed}s."
                )
                break

            time.sleep(0.1)

        if not hwnd:
            logger.error(f"Window polling timed out after {timeout} seconds.")
            raise TimeoutError(
                f"Window '{window_title}' failed to launch within the timeout period."
            )

        # Ensure the window is active and focused.
        win32gui.SetForegroundWindow(hwnd)

    return (launch_remote_play_stream,)


@app.cell
def _(cv2, logger, time):
    def wait_for_home_screen(camera, template, region, timeout=45):
        logger.info("Starting background capture thread for visual polling...")

        # 1. Start the background thread at a low framerate
        camera.start(target_fps=10, region=region)
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                # 2. Instantly read the latest frame from memory (no GPU delay)
                frame = camera.get_latest_frame()

                # The background thread guarantees non-black frames once initialized
                if frame is not None and frame.max() > 0:
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    result = cv2.matchTemplate(
                        gray_frame, template, cv2.TM_CCOEFF_NORMED
                    )
                    _, max_val, _, _ = cv2.minMaxLoc(result)

                    if max_val > 0.90:
                        logger.success("PS5 Home Screen detected!")
                        return True

                time.sleep(0.1)

            logger.error("Polling timed out.")
            return False

        finally:
            # 3. ALWAYS stop the background thread, even if it fails
            camera.stop()

    return (wait_for_home_screen,)


@app.cell
def _(
    Path,
    cv2,
    dxcam,
    launch_remote_play_stream,
    logger,
    wait_for_home_screen,
):
    project_path = Path.cwd().parent
    template_path = (
        project_path / "assets" / "templates" / "PS5_landing_page_settings_icon.png"
    )
    camera = dxcam.create(device_idx=0, output_idx=0)  # ty: ignore
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    region = (1430, 20, 1520, 105)

    # Execute the startup sequence.
    launch_remote_play_stream()
    is_ready = wait_for_home_screen(camera=camera, template=template, region=region)

    if is_ready:
        logger.info("Ready to begin vgamepad inputs!")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
