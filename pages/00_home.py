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

# Helper function to clean filename for subject
def clean_filename_for_subject(filename):
    """Clean filename to create a nice subject title"""
    if not filename:
        return "Your Subject"
    
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Replace special characters with spaces
    cleaned = re.sub(r'[_\-\.]+', ' ', name_without_ext)
    
    # Remove extra spaces and apply title case
    cleaned = ' '.join(cleaned.split()).title()
    
    return cleaned if cleaned else "Your Subject"

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
        # ORIGINAL APPROACH: Use delimiter detection (works for most CSV files)
        separator = lib.get_delimiter(io.BytesIO(file_content))
        df = pd.read_csv(io.BytesIO(file_content), sep=separator, engine='python')
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        return df, True
    except Exception as e:
        # FALLBACK 1: Force comma separator for problematic files
        try:
            df = pd.read_csv(
                io.BytesIO(file_content), 
                sep=',',
                encoding='utf-8'
            )
            df.columns = df.columns.str.strip()
            return df, True
        except Exception as e2:
            # FALLBACK 2: Enhanced parsing for complex CSV files
            try:
                df = pd.read_csv(
                    io.BytesIO(file_content), 
                    sep=',',                    
                    engine='python',            
                    encoding='utf-8',           
                    skipinitialspace=True,      
                    quotechar='"',              
                    doublequote=True,           
                    on_bad_lines='skip'         
                )
                df.columns = df.columns.str.strip()
                return df, True
            except Exception as e3:
                # FALLBACK 3: Different encoding
                try:
                    df = pd.read_csv(
                        io.BytesIO(file_content), 
                        sep=',',
                        encoding='latin-1'
                    )
                    df.columns = df.columns.str.strip()
                    return df, True
                except:
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



st.markdown("<p>Welcome to this set of tools! Upload your document, anonymize content, ask ChatGPT for insights, and revert anonymization when needed.</p>",unsafe_allow_html=True)

st.header("Upload New Source")

st.markdown("<p>Upload your file to begin processing. Choose from meeting transcripts, text documents, or data files.</p>", unsafe_allow_html=True)

# Initialize session state for file category if not already set
if 'file_category' not in st.session_state:
    st.session_state.file_category = "transcript"

# Simplified file category selection
file_category_options = {
    "transcript": "📝 **Meeting Transcripts** (.vtt or .docx from Teams/Zoom)",
    "document": "📄 **Text Documents** (.docx or .pdf files)",
    "data": "📊 **Data Files** (.csv or .xlsx spreadsheets)"
}

# Radio button for file category selection
selected_category = st.radio("**What type of file are you uploading?**", 
                           options=list(file_category_options.values()),
                           help="Choose the category that best describes your file")

# Map selected option back to file category
for key, value in file_category_options.items():
    if value == selected_category:
        st.session_state.file_category = key
        break

# Helper function to detect file type from uploaded file
def detect_file_type(uploaded_file, file_category):
    """Detect specific file type based on extension and category"""
    if not uploaded_file:
        return None
    
    file_extension = uploaded_file.name.lower().split('.')[-1]
    
    if file_category == "transcript":
        if file_extension == "vtt":
            return "vtt"
        elif file_extension == "docx":
            return "teams_docx"  # We'll try Teams format first, fallback to regular if needed
    elif file_category == "document":
        if file_extension == "docx":
            return "regular_docx"
        elif file_extension == "pdf":
            return "pdf"
    elif file_category == "data":
        if file_extension == "csv":
            return "csv"
        elif file_extension in ["xlsx", "xls"]:
            return "excel"
    
    return None

# Initialize extracted_text
extracted_text = ""
processing_success = True

# File uploader based on selected category
if st.session_state.file_category == "transcript":
    uploaded_file = st.file_uploader("**Upload your transcript file:**", 
                                    type=["vtt", "docx"], 
                                    key="transcript_uploader",
                                    help="Supports .vtt files from Zoom/Teams and .docx transcript files from Teams")
    
    if uploaded_file is not None:
        # Detect specific file type
        detected_type = detect_file_type(uploaded_file, "transcript")
        
        if detected_type == "vtt":
            # Generate file hash for caching
            file_content = uploaded_file.getvalue()
            file_hash = generate_file_hash(file_content, uploaded_file.name, "vtt")
            
            # Check if we already have this content processed
            cache_key = f"extracted_content_{file_hash}"
            
            if cache_key not in st.session_state:
                # Only show spinner when actually processing
                with st.spinner('Extracting content from VTT transcript... Please Wait.'):
                    extracted_text, processing_success = extract_vtt_content(file_content, file_hash)
                    # Cache the result
                    st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
            else:
                # Use cached result
                cached_result = st.session_state[cache_key]
                extracted_text = cached_result["content"]
                processing_success = cached_result["success"]
            
            if not processing_success:
                st.warning("**Sorry but** this document does not seem to be a valid .vtt transcript file", icon="⚠️")
        
        elif detected_type == "teams_docx":
            # Generate file hash for caching
            file_content = uploaded_file.getvalue()
            file_hash = generate_file_hash(file_content, uploaded_file.name, "teams_docx")
            
            # Check if we already have this content processed
            cache_key = f"extracted_content_{file_hash}"
            
            if cache_key not in st.session_state:
                # Only show spinner when actually processing
                with st.spinner('Extracting content from Teams transcript... Please Wait.'):
                    extracted_text, processing_success = extract_teams_docx_content(file_content, file_hash)
                    
                    # If Teams format fails, try regular DOCX format as fallback
                    if not processing_success:
                        st.info("Trying alternative DOCX format...")
                        extracted_text, processing_success = extract_regular_docx_content(file_content, file_hash)
                    
                    # Cache the result
                    st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
            else:
                # Use cached result
                cached_result = st.session_state[cache_key]
                extracted_text = cached_result["content"]
                processing_success = cached_result["success"]
            
            if not processing_success:
                st.warning("**Sorry there was an error processing this transcript file.** Please ensure it's a valid Teams transcript or try uploading as a regular document.", icon="⚠️")

