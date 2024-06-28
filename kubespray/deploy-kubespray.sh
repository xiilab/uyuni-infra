#!/bin/bash

if [ -z "$1" ]; then
    read -s -p "Enter Ansible password: " password
else
    password="$1"
fi

CURRENT_DIR=$(dirname "$(realpath "$0")")
echo "$CURRENT_DIR"
cd "$CURRENT_DIR"
./setup-py.sh

apt install -y sshpass
python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate

pip install -r "$CURRENT_DIR/requirements.txt"

ansible-playbook -i inventory/mycluster/astrago.yaml --become --become-user=root cluster.yml --extra-vars="ansible_password=$password"

