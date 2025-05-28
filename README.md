# DTN Reporting Tools
A Python app to convert transcripts, anonymize content, ask ChatGPT for processing summaries and insights, and generate interactive charts from data.

## Overview
This application provides a streamlined workflow for processing meeting transcripts and analyzing data:
1. **Upload & Extract** - Upload and convert files (.docx, .vtt, .pdf, .csv, .xlsx) into text content or tabular data
2. **Anonymize** - Replace sensitive information with generic placeholders
3. **ChatGPT** - Use AI to analyze and summarize content, perform data analysis, and generate visualizations
4. **Revert** - Convert anonymized content back to its original form

## Features
- **File Support**: Support for Teams/Zoom .vtt files, Teams .docx files, regular .docx documents, PDF files, CSV files, and Excel files
- **Anonymization**: Automatically detect and replace sensitive entities (names, organizations, etc.)
- **RAG Integration**: Uses Retrieval-Augmented Generation for more accurate AI responses
- **Vector Database**: Store and retrieve documents using ChromaDB for semantic search
- **Data Analysis**: Advanced tabular data analysis using pandas and natural language queries
- **Chart Generation**: Create interactive visualizations from your data with simple prompts
- **Multi-modal Agent**: Unified AI agent that can work with both text documents and tabular data
- **Multi-page Interface**: Intuitive Streamlit UI with step-by-step workflow

## Chart Generation Capabilities

### Available Chart Types
- **Bar Charts** - For comparing categories and values
- **Line Charts** - For showing trends over time
- **Scatter Plots** - For exploring relationships between variables
- **Histograms** - For displaying data distribution
- **Pie Charts** - For showing proportions and percentages
- **Box Plots** - For statistical distribution analysis
- **Heatmaps** - For correlation matrices and pattern visualization

### Example Prompts for Chart Generation

#### Bar Charts
```
"Create a bar chart showing sales by region using the revenue column"
"Make a bar chart of product categories vs total sales"
"Show me a bar chart comparing department budgets"
```

#### Line Charts
```
"Create a line chart showing sales trends over time"
"Generate a line chart of monthly revenue progression"
"Show me how customer satisfaction changed over the quarters"
```

#### Scatter Plots
```
"Create a scatter plot of price vs sales volume"
"Show me a scatter plot comparing age and income"
"Generate a scatter plot of marketing spend vs revenue"
```

#### Pie Charts
```
"Create a pie chart showing market share by company"
"Generate a pie chart of budget allocation by department"
"Show me a pie chart of customer segments"
```

#### Histograms
```
"Create a histogram of customer ages"
"Show me a histogram of order values"
"Generate a histogram of response times"
```

#### Box Plots
```
"Create a box plot of salaries by department"
"Generate a box plot showing price distribution"
"Show me a box plot of performance scores by team"
```

#### Heatmaps
```
"Create a correlation heatmap of all numeric columns"
"Show me a heatmap of relationships between variables"
"Generate a correlation matrix for the financial data"
```

### How to Use Chart Generation

1. **Upload Your Data**: 
   - Upload CSV or Excel files through the home page
   - Your data will be automatically processed and made available for analysis

2. **Navigate to ChatGPT Tool**: 
   - Go to the ChatGPT Tool page
   - Ensure your datasets are selected in the "Tabular Data Sources" section

3. **Request Charts with Natural Language**:
   - Use any of the example prompts above
   - The AI will automatically detect appropriate columns and create visualizations
   - Charts will appear directly in the chat interface

4. **Customize Your Charts**:
   - Specify exact column names for precision
   - Add custom titles and labels
   - Combine multiple chart types in a single conversation

### Pro Tips for Chart Generation

- **Be Specific with Column Names**: *"Create a bar chart with 'Product_Name' on x-axis and 'Revenue' on y-axis"*
- **Add Custom Titles**: *"Create a line chart of sales over time with title 'Q4 Performance Trends'"*
- **Ask for Suggestions**: *"What's the best way to visualize my sales data?"* - The AI will recommend optimal chart types
- **Combine Analysis with Visualization**: *"Analyze the top 5 products by revenue and create a bar chart"*
- **Cross-Reference Data**: *"Show me a correlation between the survey responses and the sales data"*
- **Multiple Charts**: You can request several different charts in the same conversation
- **Data Exploration**: *"Show me the data summary first, then create appropriate visualizations"*

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
1. **Upload & Extract**: Upload files (.vtt, .docx, .pdf, .csv, .xlsx) or paste text directly
2. **Anonymize Content**: Automatically detect and replace sensitive entities (text documents only)
3. **ChatGPT Tool**: Ask questions, perform analysis, and generate charts using the unified AI agent
4. **Reverse Anonymization**: Convert anonymized responses back to original form (text documents only)

## Dependencies
- streamlit - Web application framework
- openai - OpenAI API client
- langchain - Framework for LLM applications
- chromadb - Vector database for document storage and retrieval
- spacy - NLP library for entity recognition
- docx2txt, python-docx - For processing Word documents
- webvtt-py - For processing VTT subtitle files
- pandas - For data manipulation and analysis
- PyMuPDF, PyPDF2 - For PDF processing
- matplotlib, seaborn, plotly - For chart generation and data visualization
- openpyxl - For Excel file processing

## Data Storage
- Session state for temporary storage during workflow
- ChromaDB for persistent vector storage of documents
- Local parquet files for efficient tabular data storage
- Logging functionality for tracking application usage

## Advanced Features
- **RAG (Retrieval-Augmented Generation)** for more accurate AI responses
- **Multi-modal AI Agent** that can work with both text and tabular data simultaneously
- **Interactive Visualizations** with Plotly for dynamic chart exploration
- **Document chunking** for efficient processing of large documents
- **Entity recognition and anonymization** with customizable categories
- **Vector search** for finding relevant content across documents
- **Cross-reference analysis** between documents and datasets
- **Natural language data analysis** using pandas operations

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