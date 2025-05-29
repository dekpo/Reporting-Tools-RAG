# Packages
import streamlit as st
import pandas as pd

# Utils
import lib

# The App config and styling
lib.app_config()

# Sidebar and Navbar
lib.sidebar()

st.title("❓ Help & Documentation")
st.markdown("*Your guide to getting the most out of DTN Reporting Tools*")

def show_quick_start():
    st.header("🚀 Quick Start Guide")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Welcome to DTN Reporting Tools!
        
        This application helps you process documents, anonymize content, and generate insights using AI. Here's how to get started:
        
        #### **Step 1: Upload & Extract** 📁
        - Go to the **Home** page
        - Upload your files (.docx, .vtt, .pdf, .csv, .xlsx)
        - Or paste text directly into the text area
        - The content will be automatically processed
        
        #### **Step 2: Anonymize (Optional)** 🔒
        - For sensitive documents, visit the **Anonymize** page
        - The system will detect and replace names, organizations, locations
        - This protects privacy while maintaining document structure
        
        #### **Step 3: AI Analysis** 🤖
        - Head to the **ChatGPT Tool** page
        - Select your documents/datasets in the sidebar
        - Ask questions or request analysis using natural language
        - Generate reports, summaries, charts, and insights
        
        #### **Step 4: Revert (If Needed)** ↩️
        - If you anonymized content, use the **Revert** page
        - Convert AI responses back to original entities
        - Get your final reports with real names and organizations
        """)
    
    with col2:
        st.info("""
        **💡 Pro Tips:**
        
        ✅ **Start Simple:** Upload one document first to get familiar
        
        ✅ **Use Templates:** Check the Prompt Engineering tab for ready-made prompts
        
        ✅ **Combine Data:** Mix text documents with spreadsheets for richer analysis
        
        ✅ **Be Specific:** The more detail in your questions, the better the results
        """)
        
        st.success("""
        **🎯 Most Popular Use Cases:**
        
        📊 Meeting report generation
        📈 Data visualization
        🔍 Document summarization
        📋 Action item extraction
        """)

def show_prompt_engineering():
    st.header("📝 Prompt Engineering Guide")
    
    st.markdown("""
    Good prompts are the key to getting excellent results from AI. Here are proven templates and techniques:
    """)
    
    # Create sub-tabs for different prompt categories
    prompt_tab1, prompt_tab2, prompt_tab3, prompt_tab4 = st.tabs([
        "📊 Text Analysis", "📈 Data Analysis", "🎯 Advanced", "🛠️ Prompt Builder"
    ])
    
    with prompt_tab1:
        show_text_analysis_prompts()
    
    with prompt_tab2:
        show_data_analysis_prompts()
    
    with prompt_tab3:
        show_advanced_prompts()
    
    with prompt_tab4:
        show_prompt_builder()

def show_text_analysis_prompts():
    st.subheader("📊 Text Analysis & Summarization")
    
    templates = {
        "🏢 Meeting Report Generation": {
            "description": "Create professional meeting reports with structure",
            "template": """Analyze this transcript and create a professional report with the following structure:

**Executive Summary:** Key outcomes and decisions in 2-3 sentences
**Discussion Points:** Main topics covered, organized thematically  
**Decisions Made:** Clear list of what was agreed upon
**Action Items:** Who needs to do what by when
**Next Steps:** Follow-up meetings and timelines

Please write in a formal, professional tone suitable for organizational reporting.""",
            "when_to_use": "For meeting transcripts, interviews, or discussion recordings"
        },
        
        "📋 Thematic Analysis": {
            "description": "Organize content by themes and topics",
            "template": """Identify the main themes in this document and organize the content accordingly:

1. **Theme Identification:** List 3-5 major themes
2. **Content Organization:** Group relevant points under each theme
3. **Key Insights:** Provide 2-3 insights for each theme
4. **Cross-Theme Connections:** Note any relationships between themes

Present findings in a clear, structured format with bullet points.""",
            "when_to_use": "For long documents, reports, or complex discussions"
        },
        
        "⚡ Quick Summary": {
            "description": "Fast, concise overview of content",
            "template": """Provide a concise 3-paragraph summary:

**Paragraph 1:** What was the main focus and key topics discussed?
**Paragraph 2:** What were the primary conclusions, decisions, or findings?
**Paragraph 3:** What are the next steps, recommendations, or actions required?

Keep each paragraph to 3-4 sentences maximum.""",
            "when_to_use": "When you need a quick overview or executive briefing"
        },
        
        "🎯 Action-Focused Analysis": {
            "description": "Extract actionable items and commitments",
            "template": """Extract all actionable elements from this content:

**Immediate Actions:** Tasks that need to be done within 1-2 weeks
**Medium-term Actions:** Tasks for the next 1-3 months  
**Long-term Commitments:** Strategic actions beyond 3 months
**Responsible Parties:** Who is accountable for each action
**Dependencies:** What needs to happen before each action can proceed

Format as a clear action plan with timelines.""",
            "when_to_use": "For project meetings, planning sessions, or strategy discussions"
        }
    }
    
    for title, details in templates.items():
        with st.expander(title):
            st.markdown(f"**Purpose:** {details['description']}")
            st.markdown(f"**When to use:** {details['when_to_use']}")
            st.markdown("**Template:**")
            st.code(details['template'], language="text")
            if st.button(f"Copy {title}", key=f"copy_{title}"):
                st.success("✅ Template copied! Paste it in the ChatGPT Tool.")

def show_data_analysis_prompts():
    st.subheader("📈 Data Analysis & Visualization")
    
    data_templates = {
        "📊 Data Overview & Summary": {
            "description": "Get a comprehensive understanding of your dataset",
            "template": """Analyze this dataset and provide:

**Data Structure:** Number of rows, columns, data types
**Key Statistics:** Summary statistics for numerical columns
**Data Quality:** Missing values, outliers, inconsistencies  
**Initial Insights:** 3-5 interesting patterns or findings
**Recommended Visualizations:** What charts would best show this data

Please be specific about column names and values you observe.""",
            "chart_suggestions": ["Summary tables", "Distribution plots", "Missing data heatmaps"]
        },
        
        "🔍 Specific Metric Analysis": {
            "description": "Deep dive into particular metrics or relationships",
            "template": """Focus on [METRIC/COLUMN] in this dataset:

**Trend Analysis:** How has [METRIC] changed over time?
**Segmentation:** Break down [METRIC] by [CATEGORY/DIMENSION]
**Top Performers:** Identify highest and lowest values with context
**Correlations:** What other variables relate to [METRIC]?
**Visualizations:** Create charts showing these relationships

Replace [METRIC] and [CATEGORY] with actual column names from your data.""",
            "chart_suggestions": ["Bar charts", "Line charts", "Scatter plots", "Box plots"]
        },
        
        "📈 Trend & Time Analysis": {
            "description": "Understand changes over time periods",
            "template": """Analyze temporal patterns in this data:

**Overall Trends:** What's the general direction over time?
**Seasonal Patterns:** Any recurring patterns by month, quarter, year?
**Notable Changes:** Significant increases, decreases, or shifts
**Forecast Insights:** What do current trends suggest for the future?
**Time-based Charts:** Create appropriate visualizations

Focus on time-based columns and show trends clearly.""",
            "chart_suggestions": ["Line charts", "Time series plots", "Seasonal decomposition"]
        },
        
        "🎯 Comparative Analysis": {
            "description": "Compare different groups, regions, or categories",
            "template": """Compare [GROUP A] vs [GROUP B] in this dataset:

**Key Differences:** How do these groups differ across metrics?
**Performance Ranking:** Which performs better and in what areas?
**Statistical Significance:** Are differences meaningful?
**Visualization:** Create charts highlighting the comparisons
**Recommendations:** What insights emerge from these differences?

