# Packages
import streamlit as st
import spacy
import pandas as pd
from docx import Document
from PyPDF2 import PdfReader
import docx2txt
import hashlib

# Modules
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

# Steps - updated to show position 1 in the new 4-step process
# lib.steps(0)

# st.divider()

st.header("Anonymize Content")

st.markdown("<p>Apply anonymity to entities (people, organizations, locations...) using this tool, keeping references relating to entities considered substantive to discussion.</p>",unsafe_allow_html=True)

# Initialize or load SpaCy model from session state (OPTIMIZATION: Cache model loading)
@st.cache_resource
def load_spacy_model():
    """Load SpaCy model once and cache it"""
    return spacy.load('./en_core_web_md')

# Load the model (cached)
nlp = load_spacy_model()

# Helper function to generate content hash for caching
def generate_content_hash(content, labels_config):
    """Generate a hash for content and configuration to detect changes"""
    content_str = str(content) + str(labels_config)
    return hashlib.md5(content_str.encode()).hexdigest()

# Helper function to process entities (OPTIMIZATION: Batch processing)
@st.cache_data
def extract_entities_batch(text_content, selected_labels, label_replacements):
    """Extract entities from text using batch processing with caching"""
    
    # Split text into manageable chunks for SpaCy processing
    max_chunk_size = 1000000  # 1MB chunks for optimal SpaCy performance
    text_chunks = []
    
    if len(text_content) > max_chunk_size:
        # Split into chunks
        chunks = [text_content[i:i+max_chunk_size] for i in range(0, len(text_content), max_chunk_size)]
        text_chunks = chunks
    else:
        text_chunks = [text_content]
    
    # Process chunks efficiently
    selected = {}
    for label in selected_labels:
        selected[label] = {
            "Entity": [],
            "Replacement": []
        }
    
    # Process each chunk
    for chunk in text_chunks:
        # Split chunk into paragraphs for processing
        paragraphs = [p.strip() for p in chunk.split("\n") if len(p.strip()) >= 10]
        
        # Use SpaCy's pipe method for efficient batch processing
        docs = list(nlp.pipe(paragraphs, batch_size=50))
        
        for doc in docs:
            for entity in doc.ents:
                text = entity.text.replace(".", "")
                label_ = entity.label_
                
                if (label_ in selected_labels and 
                    len(text) >= 2 and 
                    text.find("Attendee") == -1 and 
                    text not in selected[label_]["Entity"]):
                    
                    selected[label_]["Entity"].append(text)
                    replacement = label_replacements[label_]
                    replacement_str = f"{replacement}{lib.add_zero(len(selected[label_]['Entity']) - 1)}"
                    selected[label_]["Replacement"].append(replacement_str)
    
    return selected

pipe_labels = {
        "Label":[],
        "Description":[],
        "Replacement":[],
        "Apply":[]
}

default_labels = [
        "GPE",
        "ORG",
        "PERSON"
]
default_replacements = [
        "Location",
        "Organization",
        "Person"
]

# Build the pipe_labels structure
for label in nlp.pipe_labels['ner']:
    if label in default_labels:
        pipe_labels["Label"].append( label )
        pipe_labels["Description"].append( spacy.explain( label ))
        pipe_labels["Apply"].append( True )
        index = default_labels.index( label )
        pipe_labels["Replacement"].append( default_replacements[index] )

st.subheader("Choose entity categories")
st.write(f'**{len(pipe_labels["Label"])} categories** of entities to anonymize.')

edited_labels = st.data_editor(pipe_labels,disabled=["Label","Description"],use_container_width=True)

# Check if content exists
if "saved_content" not in st.session_state:
    st.info("Please upload your document on the home page first.")
    st.page_link(page="pages/00_home.py", label="Go To Home Page", icon=":material/home:", use_container_width=True)