elif st.session_state.file_category == "document":
    uploaded_file = st.file_uploader("**Upload your document:**", 
                                    type=["docx", "pdf"], 
                                    key="document_uploader",
                                    help="Supports .docx Word documents and .pdf files")
    
    if uploaded_file is not None:
        # Detect specific file type
        detected_type = detect_file_type(uploaded_file, "document")
        file_content = uploaded_file.getvalue()
        
        if detected_type == "regular_docx":
            file_hash = generate_file_hash(file_content, uploaded_file.name, "regular_docx")
            
            # Check if we already have this content processed
            cache_key = f"extracted_content_{file_hash}"
            
            if cache_key not in st.session_state:
                # Only show spinner when actually processing
                with st.spinner('Extracting content from Word document... Please Wait.'):
                    extracted_text, processing_success = extract_regular_docx_content(file_content, file_hash)
                    # Cache the result
                    st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
            else:
                # Use cached result
                cached_result = st.session_state[cache_key]
                extracted_text = cached_result["content"]
                processing_success = cached_result["success"]
            
            if not processing_success:
                st.warning("**Sorry there was an error processing this Word document.**", icon="⚠️")
        
        elif detected_type == "pdf":
            file_hash = generate_file_hash(file_content, uploaded_file.name, "pdf")
            
            # Check if we already have this content processed
            cache_key = f"extracted_content_{file_hash}"
            
            if cache_key not in st.session_state:
                # Only show spinner when actually processing
                with st.spinner('Extracting content from PDF document... Please Wait.'):
                    extracted_text, processing_success = extract_pdf_content(file_content, file_hash)
                    # Cache the result
                    st.session_state[cache_key] = {"content": extracted_text, "success": processing_success}
            else:
                # Use cached result
                cached_result = st.session_state[cache_key]
                extracted_text = cached_result["content"]
                processing_success = cached_result["success"]
            
            if not processing_success:
                st.warning("**Sorry there was an error processing this PDF document.**", icon="⚠️")

elif st.session_state.file_category == "data":
    uploaded_file = st.file_uploader("**Upload your data file:**", 
                                    type=["csv", "xlsx", "xls"], 
                                    key="data_uploader",
                                    help="Supports .csv files and Excel spreadsheets (.xlsx, .xls)")
    
    if uploaded_file is not None:
        # Detect specific file type
        detected_type = detect_file_type(uploaded_file, "data")
        file_content = uploaded_file.getvalue()
        
        if detected_type == "csv":
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
        
        elif detected_type == "excel":
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

# Subject input (mandatory) - positioned after file upload with auto-population
default_title = "Your Subject"
auto_title = default_title

# Auto-populate subject from uploaded filename if available
if 'uploaded_file' in locals() and uploaded_file is not None:
    auto_title = clean_filename_for_subject(uploaded_file.name)

title_input = st.text_input("**Subject*** (mandatory)", 
                           value=auto_title, 
                           help="What is the subject of your document? (Auto-filled from filename)")

# Text area for manual input or displaying extracted content (only for text files)
text_area = ""
if st.session_state.file_category != "data":
    if extracted_text:
        text_area = st.text_area("**Extracted content:**", value=extracted_text, height=300, key="extracted_content")
    else:
        text_area = st.text_area("**Or paste your text here:**", height=300)

# Proceed button - different logic for text vs tabular data
if st.session_state.file_category == "data":
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
                # Use the detected file type for the hash
                detected_type = detect_file_type(uploaded_file, "data")
                file_hash = lib.generate_file_hash(file_content, uploaded_file.name, detected_type)
                
                # Save tabular metadata for persistence
                lib.save_tabular_metadata(title_input, df, file_hash)
                
                # Clean up temporary dataset and replace with properly titled one
                # Remove all temporary datasets to avoid duplication
                temp_keys = [key for key in st.session_state.tabular_datasets.keys() if key.startswith("temp_")]
                for temp_key in temp_keys:
                    del st.session_state.tabular_datasets[temp_key]
                
                # Add the properly titled dataset
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
