# Packages
import streamlit as st
import openai
from openai import OpenAI
from docx import Document
import pyperclip

# Modules
import time
import io
import os
from datetime import datetime

# Utils
import lib

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.title(lib.APP_TITLE)

st.divider()

# Steps - updated to show position 2 in the new 4-step process
lib.steps(1)

st.divider()

if "gpt_api_key" not in st.session_state:
    st.header("ChatGPT Tool")

    st.markdown("<p>Ask ChatGPT to answer questions about your anonymized content using advanced retrieval techniques.</p>",unsafe_allow_html=True)

    # Check if we have a persistent ChromaDB to load
    persist_directory = './chroma_db'
    if os.path.exists(persist_directory) and os.path.isdir(persist_directory):
        document_metadata = lib.load_document_metadata(persist_directory)
        if document_metadata:
            st.info(f"Found {len(document_metadata)} document(s) in storage. After submitting your API key, you'll be able to access them.")

    MY_API_KEY = st.text_input(
            label="**Please specify your own OpenAI API Key** this one is for testing purpose you can use it and buy me a coffee ;)",
            value=st.secrets["OPENAI_API_KEY"]
        )

    st.markdown("<a href=\"https://platform.openai.com/api-keys\" class=\"link-primary\" target=\"_blank\">Or get your own OpenAI API key here !</a>",unsafe_allow_html=True)

    # Define model options with categorization
    model_options = {
        "GPT-4 Models (Most Capable)": [
            "gpt-4o", 
            "gpt-4-turbo", 
            "gpt-4"
        ],
        "GPT-3.5 Models (Fast & Cost-effective)": [
            "gpt-3.5-turbo"
        ]
    }

    # Flatten the options for selectbox
    all_models = []
    for category, models in model_options.items():
        for model in models:
            all_models.append(f"{category}: {model}")

    # Model descriptions for information
    model_descriptions = {
        "gpt-4o": "Latest and most capable model, optimized for performance and cost",
        "gpt-4-turbo": "Powerful model with strong reasoning capabilities",
        "gpt-4": "Original GPT-4 model with high accuracy",
        "gpt-3.5-turbo": "Fast and cost-effective model for most general tasks"
    }

    # Select model with categorization
    selected_model_with_category = st.selectbox(
        "**Select GPT model**",
        all_models,
        index=0,
        help="Choose the OpenAI model you want to use. More capable models provide better results but may cost more."
    )

    # Extract just the model name
    selected_model = selected_model_with_category.split(": ")[-1]
    
    # Show model description if available
    if selected_model in model_descriptions:
        st.caption(model_descriptions[selected_model])

    # Store in session state
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = selected_model
    elif st.session_state["openai_model"] != selected_model:
        st.session_state["openai_model"] = selected_model
    

    if st.button("Submit Your API Key",key="submit_your_api_key_btn1",type="primary"):
        client = OpenAI(api_key=MY_API_KEY)
        try:
            # Check the validity of the API key with the selected model
            try:
                # First check if the model exists and is available
                models = client.models.list()
                model_available = False
                available_models = [model.id for model in models.data]
                
                # Check if the exact model is available
                if selected_model in available_models:
                    model_available = True
                # Some models might have different names in the API (e.g., gpt-4o might be available as gpt-4o-xxxx)
                elif any(model_id.startswith(selected_model) for model_id in available_models):
                    model_available = True
                    
                if not model_available:
                    # If model not available, suggest a fallback
                    fallback_model = "gpt-3.5-turbo"  # Default fallback
                    st.warning(f"The selected model '{selected_model}' appears to be unavailable with your API key. Falling back to {fallback_model}.", icon="⚠️")
                    selected_model = fallback_model
                    st.session_state["openai_model"] = selected_model
                
                # Now try to use the model
                client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "user", "content": "Hello this is a test."}
                    ],
                    stream=False,
                )
            except Exception as model_error:
                st.warning(f"Error with model {selected_model}: {model_error}. Trying with gpt-3.5-turbo instead.", icon="⚠️")
                # Fallback to gpt-3.5-turbo which is widely available
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": "Hello this is a test."}
                    ],
                    stream=False,
                )
                # Update the model to the fallback
                st.session_state["openai_model"] = "gpt-3.5-turbo"
                
        except Exception as e:
            st.error(f"Your API key is not valid. Please try Again. Error: {str(e)}", icon="⚠️")
            if 'submit_your_api_key_btn' in st.session_state:
                del st.session_state.submit_your_api_key_btn
        else:
            st.success(f"Your API key is valid. You will be redirected to the discussion area in few seconds. Using model: {st.session_state['openai_model']}", icon="✅")
            st.session_state["gpt_api_key"] = MY_API_KEY
            
            # Check for existing documents in the persistent storage
            persist_directory = './chroma_db'
            if os.path.exists(persist_directory) and os.path.isdir(persist_directory):
                document_metadata = lib.load_document_metadata(persist_directory)
                if document_metadata:
                    with st.spinner("Loading document database..."):
                        try:
                            # Initialize ChromaDB client with custom embedding function
                            if hasattr(lib, 'RAG_AVAILABLE') and lib.RAG_AVAILABLE:
                                # Create custom embedding function
                                embedding_function = lib.OpenAIEmbeddingFunction(api_key=MY_API_KEY)
                                
                                # Create ChromaDB client
                                import chromadb
                                from chromadb.config import Settings
                                
                                chroma_client = chromadb.PersistentClient(
                                    path=persist_directory,
                                    settings=Settings(
                                        anonymized_telemetry=False,
                                        allow_reset=True
                                    )
                                )
                                
                                # Connect to the collection
                                collection = chroma_client.get_collection(
                                    name="document_collection", 
                                    embedding_function=embedding_function
                                )
                                
                                # Store in session state
                                st.session_state.vector_db = collection
                                st.session_state.selected_doc_sources = list(document_metadata.keys())
                                
                                # If there are documents available, select the first one as the active document
                                # This allows users to immediately use their saved documents
                                if document_metadata and "saved_anonymisation" not in st.session_state:
                                    # Get the most recent document (sorted by timestamp)
                                    doc_list = []
                                    for doc_hash, doc_data in document_metadata.items():
                                        doc_list.append({
                                            "hash": doc_hash,
                                            "title": doc_data["title"],
                                            "timestamp": doc_data.get("timestamp", 0)
                                        })
                                    # Sort by timestamp (newest first)
                                    doc_list.sort(key=lambda x: x["timestamp"], reverse=True)
                                    
                                    if doc_list:
                                        # Set the latest document as the active document
                                        latest_doc = doc_list[0]
                                        
                                        # Get document hash to retrieve full metadata
                                        doc_hash = latest_doc["hash"]
                                        
                                        # Get entities from metadata if available
                                        entities_data = {
                                            "Text": [],
                                            "Replacement": [],
                                            "Category": []
                                        }
                                        
                                        # Check if this document has stored entities
                                        if 'entities' in document_metadata[doc_hash]:
                                            entities_data = document_metadata[doc_hash]['entities']
                                        
                                        st.session_state["saved_anonymisation"] = {
                                            "Title": latest_doc["title"],
                                            "Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            "Entities": entities_data  # Use stored entities if available
                                        }
                                        
                                        # Also initialize saved_gpt_answers with the same document
                                        # This ensures the revert page will have access to the document
                                        st.session_state["saved_gpt_answers"] = {
                                            "Title": latest_doc["title"],
                                            "Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            "Data": "",  # Will be populated with conversation content
                                            "Entities": entities_data,  # Use stored entities if available
                                            "Attendees": {}
                                        }
                        except Exception as e:
                            st.error(f"Error loading document database: {e}")
            
            # Load existing tabular datasets
            with st.spinner("Loading tabular datasets..."):
                try:
                    tabular_datasets = lib.load_tabular_datasets()
                    if tabular_datasets:
                        st.session_state.tabular_datasets = tabular_datasets
                        st.success(f"Loaded {len(tabular_datasets)} tabular dataset(s).")
                except Exception as e:
                    st.error(f"Error loading tabular datasets: {e}")
            
            time.sleep(1)
            st.rerun()
