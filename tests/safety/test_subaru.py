#!/usr/bin/env python3
import unittest
from panda import Panda
from panda.tests.libpanda import libpanda_py
import panda.tests.safety.common as common
from panda.tests.safety.common import CANPackerPanda, MeasurementSafetyTest


MSG_SUBARU_Brake_Status     = 0x13c
MSG_SUBARU_CruiseControl    = 0x240
MSG_SUBARU_Throttle         = 0x40
MSG_SUBARU_Steering_Torque  = 0x119
MSG_SUBARU_Wheel_Speeds     = 0x13a
MSG_SUBARU_ES_LKAS          = 0x122
MSG_SUBARU_ES_LKAS_ANGLE    = 0x124
MSG_SUBARU_ES_Brake         = 0x220
MSG_SUBARU_ES_Distance      = 0x221
MSG_SUBARU_ES_Status        = 0x222
MSG_SUBARU_ES_DashStatus    = 0x321
MSG_SUBARU_ES_LKAS_State    = 0x322
MSG_SUBARU_ES_Infotainment  = 0x323

SUBARU_MAIN_BUS = 0
SUBARU_ALT_BUS  = 1
SUBARU_CAM_BUS  = 2


def lkas_tx_msgs(alt_bus, lkas_msg=MSG_SUBARU_ES_LKAS):
  return [[lkas_msg,                    SUBARU_MAIN_BUS],
          [MSG_SUBARU_ES_Distance,      alt_bus],
          [MSG_SUBARU_ES_DashStatus,    SUBARU_MAIN_BUS],
          [MSG_SUBARU_ES_LKAS_State,    SUBARU_MAIN_BUS],
          [MSG_SUBARU_ES_Infotainment,  SUBARU_MAIN_BUS]]


def fwd_blacklisted_addr(lkas_msg=MSG_SUBARU_ES_LKAS):
  return {SUBARU_CAM_BUS: [lkas_msg, MSG_SUBARU_ES_DashStatus, MSG_SUBARU_ES_LKAS_State, MSG_SUBARU_ES_Infotainment]}

class TestSubaruSafetyBase(common.PandaSafetyTest, MeasurementSafetyTest):
  FLAGS = 0
  STANDSTILL_THRESHOLD = 0 # kph
  RELAY_MALFUNCTION_ADDR = MSG_SUBARU_ES_LKAS
  RELAY_MALFUNCTION_BUS = SUBARU_MAIN_BUS
  FWD_BUS_LOOKUP = {SUBARU_MAIN_BUS: SUBARU_CAM_BUS, SUBARU_CAM_BUS: SUBARU_MAIN_BUS}
  FWD_BLACKLISTED_ADDRS = fwd_blacklisted_addr()
  MAX_RATE_UP = 50
  MAX_RATE_DOWN = 70
  MAX_TORQUE = 2047

  MAX_RT_DELTA = 940
  RT_INTERVAL = 250000

  DRIVER_TORQUE_ALLOWANCE = 60
  DRIVER_TORQUE_FACTOR = 50

  ALT_MAIN_BUS = SUBARU_MAIN_BUS
  ALT_CAM_BUS = SUBARU_CAM_BUS

  DEG_TO_CAN = -100

  def setUp(self):
    self.packer = CANPackerPanda("subaru_global_2017_generated")
    self.safety = libpanda_py.libpanda
    self.safety.set_safety_hooks(Panda.SAFETY_SUBARU, self.FLAGS)
    self.safety.init_tests()

  def _set_prev_torque(self, t):
    self.safety.set_desired_torque_last(t)
    self.safety.set_rt_torque_last(t)

  # TODO: this is unused
  def _torque_driver_msg(self, torque):
    values = {"Steer_Torque_Sensor": torque}
    return self.packer.make_can_msg_panda("Steering_Torque", 0, values)

  def _speed_msg(self, speed):
    values = {s: speed for s in ["FR", "FL", "RR", "RL"]}
    return self.packer.make_can_msg_panda("Wheel_Speeds", self.ALT_MAIN_BUS, values)

  def _angle_meas_msg(self, angle):
    values = {"Steering_Angle": angle}
    return self.packer.make_can_msg_panda("Steering_Torque", 0, values)

  def _user_brake_msg(self, brake):
    values = {"Brake": brake}
    return self.packer.make_can_msg_panda("Brake_Status", self.ALT_MAIN_BUS, values)

  def _user_gas_msg(self, gas):
    values = {"Throttle_Pedal": gas}
    return self.packer.make_can_msg_panda("Throttle", 0, values)

  def _pcm_status_msg(self, enable):
    values = {"Cruise_Activated": enable}
    return self.packer.make_can_msg_panda("CruiseControl", self.ALT_MAIN_BUS, values)


