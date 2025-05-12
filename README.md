# DTN Reporting Tools
A Python app to convert transcripts, anonymize content and ask ChatGPT for processing summaries and insights.

## Overview
This application provides a streamlined workflow for processing meeting transcripts:
1. **Upload & Extract** - Upload and convert files (.docx, .vtt, .pdf) into text content
2. **Anonymize** - Replace sensitive information with generic placeholders
3. **ChatGPT** - Use AI to analyze and summarize the anonymized content
4. **Revert** - Convert anonymized content back to its original form

## Features
- **File Support**: Support for Teams/Zoom .vtt files, Teams .docx files, regular .docx documents, and PDF files
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
1. **Upload & Extract**: Upload a file (.vtt, .docx, .pdf) or paste text directly
2. **Anonymize Content**: Automatically detect and replace sensitive entities
3. **ChatGPT Tool**: Ask questions about the anonymized content using RAG
4. **Reverse Anonymization**: Convert anonymized responses back to original form

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

# DTN Reporting Tools - Privacy Features

## Entity Privacy in RAG System

The application implements a privacy-preserving approach for handling sensitive entity information in the Retrieval Augmented Generation (RAG) system:

### How Entity Privacy Works

1. **Separate Storage**: 
   - Anonymized content is stored in the vector database for semantic search
   - Entity mappings (original text → anonymized text) are stored separately in document metadata
   - Entity information is never included in the vector embeddings

2. **Filtered Metadata**:
   - When retrieving context chunks, the `query_vector_db` function filters metadata
   - Only safe fields like 'source' and 'chunk_id' are returned to the AI agent
   - Entity mappings are completely removed from metadata before sending to OpenAI

3. **Safe Context Construction**:
   - When constructing the prompt for the AI, only document content and safe metadata are included
   - The AI receives only anonymized text, with no access to the original entities

4. **Reverse Anonymization**:
   - Entity mappings are available for the reverse anonymization process
   - This happens locally, after the AI has generated its response

This ensures that sensitive information like names, locations, and organizations remain private while still allowing the system to provide relevant answers and perform reverse anonymization when needed.