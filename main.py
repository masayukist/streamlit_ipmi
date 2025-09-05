#!/usr/bin/env python3

import streamlit as st

import configparser

from HostsParser import get_host_data
from IPMIManager import IPMIManager

note_markdown = """
- Before shutting down, please make sure that ...
  - no other users are connected and
  - no jobs are running
- Resetting should be considered only as a last resort when the host does not respond.
"""

def main():
	st.title("Host Power Management")	
	with st.container(horizontal=True, vertical_alignment="center"):
		st.markdown(note_markdown)

	host_dic_list = get_host_data()
	n_hosts = len(host_dic_list)
	i = 0

	for d in host_dic_list:
		name = d["hostname"]
		host = d["IPMI_IP"]
		user = d["IPMI_USER"]
		passwd = d["IPMI_PASS"]
		iftype = d["IF_TYPE"]

		i += 1
		with st.container(horizontal=False, vertical_alignment="center", border=True):
			with st.container(horizontal=True, vertical_alignment="center", border=False):
				st.write(f"**{name}** ({host})")
				ipmi = IPMIManager(host, user, passwd, iftype)
				cur_stat = None
			with st.container(horizontal=True, vertical_alignment="center", border=False):
				col1, col2 = st.columns(2)
				with col1:
					with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
						if st.button("Get Status", key=i):
							cur_stat = ipmi.isPowerOnStatus()
						status = st.empty()
						status.write(f"Status: **{cur_stat}**")
				if cur_stat == "UP":
					disabled = ["Up"]
				elif cur_stat == "DOWN":
					disabled = ["Sd", "Rs"]
				else:
					disabled = ["Up", "Sd", "Rs"]
				action = None
				with col2:
					with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", border=False):
						if st.button('Up', key=i+n_hosts, disabled="Up" in disabled):
							ipmi.powerUp()
							action = "Up"
							status.write(f"Action: **{action}**")
						if st.button('Shutdown', key=i+n_hosts*2, disabled="Sd" in disabled):
							ipmi.softShutdown()
							action = "Shutdown"
							status.write(f"Action: **{action}**")
						if st.button('Reset', key=i+n_hosts*3, disabled="Rs" in disabled):
							ipmi.hardReset()
							action = "Shutdown"
							status.write(f"Action: **{action}**")

if __name__=="__main__":
	main()