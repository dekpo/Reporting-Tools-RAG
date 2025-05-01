# Packages
import streamlit as st
import docx2txt
import pandas as pd
import webvtt

# Modules
from io import StringIO
import re
import html

# Utils
import lib

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.title(lib.APP_TITLE)

st.divider()

# Steps
lib.steps(0)

st.divider()

st.header("Convert Transcripts")

st.markdown("<p>Convert raw transcripts (.docx or .vtt file) to a table (.csv file) using this tool, grouping all agenda items by theme.<br>After uploading your transcripts file, <b>please specify default information</b> about your meeting. Don't worry you'll be able to change those informations later.</p>",unsafe_allow_html=True)


st.subheader("Upload Your Meeting's Transcript File")

file_type = st.radio("**Now specify what type of file you want to process with:**",["**.vtt** file from Teams or Zoom","**.docx** file from Teams"])
    
if  ".docx" in file_type:
    file_mime = 'docx'
    min_length_input = 10
else:
    file_mime = 'vtt'
    file_info = 'VTT'
    min_length_input = 5

if "saved_convert" in st.session_state:
    min_length_input = st.session_state["saved_convert"]["Inputs"]["min_length_input"]

upload = st.file_uploader(f"**Please Upload** Your Transcripts File Here: {file_type}", type=[file_mime],accept_multiple_files=False,help=f"Browse your computer to select only one .vtt or .docx raw transcripts file")

process_error_string = "**Sorry there was an error processing this file.** Is it a raw transcripts file ? (.docx or .vtt)"
webvtt_error_string = "**Sorry but** this document does not seems to be a valid .vtt file"

st.subheader("Provide Meeting's Default Information")

if "saved_convert" not in st.session_state:
    default_meeting = "Your Meeting"
else:
    default_meeting = st.session_state["saved_convert"]["Inputs"]["meeting_input"]
meeting_input = st.text_input("**Meeting*** (mandatory)",default_meeting,help="What was the name of the meeting ?")
if not meeting_input:
    meeting_input = default_meeting

if "saved_convert" not in st.session_state:
    default_topic = "Your Topic"
else:
    default_topic = st.session_state["saved_convert"]["Inputs"]["topic_input"]
topic_input = st.text_input("**Topic*** (mandatory)",default_topic,help="What was the main topic of the meeting ?")
if not topic_input:
    topic_input = default_topic

if "saved_convert" not in st.session_state:
    default_item = "Your Item"
else:
    default_item = st.session_state["saved_convert"]["Inputs"]["item_input"]
item_input = st.text_input("**Item*** (mandatory)",default_item,help="What was the default item of the meeting ?")
if not item_input:
    item_input = default_item

if "saved_convert" not in st.session_state:
    default_segment = "Discussion"
else:
    default_segment = st.session_state["saved_convert"]["Inputs"]["segment_input"]
segment_input = st.text_input("**Segment*** (mandatory)",default_segment,help="What was the default segment of this meeting ?")
if not segment_input:
    segment_input = default_segment

saving_inputs = {
    "meeting_input":    meeting_input,
    "topic_input":      topic_input,
    "item_input":       item_input,
    "segment_input":    segment_input,
    "min_length_input": min_length_input
}

st.subheader("Clear Short Messages")

min_length_input = st.slider(label=f"**Ignore short sentences ?** (that are less than xx characters) ", min_value=0, max_value=100, value=min_length_input,help=f"The conversion process can ignore sentences of less than {min_length_input} characters for example")

st.write(f"The conversion process will ignore sentences of **less than {min_length_input} characters.**",unsafe_allow_html=True)

data = {
    "ID": [],
    "Time":[],
    "Meeting":[],
    "Topic":[],
    "Item":[],
    "Segment":[],
    "Attendee":[],
    "Message":[]
}

