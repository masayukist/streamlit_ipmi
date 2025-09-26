#!/usr/bin/env python3

import time
import streamlit as st
from pathlib import Path

from page_index import index, debug_state
from page_ipmipower import get_cluster_page_list as get_cluster_power_page_list
from page_ipmiwatt import get_cluster_page_list as get_cluster_watt_page_list
from page_udhcpd import dhcp_monitor

debug_pages = False

def check_debug():
	global debug_pages
	if Path("./DEBUG").exists():
		debug_pages = True

def main():
	check_debug()

	pmpages = get_cluster_power_page_list()
	pcpages = get_cluster_watt_page_list()

	navi_structure = {
		"": [
			st.Page(index, title="Dashboard Home"),
		],
		"Network": [
			st.Page(dhcp_monitor, title="DHCP leases"),
		],
		"Server Power Management": pmpages,
		"Server Watt Monitor": pcpages
	}

	if debug_pages:
		navi_structure["Etc"] = [st.Page(debug_state, title="Debug Session State")]

	pg = st.navigation(navi_structure)
	pg.run()

if __name__=="__main__":
	main()
