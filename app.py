#!/usr/bin/env python3

import time
import streamlit as st

from page_index import index
from page_ipmipower import pmindex, get_custer_page_list
from page_udhcpd import dhcp_monitor

def main():
	pmpages = get_custer_page_list()
	pmpages.insert(0, st.Page(pmindex, title="Readme 1st"))

	pg = st.navigation({
		"": [
			st.Page(index, title="Dashboard Home"),
		],
		"Network": [
			st.Page(dhcp_monitor, title="DHCP leases"),
		],
		"Server Power Management": pmpages 
	})
	pg.run()

if __name__=="__main__":
	main()
