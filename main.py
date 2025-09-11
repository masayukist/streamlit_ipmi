#!/usr/bin/env python3

import time
import streamlit as st

from IPMIManager import IPMIManager

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

def single_host_container(hostdic):
	name = hostdic["hostname"]
	host_ip = hostdic["IP"]
	ipmi_ip = hostdic["IPMI_IP"]
	user = hostdic["IPMI_USER"]
	passwd = hostdic["IPMI_PASS"]
	iftype = hostdic["IF_TYPE"]

	with st.container(horizontal=False, vertical_alignment="center", border=True):
		with st.container(horizontal=True, vertical_alignment="center", border=False):
			st.html(f'<b>{name}</b> (<a target="_blank" rel="noopener noreferrer" href="https://{ipmi_ip}">IPMI</a>)')
			ipmi = IPMIManager(ipmi_ip, user, passwd, iftype)
			try:
				auto_status = st.session_state["auto_status"]
			except KeyError:
				auto_status = False
			if auto_status:
				cur_stat = ipmi.isPowerOnStatus()
			else:
				cur_stat = None
		with st.container(horizontal=True, vertical_alignment="center", border=False):
			col1, col2 = st.columns(2)
			with col1:
				with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
					if st.button("Get Status", key=f"{name}-getter", disabled=auto_status):
						cur_stat = ipmi.isPowerOnStatus()
					status = st.empty()
					if cur_stat == "Up":
						disabled = ["Up"]
						status_str = f"Status: **:red[Up]**"
					elif cur_stat == "Down":
						disabled = ["Sd", "Rs"]
						status_str = f"Status: **:blue[Down]**"
					else:
						disabled = ["Up", "Sd", "Rs"]
						status_str = f"Status: **{cur_stat}**"
			with col2:
				with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", border=False):
					if st.button('Start', key=f"{name}-start", disabled="Up" in disabled):
						with st.spinner(f"Starting..."):
							ipmi.powerUp()
							while ipmi.isPowerOnStatus() == "Down":
								time.sleep(5)
							if auto_status:
								st.rerun()
							else:
								status_str = f"Status: **:red[Up]**"
					if st.button('Shutdown', key=f"{name}-shutdown", disabled="Sd" in disabled):
						with st.spinner(f"Shutting down..."):
							ipmi.softShutdown()
							while ipmi.isPowerOnStatus() == "Up":
								time.sleep(5)
							if auto_status:
								st.rerun()
							else:
								status_str = f"Status: **:blue[Down]**"
					if st.button('Reset', key=f"{name}-reset", disabled="Rs" in disabled):
						ipmi.hardReset()
						status_str = f"Status: **:red[Reset sent]**"
			status.write(status_str)

def index():
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
		items = ["IP", "IPMI_IP", "IPMI_USER", "IPMI_PASS", "IF_TYPE"]
		for x in parser.sections():
			if x == "Page":
				continue
			h = {}
			h["hostname"] = x
			for y in items:
				h[y] = parser[x][y]
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
	
def main():
	curdir = Path(".")
	inifiles_name = curdir.glob('*.ini')
	pages = []
	for fname in inifiles_name:
		pages.append(ClusterPage(fname))
	stlpages = []
	i = 0
	for p in pages:
		stlpages.append(st.Page(p.render, title=p.title(), url_path=f"page_{i}"))
		i += 1

	pg = st.navigation({
		"": [
			st.Page(index, title="Home"),
		],
		"Groups": stlpages
	})
	pg.run()

if __name__=="__main__":
	main()