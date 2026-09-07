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

from pymeasure.instruments.srs.dc205 import DC205
from pymeasure.test import expected_protocol

# Every connection forces numeric token mode first.
INIT = ("TOKN 0", None)


def test_init():
    with expected_protocol(DC205, [INIT]):
        pass


def test_voltage_setter():
    with expected_protocol(DC205, [INIT, ("VOLT 0.500000", None)]) as inst:
        inst.voltage = 0.5


def test_voltage_getter():
    with expected_protocol(DC205, [INIT, ("VOLT?", "0.500000")]) as inst:
        assert inst.voltage == 0.5


def test_voltage_range_setter():
    with expected_protocol(DC205, [INIT, ("RNGE 2", None)]) as inst:
        inst.voltage_range = 100


def test_voltage_range_getter():
    with expected_protocol(DC205, [INIT, ("RNGE?", "1")]) as inst:
        assert inst.voltage_range == 10


def test_voltage_range_setter_updates_voltage_limit():
    # After selecting the 100 V range, a 50 V setpoint must be accepted.
    with expected_protocol(
        DC205, [INIT, ("RNGE 2", None), ("VOLT 50.000000", None)]
    ) as inst:
        inst.voltage_range = 100
        inst.voltage = 50


def test_voltage_out_of_range_raises():
    # In the default 1 V range, 50 V is rejected before anything is written.
    with expected_protocol(DC205, [INIT]) as inst, pytest.raises(ValueError):
        inst.voltage = 50


def test_output_enabled_setter():
    with expected_protocol(DC205, [INIT, ("SOUT 1", None)]) as inst:
        inst.output_enabled = True


def test_isolation_setter():
    with expected_protocol(DC205, [INIT, ("ISOL 1", None)]) as inst:
        inst.isolation = "float"


def test_sensing_setter():
    with expected_protocol(DC205, [INIT, ("SENS 1", None)]) as inst:
        inst.sensing = "four-wire"


def test_overloaded_getter():
    with expected_protocol(DC205, [INIT, ("OVLD?", "1")]) as inst:
        assert inst.overloaded is True


def test_scan_range_setter():
    with expected_protocol(DC205, [INIT, ("SCAR 1", None)]) as inst:
        inst.scan_range = 10


def test_scan_time_setter():
    with expected_protocol(DC205, [INIT, ("SCAT 3600.0", None)]) as inst:
        inst.scan_time = 3600


def test_scan_shape_getter():
    with expected_protocol(DC205, [INIT, ("SCAS?", "1")]) as inst:
        assert inst.scan_shape == "up-down"


def test_scan_cycle_setter():
    with expected_protocol(DC205, [INIT, ("SCAC 1", None)]) as inst:
        inst.scan_cycle = "repeat"


def test_scan_state_getter():
    with expected_protocol(DC205, [INIT, ("SCAA?", "2")]) as inst:
        assert inst.scan_state == "scanning"


def test_arm_scan():
    with expected_protocol(DC205, [INIT, ("SCAA ARMED", None)]) as inst:
        inst.arm_scan()


def test_disarm_scan():
    with expected_protocol(DC205, [INIT, ("SCAA IDLE", None)]) as inst:
        inst.disarm_scan()


def test_start_scan():
    with expected_protocol(DC205, [INIT, ("*TRG", None)]) as inst:
        inst.start_scan()


def test_last_execution_error_getter():
    with expected_protocol(DC205, [INIT, ("LEXE?", "0")]) as inst:
        assert inst.last_execution_error == 0
