#!/bin/bash
# Setup script for FCIM AI Chatbot

set -e

echo "🚀 FCIM AI Chatbot Setup"
echo "========================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10+ required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version"

# Check Docker
echo ""
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    exit 1
fi
echo "✅ Docker $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found"
    exit 1
fi
echo "✅ Docker Compose $(docker-compose --version)"

# Check NVIDIA Docker
echo ""
echo "Checking NVIDIA Docker..."
if ! docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo "⚠️  NVIDIA Docker not working (GPU required for LLM)"
    echo "   Install nvidia-docker2: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
fi

# Create .env if not exists
echo ""
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Created .env (please configure it)"
    echo "⚠️  Update JWT_SECRET_KEY and other settings in .env"
else
    echo "✅ .env already exists"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi

# Activate and install dependencies
echo ""
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Create directories
echo ""
echo "Creating directories..."
mkdir -p data/{raw,processed,embeddings,qdrant_storage,redis_data,prometheus_data,grafana_data}
mkdir -p logs
mkdir -p models
echo "✅ Directories created"

# Initialize Qdrant (if running)
echo ""
echo "Setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Update .env with your configuration"
echo "2. Download models: python scripts/setup/download_models.py"
echo "3. Start services: docker-compose up -d"
echo "4. Initialize database: python scripts/setup/init_db.py"
echo "5. Ingest courses: python scripts/ingestion/ingest_courses.py --all"
echo "6. Test API: curl http://localhost:8000/health"
echo ""
echo "📚 Documentation: README.md"
echo "🐛 Issues: https://github.com/fcim-utm/ai-chatbot/issues"
