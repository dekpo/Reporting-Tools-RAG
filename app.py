# Suppress matplotlib warnings and font cache messages (especially for PyInstaller)
import os
import warnings

# Set matplotlib backend before any matplotlib imports
os.environ['MPLBACKEND'] = 'Agg'
os.environ['MPLCONFIGDIR'] = '/tmp'  # Use temp directory for config

# Suppress matplotlib font cache warnings
warnings.filterwarnings('ignore', message='.*font cache.*')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

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

# Simplified 4-step workflow:
# 1. Upload & Extract - Home page (00_home.py)
# 2. Anonymize - Anonymize page (01_anonymize.py)
# 3. ChatGPT - ChatGPT Tool page (02_chatgpt.py)
# 4. Reverse - Reverse Anonymization page (03_revert.py)

st.switch_page("./pages/00_home.py")