Replace [GROUP A] and [GROUP B] with actual categories from your data.""",
            "chart_suggestions": ["Bar charts", "Grouped charts", "Heatmaps", "Box plots"]
        }
    }
    
    for title, details in data_templates.items():
        with st.expander(title):
            st.markdown(f"**Purpose:** {details['description']}")
            st.markdown("**Template:**")
            st.code(details['template'], language="text")
            st.markdown(f"**Recommended Charts:** {', '.join(details['chart_suggestions'])}")
            if st.button(f"Copy {title}", key=f"copy_data_{title}"):
                st.success("✅ Template copied! Paste it in the ChatGPT Tool.")

def show_advanced_prompts():
    st.subheader("🎯 Advanced Techniques")
    
    st.markdown("""
    ### 🧠 Prompt Engineering Principles
    
    Based on proven techniques for better AI responses:
    """)
    
    principles = {
        "📋 Clear Instructions": {
            "principle": "Be specific about what you want",
            "example": "❌ 'Analyze this data'\n✅ 'Create a bar chart showing top 5 countries by funding amount, include percentage labels'",
            "tips": ["Use action verbs", "Specify output format", "Include context details"]
        },
        
        "🎭 Persona & Style": {
            "principle": "Set the right tone and expertise level",
            "example": "✅ 'Act as a UN policy analyst. Write in formal diplomatic language suitable for member state briefings.'",
            "tips": ["Define expertise level", "Specify writing style", "Set audience context"]
        },
        
        "🔄 Step-by-Step Processing": {
            "principle": "Break complex tasks into steps",
            "example": "✅ 'First, summarize the main points. Then, identify action items. Finally, suggest next steps.'",
            "tips": ["Use numbered steps", "Build complexity gradually", "Allow for iteration"]
        },
        
        "🤔 Reasoning & Validation": {
            "principle": "Ask for explanations and self-checking",
            "example": "✅ 'Explain your reasoning for each recommendation and check if you missed any important details.'",
            "tips": ["Request explanations", "Ask for self-validation", "Encourage critical thinking"]
        }
    }
    
    for title, details in principles.items():
        with st.expander(title):
            st.markdown(f"**Principle:** {details['principle']}")
            st.markdown("**Example:**")
            st.code(details['example'], language="text")
            st.markdown("**Tips:**")
            for tip in details['tips']:
                st.markdown(f"• {tip}")

def show_prompt_builder():
    st.subheader("🛠️ Interactive Prompt Builder")
    
    st.markdown("Build custom prompts using this guided form:")
    
    # Task Type Selection
    task_type = st.selectbox(
        "What do you want to do?",
        ["Summarize content", "Analyze data", "Generate report", "Extract information", "Create visualization", "Compare items"]
    )
    
    # Content Type
    content_type = st.selectbox(
        "What type of content are you working with?",
        ["Meeting transcript", "Document", "Dataset/Spreadsheet", "Multiple documents", "Mixed content"]
    )
    
    # Output Format
    output_format = st.selectbox(
        "How should the output be formatted?",
        ["Professional report", "Bullet points", "Executive summary", "Detailed analysis", "Charts and graphs", "Action list"]
    )
    
    # Audience
    audience = st.selectbox(
        "Who is the audience?",
        ["General public", "Colleagues/Team", "Management/Leadership", "Technical experts", "External stakeholders"]
    )
    
    # Additional Instructions
    additional = st.text_area(
        "Additional specific requirements:",
        placeholder="e.g., Include specific metrics, focus on certain themes, use particular terminology..."
    )
    
    if st.button("🔨 Generate Custom Prompt"):
        prompt = generate_custom_prompt(task_type, content_type, output_format, audience, additional)
        st.markdown("### Your Custom Prompt:")
        st.code(prompt, language="text")
        st.success("✅ Copy this prompt and use it in the ChatGPT Tool!")

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

def show_examples_gallery():
    st.header("💡 Examples Gallery")
    
    st.markdown("Real-world examples showing the power of good prompts:")
    
    example_categories = st.radio(
        "Choose example category:",
        ["📊 Meeting Reports", "📈 Data Insights", "🔍 Document Analysis", "📋 Action Planning"]
    )
    
    if example_categories == "📊 Meeting Reports":
        show_meeting_examples()
    elif example_categories == "📈 Data Insights":
        show_data_examples()
    elif example_categories == "🔍 Document Analysis":
        show_document_examples()
    elif example_categories == "📋 Action Planning":
        show_action_examples()

def show_meeting_examples():
    st.subheader("📊 Meeting Report Examples")
    
    with st.expander("Example 1: UN Committee Meeting Report"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Input Prompt:**")
            st.code("""
Please thoroughly review this committee meeting transcript and create a comprehensive report following UN reporting standards:

**Structure Required:**
- Executive Summary
- Key Discussion Points  
- Decisions and Recommendations
- Action Items with Timelines
- Next Steps

Write in formal diplomatic language suitable for member state distribution. Focus on consensus building and actionable outcomes.
            """)
        
        with col2:
            st.markdown("**Sample Output Structure:**")
            st.markdown("""
            **Executive Summary**
            The Committee reviewed progress on sustainable development initiatives...
            
            **Key Discussion Points**
            • Climate adaptation strategies
            • Funding mechanisms 
            • Inter-agency coordination
            
            **Decisions Made**
            1. Approved budget allocation for Q4
            2. Established working group on...
            
            **Action Items**
            - [ ] Draft policy paper (Secretariat, by Dec 15)
            - [ ] Coordinate with agencies (Chair, ongoing)
            """)

def show_data_examples():
    st.subheader("📈 Data Analysis Examples")
    
    with st.expander("Example 1: Humanitarian Funding Analysis"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Input Prompt:**")
            st.code("""
Analyze this humanitarian funding dataset:

1. Show funding trends over the past 3 years
2. Identify top 5 donor countries by total contribution
3. Create a bar chart comparing regional allocations
4. Highlight any significant patterns or anomalies
5. Provide recommendations for future funding strategies

Include appropriate visualizations and explain your findings.
            """)
        
        with col2:
            st.markdown("**Expected Deliverables:**")
            st.markdown("""
            ✅ **Trend Analysis**
            Line chart showing yearly progression
            
            ✅ **Donor Ranking** 
            Bar chart with top contributors
            
            ✅ **Regional Breakdown**
            Pie chart or bar chart by region
            
            ✅ **Insights**
            Key patterns and recommendations
            
            ✅ **Strategic Recommendations**
            Data-driven funding strategies
            """)

def show_document_examples():
    st.subheader("🔍 Document Analysis Examples")
    
    with st.expander("Example 1: Policy Document Review"):
        st.markdown("**Scenario:** Analyzing a complex policy document")
        st.code("""
Review this policy document and provide:

**Content Analysis:**
- Main policy objectives and scope
- Key stakeholder groups affected
- Implementation requirements and timelines

**Critical Assessment:**
- Strengths and potential challenges
- Alignment with existing frameworks
- Resource and capacity implications

**Recommendations:**
- Priority implementation areas
- Risk mitigation strategies
- Success metrics and monitoring approaches

Present findings in executive briefing format.
        """)

def show_action_examples():
    st.subheader("📋 Action Planning Examples")
    
    with st.expander("Example 1: Project Next Steps Extraction"):
        st.markdown("**Scenario:** Converting meeting discussions into actionable plans")
        st.code("""
Extract actionable items from this meeting discussion:

**Immediate Actions (1-2 weeks):**
- Task, responsible party, deadline

**Medium-term Actions (1-3 months):**
- Task, responsible party, deadline

**Strategic Initiatives (3+ months):**
- Initiative, lead organization, timeline

**Dependencies and Prerequisites:**
- What must happen before each action

