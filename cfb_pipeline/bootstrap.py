import ctypes
import platform

from loguru import logger

from cfb_pipeline.logging_config import configure_logging


def make_dpi_aware() -> None:
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

def bootstrap() -> None:
    """Perform process-wide initialization before GUI-dependent imports."""
    configure_logging()
    make_dpi_aware()
