# Packages
import streamlit as st

# Modules
import time

# Utils
import lib

# Ensure required directories exist and set up logging
lib.ensure_rag_directories_exist()
logger = lib.setup_logging()
logger.info("Application started")

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.switch_page("./pages/00_home.py")
