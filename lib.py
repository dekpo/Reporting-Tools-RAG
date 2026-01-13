# Packages
import streamlit as st
import streamlit_antd_components as sac
import spacy
from typing import List, Union, Dict, Any, Optional
from openai import OpenAI
import os
import json
import hashlib
import shutil
import re

# For visualization capabilities
try:
    # Suppress matplotlib font cache messages for PyInstaller exe
    import warnings
    import logging
    
    # Suppress matplotlib font manager warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')
    
    # Suppress matplotlib FigureCanvasAgg warnings  
    warnings.filterwarnings('ignore', category=UserWarning, message='.*FigureCanvasAgg.*')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.backends.*')
    
    # Set matplotlib logging level to suppress font cache messages
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    logging.getLogger('matplotlib.backends').setLevel(logging.ERROR)
    
    import matplotlib.pyplot as plt
    import matplotlib
    
    # Use Agg backend to avoid GUI dependencies in exe
    matplotlib.use('Agg')
    
    import seaborn as sns
    import plotly.express as px
    import plotly.graph_objects as go
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    st.warning("Visualization libraries not available. Install with: pip install matplotlib seaborn plotly")

# For RAG functionality - wrapped in try/except to handle missing dependencies
RAG_AVAILABLE = True
try:
    import chromadb
    from chromadb.config import Settings
    
    # We'll try to import LangChain packages but make each optional
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        # Fallback to langchain-text-splitters if available
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            RecursiveCharacterTextSplitter = None
            st.warning("RecursiveCharacterTextSplitter not available. Please install langchain.")
    
    try:
        from langchain_core.documents import Document
    except ImportError:
        try:
            from langchain.schema import Document
        except ImportError:
            Document = None
            st.warning("Document class not available. Please install langchain-core.")
    
except ImportError:
    st.warning("RAG dependencies are missing. Please install required packages with `pip install chromadb langchain`")
    RAG_AVAILABLE = False

# Modules
import time
from datetime import datetime
import random

APP_TITLE = "UN CEB - :book: Reporting Tools"
APP_VERSION = "2.8.0"

# ============================================================================
# MODEL MANAGEMENT SYSTEM - Auto-updating OpenAI model list
# ============================================================================
# NOTE: Standard GPT models (gpt-4o, gpt-4-turbo, etc.) cannot browse the web
# or access external URLs by default. To enable web browsing:
# - Implement a custom tool using a web search API (e.g., Serper, Brave Search)
# - Use the LangChain agent's tool system to add web search capabilities
# - The model can then reason about when to search the web and use the results
# ============================================================================

# Fallback model list (used if API fetch fails)
# Focused on models best for RAG, text analysis, and data analysis
FALLBACK_MODELS = {
    "Recommended for RAG & Analysis": [
        "gpt-4o",           # Best for complex reasoning and data analysis
        "gpt-4o-mini",      # Faster and cheaper, good for most tasks
        "gpt-4-turbo",      # Strong reasoning, good for complex prompts
    ],
    "Budget Options": [
        "gpt-3.5-turbo",    # Fast and economical for simple tasks
    ]
}

# Model descriptions and capabilities (focused on RAG & data analysis)
MODEL_INFO = {
    "gpt-4o": "🌟 Best for RAG & data analysis - 128K context, excellent reasoning, handles complex queries",
    "gpt-4o-mini": "⚡ Fast & affordable - Good for most RAG tasks, 128K context, 60% cheaper than GPT-4o",
    "gpt-4-turbo": "💪 Strong reasoning - Excellent for complex document analysis and multi-step tasks",
    "gpt-3.5-turbo": "💰 Budget option - Fast for simple queries, 16K context, lowest cost",
}

# Deprecated models and their recommended replacements
DEPRECATED_MODELS = {
    "gpt-4": "gpt-4o",
    "gpt-4-0314": "gpt-4o",
    "gpt-4-32k": "gpt-4o",
    "gpt-4-0613": "gpt-4o",
    "gpt-3.5-turbo-0301": "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo",
    "gpt-3.5-turbo-0613": "gpt-3.5-turbo",
}

# Cache for fetched models (to avoid repeated API calls)
_model_cache = {
    "models": None,
    "timestamp": 0,
    "cache_duration": 3600  # Cache for 1 hour
}

def get_available_models(api_key=None, force_refresh=False):
    """
    Fetch available GPT models from OpenAI API with caching and fallback.
    
    Args:
        api_key: OpenAI API key (optional, uses session state if not provided)
        force_refresh: Force refresh the cache
    
    Returns:
        dict: Dictionary of categorized models
    """
    import time
    
    # Check cache first
    current_time = time.time()
    if not force_refresh and _model_cache["models"] is not None:
        if current_time - _model_cache["timestamp"] < _model_cache["cache_duration"]:
            return _model_cache["models"]
    
    # Try to fetch from API
    if api_key or (hasattr(st, 'session_state') and "gpt_api_key" in st.session_state):
        try:
            if not api_key:
                api_key = st.session_state["gpt_api_key"]
            
            client = OpenAI(api_key=api_key)
            models_list = client.models.list()
            
            # Filter and categorize GPT models (only those useful for RAG & data analysis)
            recommended_models = []
            budget_models = []
            
            # Whitelist of models suitable for RAG and data analysis
            useful_models = {
                'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 
                'gpt-4-turbo-preview', 'gpt-3.5-turbo'
            }
            
            for model in models_list.data:
                model_id = model.id
                # Only include chat/completion GPT models
                if not model_id.startswith('gpt-'):
                    continue
                
                # Skip deprecated models
                if model_id in DEPRECATED_MODELS:
                    continue
                
                # Skip non-chat models (embedding, audio, vision-only, etc.)
                if any(skip in model_id.lower() for skip in ['whisper', 'dall-e', 'tts', 'embedding', 'instruct']):
                    continue
                
                # Only include models in our whitelist or that match our patterns
                if model_id not in useful_models:
                    # Allow if it's a dated snapshot of our useful models
                    if not any(base in model_id for base in ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo']):
                        continue
                
                # Categorize useful models
                if 'gpt-4o' in model_id or 'gpt-4-turbo' in model_id:
                    recommended_models.append(model_id)
                elif 'gpt-3.5' in model_id:
                    budget_models.append(model_id)
            
            # Build categorized dictionary (simplified for clarity)
            categorized_models = {}
            
            if recommended_models:
                # Keep only the main models, limit to 3 most recent
                main_models = []
                for priority_model in ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']:
                    if priority_model in recommended_models:
                        main_models.append(priority_model)
                
                categorized_models["Recommended for RAG & Analysis"] = main_models
            
            if budget_models:
                # Only keep gpt-3.5-turbo (the main one)
                if 'gpt-3.5-turbo' in budget_models:
                    categorized_models["Budget Options"] = ['gpt-3.5-turbo']
            
            # If we got models, cache them
            if categorized_models:
                _model_cache["models"] = categorized_models
                _model_cache["timestamp"] = current_time
                return categorized_models
            
        except Exception as e:
            # If API call fails, use fallback
            pass
    
    # Return fallback models
    return FALLBACK_MODELS

def get_model_description(model_name):
    """
    Get description for a model with context about RAG/data analysis suitability.
    
    Args:
        model_name: Name of the model
    
    Returns:
        str: Model description
    """
    if model_name in MODEL_INFO:
        return MODEL_INFO[model_name]
    
    # Generate generic description based on model name
    if 'gpt-4o' in model_name:
        return "🌟 GPT-4o variant - Excellent for RAG and complex data analysis"
    elif 'gpt-4-turbo' in model_name:
        return "💪 GPT-4 Turbo variant - Strong reasoning for document analysis"
    elif 'gpt-4' in model_name:
        return "⚠️ Older GPT-4 - Consider upgrading to gpt-4o for better performance"
    elif 'gpt-3.5' in model_name:
        return "💰 Budget model - Good for simple queries, limited for complex analysis"
    else:
        return "OpenAI language model"

def check_model_deprecation(model_name):
    """
    Check if a model is deprecated and get replacement.
    
    Args:
        model_name: Name of the model to check
    
    Returns:
        tuple: (is_deprecated, replacement_model)
    """
    if model_name in DEPRECATED_MODELS:
        return True, DEPRECATED_MODELS[model_name]
    return False, None

def get_default_model():
    """
    Get the recommended default model.
    
    Returns:
        str: Default model name
    """
    return "gpt-4o"

def validate_model_availability(client, model_name):
    """
    Validate that a specific model is available for the given API key.
    
    Args:
        client: OpenAI client instance
        model_name: Model name to validate
    
    Returns:
        bool: True if model is available, False otherwise
    """
    try:
        models = client.models.list()
        available_models = [model.id for model in models.data]
        return model_name in available_models
    except:
        return True  # Assume available if check fails

# ============================================================================
# END OF MODEL MANAGEMENT SYSTEM
# ============================================================================

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def app_config():
    st.set_page_config(page_title="UN CEB - Reporting Tools",page_icon="./assets/favicon.ico",layout="wide")
    st.logo("./assets/ceb-logo-full-text-blue.svg", link="https://unsceb.org/", icon_image="./assets/ceb-logo-blue.svg")
    local_css("./assets/css/style.css")
    global current_timestamp
    current_timestamp = int(time.time())
    global current_datetime
    current_datetime = datetime.now().strftime("%Y-%m-%d-%Hh%Mm%Ss")
    
    # Check for cleanup requests at startup
    check_cleanup_requests()

def save_content(title,content,attendees,file_type=None,file_category=None):
    st.session_state["saved_content"] = {
        "Time": current_datetime,
        "Title": title,
        "Data": content,
        "Attendees": attendees,
        "FileType": file_type,
        "FileCategory": file_category
    }
    # Clear entity cache when new content is saved
    clear_entity_cache()

def save_anonymisation(title,content,entities):
    st.session_state["saved_anonymisation"] = {
        "Time": current_datetime,
        "Title": title,
        "Data": content,
        "Entities": entities
    }

def save_gpt_answers(title,content,entities,attendees={}):
    # Ensure entities have the expected structure
    if not entities or not isinstance(entities, dict):
        entities = {
            "Text": [],
            "Replacement": [],
            "Category": []
        }
    elif "Text" not in entities or "Replacement" not in entities or "Category" not in entities:
        # Create a properly structured entities dictionary
        structured_entities = {
            "Text": [],
            "Replacement": [],
            "Category": []
        }
        # Try to copy any existing data
        if "Text" in entities:
            structured_entities["Text"] = entities["Text"]
        if "Replacement" in entities:
            structured_entities["Replacement"] = entities["Replacement"]
        if "Category" in entities:
            structured_entities["Category"] = entities["Category"]
        entities = structured_entities
    
    # Ensure attendees have the expected structure
    if not attendees or not isinstance(attendees, dict):
        attendees = {}
    
    st.session_state["saved_gpt_answers"] = {
        "Time": current_datetime,
        "Title": title,
        "Data": content,
        "Entities": entities,
        "Attendees": attendees
    }

@st.dialog("Delete Your Backup: Are You Sure?")
def del_dialog(string):
    item = st.session_state[string]
    title = item["Title"]
    date = item["Time"]
    match string:
        case "saved_content":
            name = "Extracted Content"
            icon = ":page_with_curl:"
            page = "pages/00_home.py"
        case "saved_anonymisation":
            name = "Anonymized Content"
            icon = ":speech_balloon:"
            page = "pages/01_anonymize.py"
        case "saved_gpt_answers":
            name = "ChatGPT Answers"
            icon = ":robot_face:"
            page = "pages/02_chatgpt.py"
    st.write(f"Do you really want to delete this **{name}**?")
    st.write(f"{icon} **{title}** (Saved: {date})")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes Sure Delete!"):
            del st.session_state[string]
            st.switch_page(page)
    with col2:
        if st.button("No",type="primary"):
            st.rerun()

def sidebar():
    st.sidebar.header(":book: Reporting Tools",divider=True)
    st.sidebar.page_link(page="pages/00_home.py",label="Home",icon=":material/home:")
    st.sidebar.page_link(page="pages/01_anonymize.py",label="Anonymize Content",icon=":material/sms:")
    st.sidebar.page_link(page="pages/02_chatgpt.py",label="ChatGPT Tool",icon=":material/hexagon:")
    st.sidebar.page_link(page="pages/03_revert.py",label="Reverse Anonymization",icon=":material/comment:")
    st.sidebar.page_link(page="pages/04_help.py",label="Help & Documentation",icon=":material/help:")

    # Check for persistent data sources
    persist_directory = './chroma_db'
    document_metadata = {}
    tabular_metadata = {}
    
    # Load document sources
    if os.path.exists(persist_directory) and os.path.isdir(persist_directory):
        document_metadata = load_document_metadata(persist_directory)
    
    # Load tabular sources
    tabular_metadata = get_tabular_metadata()
    
    # Show backup section if we have any persistent sources
    if document_metadata or tabular_metadata:
        st.sidebar.header(":open_file_folder: Your Sources",divider=True)
        
        # Document Sources
        if document_metadata:
            # Count active vs total documents
            active_docs = sum(1 for doc_data in document_metadata.values() if doc_data.get("active", True))
            total_docs = len(document_metadata)
            
            if active_docs == total_docs:
                st.sidebar.markdown(f'<p style="color: #262730; font-size: 16px; font-weight: bold; margin: 0 0 4px 0; line-height: 1.2;">📄 <strong>Document Sources</strong> ({total_docs})</p>', unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f'<p style="color: #262730; font-size: 16px; font-weight: bold; margin: 0 0 4px 0; line-height: 1.2;">📄 <strong>Document Sources</strong> ({active_docs}/{total_docs})</p>', unsafe_allow_html=True)
            
            # Convert metadata to list and sort by timestamp (newest first)
            doc_list = []
            for doc_hash, doc_data in document_metadata.items():
                doc_list.append({
                    "title": doc_data["title"],
                    "timestamp": doc_data.get("timestamp", 0),
                    "active": doc_data.get("active", True)
                })
            doc_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Display documents with status indicators and longer titles
            for doc in doc_list[:5]:  # Show max 5 to avoid sidebar overflow
                truncated_title = doc["title"][:28] + "..." if len(doc["title"]) > 28 else doc["title"]
                if doc["active"]:
                    status_icon = "✅"
                    st.sidebar.markdown(f'<p style="color: #262730; font-size: 14px; margin: 0; line-height: 1.2;">{status_icon} {truncated_title}</p>', unsafe_allow_html=True)
                else:
                    status_icon = "❌"
                    st.sidebar.markdown(f'<p style="color: #9CA3AF; font-size: 14px; margin: 0; line-height: 1.2;">{status_icon} {truncated_title}</p>', unsafe_allow_html=True)
            
            if len(doc_list) > 5:
                remaining_docs = doc_list[5:]
                active_remaining = sum(1 for doc in remaining_docs if doc["active"])
                inactive_remaining = len(remaining_docs) - active_remaining
                if active_remaining and inactive_remaining:
                    st.sidebar.caption(f"• ... and {len(remaining_docs)} more ({active_remaining} active, {inactive_remaining} inactive)")
                elif active_remaining:
                    st.sidebar.caption(f"• ... and {active_remaining} more (all active)")
                elif inactive_remaining:
                    st.sidebar.caption(f"• ... and {inactive_remaining} more (all inactive)")
                else:
                    st.sidebar.caption(f"• ... and {len(remaining_docs)} more")
        
        # Tabular Data Sources
        if tabular_metadata:
            # Add spacing before tabular section if there were documents above
            if document_metadata:
                st.sidebar.markdown("<br>", unsafe_allow_html=True)
            
            # Count active vs total datasets
            active_datasets = sum(1 for dataset_data in tabular_metadata.values() if dataset_data.get("active", True))
            total_datasets = len(tabular_metadata)
            
            if active_datasets == total_datasets:
                st.sidebar.markdown(f'<p style="color: #262730; font-size: 16px; font-weight: bold; margin: 0 0 4px 0; line-height: 1.2;">📊 <strong>Tabular Data Sources</strong> ({total_datasets})</p>', unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f'<p style="color: #262730; font-size: 16px; font-weight: bold; margin: 0 0 4px 0; line-height: 1.2;">📊 <strong>Tabular Data Sources</strong> ({active_datasets}/{total_datasets})</p>', unsafe_allow_html=True)
            
            # Convert metadata to list and sort by timestamp (newest first)
            dataset_list = []
            for file_hash, dataset_data in tabular_metadata.items():
                dataset_list.append({
                    "title": dataset_data["title"],
                    "timestamp": dataset_data.get("timestamp", 0),
                    "active": dataset_data.get("active", True)
                })
            dataset_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Display datasets with status indicators and longer titles
            for dataset in dataset_list[:5]:  # Show max 5 to avoid sidebar overflow
                truncated_title = dataset["title"][:28] + "..." if len(dataset["title"]) > 28 else dataset["title"]
                if dataset["active"]:
                    status_icon = "✅"
                    st.sidebar.markdown(f'<p style="color: #262730; font-size: 14px; margin: 0; line-height: 1.2;">{status_icon} {truncated_title}</p>', unsafe_allow_html=True)
                else:
                    status_icon = "❌"
                    st.sidebar.markdown(f'<p style="color: #9CA3AF; font-size: 14px; margin: 0; line-height: 1.2;">{status_icon} {truncated_title}</p>', unsafe_allow_html=True)
            
            if len(dataset_list) > 5:
                remaining_datasets = dataset_list[5:]
                active_remaining = sum(1 for dataset in remaining_datasets if dataset["active"])
                inactive_remaining = len(remaining_datasets) - active_remaining
                if active_remaining and inactive_remaining:
                    st.sidebar.caption(f"• ... and {len(remaining_datasets)} more ({active_remaining} active, {inactive_remaining} inactive)")
                elif active_remaining:
                    st.sidebar.caption(f"• ... and {active_remaining} more (all active)")
                elif inactive_remaining:
                    st.sidebar.caption(f"• ... and {inactive_remaining} more (all inactive)")
                else:
                    st.sidebar.caption(f"• ... and {len(remaining_datasets)} more")
        
        # Show active sources status if filtering is active
        if document_metadata or tabular_metadata:
            # Add spacing after the lists
            st.sidebar.markdown("<br>", unsafe_allow_html=True)
            
            active_docs = sum(1 for doc_data in document_metadata.values() if doc_data.get("active", True)) if document_metadata else 0
            total_docs = len(document_metadata) if document_metadata else 0
            active_datasets = sum(1 for dataset_data in tabular_metadata.values() if dataset_data.get("active", True)) if tabular_metadata else 0
            total_datasets = len(tabular_metadata) if tabular_metadata else 0
            
            # Show status message if not all sources are active
            if (total_docs > 0 and active_docs < total_docs) or (total_datasets > 0 and active_datasets < total_datasets):
                st.sidebar.markdown(
                    '<div style="background-color: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 4px; padding: 8px; margin: 8px 0;">'
                    '<p style="color: #1f77b4; font-size: 14px; margin: 0; line-height: 1.2;">'
                    'ℹ️ Some sources are inactive. Use \'Manage Sources\' to change selections.'
                    '</p></div>', 
                    unsafe_allow_html=True
                )
        
        # Manage Sources button
        if st.sidebar.button("🔧 Manage Sources", key="manage_sources_sidebar", use_container_width=True, help="Open data sources management dialog"):
            st.session_state["show_sources_dialog"] = True
        
        # Add New Source button
        if st.sidebar.button("📁 Add New Source", key="add_new_source_sidebar", use_container_width=True, help="Upload new documents or datasets"):
            st.switch_page("pages/00_home.py")
    
    # Check if dialog should be shown
    if st.session_state.get("show_sources_dialog", False):
        show_data_sources()
        # Reset the dialog state
        st.session_state["show_sources_dialog"] = False
    
    # Keep session variables working behind the scenes for workflow
    # (Hidden but still functional for the app logic)
    
    st.sidebar.divider()
    st.sidebar.text(f"Release Version {APP_VERSION}")

def steps(i):
    sac.steps(
        items=[
            sac.StepsItem(title='Upload & Extract', subtitle='from file', description='To Raw Text', disabled=True),
            sac.StepsItem(title='Anonymize', subtitle='by categories', description='To Hide Entities', disabled=True),
            sac.StepsItem(title='ChatGPT Tool', subtitle='for asking', description='To Summarize', disabled=True),
            sac.StepsItem(title='Reverse Anonymization', subtitle='from data', description='To DOCX document', disabled=True),
        ], placement='vertical', key="my_steps", index=i, size='sm', color='#1894c6'
    )

def strip_tags(text):
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def remove_stopwords(text):
    nlp = spacy.load('./en_core_web_md')
    doc = nlp(text)
    filtered_words = [token.text for token in doc if not token.is_stop]
    clean_text = " ".join(filtered_words)
    return clean_text

def split_text_into_chunks(text, chunk_size=12000):
    sentences = text.split('.')
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= chunk_size:
            current_chunk += sentence + '.'
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + '.'
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def summarize_text(client,text,part, model="gpt-3.5-turbo", max_tokens=500):
    if model!="gpt-3.5-turbo":
        text = remove_stopwords(text)
    message =  f"Provide a concise summary of the following discussion, limited to five sentences:\n\n{text}"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an helpful assistant."},
            {"role": "user", "content": message}
        ],
        max_tokens=max_tokens
    )
    with st.chat_message("user"):
        st.markdown(message)
    summary = part+"\n"+response.choices[0].message.content.strip()
    st.session_state.messages.append({"role": "assistant", "content": summary })
    with st.chat_message("assistant"):
        st.markdown(summary)
    return summary

