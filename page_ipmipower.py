#!/usr/bin/env python3

import streamlit as st
import time
from datetime import datetime

opening_markdown = """
### How to
- Get status first. Then, take an action, i.e., start, shutdown, or reset.
"""

note_markdown = """
### Notes
- Each action may take a few minutes. Do not hurry.
- Before shutting down, please make sure that ...
  - no other users are connected, and
  - no jobs are running.
- Resetting should be considered only as a last resort when the host does not respond.
"""

def pmindex():
	st.title("Server Power Management")
	st.markdown(opening_markdown)

	try:
		check_default = st.session_state["auto_status"]
	except KeyError:
		check_default = False

	if st.checkbox("Get status automatically", value=check_default):
		st.session_state["auto_status"] = True
	else:
		st.session_state["auto_status"] = False

	st.markdown(note_markdown)

from IPMIManager import IPMIManager
import pings

class PingManager(object):
	def __init__(self, ip):
		self.ip = ip

	def is_reached(self):
		self.pingobj = pings.Ping()
		self.ret = self.pingobj.ping(self.ip)
		return self.ret.is_reached()

class MachineStatus(object):
	def __init__(self, ipmiman, pingman):
		self.chasis = False
		self.os = False
		self.at = None
		self.error = False
		self.cause = None
		self.ipmiman = ipmiman
		self.pingman = pingman

	def __str__(self):
		if self.at is None:
			return ""
		elif self.error:
			return f'{self.cause}'
		if not self.chasis:
			return ":blue[Machine Down]"
		if not self.os:
			return ":red[Machine Up] / :blue[OS Down]"
		return f':red[Machine Up] / :red[OS Up]'

	def set_machine_down(self):
		self.chasis = False
		self.os = False
		self.at = datetime.now()

	def set_machine_up(self):
		self.chasis = True
		self.at = datetime.now()

	def set_os_up(self):
		self.chasis = True
		self.os = True
		self.at = datetime.now()

	def set_os_down(self):
		self.os = False
		self.at = datetime.now()

	def set_error(self, cause):
		self.error = True
		self.cause = cause
		self.at = datetime.now()

	def is_machine_up(self):
		return self.chasis

	def is_os_up(self):
		return self.os

	def is_error(self):
		return self.error

	def get_timestamp_str(self):
		if self.at:
			return self.at.strftime('%Y/%m/%d %H:%M:%S')
		return None

	def get(self):
		if self.ipmiman.isPowerOn():
			self.set_machine_up()
			if self.pingman.is_reached():
				self.set_os_up()
			else:
				self.set_os_down()
		else:
			if self.ipmiman.isError():
				self.set_error(self.ipmiman.getCause())
			else:
				self.set_machine_down()

def single_host_container(hostdic):
	name = hostdic["hostname"]
	host_ip = hostdic["ip"]
	ipmi_ip = hostdic["ipmi_ip"]
	user = hostdic["ipmi_user"]
	passwd = hostdic["ipmi_pass"]
	iftype = hostdic["if_type"]
	disable_all = hostdic["disabled"]
	note = hostdic["note"]

	ipmiman = IPMIManager(ipmi_ip, user, passwd, iftype)
	pingman = PingManager(host_ip)
	machine_status = MachineStatus(ipmiman, pingman)

	try:
		auto_status = st.session_state["auto_status"]
	except KeyError:
		auto_status = False
	if auto_status:
		machine_status.get()

	with st.container(horizontal=False, vertical_alignment="center", border=True):
		with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
			st.html(f'<b>{name}</b> (<a target="_blank" rel="noopener noreferrer" href="https://{ipmi_ip}">IPMI</a>)')
			lastupdate = st.caption("")
		if note:
			with st.container(horizontal=True, vertical_alignment="center", border=False):
				st.markdown(f"Note: {hostdic['note']}")
		with st.container(horizontal=True, vertical_alignment="center", border=False):
			col1, col2 = st.columns(2)
			with col1:
				with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
					if st.button("Get Status", key=f"{name}-getter", disabled=auto_status):
						machine_status.get()
					status = st.text("")
					if machine_status.is_error() or not machine_status.get_timestamp_str():
						disabled_btn = ["Up", "Sd", "Rs"]
					elif machine_status.is_machine_up():
						disabled_btn = ["Up"]
					else:
						disabled_btn = ["Sd", "Rs"]
			with col2:
				with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", border=False):
					if not disable_all:
						if st.button('Start', key=f"{name}-start", disabled="Up" in disabled_btn):
							with st.spinner(f"Starting..."):
								ipmiman.powerUp()
								while machine_status.is_machine_up() == False:
									time.sleep(5)
									machine_status.get()
							with st.spinner(f"Waiting for OS..."):
								while machine_status.is_os_up() == False:
									time.sleep(5)
									machine_status.get()
							if auto_status:
								st.rerun()
						if st.button('Shutdown', key=f"{name}-shutdown", disabled="Sd" in disabled_btn):
							with st.spinner(f"Shutting down..."):
								ipmiman.softShutdown()
								while machine_status.is_os_up():
									time.sleep(5)
									machine_status.get()
								while machine_status.is_machine_up():
									time.sleep(5)
									machine_status.get()
							if auto_status:
								st.rerun()
						if st.button('Reset', key=f"{name}-reset", disabled="Rs" in disabled_btn):
							ipmiman.hardReset()
							machine_status.get()
			status.markdown(machine_status)
			if machine_status.get_timestamp_str():
				lastupdate.badge(f"Get status at {machine_status.get_timestamp_str()}",icon=":material/check:", color="grey")

import configparser
from pathlib import Path

class ClusterPage(object):
	def __init__(self, inifile):
		self.inifile = inifile
		self.parse_data()

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
			self.hosts_dic.append(h)

		try:
			self.title_str = parser["Page"]['title']
		except:
			self.title_str = "Somewhere"
		try:
			self.note_str = parser['Page']['note']
		except KeyError:
			self.note_str = None

	def title(self):
		return self.title_str

	def render(self):
		st.header(self.title())
		if self.note_str:
			st.markdown(f"Note: {self.note_str}")
		for d in self.hosts_dic:
			single_host_container(d)

def get_custer_page_list():
	curdir = Path(".")
	inifiles_name = sorted(curdir.glob('*.ini'))
	pages = []
	for fname in inifiles_name:
		pages.append(ClusterPage(fname))
	pmpages = []
	i = 0
	for p in pages:
		pmpages.append(st.Page(p.render, title=p.title(), url_path=f"spm{i}"))
		i += 1
	return pmpages
