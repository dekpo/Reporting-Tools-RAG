# DTN Reporting Tools
A Python app to convert transcripts, anonymize content, ask ChatGPT for processing summaries and insights, and generate interactive charts from data.

## Overview
This application provides a streamlined workflow for processing meeting transcripts and analyzing data:
1. **Upload & Extract** - Upload and convert files (.docx, .vtt, .pdf, .csv, .xlsx) into text content or tabular data
2. **Anonymize** - Replace sensitive information with generic placeholders
3. **ChatGPT Analysis** - Use AI with advanced agent tools to analyze content, perform data analysis, and generate visualizations
4. **Revert** - Convert anonymized content back to its original form

## Features
- **File Support**: Support for Teams/Zoom .vtt files, Teams .docx files, regular .docx documents, PDF files, CSV files, and Excel files
- **Model Selection**: Choose from GPT-4o, GPT-4 Turbo, GPT-4, or GPT-3.5 Turbo models
- **Anonymization**: Automatically detect and replace sensitive entities (names, organizations, etc.)
- **Advanced AI Agent**: Multi-tool AI system with document search, data analysis, and visualization capabilities
- **RAG Integration**: Uses Retrieval-Augmented Generation for more accurate AI responses
- **Vector Database**: Store and retrieve documents using ChromaDB for semantic search
- **Data Analysis**: Advanced tabular data analysis using pandas and natural language queries
- **Chart Generation**: Create interactive visualizations from your data with simple prompts
- **Persistent Storage**: Cross-session data retention for documents and datasets
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
"Create a bar chart showing humanitarian aid distribution by region"
"Make a bar chart of program funding allocations by sector"
"Show me a bar chart comparing peacekeeping mission budgets"
```

#### Line Charts
```
"Create a line chart showing refugee population trends over time"
"Generate a line chart of development indicator progress by year"
"Show me how food security levels changed over the quarters"
```

#### Scatter Plots
```
"Create a scatter plot of development funding vs poverty reduction"
"Show me a scatter plot comparing education access and literacy rates"
"Generate a scatter plot of climate funding vs emission reductions"
```

#### Pie Charts
```
"Create a pie chart showing humanitarian funding by donor country"
"Generate a pie chart of program budget allocation by theme"
"Show me a pie chart of refugee populations by country of origin"
```

#### Histograms
```
"Create a histogram of beneficiary age distributions"
"Show me a histogram of project completion times"
"Generate a histogram of humanitarian response times"
```

#### Box Plots
```
"Create a box plot of program effectiveness scores by region"
"Generate a box plot showing funding distribution patterns"
"Show me a box plot of development indicators by country group"
```

#### Heatmaps
```
"Create a correlation heatmap of all development indicators"
"Show me a heatmap of relationships between humanitarian metrics"
"Generate a correlation matrix for the sustainable development goals data"
```

### How to Use Chart Generation

1. **Upload Your Data**: 
   - Upload CSV or Excel files through the home page
   - Your data will be automatically processed and stored persistently

2. **Navigate to ChatGPT Tool**: 
   - Go to the ChatGPT Tool page
   - Select your OpenAI model (GPT-4o recommended for best results)
   - Ensure your datasets are selected in the "Tabular Data Sources" section

3. **Request Charts with Natural Language**:
   - Use any of the example prompts above
   - The AI agent will automatically detect appropriate columns and create visualizations
   - Charts will appear directly in the chat interface

4. **Customize Your Charts**:
   - Specify exact column names for precision
   - Add custom titles and labels
   - Combine multiple chart types in a single conversation

### Pro Tips for Chart Generation

- **Be Specific with Column Names**: *"Create a bar chart with 'Country_Name' on x-axis and 'Funding_Amount' on y-axis"*
- **Add Custom Titles**: *"Create a line chart of aid distribution over time with title 'Q4 Humanitarian Response Trends'"*
- **Ask for Suggestions**: *"What's the best way to visualize my humanitarian data?"* - The AI will recommend optimal chart types
- **Combine Analysis with Visualization**: *"Analyze the top 5 countries by funding received and create a bar chart"*
- **Cross-Reference Data**: *"Show me a correlation between the survey responses and the program effectiveness data"*
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
- OpenAI API key (for ChatGPT, embeddings, and tool-calling functionality)
- Spacy model (en_core_web_md)

## Workflow
1. **Upload & Extract**: Upload files (.vtt, .docx, .pdf, .csv, .xlsx) or paste text directly
2. **Anonymize Content**: Automatically detect and replace sensitive entities (text documents only)
3. **ChatGPT Analysis**: Select AI model, ask questions, perform analysis, and generate charts using the multi-tool agent
4. **Reverse Anonymization**: Convert anonymized responses back to original form (text documents only)

## Dependencies
- streamlit - Web application framework
- openai - OpenAI API client
- langchain, langchain-openai, langchain-experimental - Framework for LLM applications and tool-calling
- chromadb - Vector database for document storage and retrieval
- spacy - NLP library for entity recognition
- docx2txt, python-docx - For processing Word documents
- webvtt-py - For processing VTT subtitle files
- pandas, openpyxl - For data manipulation and analysis
- PyMuPDF, PyPDF2 - For PDF processing
- matplotlib, seaborn, plotly - For chart generation and data visualization

## Data Storage
- Session state for temporary storage during workflow
- ChromaDB for persistent vector storage of documents
- Local parquet files for efficient tabular data storage
- Logging functionality for tracking application usage

## Advanced Features
- **Multi-Tool AI Agent** with document search, data analysis, and visualization tools
- **RAG (Retrieval-Augmented Generation)** for more accurate AI responses
- **Interactive Visualizations** with Plotly for dynamic chart exploration
- **Document chunking** for efficient processing of large documents
- **Entity recognition and anonymization** with customizable categories
- **Vector search** for finding relevant content across documents
- **Cross-reference analysis** between documents and datasets
- **Natural language data analysis** using pandas operations
- **Agent debugging mode** for understanding AI decision-making
- **Context optimization** for efficient conversation management

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