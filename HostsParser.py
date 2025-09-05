#!/usr/bin/env python3

import configparser

config = None

def read():
	global config
	config = configparser.ConfigParser()
	config.read("hosts.ini")

def get_host_data():
	if not config:
		read()
	l = []
	items = ["IPMI_IP", "IPMI_USER", "IPMI_PASS", "IF_TYPE"]
	for x in config.sections():
		h = {}
		h["hostname"] = x
		for y in items:
			h[y] = config[x][y]
		l.append(h)
	return l
