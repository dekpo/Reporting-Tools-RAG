# Packages
import streamlit as st
import docx2txt
import pandas as pd
import webvtt
from docx import Document
from PyPDF2 import PdfReader
import hashlib

# Modules
import re
import html
import io
import time
import os

# Utils
import lib

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.title(lib.APP_TITLE)

st.divider()

# Helper function to generate file hash for caching
def generate_file_hash(file_content, file_name, file_type):
    """Generate a unique hash for uploaded file to enable caching"""
    content_str = f"{file_name}_{file_type}_{len(file_content)}"
    return hashlib.md5(content_str.encode()).hexdigest()

# Helper function to extract content from VTT files
@st.cache_data
def extract_vtt_content(file_content, file_hash):
    """Extract content from VTT file with caching"""
    extracted_text = ""
    try:
        stringio = io.StringIO(file_content.decode("utf-8"))
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
        return extracted_text, True
    except Exception as e:
        return "", False

# Helper function to extract content from Teams DOCX files
@st.cache_data
def extract_teams_docx_content(file_content, file_hash):
    """Extract content from Teams DOCX file with caching"""
    extracted_text = ""
    try:
        # Create a temporary file-like object for docx2txt
        file_obj = io.BytesIO(file_content)
        txt = docx2txt.process(file_obj)
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
        return extracted_text, True
    except Exception as e:
        return "", False

# Helper function to extract content from regular DOCX files
@st.cache_data
def extract_regular_docx_content(file_content, file_hash):
    """Extract content from regular DOCX file with caching"""
    try:
        # Create a temporary file-like object for docx2txt
        file_obj = io.BytesIO(file_content)
        extracted_text = docx2txt.process(file_obj)
        return extracted_text, True
    except Exception as e:
        return "", False

# Helper function to extract content from PDF files
@st.cache_data
def extract_pdf_content(file_content, file_hash):
    """Extract content from PDF file with caching"""
    extracted_text = ""
    try:
        # Create a temporary file-like object for PyPDF2
        file_obj = io.BytesIO(file_content)
        pdf_reader = PdfReader(file_obj)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
        return extracted_text, True
    except Exception as e:
        return "", False

# Helper function to process CSV files
@st.cache_data
def process_csv_file(file_content, file_hash):
    """Process CSV file and return DataFrame with caching"""
    try:
        # Detect delimiter
        separator = lib.get_delimiter(io.BytesIO(file_content))
        df = pd.read_csv(io.BytesIO(file_content), sep=separator, engine='python')
        return df, True
    except Exception as e:
        return None, False

# Helper function to process Excel files
@st.cache_data  
def process_excel_file(file_content, file_hash):
    """Process Excel file and return DataFrame with caching"""
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        return df, True
    except Exception as e:
        return None, False

# Check for existing documents in the ChromaDB database
persist_directory = './chroma_db'
if os.path.exists(persist_directory) and os.path.isdir(persist_directory):
    document_metadata = lib.load_document_metadata(persist_directory)
    if document_metadata:
        # Import datetime here since it's only needed if documents exist
        from datetime import datetime
        
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            st.info(f"Found {len(document_metadata)} document(s) already stored in the database. You can continue working with them.")
        with col2:
            st.page_link(page="pages/02_chatgpt.py", label="Go to ChatGPT Tool", icon=":material/hexagon:", use_container_width=True)
            
        # Show document titles in an expandable section
        with st.expander("View stored documents"):
            # Convert metadata to a more usable format for display
            doc_list = []
            for doc_hash, doc_data in document_metadata.items():
                doc_list.append({
                    "title": doc_data["title"],
                    "timestamp": doc_data.get("timestamp", 0)
                })
            
            # Sort by timestamp (newest first)
            doc_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Display document titles
            for i, doc in enumerate(doc_list):
                try:
                    if doc["timestamp"] > 0:
                        timestamp = datetime.fromtimestamp(doc["timestamp"])
                        date_str = timestamp.strftime('%Y-%m-%d')
                    else:
                        date_str = "Unknown date"
                except Exception:
                    date_str = "Unknown date"
                
                st.write(f"**{i+1}.** {doc['title']} _(Added: {date_str})_")

# Check for existing tabular datasets
tabular_metadata = lib.get_tabular_metadata()
if tabular_metadata:
    # Import datetime here since it's only needed if datasets exist
    from datetime import datetime
    
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.info(f"Found {len(tabular_metadata)} dataset(s) already stored. You can continue working with them.")
    with col2:
        st.page_link(page="pages/02_chatgpt.py", label="Go to ChatGPT Tool", icon=":material/hexagon:", use_container_width=True)
        
    # Show dataset titles in an expandable section
    with st.expander("View stored datasets"):
        # Convert metadata to a more usable format for display
        dataset_list = []
        for file_hash, dataset_data in tabular_metadata.items():
            dataset_list.append({
                "title": dataset_data["title"],
                "shape": dataset_data["shape"],
                "columns": dataset_data["columns"],
                "timestamp": dataset_data.get("timestamp", 0)
            })
        
        # Sort by timestamp (newest first)
        dataset_list.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Display dataset titles
        for i, dataset in enumerate(dataset_list):
            try:
                if dataset["timestamp"] > 0:
                    timestamp = datetime.fromtimestamp(dataset["timestamp"])
                    date_str = timestamp.strftime('%Y-%m-%d')
                else:
                    date_str = "Unknown date"
            except Exception:
                date_str = "Unknown date"
            
            st.write(f"**{i+1}.** {dataset['title']} _{dataset['shape'][0]} rows, {dataset['shape'][1]} columns_ _(Added: {date_str})_")