class TestSubaruTorqueSafetyBase(TestSubaruSafetyBase, common.DriverTorqueSteeringSafetyTest):
  def _torque_cmd_msg(self, torque, steer_req=1):
    values = {"LKAS_Output": torque}
    return self.packer.make_can_msg_panda("ES_LKAS", 0, values)


class TestSubaruGen1Safety(TestSubaruTorqueSafetyBase):
  FLAGS = 0
  TX_MSGS = lkas_tx_msgs(SUBARU_MAIN_BUS)


class TestSubaruGen2Safety(TestSubaruTorqueSafetyBase):
  ALT_MAIN_BUS = SUBARU_ALT_BUS
  ALT_CAM_BUS = SUBARU_ALT_BUS

  MAX_RATE_UP = 40
  MAX_RATE_DOWN = 40
  MAX_TORQUE = 1000

  FLAGS = Panda.FLAG_SUBARU_GEN2
  TX_MSGS = lkas_tx_msgs(SUBARU_ALT_BUS)


class TestSubaruAngleSafetyBase(TestSubaruSafetyBase, common.AngleSteeringSafetyTest):
  TX_MSGS = lkas_tx_msgs(SUBARU_MAIN_BUS, MSG_SUBARU_ES_LKAS_ANGLE)
  RELAY_MALFUNCTION_ADDR = MSG_SUBARU_ES_LKAS_ANGLE
  FWD_BLACKLISTED_ADDRS = fwd_blacklisted_addr(MSG_SUBARU_ES_LKAS_ANGLE)

  FLAGS = Panda.FLAG_SUBARU_LKAS_ANGLE | Panda.FLAG_SUBARU_ES_STATUS

  ANGLE_RATE_BP = [0, 5, 15]
  ANGLE_RATE_UP = [5, 0.8, 0.15]
  ANGLE_RATE_DOWN = [5, 3.5, 0.4]

  def _angle_cmd_msg(self, angle, enabled=1):
    values = {"LKAS_Output": angle, "LKAS_Request": enabled}
    return self.packer.make_can_msg_panda("ES_LKAS_ANGLE", 0, values)

  def _angle_meas_msg(self, angle):
    values = {"Steering_Angle": angle}
    return self.packer.make_can_msg_panda("Steering_Torque", 0, values)

  def _pcm_status_msg(self, enable):
    values = {"Cruise_Activated": enable}
    return self.packer.make_can_msg_panda("ES_Status", self.ALT_CAM_BUS, values)


class TestSubaruForester2022Safety(TestSubaruAngleSafetyBase):
  pass


class TestSubaruOutback2023Safety(TestSubaruAngleSafetyBase):
  ALT_MAIN_BUS = SUBARU_ALT_BUS
  ALT_CAM_BUS = SUBARU_ALT_BUS

  TX_MSGS = lkas_tx_msgs(SUBARU_ALT_BUS, MSG_SUBARU_ES_LKAS_ANGLE)

  FLAGS = Panda.FLAG_SUBARU_GEN2 | Panda.FLAG_SUBARU_LKAS_ANGLE | Panda.FLAG_SUBARU_ES_STATUS

  
if __name__ == "__main__":
  unittest.main()