def final_summary(client,text, model="gpt-3.5-turbo", max_tokens=500):
    message = f"Summarize the following discussion parts in the style of a formal report. Focus only on the main points and essential discussions:\n\n{text}"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an helpful assistant."},
            {"role": "user", "content": message}
        ],
        max_tokens=max_tokens
    )
    with st.chat_message("user"):
        st.markdown(message)
    summary = response.choices[0].message.content.strip()
    st.session_state.messages.append({"role": "assistant", "content": summary })
    with st.chat_message("assistant"):
        st.markdown(summary)
    return summary

def get_gpt_answers():
    gpt_answers = ""
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            gpt_answers = gpt_answers + message["content"] + "\n\n"
    return gpt_answers

def filter_informal(text):
    informal_words = [
    "Hello everybody",
    "Hello.",
    "Hello,",
    "Good morning",
    "good morning",
    "afternoon everybody",
    "afternoon, everyone",
    "and.",
    "Hi",
    "Umm",
    "umm",
    "Um",
    "Uh",
    "uh,",
    ", uh",
    "OK.",
    "OK,",
    "OK?",
    "OK",
    "Great.",
    "Exactly.",
    "It is.",
    "Mm-hmm",
    "hmm",
    "Hmm", 
    "Sure",
    "for sure.",
    "sure.", 
    "Yeah",
    "yeah",
    "Yes",
    "yes",
    "Alright", 
    "Right",
    "alright",
    "right", 
    "Ohh",
    "Oh", 
    "Sorry",
    "So",
    "let's start then",
    "let's get started",
    "Thank you very much",
    "thank you very much",
    "Thank you so much",
    "thank you so much",
    "Thank you",
    "Thanks",
    "That's all",
    "good afternoon",
    "Good",
    "Oops",
    "Well",
    "Hasting",
    "you know",
    "No problem",
    "How are you",
    "I'm gonna",
    "I have it here",
    "Now",
    "And so on",
    "to, to",
    "Anyway",
    "It's it's",
    "of of",
    "Bye",
    "bye"
    ]
    for word in informal_words: 
        text = text.replace(word," ")
        text = text.replace(" .","")
        text = text.replace(" !","")
        text = text.replace(" ?","")
        text = text.replace(" , ","")
        text = text.replace("  "," ")
    return text

def valid_xml_char_ordinal(c):
    codepoint = ord(c)
    # conditions ordered by presumed frequency
    return (
        0x20 <= codepoint <= 0xD7FF or
        codepoint in (0x9, 0xA, 0xD) or
        0xE000 <= codepoint <= 0xFFFD or
        0x10000 <= codepoint <= 0x10FFFF
        )

def filter_xml_chars(text):
    """
    Filter out characters that are not valid in XML documents.
    This is useful when saving text to formats that use XML internally (like .docx).
    
    Args:
        text: String to filter
        
    Returns:
        String containing only valid XML characters
    """
    if not text:
        return ""
    return ''.join(c for c in text if valid_xml_char_ordinal(c))

def get_rand_id():
    array = list("123456789")
    random.shuffle( array )
    string = "".join(str(i) for i in array)
    return string

def add_zero(nb):
    number = int(nb)
    if number<10:
        number = f"0{nb}"
    return number

def clear_entity_cache():
    """
    Clear cached entity extraction results when content changes.
    This should be called when new content is uploaded or modified.
    """
    keys_to_remove = []
    for key in st.session_state:
        if key.startswith("entities_cache_"):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del st.session_state[key]
    
    # Also clear the last processed hash
    if "last_processed_hash" in st.session_state:
        del st.session_state["last_processed_hash"]

def clear_extraction_cache():
    """
    Clear cached file extraction results.
    This can be called when users want to force re-processing of files.
    """
    keys_to_remove = []
    for key in st.session_state:
        if key.startswith("extracted_content_"):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del st.session_state[key]

def clear_all_caches():
    """
    Clear all application caches (entity extraction and file extraction).
    """
    clear_entity_cache()
    clear_extraction_cache()

# RAG-related functions
def ensure_rag_directories_exist():
    """
    Create necessary directories for the RAG functionality.
    """
    directories_to_create = [
        './chroma_db',  # ChromaDB persistent storage directory
        './logs'        # Optional logging directory
    ]
    
    for directory in directories_to_create:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            st.error(f"Could not create directory {directory}: {e}")

class OpenAIEmbeddingFunction:
    """
    Custom embedding function for ChromaDB using OpenAI's embedding API.
    """
    def __init__(self, api_key=None):
        """
        Initialize the embedding function with OpenAI API key.
        If no key is provided, it tries to use the environment variable.
        """
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided")
        
        # Create OpenAI client
        self.client = OpenAI(api_key=self.api_key)
    
    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        """
        Generate embeddings for input text(s).
        Supports both single string and list of strings.
        """
        # Ensure input is a list
        if isinstance(input, str):
            input = [input]
        
        try:
            # Create embeddings using OpenAI's API
            response = self.client.embeddings.create(
                input=input,
                model="text-embedding-ada-002"
            )
            
            # Extract and return embeddings
            return [embedding.embedding for embedding in response.data]
        
        except Exception as e:
            st.error(f"Embedding generation error: {e}")
            # Return a default embedding if generation fails
            return [[0.0] * 1536] * len(input)

def get_metadata_path(persist_directory):
    """
    Get the path for the metadata JSON file.
    """
    return os.path.join(persist_directory, 'document_metadata.json')

def load_document_metadata(persist_directory):
    """
    Load metadata for documents stored in the vector database.
    """
    metadata_path = get_metadata_path(persist_directory)
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_document_metadata(persist_directory, metadata):
    """
    Save metadata for documents stored in the vector database.
    Include additional fields for document management.
    """
    metadata_path = get_metadata_path(persist_directory)
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    
    # Add timestamp if not present and active status
    for doc_hash, doc_data in metadata.items():
        if 'timestamp' not in doc_data:
            doc_data['timestamp'] = time.time()
        if 'active' not in doc_data:
            doc_data['active'] = True
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)

def generate_document_hash(content):
    """
    Generate a unique hash for the document content.
    """
    # Convert content to bytes if it's a string
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    return hashlib.md5(content).hexdigest()

def split_document_for_rag(text, chunk_size=1000, chunk_overlap=100):
    """
    Split document into chunks suitable for RAG processing.
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available. Please install the required dependencies.")
        return []
    
    # Check if Document class is available
    if Document is None:
        st.error("Document class is not available. Please install langchain or langchain-core.")
        return []
    
    # Check if RecursiveCharacterTextSplitter is available
    if RecursiveCharacterTextSplitter is None:
        st.error("RecursiveCharacterTextSplitter is not available. Please install langchain.")
        return []
    
    # Create a text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    )
    
    # Create an initial document
    doc = Document(page_content=text)
    
    # Split the document
    return text_splitter.split_documents([doc])

def create_vector_db_from_text(text, title, api_key, entities=None, document_tags=None, document_category=None):
    """
    Create a vector database from text content.
    
    Args:
        text: The document text to store
        title: The document title
        api_key: OpenAI API key for embeddings
        entities: Optional dictionary containing entity information for reverse anonymization
                 Note: Entity information is stored separately in document metadata,
                 not in the vector database chunks, to ensure it's not exposed to the AI agent
        document_tags: Optional list of tags for categorizing the document
        document_category: Optional category for the document (e.g., "legal", "sustainability", "policy")
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available. Please install the required dependencies.")
        return None
    
    # Check if Document class is available
    if Document is None:
        st.error("Document class is not available. Please install langchain or langchain-core.")
        return None
    
    # Check if RecursiveCharacterTextSplitter is available
    if RecursiveCharacterTextSplitter is None:
        st.error("RecursiveCharacterTextSplitter is not available. Please install langchain.")
        return None
    
    # Ensure directories exist
    ensure_rag_directories_exist()
    
    # Persistent directory configuration
    persist_directory = './chroma_db'
    
    # Create custom embedding function
    embedding_function = OpenAIEmbeddingFunction(api_key=api_key)
    
    # Configure ChromaDB client with explicit settings
    try:
        chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    except Exception as e:
        st.error(f"ChromaDB initialization error: {e}")
        # Attempt to reset and recreate the client
        try:
            shutil.rmtree(persist_directory)
            os.makedirs(persist_directory)
            chroma_client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        except Exception as reset_error:
            st.error(f"Failed to reset ChromaDB: {reset_error}")
            return None
    
    # Load existing metadata
    document_metadata = load_document_metadata(persist_directory)
    
    # Generate a hash for the document
    document_hash = generate_document_hash(text)
    
    # Create or get collection
    try:
        collection = chroma_client.get_or_create_collection(
            name="document_collection", 
            embedding_function=embedding_function
        )
    except Exception as e:
        st.error(f"Collection creation error: {e}")
        return None
    
    # Process document only if it's not already in the database
    if document_hash not in document_metadata:
        # Split document into chunks
        docs = split_document_for_rag(text)
        
        # Auto-detect document category if not provided
        if document_category is None:
            document_category = auto_detect_document_category(title, text, entities)
        
        # Auto-generate tags if not provided
        if document_tags is None:
            document_tags = auto_generate_document_tags(title, text, entities)
        
        # Prepare documents for ChromaDB with enhanced metadata
        texts = [doc.page_content for doc in docs]
        metadatas = [
            {
                'source': title,
                'chunk_id': i,
                'document_hash': document_hash,
                'document_category': document_category,
                'document_tags': ','.join(document_tags) if document_tags else ''
            } 
            for i in range(len(texts))
        ]
        
        # Add documents to the collection
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=[f"{document_hash}_{i}" for i in range(len(texts))]
        )
        
        # Add enhanced metadata for the new document
        document_metadata[document_hash] = {
            'title': title,
            'length': len(text),
            'chunks': len(texts),
            'category': document_category,
            'tags': document_tags or [],
            'timestamp': time.time(),
            'active': True
        }
        
        # Store entity information if provided
        if entities and isinstance(entities, dict):
            # Ensure entities have the expected structure
            if "Text" in entities and "Replacement" in entities and "Category" in entities:
                document_metadata[document_hash]['entities'] = entities
        
        # Save updated metadata
        save_document_metadata(persist_directory, document_metadata)
    
    return collection

def auto_detect_document_category(title, text, entities=None):
    """
    Automatically detect document category based on title, content, and entities.
    
    Args:
        title: Document title
        text: Document content
        entities: Entity information
    
    Returns:
        str: Detected category
    """
    title_lower = title.lower()
    text_sample = text[:2000].lower()  # First 2000 characters for analysis
    
    # Legal/Governance documents
    if any(keyword in title_lower for keyword in ['charter', 'constitution', 'treaty', 'agreement', 'convention', 'protocol']):
        return 'legal_governance'
    
    # Sustainability/Development documents
    if any(keyword in title_lower for keyword in ['sustainable', 'development', 'sdg', 'climate', 'environment']):
        return 'sustainability_development'
    
    # Policy documents
    if any(keyword in title_lower for keyword in ['policy', 'framework', 'strategy', 'plan', 'roadmap']):
        return 'policy_strategy'
    
    # International relations
    if any(keyword in title_lower for keyword in ['pact', 'alliance', 'cooperation', 'partnership', 'diplomatic']):
        return 'international_relations'
    
    # Check content for category hints
    if any(keyword in text_sample for keyword in ['article', 'shall', 'hereby', 'whereas', 'pursuant']):
        return 'legal_governance'
    
    if any(keyword in text_sample for keyword in ['sustainability', 'climate change', 'renewable', 'carbon', 'emissions']):
        return 'sustainability_development'
    
    # Check entities for category hints
    if entities and isinstance(entities, dict):
        categories = entities.get('Category', [])
        org_count = categories.count('ORG')
        gpe_count = categories.count('GPE')
        
        if org_count > 10 and gpe_count > 5:
            return 'international_relations'
    
    return 'general_document'

def auto_generate_document_tags(title, text, entities=None):
    """
    Automatically generate tags for a document based on its content.
    
    Args:
        title: Document title
        text: Document content
        entities: Entity information
    
    Returns:
        list: Generated tags
    """
    tags = []
    title_lower = title.lower()
    text_sample = text[:2000].lower()
    
    # Title-based tags
    title_keywords = ['un', 'united nations', 'charter', 'pact', 'sustainable', 'development', 'goals', 'sdg', 'climate', 'governance', 'international']
    for keyword in title_keywords:
        if keyword in title_lower:
            tags.append(keyword.replace(' ', '_'))
    
    # Content-based tags
    content_patterns = {
        'multilateral': ['multilateral', 'international cooperation', 'member states'],
        'environmental': ['environmental', 'climate', 'sustainability', 'green'],
        'human_rights': ['human rights', 'fundamental freedoms', 'dignity'],
        'economic': ['economic', 'trade', 'development', 'finance'],
        'security': ['security', 'peace', 'conflict', 'peacekeeping'],
        'technology': ['technology', 'digital', 'innovation', 'artificial intelligence'],
        'governance': ['governance', 'democracy', 'rule of law', 'transparency']
    }
    
    for tag, patterns in content_patterns.items():
        if any(pattern in text_sample for pattern in patterns):
            tags.append(tag)
    
    # Entity-based tags
    if entities and isinstance(entities, dict):
        categories = entities.get('Category', [])
        if categories.count('ORG') > 10:
            tags.append('organization_focused')
        if categories.count('GPE') > 5:
            tags.append('geopolitical')
        if categories.count('PERSON') > 3:
            tags.append('person_focused')
    
    # Remove duplicates and return
    return list(set(tags))

