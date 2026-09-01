from pathlib import Path

import cv2
from loguru import logger


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
