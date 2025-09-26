#!/usr/bin/env python3
import streamlit as st
from streamlit import session_state as ss
from pathlib import Path
from datetime import datetime
import time

import numpy
import pandas as pd

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
		self.hist_take = self.hist_take[edgenum:-(edgenum+1)]
		self.c = len(self.hist_take)
		if self.c == 0:
			return 0.0
		self.m = sum(self.hist_take)
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

from page_ipmipower import ClusterBasePage, IPMIManager
from SessionStateInterface import (
	DataRecorderSessionStateInterface,
	ClusterStatisticsSessionStateInterface,
	PageStatisticsSessionStateInterface
)

class PIDController(object):
	def __init__(self, kp:float, ki:float, kd:float, hist_limit=10):
		self.kp = kp
		self.ki = ki
		self.kd = kd

		self.error_hist_tag = "PIDCorrector_error_hist"
		if not "PIDCorrector_error_hist" in ss:
			ss[self.error_hist_tag] = []
		self.error_hist = ss[self.error_hist_tag]
		self.hist_limit = hist_limit

	def put_data(self, goal:float, current:float) -> float:
		error = goal - current
		self.put_error(error)

	def get_correction(self) -> float:
		m = self.kp * self.error_latest() + self.ki * self.error_avg() + self.kd * self.error_diff()
		return m

	def put_error(self, error:float):
		self.error_hist.append(error)
		if len(self.error_hist) > self.hist_limit:
			diff = len(self.error_hist) - self.hist_limit
			self.error_hist = self.error_hist[diff:]
		ss[self.error_hist_tag] = self.error_hist

	def error_latest(self) -> float:
		try:
			return self.error_hist[-1]
		except IndexError:
			return 0.0

	def error_avg(self) -> float:
		try:
			return self.error_sum() / len(self.error_hist)
		except ValueError:
			return 0.0

	def error_sum(self) -> float:
		return sum(self.error_hist)

	def error_diff(self) -> float:
		try:
			return self.error_hist[-1] - self.error_hist[-2]
		except IndexError:
			return 0.0

	def clear(self):
		ss[self.error_hist_tag] = []
		ss.error_hist = ss[self.error_hist_tag]

