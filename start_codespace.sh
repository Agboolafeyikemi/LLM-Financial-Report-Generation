#!/bin/bash
# Startup script for GitHub Codespace
# This script automates the setup process

set -e

echo "🚀 Setting up LLM Financial Report Generator in Codespace..."

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama is already installed"
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "🔧 Starting Ollama server..."
    ollama serve &
    sleep 3  # Wait for Ollama to start
else
    echo "✅ Ollama server is already running"
fi

# Check if model is available
if ! ollama list | grep -q "deepseek-r1:1.5b"; then
    echo "📥 Pulling deepseek-r1:1.5b model (this may take a few minutes)..."
    ollama pull deepseek-r1:1.5b
else
    echo "✅ Model deepseek-r1:1.5b is already available"
fi

# Install Python dependencies if needed
if [ ! -d ".venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Installing Python dependencies..."
source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the app:"
echo "  Option 1 (with Ollama): streamlit run streamlit_app.py --server.port 8501"
echo "  Option 2 (demo mode):   DEMO_MODE=true streamlit run streamlit_app.py --server.port 8501"
echo ""
echo "Note: In Codespaces, LLM inference may be slow (CPU-only)."
echo "      Use DEMO_MODE=true for faster testing."
