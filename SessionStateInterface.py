#!/usr/bin/env python3

import pandas as pd
from streamlit import session_state as ss
from datetime import datetime

class SessionStateInterface(object):
	def _tag_prefix(self):
		raise NotImplementedError

	def __contains__(self, name):
		page_tag = self._tag_prefix() + name
		return page_tag in ss

	def __getitem__(self, name):
		page_tag = self._tag_prefix() + name
		return ss[page_tag]

	def __setitem__(self, name, value):
		page_tag = self._tag_prefix() + name
		ss[page_tag] = value

	def get(self, name):
		page_tag = self._tag_prefix() + name
		if not page_tag in ss:
			return None
		return ss[page_tag]


class PageStatisticsInterface(SessionStateInterface):
	def __init__(self, cluster_watt_page_obj):
		self.obj = cluster_watt_page_obj
		if not "duration" in self:
			self["duration"] = 0.0
		if not "lastupdated" in self:
			self["lastupdated"] = "n/a"
		if not "autorefresh" in self:
			self["autorefresh"] = False

	def set_lastup(self):
		self["lastupdated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	def lastup(self):
		return self["lastupdated"]

	def set_duration(self, seconds):
		self["duration"] = seconds

	def duration(self):
		return self["duration"]

	def autoref(self):
		return self["autorefresh"]

	def set_autoref(self):
		self["autorefresh"] = True

	def unset_autoref(self):
		self["autorefresh"] = False

	def _tag_prefix(self):
		return self.obj.get_urlpath() + "_page_"


class ClusterStatisticsInterface(SessionStateInterface):
	def __init__(self, cluster_watt_page_obj):
		self.obj = cluster_watt_page_obj
		self.power_tag = self.obj.get_urlpath() + "_cluster_total_power"
		self.nhost_tag = self.obj.get_urlpath() + "_cluster_n_hosts"
		if not self.power_tag in ss:
			ss[self.power_tag] = 0
		if not self.nhost_tag in ss:
			ss[self.nhost_tag] = 0
		self.host_act_tag_prefix = self.obj.get_urlpath() + "_cluster_host_act-"
		self.host_power_tag_prefix = self.obj.get_urlpath() + "_cluster_host_power-"
		self.act_tagset_tag = self.obj.get_urlpath() + "_cluster_host_act_tags"
		self.power_tagset_tag = self.obj.get_urlpath() + "_cluster_host_power_tags"
		if not self.act_tagset_tag in ss:
			ss[self.act_tagset_tag] = set()
		if not self.power_tagset_tag in ss:
			ss[self.power_tagset_tag] = set()
		self.hosts_touched = False

	def _host_power_tag(self, host:str) -> str:
		tag = self.host_power_tag_prefix + host.replace(".", "_")
		ss[self.power_tagset_tag].add(tag)
		return tag

	def _host_act_tag(self, host:str) -> str:
		tag = self.host_act_tag_prefix + host.replace(".", "_")
		ss[self.act_tagset_tag].add(tag)
		return tag

	def set_host_power(self, host:str, power:float|str):
		tag = self._host_power_tag(host)
		ss[tag] = power

	def host_power(self, host:str) -> float|str:
		tag = self._host_power_tag(host)
		if not tag in ss:
			ss[tag] = "n/a"
		return ss[tag]

	def total_power(self) -> float:
		total = 0.0
		for tag in ss[self.power_tagset_tag]:
			if ss[tag] is None:
				continue
			try:
				total += ss[tag]
			except TypeError:
				pass
		return total

	def init_host_act(self, host:str):
		tag = self._host_act_tag(host)
		if not tag in ss:
			ss[tag] = False

	def set_host_act(self, host:str):
		self.init_host_act(host)
		tag = self._host_act_tag(host)
		if ss[tag] == False:
			self.hosts_touched = True
		ss[tag] = True

	def unset_host_act(self, host:str):
		self.init_host_act(host)
		tag = self._host_act_tag(host)
		if ss[tag] == True:
			self.hosts_touched = True
		ss[tag] = False

	def is_host_act(self, host:str) -> bool:
		self.init_host_act(host)
		tag = self._host_act_tag(host)
		return ss[tag]

	def is_host_skipped(self, host:str) -> bool:
		tag = self._host_act_tag(host)
		return not self.is_host_act(tag)
	
	def are_hosts_touched(self):
		return self.hosts_touched

	def total_nhost(self) -> int:
		nhost = 0
		for tag in ss[self.act_tagset_tag]:
			if ss[tag] == True:
				nhost += 1
		return nhost

	def clear_host_power(self):
		for tag in ss[self.power_tagset_tag]:
			ss[tag] = "n/a"

	def clear_host_act(self):
		for tag in ss[self.act_tagset_tag]:
			ss[tag] = False

	def clear_touched(self):
		self.hosts_touched = False


class DataRecorderInterface(SessionStateInterface):
	def __init__(self, cluster_watt_page_obj):
		self.obj = cluster_watt_page_obj
		self.id_tag = self.obj.get_urlpath() + "_drec_id"
		self.data_tag = self.obj.get_urlpath() + "_drec_df"
		self.since_tag = self.obj.get_urlpath() + "_drec_since"

	def get_id(self) -> int:
		if not self.id_tag in ss:
			self.reset_id()
		return ss[self.id_tag]

	def reset_id(self):
		ss[self.id_tag] = 0

	def inc_id(self, count:int=1):
		ss[self.id_tag] += count

	def get_data_df(self) -> pd.DataFrame:
		if not self.data_tag in ss:
			ss[self.data_tag] = pd.DataFrame()
		return ss[self.data_tag]

	def reset_data(self):
		ss[self.data_tag] = pd.DataFrame()
		ss[self.since_tag] = None

	def set_record_data(self, name:str, val:float):
		df = self.get_data_df()
		i = self.get_id()
		df.loc[i, name] = val
	
	def set_record_datetime(self, dtobj: datetime):
		if ss.get(self.since_tag) == None:
			ss[self.since_tag] = dtobj
		df = self.get_data_df()
		i = self.get_id()
		df.loc[i, "time:year"] = dtobj.year
		df.loc[i, "time:month"] = dtobj.month
		df.loc[i, "time:day"] = dtobj.day
		df.loc[i, "time:hour"] = dtobj.hour
		df.loc[i, "time:minute"] = dtobj.minute
		df.loc[i, "time:second"] = dtobj.second + dtobj.microsecond / 1000000

	def reset(self):
		self.reset_data()
		self.reset_id()

	def to_download(self):
		return self.get_data_df().to_csv().encode("utf-8")
	
	def get_fname(self) -> str:
		ts = ss.get(self.since_tag)
		if ts is not None:
			ts = ss[self.since_tag].strftime("%Y%m%d_%H%M%S")
		return f"records_since_{ts}.csv"
