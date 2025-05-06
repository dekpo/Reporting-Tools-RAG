# DTN Reporting Tools
A Python app to convert transcripts, extract contents and anonymize them to ask ChatGPT for processing summaries and insights.

## Overview
This application provides a streamlined workflow for processing meeting transcripts:
1. **Convert** - Transform raw transcripts (.docx or .vtt) into structured data
2. **Extract** - Pull out relevant content from the structured data
3. **Anonymize** - Replace sensitive information with generic placeholders
4. **ChatGPT** - Use AI to analyze and summarize the anonymized content
5. **Revert** - Convert anonymized content back to its original form

## Features
- **Transcript Conversion**: Support for Teams/Zoom .vtt files and Teams .docx files
- **Content Extraction**: Extract and organize meeting content by topic, item, and segment
- **Anonymization**: Automatically detect and replace sensitive entities (names, organizations, etc.)
- **RAG Integration**: Uses Retrieval-Augmented Generation for more accurate AI responses
- **Vector Database**: Store and retrieve documents using ChromaDB for semantic search
- **Multi-page Interface**: Intuitive Streamlit UI with step-by-step workflow

## Setup
```bash
$ git clone <this-repo-url> reporting-tools
$ cd reporting-tools
$ py -m venv .venv
$ . ./venv/bin/activate (Linux)
$ . .venv\Scripts\activate (Windows)
$ py -m pip install -r requirements.txt
```

## Running
```bash
$ streamlit run app.py
```

## Requirements
- Python 3.8+
- OpenAI API key (for ChatGPT and embedding functionality)
- Spacy model (en_core_web_md)

## Workflow
1. **Convert Transcripts**: Upload a .vtt or .docx file, provide meeting information
2. **Extract Content**: Organize and clean the transcript data
3. **Anonymize Content**: Automatically detect and replace sensitive entities
4. **ChatGPT Tool**: Ask questions about the anonymized content using RAG
5. **Reverse Anonymization**: Convert anonymized responses back to original form

## Dependencies
- streamlit - Web application framework
- openai - OpenAI API client
- langchain - Framework for LLM applications
- chromadb - Vector database for document storage and retrieval
- spacy - NLP library for entity recognition
- docx2txt, python-docx - For processing Word documents
- webvtt-py - For processing VTT subtitle files
- pandas - For data manipulation
- PyMuPDF, PyPDF2 - For PDF processing

## Data Storage
- Session state for temporary storage during workflow
- ChromaDB for persistent vector storage of documents
- Logging functionality for tracking application usage

## Advanced Features
- RAG (Retrieval-Augmented Generation) for more accurate AI responses
- Document chunking for efficient processing of large documents
- Entity recognition and anonymization with customizable categories
- Vector search for finding relevant content across documents