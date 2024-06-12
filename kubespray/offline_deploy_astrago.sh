CURRENT_DIR=$(dirname "$(realpath "$0")")

echo -n "Enter Node's root password: "
read -s password

apt install -y sshpass
python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate

pip install -r $CURRENT_DIR/requirements.txt

ansible-playbook -i inventory/offline/astrago.yaml --become --become-user=root offline-repo.yml --extra-vars="ansible_password=$password"
ansible-playbook -i inventory/offline/astrago.yaml  --become --become-user=root cluster.yml --extra-vars="ansible_password=$password"
