#!/usr/bin/env python3

import sys
import pyipmi
import pyipmi.interfaces

from datetime import datetime

class IPMIManager(object):

	def __init__(self, ip, user, passwd, iftype):
		self.ip = ip
		self.user = user
		self.passwd = passwd
		self.iftype = iftype
		self.interface = None
		self.connection = None
		self.dcmi_power_reading_rsp = None
		self.dcmi_requested_at = None
		self.error = False
		self.cause = None

	def connect(self):
		if self.connection:
			return
		
		# Supported interface_types for ipmitool are: 'lan' , 'lanplus', and 'serial-terminal'
		self.interface = pyipmi.interfaces.create_interface('ipmitool', interface_type=self.iftype)
		self.connection = pyipmi.create_connection(self.interface)
		self.connection.session.set_session_type_rmcp(self.ip, port=623)
		self.connection.session.set_auth_type_user(self.user, self.passwd)
		self.connection.session.set_priv_level("ADMINISTRATOR")
		self.connection.session.establish()

	def getDeviceID(self):
		self.connect()
		return self.connection.get_device_id()

	def getChassisStatus(self):
		self.connect()
		status = self.connection.get_chassis_status()
		return status
	
	def isPowerOn(self):
		self.connect()
		try:
			status = self.getChassisStatus()
			self.error = False
			self.cause = None
		except pyipmi.errors.IpmiConnectionError as e:
			self.error = True
			self.cause = "IPMI Connection Error"
			return False
		return status.power_on

	def isError(self):
		return self.error

	def getCause(self):
		return self.cause

	def isPowerOnStatus(self):
		self.connect()
		try:
			status = self.getChassisStatus()
			self.error = False
			self.cause = None
		except pyipmi.errors.IpmiConnectionError as e:
			self.error = True
			self.cause = "IPMI Connection Error"
			return f"IPMI Connection Error"
		return "Up" if status.power_on else "Down"
	
	def powerDown(self):
		self.connect()
		return self.connection.chassis_control_power_down()

	def powerUp(self):
		self.connect()
		return self.connection.chassis_control_power_up()

	def hardReset(self):
		self.connect()
		return self.connection.chassis_control_hard_reset()

	def softShutdown(self):
		self.connect()
		return self.connection.chassis_control_soft_shutdown()

	def getDcmiPowerRead(self):
		self.connect()
		update_dcmi_power = False
		if not self.dcmi_requested_at:
			update_dcmi_power = True
		elif (datetime.now() - self.dcmi_requested_at).seconds > 10:
			update_dcmi_power = True
		elif not self.dcmi_power_reading_rsp:
			update_dcmi_power = True
		if not update_dcmi_power:
			return
		try:
			self.dcmi_power_reading_rsp = self.connection.get_power_reading(mode=1)
			self.error = False
			self.cause = None
		except pyipmi.errors.CompletionCodeError as e:
			self.error = True
			self.cause = "Completion Code Error"
			return
		except pyipmi.errors.IpmiConnectionError as e:
			self.error = True
			self.cause = "IPMI Connection Error"
			return
		except ValueError as e:
			self.error = True
			self.cause = "Value Error"
			return
		self.dcmi_requested_at = datetime.now()

	def getCurrentPower(self):
		self.getDcmiPowerRead()
		if not self.dcmi_power_reading_rsp:
			return None
		return self.dcmi_power_reading_rsp.current_power
	
	def getAveragePower(self):
		self.getDcmiPowerRead()
		if not self.dcmi_power_reading_rsp:
			return None
		return self.dcmi_power_reading_rsp.average_power

	def getMinimumPower(self):
		self.getDcmiPowerRead()
		if not self.dcmi_power_reading_rsp:
			return None
		return self.dcmi_power_reading_rsp.minimum_power

	def getMaximumPower(self):
		self.getDcmiPowerRead()
		if not self.dcmi_power_reading_rsp:
			return None
		return self.dcmi_power_reading_rsp.minimum_power

	def getPowerPeriod(self):
		self.getDcmiPowerRead()
		if not self.dcmi_power_reading_rsp:
			return None
		return self.dcmi_power_reading_rsp.period


from pathlib import Path
import configparser

def test():
	curdir = Path(".")
	inifiles_name = sorted(curdir.glob('*.ini'))

	host_list = []

	for f in inifiles_name:
		parser = configparser.ConfigParser()
		parser.read(f)

		items = ["IP", "IPMI_IP", "IPMI_USER", "IPMI_PASS", "IF_TYPE"]
		for x in parser.sections():
			if x == "Page":
				continue
			h = {}
			h["hostname"] = x
			h = dict(**h, **parser[x])
			host_list.append(h)

	sum_current_power = 0
	for host in host_list:
		name = host["hostname"]
		ip = host["ip"]
		ipmi_ip = host["ipmi_ip"]
		user = host["ipmi_user"]
		passwd = host["ipmi_pass"]
		iftype = host["if_type"]

		ipmiman = IPMIManager(ipmi_ip, user, passwd, iftype)
		cur_power = ipmiman.getCurrentPower()
		power_str = f"{cur_power:4}" if type(cur_power) == int else " n/a"
		print(f"cur: {power_str} W ({name})")
		sum_current_power += ipmiman.getCurrentPower() if ipmiman.getCurrentPower() else 0

	print(f"Total current power: {sum_current_power} W")

if __name__=="__main__":
	test()
