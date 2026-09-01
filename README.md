# DTN Reporting Tools

A comprehensive AI-powered platform for analyzing documents and data with advanced anonymization, multi-format support, and intelligent decision support through RAG (Retrieval-Augmented Generation). Built for the UN System CEB Secretariat (Geneva).

| | |
|---|---|
| **Source** | https://github.com/dekpo/Reporting-Tools-RAG |
| Stack | Python, Streamlit, LangChain, OpenAI, SpaCy |

## Overview
This application provides an intelligent workflow for processing sensitive documents, meeting transcripts, and data files with **no memory limits** and persistent storage:

1. **Upload & Extract** - Load any text or data file (.vtt, .docx, .pdf, .csv, .xlsx) - supports video transcripts, Word documents, PDFs, and spreadsheets
2. **Anonymize** - Protect sensitive information by automatically detecting and replacing names, organizations, and locations
3. **AI Analysis** - Ask questions, get summaries, receive decision support, and analyze trends using advanced AI with RAG capabilities
4. **Revert** - Convert anonymized responses back to original form when needed

## Core Features

### 🤖 AI-Powered Analysis & Decision Support
The **primary feature** of this app is intelligent content analysis powered by OpenAI's GPT models with advanced tool-calling capabilities:
- **Ask Questions**: Query your documents and data using natural language
- **Summarize Content**: Generate executive summaries, meeting reports, and key insights
- **Decision Support**: Get recommendations and action items based on your content
- **Multi-Document Analysis**: Search across multiple documents simultaneously with semantic search
- **Data Analysis**: Analyze trends, patterns, and relationships in tabular data
- **Visualization Support**: Create charts and graphs when needed to support insights

### 🎭 Content Anonymization (Privacy-First Approach)
Protect sensitive information while maintaining analytical capability:
- **Automatic Entity Detection**: Uses SpaCy NER to identify names, organizations, locations, and more
- **Customizable Anonymization**: Choose which entity types to anonymize
- **Privacy-Preserving RAG**: Entity mappings are stored separately from vector embeddings
- **Reversible Process**: Convert anonymized responses back to original form
- **Meeting Transcript Support**: Specially optimized for Teams/Zoom transcripts with speaker identification

### 📁 Universal File Support (No Memory Limits)
Load any type of content without restrictions:
- **Video Transcripts**: Teams/Zoom .vtt files, Teams .docx transcripts
- **Documents**: Word documents (.docx), PDF files
- **Data Files**: CSV files, Excel spreadsheets (.xlsx, .xls)
- **Text Input**: Direct text paste for quick analysis
- **Persistent Storage**: All content stored with ChromaDB vector database for cross-session access
- **Multiple Sources**: Analyze multiple documents and datasets simultaneously

### 🧠 Advanced RAG (Retrieval-Augmented Generation)
Intelligent document search and context retrieval:
- **Semantic Search**: Find relevant information by meaning, not just keywords
- **Vector Database**: ChromaDB for efficient storage and retrieval
- **Smart Chunking**: Optimized document splitting for better context
- **Multi-Tool AI Agent**: Coordinated tools for document search, data analysis, and visualization
- **Context Management**: Automatic optimization for long conversations

### 📊 Data Visualization
Create charts and visualizations as part of your analysis:
- **Natural Language Requests**: "Show me a trend chart" or "Create a bar chart of top 10 items"
- **Multiple Chart Types**: Bar, line, scatter, pie, histogram, box plots, heatmaps
- **Interactive Charts**: Powered by Plotly for exploration and export
- **Integrated Analysis**: Charts appear naturally as part of AI responses

### 💾 Conversation Persistence (Never Lose Your Work)
Automatic conversation backup with multiple safety nets:
- **Auto-Save**: Conversations automatically saved every 5 messages
- **Browser-Safe**: Survives refresh, navigation, and accidental closure
- **Conversation History**: Browse and restore any previous conversation
- **Save Status Indicator**: Real-time visual feedback on unsaved changes
- **Multiple Warnings**: Alerts before clearing chat or navigating away
- **Manual Control**: Save button for explicit backup before critical actions

## Example Use Cases

### 📝 Meeting Analysis
```
"Summarize the key decisions from this meeting"
"What action items were discussed and who is responsible?"
"Extract all follow-up tasks with deadlines"
"Who mentioned budget concerns during the discussion?"
```

### 📊 Data Analysis & Reporting
```
"What are the main trends in this dataset?"
"Show me the top 10 items by performance"
"Create an executive summary with supporting charts"
"Compare Q3 and Q4 results and highlight key changes"
```

### 🎯 Decision Support
```
"Based on this data, what should be our priorities?"
"What patterns suggest we need to take action?"
"Summarize risks and opportunities mentioned in these documents"
"Provide recommendations based on the analysis"
```

