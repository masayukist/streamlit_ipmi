#!/usr/bin/env python3

import configparser
from pathlib import Path


class StreamlitBasePage(object):
	def __init__(self):
		self.icon = None

	def get_urlpath(self):
		raise NotImplementedError

	def get_title(self):
		raise NotImplementedError

	def render(self):
		raise NotImplementedError

	def set_icon(self, s):
		self.icon = s

	def get_icon(self):
		return self.icon


class ClusterBasePage(StreamlitBasePage):
	def __init__(self, inifile):
		self.inifile = inifile
		self.parse_data()
		self.avg_samples = 10
		self.avg_outliers = 4
		self.urlpath_prefix = ""
		self.urlpath_suffix = ""

	def set_urlpath_prefix(self, s):
		self.urlpath_prefix = s

	def set_urlpath_suffix(self, s):
		self.urlpath_suffix = s

	def get_urlpath(self):
		return self.urlpath_prefix + Path(self.inifile).stem + self.urlpath_suffix

	def parse_data(self):
		if not Path(self.inifile).exists():
			self.title_str = "Error"
			self.note_str = f"There is no file {self.inifile}"
			self.hosts_dic = []
			return

		parser = configparser.ConfigParser()
		parser.read(self.inifile)

		self.hosts_dic = []
		for x in parser.sections():
			if x == "Page":
				continue
			h = {}
			h["hostname"] = x
			h["ip"] = parser[x]["ip"]
			h["ipmi_ip"] = parser[x]["ipmi_ip"]
			h["ipmi_user"] = parser[x]["ipmi_user"]
			h["ipmi_pass"] = parser[x]["ipmi_pass"]
			h["if_type"] = parser[x]["if_type"]
			h["note"] = parser[x].get("note", None)
			h["disabled"] = parser[x].getboolean("disabled", False)
			h["power_method"] = parser[x].get("power_method", "dcmi")
			self.hosts_dic.append(h)

		try:
			self.title_str = parser["Page"]['title']
		except:
			self.title_str = "Somewhere"
		try:
			self.note_str = parser['Page']['note']
		except KeyError:
			self.note_str = None

	def get_hosts_dic(self):
		return self.hosts_dic

	def render(self):
		raise NotImplementedError

	def get_title(self):
		raise NotImplementedError
