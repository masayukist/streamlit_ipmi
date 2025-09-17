#!/usr/bin/env python3

import streamlit as st
import time

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

	try:
		auto_status = st.session_state["auto_status"]
	except KeyError:
		auto_status = False
	if auto_status:
		stat_ipmi = ipmiman.isPowerOnStatus()
		if not stat_ipmi == "Down":
			stat_ping = "Up" if pingman.is_reached() else "Down"
	else:
		stat_ipmi = "?"
		stat_ping = "?"

	with st.container(horizontal=False, vertical_alignment="center", border=True):
		with st.container(horizontal=True, vertical_alignment="center", border=False):
			st.html(f'<b>{name}</b> (<a target="_blank" rel="noopener noreferrer" href="https://{ipmi_ip}">IPMI</a>)')
		if note:
			with st.container(horizontal=True, vertical_alignment="center", border=False):
				st.markdown(f"Note: {hostdic['note']}")
		with st.container(horizontal=True, vertical_alignment="center", border=False):
			col1, col2 = st.columns(2)
			with col1:
				with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
					if st.button("Get Status", key=f"{name}-getter", disabled=auto_status):
						stat_ipmi = ipmiman.isPowerOnStatus()
						if not stat_ipmi == "Down":
							stat_ping = "Up" if pingman.is_reached() else "Down"
					status = st.text("")
					if stat_ipmi == "Up":
						disabled_btn = ["Up"]
						status_str = f"Status: Machine Up / OS {stat_ping}"
					elif stat_ipmi == "Down":
						disabled_btn = ["Sd", "Rs"]
						status_str = f"Status: Machine Down"
					else:
						disabled_btn = ["Up", "Sd", "Rs"]
						status_str = f"Status: Machine {stat_ipmi} / OS {stat_ping}"
					if disable_all:
						disabled_btn = ["Up", "Sd", "Rs"]
			with col2:
				with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", border=False):
					if not disable_all:
						if st.button('Start', key=f"{name}-start", disabled="Up" in disabled_btn):
							with st.spinner(f"Starting..."):
								ipmiman.powerUp()
								while ipmiman.isPowerOnStatus() == "Down":
									time.sleep(5)
								if auto_status:
									st.rerun()
								else:
									stat_ping = "Up" if pingman.is_reached() else "Down"
									status_str = f"Status: Machine Up / OS {stat_ping}"
						if st.button('Shutdown', key=f"{name}-shutdown", disabled="Sd" in disabled_btn):
							with st.spinner(f"Shutting down..."):
								ipmiman.softShutdown()
								while ipmiman.isPowerOnStatus() == "Up":
									time.sleep(5)
								if auto_status:
									st.rerun()
								else:
									status_str = f"Status: Machine Down"
						if st.button('Reset', key=f"{name}-reset", disabled="Rs" in disabled_btn):
							ipmiman.hardReset()
							status_str = f"Status: Hard Reset Sent"
			status.write(status_str)

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
