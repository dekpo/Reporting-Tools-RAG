# Packages
import streamlit as st
import docx2txt
import pandas as pd
import webvtt
from docx import Document
from PyPDF2 import PdfReader

# Modules
import re
import html
import io
import time

# Utils
import lib

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.title(lib.APP_TITLE)

st.divider()

st.markdown("<p>Welcome to this set of tools! Upload your document, anonymize content, ask ChatGPT for insights, and revert anonymization when needed.</p>",unsafe_allow_html=True)

st.header("Upload Your Document")

st.markdown("<p>Upload a transcript (.docx or .vtt file) or text document (.docx or .pdf) to begin processing.</p>", unsafe_allow_html=True)

# Subject input (mandatory)
default_title = "Your Subject"
title_input = st.text_input("**Subject*** (mandatory)", default_title, help="What is the subject of your document?")

# Initialize session state for file type if not already set
if 'file_type' not in st.session_state:
    st.session_state.file_type = "vtt"

# File type selection
file_type_options = {
    "vtt": "**.vtt** file from Teams or Zoom",
    "teams_docx": "**.docx** file from Teams transcript",
    "regular_docx": "**.docx** document (regular text)",
    "pdf": "**.pdf** document"
}

# Radio button for file type selection
selected_option = st.radio("**Select file type to upload:**", 
                          options=list(file_type_options.values()))

# Map selected option back to file type
for key, value in file_type_options.items():
    if value == selected_option:
        st.session_state.file_type = key
        break

# Initialize extracted_text
extracted_text = ""

# File uploader based on selected file type
if st.session_state.file_type == "vtt":
    uploaded_file = st.file_uploader("**Upload your .vtt file:**", 
                                    type=["vtt"], 
                                    key="vtt_uploader")
    
    if uploaded_file is not None:
        with st.spinner('Extracting content from VTT file... Please Wait.'):
            try:
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                rows = webvtt.from_buffer(stringio)
                
                for row in rows:
                    if row.text:
                        message = html.unescape(row.raw_text)
                        
                        if message.count("<v") > 0:
                            msg_info = message.replace("<v ","")
                            msg_info = msg_info.replace("</v>","")
                            msg_table = msg_info.split(">")
                            attendee = msg_table[0]
                            message = msg_table[1]
                        elif message.count(": ") > 0:
                            msg_info = message.split(": ")
                            attendee = msg_info[0]
                            message = msg_info[1]
                        else:
                            attendee = "Unknown"
                        
                        message = message.replace("\n"," ")
                        extracted_text += f"{attendee}: {message}\n"
            except:
                st.warning("**Sorry but** this document does not seem to be a valid .vtt file", icon="⚠️")

elif st.session_state.file_type == "teams_docx":
    uploaded_file = st.file_uploader("**Upload your Teams transcript .docx file:**", 
                                    type=["docx"], 
                                    key="teams_docx_uploader")
    
    if uploaded_file is not None:
        with st.spinner('Extracting content from Teams transcript... Please Wait.'):
            try:
                txt = docx2txt.process(uploaded_file)
                count_arrows = txt.count(" --> ")
                
                if count_arrows > 2:
                    file_info = "Old"
                else:
                    file_info = "New"
                
                rows = txt.split("\n\n")
                
                for row in rows:
                    if file_info == "New":
                        line = row.split('\n')
                        if len(line) > 1:
                            line.pop(0)
                            match = re.search('\\s\\s\\s',line[0])
                            if match:
                                attendee = line[0][0:match.start()]
                                timing = line[0][match.end():len(line[0])-1]
                                line.pop(0)
                                message = ""
                                for item in line:
                                    message = message + " " +item
                                extracted_text += f"{attendee}: {message}\n"
                    elif file_info == "Old":
                        line = row.split('\n')
                        if len(line) == 3:
                            extracted_text += f"{line[1]}: {line[2]}\n"
                        elif len(line) == 2:
                            extracted_text += f"Attendee: {line[1]}\n"
            except:
                st.warning("**Sorry there was an error processing this file.** Is it a Teams transcript file?", icon="⚠️")

elif st.session_state.file_type == "regular_docx":
    uploaded_file = st.file_uploader("**Upload your .docx document:**", 
                                    type=["docx"], 
                                    key="regular_docx_uploader")
    
    if uploaded_file is not None:
        with st.spinner('Extracting content from DOCX file... Please Wait.'):
            try:
                extracted_text = docx2txt.process(uploaded_file)
            except:
                st.warning("**Sorry there was an error processing this file.**", icon="⚠️")

elif st.session_state.file_type == "pdf":
    uploaded_file = st.file_uploader("**Upload your .pdf document:**", 
                                    type=["pdf"], 
                                    key="pdf_uploader")
    
    if uploaded_file is not None:
        with st.spinner('Extracting content from PDF file... Please Wait.'):
            try:
                pdf_reader = PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"
            except:
                st.warning("**Sorry there was an error processing this PDF file.**", icon="⚠️")

# Text area for manual input or displaying extracted content
if extracted_text:
    text_area = st.text_area("**Extracted content:**", value=extracted_text, height=300, key="extracted_content")
else:
    text_area = st.text_area("**Or paste your text here:**", height=300)

# Proceed button
if st.button("**Continue to Anonymization**", type="primary"):
    if not title_input or title_input == default_title:
        st.error("Please provide a subject for your document.")
    elif not text_area and not extracted_text:
        st.error("Please upload a file or paste text content.")
    else:
        # Save content for next step
        content_to_save = extracted_text if extracted_text else text_area
        lib.save_content(title_input, content_to_save, {})
        st.switch_page("./pages/03_anonymize.py")

# Display navigation options
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
   st.header("1) Anonymize")
   st.page_link(page="pages/03_anonymize.py", label="Go To Anonymize Content", icon=":material/sms:", use_container_width=True)

with col2:
   st.header("2) Ask ChatGPT")
   st.page_link(page="pages/04_chatgpt.py", label="Go To ChatGPT Tool", icon=":material/hexagon:", use_container_width=True)

with col3:
   st.header("3) Reverse Anonymization")
   st.page_link(page="pages/05_revert.py", label="Go To Reverse Anonymization", icon=":material/comment:", use_container_width=True)