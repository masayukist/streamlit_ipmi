#!/usr/bin/env python3

import pings

class PingManager(object):
	def __init__(self, ip):
		self.ip = ip

	def is_reached(self):
		self.pingobj = pings.Ping()
		self.ret = self.pingobj.ping(self.ip)
		return self.ret.is_reached()
