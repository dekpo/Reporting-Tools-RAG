# Packages
import streamlit as st
import streamlit_antd_components as sac
import spacy
from typing import List, Union, Dict, Any
from openai import OpenAI
import os
import json
import hashlib
import shutil

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
APP_VERSION = "2.0"

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

def save_convert(title,data,inputs):
    st.session_state["saved_convert"] = {
        "Time": current_datetime,
        "Title": title,
        "Data": data,
        "Inputs": inputs
    }

def save_content(title,content,attendees):
    st.session_state["saved_content"] = {
        "Time": current_datetime,
        "Title": title,
        "Data": content,
        "Attendees": attendees

    }

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
        case "saved_convert":
            name = "Converted Transcripts"
            icon = ":date:"
            page = "pages/01_convert.py"
        case "saved_content":
            name = "Extracted Content"
            icon = ":page_with_curl:"
            page = "pages/02_extract.py"
        case "saved_anonymisation":
            name = "Anonymized Content"
            icon = ":speech_balloon:"
            page = "pages/03_anonymize.py"   
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
    st.sidebar.page_link(page="pages/01_convert.py",label="Convert Transcripts",icon=":material/table:")
    st.sidebar.page_link(page="pages/02_extract.py",label="Extract Content",icon=":material/chat:")
    st.sidebar.page_link(page="pages/03_anonymize.py",label="Anonymize Content",icon=":material/sms:")
    st.sidebar.page_link(page="pages/04_chatgpt.py",label="ChatGPT Tool",icon=":material/hexagon:")
    st.sidebar.page_link(page="pages/05_revert.py",label="Reverse Anonymization",icon=":material/comment:")

    if "saved_convert" in st.session_state or "saved_content" in st.session_state or "saved_anonymisation" in st.session_state:
        st.sidebar.header(":floppy_disk: Your Backup",divider=True)
        if "saved_convert" in st.session_state:
            st.sidebar.write(":date: **Converted Transcripts**")
            if st.sidebar.button(label=f":wastebasket: {st.session_state["saved_convert"]["Title"][:18]}...",type="secondary",key="del_button01",use_container_width=True):
                del_dialog("saved_convert")
        if "saved_content" in st.session_state:
            st.sidebar.write(":page_with_curl: **Extracted Content**")
            if st.sidebar.button(label=f":wastebasket: {st.session_state["saved_content"]["Title"][:18]}...",type="secondary",key="del_button02",use_container_width=True):
                del_dialog("saved_content")
        if "saved_anonymisation" in st.session_state:
            st.sidebar.write(":speech_balloon: **Anonymized Content**")
            if st.sidebar.button(label=f":wastebasket: {st.session_state["saved_anonymisation"]["Title"][:18]}...",type="secondary",key="del_button03",use_container_width=True):
                del_dialog("saved_anonymisation")
    
    st.sidebar.divider()
    st.sidebar.text(f"Release Version {APP_VERSION}")

def steps(i):
    sac.steps(
        items=[
            sac.StepsItem(title='Convert Transcripts', subtitle='from raw', description='To CSV table', disabled=True),
            sac.StepsItem(title='Extract Content', subtitle='from csv', description='To DOCX document', disabled=True),
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

def create_vector_db_from_text(text, title, api_key):
    """
    Create a vector database from text content.
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
                return unfiltered_results["documents"][0][:n_results], unfiltered_results["metadatas"][0][:n_results]
            return [], []
        
        # If we have document sources selected, filter the results manually
        filtered_docs = []
        filtered_metadatas = []
        
        for i, doc_id in enumerate(unfiltered_results["ids"][0]):
            # Check if this document belongs to any of the selected sources
            if any(doc_hash in doc_id for doc_hash in selected_doc_sources):
                filtered_docs.append(unfiltered_results["documents"][0][i])
                filtered_metadatas.append(unfiltered_results["metadatas"][0][i])
                
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
    # Prepare source information
    source_info = []
    for metadata in context_metadatas:
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
    
    # Add the current query with context
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