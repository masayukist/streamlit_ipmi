#!/usr/bin/env python3

from pathlib import Path
import pandas
import datetime
import ipaddress
import streamlit as st

table_ts = None
table = None
n_hosts = 0

def read_dhcpleases():
	global table_ts, table, n_hosts

	table = pandas.DataFrame()
	table_ts = datetime.datetime.now()

	import subprocess
	try:
		ret = subprocess.run(['dumpleases'], capture_output=True, text=True)
	except FileNotFoundError as e:
		st.text("dumpleases command not found")
		return

	linelist = str(ret.stdout).split("\n")

	l1 = linelist[0]
	mac_begin = l1.find("Mac Address")
	ip_begin = l1.find("IP Address")
	host_begin = l1.find("Host Name")
	expire_begin = l1.find("Expires in")

	n_hosts = 0

	for line in linelist[1:-1]:
		mac = line[mac_begin:ip_begin].strip()
		ip  = ipaddress.ip_address(line[ip_begin:host_begin].strip())
		host  = line[host_begin:expire_begin].strip()
		expire = line[expire_begin:].strip()
		d = {"IP Address": ip, "Mac Address": mac, "Host name": host, "Expires in": expire}
		df_add = pandas.DataFrame([d], index=[0])
		table = pandas.concat([table, df_add], ignore_index=True)
		n_hosts += 1

	table.sort_values('IP Address', inplace=True)
	table.reset_index(inplace=True, drop=True)

def dhcp_monitor():
	read_dhcpleases()
	st.title("DHCP leases")
	with st.container(horizontal=True, vertical_alignment="center"):
		st.text(table_ts.strftime("Last updated: %Y-%m-%d %H:%M:%S"))
		if st.button("Refresh"):
			st.rerun()
	st.table(table)

class UDCHPMonitor(object):
	def __init__(self):
		pass

	def get_urlpath(self):
		return "dhcpleases"

	def get_title(self):
		return "DHCP leases"

	def render(self):
		dhcp_monitor()