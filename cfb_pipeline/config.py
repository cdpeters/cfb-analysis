from pathlib import Path

from cfb_pipeline.types import Region

MAX_ATTEMPTS_LAUNCH = 2
WINDOW_TITLE = "chiaki-ng"

# Paths.
_PROJECT_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = _PROJECT_DIR / "assets" / "templates"

# Dynasty Name.
TARGET_DYNASTY_NAME = "dynasty-name"

# Dynasty screen regions.
DYNASTY_LIST_REGION: Region = (55, 290, 695, 925)
SCROLLBAR_REGION: Region = (680, 150, 705, 925)

# Dynasty card detection.
BRIGHTNESS_THRESHOLD = 200

MORPH_KERNEL_WIDTH = 21
MORPH_KERNEL_HEIGHT = 11

MIN_CARD_WIDTH = 450
MAX_CARD_WIDTH = 650

MIN_CARD_HEIGHT = 90
MAX_CARD_HEIGHT = 180

# OCR.
OCR_SCALE_FACTOR = 3.0

OCR_CONFIRMATION_FRAMES = 3
OCR_CONFIRMATION_REQUIRED = 2

# Navigation/timing.
FRAME_CAPTURE_TIMEOUT = 2.0
DYNASTY_LOAD_TIMEOUT = 30.0

END_OF_LIST_DIFF_THRESHOLD = 1.5
