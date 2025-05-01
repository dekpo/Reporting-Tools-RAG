# Packages
import streamlit as st
import spacy
import pandas as pd
from docx import Document
from PyPDF2 import PdfReader
import docx2txt

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

# Steps
lib.steps(2)

st.divider()

st.header("Anonymize Content")

st.markdown("<p>Apply anonymity to entities (people, organizations, locations...) using this tool, keeping references relating to entities considered substantive to discussion.</p>",unsafe_allow_html=True)

nlp = spacy.load('./en_core_web_md')

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
for label in nlp.pipe_labels['ner']:
    
    if label in default_labels:
        pipe_labels["Label"].append( label )
        pipe_labels["Description"].append( spacy.explain( label ))
        pipe_labels["Apply"].append( True )
        index = default_labels.index( label )
        pipe_labels["Replacement"].append( default_replacements[index] )

st.subheader("Choose entity categories")
st.write(f'**{len(pipe_labels["Label"])} categories** of entities to anonymize.')

edited_labels = st.data_editor(pipe_labels,disabled=["Label","Description"],use_container_width=True )


text_area = ""
if "saved_content" not in st.session_state:

    st.subheader("Do You Want To Anonymize Free Text ?")
    default_title = "Your Subject"
    title_input = st.text_input("**Subject*** (mandatory)",default_title,help="What is the title item of the content you want to anonymize?")
    text_value = ""

    upload_docx = st.file_uploader("**Upload a DOCX file**",type=["docx"],accept_multiple_files=False,help=f"You can upload a DOCX file with long text")
    if upload_docx is not None:
        with st.spinner('Extracting content from DOCX file... Please Wait.'):
            text_value = docx2txt.process(upload_docx)
            time.sleep(1)

    upload_pdf = st.file_uploader("**Or upload a PDF file**",type=["pdf"],accept_multiple_files=False,help=f"You can upload a PDF file with long text")
    if upload_pdf is not None:
        with st.spinner('Extracting content from PDF file... Please Wait.'):
            pdf_reader = PdfReader(upload_pdf)
            for page in pdf_reader.pages:
                text_value+= page.extract_text()
            time.sleep(1)

    text_area = st.text_area("**Or simply paste Your Free Text Here**", help="As you have no summary in your backups you can anonymize free text.",height=400,value=text_value)
    st.button("Anonymize This Free Text",type="primary", key="anonymize_free_text")
    

if ("saved_content" in st.session_state or len(text_area)>0):
    with st.spinner('Analysing content... Please Wait.'):
         time.sleep(3)
    if "saved_content" not in st.session_state:
        title = title_input if title_input else default_title
        txt = ''.join(c for c in text_area if lib.valid_xml_char_ordinal(c))
    else:
        title = st.session_state["saved_content"]["Title"]
        txt = st.session_state["saved_content"]["Data"]

    parags = txt.split("\n")
    
    entities = {}
    selected = {}
    label_index = 0
    for label in edited_labels["Apply"]:
        if label:
            selected[edited_labels["Label"][label_index]] = {
                "Entity":[],
                "Replacement":[]
            }
        label_index = label_index + 1

    document_entities = {
        "Text":[],
        "Replacement":[],
        "Category":[]
    }

    parag_fuse = 0
    parag_max = 100000
    with st.spinner('Anonymization in progress... Please Wait.'):
        time.sleep(2)
        for parag in parags:
            
            if len(parag) >= 10:
                doc = nlp(parag)
                entities = list(doc.ents)

                for entity in entities:
                    text = entity.text
                    text = text.replace(".","")
                    label_ = entity.label_

                    if label_ in edited_labels["Label"]:
                        label_index = edited_labels["Label"].index(label_)
                        if edited_labels["Apply"][label_index] and text not in selected[label_]["Entity"] and len(text)>=2 and text.find("Attendee") == -1:
                            selected[label_]["Entity"].append( text )
                            index = selected[label_]["Entity"].index(text)
                            replacement = edited_labels["Replacement"][label_index]
                            replacement_str = f"{replacement}{lib.add_zero(index)}"
                            selected[label_]["Replacement"].append( replacement_str )
                if parag_fuse >= parag_max:
                    break
                parag_fuse = parag_fuse + 1

        # if len(entities) > 0 and len(selected) > 0:
        if len(selected) > 0:
            tab1, tab2 = st.tabs(["Edit entity by categories", "Edit all entities and save references"])

            with tab1:
                st.write(f'**{len(selected)} categorie(s)** of entities selected.')  
                edited_selected = {}
                for category in selected:
                    st.subheader(f'{category}: **{len(selected[category]["Entity"])} entities** ')
                    edited_selected[category] = st.data_editor(selected[category],num_rows="dynamic",use_container_width=True,key=category)

                    for entity in edited_selected[category]["Entity"]:
                        if entity not in document_entities["Text"]:
                            document_entities["Text"].append( entity )
                            index = edited_selected[category]["Entity"].index(entity)
                            replacement_str = edited_selected[category]["Replacement"][index]
                            document_entities["Replacement"].append( replacement_str )
                            document_entities["Category"].append( category )
            with tab2:
                st.subheader(f'All Categories: **{len(document_entities["Text"])} entities** to anonymize.')
                edited_entities = st.data_editor(document_entities,num_rows="dynamic",disabled=["Category"],use_container_width=True,key="all_entities")
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
            
            anonymize_now = st.checkbox('**Anonymize All Entities Now ?**',key="anonymize_now",value=True,help="This feature can automatically detect entities in the content and replace them.")

            st.divider()

            st.write("""<div id='top-content'></div>""",unsafe_allow_html=True)

            st.subheader("Your Anonymized Content's Below:")

            st.markdown("<p><a href='#download-or-save-your-data'>🔽Download Or Save Your Data At The Bottom Of This Page🔽</a></p>",unsafe_allow_html=True)

            content = st.container(border=True)

            content.write("""<div class='extracted-content' />""",unsafe_allow_html=True)

            if anonymize_now:
                for term in edited_entities["Text"]:
                    index = edited_entities["Text"].index(term)
                    replacement = edited_entities["Replacement"][index]
                    category = edited_entities["Category"][index]
                    if term:
                        txt = txt.replace(term,f'<span class="entity {category.lower()}">{replacement}</span>')
            txt = txt.replace("$","\\$")
            txt = txt.replace("\n","<br>")
            content.markdown(txt,unsafe_allow_html=True)
            content_txt = lib.strip_tags(txt)

            st.divider()

            st.subheader("Download Or Save Your Data")
            st.write(f"This content is {len(content_txt)} chars long.")

            col1, col2, col3 = st.columns(3)

            with col1:
                doc_download = Document()
                raw_text = lib.strip_tags(txt)
                doc_download.add_paragraph(raw_text)

                bio = io.BytesIO()
                doc_download.save(bio)
                if doc_download:
                    st.download_button(
                    label="**Download Your Content As DOCX File**",
                    data=bio.getvalue(),
                    file_name=f'{lib.current_datetime}_anonymised_content.docx',
                    mime="docx"
                    )
            with col2:
                st.write("OR")
            with col3:

                if st.button(label="**Save This Content For Next Step >> Ask ChatGPT**",type="primary",key="save_anonymisation_btn", on_click=lib.save_anonymisation,args=[title,content_txt,document_entities]):
                    st.switch_page("./pages/04_chatgpt.py")
            st.divider()
            st.markdown("<p><a href='#top-content'>🔼Go Back To The Top Of This Content🔼</a></p>",unsafe_allow_html=True)
        else:
            st.divider()
            st.subheader("Nothing To Anonymize.")