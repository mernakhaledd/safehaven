#!/bin/bash

# Complete Setup Script for Help Gesture Detection
# This script automates the entire setup process

echo "=============================================="
echo "Help Gesture Detection - Complete Setup"
echo "=============================================="
echo ""

# Check Python version
echo "[1/6] Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed!"
    exit 1
fi
echo "✓ Python 3 found"
echo ""

# Create virtual environment
echo "[2/6] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "[3/6] Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "[4/6] Upgrading pip..."
pip install --upgrade pip
echo "✓ Pip upgraded"
echo ""

# Install dependencies
echo "[5/6] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies!"
    exit 1
fi
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "[6/6] Creating project directories..."
mkdir -p dataset
mkdir -p models
mkdir -p snapshots
echo "✓ Directories created"
echo ""

echo "=============================================="
echo "Setup Complete! ✓"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Collect training data: python 1_data_collection.py"
echo "3. Train the model: python 2_train_model.py"
echo "4. Test on laptop: python 3_test_realtime.py"
echo "5. Deploy to Raspberry Pi: python 4_raspberry_pi_deploy.py"
echo ""
echo "For detailed instructions, see README.md"
echo "=============================================="