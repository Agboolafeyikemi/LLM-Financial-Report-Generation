"""
Streamlit Web UI for LLM Financial Report Generator

This is the web-based interface for the financial report generation system.
It provides a user-friendly way to upload Excel files, configure LLM settings,
and generate comprehensive financial reports with AI-powered insights.
"""

import streamlit as st
import os
import tempfile
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from analysis.report_generation import generate_report
from md_to_word import convert_md_to_docx

# Page configuration
st.set_page_config(
    page_title="LLM Financial Report Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stProgress > div > div > div {
        background-color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = None
if 'report_md' not in st.session_state:
    st.session_state.report_md = None


def check_ollama_connection():
    """Check if Ollama is running"""
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def check_provider_available(provider: str) -> bool:
    """Check if the selected LLM provider is available and configured"""
    if provider == "demo":
        return True  # Demo mode always available
    elif provider == "openai":
        return os.getenv("OPENAI_API_KEY") is not None
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY") is not None
    elif provider == "ollama":
        return check_ollama_connection()
    return False


def main():
    # Header
    st.markdown('<div class="main-header">📊 LLM Financial Report Generator</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model selection
        model_options = {
            "phi4:latest": "Best results (16 GB GPU RAM)",
            "gemma3:12b": "Good results (12 GB GPU RAM)",
            "deepseek-r1:1.5b": "Basic results (3 GB GPU RAM)"
        }
        
        selected_model = st.selectbox(
            "LLM Model",
            options=list(model_options.keys()),
            index=0,
            help="Select the LLM model to use for report generation"
        )
        st.caption(model_options[selected_model])
        
        # Temperature setting
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.1,
            help="Controls randomness in LLM responses. Lower = more deterministic"
        )
        
        # Max tokens
        max_tokens = st.slider(
            "Max Tokens",
            min_value=512,
            max_value=4096,
            value=2048,
            step=256,
            help="Maximum length of LLM response"
        )
        
        st.markdown("---")
        
        # LLM Provider selection
        st.subheader("🤖 LLM Provider")
        
        # Get default provider from env or use ollama
        default_provider = os.getenv("LLM_PROVIDER", "ollama")
        provider_options = ["openai", "anthropic", "ollama", "demo"]
        default_index = provider_options.index(default_provider) if default_provider in provider_options else 2
        
        provider = st.selectbox(
            "Select LLM Provider",
            options=provider_options,
            index=default_index,
            help="Choose your LLM provider. OpenAI/Anthropic require API keys."
        )
        
        # Set provider in environment for this session
        os.environ["LLM_PROVIDER"] = provider
        
        # Provider-specific status and instructions
        st.subheader("🔌 Connection Status")
        provider_available = check_provider_available(provider)
        
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                st.success("✅ OpenAI API key configured")
            else:
                st.error("❌ OPENAI_API_KEY not set")
                st.info("Add it to your `.env` file:\n```\nOPENAI_API_KEY=sk-...\nLLM_PROVIDER=openai\n```")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                st.success("✅ Anthropic API key configured")
            else:
                st.error("❌ ANTHROPIC_API_KEY not set")
                st.info("Add it to your `.env` file:\n```\nANTHROPIC_API_KEY=sk-ant-...\nLLM_PROVIDER=anthropic\n```")
        elif provider == "ollama":
            if check_ollama_connection():
                st.success("✅ Ollama is running")
            else:
                st.error("❌ Ollama is not running")
                st.info("Start Ollama:\n```bash\nollama serve\n```")
        else:  # demo
            st.success("✅ Demo mode - no API needed")
            st.info("Using pre-generated responses for testing")
        
        st.markdown("---")
        st.markdown("### 📖 About")
        st.markdown("""
        This application uses LLMs to automatically generate 
        comprehensive financial reports from Excel data.
        
        **Features:**
        - 📈 Data analysis
        - 🤖 AI-powered insights
        - 📊 Visualizations
        - 📄 Word document export
        
        **LLM Providers:**
        - **OpenAI**: Cloud API (requires API key)
        - **Anthropic**: Claude API (requires API key)
        - **Ollama**: Local LLM (free, requires installation)
        - **Demo**: Pre-generated responses (no setup needed)
        """)


    # Main content area
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Generate", "📊 Results", "📄 Report"])

    with tab1:
        st.header("Upload Excel File")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            help="Upload your financial data in Excel format"
        )
        
        # Or use sample data
        use_sample = st.checkbox("Use sample data (1k_lines_sales_data.xlsx)", value=False)
        
        if use_sample and os.path.exists('./1k_lines_sales_data.xlsx'):
            file_path = './1k_lines_sales_data.xlsx'
            st.info("Using sample data file")
        elif uploaded_file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                file_path = tmp_file.name
            st.success(f"File uploaded: {uploaded_file.name}")
        else:
            file_path = None
            st.info("👆 Please upload an Excel file or use sample data")
        
        # Preview uploaded data
        if file_path and os.path.exists(file_path):
            try:
                df_preview = pd.read_excel(file_path, nrows=5)
                with st.expander("📋 Preview Data (first 5 rows)"):
                    st.dataframe(df_preview)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        # Generate button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Check if provider is available
            provider_available = check_provider_available(provider)
            
            generate_button = st.button(
                "🚀 Generate Report",
                type="primary",
                use_container_width=True,
                disabled=(file_path is None or not provider_available)
            )
            
            # Show helpful message if button is disabled
            if file_path is None:
                st.info("👆 Please upload an Excel file or use sample data to enable report generation.")
            elif not provider_available:
                if provider == "openai":
                    st.warning("⚠️ OpenAI API key not found. Set OPENAI_API_KEY in your .env file or environment.")
                elif provider == "anthropic":
                    st.warning("⚠️ Anthropic API key not found. Set ANTHROPIC_API_KEY in your .env file or environment.")
                elif provider == "ollama":
                    st.warning("⚠️ Ollama is not running. Start it with 'ollama serve' or switch to a different provider.")
        
        if generate_button and file_path:
            # Create output directory
            output_dir = "./output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Data processing
                status_text.text("📊 Processing data...")
                progress_bar.progress(20)
                
                # Step 2: Generate report
                status_text.text("🤖 Generating report with LLM...")
                progress_bar.progress(40)
                
                report_md = generate_report(file_path, output_dir, selected_model, temperature, max_tokens)
                print(report_md)
                print(type(report_md), 'TEST')
                print("--------------------------------")
                # print(report_md is None)
                # print(type(report_md is None))
                # print("--------------------------------")
                # print(report_md is not None)
                # print(type(report_md is not None))
                # print("--------------------------------")
                # print(report_md is not None)
                # print(type(report_md is not None))
                # print("--------------------------------")
                # print(report_md is not None)
                # print(type(report_md is not None))
                # print("--------------------------------")
                # print(report_md is not None)
                # print(type(report_md is not None))
                # print("--------------------------------")

                if report_md:
                    progress_bar.progress(70)
                    status_text.text("📝 Converting to Word document...")
                    
                    # Save markdown report
                    md_report = os.path.join(output_dir, "executive_report.md")
                    with open(md_report, 'w') as f:
                        f.write(report_md)
                    
                    # Convert to Word
                    if convert_md_to_docx(md_report, output_dir):
                        progress_bar.progress(100)
                        status_text.text("✅ Report generated successfully!")
                        
                        # Update session state
                        st.session_state.report_generated = True
                        st.session_state.output_dir = output_dir
                        st.session_state.report_md = report_md
                        
                        st.success("🎉 Report generation complete!")
                        st.balloons()
                        
                        # Auto-switch to Results tab
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Report generation completed but Word conversion failed")
                else:
                    st.error("❌ Report generation failed. Please check the logs and ensure Ollama is running.")
                    progress_bar.empty()
                    status_text.empty()
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                progress_bar.empty()
                status_text.empty()
                st.exception(e)

    with tab2:
        st.header("📊 Analysis Results")
        
        if st.session_state.report_generated and st.session_state.output_dir:
            output_dir = st.session_state.output_dir
            
            # Display visualizations
            viz_dir = os.path.join(output_dir, "visualizations")
            
            if os.path.exists(viz_dir):
                st.subheader("📈 Visualizations")
                
                # Annual Revenue
                annual_rev_path = os.path.join(viz_dir, "annual_revenue.png")
                if os.path.exists(annual_rev_path):
                    st.markdown("### Annual Revenue by Property")
                    st.image(annual_rev_path, use_container_width=True)
                
                # Top Tenants
                st.markdown("### Top Tenants by Property")
                tenant_files = [f for f in os.listdir(viz_dir) if f.startswith("top_tenants_")]
                if tenant_files:
                    cols = st.columns(min(2, len(tenant_files)))
                    for idx, filename in enumerate(tenant_files):
                        with cols[idx % len(cols)]:
                            prop_name = filename.replace("top_tenants_", "").replace(".png", "").replace("_", " ")
                            st.image(os.path.join(viz_dir, filename), caption=prop_name, use_container_width=True)
                
                # Revenue Changes
                st.markdown("### Revenue Changes Analysis")
                change_files = [f for f in os.listdir(viz_dir) if f.startswith("top10_changes_")]
                if change_files:
                    cols = st.columns(min(2, len(change_files)))
                    for idx, filename in enumerate(change_files):
                        with cols[idx % len(cols)]:
                            st.image(os.path.join(viz_dir, filename), caption=filename.replace(".png", ""), use_container_width=True)
                
                # Analysis Results Excel
                excel_path = os.path.join(output_dir, "analysis_results.xlsx")
                if os.path.exists(excel_path):
                    st.markdown("---")
                    st.subheader("📊 Analysis Data")
                    with open(excel_path, "rb") as f:
                        st.download_button(
                            label="📥 Download Analysis Results (Excel)",
                            data=f.read(),
                            file_name="analysis_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            else:
                st.info("No visualizations found. Please generate a report first.")
        else:
            st.info("👈 Please generate a report first using the 'Upload & Generate' tab")

    with tab3:
        st.header("📄 Generated Report")
        
        if st.session_state.report_generated and st.session_state.report_md:
            # Display markdown report
            st.markdown(st.session_state.report_md)
            
            st.markdown("---")
            
            # Download buttons
            col1, col2 = st.columns(2)
            
            with col1:
                # Download Markdown
                md_path = os.path.join(st.session_state.output_dir, "executive_report.md")
                if os.path.exists(md_path):
                    with open(md_path, "r") as f:
                        st.download_button(
                            label="📥 Download Markdown Report",
                            data=f.read(),
                            file_name="executive_report.md",
                            mime="text/markdown"
                        )
            
            with col2:
                # Download Word Document
                docx_path = os.path.join(st.session_state.output_dir, "executive_report.docx")
                if os.path.exists(docx_path):
                    with open(docx_path, "rb") as f:
                        st.download_button(
                            label="📥 Download Word Document",
                            data=f.read(),
                            file_name="executive_report.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
        else:
            st.info("👈 Please generate a report first using the 'Upload & Generate' tab")


if __name__ == "__main__":
    main()
