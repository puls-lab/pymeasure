#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2026 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
from time import sleep, time

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set, strict_range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Conversion between the SI unit of the Python API (meters) and the controller's
# physical unit. For the supported linear stages this physical unit is millimeters.
MM_PER_M = 1e3

# Common PI GCS 2.0 error codes (subset). See the PI GCS 2.0 command reference for
# the full list.
GCS_ERRORS = {
    0: "No error",
    1: "Parameter syntax error",
    2: "Unknown command",
    3: "Command length out of limits or command buffer overrun",
    4: "Error while scanning",
    5: "Move attempted while servo off or axis not referenced",
    7: "Position out of limits",
    8: "Velocity out of limits",
    10: "Controller was stopped by command",
    15: "Invalid axis identifier",
    17: "Parameter out of range",
    20: "Macro not found",
    23: "Illegal axis",
    54: "Unknown parameter",
    200: "No stage connected to axis",
}


def _value(reply):
    """Return the value of a ``<axis>=<value>`` GCS reply as a string.

    GCS answers axis-addressed queries in the form ``1=12.34``; this strips the
    ``<axis>=`` prefix and returns ``"12.34"``.
    """
    return str(reply).split("=")[-1]


class PIGCS2Base(Instrument):
    """Base class for Physik Instrumente controllers speaking the PI General
    Command Set 2.0 (GCS 2.0) over a serial (RS-232/USB) connection.

    The class targets single-axis Mercury™ class controllers with GCS firmware
    (e.g. C-663, C-863). All commands address axis ``1``, which is the default
    identifier of a single controller; a differently configured or daisy-chained
    controller can be queried with ``SAI?``/``TVI?``. Positions, velocities and
    accelerations are exposed in SI units (meters, m/s, m/s²); internally they are
    converted to the controller's physical unit, which is assumed to be millimeters
    (as for the supported linear stages).

    Absolute positioning requires the axis to be referenced first (see
    :meth:`reference`) and, for closed-loop controllers, the servo to be enabled
    (see :attr:`servo_enabled`).

    :param adapter: pyvisa resource name or adapter instance.
    :param name: Instrument name.
    :param baud_rate: Serial baud rate (controller-configurable).
    """

    def __init__(self, adapter, name="PI GCS 2.0 Controller", baud_rate=115200, **kwargs):
        super().__init__(
            adapter,
            name,
            write_termination="\n",
            read_termination="\n",
            timeout=5000,
            baud_rate=baud_rate,
            **kwargs,
        )

    @property
    def id(self):
        """Get the identification string of the controller (``*IDN?``)."""
        return self.ask("*IDN?").strip()

    @property
    def version(self):
        """Get the firmware version reported by ``VER?`` (str).

        ``VER?`` answers with one or several LF-terminated lines (one per firmware
        component); all of them are read - and thus removed from the input buffer -
        and joined into a single string.
        """
        self.write("VER?")
        lines = []
        while True:
            try:
                lines.append(self.read())
            except Exception:
                # No more data (read timeout on hardware / no pair left in tests):
                # the whole multi-line reply has been consumed.
                break
        return "\n".join(lines)

    error = Instrument.measurement(
        "ERR?",
        """Get the current error code and clear it, ``0`` meaning no error (int).""",
        cast=int,
    )

    connected_stage = Instrument.measurement(
        "CST? 1",
        """Get the name of the stage connected to the axis, ``NOSTAGE`` if none (str).""",
        preprocess_reply=_value,
        cast=str,
    )

    # Motion and position -----------------------------------------------------
    position = Instrument.control(
        "POS? 1", "MOV 1 %.9g",
        """Control the axis position, in meters (float).

        Setting commands an absolute move to the target position; getting returns the
        current actual position. Requires the axis to be referenced.""",
        validator=strict_range,
        values=[-1, 1],
        dynamic=True,
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
        set_process=lambda v: v * MM_PER_M,
    )

    target_position = Instrument.measurement(
        "MOV? 1",
        """Get the commanded target position of the axis, in meters (float).""",
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
    )

    min_position = Instrument.measurement(
        "TMN? 1",
        """Get the minimum commandable position of the axis, in meters (float).""",
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
    )

    max_position = Instrument.measurement(
        "TMX? 1",
        """Get the maximum commandable position of the axis, in meters (float).""",
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
    )

    home_position = Instrument.measurement(
        "DFH? 1",
        """Get the defined home position of the axis, in meters (float).""",
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
    )

    on_target = Instrument.measurement(
        "ONT? 1",
        """Get whether the axis has reached its target position (bool).""",
        preprocess_reply=_value,
        get_process=lambda v: bool(int(v)),
    )

    velocity = Instrument.control(
        "VEL? 1", "VEL 1 %.9g",
        """Control the closed-loop velocity of the axis, in m/s (float).""",
        validator=strict_range,
        values=[0, 1],
        dynamic=True,
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
        set_process=lambda v: v * MM_PER_M,
    )

    acceleration = Instrument.control(
        "ACC? 1", "ACC 1 %.9g",
        """Control the acceleration of the axis, in m/s² (float).

        Not every controller supports acceleration; on unsupported ones setting it
        logs the resulting GCS error (``check_set_errors``).""",
        validator=strict_range,
        values=[0, 100],
        dynamic=True,
        check_set_errors=True,
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
        set_process=lambda v: v * MM_PER_M,
    )

    deceleration = Instrument.control(
        "DEC? 1", "DEC 1 %.9g",
        """Control the deceleration of the axis, in m/s² (float).

        Not every controller supports deceleration; on unsupported ones setting it
        logs the resulting GCS error (``check_set_errors``).""",
        validator=strict_range,
        values=[0, 100],
        dynamic=True,
        check_set_errors=True,
        preprocess_reply=_value,
        get_process=lambda v: v / MM_PER_M,
        set_process=lambda v: v * MM_PER_M,
    )

    # Servo and referencing ---------------------------------------------------
    servo_enabled = Instrument.control(
        "SVO? 1", "SVO 1 %d",
        """Control whether the servo (closed-loop control) of the axis is enabled (bool).""",
        validator=strict_discrete_set,
        values=[True, False],
        preprocess_reply=_value,
        get_process=lambda v: bool(int(v)),
        set_process=lambda v: int(v),
    )

    referenced = Instrument.measurement(
        "FRF? 1",
        """Get whether the axis has been successfully referenced (bool).""",
        preprocess_reply=_value,
        get_process=lambda v: bool(int(v)),
    )

    reference_mode = Instrument.control(
        "RON? 1", "RON 1 %d",
        """Control the reference mode of the axis (bool).

        If True, a reference move is required before absolute targets can be
        commanded; if False, positions may be set manually.""",
        validator=strict_discrete_set,
        values=[True, False],
        preprocess_reply=_value,
        get_process=lambda v: bool(int(v)),
        set_process=lambda v: int(v),
    )

    # Methods -----------------------------------------------------------------
    def enable(self):
        """Enable the servo (closed-loop control) of the axis."""
        self.servo_enabled = True

    def disable(self):
        """Disable the servo (closed-loop control) of the axis."""
        self.servo_enabled = False

    def move_relative(self, distance):
        """Command a relative move of the axis by ``distance`` meters."""
        self.write("MVR 1 %.9g" % (distance * MM_PER_M))

    def reference(self):
        """Start a reference move to the reference switch (``FRF``).

        Use :meth:`wait_for_move` to block until it has finished and :attr:`referenced`
        to check success.
        """
        self.write("FRF 1")

    def reference_negative_limit(self):
        """Start a reference move to the negative limit switch (``FNL``)."""
        self.write("FNL 1")

    def reference_positive_limit(self):
        """Start a reference move to the positive limit switch (``FPL``)."""
        self.write("FPL 1")

    def define_home(self):
        """Define the current position as the home position (``DFH``)."""
        self.write("DFH 1")

    def go_home(self):
        """Move the axis to the defined home position (``GOH``)."""
        self.write("GOH 1")

    def halt(self):
        """Halt the axis smoothly with deceleration (``HLT``)."""
        self.write("HLT 1")

    def stop(self):
        """Abruptly stop all axes (``STP``)."""
        self.write("STP")

    def is_moving(self):
        """Return whether the axis is currently moving.

        Uses the binary motion-status query (single character ``0x05``), which works
        for both open- and closed-loop controllers. The reply is the decimal sum of
        the per-axis "moving" bit codes, so any non-zero value means motion.
        """
        self.write_bytes(b"\x05")
        return int(self.read().strip()) != 0

    def wait_for_move(self, interval=0.05, timeout=60):
        """Block until the axis has stopped moving.

        :param interval: Polling interval in seconds.
        :param timeout: Maximum time to wait in seconds before raising ``TimeoutError``.
        """
        start = time()
        while self.is_moving():
            if time() - start > timeout:
                raise TimeoutError("Timed out waiting for the axis to stop moving.")
            sleep(interval)

    def apply_travel_limits(self):
        """Query the stage travel range (``TMN?``/``TMX?``) and use it as the
        allowed range of :attr:`position`."""
        self.position_values = [self.min_position, self.max_position]

    def check_errors(self):
        """Read the controller error and log it.

        :return: List of ``(code, message)`` tuples; empty if there was no error.
        """
        code = self.error
        if code:
            message = GCS_ERRORS.get(code, "Unknown error")
            log.error("%s reported error %d: %s", self.name, code, message)
            return [(code, message)]
        return []

    def check_set_errors(self):
        """Check for errors after setting a property (see :meth:`check_errors`)."""
        return self.check_errors()

    def shutdown(self):
        """Disable the servo and close the connection."""
        self.disable()
        super().shutdown()


class PIC663(PIGCS2Base):
    """Physik Instrumente C-663 Mercury™ Step single-axis stepper motor controller
    (GCS 2.0).

    .. code-block:: python

        stage = PIC663("ASRL3::INSTR")
        stage.reference()
        stage.wait_for_move()
        stage.position = 0.01   # move to 10 mm
    """

    def __init__(self, adapter, name="PI C-663 Mercury Step", baud_rate=115200, **kwargs):
        super().__init__(adapter, name, baud_rate=baud_rate, **kwargs)


class PIC863(PIGCS2Base):
    """Physik Instrumente C-863 Mercury™ single-axis DC motor controller (GCS 2.0).

    .. code-block:: python

        stage = PIC863("ASRL4::INSTR")
        stage.enable()          # DC servo controller: enable the servo loop
        stage.reference()
        stage.wait_for_move()
        stage.position = 0.01   # move to 10 mm
    """

    def __init__(self, adapter, name="PI C-863 Mercury", baud_rate=38400, **kwargs):
        super().__init__(adapter, name, baud_rate=baud_rate, **kwargs)
