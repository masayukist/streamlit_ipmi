#!/usr/bin/env python3

import streamlit as st
import time
from datetime import datetime

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

def pmindex():
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

from IPMIManager import IPMIManager
import pings


class PingManager(object):
	def __init__(self, ip):
		self.ip = ip

	def is_reached(self):
		self.pingobj = pings.Ping()
		self.ret = self.pingobj.ping(self.ip)
		return self.ret.is_reached()

class MachineStatus(object):
	def __init__(self, ipmiman, pingman):
		self.chasis = False
		self.os = False
		self.at = None
		self.error = False
		self.cause = None
		self.ipmiman = ipmiman
		self.pingman = pingman

	def __str__(self):
		if self.at is None:
			return ""
		elif self.error:
			return f'{self.cause}'
		if not self.chasis:
			return ":blue[Machine Down]"
		if not self.os:
			return ":red[Machine Up] / :blue[OS Down]"
		return f':red[Machine Up] / :red[OS Up]'

	def set_machine_down(self):
		self.chasis = False
		self.os = False
		self.at = datetime.now()

	def set_machine_up(self):
		self.chasis = True
		self.at = datetime.now()

	def set_os_up(self):
		self.chasis = True
		self.os = True
		self.at = datetime.now()

	def set_os_down(self):
		self.os = False
		self.at = datetime.now()

	def set_error(self, cause):
		self.error = True
		self.cause = cause
		self.at = datetime.now()

	def is_machine_up(self):
		return self.chasis

	def is_os_up(self):
		return self.os

	def is_error(self):
		return self.error

	def get_timestamp_str(self):
		if self.at:
			return self.at.strftime('%Y/%m/%d %H:%M:%S')
		return None

	def get(self):
		if self.ipmiman.isPowerOn():
			self.set_machine_up()
			if self.pingman.is_reached():
				self.set_os_up()
			else:
				self.set_os_down()
		else:
			if self.ipmiman.isError():
				self.set_error(self.ipmiman.getCause())
			else:
				self.set_machine_down()

def single_host_container(hostdic):
	name = hostdic["hostname"]
	host_ip = hostdic["ip"]
	ipmi_ip = hostdic["ipmi_ip"]
	user = hostdic["ipmi_user"]
	passwd = hostdic["ipmi_pass"]
	iftype = hostdic["if_type"]
	disable_all = hostdic["disabled"]
	note = hostdic["note"]

	ipmiman = IPMIManager(ipmi_ip, user, passwd, iftype)
	pingman = PingManager(host_ip)
	machine_status = MachineStatus(ipmiman, pingman)

	try:
		auto_status = st.session_state["auto_status"]
	except KeyError:
		auto_status = False
	if auto_status:
		machine_status.get()

	with st.container(horizontal=False, vertical_alignment="center", border=True):
		with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
			st.html(f'<b>{name}</b> (<a target="_blank" rel="noopener noreferrer" href="https://{ipmi_ip}">IPMI</a>)')
			lastupdate = st.caption("")
		if note:
			with st.container(horizontal=True, vertical_alignment="center", border=False):
				st.markdown(f"Note: {hostdic['note']}")
		with st.container(horizontal=True, vertical_alignment="center", border=False):
			col1, col2 = st.columns(2)
			with col1:
				with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", border=False):
					if st.button("Get Status", key=f"{name}-getter", disabled=auto_status):
						machine_status.get()
					status = st.text("")
					if machine_status.is_error() or not machine_status.get_timestamp_str():
						disabled_btn = ["Up", "Sd", "Rs"]
					elif machine_status.is_machine_up():
						disabled_btn = ["Up"]
					else:
						disabled_btn = ["Sd", "Rs"]
			with col2:
				with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", border=False):
					if not disable_all:
						if st.button('Start', key=f"{name}-start", disabled="Up" in disabled_btn):
							with st.spinner(f"Starting..."):
								ipmiman.powerUp()
								while machine_status.is_machine_up() == False:
									time.sleep(5)
									machine_status.get()
							with st.spinner(f"Waiting for OS..."):
								while machine_status.is_os_up() == False:
									time.sleep(5)
									machine_status.get()
							if auto_status:
								st.rerun()
						if st.button('Shutdown', key=f"{name}-shutdown", disabled="Sd" in disabled_btn):
							with st.spinner(f"Shutting down..."):
								ipmiman.softShutdown()
								while machine_status.is_os_up():
									time.sleep(5)
									machine_status.get()
								while machine_status.is_machine_up():
									time.sleep(5)
									machine_status.get()
							if auto_status:
								st.rerun()
						if st.button('Reset', key=f"{name}-reset", disabled="Rs" in disabled_btn):
							ipmiman.hardReset()
							machine_status.get()
			status.markdown(machine_status)
			if machine_status.get_timestamp_str():
				lastupdate.badge(f"Get status at {machine_status.get_timestamp_str()}",icon=":material/check:", color="grey")

