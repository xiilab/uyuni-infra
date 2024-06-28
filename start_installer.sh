#!/bin/bash

CURRENT_DIR=$(dirname "$(realpath "$0")")
$CURRENT_DIR/kubespray/setup-py.sh
dpkg -s sshpass &> /dev/null
if [ $? -ne 0 ]; then
  apt install -y sshpass
fi
python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate
pip install -r "$CURRENT_DIR/kubespray/requirements.txt"
python3.11 $CURRENT_DIR/install.py
