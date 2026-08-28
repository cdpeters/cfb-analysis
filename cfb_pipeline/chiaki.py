import subprocess
import time
from pathlib import Path

import win32api
import win32con
import win32gui
from loguru import logger

from cfb_pipeline.config import WINDOW_TITLE
from cfb_pipeline.exceptions import (
    ChiakiExecutableNotFoundError,
    ChiakiFullscreenError,
    ChiakiWindowNotFoundError,
)


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
    start = time.monotonic()
    deadline = start + timeout

    logger.info(f"Polling OS for window '{window_title}' (Timeout: {timeout}s)...")

    while time.monotonic() < deadline:
        hwnd = win32gui.FindWindow(None, window_title)

        if hwnd and win32gui.IsWindowVisible(hwnd):
            elapsed = round(time.monotonic() - start, 2)
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