class ClusterWattPage(ClusterBasePage):

	def get_title(self):
		return self.title_str

	def render(self):
		self.duration_start_time = datetime.now()

		self.init_session_state()
		self.ui_render()
		self.exec_logic()

	def init_session_state(self):
		if not hasattr(self, "drec"):
			self.drec = DataRecorderSessionStateInterface(self)
		if not hasattr(self, "clstat"):
			self.clstat = ClusterStatisticsSessionStateInterface(self)
		if not hasattr(self, "pagestat"):
			self.pagestat = PageStatisticsSessionStateInterface(self)

		pss = PageStatisticsSessionStateInterface(self)

		if not "stat_outliers" in pss:
			pss["stat_outliers"] = 0
		if not "stat_samples" in pss:
			pss["stat_samples"] = 10

		st_o = pss["stat_outliers"]
		st_s = pss["stat_samples"]

		if not "ar_intl" in pss:
			pss["ar_intl"] = Averager(st_s, st_o, 3)
		if not "ar_dura" in pss:
			pss["ar_dura"] = Averager(st_s, st_o, 3)
		if not "ar_tgte" in pss:
			pss["ar_tgte"] = Averager(st_s, st_o, 3)

		if not "target_interval" in pss:
			pss["target_interval"] = 0.0
		if not "interval_error_correction" in pss:
			pss["interval_error_correction"] = 0.0

		if not "auto_iec_amount" in pss:
			pss["auto_iec_amount"] = 0.0

		#formats
		self.total_hosts_field_format = "({} machines)"
		self.power_field_format = "{} W"
		self.duration_field_format = "{} sec."
		self.interval_field_format = "{} sec."
		self.tgterror_field_format = "{} sec."

		# proxy
		self.ar_intl = pss["ar_intl"]
		self.ar_dura = pss["ar_dura"]
		self.ar_tgte = pss["ar_tgte"]

		self.since_date_tag = self.get_urlpath() + "_auto_since_date"

	def ui_render(self):
		pss = PageStatisticsSessionStateInterface(self)

		# page's UI
		st.header(f"Watt Monitor in {self.get_title()}")

		with st.expander(label="Auto refresh"):
			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				self.auto_refresh_toggle = st.toggle("Auto refresh")

			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				ar_tgt = pss.get("ar_tgt") if pss.get("ar_tgt") else 1.0
				self.target_interval = st.number_input(
					"Interval of auto refresh in seconds (target value)",
					value=ar_tgt, placeholder="Type a number...", min_value=1.0, step=1.0, format="%.3f")

			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				self.auto_correct_toggle = st.toggle("Automatic interval error correction", disabled=not self.auto_refresh_toggle)

			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				disabled = self.auto_correct_toggle or not self.auto_refresh_toggle
				self.interval_error_correction = st.number_input(
					"Amount of manual error correction to the target", value=0.0,
					min_value=-5.0, max_value=5.0, step=0.1, format="%.3f", disabled=disabled)

			col1, col2 = st.columns(2)
			with col1:
				with st.container(border=True, horizontal=False):
					st.write("Statistics of auto refresh")
					with st.container(horizontal=True):
						st.caption("Since")
						self.since_field = st.text(f"{ss.get(self.since_date_tag)}")
					with st.container(horizontal=True):
						st.caption("Actual duration (avg.)")
						self.duration_field = st.text(self.duration_field_format.format(self.ar_dura.get_str()))
					with st.container(horizontal=True):
						st.caption("Actual interval (avg.)")
						self.interval_field = st.text(self.interval_field_format.format(self.ar_intl.get_str()))
			with col2:
				with st.container(border=True, horizontal=False):
					st.write("Automatic interval error correction")
					with st.container(horizontal=True):
						st.caption("Actual interval error (avg.)")
						self.tgterror_field = st.text(self.tgterror_field_format.format(self.ar_tgte.get_str()))
					with st.container(horizontal=True):
						st.caption(f"Amount of auto error correction")
						st.text(f"{pss['auto_iec_amount']:.3f} sec.")

		with st.expander(label="Recording"):
			with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
				with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
					self.record_data = st.toggle("Record data")
					st.text(f"Records: {self.drec.get_id()}")
					disabled = True if self.drec.get_id() == 0 else False
				st.download_button(
					label="Download", data=self.drec.to_download(), file_name=self.drec.get_fname(),
					mime="text/csv", icon=":material/download:", disabled=disabled)
				self.reset_recorded_data = st.button("Reset", disabled=disabled, icon=":material/delete:")

		with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left"):
			refresh = st.button("Manual refresh", disabled=self.auto_refresh_toggle)
			self.lastupdate_field = st.text(f"Last-updated: {pss.lastup()}")
			self.manualdura_field = st.text(f"Duration: {pss.duration():.3f} sec.")

		if self.auto_refresh_toggle and self.ar_dura.get() is not None and float(self.ar_dura.get()) > self.target_interval:
			st.error("The actual duration overcomes the target interval. Please consider increasing the target interval.")
		else:
			st.empty()

		with st.container(horizontal=True, border=True, horizontal_alignment="distribute"):
			st.markdown(f"**Total power consumption**")
			self.total_hosts_field = st.text(self.total_hosts_field_format.format(self.clstat.total_nhost()))
			self.total_power_field = st.text(self.power_field_format.format(self.clstat.total_power()))

		self.host_act_check = {}
		self.host_power_field = {}
		for d in self.hosts_dic:
			host = d["hostname"]

			with st.container(horizontal=True, border=True, horizontal_alignment="distribute"):
				self.host_act_check[host] = st.toggle("Activate", key=f"{host}-skip", label_visibility="collapsed")
				st.markdown(f"**{host}**")
				self.host_power_field[host] = st.text(self.power_field_format.format(self.clstat.host_power(host)))

	def finish_duration_measurement(self):
		duration_end_time = datetime.now()
		self.duration = duration_end_time - self.duration_start_time
		self.ar_dura.put(self.duration.total_seconds())
		self.duration_field.text(self.duration_field_format.format(self.ar_dura.get_str()))
		self.pagestat.set_duration(self.duration.total_seconds())
		self.manualdura_field.text(f"Duration: {self.pagestat.duration():.3f} sec.")

	def exec_logic(self):
		pss = PageStatisticsSessionStateInterface(self)

		if self.reset_recorded_data:
			self.drec.reset()
			st.rerun()

		pss.set_lastup()
		self.lastupdate_field.text(f"Last-updated: {pss.lastup()}")

		self.clstat.clear_touched()

		for d in self.hosts_dic:
			host = d["hostname"]

			if self.host_act_check[host]:
				self.clstat.set_host_act(host)
				ipmiman = IPMIManager(d["ipmi_ip"], d["ipmi_user"], d["ipmi_pass"], d["if_type"])
				power = ipmiman.getCurrentPower()
				if ipmiman.isError():
					power = f"/* {ipmiman.getCause()} */"
					self.clstat.set_host_power(host, power)
				else:
					self.clstat.set_host_power(host, power)
				if self.record_data:
					self.drec.set_record_data("power:"+host, power)
			else:
				self.clstat.unset_host_act(host)
				power = "n/a"
				self.clstat.set_host_power(host, power)

			self.host_power_field[host].text(self.power_field_format.format(power))

		if self.record_data:
			t = datetime.now()
			self.drec.set_record_data("power:total", self.clstat.total_power())
			self.drec.set_record_datetime(t)
			self.drec.inc_id()

		self.total_hosts_field.text(self.total_hosts_field_format.format(self.clstat.total_nhost()))
		self.total_power_field.text(self.power_field_format.format(self.clstat.total_power()))

		if not self.auto_refresh_toggle:
			pss.unset_autoref()
			self.finish_duration_measurement()
		else:
			init_refresh = False
			if not pss.autoref():
				init_refresh = True
			pss.set_autoref()

			if pss["target_interval"] != self.target_interval:
				init_refresh = True
			if pss["interval_error_correction"] != self.interval_error_correction:
				init_refresh = True
			if self.clstat.are_hosts_touched():
				init_refresh = True

			pss["target_interval"] = self.target_interval
			pss["interval_error_correction"] = self.interval_error_correction

			if not hasattr(self, "pid"):
				self.pidcon = PIDController(0.1, 0.05, 0.15)

			if init_refresh:
				pss[self.since_date_tag] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
				pss["duration_start_previous"] = None
				self.since_field.text(f"{ss.get(self.since_date_tag)}")
				self.ar_intl.clear()
				self.ar_dura.clear()
				self.ar_tgte.clear()
				self.duration_field.text(self.duration_field_format.format(self.ar_dura.get_str()))
				self.interval_field.text(self.interval_field_format.format(self.ar_intl.get_str()))
				self.tgterror_field.text(self.tgterror_field_format.format(self.ar_tgte.get_str()))

			init_auto_correct = False
			if self.auto_correct_toggle:
				if not pss["auto_correct"]:
					init_auto_correct = True
				pss["auto_correct"] = True
			else:
				pss["auto_correct"] = False

			if init_auto_correct:
				self.pidcon.clear()
				pss["auto_iec_amount"] = 0.0

			if pss["duration_start_previous"] != None:
				self.interval = self.duration_start_time - pss["duration_start_previous"]
				self.ar_intl.put(self.interval.total_seconds())
				self.interval_field.text(self.interval_field_format.format(self.ar_intl.get_str()))
				self.ar_tgte.put(self.interval.total_seconds() - self.target_interval)
				self.tgterror_field.text(self.tgterror_field_format.format(self.ar_tgte.get_str()))
				self.pidcon.put_data(self.target_interval, self.interval.total_seconds())
			pss["duration_start_previous"] = self.duration_start_time

				
			seconds = self.target_interval + self.interval_error_correction

			if pss["auto_correct"]:
				pss["auto_iec_amount"] += self.pidcon.get_correction()
				seconds += pss["auto_iec_amount"]
				print(f"{pss["auto_iec_amount"]:.4f}, {self.pidcon.get_correction():+.4f}")

			if seconds < 0:
				seconds = 0
				pss["auto_iec_amount"] = 0.0
				pss["interval_error_correction"] = 0.0

			self.finish_duration_measurement()

			time.sleep(seconds)
			st.rerun()

def get_ini_files():
	curdir = Path(".")
	inifiles_name = list(curdir.glob('*.ini'))
	st.session_state["inifiles_name"] = inifiles_name
	return sorted(inifiles_name)

def get_cluster_page_obj():
	inifiles_name = get_ini_files()
	cluster_objlist = []
	for fname in inifiles_name:
		cluster_objlist.append(ClusterWattPage(fname))
	return cluster_objlist

def get_cluster_page_list():
	cluster_objs = get_cluster_page_obj()
	pmpages = []
	for p in cluster_objs:
		p.set_urlpath_prefix("wattmon_")
		pmpages.append(st.Page(p.render, title=p.get_title(), url_path=p.get_urlpath()))
	return pmpages
