#!/usr/bin/env python3

import streamlit as st

def index():
	st.title("Dashboard")
	st.text("Welcome. Use the menu on the left to navigate.")

def debug_state():
	st.title("Debug Session State")

	sorted_keys = sorted(st.session_state)
	sorted_dict_by_key = {k: st.session_state[k] for k in sorted_keys}
	st.write(sorted_dict_by_key)
