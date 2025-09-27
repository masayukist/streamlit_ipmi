#!/usr/bin/env python3

import streamlit as st
from pathlib import Path

from page_index import index, debug_state
from page_udhcpd import dhcp_monitor
from ClusterWattPage import ClusterWattPage
from ClusterPowerPage import ClusterPowerPage

debug_pages = False

def check_debug():
	global debug_pages
	if Path("./DEBUG").exists():
		debug_pages = True

def get_ini_files():
	curdir = Path(".")
	inifiles_name = list(curdir.glob('*.ini'))
	st.session_state["inifiles_name"] = inifiles_name
	return sorted(inifiles_name)

def get_cluster_watt_page_list():
	inifiles_name = get_ini_files()
	cluster_objlist = []
	for fname in inifiles_name:
		cluster_objlist.append(ClusterWattPage(fname))
	pmpages = []
	for p in cluster_objlist:
		p.set_urlpath_prefix("wattmon_")
		pmpages.append(st.Page(p.render, title=p.get_title(), url_path=p.get_urlpath()))
	return pmpages

def get_cluster_power_page_list():
	inifiles_name = get_ini_files()
	cluster_objlist = []
	for fname in inifiles_name:
		cluster_objlist.append(ClusterPowerPage(fname))
	pmpages = []
	for p in cluster_objlist:
		p.set_urlpath_prefix("powerman_")
		pmpages.append(st.Page(p.render, title=p.get_title(), url_path=p.get_urlpath()))
	return pmpages

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
