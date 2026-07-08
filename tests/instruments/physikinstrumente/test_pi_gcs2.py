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

import pytest

from pymeasure.test import expected_protocol
from pymeasure.instruments.physikinstrumente import PIGCS2Base, PIC663, PIC863


def test_init():
    with expected_protocol(PIGCS2Base, []):
        pass


def test_model_defaults():
    with expected_protocol(PIC663, []) as inst:
        assert inst.name == "PI C-663 Mercury Step"
    with expected_protocol(PIC863, []) as inst:
        assert inst.name == "PI C-863 Mercury"


def test_id():
    with expected_protocol(
        PIGCS2Base,
        [("*IDN?", "Physik Instrumente,C-663,0,1.2.0.0")],
    ) as inst:
        assert inst.id == "Physik Instrumente,C-663,0,1.2.0.0"


def test_version_single_line():
    with expected_protocol(PIGCS2Base, [("VER?", "2.0.0.0")]) as inst:
        assert inst.version == "2.0.0.0"


def test_version_multi_line():
    # VER? answers with several LF-terminated lines; all must be consumed.
    with expected_protocol(
        PIGCS2Base,
        [("VER?", "FW: 1.0.0.11"), (None, "C-663, Ver. 1.06"), (None, "DIVA, Ver. 8.40")],
    ) as inst:
        assert inst.version == "FW: 1.0.0.11\nC-663, Ver. 1.06\nDIVA, Ver. 8.40"


def test_error():
    with expected_protocol(PIGCS2Base, [("ERR?", "0")]) as inst:
        assert inst.error == 0


def test_connected_stage():
    with expected_protocol(PIGCS2Base, [("CST? 1", "1=M-403.4DG")]) as inst:
        assert inst.connected_stage == "M-403.4DG"


def test_position_getter():
    with expected_protocol(PIGCS2Base, [("POS? 1", "1=10.000000")]) as inst:
        assert inst.position == pytest.approx(0.01)


def test_position_setter():
    # 0.01 m is commanded as 10 mm on the wire.
    with expected_protocol(PIGCS2Base, [("MOV 1 10", None)]) as inst:
        inst.position = 0.01


def test_target_position():
    with expected_protocol(PIGCS2Base, [("MOV? 1", "1=12.300000")]) as inst:
        assert inst.target_position == pytest.approx(0.0123)


def test_travel_limits():
    with expected_protocol(
        PIGCS2Base,
        [("TMN? 1", "1=0.000000"), ("TMX? 1", "1=25.000000")],
    ) as inst:
        assert inst.min_position == pytest.approx(0.0)
        assert inst.max_position == pytest.approx(0.025)


def test_apply_travel_limits():
    with expected_protocol(
        PIGCS2Base,
        [("TMN? 1", "1=0.000000"), ("TMX? 1", "1=25.000000"), ("MOV 1 20", None)],
    ) as inst:
        inst.apply_travel_limits()
        inst.position = 0.02  # within the queried 0..0.025 m range
        with pytest.raises(ValueError):
            inst.position = 0.03  # outside the range -> rejected before any write


def test_velocity():
    with expected_protocol(
        PIGCS2Base,
        [("VEL 1 1", None), ("VEL? 1", "1=1.000000")],
    ) as inst:
        inst.velocity = 0.001
        assert inst.velocity == pytest.approx(0.001)


def test_acceleration():
    # 0.5 m/s^2 is commanded as 500 mm/s^2; check_set_errors adds an ERR? query.
    with expected_protocol(
        PIGCS2Base,
        [("ACC 1 500", None), ("ERR?", "0"), ("ACC? 1", "1=500.000000")],
    ) as inst:
        inst.acceleration = 0.5
        assert inst.acceleration == pytest.approx(0.5)


def test_deceleration():
    with expected_protocol(
        PIGCS2Base,
        [("DEC 1 500", None), ("ERR?", "0"), ("DEC? 1", "1=500.000000")],
    ) as inst:
        inst.deceleration = 0.5
        assert inst.deceleration == pytest.approx(0.5)


def test_servo_enabled():
    with expected_protocol(
        PIGCS2Base,
        [("SVO 1 1", None), ("SVO? 1", "1=1")],
    ) as inst:
        inst.servo_enabled = True
        assert inst.servo_enabled is True


def test_enable_disable():
    with expected_protocol(
        PIGCS2Base,
        [("SVO 1 1", None), ("SVO 1 0", None)],
    ) as inst:
        inst.enable()
        inst.disable()


def test_referenced_and_on_target():
    with expected_protocol(
        PIGCS2Base,
        [("FRF? 1", "1=1"), ("ONT? 1", "1=0")],
    ) as inst:
        assert inst.referenced is True
        assert inst.on_target is False


def test_reference_mode():
    with expected_protocol(
        PIGCS2Base,
        [("RON 1 1", None), ("RON? 1", "1=1")],
    ) as inst:
        inst.reference_mode = True
        assert inst.reference_mode is True


def test_move_relative():
    with expected_protocol(PIGCS2Base, [("MVR 1 5", None)]) as inst:
        inst.move_relative(0.005)


def test_reference_moves():
    with expected_protocol(
        PIGCS2Base,
        [("FRF 1", None), ("FNL 1", None), ("FPL 1", None)],
    ) as inst:
        inst.reference()
        inst.reference_negative_limit()
        inst.reference_positive_limit()


def test_home_and_stop():
    with expected_protocol(
        PIGCS2Base,
        [("DFH 1", None), ("GOH 1", None), ("HLT 1", None), ("STP", None)],
    ) as inst:
        inst.define_home()
        inst.go_home()
        inst.halt()
        inst.stop()


def test_is_moving():
    with expected_protocol(PIGCS2Base, [(b"\x05", b"1")]) as inst:
        assert inst.is_moving() is True
    with expected_protocol(PIGCS2Base, [(b"\x05", b"0")]) as inst:
        assert inst.is_moving() is False


def test_check_errors():
    with expected_protocol(PIGCS2Base, [("ERR?", "5")]) as inst:
        assert inst.check_errors() == [
            (5, "Move attempted while servo off or axis not referenced")
        ]


def test_shutdown():
    with expected_protocol(PIGCS2Base, [("SVO 1 0", None)]) as inst:
        inst.shutdown()
        assert inst.isShutdown is True
