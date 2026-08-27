# Template Matching Errors.
class TemplateFileNotFoundError(Exception):
    """Raised when the image template file is not found."""

class TemplateMatchTimeoutError(Exception):
    """Raised when the timeout is exceeded during polling for a template match."""


# Chiaki/Remote Play Errors.
class ChiakiExecutableNotFoundError(Exception):
    """Raised when the `chiaki-ng` executable is not found."""

class ChiakiFullscreenError(Exception):
    """Raised when forcing chiaki to fullscreen fails."""

class ChiakiWindowNotFoundError(Exception):
    """Raised when the local chiaki-ng window fails to appear or become visible."""


# PS5 UI Errors.
class CFBGameTitleNotFoundError(Exception):
    """Raised when the CFB game title is not found on the PS5 home screen."""

class PS5SettingsIconNotFoundError(Exception):
    """Raised when the PS5 Settings Icon is not found on the PS5 home screen."""


# CFB Main Menu UI Errors.
class EAConnectionTimeoutError(Exception):
    """Raised when reconnection to EA servers exceeds its allowed timeout."""

class MainMenuPollingTimeoutError(Exception):
    """Raised when main-menu polling exceeds its overall deadline."""


# Load Dynasty UI Errors.
class DynastyNotFoundError(Exception):
    """Raised when the requested dynasty is not present in the save list."""

class DynastyOCRReadError(Exception):
    """Raised when OCR cannot produce a stable dynasty-name reading."""

class DynastySelectionNotFoundError(Exception):
    """Raised when the highlighted dynasty card cannot be located."""


# Frame Capture Errors.
class FrameCaptureTimeoutError(Exception):
    """Raised when a usable frame cannot be captured within the timeout."""