st.markdown("<p>Welcome to this set of tools! Upload your document, anonymize content, ask ChatGPT for insights, and revert anonymization when needed.</p>",unsafe_allow_html=True)

st.header("Upload Your Document")

st.markdown("<p>Upload a transcript (.docx or .vtt file), text document (.docx or .pdf), or data file (.csv or .xlsx) to begin processing.</p>", unsafe_allow_html=True)

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
    "pdf": "**.pdf** document",
    "csv": "**.csv** data file",
    "excel": "**.xlsx** Excel file"
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
processing_success = True

# File uploader based on selected file type
if st.session_state.file_type == "vtt":
    uploaded_file = st.file_uploader("**Upload your .vtt file:**", 
                                    type=["vtt"], 
                                    key="vtt_uploader")
    
    if uploaded_file is not None:
        # Generate file hash for caching
        file_content = uploaded_file.getvalue()
        file_hash = generate_file_hash(file_content, uploaded_file.name, "vtt")
        
        # Check if we already have this content processed
        cache_key = f"extracted_content_{file_hash}"
        
        if cache_key not in st.session_state:
            # Only show spinner when actually processing
            with st.spinner('Extracting content from VTT file... Please Wait.'):
                extracted_text, processing_success = extract_vtt_content(file_content, file_hash)
                # Cache the result
                st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
        else:
            # Use cached result
            cached_result = st.session_state[cache_key]
            extracted_text = cached_result["content"]
            processing_success = cached_result["success"]
        
        if not processing_success:
            st.warning("**Sorry but** this document does not seem to be a valid .vtt file", icon="⚠️")

elif st.session_state.file_type == "teams_docx":
    uploaded_file = st.file_uploader("**Upload your Teams transcript .docx file:**", 
                                    type=["docx"], 
                                    key="teams_docx_uploader")
    
    if uploaded_file is not None:
        # Generate file hash for caching
        file_content = uploaded_file.getvalue()
        file_hash = generate_file_hash(file_content, uploaded_file.name, "teams_docx")
        
        # Check if we already have this content processed
        cache_key = f"extracted_content_{file_hash}"
        
        if cache_key not in st.session_state:
            # Only show spinner when actually processing
            with st.spinner('Extracting content from Teams transcript... Please Wait.'):
                extracted_text, processing_success = extract_teams_docx_content(file_content, file_hash)
                # Cache the result
                st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
        else:
            # Use cached result
            cached_result = st.session_state[cache_key]
            extracted_text = cached_result["content"]
            processing_success = cached_result["success"]
        
        if not processing_success:
            st.warning("**Sorry there was an error processing this file.** Is it a Teams transcript file?", icon="⚠️")

elif st.session_state.file_type == "regular_docx":
    uploaded_file = st.file_uploader("**Upload your .docx document:**", 
                                    type=["docx"], 
                                    key="regular_docx_uploader")
    
    if uploaded_file is not None:
        # Generate file hash for caching
        file_content = uploaded_file.getvalue()
        file_hash = generate_file_hash(file_content, uploaded_file.name, "regular_docx")
        
        # Check if we already have this content processed
        cache_key = f"extracted_content_{file_hash}"
        
        if cache_key not in st.session_state:
            # Only show spinner when actually processing
            with st.spinner('Extracting content from DOCX file... Please Wait.'):
                extracted_text, processing_success = extract_regular_docx_content(file_content, file_hash)
                # Cache the result
                st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
        else:
            # Use cached result
            cached_result = st.session_state[cache_key]
            extracted_text = cached_result["content"]
            processing_success = cached_result["success"]
        
        if not processing_success:
            st.warning("**Sorry there was an error processing this file.**", icon="⚠️")

elif st.session_state.file_type == "pdf":
    uploaded_file = st.file_uploader("**Upload your .pdf document:**", 
                                    type=["pdf"], 
                                    key="pdf_uploader")
    
    if uploaded_file is not None:
        # Generate file hash for caching
        file_content = uploaded_file.getvalue()
        file_hash = generate_file_hash(file_content, uploaded_file.name, "pdf")
        
        # Check if we already have this content processed
        cache_key = f"extracted_content_{file_hash}"
        
        if cache_key not in st.session_state:
            # Only show spinner when actually processing
            with st.spinner('Extracting content from PDF file... Please Wait.'):
                extracted_text, processing_success = extract_pdf_content(file_content, file_hash)
                # Cache the result
                st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
        else:
            # Use cached result
            cached_result = st.session_state[cache_key]
            extracted_text = cached_result["content"]
            processing_success = cached_result["success"]
        
        if not processing_success:
            st.warning("**Sorry there was an error processing this PDF file.**", icon="⚠️")

