#!/usr/bin/env python3

from streamlit import session_state as ss

class PIDController(object):
	def __init__(self, kp:float, ki:float, kd:float, hist_limit=10):
		self.kp = kp
		self.ki = ki
		self.kd = kd

		self.error_hist_tag = "PIDCorrector_error_hist"
		if not "PIDCorrector_error_hist" in ss:
			ss[self.error_hist_tag] = []
		self.error_hist = ss[self.error_hist_tag]
		self.hist = []
		self.hist_limit = hist_limit

	def put_data(self, goal:float, current:float) -> float:
		error = goal - current
		self.put_error(error)

	def get_correction(self) -> float:
		p = self.kp * self.error_latest()
		i = self.ki * self.error_avg()
		d = self.kd * self.error_diff()
		m = p + i + d
		return m

	def put_error(self, error:float):
		self.error_hist.append(error)
		if len(self.error_hist) > self.hist_limit:
			diff = len(self.error_hist) - self.hist_limit
			self.error_hist = self.error_hist[diff:]
		ss[self.error_hist_tag] = self.error_hist

		self.hist_no_out = set(self.remove_outliers())
		self.outliers = set(self.error_hist) - set(self.hist_no_out)
		self.hist = []
		for x in self.error_hist:
			if not x in self.outliers:
				self.hist.append(x)

	def remove_outliers(self):
		h = sorted(self.error_hist)
		try:
			return h[2:-2]
		except IndexError:
			return h

	def error_latest(self) -> float:
		try:
			return self.hist[-1]
		except IndexError:
			return 0.0

	def error_avg(self) -> float:
		try:
			return self.error_sum() / len(self.hist)
		except ZeroDivisionError:
			return 0.0

	def error_diff(self) -> float:
		try:
			return self.hist[-1] - self.hist[-2]
		except IndexError:
			return 0.0

	def error_sum(self) -> float:
		return sum(self.hist)

	def clear(self):
		ss[self.error_hist_tag] = []
		ss.error_hist = ss[self.error_hist_tag]