def query_vector_db(collection, query, n_results=5, selected_doc_sources=None):
    """
    Query the vector database with a user question.
    Filter by selected document sources if provided.
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available. Please install the required dependencies.")
        return [], []
    
    if collection is None:
        return [], []
    
    try:
        # First, perform the query without filters to get the best semantic matches
        unfiltered_results = collection.query(
            query_texts=[query],
            n_results=n_results * 3  # Get more results than needed to allow for filtering
        )
        
        # If no results or no document source filtering needed, return the unfiltered results
        if not unfiltered_results["documents"][0] or not selected_doc_sources:
            if unfiltered_results["documents"] and len(unfiltered_results["documents"][0]) > 0:
                # Filter out any sensitive metadata before returning
                filtered_metadatas = []
                for metadata in unfiltered_results["metadatas"][0][:n_results]:
                    # Create a clean copy with only safe fields
                    filtered_metadata = {
                        'source': metadata.get('source', 'Unknown'),
                        'chunk_id': metadata.get('chunk_id', 0)
                    }
                    filtered_metadatas.append(filtered_metadata)
                return unfiltered_results["documents"][0][:n_results], filtered_metadatas
            return [], []
        
        # If we have document sources selected, filter the results manually
        filtered_docs = []
        filtered_metadatas = []
        
        for i, doc_id in enumerate(unfiltered_results["ids"][0]):
            # Check if this document belongs to any of the selected sources
            if any(doc_hash in doc_id for doc_hash in selected_doc_sources):
                filtered_docs.append(unfiltered_results["documents"][0][i])
                # Create a clean copy with only safe fields
                metadata = unfiltered_results["metadatas"][0][i]
                filtered_metadata = {
                    'source': metadata.get('source', 'Unknown'),
                    'chunk_id': metadata.get('chunk_id', 0)
                }
                filtered_metadatas.append(filtered_metadata)
                
                # Break if we have enough results
                if len(filtered_docs) >= n_results:
                    break
        
        # Return the filtered results, or empty if no matches
        return filtered_docs, filtered_metadatas
        
    except Exception as e:
        st.error(f"Error querying vector database: {e}")
        st.error(f"Query: {query}, Selected sources: {selected_doc_sources}")
        return [], []

def generate_rag_response(client, query, context_docs, context_metadatas, model, chat_history=None):
    """
    Generate a response based on the retrieved context and query.
    """
    # Prepare source information - only use safe fields
    source_info = []
    for metadata in context_metadatas:
        # Only use the source field, which should be safe
        source = metadata.get('source', 'Unknown')
        if source not in source_info:
            source_info.append(source)
    
    # Join source information
    sources_str = ", ".join(source_info)
    
    # Concatenate relevant texts for context
    context = " ".join(context_docs)
    
    # Prepare messages for API call
    system_message = "You are a helpful assistant providing information based on the supplied document context. Answer questions accurately and cite sources when appropriate."
    
    messages = [
        {"role": "system", "content": system_message}
    ]
    
    # Add chat history for context if provided
    if chat_history:
        messages.extend(
            [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
        )
    
    # Add the current query with context - only include safe metadata
    user_message = f"Context from documents: {context}\n\nSources: {sources_str}\n\nUser Question: {query}"
    messages.append({"role": "user", "content": user_message})
    
    # Generate response
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,  # Adjust as needed for creativity vs accuracy
            max_tokens=1000   # Adjust as needed for response length
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return f"I'm sorry, I couldn't generate a response due to an error: {e}"

# Logging utility
def setup_logging():
    """
    Set up logging for the application.
    """
    import logging
    
    # Ensure logs directory exists
    os.makedirs('./logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        filename='./logs/app.log',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return logging.getLogger('combined_app')

def clear_vector_database():
    """
    Clear the vector database and its metadata.
    This removes all indexed documents from the system.
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available. No database to clear.")
        return False
    
    try:
        # Persistent directory configuration
        persist_directory = './chroma_db'
        
        # Close any existing connections in the session state
        if "vector_db" in st.session_state:
            # Force close the collection connection
            st.session_state["vector_db"] = None
            del st.session_state["vector_db"]
        
        # Explicitly run garbage collection to help release file handles
        import gc
        gc.collect()
        
        # Remove metadata file
        metadata_path = get_metadata_path(persist_directory)
        if os.path.exists(metadata_path):
            try:
                os.remove(metadata_path)
            except Exception as metadata_error:
                st.warning(f"Could not remove metadata file: {metadata_error}")
        
        # Reset ChromaDB safely
        try:
            try:
                # Try to get a client reference
                chroma_client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                # Delete the collection if it exists
                try:
                    chroma_client.delete_collection("document_collection")
                except Exception as collection_error:
                    st.warning(f"Could not delete collection: {collection_error}")
                
                # Explicitly close the client connection
                del chroma_client
                gc.collect()
            except Exception as client_error:
                st.warning(f"Could not properly close ChromaDB client: {client_error}")
            
            # Delay to allow file handles to be released
            import time
            time.sleep(1)
            
            # Try to remove the directory
            try:
                # Remove the entire ChromaDB directory and recreate it
                import shutil
                shutil.rmtree(persist_directory)
            except PermissionError as pe:
                st.warning(f"Windows file lock detected: {pe}")
                st.info("To fix this issue, please follow these steps:")
                st.info("1. Save any work you're doing")
                st.info("2. Close this application completely")
                st.info("3. Restart the application and try clearing the database again")
                
                # Add option to mark files for deletion on next startup
                if st.button("Mark for Deletion on Next Startup", key="mark_for_deletion"):
                    try:
                        # Create a marker file that will be checked on startup
                        marker_file = os.path.join(os.path.dirname(persist_directory), "delete_chroma_on_startup.txt")
                        with open(marker_file, "w") as f:
                            f.write(f"delete_requested={datetime.now().isoformat()}")
                        
                        st.success("Database marked for deletion on next startup. Please close and restart the application.")
                        
                        # Provide a restart button
                        if st.button("Restart Application Now", key="restart_app_chroma_db"):
                            st.experimental_rerun()
                            
                    except Exception as marker_error:
                        st.error(f"Could not create marker file: {marker_error}")
                        
                return False
            except Exception as rm_error:
                st.warning(f"Could not remove directory: {rm_error}")
                return False
            
            # Recreate the directory
            os.makedirs(persist_directory, exist_ok=True)
            
            return True
            
        except Exception as e:
            st.error(f"Error clearing vector database: {e}")
            return False
            
    except Exception as e:
        st.error(f"Unexpected error clearing vector database: {e}")
        return False

def check_cleanup_requests():
    """
    Check if there are any cleanup requests from previous sessions
    and handle them at startup when file locks are released.
    """
    # Path to the marker file
    marker_file = "./delete_chroma_on_startup.txt"
    
    # Check if the marker file exists
    if os.path.exists(marker_file):
        try:
            # Get the persist directory path
            persist_directory = './chroma_db'
            
            # Check if the directory exists
            if os.path.exists(persist_directory) and os.path.isdir(persist_directory):
                # Remove the entire chroma_db directory
                try:
                    shutil.rmtree(persist_directory)
                    # Recreate an empty directory
                    os.makedirs(persist_directory, exist_ok=True)
                    # Show success message
                    st.success("Vector database successfully cleared on startup as requested.")
                except Exception as e:
                    st.error(f"Failed to clear vector database on startup: {e}")
            
            # Remove the marker file regardless of success/failure
            os.remove(marker_file)
            
        except Exception as e:
            # Log the error but don't crash
            st.error(f"Error processing cleanup request: {e}")
            # Try to remove the marker file even if cleanup failed
            try:
                os.remove(marker_file)
            except:
                pass

def delete_document_from_vector_db(document_hash):
    """
    Delete a specific document from the vector database.
    
    Args:
        document_hash: Hash of the document to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available. No database to modify.")
        return False
    
    try:
        # Persistent directory configuration
        persist_directory = './chroma_db'
        
        # Close any existing connections in the session state
        reset_vector_db_connection = False
        if "vector_db" in st.session_state:
            # Store this to reconnect later
            reset_vector_db_connection = True
            # Force close the collection connection
            st.session_state["vector_db"] = None
            del st.session_state["vector_db"]
        
        # Explicitly run garbage collection to help release file handles
        import gc
        gc.collect()
        
        # Load metadata
        document_metadata = load_document_metadata(persist_directory)
        
        # Check if document exists
        if document_hash not in document_metadata:
            st.warning(f"Document with hash {document_hash} not found in metadata.")
            return False
        
        # Get document info for user feedback
        doc_title = document_metadata[document_hash].get('title', 'Unknown document')
        
        # Remove from metadata
        del document_metadata[document_hash]
        save_document_metadata(persist_directory, document_metadata)
        
        # Connect to ChromaDB to delete the document chunks
        try:
            client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get the collection
            collection = client.get_collection("document_collection")
            
            # First get all IDs that contain our document hash
            all_ids = collection.get(include=[])["ids"]
            matching_ids = [doc_id for doc_id in all_ids if document_hash in doc_id]
            
            # Delete all matched IDs
            if matching_ids:
                collection.delete(
                    ids=matching_ids
                )
            
            # Reconnect if needed
            if reset_vector_db_connection and "gpt_api_key" in st.session_state:
                # Create embedding function with current API key
                embedding_function = OpenAIEmbeddingFunction(api_key=st.session_state["gpt_api_key"])
                
                # Reconnect to the collection
                collection = client.get_collection(
                    name="document_collection", 
                    embedding_function=embedding_function
                )
                
                # Store in session state
                st.session_state.vector_db = collection
                
                # Update selected docs
                if "selected_doc_sources" in st.session_state:
                    st.session_state.selected_doc_sources = [
                        doc_hash for doc_hash in st.session_state.selected_doc_sources 
                        if doc_hash != document_hash
                    ]
            
            st.success(f"Document '{doc_title}' has been removed from the database.")
            return True
            
        except Exception as e:
            st.error(f"Error accessing ChromaDB: {e}")
            return False
        
    except Exception as e:
        st.error(f"Error deleting document: {e}")
        return False

def get_document_content_from_hash(document_hash, api_key=None):
    """
    Retrieve the original document content from the vector database using a document hash.
    
    Args:
        document_hash: The hash of the document to retrieve
        api_key: Optional OpenAI API key if needed for authentication
        
    Returns:
        tuple: (document_content, document_title, entities_data) or (None, None, None) if not found
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available. Please install the required dependencies.")
        return None, None, None
    
    # Persistent directory configuration
    persist_directory = './chroma_db'
    
    # Load document metadata
    document_metadata = load_document_metadata(persist_directory)
    
    # Check if document exists in metadata
    if document_hash not in document_metadata:
        return None, None, None
    
    # Get document title
    document_title = document_metadata[document_hash].get('title', 'Untitled Document')
    
    # Get entities data if available
    entities_data = document_metadata[document_hash].get('entities', {
        "Text": [],
        "Replacement": [],
        "Category": []
    })
    
    # Create embedding function if API key provided
    embedding_function = None
    if api_key:
        embedding_function = OpenAIEmbeddingFunction(api_key=api_key)
    
    try:
        # Connect to ChromaDB
        chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get collection
        collection_params = {"name": "document_collection"}
        if embedding_function:
            collection_params["embedding_function"] = embedding_function
            
        collection = chroma_client.get_collection(**collection_params)
        
        # Get all chunks for this document
        all_ids = collection.get(include=[])["ids"]
        matching_ids = [doc_id for doc_id in all_ids if document_hash in doc_id]
        
        if not matching_ids:
            return None, document_title, entities_data
        
        # Get all chunks
        result = collection.get(ids=matching_ids, include=["documents", "metadatas"])
        
        # Sort chunks by chunk_id if available
        sorted_chunks = []
        for i, doc_id in enumerate(result["ids"]):
            chunk_id = result["metadatas"][i].get("chunk_id", i)
            sorted_chunks.append((chunk_id, result["documents"][i]))
        
        sorted_chunks.sort(key=lambda x: x[0])
        
        # Combine chunks into a single document
        document_content = " ".join([chunk[1] for chunk in sorted_chunks])
        
        return document_content, document_title, entities_data
        
    except Exception as e:
        st.error(f"Error retrieving document content: {e}")
        return None, document_title, entities_data

def update_document_entities(document_hash, entities):
    """
    Update the entity information for a specific document in the metadata.
    
    Args:
        document_hash: The hash of the document to update
        entities: Dictionary containing entity information
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if RAG functionality is available
    if not RAG_AVAILABLE:
        st.error("RAG functionality is not available.")
        return False
    
    # Persistent directory configuration
    persist_directory = './chroma_db'
    
    try:
        # Load document metadata
        document_metadata = load_document_metadata(persist_directory)
        
        # Check if document exists in metadata
        if document_hash not in document_metadata:
            st.warning(f"Document with hash {document_hash} not found in metadata.")
            return False
        
        # Update entities in metadata
        document_metadata[document_hash]['entities'] = entities
        
        # Save updated metadata
        save_document_metadata(persist_directory, document_metadata)
        
        return True
        
    except Exception as e:
        st.error(f"Error updating document entities: {e}")
        return False

# ===== TABULAR DATA HANDLING FUNCTIONS =====

def get_delimiter(file, bytes=4096):
    """Detect CSV delimiter using csv.Sniffer with fallback"""
    import csv
    from io import StringIO
    
    try:
        sniffer = csv.Sniffer()
        # Try UTF-8 first
        try:
            stringio = StringIO(file.getvalue().decode("utf-8"))
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            stringio = StringIO(file.getvalue().decode("latin-1"))
        
        data = stringio.read(bytes)
        delimiter = sniffer.sniff(data).delimiter
        return delimiter
    except Exception:
        # If all else fails, return comma as default
        return ','

def save_tabular_metadata(title, df, file_hash):
    """
    Save metadata about tabular datasets for persistence.
    
    Args:
        title: The title/name of the dataset
        df: The pandas DataFrame
        file_hash: Unique hash for the file
    """
    import pandas as pd
    
    metadata_path = "./data_storage/tabular_metadata.json"
    
    # Create directory if it doesn't exist
    os.makedirs("./data_storage", exist_ok=True)
    
    # Debug logging to track what's being saved
    if st.session_state.get("show_debug", False):
        st.write(f"🔧 DEBUG SAVE: Saving '{title}' with hash '{file_hash}'")
        st.write(f"🔧 DEBUG SAVE: Input DataFrame shape: {df.shape}")
        st.write(f"🔧 DEBUG SAVE: Input DataFrame columns: {list(df.columns)}")
        st.write(f"🔧 DEBUG SAVE: Input DataFrame memory ID: {id(df)}")
        st.write(f"🔧 DEBUG SAVE: First few values of first column: {df.iloc[:3, 0].tolist()}")
    
    # Save DataFrame to parquet for efficient storage
    df_path = f"./data_storage/{file_hash}.parquet"
    
    # Create a copy to avoid any reference issues during save
    df_to_save = df.copy()
    df_to_save.to_parquet(df_path)
    
    # Verify what was actually saved by reading it back immediately
    if st.session_state.get("show_debug", False):
        try:
            verification_df = pd.read_parquet(df_path)
            st.write(f"🔧 DEBUG SAVE: Verification read - Shape: {verification_df.shape}")
            st.write(f"🔧 DEBUG SAVE: Verification read - Columns: {list(verification_df.columns)}")
            st.write(f"🔧 DEBUG SAVE: Verification read - First few values: {verification_df.iloc[:3, 0].tolist()}")
            
            # Check if verification matches input
            if verification_df.shape != df.shape:
                st.error(f"🚨 SAVE ERROR: Shape mismatch! Input: {df.shape}, Saved: {verification_df.shape}")
            if list(verification_df.columns) != list(df.columns):
                st.error(f"🚨 SAVE ERROR: Column mismatch! Input: {list(df.columns)}, Saved: {list(verification_df.columns)}")
        except Exception as verify_error:
            st.error(f"🚨 SAVE ERROR: Could not verify saved file: {verify_error}")
    
    # Load existing metadata
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}
    
    # Check for hash collisions
    if file_hash in metadata:
        existing_title = metadata[file_hash].get("title", "Unknown")
        if st.session_state.get("show_debug", False):
            st.warning(f"🚨 HASH COLLISION: Hash '{file_hash}' already exists for '{existing_title}'! Overwriting with '{title}'")
    
    # Add new dataset metadata
    metadata[file_hash] = {
        "title": title,
        "file_path": df_path,
        "columns": list(df.columns),
        "shape": df.shape,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "timestamp": time.time(),
        "active": True  # New datasets are active by default
    }
    
    # Save updated metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    if st.session_state.get("show_debug", False):
        st.write(f"🔧 DEBUG SAVE: Successfully saved metadata for '{title}' at {df_path}")
        st.write(f"🔧 DEBUG SAVE: Total datasets in metadata: {len(metadata)}")

def load_tabular_datasets():
    """
    Load all saved tabular datasets into session state.
    
    Returns:
        dict: Dictionary of dataset_title -> DataFrame
    """
    import pandas as pd
    
    metadata_path = "./data_storage/tabular_metadata.json"
    
    if not os.path.exists(metadata_path):
        return {}
    
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except Exception as e:
        st.warning(f"Could not load tabular metadata: {e}")
        return {}
    
    datasets = {}
    for file_hash, info in metadata.items():
        try:
            if os.path.exists(info["file_path"]):
                df = pd.read_parquet(info["file_path"])
                
                # Debug logging to verify correct data is being loaded
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG LOAD: Loading '{info['title']}' from {info['file_path']}")
                    st.write(f"🔧 DEBUG LOAD: Shape: {df.shape}")
                    st.write(f"🔧 DEBUG LOAD: Columns: {list(df.columns)}")
                    st.write(f"🔧 DEBUG LOAD: Memory ID: {id(df)}")
                
                # Create a fresh copy to avoid any reference issues
                datasets[info["title"]] = df.copy()
            else:
                st.warning(f"Dataset file not found: {info['title']}")
        except Exception as e:
            st.warning(f"Could not load dataset {info['title']}: {e}")
    
    # Additional debug info for the final datasets dictionary
    if st.session_state.get("show_debug", False):
        st.write(f"🔧 DEBUG LOAD: Final datasets dictionary keys: {list(datasets.keys())}")
        for name, df in datasets.items():
            st.write(f"🔧 DEBUG LOAD: Final '{name}' - Shape: {df.shape}, Memory ID: {id(df)}")
    
    return datasets

def get_tabular_metadata():
    """
    Get metadata about all saved tabular datasets.
    
    Returns:
        dict: Metadata dictionary
    """
    metadata_path = "./data_storage/tabular_metadata.json"
    
    if not os.path.exists(metadata_path):
        return {}
    
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Could not load tabular metadata: {e}")
        return {}

def delete_tabular_dataset(file_hash):
    """
    Delete a specific tabular dataset.
    
    Args:
        file_hash: Hash of the dataset to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    metadata_path = "./data_storage/tabular_metadata.json"
    
    try:
        # Load metadata
        if not os.path.exists(metadata_path):
            return False
            
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Check if dataset exists
        if file_hash not in metadata:
            st.warning(f"Dataset with hash {file_hash} not found.")
            return False
        
        # Get dataset info
        dataset_info = metadata[file_hash]
        dataset_title = dataset_info.get('title', 'Unknown dataset')
        
        # Remove the parquet file
        if os.path.exists(dataset_info["file_path"]):
            os.remove(dataset_info["file_path"])
        
        # Remove from metadata
        del metadata[file_hash]
        
        # Save updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Remove from session state if present
        if "tabular_datasets" in st.session_state:
            if dataset_title in st.session_state.tabular_datasets:
                del st.session_state.tabular_datasets[dataset_title]
            
            # Clean up empty session state to prevent inconsistencies
            if not st.session_state.tabular_datasets:
                # If the dictionary is empty, ensure it's properly initialized
                st.session_state.tabular_datasets = {}
        
        # Clean up related session state variables
        if "selected_datasets" in st.session_state:
            if dataset_title in st.session_state.selected_datasets:
                st.session_state.selected_datasets.remove(dataset_title)
        
        st.success(f"Dataset '{dataset_title}' has been removed.")
        return True
        
    except Exception as e:
        st.error(f"Error deleting dataset: {e}")
        return False

