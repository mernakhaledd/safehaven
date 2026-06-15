#!/bin/bash
# install_python310.sh
# This script installs Python 3.10 on Raspberry Pi 5 automatically.

echo "Starting Python 3.10 Installation..."
echo "update system..."
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

echo "download python..."
cd ~
wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz
tar -xf Python-3.10.13.tgz
cd Python-3.10.13

echo "configure..."
./configure --enable-optimizations

echo "compile (this takes ~15 mins)..."
make -j4
sudo make altinstall

echo "Done! Verifying..."
python3.10 --version
