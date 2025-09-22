#!/usr/bin/env python3

import time
import streamlit as st

from page_index import index, debug_state
from page_ipmipower import pmindex, get_cluster_power_management_page_list, get_cluster_watt_monitor_page_list
from page_udhcpd import dhcp_monitor

def main():
	pmpages = get_cluster_power_management_page_list()
	pmpages.insert(0, st.Page(pmindex, title="Readme 1st"))
	pcpages = get_cluster_watt_monitor_page_list()

	pg = st.navigation({
		"": [
			st.Page(index, title="Dashboard Home"),
		],
		"Network": [
			st.Page(dhcp_monitor, title="DHCP leases"),
		],
		"Server Power Management": pmpages,
		"Server Watt Monitor": pcpages,
		"Etc": {
			st.Page(debug_state, title="Debug Session State")
		}
	})
	pg.run()

if __name__=="__main__":
	main()
