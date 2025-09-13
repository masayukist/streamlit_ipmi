#!/usr/bin/env python3

from pathlib import Path
import pandas
import datetime

table_ts = None
table = pandas.DataFrame()
n_hosts = 0

def read_dhcpleases():
	global table_ts, table, n_hosts

	import subprocess
	ret = subprocess.run(['dumpleases'], capture_output=True, text=True)
	table_ts = datetime.datetime.now()
	linelist = str(ret.stdout).split("\n")

	l1 = linelist[0]
	mac_begin = l1.find("Mac Address")
	ip_begin = l1.find("IP Address")
	host_begin = l1.find("Host Name")
	expire_begin = l1.find("Expires in")

	n_hosts = 0

	for line in linelist[1:-1]:
		mac = line[mac_begin:ip_begin].strip()
		ip  = line[ip_begin:host_begin].strip()
		host  = line[host_begin:expire_begin].strip()
		expire = line[expire_begin:].strip()
		table.loc[ip, "Mac Address"] = mac
		table.loc[ip, "Host name"] = host
		table.loc[ip, "Expires in"] = expire

		n_hosts += 1

	table.sort_values('Expires in', inplace=True)

def dhcp_monitor():
	import streamlit as st
	read_dhcpleases()
	st.title("DHCP leases")
	with st.container(horizontal=True, vertical_alignment="center"):
		st.text(table_ts.strftime("Last updated: %Y-%m-%d %H:%M:%S"))
		if st.button("Refresh"):
			st.rerun()
	st.text(f"Number of leased hosts: {n_hosts}")
	st.table(table)

