#!/usr/bin/env python3

import pyipmi
import pyipmi.interfaces


class IPMIManager(object):

	def __init__(self, ip, user, passwd, iftype):
		self.ip = ip
		self.user = user
		self.passwd = passwd
		self.iftype = iftype
		self.interface = None
		self.connection = None

	def connect(self):
		if self.connection:
			return
		# Supported interface_types for ipmitool are: 'lan' , 'lanplus', and 'serial-terminal'
		self.interface = pyipmi.interfaces.create_interface('ipmitool', interface_type=self.iftype)
		self.connection = pyipmi.create_connection(self.interface)

		self.connection.session.set_session_type_rmcp(self.ip, port=623)
		self.connection.session.set_auth_type_user(self.user, self.passwd)

		# self.connection.target = pyipmi.Target(
		# 	ipmb_address=0x82, routing=[(0x81,0x20,0),(0x20,0x82,7)])
		# self.connection.target = pyipmi.Target(0x82)
		# self.connection.target.set_routing([(0x81,0x20,0),(0x20,0x82,7)])

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
		except pyipmi.errors.IpmiConnectionError as e:
			return False
		return status.power_on

	def isPowerOnStatus(self):
		self.connect()
		try:
			status = self.getChassisStatus()
		except pyipmi.errors.IpmiConnectionError as e:
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

def main():
	from HostsParser import get_host_data

	hostlist = get_host_data()

	for x in sorted(hostlist, key=lambda x:x["hostname"]):
		hostname = x["hostname"]
		ipmiman = IPMIManager(x["IPMI_IP"], x["IPMI_USER"], x["IPMI_PASS"], x["IF_TYPE"])
		status = ipmiman.isPowerOnStatus()
		print(f"{hostname}\t{status}")

if __name__=="__main__":
	main()
