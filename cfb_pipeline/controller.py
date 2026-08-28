import time
from enum import Enum, auto

import vgamepad as vg
from loguru import logger


class InputType(Enum):
    """
    Categorizes the types of virtual controller inputs.

    This enumeration ensures that each button press is routed to the
    correct underlying `vgamepad` method, as standard buttons, D-Pad
    directions, and special buttons require different API calls.

    Attributes
    ----------
    STANDARD : InputType
        Represents standard face buttons, options button, bumpers, and
        triggers.
    DPAD : InputType
        Represents directional pad inputs.
    SPECIAL : InputType
        Represents special buttons, such as the PlayStation button.
    """

    DPAD = auto()
    SPECIAL = auto()
    STANDARD = auto()

class Button(Enum):
    """
    Mappings for virtual DualShock 4 (DS4) controller inputs.

    This enumeration maps readable button names to their corresponding
    input categories and vgamepad bitmasks. The `.value` property of each
    member returns a:

    ```python
    tuple[
        InputType,
        vg.DS4_BUTTONS
        | vg.DS4_SPECIAL_BUTTONS
        | vg.DS4_DPAD_DIRECTIONS,
    ]
    ```

    Attributes
    ----------
    DPAD_UP : Button
        The D-Pad North (Up) direction.
    DPAD_DOWN : Button
        The D-Pad South (Down) direction.
    DPAD_LEFT : Button
        The D-Pad West (Left) direction.
    DPAD_RIGHT : Button
        The D-Pad East (Right) direction.
    DPAD_NEUTRAL : Button
        The state representing a released or neutral D-Pad.
    SQUARE : Button
        The Square face button.
    TRIANGLE : Button
        The Triangle face button.
    CROSS : Button
        The Cross (X) face button.
    CIRCLE : Button
        The Circle face button.
    L1 : Button
        The L1 bumper button.
    R1 : Button
        The R1 bumper button.
    L2 : Button
        The L2 trigger button.
    R2 : Button
        The R2 trigger button.
    PS : Button
        The PlayStation (PS) special menu button.
    OPTIONS : Button
        The Options menu button.
    """

    # D-Pad Directions.
    DPAD_UP = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
    DPAD_DOWN = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
    DPAD_LEFT = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST)
    DPAD_RIGHT = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST)
    DPAD_NEUTRAL = (InputType.DPAD, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)

    # Face Buttons.
    SQUARE = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
    TRIANGLE = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
    CROSS = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
    CIRCLE = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)

    # Bumpers and Triggers.
    L1 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
    R1 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
    L2 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)
    R2 = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)

    # Menu Buttons.
    PS = (InputType.SPECIAL, vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
    OPTIONS = (InputType.STANDARD, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)

class VirtualController:
    """
    A wrapper class to manage controller emulation and input sequences.

    This class encapsulates a virtual DualShock 4 (DS4) gamepad and
    provides standardized methods for executing button presses, D-pad
    movements, and special button interactions with appropriate timing
    buffers.

    Attributes
    ----------
    DEFAULT_TAP_TIME : float
        The standard duration in seconds for a button tap.
    DEFAULT_HOLD_TIME : float
        The standard duration in seconds for a button hold.
    DEFAULT_REST_TIME : float
        The standard duration in seconds to wait after an input is
        released, allowing the corresponding UI animation to finish.
    gamepad : vg.VDS4Gamepad
        The underlying virtual gamepad instance used to send inputs to the
        OS.
    """

    DEFAULT_TAP_TIME = 0.1
    DEFAULT_HOLD_TIME = 1.2
    DEFAULT_REST_TIME = 0.3

    def __init__(self) -> None:
        """Initializes the virtual gamepad."""
        logger.info("Initializing DS4 gamepad emulation...")
        self.gamepad = vg.VDS4Gamepad()

        # Allow the OS time to mount the virtual controller before sending
        # inputs.
        time.sleep(1.0)

    def _execute_action(
        self,
        button: Button,
        action_time: float,
        rest_time: float,
    ) -> None:
        """
        Executes the central sequence of pressing, updating, and releasing.

        This engine standardizes the required delays between sending a
        state change to the virtual controller and resetting it, routing
        the input to the correct vgamepad method based on the input type.

        Parameters
        ----------
        button : Button
            The specific Button enum member to be pressed and released.
        action_time : float
            The duration in seconds to wait while the button is pressed.
        rest_time : float
            The duration in seconds to wait after the button is released.
        """
        input_type, button_val = button.value

        # Press button.
        if input_type == InputType.STANDARD:
            self.gamepad.press_button(button=button_val)
        elif input_type == InputType.SPECIAL:
            self.gamepad.press_special_button(special_button=button_val)
        elif input_type == InputType.DPAD:
            self.gamepad.directional_pad(direction=button_val)

        self.gamepad.update()
        time.sleep(action_time)

        # Release button.
        if input_type == InputType.STANDARD:
            self.gamepad.release_button(button=button_val)
        elif input_type == InputType.SPECIAL:
            self.gamepad.release_special_button(special_button=button_val)
        elif input_type == InputType.DPAD:
            neutral_val = Button.DPAD_NEUTRAL.value[1]
            self.gamepad.directional_pad(direction=neutral_val)

        self.gamepad.update()
        time.sleep(rest_time)

        action_type = "tap" if action_time == self.DEFAULT_TAP_TIME else "hold"

        logger.trace(
            f"Controller input executed: {action_type} {button.name} (rest time: {rest_time}s)"
        )

    def tap(
        self,
        button: Button,
        /,
        *,
        rest_time: float | None = None,
    ) -> None:
        """
        A quick press and release of a controller button.

        Parameters
        ----------
        button : Button
            The specific button to tap.
        rest_time : float, optional
            The duration in seconds to wait after releasing the button.
            Falls back to `DEFAULT_REST_TIME` if None.
        """
        actual_rest = rest_time if rest_time is not None else self.DEFAULT_REST_TIME

        self._execute_action(
            button=button, action_time=self.DEFAULT_TAP_TIME, rest_time=actual_rest
        )

    def hold(
        self,
        button: Button,
        /,
        *,
        rest_time: float | None = None,
    ) -> None:
        """
        A prolonged press and release of a controller button.

        Parameters
        ----------
        button : Button
            The specific button to hold.
        rest_time : float, optional
            The duration in seconds to wait after releasing the button.
            Falls back to `DEFAULT_REST_TIME` if None.
        """
        actual_rest = rest_time if rest_time is not None else self.DEFAULT_REST_TIME

        self._execute_action(
            button=button, action_time=self.DEFAULT_HOLD_TIME, rest_time=actual_rest
        )