else:
    # Get content
    title = st.session_state["saved_content"]["Title"]
    txt = st.session_state["saved_content"]["Data"]
    
    # Create configuration for caching
    selected_labels = [edited_labels["Label"][i] for i, apply in enumerate(edited_labels["Apply"]) if apply]
    label_replacements = {edited_labels["Label"][i]: edited_labels["Replacement"][i] 
                         for i, apply in enumerate(edited_labels["Apply"]) if apply}
    
    # Generate hash for current content and configuration
    content_hash = generate_content_hash(txt, {"labels": selected_labels, "replacements": label_replacements})
    
    # Check if we need to reprocess (OPTIMIZATION: Avoid redundant processing)
    cache_key = f"entities_cache_{content_hash}"
    
    if cache_key not in st.session_state or st.session_state.get("force_reprocess", False):
        # Only show processing spinner when actually processing
        with st.spinner('Processing entities... Please wait.'):
            # Process entities (cached function will handle efficiency)
            selected = extract_entities_batch(txt, selected_labels, label_replacements)
            
            # Cache the results
            st.session_state[cache_key] = selected
            st.session_state["last_processed_hash"] = content_hash
            
            # Reset force reprocess flag
            if "force_reprocess" in st.session_state:
                del st.session_state["force_reprocess"]
    else:
        # Use cached results
        selected = st.session_state[cache_key]
    
    # Build document_entities structure from selected entities
    document_entities = {
        "Text": [],
        "Replacement": [],
        "Category": []
    }
    
    # Only proceed if we have entities to process
    if len(selected) > 0 and any(len(selected[cat]["Entity"]) > 0 for cat in selected):
        tab1, tab2 = st.tabs(["Edit entity by categories", "Edit all entities and save references"])

        with tab1:
            st.write(f'**{len(selected)} categorie(s)** of entities selected.')  
            edited_selected = {}
            for category in selected:
                if len(selected[category]["Entity"]) > 0:  # Only show categories with entities
                    st.subheader(f'{category}: **{len(selected[category]["Entity"])} entities** ')
                    edited_selected[category] = st.data_editor(selected[category],num_rows="dynamic",use_container_width=True,key=f"{category}_{content_hash}")
                else:
                    edited_selected[category] = selected[category]

            # Build document_entities from edited data
            for category in edited_selected:
                for i, entity in enumerate(edited_selected[category]["Entity"]):
                    if entity not in document_entities["Text"]:
                        document_entities["Text"].append(entity)
                        document_entities["Replacement"].append(edited_selected[category]["Replacement"][i])
                        document_entities["Category"].append(category)
                        
        with tab2:
            st.subheader(f'All Categories: **{len(document_entities["Text"])} entities** to anonymize.')
            edited_entities = st.data_editor(document_entities,num_rows="dynamic",disabled=["Category"],use_container_width=True,key=f"all_entities_{content_hash}")
            
            @st.cache_data
            def convert_df(df):
                # IMPORTANT: Cache the conversion to prevent computation on every rerun
                return df.to_csv(index=True).encode('utf-8')
            
            all_entities = pd.DataFrame(edited_entities)
            csv = convert_df(all_entities)

            st.download_button(
                label="**Download Your Entities Table As CSV File**",
                data=csv,
                file_name=f'{lib.current_datetime}_all_entities.csv',
                mime='text/csv',
            )
        
        anonymize_now = st.checkbox('**Anonymize All Entities Now ?**',key=f"anonymize_now_{content_hash}",value=True,help="This feature can automatically detect entities in the content and replace them.")

        st.divider()

        st.write("""<div id='top-content'></div>""",unsafe_allow_html=True)

        st.subheader("Your Anonymized Content's Below:")

        st.markdown("<p><a href='#download-or-save-your-data'>🔽Download Or Save Your Data At The Bottom Of This Page🔽</a></p>",unsafe_allow_html=True)

        content = st.container(border=True)

        content.write("""<div class='extracted-content' />""",unsafe_allow_html=True)

        # Apply anonymization if requested (OPTIMIZATION: More efficient text replacement)
        processed_txt = txt
        if anonymize_now:
            # Create replacement mapping for efficient processing
            replacement_map = {}
            for i, term in enumerate(edited_entities["Text"]):
                if term:
                    replacement = edited_entities["Replacement"][i]
                    category = edited_entities["Category"][i]
                    replacement_map[term] = f'<span class="entity {category.lower()}">{replacement}</span>'
            
            # Apply replacements efficiently
            for term, replacement in replacement_map.items():
                processed_txt = processed_txt.replace(term, replacement)
        
        processed_txt = processed_txt.replace("$","\\$")
        processed_txt = processed_txt.replace("\n","<br>")
        content.markdown(processed_txt,unsafe_allow_html=True)
        content_txt = lib.strip_tags(processed_txt)

        st.divider()

        st.subheader("Download Or Save Your Data")
        st.write(f"This content is {len(content_txt)} chars long.")

        col1, col2, col3 = st.columns(3)

        with col1:
            # OPTIMIZATION: Only create document when download is actually clicked
            @st.cache_data
            def create_download_doc(text_content):
                doc_download = Document()
                raw_text = lib.strip_tags(text_content)
                # Filter out invalid XML characters before adding to the document
                raw_text = lib.filter_xml_chars(raw_text)
                doc_download.add_paragraph(raw_text)
                bio = io.BytesIO()
                doc_download.save(bio)
                return bio.getvalue()
            
            doc_data = create_download_doc(processed_txt)
            st.download_button(
                label="**Download Your Content As DOCX File**",
                data=doc_data,
                file_name=f'{lib.current_datetime}_anonymised_content.docx',
                mime="docx"
            )
            
        with col2:
            st.write("OR")
            
        with col3:
            if st.button(label="**Save This Content For Next Step >> Ask ChatGPT**",type="primary",key=f"save_anonymisation_btn_{content_hash}", on_click=lib.save_anonymisation,args=[title,content_txt,document_entities]):
                st.switch_page("./pages/02_chatgpt.py")
                
        st.divider()
        st.markdown("<p><a href='#top-content'>🔼Go Back To The Top Of This Content🔼</a></p>",unsafe_allow_html=True)
    else:
        st.divider()
        st.subheader("Nothing To Anonymize.")
        st.info("No entities were found that match your selected categories, or all text segments were too short to process.")