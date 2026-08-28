import subprocess

from loguru import logger


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