elif st.session_state.file_type == "csv":
    uploaded_file = st.file_uploader("**Upload your .csv data file:**", 
                                    type=["csv"], 
                                    key="csv_uploader")
    
    if uploaded_file is not None:
        # Generate file hash for caching
        file_content = uploaded_file.getvalue()
        file_hash = lib.generate_file_hash(file_content, uploaded_file.name, "csv")
        
        # Check if we already have this content processed
        cache_key = f"processed_data_{file_hash}"
        
        if cache_key not in st.session_state:
            # Only show spinner when actually processing
            with st.spinner('Processing CSV file... Please Wait.'):
                df, processing_success = process_csv_file(file_content, file_hash)
                # Cache the result
                st.session_state[cache_key] = {"dataframe": df, "success": processing_success}
        else:
            # Use cached result
            cached_result = st.session_state[cache_key]
            df = cached_result["dataframe"]
            processing_success = cached_result["success"]
        
        if processing_success and df is not None:
            st.success(f"CSV file processed successfully! Found {df.shape[0]} rows and {df.shape[1]} columns.")
            st.dataframe(df.head(), use_container_width=True)
            
            # Store in session state for immediate use
            if "tabular_datasets" not in st.session_state:
                st.session_state.tabular_datasets = {}
            st.session_state.tabular_datasets[f"temp_{uploaded_file.name}"] = df
        else:
            st.warning("**Sorry there was an error processing this CSV file.**", icon="⚠️")

elif st.session_state.file_type == "excel":
    uploaded_file = st.file_uploader("**Upload your .xlsx Excel file:**", 
                                    type=["xlsx"], 
                                    key="excel_uploader")
    
    if uploaded_file is not None:
        # Generate file hash for caching
        file_content = uploaded_file.getvalue()
        file_hash = lib.generate_file_hash(file_content, uploaded_file.name, "excel")
        
        # Check if we already have this content processed
        cache_key = f"processed_data_{file_hash}"
        
        if cache_key not in st.session_state:
            # Only show spinner when actually processing
            with st.spinner('Processing Excel file... Please Wait.'):
                df, processing_success = process_excel_file(file_content, file_hash)
                # Cache the result
                st.session_state[cache_key] = {"dataframe": df, "success": processing_success}
        else:
            # Use cached result
            cached_result = st.session_state[cache_key]
            df = cached_result["dataframe"]
            processing_success = cached_result["success"]
        
        if processing_success and df is not None:
            st.success(f"Excel file processed successfully! Found {df.shape[0]} rows and {df.shape[1]} columns.")
            st.dataframe(df.head(), use_container_width=True)
            
            # Store in session state for immediate use
            if "tabular_datasets" not in st.session_state:
                st.session_state.tabular_datasets = {}
            st.session_state.tabular_datasets[f"temp_{uploaded_file.name}"] = df
        else:
            st.warning("**Sorry there was an error processing this Excel file.**", icon="⚠️")

# Text area for manual input or displaying extracted content (only for text files)
text_area = ""
if st.session_state.file_type not in ["csv", "excel"]:
    if extracted_text:
        text_area = st.text_area("**Extracted content:**", value=extracted_text, height=300, key="extracted_content")
    else:
        text_area = st.text_area("**Or paste your text here:**", height=300)

# Proceed button - different logic for text vs tabular data
if st.session_state.file_type in ["csv", "excel"]:
    # For tabular data - skip anonymization and go directly to ChatGPT
    button_text = "**Continue to Analysis**"
    if st.button(button_text, type="primary"):
        if not title_input or title_input == default_title:
            st.error("Please provide a subject for your document.")
        elif "tabular_datasets" not in st.session_state or not st.session_state.tabular_datasets:
            st.error("Please upload a CSV or Excel file first.")
        else:
            # Get the uploaded file info
            temp_key = list(st.session_state.tabular_datasets.keys())[0]
            df = st.session_state.tabular_datasets[temp_key]
            
            # Generate proper file hash and save persistently
            if uploaded_file is not None:
                file_content = uploaded_file.getvalue()
                file_hash = lib.generate_file_hash(file_content, uploaded_file.name, st.session_state.file_type)
                
                # Save tabular metadata for persistence
                lib.save_tabular_metadata(title_input, df, file_hash)
                
                # Update session state with proper title
                del st.session_state.tabular_datasets[temp_key]
                st.session_state.tabular_datasets[title_input] = df
                
                # Skip anonymization, go directly to ChatGPT
                st.switch_page("./pages/02_chatgpt.py")
            else:
                st.error("Please upload a file first.")
else:
    # For text files - continue with existing anonymization flow
    button_text = "**Continue to Anonymization**"
    if st.button(button_text, type="primary"):
        if not title_input or title_input == default_title:
            st.error("Please provide a subject for your document.")
        elif not text_area and not extracted_text:
            st.error("Please upload a file or paste text content.")
        else:
            # Save content for next step
            content_to_save = extracted_text if extracted_text else text_area
            lib.save_content(title_input, content_to_save, {})
            st.switch_page("./pages/01_anonymize.py")