import numpy
import pandas as pd
import plotly.graph_objects as go

class Averager(object):
	def __init__(self, num, num_outliers, precision):
		self.hist = []
		self.hist_take = []
		self.hist_avg = []
		self.num = num
		if self.num < 3:
			self.num = 3
		self.num_outliers = num_outliers
		if self.num_outliers % 2 != 0:
			assert(True)
		self.precision = precision
		self.put_count = 0
		self.count_until_max = 0

	def put(self, val):
		self.put_count += 1
		self.count_until_max += 1
		self.hist.append(val)
		if len(self.hist) > self.num:
			self.hist = self.hist[1:]
		self.put_hist_avg(self.get())

	def put_hist_avg(self, val):
		self.hist_avg.append(val)
		if len(self.hist_avg) > self.num:
			self.hist_avg = self.hist_avg[1:]

	def get_stddev(self):
		return numpy.std(self.hist)

	def get_rawavg(self):
		if len(self.hist) == 0:
			return 0.0
		avg = round(sum(self.hist)/len(self.hist), self.precision)
		return avg
	
	def get_variance(self):
		return numpy.var(self.hist)


	def get(self):
		if len(self.hist) == 0:
			return 0.0
		if len(self.hist) <= self.num_outliers:
			avg = sum(self.hist)/len(self.hist)
			return avg
		self.hist_take = sorted(self.hist)
		edgenum = int(self.num_outliers / 2)
		self.hist_take = self.hist_take[edgenum:-edgenum]
		self.m = sum(self.hist_take)
		self.c = len(self.hist_take)
		avg = self.m/self.c
		return avg
	
	def get_str(self):
		return f"{self.get():.3f}"
	
	def stat(self):
		return f"{self.n_effective()} eff. / {self.n_samples()} smpl. / {self.n_all()} tot."

	def is_good(self):
		if self.num == len(self.hist):
			return True
		return False

	def n_all(self):
		return self.put_count

	def n_samples(self):
		return len(self.hist)
	
	def n_effective(self):
		return len(self.hist_take)

	def clear(self):
		self.hist = []
		self.hist_take = []
		self.hist_avg = []
		self.put_count = 0

	# def get_plotly_fig(self):
	# 	df = pd.DataFrame()
	# 	i = 0
	# 	for x in range(self.num):
	# 		try:
	# 			df.loc[i, "Time"] = self.hist[i]
	# 			df.loc[i, "Avg"] = self.hist_avg[i]
	# 		except IndexError:
	# 			df.loc[i, "Time"] = None
	# 			df.loc[i, "Avg"] = None
	# 		i+=1

	# 	raw_avg = self.get_rawavg()
	# 	std_dev = self.get_stddev()

	# 	fig = go.Figure()

	# 	fig.add_hrect(y0=raw_avg-std_dev, y1=raw_avg+std_dev, fillcolor="red", opacity=0.1)
	# 	fig.update_layout(yaxis_range=[raw_avg-std_dev*2, raw_avg+std_dev*2])

	# 	fig.add_trace(go.Bar(x=df.index, y=df["Time"]))
	# 	fig.add_trace(go.Scatter(x=df.index, y=df["Avg"]))

	# 	fig.update_traces(selector=0, marker=dict(color="silver"))
	# 	fig.update_traces(selector=1, line=dict(color="red"))
	# 	fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50)

	# 	fig.update_xaxes(title_text=None, visible=False)
	# 	fig.update_yaxes(title_text=None, visible=False)
	# 	fig.update_layout(showlegend=False)
	# 	return fig

	# def get_plotly_fig2(self):
	# 	df = pd.DataFrame()
	# 	i = 0

	# 	hist = sorted(self.hist)

	# 	for x in range(self.num):
	# 		try:
	# 			df.loc[i, "Time"] = hist[i]
	# 		except IndexError:
	# 			df.loc[i, "Time"] = None
	# 		i+=1

	# 	raw_avg = self.get_rawavg()
	# 	std_dev = self.get_stddev()
	# 	variance = self.get_variance()

	# 	fig = go.Figure()

	# 	fig.add_hrect(y0=raw_avg-std_dev, y1=raw_avg+std_dev, fillcolor="red", opacity=0.1)
	# 	edgenum = int(self.num_outliers / 2)
	# 	fig.add_vrect(x0=edgenum, x1=self.num-edgenum-1, fillcolor="blue", opacity=0.1)
	# 	fig.add_hline(y=self.get())
	# 	fig.add_trace(go.Scatter(x=df.index, y=df["Time"], mode="markers"))
	# 	fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50)

	# 	fig.update_xaxes(title_text=None, visible=False)
	# 	fig.update_yaxes(title_text=None, visible=False)
	# 	fig.update_layout(showlegend=False)
	# 	return fig
	
	# def set_outliers(self, n):
	# 	if n != self.num_outliers:
	# 		self.clear()
	# 	self.num_outliers = n

	# def set_samples(self, n):
	# 	if n != self.num:
	# 		self.clear()
	# 	self.num = n

	# def get_count(self):
	# 	if self.count_until_max > self.num:
	# 		self.count_until_max = self.num
	# 	return self.count_until_max
	
	# def reset_count(self):
	# 	self.count_until_max = 0

	# def progress(self):
	# 	return int(self.get_count()/self.num * 100)


