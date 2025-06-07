import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import json
import os
from pathlib import Path
import time

# Import our custom modules
from ai_agent import EnterpriseAIAgent, initialize_agent
from document_processor import DocumentProcessor

# Page configuration
st.set_page_config(
    page_title="Enterprise AI Document Q&A Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
        color: #333;
    }
    .user-message {
        background-color: #f0f8ff;
        border-left-color: #1f77b4;
    }
    .ai-message {
        background-color: #f8f9fa;
        border-left-color: #28a745;
    }
    .sidebar-content {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-online { background-color: #28a745; }
    .status-offline { background-color: #dc3545; }
    .status-processing { background-color: #ffc107; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize session state variables."""
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'processed_docs' not in st.session_state:
        st.session_state.processed_docs = {}
    if 'doc_processor' not in st.session_state:
        st.session_state.doc_processor = DocumentProcessor()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'arxiv_results' not in st.session_state:
        st.session_state.arxiv_results = []

def main():
    """Main application function."""
    initialize_session_state()
    
    # Main header
    st.markdown('<h1 class="main-header">🤖 Enterprise AI Document Q&A Agent</h1>', unsafe_allow_html=True)
    
    # Initialize agent if not already done
    if st.session_state.agent is None:
        with st.spinner("Initializing AI Agent..."):
            st.session_state.agent = initialize_agent()
    
    # Status indicator
    status_color = "status-online" if st.session_state.agent else "status-offline"
    status_text = "Online" if st.session_state.agent else "Offline"
    st.markdown(f'<div><span class="{status_color} status-indicator"></span>Agent Status: {status_text}</div>', unsafe_allow_html=True)
    
    if not st.session_state.agent:
        st.error("⚠️ AI Agent initialization failed. Please check your API configuration.")
        return
    
    # Sidebar configuration
    setup_sidebar()
    
    st.markdown("""
    <style>
    div[data-baseweb="tab-list"] {
        border-radius: 10px;
        padding: 1rem;
        width: 100% !important;
        display: flex;
        flex-wrap: wrap;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }
    .stTabs > div {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Document Processing", "💬 Q&A Interface", "🔍 ArXiv Search", "📊 Analytics"])
    
    with tab1:
        document_processing_tab()
    
    with tab2:
        qa_interface_tab()
    
    with tab3:
        arxiv_search_tab()
    
    with tab4:
        analytics_tab()

def setup_sidebar():
    """Setup sidebar with navigation and controls."""
    st.sidebar.markdown("# 🎛️ Control Panel")
    
    # Document management
    st.sidebar.markdown("### 📁 Document Management")
    doc_count = len(st.session_state.processed_docs)
    st.sidebar.metric("Processed Documents", doc_count)
    
    if doc_count > 0:
        if st.sidebar.button("🗑️ Clear All Documents"):
            st.session_state.processed_docs = {}
            st.session_state.doc_processor = DocumentProcessor()
            st.success("All documents cleared!")
    
    # Chat management
    st.sidebar.markdown("### 💬 Chat Management")
    if st.session_state.chat_history:
        st.sidebar.metric("Chat Messages", len(st.session_state.chat_history))
        if st.sidebar.button("🧹 Clear Chat History"):
            st.session_state.chat_history = []
            if st.session_state.agent:
                st.session_state.agent.clear_history()
            st.success("Chat history cleared!")
    
    # Settings
    st.sidebar.markdown("### ⚙️ Settings")
    st.sidebar.selectbox("Response Style", ["Detailed", "Concise", "Technical"], key="response_style")
    st.sidebar.slider("Max ArXiv Results", 1, 20, 5, key="max_arxiv_results")
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

def document_processing_tab():
    """Document processing and upload interface."""
    st.markdown('<h2 class="sub-header">📄 Document Processing</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Upload Documents")
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload one or more PDF documents for processing"
        )
        
        if uploaded_files:
            process_button = st.button("🔄 Process Documents", type="primary")
            
            if process_button:
                process_uploaded_files(uploaded_files)
    
    with col2:
        st.markdown("### Processing Status")
        if st.session_state.processed_docs:
            for doc_name, doc_data in st.session_state.processed_docs.items():
                with st.expander(f"📄 {doc_name}"):
                    summary = st.session_state.doc_processor.get_document_summary(doc_name)
                    st.json(summary)
        else:
            st.info("No documents processed yet.")
    
    # Display processed documents overview
    if st.session_state.processed_docs:
        st.markdown("### 📊 Document Overview")
        display_document_overview()

def process_uploaded_files(uploaded_files):
    """Process uploaded PDF files."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    os.makedirs("temp_uploads", exist_ok=True)
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        # Save uploaded file temporarily
        temp_path = f"temp_uploads/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # Process the document
            content = st.session_state.doc_processor.extract_pdf_content(temp_path)
            st.session_state.processed_docs[uploaded_file.name] = content
            
            # Clean up temp file
            os.remove(temp_path)
            
            st.success(f"✅ Successfully processed {uploaded_file.name}")
            
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text("Processing complete!")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()

def display_document_overview():
    """Display overview of processed documents."""
    doc_data = []
    
    for doc_name, doc_content in st.session_state.processed_docs.items():
        summary = st.session_state.doc_processor.get_document_summary(doc_name)
        doc_data.append({
            'Document': doc_name,
            'Pages': summary.get('pages', 0),
            'Sections': len(summary.get('sections', [])),
            'Tables': summary.get('tables_count', 0),
            'References': summary.get('references_count', 0),
            'Word Count': summary.get('word_count', 0)
        })
    
    if doc_data:
        df = pd.DataFrame(doc_data)
        st.dataframe(df, use_container_width=True)
        
        # Visualization
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(df, x='Document', y='Pages', title='Pages per Document')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(df, values='Word Count', names='Document', title='Word Count Distribution')
            st.plotly_chart(fig, use_container_width=True)

def qa_interface_tab():
    """Q&A interface for document queries."""
    st.markdown('<h2 class="sub-header">💬 Document Q&A Interface</h2>', unsafe_allow_html=True)
    
    if not st.session_state.processed_docs:
        st.warning("⚠️ Please process some documents first in the Document Processing tab.")
        return
    
    # Query input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        user_query = st.text_input(
            "Ask a question about your documents:",
            placeholder="e.g., What are the main findings in the research papers?",
            key="user_query"
        )
    
    with col2:
        query_type = st.selectbox(
            "Query Type",
            ["general", "summary", "extraction"],
            help="Choose the type of query for optimized responses"
        )
    
    # Process query
    if user_query:
        if st.button("🚀 Ask Question", type="primary"):
            process_query(user_query, query_type)
    
    # Display chat history
    display_chat_history()

def process_query(query: str, query_type: str):
    """Process user query and get AI response."""
    with st.spinner("🤔 Thinking..."):
        try:
            response = st.session_state.agent.query_documents(
                query, 
                st.session_state.processed_docs, 
                query_type
            )
            
            # Add to chat history
            st.session_state.chat_history.append({
                'query': query,
                'response': response,
                'type': query_type
            })
            
            st.success("✅ Query processed successfully!")
            
        except Exception as e:
            st.error(f"❌ Error processing query: {str(e)}")

def display_chat_history():
    """Display chat history with enhanced formatting."""
    if st.session_state.chat_history:
        st.markdown("### 📝 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history[-10:])):  # Show last 10
            with st.container():
                st.markdown(f'<div class="chat-message user-message"><strong>🧑 You :</strong><br>{chat["query"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-message ai-message"><strong>🤖 AI Assistant:</strong><br>{chat["response"]}</div>', unsafe_allow_html=True)
                st.markdown("---")

def arxiv_search_tab():
    """ArXiv search and paper discovery interface."""
    st.markdown('<h2 class="sub-header">🔍 ArXiv Paper Search</h2>', unsafe_allow_html=True)
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_description = st.text_area(
            "Describe the paper you're looking for:",
            placeholder="e.g., Machine learning papers about natural language processing with transformer models",
            height=100
        )
    
    with col2:
        st.markdown("### Search Settings")
        max_results = st.number_input("Max Results", 1, 20, st.session_state.get('max_arxiv_results', 5))
        search_button = st.button("🔍 Search ArXiv", type="primary")
    
    # Process search
    if search_button and search_description:
        search_arxiv_papers(search_description, max_results)
    
    # Display search results
    display_arxiv_results()

def search_arxiv_papers(description: str, max_results: int):
    """Search ArXiv papers based on description."""
    with st.spinner("🔍 Searching ArXiv database..."):
        try:
            results = st.session_state.agent.search_arxiv_papers(description, max_results)
            st.session_state.arxiv_results = results
            
            if results:
                st.success(f"✅ Found {len(results)} papers!")
            else:
                st.warning("⚠️ No papers found matching your description.")
                
        except Exception as e:
            st.error(f"❌ Error searching ArXiv: {str(e)}")

def display_arxiv_results():
    """Display ArXiv search results with enhanced formatting."""
    if st.session_state.arxiv_results:
        st.markdown("### 📚 Search Results")
        
        for i, paper in enumerate(st.session_state.arxiv_results):
            with st.expander(f"📄 {paper['title'][:80]}...", expanded=(i == 0)):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Title:** {paper['title']}")
                    st.markdown(f"**Authors:** {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
                    st.markdown(f"**Published:** {paper['published']}")
                    st.markdown(f"**Categories:** {', '.join(paper['categories'])}")
                    
                    # Summary with truncation
                    summary = paper['summary']
                    if len(summary) > 300:
                        summary = summary[:300] + "..."
                    st.markdown(f"**Abstract:** {summary}")
                
                with col2:
                    st.markdown("**Actions:**")
                    st.markdown(f"[📖 View PDF]({paper['pdf_url']})")
                    
                    # Download button
                    if st.button(f"📥 Download", key=f"download_{i}"):
                        download_paper(paper['arxiv_id'], paper['title'])
                    
                    # Add to processing queue
                    if st.button(f"➕ Add to Queue", key=f"queue_{i}"):
                        st.info("Feature coming soon: Auto-download and process paper")

def download_paper(arxiv_id: str, title: str):
    """Download paper from ArXiv."""
    with st.spinner(f"📥 Downloading {title[:30]}..."):
        try:
            filepath = st.session_state.agent.download_arxiv_paper(arxiv_id)
            if filepath:
                st.success(f"✅ Downloaded: {title[:50]}...")
                st.info(f"📁 Saved to: {filepath}")
            else:
                st.error("❌ Download failed")
        except Exception as e:
            st.error(f"❌ Download error: {str(e)}")

def analytics_tab():
    """Analytics and insights dashboard."""
    st.markdown('<h2 class="sub-header">📊 Analytics Dashboard</h2>', unsafe_allow_html=True)
    
    if not st.session_state.processed_docs and not st.session_state.chat_history:
        st.info("📈 Analytics will appear here once you process documents and start chatting!")
        return
    
    st.markdown("""
    <style>
        .metrics-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin: 20px 0;
        }

        .metric-card {
            background: #000;
            border-radius: 16px;
            padding: 32px 24px;
            text-align: center;
            box-shadow: 
                0 10px 25px rgba(0, 0, 0, 0.1),
                0 4px 10px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.8);
            border-shadow: 0 4px 8px rgba(0, 0, 255, 0.1);
            backdrop-filter: blur(10px);
        }

        .metric-card:hover {
            transform: translateY(-8px);
            box-shadow: 
                0 20px 40px rgba(0, 0, 0, 0.15),
                0 8px 16px rgba(0, 0, 0, 0.1);
        }

        .metric-value {
            font-size: 3rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .metric-label {
            font-size: 1rem;
            font-weight: 500;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        @media (max-width: 768px) {
            .metrics-container {
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            }
        }

        @media (max-width: 480px) {
            .metrics-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # Calculate metrics
    total_pages = sum(doc.get('total_pages', 0) for doc in st.session_state.processed_docs.values())

    # Render metrics
    st.markdown(f"""
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-value">{len(st.session_state.processed_docs)}</div>
            <div class="metric-label">Documents Processed</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{total_pages:,}</div>
            <div class="metric-label">Total Pages</div>
        </div>        
        <div class="metric-card">
            <div class="metric-value">{len(st.session_state.chat_history)}</div>
            <div class="metric-label">Chat Interactions</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{len(st.session_state.arxiv_results)}</div>
            <div class="metric-label">ArXiv Searches</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Document analytics
    if st.session_state.processed_docs:
        st.markdown("### 📄 Document Analytics")
        
        # Create analytics dataframe
        analytics_data = []
        for doc_name, doc_content in st.session_state.processed_docs.items():
            summary = st.session_state.doc_processor.get_document_summary(doc_name)
            analytics_data.append({
                'Document': doc_name,
                'Pages': summary.get('pages', 0),
                'Sections': len(summary.get('sections', [])),
                'Tables': summary.get('tables_count', 0),
                'References': summary.get('references_count', 0),
                'Words': summary.get('word_count', 0)
            })
        
        df = pd.DataFrame(analytics_data)
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Document complexity radar chart
            fig = go.Figure()
            
            categories = ['Pages', 'Sections', 'Tables', 'References']
            for _, row in df.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[row['Pages'], row['Sections'], row['Tables'], row['References']],
                    theta=categories,
                    fill='toself',
                    name=row['Document'][:20]
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, max(df[categories].max())])
                ),
                showlegend=True,
                title="Document Complexity Analysis"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Word count distribution
            fig = px.box(df, y='Words', title='Word Count Distribution')
            st.plotly_chart(fig, use_container_width=True)
    
    # Performance insights
    st.markdown("### 🎯 Performance Insights")
    insights = []
    
    if st.session_state.processed_docs:
        avg_pages = sum(doc.get('total_pages', 0) for doc in st.session_state.processed_docs.values()) / len(st.session_state.processed_docs)
        insights.append(f"📄 Average document length: {avg_pages:.1f} pages")
    
    if st.session_state.chat_history:
        recent_queries = len([chat for chat in st.session_state.chat_history])
        insights.append(f"💬 Total queries processed: {recent_queries}")
    
    if st.session_state.arxiv_results:
        insights.append(f"🔍 ArXiv papers found: {len(st.session_state.arxiv_results)}")
    
    for insight in insights:
        st.info(insight)

# Additional utility functions
def export_chat_history():
    """Export chat history as JSON."""
    if st.session_state.chat_history:
        return json.dumps(st.session_state.chat_history, indent=2)
    return "{}"

def get_system_status():
    """Get system status information."""
    return {
        'agent_initialized': st.session_state.agent is not None,
        'documents_processed': len(st.session_state.processed_docs),
        'chat_messages': len(st.session_state.chat_history),
        'arxiv_results': len(st.session_state.arxiv_results)
    }

if __name__ == "__main__":
    main()