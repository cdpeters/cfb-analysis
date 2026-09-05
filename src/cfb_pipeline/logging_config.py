import sys
from pathlib import Path

from loguru import logger

from cfb_pipeline.config import LOGS_DIR


def configure_logging(
    log_path: Path = LOGS_DIR,
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
    log_path : Path, optional
        The base directory where log files will be saved. Default is
        LOG_DIR.
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
