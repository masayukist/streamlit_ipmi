#!/usr/bin/env python3

import streamlit as st

import configparser

from HostsParser import get_host_data
from IPMIManager import IPMIManager

opening_markdown = """
- Get status first. Then, take an action, i.e., start, shutdown, or reset.
- Please refer to notes at the bottom of this page.
"""

footnote_markdown = """
### Notes
- Each action may take a few minutes. Do not hurry.
- Before shutting down, please make sure that ...
  - no other users are connected, and
  - no jobs are running.
- Resetting should be considered only as a last resort when the host does not respond.
"""

def main():
	st.title("Host Power Management")	
	with st.container(horizontal=True, vertical_alignment="center"):
		st.markdown(opening_markdown)

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
						if st.button('Start', key=i+n_hosts, disabled="Up" in disabled):
							ipmi.powerUp()
							status_str = f"Action: **:red[Start]**"
						if st.button('Shutdown', key=i+n_hosts*2, disabled="Sd" in disabled):
							ipmi.softShutdown()
							status_str = f"Action: **:blue[Shutdown]**"
						if st.button('Reset', key=i+n_hosts*3, disabled="Rs" in disabled):
							ipmi.hardReset()
							status_str = f"Action: **:red[Reset]**"
				status.write(status_str)

	st.markdown(footnote_markdown)

if __name__=="__main__":
	main()