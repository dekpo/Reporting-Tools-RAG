# Packages
import streamlit as st
import pyperclip

# Modules

# Utils
import lib

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.title(lib.APP_TITLE)

st.divider()

st.markdown("<p>Welcome to this set of tools ! Here you can Convert transcripts files, Extract Content, Anonymize your content and Ask ChatGPT to process with your content...</p>",unsafe_allow_html=True)



col1, col2 = st.columns(2)
with col1:
   st.header("1) Convert Transcripts")
   st.page_link(page="pages/01_convert.py",label="Got To Convert Transcripts",icon=":material/table:",use_container_width=True)

with col2:
   st.header("2) Extract Content")
   st.page_link(page="pages/02_extract.py",label="Got To Extract Content",icon=":material/chat:",use_container_width=True)

col3, col4 = st.columns(2)
with col3:
   st.header("3) Anonymize Content")
   st.page_link(page="pages/03_anonymize.py",label="Got To Anonymize Content",icon=":material/sms:",use_container_width=True)

with col4:
   st.header("4) Ask ChatGPT")
   st.page_link(page="pages/04_chatgpt.py",label="Got To ChatGPT Tool",icon=":material/hexagon:",use_container_width=True)