def clear_all_tabular_data():
    """
    Clear all tabular datasets and metadata.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Remove data storage directory
        data_storage_path = "./data_storage"
        if os.path.exists(data_storage_path):
            shutil.rmtree(data_storage_path)
        
        # Clear from session state
        if "tabular_datasets" in st.session_state:
            del st.session_state.tabular_datasets
        
        st.success("All tabular datasets have been cleared.")
        return True
        
    except Exception as e:
        st.error(f"Error clearing tabular data: {e}")
        return False

def generate_file_hash(file_content, file_name, file_type):
    """Generate a unique hash for uploaded file to enable caching"""
    # Use actual file content for hash to ensure uniqueness
    import hashlib
    
    # Create hash from file content + metadata to ensure uniqueness
    if isinstance(file_content, bytes):
        content_hash = hashlib.md5(file_content).hexdigest()
    else:
        content_hash = hashlib.md5(str(file_content).encode('utf-8')).hexdigest()
    
    # Combine content hash with metadata for extra uniqueness
    combined_str = f"{file_name}_{file_type}_{len(file_content)}_{content_hash}"
    final_hash = hashlib.md5(combined_str.encode()).hexdigest()
    
    return final_hash

# ===== TOOL DEFINITIONS FOR MULTI-MODAL AGENT =====

# Import tool decorators - wrapped in try/except for graceful degradation
TOOLS_AVAILABLE = True
try:
    from langchain.tools import tool
    from langchain.agents import AgentType, create_openai_tools_agent, AgentExecutor
    from langchain_experimental.agents import create_pandas_dataframe_agent
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
except ImportError:
    TOOLS_AVAILABLE = False
    st.warning("Tool-calling dependencies are missing. Please install langchain-experimental and langchain-openai.")

@tool
def search_documents(query: str, doc_sources: Optional[str] = None, category_filter: Optional[str] = None, tag_filter: Optional[str] = None) -> str:
    """
    Search through uploaded text documents using semantic similarity.
    
    Args:
        query: The search query to find relevant information in documents
        doc_sources: Optional comma-separated list of document titles to search in specific documents
        category_filter: Optional category to filter documents (e.g., 'legal_governance', 'sustainability_development')
        tag_filter: Optional tag to filter documents (e.g., 'un', 'climate', 'governance')
    
    Returns:
        Relevant text passages from documents with source information
    """
    if not hasattr(st.session_state, 'vector_db') or st.session_state.vector_db is None:
        return "No text documents are currently loaded in the database."
    
    try:
        # Parse doc_sources if provided, otherwise use selected checkboxes
        selected_sources = None
        if doc_sources:
            # Convert document titles to hashes if needed
            # For now, use the existing selected_doc_sources
            selected_sources = st.session_state.get("selected_doc_sources", [])
        else:
            # Use the checkbox selections from Data Sources Management
            selected_sources = st.session_state.get("selected_doc_sources", [])
            # If no specific selection exists, use all available documents
            if not selected_sources:
                persist_directory = './chroma_db'
                document_metadata = load_document_metadata(persist_directory)
                if document_metadata:
                    selected_sources = list(document_metadata.keys())
        
        # Query the vector database
        context_docs, context_metadatas = query_vector_db(
            st.session_state.vector_db, 
            query,
            n_results=5,
            selected_doc_sources=selected_sources
        )
        
        if not context_docs:
            # Check if filtering might be the issue
            if selected_sources:
                persist_directory = './chroma_db'
                document_metadata = load_document_metadata(persist_directory)
                total_docs = len(document_metadata) if document_metadata else 0
                active_docs = len(selected_sources)
                
                if active_docs < total_docs:
                    return f"No relevant information found in the {active_docs} selected document(s) for query: '{query}'. Note: {total_docs - active_docs} document(s) are currently inactive and not being searched. You can change document selection in Data Sources Management."
                else:
                    return f"No relevant information found in documents for query: '{query}'"
            else:
                return f"No relevant information found in documents for query: '{query}'"
        
        # Format results for the LLM
        result = f"Found {len(context_docs)} relevant passages for '{query}'"
        
        # Add filtering information if applicable
        if selected_sources:
            persist_directory = './chroma_db'
            document_metadata = load_document_metadata(persist_directory)
            total_docs = len(document_metadata) if document_metadata else 0
            active_docs = len(selected_sources)
            
            if active_docs < total_docs:
                result += f" (searched {active_docs} of {total_docs} available documents)"
            elif active_docs == total_docs:
                result += f" (searched all {total_docs} documents)"
        
        result += ":\n\n"
        
        for i, (doc, metadata) in enumerate(zip(context_docs, context_metadatas)):
            source = metadata.get('source', 'Unknown Document')
            result += f"[Source: {source}]\n{doc}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error searching documents: {str(e)}"

@tool
def analyze_tabular_data(query: str, dataset_name: Optional[str] = None) -> str:
    """
    Perform analysis on uploaded CSV/Excel data using natural language queries.
    
    Args:
        query: Natural language query about the data (e.g., "show top 5 countries by funding received", "calculate average program effectiveness")
        dataset_name: Optional specific dataset name to analyze (if not provided, uses the first available dataset)
    
    Returns:
        Analysis results including statistics, trends, or specific data points
    """
    # Get selected datasets based on checkbox selection
    available_datasets = get_selected_tabular_datasets()
    
    if not available_datasets:
        # Check if there are datasets but none selected
        all_datasets = st.session_state.get("tabular_datasets", {})
        if all_datasets:
            selected_count = len(st.session_state.get("selected_datasets", []))
            total_count = len(all_datasets)
            return f"No datasets are currently selected for analysis. {total_count - selected_count} of {total_count} datasets are inactive. You can change dataset selection in Data Sources Management."
        else:
            return "No tabular datasets are currently loaded. Please upload a CSV or Excel file first."
    
    try:
        # Select dataset
        if dataset_name and dataset_name in available_datasets:
            df = available_datasets[dataset_name]
            dataset_info = f"Analyzing dataset: {dataset_name}"
        else:
            # Use first available dataset
            dataset_name = list(available_datasets.keys())[0]
            df = available_datasets[dataset_name]
            dataset_info = f"Analyzing dataset: {dataset_name}"
        
        # Create pandas agent for this specific query
        if not TOOLS_AVAILABLE:
            return "Pandas agent functionality is not available. Please install required dependencies."
        
        llm = ChatOpenAI(
            temperature=0, 
            model=st.session_state.get("openai_model", "gpt-3.5-turbo"), 
            api_key=st.session_state["gpt_api_key"]
        )
        
        agent = create_pandas_dataframe_agent(
            llm,
            df,
            verbose=False,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True
        )
        
        # Execute the query
        result = agent.invoke(query)
        
        # Add filtering information
        result_text = f"{dataset_info}"
        
        # Check if filtering is active
        all_datasets = st.session_state.get("tabular_datasets", {})
        selected_datasets = get_selected_tabular_datasets()
        
        if len(selected_datasets) < len(all_datasets):
            result_text += f" (using {len(selected_datasets)} of {len(all_datasets)} available datasets)"
        elif len(selected_datasets) == len(all_datasets) and len(all_datasets) > 1:
            result_text += f" (using all {len(all_datasets)} datasets)"
        
        result_text += f"\n\nQuery: {query}\n\nResult:\n{result['output']}"
        return result_text
        
    except Exception as e:
        return f"Error analyzing data: {str(e)}"

@tool
def cross_reference_analysis(document_query: str, data_query: str) -> str:
    """
    Find connections between document content and tabular data by analyzing both sources.
    
    Args:
        document_query: What to search for in the text documents
        data_query: What to analyze in the tabular data
    
    Returns:
        Combined insights showing connections between text and data sources
    """
    try:
        # Get document insights
        doc_results = search_documents(document_query)
        
        # Get data insights  
        data_results = analyze_tabular_data(data_query)
        
        # Check if we got valid results from both sources
        if "No relevant information found" in doc_results and "No tabular datasets" in data_results:
            return "No data sources available for cross-reference analysis."
        elif "No relevant information found" in doc_results:
            return f"Could not find relevant information in documents for '{document_query}', but here's the data analysis:\n\n{data_results}"
        elif "No tabular datasets" in data_results:
            return f"No tabular data available for analysis, but here's what I found in documents:\n\n{doc_results}"
        
        # Combine the results
        combined_analysis = f"""
CROSS-REFERENCE ANALYSIS

Document Analysis for '{document_query}':
{doc_results}

Data Analysis for '{data_query}':
{data_results}

