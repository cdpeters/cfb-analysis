from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import dxcam_cpp as dxcam

    from .controller import VirtualController


_camera: dxcam.DXCamera | None = None  # ty: ignore[unresolved-attribute]
_controller: VirtualController | None = None


def initialize_runtime() -> None:
    """Initialize process-wide hardware/control resources."""
    global _camera, _controller

    # If both are initialized, then simply return so that this function remains idempotent.
    if _camera is not None and _controller is not None:
        return

    # If only one resource is initialized, something went wrong so raise.
    if _camera is not None or _controller is not None:
        raise RuntimeError("Runtime is only partially initialized.")

    import dxcam_cpp as dxcam

    from .controller import VirtualController

    _camera = dxcam.create(  # ty: ignore[unresolved-attribute]
        device_idx=0,
        output_idx=0,
        output_color="BGRA",
    )

    _controller = VirtualController()


def get_camera() -> dxcam.DXCamera:  # ty: ignore[unresolved-attribute]
    """Return the initialized global camera."""
    if _camera is None:
        raise RuntimeError("Runtime has not been initialized.")

    return _camera


def get_controller() -> VirtualController:
    """Return the initialized virtual controller."""
    if _controller is None:
        raise RuntimeError("Runtime has not been initialized.")

    return _controller