### 📈 Quick Visualization (When Needed)
```
"Create a trend chart showing changes over time"
"Show me a bar chart of the top performers"
"Visualize the distribution of responses"
"Generate a correlation heatmap for these metrics"
```

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

## Typical Workflows

### Workflow 1: Sensitive Document Analysis (with Anonymization)
1. **Upload**: Load meeting transcript or document (.vtt, .docx, .pdf)
2. **Anonymize**: Automatically detect and replace names, organizations, locations
3. **Analyze**: Ask questions, get summaries, extract action items
4. **Revert**: Convert AI responses back to original names when needed

### Workflow 2: Quick Data Analysis (no Anonymization)
1. **Upload**: Load data files (.csv, .xlsx) or non-sensitive documents
2. **Skip Anonymization**: Go directly to AI analysis
3. **Analyze**: Query data, identify trends, generate insights and charts
4. **Export**: Download reports and visualizations

### Workflow 3: Multi-Source Analysis (no Memory Limits)
1. **Upload Multiple Files**: Load various documents and datasets over time
2. **Persistent Storage**: All content stored in vector database
3. **Cross-Reference Analysis**: Ask questions that span multiple sources
4. **Continuous Learning**: Add more sources anytime without losing previous data

## Requirements
- Python 3.8+
- OpenAI API key (for GPT models, embeddings, and tool-calling functionality)
- Spacy model (en_core_web_md - included)

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
- JSON files for conversation history and recovery
- Logging functionality for tracking application usage

## How It Works

### AI Agent Architecture
The app uses OpenAI's function calling with a sophisticated multi-tool agent system:

1. **Document Search Tool**: Semantic search across your uploaded documents using ChromaDB vector database
2. **Data Analysis Tool**: Natural language queries on tabular data using pandas operations  
3. **Visualization Tool**: Dynamic chart generation when visualizations support your analysis
4. **Coordinated Intelligence**: The AI decides which tools to use and how to combine them

### Privacy-Preserving Anonymization
- **Separate Storage**: Anonymized content in vector database, entity mappings stored separately
- **Filtered Metadata**: Entity information never sent to OpenAI API
- **Local Reversal**: Anonymization reversal happens locally after AI generates responses
- **No Data Leakage**: Original sensitive information remains completely private

### Persistent Storage & No Memory Limits
- **ChromaDB Vector Database**: All documents stored with semantic embeddings
- **Parquet Data Files**: Efficient tabular data storage across sessions
- **Metadata Management**: Track all sources with activation/deactivation controls
- **Session Independence**: Access your data anytime without re-uploading

## Advanced Configuration
- **Model Selection**: Choose from gpt-4o, gpt-4o-mini, gpt-4-turbo, or gpt-3.5-turbo based on your needs
- **Debug Mode**: View detailed agent execution steps and tool usage
- **Context Management**: Automatic optimization for long conversations with intelligent token management
  - Auto-trimming when approaching model token limits (80% threshold)
  - Smart conversation loading (summarizes older messages when loading 30+ message conversations)
  - Real-time token warnings based on model capabilities (GPT-3.5: 16K, GPT-4o: 128K)
  - UI display optimization (shows last 50 messages for conversations with 50+ messages)
- **Max Iterations**: Configure analysis depth (3-20 tool calls per response)
- **Data Source Management**: Enable/disable specific documents or datasets
- **Auto-Save Settings**: Configure conversation backup frequency (3-20 messages)

## Key Advantages

### ✅ No Memory Limits & Zero Data Loss
Unlike traditional chat interfaces, this app stores all your documents, data, and conversations persistently. You can:
- Upload unlimited documents and datasets
- Access previous content across sessions
- Build a growing knowledge base over time
- Never lose conversations due to refresh or navigation
- Recover work from crashes or accidental closures

### ✅ Privacy-First Design
Complete control over sensitive information:
- Anonymize content before AI processing
- Entity mappings never sent to OpenAI API
- Reverse anonymization happens locally
- Full transparency and control

### ✅ Multi-Format Intelligence
One platform for all your analysis needs:
- Meeting transcripts (VTT, Teams DOCX)
- Documents (Word, PDF)
- Data files (CSV, Excel)
- Mixed document and data analysis

### ✅ Professional AI Analysis
Beyond simple chatbots:
- Retrieval-Augmented Generation for accuracy
- Multi-tool agent for complex queries
- Decision support and recommendations
- Executive-ready reports and visualizations

## Getting Started

1. **Clone & Install**: Follow the setup instructions above
2. **Get API Key**: Obtain your OpenAI API key from [platform.openai.com](https://platform.openai.com/api-keys)
3. **Upload Content**: Start with a meeting transcript or data file
4. **Analyze**: Ask questions, get summaries, create reports
5. **Scale Up**: Add more documents and datasets as needed

## Support & Documentation

For technical details on the privacy implementation and advanced features, refer to the inline documentation in the source code. The app includes helpful tooltips and guidance throughout the interface.