else:
    st.header(f"ChatGPT Discussion ({st.session_state["openai_model"] })")

    # Initialize session state variables BEFORE creating tabs
    # Initialize messages in session state if they don't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize processed_anonymizations if it doesn't exist
    if "processed_anonymizations" not in st.session_state:
        st.session_state.processed_anonymizations = set()

    # Initialize client
    client = OpenAI(api_key=st.session_state["gpt_api_key"])

    # Create the main tab interface
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Sources", "⚙️ Settings"])
    
    # =================== TAB 1: CHAT (DEFAULT) ===================
    with tab1:
        # Process document and create vector database if not already processed
        if "saved_anonymisation" in st.session_state:
            # Generate a unique key for this anonymization
            anon_key = st.session_state["saved_anonymisation"]["Title"] + "_" + st.session_state["saved_anonymisation"]["Time"]
            
            # Check if this anonymization has already been processed
            if anon_key not in st.session_state.processed_anonymizations and "vector_db" in st.session_state:
                # We have a new document to add to the existing vector DB
                # Only process if we have actual document data
                if "Data" in st.session_state["saved_anonymisation"] and st.session_state["saved_anonymisation"]["Data"]:
                    with st.spinner(f"Adding new document '{st.session_state['saved_anonymisation']['Title']}' to the database..."):
                        # Get document info
                        document_title = st.session_state["saved_anonymisation"]["Title"]
                        document_content = st.session_state["saved_anonymisation"]["Data"]
                        document_entities = st.session_state["saved_anonymisation"]["Entities"]
                        
                        # Add to vector database
                        st.session_state.vector_db = lib.create_vector_db_from_text(
                            document_content, 
                            document_title, 
                            st.session_state["gpt_api_key"],
                            document_entities  # Pass entities for reverse anonymization
                        )
                        
                        if st.session_state.vector_db is not None:
                            st.success(f"Document '{document_title}' added successfully to the database!")
                            # Mark as processed
                            st.session_state.processed_anonymizations.add(anon_key)
                        else:
                            st.error(f"Failed to add document '{document_title}' to the database.")
                    
            elif anon_key not in st.session_state.processed_anonymizations and "vector_db" not in st.session_state:
                # This is the first document, and we need to create the vector DB
                # Only process if we have actual document data
                if "Data" in st.session_state["saved_anonymisation"] and st.session_state["saved_anonymisation"]["Data"]:
                    with st.spinner("Processing your document... This might take a minute."):
                        # Check if RAG is available
                        if not hasattr(lib, 'RAG_AVAILABLE') or not lib.RAG_AVAILABLE:
                            st.warning("RAG functionality is not available. The app will use the traditional chunking approach instead.")
                            # Set vector_db to None to skip RAG-related code
                            st.session_state.vector_db = None
                        else:
                            # Create vector database from anonymized content
                            document_title = st.session_state["saved_anonymisation"]["Title"]
                            document_content = st.session_state["saved_anonymisation"]["Data"]
                            document_entities = st.session_state["saved_anonymisation"]["Entities"]
                            
                            # Create vector database
                            st.session_state.vector_db = lib.create_vector_db_from_text(
                                document_content, 
                                document_title, 
                                st.session_state["gpt_api_key"],
                                document_entities  # Pass entities for reverse anonymization
                            )
                            
                            if st.session_state.vector_db is not None:
                                st.success(f"Document processed successfully! You can now ask questions about '{document_title}'")
                                # Mark as processed
                                st.session_state.processed_anonymizations.add(anon_key)
                            else:
                                st.error("Failed to process document with RAG. Falling back to traditional approach.")
                                # Set vector_db to None to indicate RAG is not available
                                st.session_state.vector_db = None

        # Check available data sources and show appropriate messages
        has_documents = ("vector_db" in st.session_state and st.session_state.vector_db is not None) or ("saved_anonymisation" in st.session_state)
        has_datasets = "tabular_datasets" in st.session_state and st.session_state.tabular_datasets
        
        if not has_documents and not has_datasets:
            st.warning("No data sources loaded. Please upload documents or datasets to begin analysis.")
        else:
            # Show what's available
            available_sources = []
            if has_documents:
                num_docs = len(st.session_state.get('selected_doc_sources', []))
                available_sources.append(f"{num_docs} text document(s)")
            if has_datasets:
                num_datasets = len(st.session_state.get('tabular_datasets', {}))
                available_sources.append(f"{num_datasets} tabular dataset(s)")
            
            st.info(f"Ready to analyze: {', '.join(available_sources)}")

        # Create chat container with fixed height for scrolling
        chat_container = st.container(height=600, border=True)
        
        # Display chat messages from history in the container
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    # Display the message content
                    message_content = message["content"]
                    
                    # Check if this message contains chart IDs (support multiple charts)
                    import re
                    chart_matches = re.findall(r'\[CHART_ID:(chart_\d+(?:_\d+)?)\]', message_content)
                    
                    if st.session_state.get("show_debug", False):
                        st.write(f"🔧 DEBUG: Checking message for chart IDs: {message_content[:100]}...")
                        if chart_matches:
                            st.write(f"🔧 DEBUG: Found chart IDs in message: {chart_matches}")
                        else:
                            st.write(f"🔧 DEBUG: No chart IDs found in message")
                    
                    if chart_matches and message["role"] == "assistant":
                        # Remove all chart IDs from the displayed message
                        display_content = re.sub(r'\[CHART_ID:chart_\d+(?:_\d+)?\]', '', message_content)
                        st.markdown(display_content)
                        
                        # Display all charts that exist in stored charts
                        for chart_id in chart_matches:
                            if st.session_state.get("show_debug", False):
                                st.write(f"🔧 DEBUG: Looking for chart ID: {chart_id}")
                                st.write(f"🔧 DEBUG: Available chart IDs: {list(st.session_state.get('stored_charts', {}).keys())}")
                            
                            if chart_id in st.session_state.get("stored_charts", {}):
                                chart_config = st.session_state.stored_charts[chart_id]
                                if st.session_state.get("show_debug", False):
                                    st.write(f"🔧 DEBUG: Found chart config, recreating chart")
                                
                                fig = lib.recreate_chart_from_config(chart_config)
                                if fig is not None:
                                    if st.session_state.get("show_debug", False):
                                        st.write(f"🔧 DEBUG: Chart recreation successful for history display")
                                    st.plotly_chart(fig, use_container_width=True, key=f"history_chart_{chart_id}")
                                else:
                                    # Show fallback message if chart recreation failed
                                    st.warning(f"⚠️ Chart {chart_id} could not be displayed. The chart data may be corrupted or incompatible with the current session.")
                                    if st.session_state.get("show_debug", False):
                                        st.write("**Debug Info:** Chart config:", chart_config)
                            else:
                                if st.session_state.get("show_debug", False):
                                    st.write(f"🔧 DEBUG: Chart ID {chart_id} not found in stored charts")
                    else:
                        # Display normal message
                        st.markdown(message_content)

        # Prompt Assistant Dialog Function
        @st.dialog("💡 Prompt Assistant & Templates", width="large")
        def show_prompt_assistant():
            # Use custom CSS to make dialog much wider
            st.markdown("""
            <style>
            .stDialog > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
                width: 98vw !important;
                max-width: 1600px !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("**Quick access to proven prompt templates for better AI results**")
            
            # Check available data sources for smart suggestions
            has_documents = ("vector_db" in st.session_state and st.session_state.vector_db is not None) or ("saved_anonymisation" in st.session_state)
            has_datasets = "tabular_datasets" in st.session_state and st.session_state.tabular_datasets
            
            # Smart suggestions
            col1, col2 = st.columns(2)
            with col1:
                if has_documents:
                    st.info("📄 **Document sources loaded** - Use text analysis templates")
            with col2:
                if has_datasets:
                    st.info("📊 **Datasets loaded** - Use data analysis templates")
            
            # Simple layout - no tabs, just organized sections
            st.markdown("### 📊 Text Analysis Templates")
            
            text_templates = {
                "📝 Meeting Report": {
                    "template": """Create a professional meeting report with this structure:

**Executive Summary:** Key outcomes and decisions
**Discussion Points:** Main topics covered  
**Decisions Made:** What was agreed upon
**Action Items:** Who does what by when
**Next Steps:** Follow-up actions

Write in formal, professional tone suitable for organizational reporting."""
                },
                
                "⚡ Quick Summary": {
                    "template": """Provide a concise 3-paragraph summary:

**Paragraph 1:** Main focus and key topics discussed
**Paragraph 2:** Primary conclusions, decisions, or findings  
**Paragraph 3:** Next steps, recommendations, or actions required

Keep each paragraph to 3-4 sentences maximum."""
                },
                
                "🎯 Action Items": {
                    "template": """Extract all actionable elements:

**Immediate Actions:** Tasks for next 1-2 weeks
**Medium-term Actions:** Tasks for next 1-3 months
**Long-term Commitments:** Strategic actions beyond 3 months
**Responsible Parties:** Who is accountable for each action
**Dependencies:** Prerequisites for each action

Format as clear action plan with timelines."""
                },
                
                "📋 Key Themes": {
                    "template": """Identify and organize the main themes:

1. **Theme Identification:** List 3-5 major themes
2. **Content Organization:** Group relevant points under each theme
3. **Key Insights:** Provide 2-3 insights for each theme
4. **Connections:** Note relationships between themes

Present findings in clear, structured format."""
                }
            }
            
            cols = st.columns(4)
            for i, (title, details) in enumerate(text_templates.items()):
                with cols[i % 4]:
                    with st.container():
                        st.markdown(f"**{title}**")
                        if st.button(f"Use Template", key=f"text_{i}", use_container_width=True):
                            st.session_state.template_to_use = details['template']
                            st.session_state.close_dialog = True
                            st.rerun()
            
            st.divider()
            st.markdown("### 📈 Data Analysis Templates")
            
            data_templates = {
                "📊 Data Overview": {
                    "template": """Analyze this dataset and provide:

**Data Structure:** Number of rows, columns, data types
**Key Statistics:** Summary statistics for numerical columns
**Data Quality:** Missing values, outliers, any issues
**Top Insights:** 5 most interesting patterns or findings
**Recommended Charts:** Best visualizations for this data

Be specific about column names and values."""
                },
                
                "📈 Create Charts": {
                    "template": """Create these visualizations from the data:

1. Bar chart showing top 10 values by the main metric
2. Line chart showing trends over time (if time data exists)
3. Summary statistics table for key numerical columns
4. Distribution chart for the most important variable

Include clear titles and labels. Suggest additional charts if helpful."""
                },
                
                "🔍 Trend Analysis": {
                    "template": """Analyze trends and patterns in this data:

**Overall Trends:** General direction and changes over time
**Key Patterns:** Notable increases, decreases, or cyclical patterns  
**Top Performers:** Highest and lowest values with context
**Relationships:** Correlations between different variables
**Time-based Charts:** Visualizations showing temporal patterns

Focus on actionable insights."""
                },
                
                "⚖️ Compare Groups": {
                    "template": """Compare different groups or categories in this data:

**Performance Comparison:** Which groups perform better in key metrics
**Key Differences:** How groups differ across important measures
**Rankings:** Rank groups from best to worst performance
**Visualization:** Create charts highlighting these comparisons
**Insights:** What do these differences tell us

Provide clear, actionable recommendations."""
                }
            }
            
            cols = st.columns(4)
            for i, (title, details) in enumerate(data_templates.items()):
                with cols[i % 4]:
                    with st.container():
                        st.markdown(f"**{title}**")
                        if st.button(f"Use Template", key=f"data_{i}", use_container_width=True):
                            st.session_state.template_to_use = details['template']
                            st.session_state.close_dialog = True
                            st.rerun()
            
            st.divider()
            st.markdown("### 🚀 Quick Starters")
            
            quick_templates = {
                "📋 What's in this data?": "Analyze this dataset and tell me what's most interesting. Show me the key patterns, trends, and create 2-3 charts that best represent the data.",
                
                "📊 Show me charts": "Create 3 different charts from this data that show the most important insights. Use bar charts, line charts, or other appropriate visualizations.",
                
                "🔍 Find patterns": "Look for interesting patterns, trends, and relationships in this data. Highlight anything unusual or noteworthy.",
                
                "📈 Executive summary": "Create an executive summary of this data suitable for leadership, including key metrics, trends, and 1-2 supporting charts.",
                
                "🎯 Action insights": "Analyze this data and provide actionable insights and recommendations based on what the data shows.",
                
                "📑 Meeting summary": "Summarize this meeting transcript with key decisions, action items, and next steps."
            }
            
            cols = st.columns(3)
            for i, (title, template) in enumerate(quick_templates.items()):
                with cols[i % 3]:
                    if st.button(title, key=f"quick_{i}", use_container_width=True):
                        st.session_state.template_to_use = template
                        st.session_state.close_dialog = True
                        st.rerun()
            
            # Simple tips at bottom
            st.divider()
            st.success("💡 **Tip:** Select any template above and it will automatically appear in your input box ready to send!")

        def generate_custom_prompt(task_type, content_type, output_format, audience, additional):
            # Map selections to prompt components
            task_mapping = {
                "Summarize content": "Analyze and summarize the key points from",
                "Analyze data": "Perform a comprehensive analysis of",
                "Generate report": "Create a detailed report based on",
                "Extract information": "Extract and organize specific information from",
                "Create visualization": "Analyze the data and create appropriate visualizations for",
                "Compare items": "Compare and contrast the elements in"
            }
            
            format_mapping = {
                "Professional report": "Present findings in a formal report structure with executive summary, main findings, and recommendations.",
                "Bullet points": "Organize information in clear, concise bullet points.",
                "Executive summary": "Provide a high-level executive summary suitable for leadership review.",
                "Detailed analysis": "Include detailed analysis with supporting evidence and reasoning.",
                "Charts and graphs": "Include relevant visualizations and charts to support findings.",
                "Action list": "Focus on actionable items with timelines and responsible parties."
            }
            
            audience_mapping = {
                "General public": "Use clear, accessible language suitable for general audiences.",
                "Colleagues/Team": "Use professional language appropriate for team collaboration.",
                "Management/Leadership": "Use executive-level language focusing on strategic implications.",
                "Technical experts": "Include technical details and specialized terminology as appropriate.",
                "External stakeholders": "Use diplomatic, formal language suitable for external communications."
            }
            
            prompt = f"""{task_mapping[task_type]} this {content_type.lower()}.

{format_mapping[output_format]}

{audience_mapping[audience]}"""
            
            if additional:
                prompt += f"\n\nAdditional requirements: {additional}"
            
            prompt += "\n\nPlease be thorough, accurate, and ensure all important points are covered."
            
            return prompt

        # Chat input area with prompt assistant button - MOVED TO LEFT
        col1, col2 = st.columns([0.15, 0.85])
        
        with col1:
            # Prompt Assistant button - NOW ON THE LEFT
            if st.button("💡 Prompt Assistant", use_container_width=True, help="Open prompt assistant with ready-made templates"):
                show_prompt_assistant()
        
        with col2:
            # Check if we have a template from the dialog and auto-close
            template_value = st.session_state.get("template_to_use", "")
            if template_value:
                # Clear the template after using it
                del st.session_state.template_to_use
                # Check if we should close dialog
                if st.session_state.get("close_dialog", False):
                    st.session_state.close_dialog = False
            
            # Use text_area instead of chat_input for better control
            prompt = st.text_area(
                "Ask questions about your documents and data",
                value=template_value,
                height=100,
                max_chars=8000,
                key="main_prompt_input",
                placeholder="Type your question here or use the Prompt Assistant for templates...",
                help="💡 Use the Prompt Assistant button to get professional templates!"
            )
            
            # Send button
            col2a, col2b = st.columns([0.85, 0.15])
            with col2b:
                send_button = st.button("📤 Send", type="primary", use_container_width=True)
            
            # Process the prompt when send button is clicked or Enter is pressed
            if send_button and prompt.strip():
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Display user message in the container
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)
                
                # Generate response using UNIFIED AGENT
                with chat_container:
                    with st.chat_message("assistant"):
                        try:
                            with st.spinner("Analyzing your request..."):
                                # Check if tool-calling is available
                                if hasattr(lib, 'TOOLS_AVAILABLE') and lib.TOOLS_AVAILABLE:
                                    # Create unified agent
                                    agent_executor = lib.create_unified_agent()
                                    
                                    if agent_executor is not None:
                                        # Execute the query using the unified agent
                                        try:
                                            result = agent_executor.invoke({"input": prompt})
                                            response = result["output"]
                                            
                                            # Check if the response indicates max iterations was reached
                                            max_iterations = st.session_state.get("max_iterations", 10)
                                            if "Agent stopped due to max iterations" in response or len(result.get("intermediate_steps", [])) >= max_iterations:
                                                st.warning("⚠️ The AI agent reached its maximum number of tool calls. The response may be incomplete.")
                                                response += "\n\n💡 **Tip**: Try asking a more specific question or break your request into smaller parts for better results."
                                            
                                        except Exception as agent_error:
                                            # Handle specific agent errors
                                            error_str = str(agent_error)
                                            if "max iterations" in error_str.lower():
                                                response = """I apologize, but I reached the maximum number of analysis steps while processing your request. This usually happens with very complex queries.

**What you can do:**
1. **Break down your question** into smaller, more specific parts
2. **Be more specific** about which dataset or document you want me to analyze
3. **Try a simpler version** of your question first

**Examples of more specific questions:**
- Instead of "analyze everything", try "show me refugee trends for Q4"
- Instead of "create charts for all data", try "create a bar chart of funding by region"
- Instead of "what does the data show", try "what are the top 5 programs by effectiveness"

Please try rephrasing your question more specifically, and I'll be happy to help!"""
                                                st.warning("⚠️ Analysis complexity limit reached")
                                            else:
                                                response = f"I encountered an error while processing your request: {error_str}\n\nPlease try rephrasing your question or contact support if the issue persists."
                                                st.error("An error occurred during analysis")
                                        
                                        # Display the response
                                        st.markdown(response)
                                        
                                        # Check if charts were created and display them
                                        chart_ids_to_display = []
                                        chart_ids_for_response = ""
                                        
                                        # Check for multiple charts created in this response
                                        if "current_chart_ids" in st.session_state and st.session_state.current_chart_ids:
                                            chart_ids_to_display = st.session_state.current_chart_ids.copy()
                                            if st.session_state.get("show_debug", False):
                                                st.write(f"🔧 DEBUG: Found current_chart_ids: {chart_ids_to_display}")
                                        # Fallback to single chart ID for backwards compatibility
                                        elif "current_chart_id" in st.session_state and st.session_state.current_chart_id is not None:
                                            chart_ids_to_display = [st.session_state.current_chart_id]
                                            if st.session_state.get("show_debug", False):
                                                st.write(f"🔧 DEBUG: Found single current_chart_id: {st.session_state.current_chart_id}")
                                        
                                        # Display all charts that were created
                                        for chart_id in chart_ids_to_display:
                                            if st.session_state.get("show_debug", False):
                                                st.write(f"🔧 DEBUG: Processing chart ID: {chart_id}")
                                                st.write(f"🔧 DEBUG: Stored charts keys: {list(st.session_state.get('stored_charts', {}).keys())}")
                                            
                                            if chart_id in st.session_state.get("stored_charts", {}):
                                                chart_config = st.session_state.stored_charts[chart_id]
                                                if st.session_state.get("show_debug", False):
                                                    st.write(f"🔧 DEBUG: About to recreate chart with config: {chart_config}")
                                                
                                                fig = lib.recreate_chart_from_config(chart_config)
                                                if fig is not None:
                                                    if st.session_state.get("show_debug", False):
                                                        st.write(f"🔧 DEBUG: Chart recreation successful, displaying chart")
                                                    st.plotly_chart(fig, use_container_width=True, key=f"current_chart_{chart_id}")
                                                    
                                                    # Collect chart IDs for adding to response
                                                    chart_ids_for_response += f"\n\n[CHART_ID:{chart_id}]"
                                                else:
                                                    # Show fallback message if chart recreation failed
                                                    st.warning(f"⚠️ Chart {chart_id} could not be displayed. The chart data may be corrupted or incompatible with the current session.")
                                                    if st.session_state.get("show_debug", False):
                                                        st.write("**Debug Info:** Chart config:", chart_config)
                                            else:
                                                if st.session_state.get("show_debug", False):
                                                    st.write(f"🔧 DEBUG: Chart ID {chart_id} not found in stored_charts")
                                        
                                        # Add all chart IDs to response for persistence in chat history
                                        if chart_ids_for_response:
                                            response += chart_ids_for_response
                                        
                                        # Clear the current chart IDs after displaying
                                        if "current_chart_ids" in st.session_state:
                                            st.session_state.current_chart_ids = []
                                        st.session_state.current_chart_id = None
                                        
                                        # Show debug information if enabled
                                        if st.session_state.get("show_debug", False):
                                            with st.expander("🔍 Agent Execution Details (Debug Mode)", expanded=False):
                                                # Show the tools that were used
                                                if "intermediate_steps" in result and result["intermediate_steps"]:
                                                    st.write("### 🛠️ Tools Used:")
                                                    
                                                    for i, (action, observation) in enumerate(result["intermediate_steps"]):
                                                        # Extract tool name and input
                                                        tool_name = action.tool if hasattr(action, 'tool') else 'Unknown Tool'
                                                        tool_input = action.tool_input if hasattr(action, 'tool_input') else {}
                                                        
                                                        # Display tool usage in a nice format
                                                        st.write(f"**Step {i+1}: {tool_name}**")
                                                        
                                                        # Show tool input parameters
                                                        if tool_input:
                                                            with st.container():
                                                                st.write("*Input parameters:*")
                                                                for key, value in tool_input.items():
                                                                    st.write(f"- {key}: `{value}`")
                                                        
                                                        # Show tool output (truncated for readability)
                                                        if observation:
                                                            with st.container():
                                                                st.write("*Tool output:*")
                                                                # Truncate long outputs
                                                                if len(str(observation)) > 500:
                                                                    truncated_output = str(observation)[:500] + "... (truncated)"
                                                                    st.text_area("", value=truncated_output, height=100, key=f"debug_output_{i}", disabled=True)
                                                                else:
                                                                    st.text_area("", value=str(observation), height=100, key=f"debug_output_{i}", disabled=True)
                                                        
                                                        if i < len(result["intermediate_steps"]) - 1:
                                                            st.divider()
                                        
                                        # Add assistant response to chat history
                                        st.session_state.messages.append({"role": "assistant", "content": response})
                                    else:
                                        # Fallback if agent creation fails
                                        error = "Agent creation failed. Please check your configuration."
                                        st.error(error)
                                        st.session_state.messages.append({"role": "assistant", "content": error})
                                else:
                                    # Fallback to basic approach if tools not available
                                    st.warning("Advanced tool-calling is not available. Using basic chat mode.")
                                    
                                    # Create basic chat response
                                    messages = [
                                        {"role": "system", "content": "You are a helpful assistant. Answer questions based on your knowledge."}
                                    ]
                                    # Add all previous messages
                                    messages.extend([
                                        {"role": m["role"], "content": m["content"]} 
                                        for m in st.session_state.messages
                                    ])
                                    
                                    # Create streaming response
                                    stream = client.chat.completions.create(
                                        model=st.session_state["openai_model"],
                                        messages=messages,
                                        stream=True,
                                    )
                                    
                                    # Display streaming response
                                    response = st.write_stream(stream)
                                    
                                    # Add assistant response to chat history
                                    st.session_state.messages.append({"role": "assistant", "content": response})
                                    
                        except openai.APIConnectionError as e:
                            error = "Sorry, the server could not be reached. Please try again later..."
                            st.error(error)
                            st.session_state.messages.append({"role": "assistant", "content": error})
                            
                        except openai.RateLimitError as e:
                            error = "Too many requests. Please try again later..."
                            st.error(error)
                            st.session_state.messages.append({"role": "assistant", "content": error})
                            
                        except openai.APIStatusError as e:
                            error = "An error occurred while processing your request. Please try again later..."
                            st.error(error)
                            st.session_state.messages.append({"role": "assistant", "content": error})
                            
                        except Exception as e:
                            error = f"An unexpected error occurred: {str(e)}"
                            st.error(error)
                            st.session_state.messages.append({"role": "assistant", "content": error})
                
                # Force a rerun to ensure proper rendering and scrolling
                st.rerun()
        
        # Conversation Management - Always visible at bottom when there are messages
        if len(st.session_state.messages) > 0:
            st.divider()
            st.subheader("Conversation Management")
            
            # Use 4 columns for more compact buttons
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            with col1:
                # Download answers as DOCX - More compact button
                doc_download = Document()
                if "saved_anonymisation" in st.session_state:
                    doc_title = st.session_state["saved_anonymisation"]["Title"].replace(">"," ")
                else:
                    doc_title = "Chat Conversation"
                # Filter the title for invalid XML characters
                doc_title = lib.filter_xml_chars(doc_title)
                doc_download.add_heading(doc_title, level=1)
                
                # Add conversation to document
                for message in st.session_state.messages:
                    if message["role"] == "user":
                        question_text = lib.filter_xml_chars(message['content'])
                        doc_download.add_heading(f"Question: {question_text}", level=2)
                    else:
                        answer_text = lib.filter_xml_chars(message['content'])
                        doc_download.add_paragraph(answer_text)
                
                # Save document to buffer
                bio = io.BytesIO()
                doc_download.save(bio)
                
                # Download button - More compact
                st.download_button(
                    label="Download DOCX",
                    type="secondary",
                    data=bio.getvalue(),
                    file_name=f"ChatGPT Answers About {doc_title}.docx",
                    mime="docx",
                    key="download_conversation_btn",
                    use_container_width=True
                )
            
            with col2:
                # Copy answers to clipboard - More compact
                if st.button("Copy", use_container_width=True):
                    # Format conversation for clipboard
                    conversation_text = ""
                    for message in st.session_state.messages:
                        if message["role"] == "user":
                            conversation_text += f"Question: {message['content']}\n\n"
                        else:
                            conversation_text += f"Answer: {message['content']}\n\n"
                    
                    # Copy to clipboard
                    pyperclip.copy(conversation_text)
                    st.success("Copied!")
            
            with col3:
                # Clear conversation - More compact
                if st.button("Clear Chat", use_container_width=True):
                    st.session_state.messages = []
                    # Also clear stored charts to free up memory
                    if "stored_charts" in st.session_state:
                        st.session_state.stored_charts = {}
                    if "current_chart_id" in st.session_state:
                        st.session_state.current_chart_id = None
                    if "current_chart_ids" in st.session_state:
                        st.session_state.current_chart_ids = []
                    st.rerun()
            
            with col4:
                # Save and proceed to reverse anonymization - More compact
                if "saved_anonymisation" in st.session_state:
                    entities = st.session_state["saved_anonymisation"]["Entities"]
                    if "saved_content" in st.session_state:
                        attendees = st.session_state["saved_content"]["Attendees"]
                    else:
                        attendees = {}
                    
                    # Format conversation for saving
                    conversation_text = ""
                    for message in st.session_state.messages:
                        if message["role"] == "user":
                            conversation_text += f"Question: {message['content']}\n\n"
                        else:
                            conversation_text += f"Answer: {message['content']}\n\n"
                    
                    # Save button - More compact
                    if st.button(
                        label="Save & Reverse",
                        type="primary",
                        use_container_width=True,
                        key="save_conversation",
                        on_click=lib.save_gpt_answers,
                        args=[st.session_state["saved_anonymisation"]["Title"], conversation_text, entities, attendees]
                    ):
                        st.switch_page("pages/03_revert.py")
                else:
                    # If no saved_anonymisation, show disabled button with tooltip
                    st.button(
                        label="Save & Reverse",
                        type="primary",
                        disabled=True,
                        use_container_width=True,
                        key="save_conversation_disabled",
                        help="Process a document first to enable this feature"
                    )

    # =================== TAB 2: SOURCES ===================
    with tab2:
        st.markdown("### 📊 Data Sources Management")
        st.markdown("Manage your document and tabular data sources for AI analysis.")
        
        # Document Sources Section
        if "vector_db" in st.session_state and st.session_state.vector_db is not None:
            st.subheader("📄 Document Sources")
            
            # Load document metadata
            persist_directory = './chroma_db'
            document_metadata = lib.load_document_metadata(persist_directory)
            
            if document_metadata:
                # Display document list with selection options
                st.write("Select documents to use as sources for your questions:")
                
                # Convert metadata to a more usable format for display
                doc_list = []
                for doc_hash, doc_data in document_metadata.items():
                    doc_list.append({
                        "hash": doc_hash,
                        "title": doc_data["title"],
                        "chunks": doc_data["chunks"],
                        "timestamp": doc_data.get("timestamp", 0),
                        "active": doc_data.get("active", True)
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
                        timestamp = datetime.fromtimestamp(doc["timestamp"])
                        st.caption(f"Added: {timestamp.strftime('%Y-%m-%d')}")
                    
                    with col3:
                        if st.button("Remove", key=f"remove_{doc['hash']}"):
                            if st.session_state.get("confirm_delete") == doc['hash']:
                                # If already confirmed, perform the deletion
                                with st.spinner(f"Deleting '{doc['title']}'..."):
                                    success = lib.delete_document_from_vector_db(doc['hash'])
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
                lib.save_document_metadata(persist_directory, document_metadata)
                
                # Add Clear Vector Database button at the end of document list
                st.divider()
                if hasattr(lib, 'RAG_AVAILABLE') and lib.RAG_AVAILABLE:
                    # Warning message before the button
                    st.warning("This will remove all documents from the database. This action cannot be undone.", icon="⚠️")
                    
                    # Full-width button with confirmation
                    if st.button("Clear All Documents", type="secondary", use_container_width=True):
                        # Show confirmation dialog
                        if st.session_state.get("confirm_clear_all"):
                            with st.spinner("Clearing vector database..."):
                                success = lib.clear_vector_database()
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

        # Tabular Dataset Sources Section
        st.divider()
        if "tabular_datasets" in st.session_state and st.session_state.tabular_datasets:
            st.subheader("📊 Tabular Data Sources")
            
            # Load tabular metadata
            tabular_metadata = lib.get_tabular_metadata()
            
            if tabular_metadata:
                # Display dataset list with selection options
                st.write("Select datasets to use as sources for your questions:")
                
                # Convert metadata to a more usable format for display
                dataset_list = []
                for file_hash, dataset_data in tabular_metadata.items():
                    dataset_list.append({
                        "hash": file_hash,
                        "title": dataset_data["title"],
                        "shape": dataset_data["shape"],
                        "columns": dataset_data["columns"],
                        "timestamp": dataset_data.get("timestamp", 0),
                        "active": dataset_data.get("active", True)
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
                        timestamp = datetime.fromtimestamp(dataset["timestamp"])
                        st.caption(f"Added: {timestamp.strftime('%Y-%m-%d')}")
                    
                    with col3:
                        if st.button("Remove", key=f"remove_dataset_{dataset['hash']}"):
                            if st.session_state.get("confirm_delete_dataset") == dataset['hash']:
                                # If already confirmed, perform the deletion
                                with st.spinner(f"Deleting '{dataset['title']}'..."):
                                    success = lib.delete_tabular_dataset(dataset['hash'])
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
                            success = lib.clear_all_tabular_data()
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
        else:
            st.info("📊 No tabular datasets loaded. Upload CSV or Excel files on the Home page to add datasets.")

    # =================== TAB 3: SETTINGS ===================
    with tab3:
        st.markdown("### ⚙️ Model & System Settings")
        st.markdown("Configure AI model settings and advanced options.")
        
        # Model Settings Section
        st.subheader("🤖 AI Model Configuration")
        
        # Display current model and provide model information
        st.info(f"Current model: **{st.session_state['openai_model']}**")
        
        # Add model information based on the selected model
        model_info = {
            "gpt-4o": "Latest and most capable model, optimized for performance and cost-effectiveness.",
            "gpt-4-turbo": "Powerful model with strong reasoning capabilities and knowledge up to Apr 2023.",
            "gpt-4": "Original GPT-4 model with high accuracy and reasoning capabilities.",
            "gpt-3.5-turbo": "Fast and cost-effective model for most general tasks. 16K context window."
        }
        
        if st.session_state["openai_model"] in model_info:
            st.caption(model_info[st.session_state["openai_model"]])
        
        # Model rate information
        st.caption("**Note:** Different models have different pricing. Check [OpenAI API Pricing](https://openai.com/api/pricing/) for details.")
        
        # Add a button to reset API key and change model
        if st.button("Change AI Model", use_container_width=True):
            del st.session_state["gpt_api_key"]
            del st.session_state["openai_model"]
            # Clear vector DB session state if it exists
            if "vector_db" in st.session_state:
                del st.session_state["vector_db"]
            st.rerun()
        
        # Advanced Settings Section
        st.divider()
        st.subheader("🔧 Advanced Settings")
        
        # Debug mode toggle
        debug_enabled = st.checkbox(
            "Enable debug mode", 
            key="debug_toggle", 
            value=st.session_state.get("show_debug", False),
            help="Show detailed information about agent tool usage and execution steps. Useful for understanding how the AI processes your questions."
        )
        st.session_state.show_debug = debug_enabled
        
        # Max iterations configuration
        max_iterations = st.slider(
            "Max Analysis Steps",
            min_value=3,
            max_value=20,
            value=st.session_state.get("max_iterations", 10),
            help="Maximum number of tool calls the AI agent can make per response. Higher values allow more complex analysis but may take longer."
        )
        st.session_state.max_iterations = max_iterations
        
        if debug_enabled:
            st.info("🔍 Debug mode is **ON**. You'll see detailed execution information after each AI response.")
        else:
            st.info("🔍 Debug mode is **OFF**. Clean interface with no technical details shown.")
        
        # Show current configuration
        st.caption(f"Current settings: Max steps = {max_iterations}, Debug = {'ON' if debug_enabled else 'OFF'}")
        
        # Additional System Information
        st.divider()
        st.subheader("ℹ️ System Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Session Documents", len(st.session_state.get('selected_doc_sources', [])))
            st.metric("Session Datasets", len(st.session_state.get('tabular_datasets', {})))
        
        with col2:
            st.metric("Chat Messages", len(st.session_state.get('messages', [])))
            st.metric("Stored Charts", len(st.session_state.get('stored_charts', {})))
        
        # Session Management
        st.divider()
        st.subheader("🗃️ Session Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Chat History", use_container_width=True):
                st.session_state.messages = []
                if "stored_charts" in st.session_state:
                    st.session_state.stored_charts = {}
                if "current_chart_id" in st.session_state:
                    st.session_state.current_chart_id = None
                if "current_chart_ids" in st.session_state:
                    st.session_state.current_chart_ids = []
                st.success("Chat history cleared!")
        
        with col2:
            if st.button("Reset All Settings", use_container_width=True):
                # Reset to defaults
                st.session_state.show_debug = False
                st.session_state.max_iterations = 10
                st.success("Settings reset to defaults!")

def display_tabular_sources():
    """Display available tabular data sources with management options"""
    available_datasets = st.session_state.get("tabular_datasets", {})
    
    if available_datasets:
        st.subheader("📊 Tabular Data Sources")
        
        # Add debug mode toggle
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{len(available_datasets)} dataset(s) available for analysis:**")
        with col2:
            debug_mode = st.checkbox("🔧 Debug Mode", 
                                   value=st.session_state.get("show_debug", False),
                                   help="Show detailed debugging information for chart generation")
            st.session_state.show_debug = debug_mode
        
        # Display datasets in columns
        cols = st.columns(min(len(available_datasets), 3))
        for idx, (name, df) in enumerate(available_datasets.items()):
            with cols[idx % 3]:
                with st.expander(f"📊 {name}", expanded=False):
                    st.write(f"**Rows:** {df.shape[0]:,}")
                    st.write(f"**Columns:** {df.shape[1]}")
                    st.write("**Column names:**")
                    for col in df.columns:
                        st.write(f"• {col}")
                    
                    # Show sample data
                    st.write("**Sample data:**")
                    st.dataframe(df.head(3), use_container_width=True)
                    
                    # Add data type info in debug mode
                    if st.session_state.get("show_debug", False):
                        st.write("**Data types:**")
                        for col, dtype in df.dtypes.items():
                            st.write(f"• {col}: {dtype}")
        
        st.markdown("---")
        st.markdown("💡 **Tip:** Reference column names exactly as shown above when requesting specific charts.")
        
        # Clear data option
        if st.button("🗑️ Clear All Tabular Data", type="secondary"):
            st.session_state.tabular_datasets = {}
            st.success("All tabular data cleared!")
            st.rerun()
    else:
        st.info("📊 No tabular datasets loaded. Upload CSV or Excel files on the Home page to get started.")