import configparser
from pathlib import Path
from streamlit import session_state as ss

class ClusterPage(object):
	def __init__(self, inifile):
		self.inifile = inifile
		self.parse_data()
		self.avg_samples = 10
		self.avg_outliers = 4

	def get_urlpath(self, suffix=""):
		return Path(self.inifile).stem + suffix

	def parse_data(self):
		if not Path(self.inifile).exists():
			self.title_str = "Error"
			self.note_str = f"There is no file {self.inifile}"
			self.hosts_dic = []
			return

		parser = configparser.ConfigParser()
		parser.read(self.inifile)

		self.hosts_dic = []
		for x in parser.sections():
			if x == "Page":
				continue
			h = {}
			h["hostname"] = x
			h["ip"] = parser[x]["ip"]
			h["ipmi_ip"] = parser[x]["ipmi_ip"]
			h["ipmi_user"] = parser[x]["ipmi_user"]
			h["ipmi_pass"] = parser[x]["ipmi_pass"]
			h["if_type"] = parser[x]["if_type"]
			h["note"] = parser[x].get("note", None)
			h["disabled"] = parser[x].getboolean("disabled", False)
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

	def render_power_management(self):
		st.header(self.title())
		if self.note_str:
			st.markdown(f"Note: {self.note_str}")
		for d in self.hosts_dic:
			single_host_container(d)

	def init_session_state(self):
		if not "stat_outliers" in ss:
			ss["stat_outliers"] = 10
		if not "stat_samples" in ss:
			ss["stat_samples"] = 20

		st_o = ss["stat_outliers"]
		st_s = ss["stat_samples"]

		if not "ar_intl" in ss:
			ss["ar_intl"] = Averager(st_s, st_o, 3)
		if not "ar_dura" in ss:
			ss["ar_dura"] = Averager(st_s, st_o, 3)
		if not "ar_tgte" in ss:
			ss["ar_tgte"] = Averager(st_s, st_o, 3)
		if not "auto_refresh_toggle" in ss:
			ss["auto_refresh_toggle"] = False
		if not "auto_refresh_firstperiod" in ss:
			ss["auto_refresh_firstperiod"] = False

		if not "interval_error_correction" in ss:
			ss["interval_error_correction"] = 0.0
		if not "auto_iec_amount" in ss:
			ss["auto_iec_amount"] = 0.0
		if not "auto_iec_interval_count" in ss:
			ss['auto_iec_interval_count'] = 0

	def render_watt_monitor(self):
		duration_start_time = datetime.now()

		#tags to access session_state
		since_date_tag = self.get_urlpath("_pmon") + "_auto_since_date"
		page_tag = self.get_urlpath("_pmon") + "_lastupdate"
		clstpw_tag = self.get_urlpath("_pmon") + "_cluster_power"
		clstnh_tag = self.get_urlpath("_pmon") + "_cluster_n_hosts"

		#formats
		total_hosts_field_format = "({} machines)"
		power_field_format = "{} W"
		duration_field_format = "{} sec."
		interval_field_format = "{} sec."
		tgterror_field_format = "{} sec."

		# init
		self.init_session_state()

		# proxy
		ar_intl = ss["ar_intl"]
		ar_dura = ss["ar_dura"]
		ar_tgte = ss["ar_tgte"]

		# page's UI
		st.header(f"Watt Monitor in {self.title()}")

		with st.expander(label="Auto refresh"):
			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				auto_refresh_toggle = st.toggle("Auto refresh")

			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				ar_tgt = ss.get("ar_tgt") if ss.get("ar_tgt") else 3.0
				target_interval = st.number_input(
					"Target interval to refresh in seconds",
					value=ar_tgt, placeholder="Type a number...", min_value=1.0, step=1.0, format="%.3f")

			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				auto_correct_toggle = st.toggle("Automatic interval error correction")

			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				interval_error_correction = st.number_input(
					"Error correction to the target", value=0.0,
					min_value=-5.0, max_value=5.0, step=0.1, format="%.3f", disabled=auto_correct_toggle)

			col1, col2 = st.columns(2)
			with col1:
				with st.container(border=True, horizontal=False):
					st.write("Interval statistics")
					with st.container(horizontal=True):
						st.caption("Since")
						since_field = st.text(f"{ss.get(since_date_tag)}")
					with st.container(horizontal=True):
						st.caption("Actual duration (avg.)")
						duration_field = st.text(duration_field_format.format(ar_dura.get_str()))
					with st.container(horizontal=True):
						st.caption("Actual interval (avg.)")
						interval_field = st.text(interval_field_format.format(ar_intl.get_str()))
					with st.container(horizontal=True):
						st.caption("Actual interval error (avg.)")
						tgterror_field = st.text(tgterror_field_format.format(ar_tgte.get_str()))
			with col2:
				with st.container(border=True, horizontal=False):
					st.write("Automatic interval error correction")
					with st.container(horizontal=True):
						st.caption(f"Amount of error correction:")
						st.text(f"{ss['auto_iec_amount']:.3f} sec.")
					with st.container(horizontal=True):
						st.caption(f"Next change after:")
						st.text(f"{20 - ss['auto_iec_interval_count']} refreshes")

			# with st.container(horizontal=False, horizontal_alignment="center"):
			# 	col1, col2, col3 = st.columns(3)
			# 	with col1:
			# 		with st.container(horizontal_alignment="center", border=True):
			# 			with st.container(horizontal=True):
			# 				st.caption("Duration")
			# 				duration_field = st.text(duration_field_format.format(ar_dura.get_str()))
			# 			# with st.container(horizontal=True):
			# 			# 	st.plotly_chart(ar_dura.get_plotly_fig(), key="ar_dura_g")
			# 			# 	st.plotly_chart(ar_dura.get_plotly_fig2(), key="ar_dura_g2")
			# 			# 	st.markdown("") if not ar_dura.is_good() else st.markdown(":blue[**OK**]")
			# 	with col2:
			# 		with st.container(horizontal_alignment="center", border=True):
			# 			with st.container(horizontal=True):
			# 				st.caption("Interval")
			# 				interval_field = st.text(interval_field_format.format(ar_intl.get_str()))
			# 			# with st.container(horizontal=True):
			# 			# 	st.plotly_chart(ar_intl.get_plotly_fig(), key="ar_intl_g")
			# 			# 	st.plotly_chart(ar_intl.get_plotly_fig2(), key="ar_intl_g2")
			# 			# 	st.markdown("") if not ar_intl.is_good() else st.markdown(":blue[**OK**]")
			# 	with col3:
			# 		with st.container(horizontal_alignment="center", border=True):
			# 			with st.container(horizontal=True):
			# 				st.caption("Interval Error")
			# 				tgterror_field = st.text(tgterror_field_format.format(ar_tgte.get_str()))
			# 			# with st.container(horizontal=True):
			# 				# st.plotly_chart(ar_tgte.get_plotly_fig(), key="ar_tgte_g")
			# 				# st.plotly_chart(ar_tgte.get_plotly_fig2(), key="ar_tgte_g2")
			# 			# 	st.markdown("") if not ar_tgte.is_good() else st.markdown(":blue[**OK**]")

			# with st.container(horizontal=True, horizontal_alignment="center"):
			# 	col1, col2 = st.columns(2)
			# 	with col1:
			# 		with st.container(horizontal=True, border=True):
			# 			st.caption(f"Amount of auto error correction:")
			# 			st.text(f"{st.session_state['auto_iec_amount']:.3f} sec.")
			# 	with col2:
			# 		with st.container(horizontal=True, border=True):
			# 			st.caption(f"Next change until:")
			# 			st.text(f"{20 - st.session_state['auto_iec_interval_count']} ref.")

			# #st.html(f"<center><small>The three values are averaged by {st.session_state["stat_samples"] - st.session_state["stat_outliers"]} effectives from recent {st.session_state["stat_samples"]} samples except {st.session_state["stat_outliers"]} outliers.</small></center>")

		with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
			refresh = st.button("Manual refresh", disabled=auto_refresh_toggle)
			lastupdate_field = st.text(f"Last-updated: {ss.get(page_tag)}")
			manualdura_field = st.text(f"Duration: {ss.get("duration")} sec.")

		if ar_dura.get() is not None and float(ar_dura.get()) > target_interval:
			st.error("The auto refresh interval overcomes the target interval. Please reconsider the terget interval.")

		with st.container(horizontal=True, border=True, horizontal_alignment="distribute"):
			st.markdown(f"**Total power consumption**")
			total_hosts_field = st.text(total_hosts_field_format.format(ss.get(clstnh_tag)))
			total_power_field = st.text(power_field_format.format(ss.get(clstpw_tag)))

		host_act_check = {}
		host_power_field = {}
		for d in self.hosts_dic:
			host = d["hostname"]
			host_power_tag = "power_val-" + d["hostname"].replace(".", "_")
				
			with st.container(horizontal=True, border=True, horizontal_alignment="distribute"):
				host_act_check[host] = st.toggle("Activate", key=f"{host}-skip", label_visibility="collapsed")
				st.markdown(f"**{host}**")
				host_power_field[host] = st.text(power_field_format.format(ss.get(host_power_tag)))

		# page's logic
		ss[page_tag] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		lastupdate_field.text(f"Last-updated: {ss.get(page_tag)}")

		host_toggle_changed = False
		total_hosts = 0
		total_power = 0
		for d in self.hosts_dic:
			host = d["hostname"]
			skipped_tag = "skip-" + d["hostname"].replace(".", "_")
			host_power_tag = "power_val-" + d["hostname"].replace(".", "_")

			if host_act_check[host]:
				ipmiman = IPMIManager(d["ipmi_ip"], d["ipmi_user"], d["ipmi_pass"], d["if_type"])
				ss[host_power_tag] = ipmiman.getCurrentPower()
				if ipmiman.isError():
					ss[host_power_tag] = f"/* {ipmiman.getCause()} */"
				else:
					total_power += ss[host_power_tag]
					total_hosts += 1
				host_power_field[host].text(power_field_format.format(ss.get(host_power_tag)))
			else:
				ss[host_power_tag] = None
				host_power_field[host].text(power_field_format.format(ss.get(host_power_tag)))
			
			if skipped_tag in ss:
				if ss[skipped_tag] != host_act_check[host]:
					host_toggle_changed = True
			ss[skipped_tag] = host_act_check[host]

		ss[clstnh_tag] = total_hosts
		ss[clstpw_tag] = total_power

		total_hosts_field.text(total_hosts_field_format.format(ss.get(clstnh_tag)))
		total_power_field.text(power_field_format.format(ss.get(clstpw_tag)))

		duration_end_time = datetime.now()

		duration = duration_end_time - duration_start_time
		ss["duration"] = round(duration.total_seconds(), 3)
		manualdura_field.text(f"Duration: {ss["duration"]:.3f} sec.")

		if auto_refresh_toggle:

			init_refresh = False
			if not ss["auto_refresh_toggle"]:
				init_refresh = True
			ss["auto_refresh_toggle"] = True

			if host_toggle_changed:
				init_refresh = True

			if "target_interval" in ss:
				if ss["target_interval"] != target_interval:
					init_refresh = True
			ss["target_interval"] = target_interval

			if "interval_error_correction" in ss:
				if ss["interval_error_correction"] != interval_error_correction:
					init_refresh = True
			ss["interval_error_correction"] = interval_error_correction

			if init_refresh:
				ss[since_date_tag] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
				ss["duration_start_previous"] = None
				since_field.text(f"{ss.get(since_date_tag)}")
				ar_intl.clear()
				ar_dura.clear()
				ar_tgte.clear()
				ss["auto_iec_amount"] = 0.0
				ss["auto_iec_interval_count"] = 0
				duration_field.text(duration_field_format.format(ar_dura.get_str()))
				interval_field.text(interval_field_format.format(ar_intl.get_str()))
				tgterror_field.text(tgterror_field_format.format(ar_tgte.get_str()))

			logic_duration = duration_end_time - duration_start_time
			ar_dura.put(logic_duration.total_seconds())
			duration_field.text(duration_field_format.format(ar_dura.get_str()))

			if ss["duration_start_previous"] != None:
				logic_interval = duration_start_time - ss["duration_start_previous"]
				ar_intl.put(logic_interval.total_seconds())
				interval_field.text(interval_field_format.format(ar_intl.get_str()))
				ar_tgte.put(target_interval - logic_interval.total_seconds())
				tgterror_field.text(tgterror_field_format.format(ar_tgte.get_str()))
			ss["duration_start_previous"] = duration_start_time

			auto_correct_firstperiod = False
			if auto_correct_toggle:
				if not ss["auto_correct"]:
					auto_correct_firstperiod = True
				ss["auto_correct"] = True
			else:
				ss["auto_correct"] = False
				
			if auto_correct_firstperiod:
				ss["auto_iec_amount"] = ar_tgte.get()
				ss["auto_iec_interval_count"] = 0

			seconds = target_interval + interval_error_correction

			if ss["auto_correct"]:
				if ss["auto_iec_interval_count"] >= 20:
					ss["auto_iec_amount"] += ar_tgte.get()
					ss["auto_iec_interval_count"] = 0
				seconds += ss["auto_iec_amount"]
				ss["auto_iec_interval_count"] += 1

			time.sleep(seconds)
			st.rerun()
		else:
			ss["auto_refresh_toggle"] = False
			# ar_dura.clear()
			# ar_intl.clear()
			# ar_tgte.clear()
			# duration_field.text(duration_field_format.format(ar_dura.get_str()))
			# interval_field.text(interval_field_format.format(ar_intl.get_str()))
			# tgterror_field.text(tgterror_field_format.format(ar_tgte.get_str()))
			# ss[since_date_tag] = None

def get_ini_files():
	curdir = Path(".")
	inifiles_name = list(curdir.glob('*.ini'))
	st.session_state["inifiles_name"] = inifiles_name
	return sorted(inifiles_name)

def get_cluster_page_obj():
	if "cluster_objlist" in st.session_state:
		return st.session_state["cluster_objlist"]
	inifiles_name = get_ini_files()
	cluster_objlist = []
	for fname in inifiles_name:
		cluster_objlist.append(ClusterPage(fname))
	st.session_state["cluster_objlist"] = cluster_objlist
	return cluster_objlist

def get_cluster_power_management_page_list():
	cluster_objs = get_cluster_page_obj()
	pmpages = []
	for p in cluster_objs:
		pmpages.append(st.Page(p.render_power_management, title=p.title(), url_path=p.get_urlpath("_pman")))
	return pmpages

def get_cluster_watt_monitor_page_list():
	cluster_objs = get_cluster_page_obj()
	pmpages = []
	for p in cluster_objs:
		pmpages.append(st.Page(p.render_watt_monitor, title=p.title(), url_path=p.get_urlpath("_pmon_next")))
	return pmpages