SYNTHESIS:
Based on the document content and data analysis above, here are the key connections and insights:
- The documents provide context and qualitative insights
- The data provides quantitative evidence and trends
- Together, they offer a comprehensive view of the topic
"""
        
        return combined_analysis
        
    except Exception as e:
        return f"Error performing cross-reference analysis: {str(e)}"

@tool
def get_data_summary(dataset_name: Optional[str] = None) -> str:
    """
    Get a summary overview of the available tabular datasets including column information and basic statistics.
    
    Args:
        dataset_name: Optional specific dataset name to summarize (if not provided, summarizes all datasets)
    
    Returns:
        Summary information about the dataset(s) including columns, data types, and basic statistics
    """
    available_datasets = get_selected_tabular_datasets()
    
    if not available_datasets:
        # Check if there are datasets but none selected
        all_datasets = st.session_state.get("tabular_datasets", {})
        if all_datasets:
            selected_count = len(st.session_state.get("selected_datasets", []))
            total_count = len(all_datasets)
            return f"No datasets are currently selected for summary. {total_count - selected_count} of {total_count} datasets are inactive. You can change dataset selection in Data Sources Management."
        else:
            return "No tabular datasets are currently loaded."
    
    try:
        if dataset_name and dataset_name in available_datasets:
            # Summarize specific dataset
            df = available_datasets[dataset_name]
            summary = f"Dataset: {dataset_name}\n"
            summary += f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n\n"
            summary += f"Columns:\n"
            for col in df.columns:
                summary += f"- {col} ({df[col].dtype})\n"
            summary += f"\nBasic Statistics:\n{df.describe()}"
            return summary
        else:
            # Summarize all datasets
            summary = f"Available Datasets ({len(available_datasets)}):\n\n"
            for name, df in available_datasets.items():
                summary += f"• {name}: {df.shape[0]} rows, {df.shape[1]} columns\n"
                summary += f"  Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}\n\n"
            return summary
            
    except Exception as e:
        return f"Error getting data summary: {str(e)}"

@tool
def create_visualization(chart_type: str, dataset_name: Optional[str] = None, x_column: Optional[str] = None, y_column: Optional[str] = None, title: Optional[str] = None, use_different_colors: Optional[bool] = True) -> str:
    """
    Create charts and visualizations from tabular data.
    
    Args:
        chart_type: Type of chart to create (bar, line, scatter, histogram, pie, heatmap, box)
        dataset_name: Name of the dataset to visualize (if not provided, uses first available)
        x_column: Column name for x-axis (required for most chart types)
        y_column: Column name for y-axis (required for some chart types)
        title: Optional title for the chart
        use_different_colors: Whether to use different colors for each category (default True for better visualization)
    
    Returns:
        Status message about chart creation
    """
    if not VISUALIZATION_AVAILABLE:
        return "Visualization libraries are not available. Please install matplotlib, seaborn, and plotly."
    
    available_datasets = get_selected_tabular_datasets()
    
    if not available_datasets:
        # Check if there are datasets but none selected
        all_datasets = st.session_state.get("tabular_datasets", {})
        if all_datasets:
            selected_count = len(st.session_state.get("selected_datasets", []))
            total_count = len(all_datasets)
            return f"No datasets are currently selected for visualization. {total_count - selected_count} of {total_count} datasets are inactive. You can change dataset selection in Data Sources Management."
        else:
            return "No tabular datasets are currently loaded."
    
    try:
        import pandas as pd
        
        # Debug: Log function entry
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Creating {chart_type} chart")
            st.write(f"🔧 DEBUG: Available datasets: {list(available_datasets.keys())}")
        
        # Select dataset
        if dataset_name and dataset_name in available_datasets:
            df = available_datasets[dataset_name]
        else:
            dataset_name = list(available_datasets.keys())[0]
            df = available_datasets[dataset_name]
        
        # Make a copy to avoid modifying the original dataset
        df = df.copy()
        
        # Debug: Log dataset info
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Using dataset '{dataset_name}' with shape {df.shape}")
            st.write(f"🔧 DEBUG: Columns: {list(df.columns)}")
            st.write(f"🔧 DEBUG: Column dtypes: {dict(df.dtypes)}")
        
        # DATA TYPE CONVERSION FIX - Convert object columns that contain numbers to numeric
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to convert to numeric if possible
                try:
                    # Check if it's mostly numeric (allows for some missing values)
                    numeric_converted = pd.to_numeric(df[col], errors='coerce')
                    non_null_count = numeric_converted.notna().sum()
                    total_count = len(df[col])
                    
                    # If more than 70% of values can be converted to numeric, do the conversion
                    if non_null_count / total_count > 0.7:
                        df[col] = numeric_converted
                        if st.session_state.get("show_debug", False):
                            st.write(f"🔧 DEBUG: Converted column '{col}' from object to numeric")
                except:
                    # If conversion fails, keep as is
                    pass
        
        # Set default title
        if not title:
            title = f"{chart_type.title()} Chart - {dataset_name}"
        
        # Validate chart requirements and prepare data
        chart_data = None
        
        if chart_type.lower() == "bar":
            if not x_column:
                return "Bar chart requires at least x_column parameter."
            
            if y_column:
                # Standard bar chart with both x and y columns
                chart_data = df[[x_column, y_column]].copy()
            else:
                # Categorical bar chart - create counts automatically
                chart_data = df[x_column].value_counts().reset_index()
                chart_data.columns = [x_column, 'count']
                y_column = 'count'  # Set y_column for bar chart
            
        elif chart_type.lower() == "line":
            if not x_column or not y_column:
                return "Line chart requires both x_column and y_column parameters."
            chart_data = df[[x_column, y_column]].copy()
            # For time series data, aggregate by x-axis (typically years) to avoid sawtooth patterns
            chart_data = chart_data.groupby(x_column)[y_column].sum().reset_index()
            # Sort by x-axis for proper time series line display
            chart_data = chart_data.sort_values(by=x_column)
            
        elif chart_type.lower() == "scatter":
            if not x_column or not y_column:
                return "Scatter plot requires both x_column and y_column parameters."
            chart_data = df[[x_column, y_column]].copy()
            
        elif chart_type.lower() == "histogram":
            if not x_column:
                return "Histogram requires x_column parameter."
            chart_data = df[[x_column]].copy()
            
        elif chart_type.lower() == "pie":
            if not x_column:
                return "Pie chart requires x_column parameter for categories."
            # For pie charts, we need to aggregate data if y_column is provided
            if y_column:
                chart_data = df.groupby(x_column)[y_column].sum().reset_index()
            else:
                # Use value counts for categorical data
                chart_data = df[x_column].value_counts().reset_index()
                chart_data.columns = [x_column, 'count']
                y_column = 'count'  # Set y_column for pie chart
            
        elif chart_type.lower() == "box":
            if not y_column:
                return "Box plot requires y_column parameter."
            if x_column:
                chart_data = df[[x_column, y_column]].copy()
            else:
                chart_data = df[[y_column]].copy()
            
        elif chart_type.lower() == "heatmap":
            # Create correlation heatmap for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) < 2:
                return "Heatmap requires at least 2 numeric columns."
            chart_data = df[numeric_cols].corr()
            
        else:
            return f"Unsupported chart type: {chart_type}. Supported types: bar, line, scatter, histogram, pie, box, heatmap"
        
        # ADDITIONAL DATA VALIDATION - Check for empty or invalid data
        if chart_data is None or chart_data.empty:
            return f"Error: No valid data found for creating {chart_type} chart. Please check your column names and data."
        
        # For numeric charts, ensure we have valid numeric data
        if chart_type.lower() in ["bar", "line", "scatter", "box"] and y_column:
            if y_column in chart_data.columns:
                # Check if y_column has valid numeric data
                if chart_data[y_column].dtype == 'object':
                    # Try one more conversion attempt
                    chart_data[y_column] = pd.to_numeric(chart_data[y_column], errors='coerce')
                
                # Check for all NaN values after conversion
                if chart_data[y_column].isna().all():
                    return f"Error: Column '{y_column}' contains no valid numeric data for {chart_type} chart."
                
                # Remove rows with NaN values in y_column
                chart_data = chart_data.dropna(subset=[y_column])
                
                if chart_data.empty:
                    return f"Error: No valid data rows remaining after cleaning for {chart_type} chart."
        
        # Debug: Log chart data info
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Chart data shape: {chart_data.shape}")
            st.write(f"🔧 DEBUG: Chart data columns: {list(chart_data.columns)}")
            st.write(f"🔧 DEBUG: Chart data dtypes: {dict(chart_data.dtypes)}")
            if y_column and y_column in chart_data.columns:
                st.write(f"🔧 DEBUG: Y-column '{y_column}' sample values: {chart_data[y_column].head().tolist()}")
        
        # Initialize charts storage if it doesn't exist
        if "stored_charts" not in st.session_state:
            st.session_state.stored_charts = {}
        
        # Generate a unique chart ID that includes timestamp and counter to avoid collisions
        import time
        base_chart_id = f"chart_{len(st.session_state.get('messages', []))}"
        
        # Check if this chart ID already exists, if so add a counter
        counter = 0
        chart_id = base_chart_id
        while chart_id in st.session_state.stored_charts:
            counter += 1
            chart_id = f"{base_chart_id}_{counter}"
        
        # Store chart configuration instead of the figure object
        chart_config = {
            "chart_type": chart_type.lower(),
            "dataset_name": dataset_name,
            "x_column": x_column,
            "y_column": y_column,
            "title": title,
            "use_different_colors": use_different_colors,
            "data": chart_data.to_dict('records') if hasattr(chart_data, 'to_dict') else chart_data.to_dict(),
            "columns": list(chart_data.columns) if hasattr(chart_data, 'columns') else None,
            # Add styling configuration to reduce rendering artifacts
            "styling": {
                "remove_borders": True,
                "clean_background": True,
                "anti_aliasing_fix": True
            }
        }
        
        # Debug: Log chart config
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Chart ID: {chart_id}")
            st.write(f"🔧 DEBUG: Chart config keys: {list(chart_config.keys())}")
            st.write(f"🔧 DEBUG: Data type: {type(chart_config['data'])}")
        
        # Store the chart configuration
        st.session_state.stored_charts[chart_id] = chart_config
        
        # Store multiple chart IDs for this response
        if "current_chart_ids" not in st.session_state:
            st.session_state.current_chart_ids = []
        st.session_state.current_chart_ids.append(chart_id)
        
        # Also keep the old current_chart_id for backwards compatibility
        st.session_state.current_chart_id = chart_id
        
        # Create a descriptive message about the chart with the chart ID embedded
        chart_description = f"**{chart_type.title()} Chart Created: {title}**\n\n"
        chart_description += f"**Dataset:** {dataset_name}\n"
        if x_column:
            chart_description += f"**X-axis:** {x_column}\n"
        if y_column:
            chart_description += f"**Y-axis:** {y_column}\n"
        chart_description += f"**Chart Type:** {chart_type.title()}\n"
        chart_description += f"**Data Points:** {len(chart_data)} rows\n"
        
        # Add color information for relevant chart types
        if chart_type.lower() in ["bar", "pie"] and use_different_colors:
            unique_categories = len(chart_data[x_column].unique()) if x_column in chart_data.columns else 0
            chart_description += f"**Colors:** Each {x_column} category has a distinct color ({unique_categories} different colors)\n"
        
        chart_description += f"\n[CHART_ID:{chart_id}]"  # Hidden marker for chart identification
        
        return chart_description
        
    except Exception as e:
        error_msg = f"Error creating visualization: {str(e)}"
        if st.session_state.get("show_debug", False):
            import traceback
            st.write(f"🔧 DEBUG: Full error traceback:")
            st.code(traceback.format_exc())
        return error_msg

def recreate_chart_from_config(chart_config):
    """
    Recreate a Plotly chart from stored configuration data.
    
    Args:
        chart_config: Dictionary containing chart configuration
        
    Returns:
        Plotly figure object or None if recreation fails
    """
    try:
        import pandas as pd
        
        # Debug: Log recreation attempt
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Recreating chart from config")
            st.write(f"🔧 DEBUG: Config keys: {list(chart_config.keys()) if chart_config else 'None'}")
        
        # Validate chart config
        if not chart_config or not isinstance(chart_config, dict):
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: Invalid chart config: {chart_config}")
            return None
            
        # Extract configuration
        chart_type = chart_config.get("chart_type")
        title = chart_config.get("title", "Chart")
        x_column = chart_config.get("x_column")
        y_column = chart_config.get("y_column")
        use_different_colors = chart_config.get("use_different_colors", True)
        data = chart_config.get("data")
        columns = chart_config.get("columns")
        
        # Debug: Log extracted config
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Chart type: {chart_type}")
            st.write(f"🔧 DEBUG: X column: {x_column}")
            st.write(f"🔧 DEBUG: Y column: {y_column}")
            st.write(f"🔧 DEBUG: Data type: {type(data)}")
            st.write(f"🔧 DEBUG: Columns: {columns}")
        
        if not chart_type or not data:
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: Missing chart_type or data")
            return None
        
        # Recreate DataFrame from stored data
        try:
            if columns and isinstance(data, list):
                # Regular DataFrame from records
                df = pd.DataFrame(data)
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: Created DataFrame from records, shape: {df.shape}")
            elif isinstance(data, dict):
                # For correlation matrices (heatmaps) or other dict-based data
                df = pd.DataFrame(data)
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: Created DataFrame from dict, shape: {df.shape}")
            else:
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: Unsupported data format")
                return None
        except Exception as df_error:
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: DataFrame creation error: {df_error}")
            st.error(f"Error recreating DataFrame: {df_error}")
            return None
        
        # DATA TYPE CONVERSION FIX FOR RECREATION - Ensure numeric columns are properly typed
        if chart_type != "heatmap":  # Heatmap already has proper correlation data
            for col in df.columns:
                if col == y_column and y_column:
                    # Ensure y_column is numeric for numerical charts
                    if chart_type in ["bar", "line", "scatter", "box", "pie"]:
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            if st.session_state.get("show_debug", False):
                                st.write(f"🔧 DEBUG: Converted '{col}' to numeric for chart recreation")
                        except:
                            pass
        
        # Debug: Log DataFrame info after conversion
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: DataFrame dtypes after conversion: {dict(df.dtypes)}")
            if y_column and y_column in df.columns:
                st.write(f"🔧 DEBUG: Y-column '{y_column}' sample values: {df[y_column].head().tolist()}")
        
        # Validate that required columns exist
        if chart_type in ["bar", "line", "scatter"] and (not x_column or not y_column):
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: Missing required columns for {chart_type}")
            return None
        if chart_type in ["histogram", "pie"] and not x_column:
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: Missing x_column for {chart_type}")
            return None
        if chart_type == "box" and not y_column:
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: Missing y_column for box plot")
            return None
            
        # Check if required columns exist in the DataFrame
        if chart_type != "heatmap":  # Heatmap uses correlation matrix, different structure
            if x_column and x_column not in df.columns:
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: x_column '{x_column}' not in DataFrame columns: {list(df.columns)}")
                return None
            if y_column and y_column not in df.columns:
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: y_column '{y_column}' not in DataFrame columns: {list(df.columns)}")
                return None
        
        # ADDITIONAL VALIDATION - Check for valid data before plotting
        if chart_type in ["bar", "line", "scatter", "box", "pie"] and y_column:
            if df[y_column].isna().all():
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: All values in y_column '{y_column}' are NaN")
                return None
            
            # Remove NaN values
            df_clean = df.dropna(subset=[y_column])
            if df_clean.empty:
                if st.session_state.get("show_debug", False):
                    st.write(f"🔧 DEBUG: No valid data after removing NaN values")
                return None
            df = df_clean
        
        # Debug: Log before chart creation
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: About to create {chart_type} chart")
            st.write(f"🔧 DEBUG: Final DataFrame shape: {df.shape}")
        
        # Recreate the chart based on type with improved styling to reduce artifacts
        if chart_type == "bar":
            # Create bar chart with conditional coloring based on user preference
            if use_different_colors:
                # Use expanded qualitative color palette for truly different colors
                # Combine multiple color palettes to ensure enough distinct colors
                color_palette = (px.colors.qualitative.Set3 + 
                               px.colors.qualitative.Pastel + 
                               px.colors.qualitative.Set2)
                fig = px.bar(df, x=x_column, y=y_column, title=title, 
                           color=x_column, color_discrete_sequence=color_palette)
            else:
                fig = px.bar(df, x=x_column, y=y_column, title=title)
            
            # Apply aggressive styling to eliminate horizontal stripes and artifacts
            fig.update_traces(
                marker=dict(
                    line=dict(width=0, color='rgba(0,0,0,0)'),  # Completely remove borders
                    opacity=1.0,  # Ensure full opacity
                ),
                text=None,  # Remove text labels completely
                texttemplate=None,  # Remove text template
                selector=dict(type='bar')
            )
            
            # Apply additional anti-aliasing fixes to reduce horizontal stripes
            fig.update_layout(
                {
                    'font': {'size': 12, 'color': 'black'},
                    'template': 'plotly_white',  # Use clean white template
                }
            )
            
            # Update layout for cleaner appearance and stripe elimination
            fig.update_layout(
                plot_bgcolor='rgba(255,255,255,1)',  # Pure white background
                paper_bgcolor='rgba(255,255,255,1)',  # Pure white paper background
                font=dict(size=12, color='black'),  # Consistent font
                showlegend=False,  # Remove legend to reduce clutter
                margin=dict(t=80, b=60, l=60, r=60),  # Better margins
                xaxis=dict(
                    gridcolor='rgba(240,240,240,0.8)',  # Very light grid lines
                    showline=True,
                    linecolor='rgba(0,0,0,0.8)',
                    linewidth=1,
                    zeroline=False,
                    showgrid=True
                ),
                yaxis=dict(
                    gridcolor='rgba(240,240,240,0.8)',  # Very light grid lines
                    showline=True,
                    linecolor='rgba(0,0,0,0.8)',
                    linewidth=1,
                    zeroline=False,
                    showgrid=True
                ),
                # Additional anti-aliasing and rendering improvements
                hovermode='closest',
                dragmode=False
            )
            
            # Force sharp rendering to reduce anti-aliasing artifacts
            fig.update_layout(
                {
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white'
                }
            )
        elif chart_type == "line":
            # For line charts with time series data, aggregate and sort for proper display
            df_aggregated = df.groupby(x_column)[y_column].sum().reset_index()
            df_sorted = df_aggregated.sort_values(by=x_column)
            fig = px.line(df_sorted, x=x_column, y=y_column, title=title)
            # Ensure markers are visible for individual data points
            fig.update_traces(mode='lines+markers', line=dict(width=3))
            # Apply clean styling
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                margin=dict(t=60, b=60, l=60, r=60),
                xaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black'),
                yaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black')
            )
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_column, y=y_column, title=title)
            fig.update_traces(marker=dict(size=8, opacity=0.8))
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                margin=dict(t=60, b=60, l=60, r=60),
                xaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black'),
                yaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black')
            )
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_column, title=title)
            fig.update_traces(marker=dict(line=dict(width=0), opacity=0.8))
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                margin=dict(t=60, b=60, l=60, r=60),
                xaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black'),
                yaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black')
            )
        elif chart_type == "pie":
            fig = px.pie(df, values=y_column, names=x_column, title=title)
            fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(width=1, color='white')))
            fig.update_layout(
                paper_bgcolor='white',
                font=dict(size=12),
                margin=dict(t=60, b=60, l=60, r=60)
            )
        elif chart_type == "box":
            if x_column and x_column in df.columns:
                fig = px.box(df, x=x_column, y=y_column, title=title)
            else:
                fig = px.box(df, y=y_column, title=title)
            fig.update_traces(marker=dict(opacity=0.8), line=dict(width=2))
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                margin=dict(t=60, b=60, l=60, r=60),
                xaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black'),
                yaxis=dict(gridcolor='rgba(200,200,200,0.5)', showline=True, linecolor='black')
            )
        elif chart_type == "heatmap":
            fig = px.imshow(df, text_auto=True, title=title)
            fig.update_layout(
                paper_bgcolor='white',
                font=dict(size=12),
                margin=dict(t=60, b=60, l=60, r=60)
            )
        else:
            if st.session_state.get("show_debug", False):
                st.write(f"🔧 DEBUG: Unsupported chart type: {chart_type}")
            return None
        
        # Debug: Log successful creation
        if st.session_state.get("show_debug", False):
            st.write(f"🔧 DEBUG: Chart created successfully!")
            st.write(f"🔧 DEBUG: Figure type: {type(fig)}")
            
        return fig
        
    except Exception as e:
        # Show error in debug mode or always for debugging this issue
        error_msg = f"Error recreating chart: {e}"
        if st.session_state.get("show_debug", False):
            import traceback
            st.write(f"🔧 DEBUG: Chart recreation error: {error_msg}")
            st.code(traceback.format_exc())
        else:
            st.error(error_msg)  # Show error even without debug mode for now
        return None

def get_recent_conversation_context(messages, last_n=6):
    """
    Get recent conversation context for the agent, excluding the current message.
    
    Args:
        messages: List of chat messages from st.session_state.messages
        last_n: Number of recent messages to include (default 6 = 3 exchanges)
    
    Returns:
        List of message tuples for ChatPromptTemplate
    """
    if not messages or len(messages) == 0:
        return []
    
    # Get the last N messages, but ensure we have complete user-assistant pairs
    recent_messages = messages[-last_n:] if len(messages) >= last_n else messages
    
    # Convert to ChatPromptTemplate format and filter out chart IDs for cleaner context
    context_messages = []
    for msg in recent_messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        # Clean up content by removing chart IDs for cleaner context
        import re
        clean_content = re.sub(r'\[CHART_ID:chart_\d+(?:_\d+)?\]', '', content).strip()
        
        # Only include non-empty messages
        if clean_content and role in ["user", "assistant"]:
            context_messages.append((role, clean_content))
    
    return context_messages

def create_unified_agent():
    """
    Create a unified agent that can work with both text documents and tabular data.
    Now includes recent conversation history for better contextual understanding.
    
    Returns:
        AgentExecutor: The configured agent executor
    """
    if not TOOLS_AVAILABLE:
        st.error("Tool-calling functionality is not available. Please install required dependencies.")
        return None
    
    # Define all available tools
    tools = [
        get_document_sources,
        get_active_sources_summary,
        search_documents,
        analyze_tabular_data,
        cross_reference_analysis,
        get_data_summary,
        create_visualization
    ]
    
    # Count available data sources
    num_documents = len(st.session_state.get('selected_doc_sources', []))
    num_datasets = len(st.session_state.get('tabular_datasets', {}))
    
    # Get recent conversation context for better continuity
    conversation_context = get_recent_conversation_context(
        st.session_state.get('messages', []), 
        last_n=6  # Include last 6 messages (3 exchanges) for context
    )
    
    # Build the prompt messages list
    prompt_messages = [
        ("system", f"""You are an intelligent assistant that can analyze both text documents and tabular data.