if upload:

    st.divider()

    error = ""
    if file_mime == "docx":
        try:
            txt = docx2txt.process(upload)
        except:
            error = st.warning(process_error_string, icon="⚠️")
        if error == "":
            count_arrows = txt.count(" --> ")
            if count_arrows > 2:
                file_info = "Old"
            else:
                file_info = "New"

            rows = txt.split("\n\n")

    if file_mime == "vtt":
        try:
            stringio = StringIO(upload.getvalue().decode("utf-8"))
        except:
            error = st.warning(process_error_string, icon="⚠️")
        try:
            rows = webvtt.from_buffer(stringio)
        except:
            error = st.warning(webvtt_error_string, icon="⚠️")

    if error == "":
        index = 0
        for row in rows:
            # New way to process docx files
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
                        if len(line) >= 1 and meeting_input and topic_input and item_input and segment_input:
                            if len(message) >= min_length_input:
                                data["ID"].append(index)
                                data["Time"].append(timing)
                                data["Meeting"].append(meeting_input)
                                data["Topic"].append(topic_input)
                                data["Item"].append(item_input)
                                data["Segment"].append(segment_input)
                                data["Attendee"].append(attendee)
                                data["Message"].append(message)
                                index +=1
                        else:
                            error = st.warning(process_error_string, icon="⚠️")
                            break
            
            # Old way to process docx files
            if file_info == "Old":
                line = row.split('\n')
                if len(line) == 3 and meeting_input and topic_input and item_input and segment_input:
                    if len(line[2]) >= min_length_input:
                        data["ID"].append(index)
                        data["Time"].append(line[0])
                        data["Meeting"].append(meeting_input)
                        data["Topic"].append(topic_input)
                        data["Item"].append(item_input)
                        data["Segment"].append(segment_input)
                        data["Attendee"].append(line[1])
                        data["Message"].append(line[2])
                        index +=1
                elif len(line) == 2 and meeting_input and topic_input and item_input and segment_input:
                    if len(line[1]) >= min_length_input:
                        data["ID"].append(index)
                        data["Time"].append(line[0])
                        data["Meeting"].append(meeting_input)
                        data["Topic"].append(topic_input)
                        data["Item"].append(item_input)
                        data["Segment"].append(segment_input)
                        data["Attendee"].append("Attendee")
                        data["Message"].append(line[1])
                        index +=1
                else:
                        error = st.warning(process_error_string, icon="⚠️")
                        break
            
                # Way to process vtt files
            if file_info == "VTT":
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
                        if len(message) >= min_length_input:
                            data["ID"].append(index)
                            data["Time"].append(row.start)
                            data["Meeting"].append(meeting_input)
                            data["Topic"].append(topic_input)
                            data["Item"].append(item_input)
                            data["Segment"].append(segment_input)
                            data["Attendee"].append(attendee)
                            data["Message"].append(message)
                            index +=1
                    else:
                        error = st.warning(process_error_string, icon="⚠️")
                        break
    

    if error == "" and len(data) > 1:
    
        st.subheader("Edit Your Data Like An Excel Table")

        df = pd.DataFrame(data)
        
        st.markdown(f"You have **{len(df)} rows** to edit.")
        edited_data = st.data_editor(df,num_rows="dynamic",disabled=["ID","Time","Meeting"],use_container_width=True,hide_index=True)

        
        if len(df) > 0:
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8')

            csv_file = convert_df(edited_data)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    label="**Download Data As CSV File**",
                    type="secondary",
                    data=csv_file,
                    file_name=f'{lib.current_datetime}_converted_transcripts.csv',
                    mime='text/csv',
                )
            with col2:
                st.write("OR")
            
            with col3:
                if st.button(label="**Save Data For Next Step >> Extract Content**",type="primary", on_click=lib.save_convert,args=[meeting_input,edited_data,saving_inputs]):
                    st.switch_page("./pages/02_extract.py")
        else:
            st.warning(process_error_string, icon="⚠️")

elif "saved_convert" in st.session_state:

    st.subheader("Edit Your Data Like An Excel Table")

    df = pd.DataFrame(st.session_state["saved_convert"]["Data"])
    
    df["Meeting"] = meeting_input
    df["Topic"] = topic_input
    df["Item"] = item_input
    df = df.drop(df[df["Message"].map(len) <= min_length_input].index)
    df.reset_index(drop=True, inplace=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(f"You have **{len(df)} rows** to edit from your previous backup **{st.session_state["saved_convert"]["Time"]}**")
    with col_right:
        if st.button(label="**Delete This Backup (are you sure ?)**",type="secondary"):
            del st.session_state["saved_convert"]
            st.switch_page("./pages/01_convert.py")

    edited_data = st.data_editor(df,num_rows="dynamic",disabled=["ID","Time","Meeting"],use_container_width=True,hide_index=True)

    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv_file = convert_df(edited_data)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="**Download Data As CSV File**",
            type="secondary",
            data=csv_file,
            file_name=f'{lib.current_datetime}_converted_transcripts.csv',
            mime='text/csv',
        )
    with col2:
        st.write("OR")
    
    with col3:
        if st.button(label="**Save Data For Next Step >> Extract Content**",type="primary", on_click=lib.save_convert,args=[meeting_input,edited_data,saving_inputs]):
            st.switch_page("./pages/02_extract.py")

else:
    st.divider()

    st.subheader("Your Data Will Be Displayed Here")
    st.markdown(f"You have **no row** to edit for now.")
    st.dataframe(data,use_container_width=True)