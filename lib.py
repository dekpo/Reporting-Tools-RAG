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

# For visualization capabilities
try:
    # Suppress matplotlib font cache messages for PyInstaller exe
    import warnings
    import logging
    
    # Suppress matplotlib font manager warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')
    
    # Set matplotlib logging level to suppress font cache messages
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    
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
APP_VERSION = "2.5"

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

def save_content(title,content,attendees):
    st.session_state["saved_content"] = {
        "Time": current_datetime,
        "Title": title,
        "Data": content,
        "Attendees": attendees

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
        st.sidebar.header(":floppy_disk: Your Backup",divider=True)
        
        # Document Sources
        if document_metadata:
            st.sidebar.write(":page_with_curl: **Document Sources**")
            # Convert metadata to list and sort by timestamp (newest first)
            doc_list = []
            for doc_hash, doc_data in document_metadata.items():
                doc_list.append({
                    "title": doc_data["title"],
                    "timestamp": doc_data.get("timestamp", 0)
                })
            doc_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Display truncated document names
            for doc in doc_list[:5]:  # Show max 5 to avoid sidebar overflow
                truncated_title = doc["title"][:15] + "..." if len(doc["title"]) > 15 else doc["title"]
                st.sidebar.caption(f"• {truncated_title}")
            
            if len(doc_list) > 5:
                st.sidebar.caption(f"• ... and {len(doc_list) - 5} more")
        
        # Tabular Data Sources
        if tabular_metadata:
            st.sidebar.write(":bar_chart: **Tabular Data Sources**")
            # Convert metadata to list and sort by timestamp (newest first)
            dataset_list = []
            for file_hash, dataset_data in tabular_metadata.items():
                dataset_list.append({
                    "title": dataset_data["title"],
                    "timestamp": dataset_data.get("timestamp", 0)
                })
            dataset_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Display truncated dataset names
            for dataset in dataset_list[:5]:  # Show max 5 to avoid sidebar overflow
                truncated_title = dataset["title"][:15] + "..." if len(dataset["title"]) > 15 else dataset["title"]
                st.sidebar.caption(f"• {truncated_title}")
            
            if len(dataset_list) > 5:
                st.sidebar.caption(f"• ... and {len(dataset_list) - 5} more")
        
        # Manage Sources button
        if st.sidebar.button("🔧 Manage Sources", key="manage_sources_sidebar", use_container_width=True, help="Open data sources management dialog"):
            st.session_state["show_sources_dialog"] = True
    
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

def create_vector_db_from_text(text, title, api_key, entities=None):
    """
    Create a vector database from text content.
    
    Args:
        text: The document text to store
        title: The document title
        api_key: OpenAI API key for embeddings
        entities: Optional dictionary containing entity information for reverse anonymization
                 Note: Entity information is stored separately in document metadata,
                 not in the vector database chunks, to ensure it's not exposed to the AI agent
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
        
        # Prepare documents for ChromaDB
        texts = [doc.page_content for doc in docs]
        metadatas = [
            {
                'source': title,
                'chunk_id': i
            } 
            for i in range(len(texts))
        ]
        
        # Add documents to the collection
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=[f"{document_hash}_{i}" for i in range(len(texts))]
        )
        
        # Add metadata for the new document
        document_metadata[document_hash] = {
            'title': title,
            'length': len(text),
            'chunks': len(texts)
        }
        
        # Store entity information if provided
        if entities and isinstance(entities, dict):
            # Ensure entities have the expected structure
            if "Text" in entities and "Replacement" in entities and "Category" in entities:
                document_metadata[document_hash]['entities'] = entities
        
        # Save updated metadata
        save_document_metadata(persist_directory, document_metadata)
    
    return collection

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
    
    # Save DataFrame to parquet for efficient storage
    df_path = f"./data_storage/{file_hash}.parquet"
    df.to_parquet(df_path)
    
    # Load existing metadata
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}
    
    # Add new dataset metadata
    metadata[file_hash] = {
        "title": title,
        "file_path": df_path,
        "columns": list(df.columns),
        "shape": df.shape,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "timestamp": time.time()
    }
    
    # Save updated metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

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
                datasets[info["title"]] = df
            else:
                st.warning(f"Dataset file not found: {info['title']}")
        except Exception as e:
            st.warning(f"Could not load dataset {info['title']}: {e}")
    
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
    content_str = f"{file_name}_{file_type}_{len(file_content)}"
    return hashlib.md5(content_str.encode()).hexdigest()

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
def search_documents(query: str, doc_sources: Optional[str] = None) -> str:
    """
    Search through uploaded text documents using semantic similarity.
    
    Args:
        query: The search query to find relevant information in documents
        doc_sources: Optional comma-separated list of document titles to search in specific documents
    
    Returns:
        Relevant text passages from documents with source information
    """
    if not hasattr(st.session_state, 'vector_db') or st.session_state.vector_db is None:
        return "No text documents are currently loaded in the database."
    
    try:
        # Parse doc_sources if provided
        selected_sources = None
        if doc_sources:
            # Convert document titles to hashes if needed
            # For now, use the existing selected_doc_sources
            selected_sources = st.session_state.get("selected_doc_sources", [])
        
        # Query the vector database
        context_docs, context_metadatas = query_vector_db(
            st.session_state.vector_db, 
            query,
            n_results=5,
            selected_doc_sources=selected_sources
        )
        
        if not context_docs:
            return f"No relevant information found in documents for query: '{query}'"
        
        # Format results for the LLM
        result = f"Found {len(context_docs)} relevant passages for '{query}':\n\n"
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
    # Get available datasets from session state
    available_datasets = st.session_state.get("tabular_datasets", {})
    
    if not available_datasets:
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
        return f"{dataset_info}\n\nQuery: {query}\n\nResult:\n{result['output']}"
        
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
    available_datasets = st.session_state.get("tabular_datasets", {})
    
    if not available_datasets:
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
def create_visualization(chart_type: str, dataset_name: Optional[str] = None, x_column: Optional[str] = None, y_column: Optional[str] = None, title: Optional[str] = None) -> str:
    """
    Create charts and visualizations from tabular data.
    
    Args:
        chart_type: Type of chart to create (bar, line, scatter, histogram, pie, heatmap, box)
        dataset_name: Name of the dataset to visualize (if not provided, uses first available)
        x_column: Column name for x-axis (required for most chart types)
        y_column: Column name for y-axis (required for some chart types)
        title: Optional title for the chart
    
    Returns:
        Status message about chart creation
    """
    if not VISUALIZATION_AVAILABLE:
        return "Visualization libraries are not available. Please install matplotlib, seaborn, and plotly."
    
    available_datasets = st.session_state.get("tabular_datasets", {})
    
    if not available_datasets:
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
            "data": chart_data.to_dict('records') if hasattr(chart_data, 'to_dict') else chart_data.to_dict(),
            "columns": list(chart_data.columns) if hasattr(chart_data, 'columns') else None
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
        chart_description += f"**Data Points:** {len(chart_data)} rows\n\n"
        chart_description += f"[CHART_ID:{chart_id}]"  # Hidden marker for chart identification
        
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
        
        # Recreate the chart based on type
        if chart_type == "bar":
            fig = px.bar(df, x=x_column, y=y_column, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x_column, y=y_column, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_column, y=y_column, title=title)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_column, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, values=y_column, names=x_column, title=title)
        elif chart_type == "box":
            if x_column and x_column in df.columns:
                fig = px.box(df, x=x_column, y=y_column, title=title)
            else:
                fig = px.box(df, y=y_column, title=title)
        elif chart_type == "heatmap":
            fig = px.imshow(df, text_auto=True, title=title)
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

def create_unified_agent():
    """
    Create a unified agent that can work with both text documents and tabular data.
    
    Returns:
        AgentExecutor: The configured agent executor
    """
    if not TOOLS_AVAILABLE:
        st.error("Tool-calling functionality is not available. Please install required dependencies.")
        return None
    
    # Define all available tools
    tools = [
        search_documents,
        analyze_tabular_data,
        cross_reference_analysis,
        get_data_summary,
        create_visualization
    ]
    
    # Count available data sources
    num_documents = len(st.session_state.get('selected_doc_sources', []))
    num_datasets = len(st.session_state.get('tabular_datasets', {}))
    
    # Create custom prompt that understands the available data types
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an intelligent assistant that can analyze both text documents and tabular data.

Available capabilities:
- search_documents: Find information in uploaded text documents (PDFs, DOCX, transcripts, etc.)
- analyze_tabular_data: Perform analysis on CSV/Excel data using pandas operations
- cross_reference_analysis: Find connections between documents and data
- get_data_summary: Get overview information about available datasets
- create_visualization: Generate charts and graphs from tabular data (bar, line, scatter, histogram, pie, box, heatmap)

Current session contains:
- Text Documents: {num_documents} documents available for search
- Tabular Datasets: {num_datasets} datasets available for analysis

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

TOOL SELECTION STRATEGY:
- Chart/visualization requests → create_visualization (direct, multiple calls for multiple charts)
- Data analysis questions → analyze_tabular_data (direct)
- Document content questions → search_documents (direct)
- Questions needing both → cross_reference_analysis (single call)
- Data structure questions → get_data_summary (only when necessary)

IMPORTANT OUTPUT FORMATTING RULES:
- NEVER use markdown image syntax ![alt](url) in your responses
- DO NOT attempt to include icons, images, or visual elements in bullet points
- DO NOT generate any markdown that tries to display external images
- Focus on text-based descriptions and let the create_visualization tool handle all visual content
- When describing charts, use plain text descriptions without attempting to embed visual elements

When users ask questions:
1. Choose the MOST DIRECT tool approach - avoid multi-step processes
2. For multiple charts, call create_visualization once for EACH chart separately
3. Provide comprehensive answers that combine insights from all relevant sources
4. Always cite your sources and be specific about which documents or datasets you're referencing
5. If you hit iteration limits, summarize what you've found so far and suggest the user ask more specific questions
6. Use clear, text-only formatting - no visual elements or image references in your text responses
"""),
        ("user", "{input}"),
        ("assistant", "{agent_scratchpad}")
    ])
    
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
    with st.expander("📄 Document Sources", expanded=documents_expanded):
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
                            st.caption(f"Added: {timestamp.strftime('%Y-%m-%d')}")
                        except (ValueError, OSError):
                            st.caption("Added: Unknown")
                    
                    with col3:
                        if st.button("Remove", key=f"remove_{doc['hash']}"):
                            if st.session_state.get("confirm_delete") == doc['hash']:
                                # If already confirmed, perform the deletion
                                with st.spinner(f"Deleting '{doc['title']}'..."):
                                    success = delete_document_from_vector_db(doc['hash'])
                                    if success:
                                        st.rerun()
                                # Clear confirmation state
                                st.session_state["confirm_delete"] = None
                            else:
                                # Set confirmation state and show confirmation message
                                st.session_state["confirm_delete"] = doc['hash']
                                st.warning("Click 'Remove' again to confirm deletion.", icon="⚠️")
                
                # Store selected documents in session state
                if "selected_doc_sources" not in st.session_state or st.session_state.selected_doc_sources != selected_docs:
                    st.session_state.selected_doc_sources = selected_docs
                
                # Update metadata with active status
                for doc_hash in document_metadata:
                    document_metadata[doc_hash]['active'] = doc_hash in selected_docs
                save_document_metadata(persist_directory, document_metadata)
                
                # Add Clear Vector Database button at the end of document list
                st.divider()
                if hasattr(st.session_state, 'RAG_AVAILABLE') or RAG_AVAILABLE:
                    # Warning message before the button
                    st.warning("This will remove all documents from the database. This action cannot be undone.", icon="⚠️")
                    
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
                            st.error("Click 'Clear All Documents' again to confirm deletion of ALL documents.", icon="⚠️")
            else:
                st.info("No documents found in the database. Process a document to add it to the sources.")
        else:
            st.info("📄 No document sources loaded. Upload documents on the Home page and process them to add document sources.")
            st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)

    # Tabular Dataset Sources Section with Expander
    with st.expander("📊 Tabular Data Sources", expanded=datasets_expanded):
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
                            st.caption(f"Added: {timestamp.strftime('%Y-%m-%d')}")
                        except (ValueError, OSError):
                            st.caption("Added: Unknown")
                    
                    with col3:
                        if st.button("Remove", key=f"remove_dataset_{dataset['hash']}"):
                            if st.session_state.get("confirm_delete_dataset") == dataset['hash']:
                                # If already confirmed, perform the deletion
                                with st.spinner(f"Deleting '{dataset['title']}'..."):
                                    success = delete_tabular_dataset(dataset['hash'])
                                    if success:
                                        st.rerun()
                                # Clear confirmation state
                                st.session_state["confirm_delete_dataset"] = None
                            else:
                                # Set confirmation state and show confirmation message
                                st.session_state["confirm_delete_dataset"] = dataset['hash']
                                st.warning("Click 'Remove' again to confirm deletion.", icon="⚠️")
                
                # Store selected datasets in session state
                if "selected_datasets" not in st.session_state or st.session_state.selected_datasets != selected_datasets:
                    st.session_state.selected_datasets = selected_datasets
                
                # Update metadata with active status
                for file_hash, dataset_data in tabular_metadata.items():
                    dataset_data['active'] = dataset_data['title'] in selected_datasets
                # Note: We would need to add a save function for tabular metadata if we want to persist active status
                
                # Add Clear All Datasets button
                st.divider()
                st.warning("This will remove all datasets from storage. This action cannot be undone.", icon="⚠️")
                
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
                        st.error("Click 'Clear All Datasets' again to confirm deletion of ALL datasets.", icon="⚠️")
            else:
                st.info("No datasets found in storage. Upload a CSV or Excel file to add datasets.")
                st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)
        else:
            st.info("📊 No tabular datasets loaded. Upload CSV or Excel files on the Home page to add datasets.")
            st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)