Available capabilities:
- get_document_sources: Get detailed information about all available text documents with titles and metadata
- search_documents: Find information in uploaded text documents (PDFs, DOCX, transcripts, etc.)
- analyze_tabular_data: Perform analysis on CSV/Excel data using pandas operations
- cross_reference_analysis: Find connections between documents and data
- get_data_summary: Get overview information about available datasets
- create_visualization: Generate charts and graphs from tabular data (bar, line, scatter, histogram, pie, box, heatmap)

Current session contains:
- Text Documents: {num_documents} documents available for search
- Tabular Datasets: {num_datasets} datasets available for analysis

CRITICAL DATA SOURCE PRIORITY RULES:
When users ask ANY question that could relate to uploaded content, you MUST:
1. **ALWAYS use tools first** - Never provide generic answers when data sources exist
2. **For ANY analysis request** (reports, summaries, insights, action items): Use search_documents or analyze_tabular_data
3. **For meeting reports, summaries, or content analysis**: ALWAYS search uploaded documents first
4. **For data questions or charts**: ALWAYS check tabular datasets first
5. **NO GENERIC RESPONSES** - If users have uploaded content, base answers ONLY on that content
6. **If no relevant content found** in tools, then explain what you searched and offer general guidance

Example correct behavior:
- User asks: "Create a meeting report" → MUST use search_documents to find meeting content
- User asks: "Show me trends" → MUST use analyze_tabular_data or get_data_summary
- User asks: "What are the key insights?" → MUST search available sources first

CONVERSATION CONTINUITY:
You have access to recent conversation history above. Use this context to:
- Understand references like "that document", "the previous analysis", "add takeaways"
- Build upon previous responses when users ask follow-up questions
- Maintain continuity when users ask for additions or modifications to previous work
- Reference specific results, charts, or findings from earlier in the conversation

CRITICAL EFFICIENCY GUIDELINES:
1. MINIMIZE tool calls - aim for 1-3 tool calls maximum per response
2. For chart requests: go DIRECTLY to create_visualization if you know the dataset exists
3. For data questions: use analyze_tabular_data DIRECTLY without calling get_data_summary first
4. For document questions: use search_documents DIRECTLY
5. Only use get_data_summary if you truly need to understand data structure first
6. Avoid redundant tool calls - each tool call should add unique value
7. If you're approaching iteration limits, provide the best answer you can with available information

VISUALIZATION BEST PRACTICES:
- For categorical data (like SEX, GRADE, ORGANIZATION): Use bar charts with only x_column (counts will be created automatically), or pie charts
- For numeric trends over time: Use line charts with time on x-axis and numeric values on y-axis
- For numeric comparisons: Use bar charts with category on x-axis and numeric values on y-axis
- For distributions: Use histograms for single variables, box plots for distributions by category
- For correlations: Use scatter plots or heatmaps
- When creating multiple charts, make each chart call separately to ensure all charts are displayed
- COLORS: By default, bar charts and pie charts will use different colors for each category automatically (use_different_colors=True is default)
- When users request "different colors" or "distinct colors" for categories, the system will automatically provide this