Format as a project management action plan with clear accountability.
        """)

def show_features_guide():
    st.header("⚙️ Features Guide")
    
    feature_sections = st.radio(
        "Select feature to learn about:",
        ["📁 File Processing", "🔒 Anonymization", "🤖 AI Analysis", "📊 Data Visualization", "🔄 RAG System"]
    )
    
    if feature_sections == "📁 File Processing":
        show_file_processing_guide()
    elif feature_sections == "🔒 Anonymization":
        show_anonymization_guide()
    elif feature_sections == "🤖 AI Analysis":
        show_ai_analysis_guide()
    elif feature_sections == "📊 Data Visualization":
        show_visualization_guide()
    elif feature_sections == "🔄 RAG System":
        show_rag_guide()

def show_file_processing_guide():
    st.subheader("📁 File Processing Capabilities")
    
    st.markdown("""
    ### Supported File Types
    
    The application can process various file formats automatically:
    """)
    
    file_types = {
        "📄 Text Documents": {
            "formats": [".docx", ".pdf", ".txt"],
            "description": "Word documents, PDFs, and plain text files",
            "features": ["Text extraction", "Content parsing", "Structure preservation"]
        },
        "🎥 Meeting Files": {
            "formats": [".vtt", ".srt"],
            "description": "Teams/Zoom meeting transcripts and subtitles",
            "features": ["Timestamp extraction", "Speaker identification", "Automatic formatting"]
        },
        "📊 Data Files": {
            "formats": [".csv", ".xlsx", ".xls"],
            "description": "Spreadsheets and tabular data",
            "features": ["Data type detection", "Column analysis", "Statistical summaries"]
        }
    }
    
    for category, details in file_types.items():
        with st.expander(category):
            st.markdown(f"**Supported formats:** {', '.join(details['formats'])}")
            st.markdown(f"**Description:** {details['description']}")
            st.markdown("**Key features:**")
            for feature in details['features']:
                st.markdown(f"• {feature}")

def show_anonymization_guide():
    st.subheader("🔒 Anonymization & Privacy")
    
    st.markdown("""
    ### What Gets Anonymized
    
    The system automatically detects and replaces sensitive information:
    """)
    
    entities = {
        "👤 People": ["Names", "Titles", "Personal identifiers"],
        "🏢 Organizations": ["Company names", "Institution names", "Department names"],
        "📍 Locations": ["Cities", "Countries", "Addresses", "Regions"],
        "📧 Contact Info": ["Email addresses", "Phone numbers"],
        "🆔 Identifiers": ["Account numbers", "Reference codes", "IDs"]
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        for category, items in entities.items():
            st.markdown(f"**{category}**")
            for item in items:
                st.markdown(f"• {item}")
    
    with col2:
        st.info("""
        **🔒 Privacy Protection:**
        
        ✅ Original entities never sent to AI
        ✅ Secure local processing
        ✅ Reversible anonymization
        ✅ No data retention by AI service
        """)

def show_ai_analysis_guide():
    st.subheader("🤖 AI Analysis Capabilities")
    
    st.markdown("""
    ### What the AI Can Do
    
    The ChatGPT integration provides powerful analysis capabilities:
    """)
    
    capabilities = {
        "📝 Text Analysis": [
            "Document summarization",
            "Key point extraction", 
            "Thematic analysis",
            "Report generation",
            "Action item identification"
        ],
        "📊 Data Analysis": [
            "Statistical summaries",
            "Trend identification",
            "Correlation analysis",
            "Comparative analysis",
            "Pattern recognition"
        ],
        "🎨 Visualization": [
            "Chart generation",
            "Interactive plots",
            "Custom visualizations",
            "Multi-chart dashboards",
            "Data storytelling"
        ],
        "🔍 Advanced Features": [
            "Cross-document analysis",
            "Multi-source insights",
            "Fact verification",
            "Recommendation generation",
            "Scenario planning"
        ]
    }
    
    for category, items in capabilities.items():
        with st.expander(category):
            for item in items:
                st.markdown(f"• {item}")

def show_visualization_guide():
    st.subheader("📊 Data Visualization Guide")
    
    st.markdown("### Available Chart Types & When to Use Them")
    
    charts = {
        "📊 Bar Charts": {
            "use_case": "Comparing categories or showing rankings",
            "example": "Funding by region, top performing countries",
            "prompt": "Create a bar chart showing the top 10 countries by humanitarian aid received"
        },
        "📈 Line Charts": {
            "use_case": "Showing trends over time",
            "example": "Budget changes over years, population growth",
            "prompt": "Show me a line chart of refugee populations from 2020 to 2023"
        },
        "🥧 Pie Charts": {
            "use_case": "Showing proportions and percentages",
            "example": "Budget allocation by sector, demographic breakdowns",
            "prompt": "Create a pie chart showing the distribution of development aid by sector"
        },
        "📉 Scatter Plots": {
            "use_case": "Exploring relationships between variables",
            "example": "Income vs education, funding vs outcomes",
            "prompt": "Show me a scatter plot of education spending vs literacy rates"
        },
        "📦 Box Plots": {
            "use_case": "Statistical distribution analysis",
            "example": "Performance variations, outcome distributions",
            "prompt": "Create box plots showing the distribution of project completion times by region"
        }
    }
    
    for chart_type, details in charts.items():
        with st.expander(chart_type):
            st.markdown(f"**Best for:** {details['use_case']}")
            st.markdown(f"**Example use:** {details['example']}")
            st.markdown("**Sample prompt:**")
            st.code(details['prompt'])

def show_rag_guide():
    st.subheader("🔄 RAG (Retrieval-Augmented Generation) System")
    
    st.markdown("""
    ### How RAG Enhances Your Analysis
    
    The RAG system makes AI responses more accurate by finding relevant context from your documents:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **How It Works:**
        1. 📚 Documents stored in vector database
        2. 🔍 Your question triggers semantic search
        3. 📄 Relevant content retrieved automatically
        4. 🤖 AI generates response using context
        5. ✅ More accurate, grounded answers
        """)
    
    with col2:
        st.markdown("""
        **Benefits:**
        • Answers based on your actual documents
        • Reduces hallucination and errors
        • Maintains privacy (anonymized content)
        • Works across multiple documents
        • Finds connections you might miss
        """)
    
    st.info("""
    **💡 Pro Tip:** Upload related documents together for better cross-referencing and more comprehensive analysis.
    """)

def show_troubleshooting():
    st.header("🔧 Troubleshooting")
    
    issues = {
        "🚫 File Upload Issues": {
            "symptoms": ["File won't upload", "Processing errors", "Unsupported format"],
            "solutions": [
                "Check file size (must be under 200MB)",
                "Ensure file format is supported (.docx, .pdf, .vtt, .csv, .xlsx)",
                "Try converting to a supported format",
                "Check file isn't corrupted or password-protected"
            ]
        },
        "🤖 AI Not Responding": {
            "symptoms": ["No response from ChatGPT", "Error messages", "Slow responses"],
            "solutions": [
                "Check your internet connection",
                "Verify OpenAI API key is configured",
                "Try a simpler question first",
                "Check if documents are properly loaded",
                "Refresh the page and try again"
            ]
        },
        "📊 Charts Not Generating": {
            "symptoms": ["No charts appear", "Chart errors", "Wrong visualizations"],
            "solutions": [
                "Ensure data files are uploaded and selected",
                "Check column names match your request",
                "Use specific column names in your prompt",
                "Try requesting chart type explicitly",
                "Verify data has appropriate format for visualization"
            ]
        },
        "🔒 Anonymization Problems": {
            "symptoms": ["Entities not detected", "Wrong replacements", "Revert issues"],
            "solutions": [
                "Check document language is English",
                "Verify text is properly formatted",
                "Manual review of anonymized content",
                "Use custom entity lists if needed",
                "Process documents one at a time for complex content"
            ]
        }
    }
    
    for issue, details in issues.items():
        with st.expander(issue):
            st.markdown("**Common symptoms:**")
            for symptom in details['symptoms']:
                st.markdown(f"• {symptom}")
            st.markdown("**Solutions to try:**")
            for solution in details['solutions']:
                st.markdown(f"✅ {solution}")
    
    st.warning("""
    **💡 Still having issues?** Contact the development team using the contact information at the bottom of this page.
    """)

# ===== MAIN CONTENT - Tabs and Contact Section =====
# Create tabs for different help sections
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Quick Start", 
    "📝 Prompt Engineering", 
    "💡 Examples Gallery", 
    "⚙️ Features Guide",
    "🔧 Troubleshooting"
])

with tab1:
    show_quick_start()

with tab2:
    show_prompt_engineering()

with tab3:
    show_examples_gallery()

with tab4:
    show_features_guide()

with tab5:
    show_troubleshooting()

# Discrete contact section at the bottom
st.markdown("---")
with st.expander("📧 Contact Information", expanded=False):
    st.markdown("""
    <div style='font-size: 0.9em; color: #666;'>
    For any questions regarding this app please contact:<br>
    • <a href='mailto:pierre.cornier@un.org'>Pierre Cornier</a> (pierre.cornier@un.org)<br>
    • <a href='mailto:dekpo.yologaza@un.org'>Dekpo Yologaza</a> (dekpo.yologaza@un.org)<br>
    <em>From the United Nations System Chief Executives Board for Coordination (UN CEB) at UNOG</em>
    </div>
    """, unsafe_allow_html=True) 