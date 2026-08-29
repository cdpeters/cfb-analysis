import time

from loguru import logger

from .capture import _stop_camera_capture
from .chiaki import shutdown_chiaki
from .runtime import get_controller


def shutdown_pipeline() -> None:
    """
    Releases hardware resources and forcefully stops external applications.

    Acts as the master cleanup routine for the data pipeline. It resets
    the virtual gamepad to a neutral state to prevent stuck inputs on the
    OS level, stops the global background camera capture thread if it
    remains active, and terminates the remote play stream process.
    """
    logger.info("Executing global pipeline shutdown...")

    controller = get_controller()

    controller.reset()
    _stop_camera_capture()
    shutdown_chiaki()

def reset_pipeline_and_ps5() -> None:
    """Shuts down the pipeline and waits for the PS5 to enter rest mode."""
    logger.info(
        "Shutting down pipeline and waiting for PS5 to fully enter rest mode before retrying..."
    )
    shutdown_pipeline()
    time.sleep(30.0)