TOOL SELECTION STRATEGY:
- Document availability questions → get_document_sources (first to understand what's available)
- Chart/visualization requests → create_visualization (direct, multiple calls for multiple charts)
- Data analysis questions → analyze_tabular_data (direct)
- Document content questions → search_documents (direct, but use get_document_sources first if user needs overview)
- Questions needing both → cross_reference_analysis (single call)
- Data structure questions → get_data_summary (only when necessary)

IMPORTANT OUTPUT FORMATTING RULES:
- NEVER use markdown image syntax ![alt](url) in your responses
- DO NOT attempt to include icons, images, or visual elements in bullet points
- DO NOT generate any markdown that tries to display external images
- Focus on text-based descriptions and let the create_visualization tool handle all visual content
- When describing charts, use plain text descriptions without attempting to embed visual elements

When users ask questions:
1. **ALWAYS check data sources first** - Use tools before providing any analysis
2. Choose the MOST DIRECT tool approach - avoid multi-step processes
3. For multiple charts, call create_visualization once for EACH chart separately
4. Provide comprehensive answers that combine insights from all relevant sources
5. Always cite your sources and be specific about which documents or datasets you're referencing
6. If you hit iteration limits, summarize what you've found so far and suggest the user ask more specific questions
7. Use clear, text-only formatting - no visual elements or image references in your text responses
8. USE CONVERSATION HISTORY to understand context and provide relevant follow-up responses
9. **If tools return no relevant content**, explain what you searched and provide guidance for better queries
""")
    ]
    
    # Add conversation context if available
    if conversation_context:
        prompt_messages.extend(conversation_context)
    
    # Add the current input and agent scratchpad
    prompt_messages.extend([
        ("user", "{input}"),
        ("assistant", "{agent_scratchpad}")
    ])
    
    # Create the prompt template with conversation history
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    # Create the LLM
    llm = ChatOpenAI(
        temperature=0,
        model=st.session_state.get("openai_model", "gpt-3.5-turbo"),
        api_key=st.session_state["gpt_api_key"]
    )
    
    # Create the agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Create agent executor with conditional verbose mode
    # Only show verbose output in terminal if debug mode is enabled
    debug_mode = st.session_state.get("show_debug", False)
    max_iterations = st.session_state.get("max_iterations", 10)  # Get from session state or default to 10
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools,
        verbose=debug_mode,  # Only verbose in terminal when debug is on
        handle_parsing_errors=True,
        max_iterations=max_iterations,  # Use configurable value
        return_intermediate_steps=True,  # Capture steps for UI display
        early_stopping_method="generate"  # Return partial results instead of error when max iterations reached
    )
    
    return agent_executor

# ===== PHASE 1 CONTEXT OPTIMIZATION FUNCTIONS =====

def truncate_tool_output(output_text, max_length=1000):
    """
    Truncate long tool outputs to save context space while preserving key information.
    
    Args:
        output_text: The tool output string to truncate
        max_length: Maximum allowed length for the output
    
    Returns:
        Truncated output with summary information
    """
    if not output_text or len(str(output_text)) <= max_length:
        return str(output_text)
    
    truncated = str(output_text)[:max_length]
    
    # Try to cut at a complete sentence or line break
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    
    if last_period > max_length * 0.8:  # If we can cut at a sentence without losing too much
        truncated = truncated[:last_period + 1]
    elif last_newline > max_length * 0.7:  # If we can cut at a line break
        truncated = truncated[:last_newline]
    
    original_length = len(str(output_text))
    truncated_chars = original_length - len(truncated)
    
    summary = f"\n\n[📊 **Tool Output Summary**: Showing {len(truncated):,} of {original_length:,} characters. {truncated_chars:,} characters truncated to save context space.]"
    
    return truncated + summary

def manage_context_window(messages, max_context_messages=20, preserve_recent=10):
    """
    Manage context window by keeping recent messages and summarizing older ones.
    
    Args:
        messages: List of chat messages
        max_context_messages: Maximum number of messages to keep in full
        preserve_recent: Number of recent messages to always preserve
    
    Returns:
        Optimized message list with context management
    """
    if len(messages) <= max_context_messages:
        return messages
    
    # Always preserve system message if it exists
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
    
    # If we have fewer non-system messages than max, return all
    if len(non_system_messages) <= max_context_messages:
        return messages
    
    # Keep the most recent messages
    recent_messages = non_system_messages[-preserve_recent:]
    
    # Summarize older messages if there are any
    older_messages = non_system_messages[:-preserve_recent]
    
    if older_messages:
        # Create a summary of older conversation
        summary_content = "Previous conversation summary:\n"
        
        # Group older messages into user-assistant pairs for summarization
        for i in range(0, len(older_messages), 2):
            if i + 1 < len(older_messages):
                user_msg = older_messages[i]
                assistant_msg = older_messages[i + 1]
                
                if user_msg.get("role") == "user" and assistant_msg.get("role") == "assistant":
                    # Create a brief summary of this exchange
                    user_content = user_msg.get("content", "")[:200]  # First 200 chars
                    assistant_content = assistant_msg.get("content", "")[:300]  # First 300 chars
                    
                    summary_content += f"• User asked: {user_content}{'...' if len(user_msg.get('content', '')) > 200 else ''}\n"
                    summary_content += f"• Assistant replied: {assistant_content}{'...' if len(assistant_msg.get('content', '')) > 300 else ''}\n\n"
        
        # Create summary message
        summary_message = {
            "role": "system", 
            "content": f"{summary_content}\n[Context optimized: {len(older_messages)} older messages summarized to save space]"
        }
        
        # Combine: system messages + summary + recent messages
        optimized_messages = system_messages + [summary_message] + recent_messages
    else:
        # No older messages to summarize
        optimized_messages = system_messages + recent_messages
    
    return optimized_messages

def get_context_stats(messages):
    """
    Get statistics about the current context usage.
    
    Args:
        messages: List of chat messages
    
    Returns:
        Dictionary with context statistics
    """
    total_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
    
    # Rough estimation: 1 token ≈ 4 characters for English text
    estimated_tokens = total_chars // 4
    
    return {
        "total_messages": len(messages),
        "total_characters": total_chars,
        "estimated_tokens": estimated_tokens,
        "user_messages": len([msg for msg in messages if msg.get("role") == "user"]),
        "assistant_messages": len([msg for msg in messages if msg.get("role") == "assistant"]),
        "system_messages": len([msg for msg in messages if msg.get("role") == "system"])
    }

def optimize_agent_result(result):
    """
    Optimize agent execution result by truncating long tool outputs.
    
    Args:
        result: Agent execution result with intermediate_steps
    
    Returns:
        Optimized result with truncated tool outputs
    """
    if "intermediate_steps" not in result:
        return result
    
    optimized_steps = []
    
    for action, observation in result["intermediate_steps"]:
        # Truncate the observation (tool output) to save context
        truncated_observation = truncate_tool_output(observation, max_length=800)
        optimized_steps.append((action, truncated_observation))
    
    # Create a new result with optimized steps
    optimized_result = result.copy()
    optimized_result["intermediate_steps"] = optimized_steps
    
    return optimized_result

# Data Sources Dialog Function
@st.dialog("📊 Data Sources Management", width="large")
def show_data_sources():
    # Add New Source Section - moved to top
    st.markdown("### 📁 Add New Sources")
    st.markdown("*Upload new documents or datasets to expand your analysis capabilities*")
    
    if st.button("📁 Add New Source", use_container_width=True):
        st.switch_page("pages/00_home.py")
    
    st.markdown("**Manage your document and tabular data sources for AI analysis**")
    
    # Check available data sources for smart expansion with protective logic
    has_documents = bool("vector_db" in st.session_state and st.session_state.vector_db is not None)
    has_datasets = bool("tabular_datasets" in st.session_state and st.session_state.tabular_datasets)
    
    # Additional check: Ensure we have actual data from persistent storage if session state is empty
    if not has_datasets:
        try:
            tabular_metadata = get_tabular_metadata()
            if tabular_metadata:
                has_datasets = True
        except Exception:
            has_datasets = False
    
    if not has_documents:
        try:
            persist_directory = './chroma_db'
            document_metadata = load_document_metadata(persist_directory)
            if document_metadata:
                has_documents = True
        except Exception:
            has_documents = False
    
    # Ensure boolean values are explicitly set to prevent Streamlit expander errors
    documents_expanded = bool(has_documents and not has_datasets)
    datasets_expanded = bool(has_datasets and not has_documents)

    # Document Sources Section with Expander
    with st.expander("📄 **Document Sources**", expanded=documents_expanded):
        # Check both session state and persistent storage for robustness
        session_has_documents = "vector_db" in st.session_state and st.session_state.vector_db is not None
        
        # Load document metadata to check persistent storage
        try:
            persist_directory = './chroma_db'
            document_metadata = load_document_metadata(persist_directory)
        except Exception as e:
            st.error(f"Error loading document metadata: {e}")
            document_metadata = {}
        
        if session_has_documents or document_metadata:
            if document_metadata:
                st.markdown("*Select documents to use as sources for your questions*")
                
                # Convert metadata to a more usable format for display
                doc_list = []
                for doc_hash, doc_data in document_metadata.items():
                    # Defensive programming: ensure all required fields exist
                    title = doc_data.get("title", f"Document_{doc_hash[:8]}")
                    chunks = doc_data.get("chunks", 0)
                    timestamp = doc_data.get("timestamp", 0)
                    active = doc_data.get("active", True)
                    
                    doc_list.append({
                        "hash": doc_hash,
                        "title": title,
                        "chunks": chunks,
                        "timestamp": timestamp,
                        "active": active
                    })
                
                # Sort by timestamp (newest first)
                doc_list.sort(key=lambda x: x["timestamp"], reverse=True)
                
                # Table headers
                col1, col2, col3 = st.columns([0.6, 0.15, 0.25])
                with col1:
                    st.markdown("**File**")
                with col2:
                    st.markdown("**Date**")
                with col3:
                    st.markdown("")  # No header for remove button
                
                # Create selection interface
                selected_docs = []
                for doc in doc_list:
                    col1, col2, col3 = st.columns([0.6, 0.15, 0.25])
                    with col1:
                        selected = st.checkbox(
                            f"{doc['title']} ({doc['chunks']} chunks)", 
                            value=doc['active'],
                            key=f"doc_select_{doc['hash']}"
                        )
                        if selected:
                            selected_docs.append(doc['hash'])
                    
                    with col2:
                        from datetime import datetime
                        try:
                            timestamp = datetime.fromtimestamp(doc["timestamp"])
                            st.write(timestamp.strftime('%Y-%m-%d'))
                        except (ValueError, OSError):
                            st.write("Unknown")
                    
                    with col3:
                        if st.button("Remove", key=f"remove_{doc['hash']}"):
                            if st.session_state.get("confirm_delete") == doc['hash']:
                                # Set deletion in progress state
                                st.session_state["deleting_in_progress"] = doc['hash']
                                st.session_state["confirm_delete"] = None
                            else:
                                # Set confirmation state
                                st.session_state["confirm_delete"] = doc['hash']
                    
                    # Show confirmation message below item if needed
                    if st.session_state.get("confirm_delete") == doc['hash']:
                        st.warning("Click 'Remove' again to confirm deletion.", icon="⚠️")
                    
                    # Handle deletion with spinner outside column layout
                    if st.session_state.get("deleting_in_progress") == doc['hash']:
                        with st.spinner(f"Deleting '{doc['title']}'..."):
                            success = delete_document_from_vector_db(doc['hash'])
                            if success:
                                st.session_state["deleting_in_progress"] = None
                                st.rerun()
                            else:
                                st.session_state["deleting_in_progress"] = None
                
                # Store selected documents in session state
                if "selected_doc_sources" not in st.session_state or st.session_state.selected_doc_sources != selected_docs:
                    st.session_state.selected_doc_sources = selected_docs
                
                # Update metadata with active status
                for doc_hash in document_metadata:
                    document_metadata[doc_hash]['active'] = doc_hash in selected_docs
                save_document_metadata(persist_directory, document_metadata)
                
                # Add Clear Vector Database button at the end of document list
                if hasattr(st.session_state, 'RAG_AVAILABLE') or RAG_AVAILABLE:
                    # Full-width button with confirmation
                    if st.button("Clear All Documents", type="secondary", use_container_width=True):
                        # Show confirmation dialog
                        if st.session_state.get("confirm_clear_all"):
                            with st.spinner("Clearing vector database..."):
                                success = clear_vector_database()
                                if success:
                                    st.success("Vector database cleared successfully!")
                                    # Also clear the vector_db from session state
                                    if "vector_db" in st.session_state:
                                        del st.session_state["vector_db"]
                                    if "selected_doc_sources" in st.session_state:
                                        del st.session_state["selected_doc_sources"]
                                    if "processed_anonymizations" in st.session_state:
                                        del st.session_state["processed_anonymizations"]
                                    st.rerun()
                                else:
                                    st.error("Failed to clear vector database. If you're seeing a file access error, this could be due to Windows file locks. Try restarting the application.")
                                    if st.button("Restart Application", key="restart_app_button"):
                                        st.rerun()
                            # Clear confirmation state
                            st.session_state["confirm_clear_all"] = False
                        else:
                            # Set confirmation state and show confirmation message
                            st.session_state["confirm_clear_all"] = True
                    
                    # Show confirmation message below button if needed
                    if st.session_state.get("confirm_clear_all"):
                        st.error("Click 'Clear All Documents' again to confirm deletion of ALL documents. This action cannot be undone.", icon="⚠️")
            else:
                st.info("No documents found in the database. Process a document to add it to the sources.")
        else:
            st.info("📄 No document sources loaded. Upload documents on the Home page and process them to add document sources.")
            st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)

    # Tabular Dataset Sources Section with Expander
    with st.expander("📊 **Tabular Data Sources**", expanded=datasets_expanded):
        # Check both session state and persistent storage for robustness
        session_has_datasets = "tabular_datasets" in st.session_state and bool(st.session_state.tabular_datasets)
        
        # Load tabular metadata to check persistent storage
        try:
            tabular_metadata = get_tabular_metadata()
        except Exception as e:
            st.error(f"Error loading tabular metadata: {e}")
            tabular_metadata = {}
        
        if session_has_datasets or tabular_metadata:
            # If we have metadata but no session datasets, try to reload
            if tabular_metadata and not session_has_datasets:
                try:
                    persistent_datasets = load_tabular_datasets()
                    if persistent_datasets:
                        st.session_state.tabular_datasets = persistent_datasets
                        session_has_datasets = True
                        st.info("Reloaded datasets from storage.")
                except Exception as e:
                    st.warning(f"Could not reload datasets: {e}")
            
            if tabular_metadata:
                st.markdown("*Select datasets to use as sources for your questions*")
                
                # Convert metadata to a more usable format for display
                dataset_list = []
                for file_hash, dataset_data in tabular_metadata.items():
                    # Defensive programming: ensure all required fields exist
                    title = dataset_data.get("title", f"Dataset_{file_hash[:8]}")
                    shape = dataset_data.get("shape", [0, 0])
                    columns = dataset_data.get("columns", [])
                    timestamp = dataset_data.get("timestamp", 0)
                    active = dataset_data.get("active", True)
                    
                    dataset_list.append({
                        "hash": file_hash,
                        "title": title,
                        "shape": shape,
                        "columns": columns,
                        "timestamp": timestamp,
                        "active": active
                    })
                
                # Sort by timestamp (newest first)
                dataset_list.sort(key=lambda x: x["timestamp"], reverse=True)
                
                # Table headers
                col1, col2, col3 = st.columns([0.6, 0.15, 0.25])
                with col1:
                    st.markdown("**File**")
                with col2:
                    st.markdown("**Date**")
                with col3:
                    st.markdown("")  # No header for remove button
                
                # Create selection interface
                selected_datasets = []
                for dataset in dataset_list:
                    col1, col2, col3 = st.columns([0.6, 0.15, 0.25])
                    with col1:
                        selected = st.checkbox(
                            f"{dataset['title']} ({dataset['shape'][0]} rows, {dataset['shape'][1]} cols)", 
                            value=dataset['active'],
                            key=f"dataset_select_{dataset['hash']}"
                        )
                        if selected:
                            selected_datasets.append(dataset['title'])
                    
                    with col2:
                        from datetime import datetime
                        try:
                            timestamp = datetime.fromtimestamp(dataset["timestamp"])
                            st.write(timestamp.strftime('%Y-%m-%d'))
                        except (ValueError, OSError):
                            st.write("Unknown")
                    
                    with col3:
                        if st.button("Remove", key=f"remove_dataset_{dataset['hash']}"):
                            if st.session_state.get("confirm_delete_dataset") == dataset['hash']:
                                # Set deletion in progress state
                                st.session_state["deleting_dataset_in_progress"] = dataset['hash']
                                st.session_state["confirm_delete_dataset"] = None
                            else:
                                # Set confirmation state
                                st.session_state["confirm_delete_dataset"] = dataset['hash']
                    
                    # Show confirmation message below item if needed
                    if st.session_state.get("confirm_delete_dataset") == dataset['hash']:
                        st.warning("Click 'Remove' again to confirm deletion.", icon="⚠️")
                    
                    # Handle deletion with spinner outside column layout
                    if st.session_state.get("deleting_dataset_in_progress") == dataset['hash']:
                        with st.spinner(f"Deleting '{dataset['title']}'..."):
                            success = delete_tabular_dataset(dataset['hash'])
                            if success:
                                st.session_state["deleting_dataset_in_progress"] = None
                                st.rerun()
                            else:
                                st.session_state["deleting_dataset_in_progress"] = None
                
                # Store selected datasets in session state
                if "selected_datasets" not in st.session_state or st.session_state.selected_datasets != selected_datasets:
                    st.session_state.selected_datasets = selected_datasets
                
                # Update metadata with active status
                for file_hash, dataset_data in tabular_metadata.items():
                    dataset_data['active'] = dataset_data['title'] in selected_datasets
                # Save the updated metadata
                save_tabular_metadata_active_status(tabular_metadata)
                
                # Add Clear All Datasets button
                if st.button("Clear All Datasets", type="secondary", use_container_width=True):
                    if st.session_state.get("confirm_clear_all_datasets"):
                        with st.spinner("Clearing all tabular datasets..."):
                            success = clear_all_tabular_data()
                            if success:
                                st.success("All datasets cleared successfully!")
                                # Clear from session state
                                if "tabular_datasets" in st.session_state:
                                    del st.session_state["tabular_datasets"]
                                if "selected_datasets" in st.session_state:
                                    del st.session_state["selected_datasets"]
                                st.rerun()
                            else:
                                st.error("Failed to clear datasets.")
                        # Clear confirmation state
                        st.session_state["confirm_clear_all_datasets"] = False
                    else:
                        # Set confirmation state and show confirmation message
                        st.session_state["confirm_clear_all_datasets"] = True
                
                # Show confirmation message below button if needed
                if st.session_state.get("confirm_clear_all_datasets"):
                    st.error("Click 'Clear All Datasets' again to confirm deletion of ALL datasets. This action cannot be undone.", icon="⚠️")
            else:
                st.info("No datasets found in storage. Upload a CSV or Excel file to add datasets.")
                st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)
        else:
            st.info("📊 No tabular datasets loaded. Upload CSV or Excel files on the Home page to add datasets.")
            st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)
    
    # Content insights toggle section
    st.markdown("### 🔍 Content Insights")
    show_insights = st.checkbox("Show Content Insights", help="Display AI-powered analysis of your content (no tokens consumed)")
    
    # Perform content analysis if requested
    if show_insights:
        st.subheader("📋 Content Analysis Summary")
        
        # Persistent Document insights
        persist_directory = './chroma_db'
        document_metadata = load_document_metadata(persist_directory)
        if document_metadata:
            with st.expander("📚 Persistent Document Sources", expanded=True):
                st.markdown(f"**{len(document_metadata)} document(s) in vector database:**")
                
                for doc_hash, doc_data in document_metadata.items():
                    title = doc_data.get('title', 'Unknown Document')
                    chunks = doc_data.get('chunks', 0)
                    length = doc_data.get('length', 0)
                    active = doc_data.get('active', True)
                    entities = doc_data.get('entities', {})
                    
                    status_icon = "✅" if active else "⏸️"
                    st.write(f"{status_icon} **{title}**")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Word Count", f"{length:,}")
                    with col2:
                        st.metric("Text Chunks", chunks)
                    with col3:
                        entity_count = len(entities.get('Text', [])) if entities else 0
                        st.metric("Entities", entity_count)
                    with col4:
                        status = "Active" if active else "Inactive"
                        st.metric("Status", status)
                    
                    # Entity breakdown for persistent documents
                    if entities and 'Category' in entities:
                        entity_types = entities['Category']
                        if entity_types:
                            st.write("**Entity Types:**")
                            entity_counts = {}
                            for entity_type in entity_types:
                                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                            
                            for entity_type, count in entity_counts.items():
                                st.write(f"• {entity_type}: {count} instances")
                    
                    st.markdown("---")
        
        # Current session document insights
        if "saved_anonymisation" in st.session_state:
            document_content = st.session_state["saved_anonymisation"].get("Data", "")
            document_entities = st.session_state["saved_anonymisation"].get("Entities", {})
            if document_content:
                with st.expander("📄 Document Insights", expanded=True):
                    insights = analyze_document_locally(document_content, document_entities)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Content Type", insights.get('meeting_type', 'document').replace('_', ' ').title())
                    with col2:
                        st.metric("Word Count", f"{insights.get('word_count', 0):,}")
                    with col3:
                        st.metric("Formality Score", f"{insights.get('formality_score', 0):.1%}")
                    with col4:
                        action_status = "✅ Yes" if insights.get('has_action_items') else "❌ No"
                        st.metric("Has Actions", action_status)
                    
                    # Entity breakdown
                    entity_types = insights.get('entity_types', [])
                    if entity_types:
                        st.write("**Detected Entities:**")
                        entity_counts = {}
                        for entity_type in entity_types:
                            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                        
                        for entity_type, count in entity_counts.items():
                            st.write(f"• {entity_type}: {count} instances")
        
        # Dataset insights
        if "tabular_datasets" in st.session_state and st.session_state.tabular_datasets:
            with st.expander("📊 Dataset Insights", expanded=True):
                for dataset_name, df in st.session_state.tabular_datasets.items():
                    # Call analysis with fresh DataFrame reference
                    insights = analyze_dataset_locally(df.copy(), dataset_name)
                    
                    st.write(f"**{dataset_name}**")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Rows", f"{insights.get('row_count', 0):,}")
                    with col2:
                        st.metric("Columns", insights.get('column_count', 0))
                    with col3:
                        st.metric("Key Metrics", len(insights.get('key_metrics', [])))
                    with col4:
                        data_quality = f"{insights.get('data_density', 0):.1f}%"
                        st.metric("Data Quality", data_quality)
                    
                    # Show column headers in original order
                    all_columns = list(df.columns)
                    
                    st.write("**Column Headers:**")
                    
                    # Display columns in original order, with smart truncation
                    if len(all_columns) <= 12:
                        # Show all columns if 12 or fewer
                        st.write(f"*({len(all_columns)} columns):* {', '.join(all_columns)}")
                    else:
                        # Show first 10 columns and indicate how many more
                        displayed_columns = all_columns[:10]
                        remaining_count = len(all_columns) - 10
                        st.write(f"*({len(all_columns)} columns):* {', '.join(displayed_columns)}")
                        st.caption(f"... and {remaining_count} more columns")
                    
                    # Show suggested charts
                    suggested_charts = insights.get('suggested_charts', [])
                    if suggested_charts:
                        st.write("**Recommended Charts:**")
                        for chart in suggested_charts[:3]:
                            st.write(f"• {chart.get('type', 'chart').title()}: {chart.get('description', 'No description')}")
                    
                    if dataset_name != list(st.session_state.tabular_datasets.keys())[-1]:  # Not the last item
                        st.markdown("---")
        
        if not "saved_anonymisation" in st.session_state and not ("tabular_datasets" in st.session_state and st.session_state.tabular_datasets):
            st.info("💡 Upload documents or datasets to see AI-powered content insights!")

# ===== LOCAL CONTENT ANALYSIS FUNCTIONS (ZERO TOKENS) =====

def analyze_document_locally(document_text, entities_data):
    """
    Analyze document content without consuming API tokens.
    Uses local pattern matching and statistical analysis.
    
    Args:
        document_text: The document content as string
        entities_data: The entities dictionary with Text, Replacement, Category
    
    Returns:
        dict: Document insights without API calls
    """
    if not document_text:
        return {}
    
    # Basic text statistics
    words = document_text.split()
    word_count = len(words)
    paragraph_count = len([p for p in document_text.split('\n\n') if p.strip()])
    sentence_count = len([s for s in re.split(r'[.!?]+', document_text) if s.strip()])
    
    # Entity analysis
    entity_types = set()
    has_people = False
    has_organizations = False
    has_dates = False
    has_locations = False
    
    if entities_data and isinstance(entities_data, dict):
        categories = entities_data.get('Category', [])
        if categories:
            entity_types = set(categories)
            has_people = any('PERSON' in cat or 'PER' in cat for cat in categories)
            has_organizations = any('ORG' in cat for cat in categories)
            has_dates = any('DATE' in cat or 'TIME' in cat for cat in categories)
            has_locations = any('LOC' in cat or 'GPE' in cat for cat in categories)
    
    # Content type detection patterns
    meeting_indicators = count_meeting_patterns(document_text)
    action_keywords = count_action_keywords(document_text)
    question_density = document_text.count('?') / max(word_count, 1) * 1000
    
    # Meeting type detection
    meeting_type = detect_meeting_type(document_text, meeting_indicators, action_keywords)
    
    # Content characteristics
    formal_score = calculate_formality_score(document_text)
    
    insights = {
        'word_count': word_count,
        'paragraph_count': paragraph_count,
        'sentence_count': sentence_count,
        'avg_words_per_sentence': word_count / max(sentence_count, 1),
        'entity_types': list(entity_types),
        'has_people': has_people,
        'has_organizations': has_organizations,
        'has_dates': has_dates,
        'has_locations': has_locations,
        'meeting_indicators': meeting_indicators,
        'action_keywords': action_keywords,
        'question_density': question_density,
        'meeting_type': meeting_type,
        'formality_score': formal_score,
        'has_action_items': action_keywords > 3,
        'is_meeting_transcript': meeting_indicators > 2,
        'is_formal_document': formal_score > 0.6
    }
    
    return insights

def analyze_dataset_locally(df, dataset_name):
    """
    Analyze tabular dataset structure without API calls.
    Uses pandas built-in functions for statistical analysis.
    
    Args:
        df: pandas DataFrame
        dataset_name: Name of the dataset
    
    Returns:
        dict: Dataset insights without API calls
    """
    if df is None or df.empty:
        return {}
    
    # Basic structure
    row_count, col_count = df.shape
    
    # Column type analysis
    numeric_columns = list(df.select_dtypes(include=['number']).columns)
    categorical_columns = list(df.select_dtypes(include=['object', 'category']).columns)
    datetime_columns = detect_date_columns(df)
    
    # Data quality analysis
    missing_data = df.isnull().sum().to_dict()
    missing_percentage = {col: (missing / row_count * 100) for col, missing in missing_data.items()}
    
    # Key metrics identification
    key_metrics = identify_metric_columns(df, numeric_columns)
    
    # Time series detection
    has_time_series = len(datetime_columns) > 0 or any('date' in col.lower() or 'time' in col.lower() for col in df.columns)
    
    # Suggested visualizations
    suggested_charts = suggest_charts_locally(df, numeric_columns, categorical_columns, datetime_columns)
    
    # Content patterns
    top_categories = get_top_categories(df, categorical_columns)
    
    insights = {
        'dataset_name': dataset_name,
        'row_count': row_count,
        'column_count': col_count,
        'numeric_columns': numeric_columns,
        'categorical_columns': categorical_columns,
        'datetime_columns': datetime_columns,
        'key_metrics': key_metrics,
        'has_time_series': has_time_series,
        'missing_data': missing_data,
        'missing_percentage': missing_percentage,
        'suggested_charts': suggested_charts,
        'top_categories': top_categories,
        'data_density': (row_count * col_count - sum(missing_data.values())) / (row_count * col_count) * 100
    }
    
    return insights

def count_meeting_patterns(text):
    """Count patterns that indicate meeting content"""
    patterns = [
        r'\bmeeting\b',
        r'\bdiscussed?\b',
        r'\bagreed?\b',
        r'\bdecided?\b',
        r'\baction\s+item\b',
        r'\bnext\s+steps?\b',
        r'\bfollow\s*up\b',
        r'\battendees?\b',
        r'\bparticipants?\b',
        r'\bminutes?\b'
    ]
    
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    
    return count

def count_action_keywords(text):
    """Count action-oriented keywords"""
    action_words = [
        r'\bwill\b', r'\bshall\b', r'\bmust\b', r'\bshould\b',
        r'\btodo\b', r'\baction\b', r'\btask\b', r'\bassign\b',
        r'\bresponsible\b', r'\bdeadline\b', r'\bby\s+\w+day\b',
        r'\bimplement\b', r'\bexecute\b', r'\bcomplete\b',
        r'\bdeliverable\b', r'\bmilestone\b'
    ]
    
    count = 0
    for pattern in action_words:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    
    return count

def detect_meeting_type(text, meeting_indicators, action_keywords):
    """Detect the type of meeting based on content patterns"""
    if meeting_indicators < 2:
        return "document"
    
    # Decision-focused meeting
    if action_keywords > 5 and any(word in text.lower() for word in ['decision', 'approve', 'reject', 'vote']):
        return "decision_meeting"
    
    # Planning meeting
    if any(word in text.lower() for word in ['plan', 'strategy', 'roadmap', 'timeline']):
        return "planning_meeting"
    
    # Status/update meeting
    if any(word in text.lower() for word in ['status', 'update', 'progress', 'report']):
        return "status_meeting"
    
    # General meeting
    return "general_meeting"

def calculate_formality_score(text):
    """Calculate formality score based on language patterns"""
    formal_indicators = [
        r'\btherefore\b', r'\bhowever\b', r'\bmoreover\b', r'\bfurthermore\b',
        r'\bconsequently\b', r'\bnevertheless\b', r'\bnotwithstanding\b',
        r'\bregarding\b', r'\bconcerning\b', r'\bpursuant\b'
    ]
    
    informal_indicators = [
        r'\byeah\b', r'\bokay\b', r'\boh\b', r'\bum\b', r'\buh\b',
        r'\bguys\b', r'\bstuff\b', r'\bthings\b', r'\.\.\.', r'\!+'
    ]
    
    formal_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in formal_indicators)
    informal_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in informal_indicators)
    
    total_words = len(text.split())
    formal_ratio = formal_count / max(total_words / 100, 1)  # Per 100 words
    informal_ratio = informal_count / max(total_words / 100, 1)
    
    # Score from 0 to 1, where 1 is most formal
    return min(max(formal_ratio - informal_ratio + 0.5, 0), 1)

def detect_date_columns(df):
    """Detect columns that contain date/time information"""
    date_columns = []
    
    for col in df.columns:
        # Check column name patterns
        if any(pattern in col.lower() for pattern in ['date', 'time', 'created', 'updated', 'timestamp']):
            date_columns.append(col)
            continue
        
        # Check if column values look like dates
        if df[col].dtype == 'object':
            sample_values = df[col].dropna().head(10).astype(str)
            date_like_count = 0
            
            for value in sample_values:
                # Simple date pattern matching
                if re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', value) or \
                   re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', value) or \
                   any(month in value.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                    date_like_count += 1
            
            if date_like_count >= len(sample_values) * 0.7:  # 70% threshold
                date_columns.append(col)
    
    return date_columns

def identify_metric_columns(df, numeric_columns):
    """Identify the most important numeric columns for analysis"""
    if not numeric_columns:
        return []
    
    key_metrics = []
    
    for col in numeric_columns:
        # Skip ID-like columns
        if 'id' in col.lower() and df[col].nunique() == len(df):
            continue
        
        # Prioritize columns with meaningful names
        if any(keyword in col.lower() for keyword in [
            'amount', 'value', 'price', 'cost', 'revenue', 'profit',
            'count', 'total', 'sum', 'average', 'score', 'rating',
            'percentage', 'rate', 'ratio', 'budget', 'sales'
        ]):
            key_metrics.append(col)
        elif df[col].nunique() > 1:  # Has variation
            key_metrics.append(col)
    
    # Return top 5 most important metrics
    return key_metrics[:5]

def suggest_charts_locally(df, numeric_columns, categorical_columns, datetime_columns):
    """Suggest appropriate chart types based on data structure"""
    suggestions = []
    
    # Time series charts
    if datetime_columns and numeric_columns:
        suggestions.append({
            'type': 'line',
            'description': f'Time trends for {", ".join(numeric_columns[:3])}',
            'x_column': datetime_columns[0],
            'y_columns': numeric_columns[:3]
        })
    
    # Bar charts for categorical data
    if categorical_columns and numeric_columns:
        suggestions.append({
            'type': 'bar',
            'description': f'Comparison by {categorical_columns[0]}',
            'x_column': categorical_columns[0],
            'y_column': numeric_columns[0]
        })
    
    # Distribution charts
    if numeric_columns:
        suggestions.append({
            'type': 'histogram',
            'description': f'Distribution of {numeric_columns[0]}',
            'column': numeric_columns[0]
        })
    
    # Correlation analysis
    if len(numeric_columns) >= 2:
        suggestions.append({
            'type': 'scatter',
            'description': f'Relationship between {numeric_columns[0]} and {numeric_columns[1]}',
            'x_column': numeric_columns[0],
            'y_column': numeric_columns[1]
        })
    
    return suggestions[:4]  # Return top 4 suggestions

def get_top_categories(df, categorical_columns):
    """Get top categories from categorical columns"""
    top_categories = {}
    
    for col in categorical_columns[:3]:  # Analyze first 3 categorical columns
        if df[col].nunique() <= 20:  # Only for columns with reasonable number of categories
            value_counts = df[col].value_counts().head(5)
            top_categories[col] = value_counts.to_dict()
    
    return top_categories

def generate_smart_templates_locally(document_insights=None, dataset_insights=None):
    """
    Generate contextual prompt templates based on local analysis.
    No API tokens consumed.
    
    Args:
        document_insights: Results from analyze_document_locally()
        dataset_insights: Dictionary of dataset_name -> analyze_dataset_locally() results
    
    Returns:
        dict: Smart template prompts based on content analysis
    """
    templates = {}
    
    # Document-based smart templates
    if document_insights:
        word_count = document_insights.get('word_count', 0)
        meeting_type = document_insights.get('meeting_type', 'document')
        has_action_items = document_insights.get('has_action_items', False)
        has_people = document_insights.get('has_people', False)
        has_organizations = document_insights.get('has_organizations', False)
        is_formal = document_insights.get('is_formal_document', False)
        
        if meeting_type == 'decision_meeting':
            templates['🎯 Decision Summary'] = """Extract and organize all decisions made in this meeting:

**Key Decisions:** What was decided and why
**Decision Context:** Background information for each decision
**Implementation Plan:** How decisions will be executed
**Responsible Parties:** Who is accountable for each decision
**Timeline:** When decisions need to be implemented

Focus on actionable outcomes and clear accountability."""
        
        elif meeting_type == 'planning_meeting':
            templates['📋 Strategic Plan'] = """Create a comprehensive planning summary:

**Strategic Objectives:** Main goals and targets discussed
**Action Plan:** Step-by-step implementation approach
**Resource Requirements:** People, budget, and materials needed
**Timeline & Milestones:** Key dates and checkpoints
**Success Metrics:** How progress will be measured

Format as an executive planning document."""
        
        elif meeting_type == 'status_meeting':
            templates['📊 Status Report'] = """Generate a professional status report:

**Current Progress:** What has been accomplished
**Key Metrics:** Quantifiable progress indicators  
**Challenges & Risks:** Issues that need attention
**Next Steps:** Immediate actions required
**Resource Status:** Team, budget, and timeline updates

Structure as a formal status update for leadership."""
        
        if has_action_items:
            templates['✅ Action Item Tracker'] = """Create a detailed action item list:

**Immediate Actions (1-2 weeks):** Urgent tasks with deadlines
**Medium-term Actions (1-3 months):** Important ongoing work
**Long-term Commitments (3+ months):** Strategic initiatives
**Responsible Parties:** Clear ownership for each item
**Dependencies:** What needs to happen first

Format as a trackable task management list."""
        
        if has_people and has_organizations:
            templates['🏢 Stakeholder Analysis'] = """Analyze stakeholder involvement and relationships:

**Key Stakeholders:** Important people and their roles
**Organizational Dynamics:** How different groups interact
**Decision Makers:** Who has authority and influence
**Communication Needs:** How stakeholders should be engaged
**Relationship Map:** Connections between parties

Provide strategic stakeholder management insights."""
        
        if is_formal and word_count > 2000:
            templates['📄 Executive Summary'] = """Create a concise executive summary for leadership:

**Purpose & Scope:** Why this document matters
**Key Findings:** Most important insights and conclusions
**Strategic Implications:** What this means for the organization
**Recommendations:** Specific actions leadership should consider
**Next Steps:** Immediate follow-up required

Write in formal executive communication style."""
    
    # Dataset-based smart templates
    if dataset_insights:
        for dataset_name, insights in dataset_insights.items():
            row_count = insights.get('row_count', 0)
            numeric_cols = insights.get('numeric_columns', [])
            categorical_cols = insights.get('categorical_columns', [])
            has_time_series = insights.get('has_time_series', False)
            key_metrics = insights.get('key_metrics', [])
            
            # Time-based analysis
            if has_time_series and numeric_cols:
                templates[f'📈 Trend Analysis - {dataset_name}'] = f"""Analyze trends and patterns over time in {dataset_name}:

**Overall Trends:** Direction and magnitude of changes in {', '.join(key_metrics[:3])}
**Seasonal Patterns:** Recurring cycles or seasonal variations
**Growth Rates:** Calculate period-over-period growth rates
**Trend Analysis:** What the data tells us about future direction
**Key Insights:** Most important findings from temporal analysis

Create line charts showing trends over time and highlight significant changes."""
            
            # Categorical comparison
            if categorical_cols and numeric_cols:
                templates[f'⚖️ Performance Comparison - {dataset_name}'] = f"""Compare performance across different groups in {dataset_name}:

**Group Rankings:** Rank {categorical_cols[0]} by {numeric_cols[0] if numeric_cols else 'performance'}
**Performance Gaps:** Identify best and worst performers
**Statistical Analysis:** Show averages, medians, and distributions by group
**Key Differences:** What makes top performers different
**Actionable Insights:** Recommendations based on performance patterns

Create bar charts and comparison tables showing group differences."""
            
            # Data overview for large datasets
            if row_count > 1000:
                templates[f'📊 Data Deep Dive - {dataset_name}'] = f"""Provide comprehensive analysis of {dataset_name} ({row_count:,} records):

**Data Profile:** Key statistics and distributions for main metrics
**Top Insights:** 5 most important patterns or findings
**Quality Assessment:** Data completeness and any anomalies
**Correlation Analysis:** Relationships between different variables
**Segmentation:** Identify distinct groups or clusters in the data

Create multiple visualizations highlighting key findings."""
            
            # Quick insights for smaller datasets
            else:
                templates[f'🔍 Quick Insights - {dataset_name}'] = f"""Generate quick insights from {dataset_name}:

**Top Performers:** Highest values in key metrics
**Key Patterns:** Notable trends or relationships
**Summary Statistics:** Essential numbers every stakeholder should know
**Recommended Actions:** What the data suggests we should do
**Visual Summary:** 2-3 charts that tell the story

Focus on the most actionable insights."""
    
    # Cross-source templates (when both documents and datasets available)
    if document_insights and dataset_insights:
        templates['🔗 Integrated Analysis'] = """Combine insights from documents and data sources:

**Document Context:** Key themes and decisions from text analysis
**Data Validation:** How the numerical data supports or contradicts document insights
**Comprehensive View:** What the complete picture tells us
**Evidence-Based Recommendations:** Suggestions backed by both qualitative and quantitative evidence
**Action Plan:** Next steps based on integrated analysis

Create a unified analysis that leverages both data types."""
    
    return templates

# ===== END LOCAL ANALYSIS FUNCTIONS =====

@tool
def get_document_sources() -> str:
    """
    Get detailed information about all available document sources in the system.
    
    Returns:
        Detailed list of available documents with titles, summaries, and metadata
    """
    # Check if vector database is available
    if not hasattr(st.session_state, 'vector_db') or st.session_state.vector_db is None:
        return "No text documents are currently loaded in the database."
    
    try:
        # Load document metadata
        persist_directory = './chroma_db'
        document_metadata = load_document_metadata(persist_directory)
        
        if not document_metadata:
            return "No documents found in the database."
        
        # Count active vs total documents
        active_count = sum(1 for doc_data in document_metadata.values() if doc_data.get("active", True))
        total_count = len(document_metadata)
        
        # Create detailed document listing with status summary
        if active_count == total_count:
            result = f"Document Sources ({total_count} documents - all active):\n\n"
        else:
            result = f"Document Sources ({active_count} active, {total_count} total):\n\n"
        
        # Sort documents by timestamp (newest first)
        doc_list = []
        for doc_hash, doc_data in document_metadata.items():
            doc_list.append({
                "hash": doc_hash,
                "title": doc_data.get("title", "Unknown Document"),
                "length": doc_data.get("length", 0),
                "chunks": doc_data.get("chunks", 0),
                "timestamp": doc_data.get("timestamp", 0),
                "active": doc_data.get("active", True),
                "entities": doc_data.get("entities", {})
            })
        
        doc_list.sort(key=lambda x: x["timestamp"], reverse=True)
        
        for i, doc in enumerate(doc_list, 1):
            result += f"{i}. **{doc['title']}**\n"
            result += f"   - Length: {doc['length']:,} characters\n"
            result += f"   - Chunks: {doc['chunks']} text segments\n"
            result += f"   - Status: {'Active' if doc['active'] else 'Inactive'}\n"
            
            # Add entity information if available
            entities = doc.get('entities', {})
            if entities and 'Category' in entities:
                entity_types = set(entities['Category'])
                entity_summary = []
                for entity_type in ['PERSON', 'ORG', 'GPE', 'DATE', 'TIME']:
                    count = entities['Category'].count(entity_type)
                    if count > 0:
                        entity_summary.append(f"{entity_type}: {count}")
                
                if entity_summary:
                    result += f"   - Key Entities: {', '.join(entity_summary)}\n"
            
            # Add content hint based on title and entities
            content_hints = []
            title_lower = doc['title'].lower()
            if 'sustainable' in title_lower or 'development' in title_lower:
                content_hints.append("sustainability/development topics")
            if 'charter' in title_lower or 'constitution' in title_lower:
                content_hints.append("governance/legal framework")
            if 'pact' in title_lower or 'agreement' in title_lower:
                content_hints.append("international agreements")
            
            if content_hints:
                result += f"   - Content Type: {', '.join(content_hints)}\n"
            
            result += "\n"
        
        result += "💡 **Usage Tips:**\n"
        result += "- Use search_documents() to find specific information within these documents\n"
        result += "- Mention document titles in your queries for more targeted searches\n"
        result += "- All documents are anonymized for privacy protection\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving document sources: {str(e)}"

@tool
def get_active_sources_summary() -> str:
    """
    Get a summary of currently ACTIVE/SELECTED data sources that will be used for analysis.
    
    Returns:
        Summary of active documents and datasets that the agent can currently access
    """
    summary_parts = []
    
    # Check active documents
    if hasattr(st.session_state, 'vector_db') and st.session_state.vector_db is not None:
        try:
            persist_directory = './chroma_db'
            document_metadata = load_document_metadata(persist_directory)
            
            if document_metadata:
                active_docs = [doc_data for doc_data in document_metadata.values() if doc_data.get("active", True)]
                total_docs = len(document_metadata)
                
                if active_docs:
                    active_titles = [doc.get("title", "Unknown") for doc in active_docs]
                    summary_parts.append(f"📄 **Active Documents ({len(active_docs)} of {total_docs} available):**")
                    for i, title in enumerate(active_titles, 1):
                        summary_parts.append(f"   {i}. {title}")
                else:
                    summary_parts.append(f"📄 **Documents:** 0 active ({total_docs} available but all inactive)")
            else:
                summary_parts.append("📄 **Documents:** None available")
        except Exception:
            summary_parts.append("📄 **Documents:** Error checking document status")
    else:
        summary_parts.append("📄 **Documents:** None loaded")
    
    # Check active tabular datasets
    available_datasets = get_selected_tabular_datasets()
    all_datasets = st.session_state.get("tabular_datasets", {})
    
    if available_datasets:
        dataset_names = list(available_datasets.keys())
        total_datasets = len(all_datasets)
        summary_parts.append(f"📊 **Active Datasets ({len(available_datasets)} of {total_datasets} available):**")
        for i, name in enumerate(dataset_names, 1):
            df = available_datasets[name]
            summary_parts.append(f"   {i}. {name} ({df.shape[0]} rows, {df.shape[1]} columns)")
        
        # Add debug info to help troubleshoot
        tabular_metadata = get_tabular_metadata()
        if tabular_metadata:
            metadata_active_count = sum(1 for data in tabular_metadata.values() if data.get("active", True))
            if len(available_datasets) != metadata_active_count:
                summary_parts.append(f"   ⚠️ Debug: Metadata shows {metadata_active_count} active, but filtered to {len(available_datasets)}")
    elif all_datasets:
        total_datasets = len(all_datasets)
        summary_parts.append(f"📊 **Datasets:** 0 active ({total_datasets} available but all inactive)")
        
        # Show metadata status for debugging
        tabular_metadata = get_tabular_metadata()
        if tabular_metadata:
            metadata_active_count = sum(1 for data in tabular_metadata.values() if data.get("active", True))
            summary_parts.append(f"   🔍 Debug: Metadata shows {metadata_active_count} datasets as active")
    else:
        summary_parts.append("📊 **Datasets:** None loaded")
    
    if not summary_parts:
        return "No data sources are currently available for analysis."
    
    result = "**ACTIVE DATA SOURCES SUMMARY**\n\n" + "\n".join(summary_parts)
    result += "\n\n💡 **Note:** Only active/selected sources will be used for analysis. You can change selections in Data Sources Management."
    
    return result

def get_selected_tabular_datasets():
    """
    Get only the selected tabular datasets based on checkbox selection in Data Sources Management.
    
    Returns:
        dict: Dictionary of selected datasets {name: dataframe}
    """
    # Get all available datasets
    all_datasets = st.session_state.get("tabular_datasets", {})
    
    if not all_datasets:
        return {}
    
    # Get selected dataset names from checkboxes
    selected_dataset_names = st.session_state.get("selected_datasets", [])
    
    # Check if we have metadata to determine the actual active status
    tabular_metadata = get_tabular_metadata()
    
    # If we have metadata with active status information, use that
    if tabular_metadata:
        filtered_datasets = {}
        for file_hash, dataset_data in tabular_metadata.items():
            dataset_title = dataset_data.get("title", "Unknown")
            is_active = dataset_data.get("active", True)
            
            # Only include if marked as active in metadata AND exists in session state
            if is_active and dataset_title in all_datasets:
                filtered_datasets[dataset_title] = all_datasets[dataset_title]
        
        return filtered_datasets
    
    # Fallback: If no metadata exists, use session state selection
    # If no selection exists, return all datasets (default behavior for new installations)
    if not selected_dataset_names:
        return all_datasets
    
    # Filter datasets based on selection
    filtered_datasets = {}
    for dataset_name in selected_dataset_names:
        if dataset_name in all_datasets:
            filtered_datasets[dataset_name] = all_datasets[dataset_name]
    
    return filtered_datasets

def save_tabular_metadata_active_status(metadata):
    """
    Save tabular metadata with updated active status.
    
    Args:
        metadata: Dictionary of tabular metadata to save
    """
    try:
        metadata_file = "./data_storage/tabular_metadata.json"
        
        # Ensure directory exists
        os.makedirs("./data_storage", exist_ok=True)
        
        # Save metadata
        with open(metadata_file, 'w') as f:
            # Convert any numpy types to native Python types for JSON serialization
            serializable_metadata = {}
            for key, value in metadata.items():
                serializable_value = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (list, tuple)):
                        # Convert any numpy types in lists
                        serializable_value[sub_key] = [
                            item.tolist() if hasattr(item, 'tolist') else item 
                            for item in sub_value
                        ]
                    elif hasattr(sub_value, 'tolist'):
                        # Convert numpy arrays
                        serializable_value[sub_key] = sub_value.tolist()
                    else:
                        serializable_value[sub_key] = sub_value
                serializable_metadata[key] = serializable_value
            
            json.dump(serializable_metadata, f, indent=2)
            
    except Exception as e:
        st.warning(f"Could not save tabular metadata: {e}")

