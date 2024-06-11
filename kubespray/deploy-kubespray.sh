CURRENT_DIR=$(dirname "$(realpath "$0")")

apt install -y sshpass
python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate

pip install -r $CURRENT_DIR/requirements.txt

echo -n "Enter password: "
read -s password
echo "$password" > ~/.vault_pass.txt
chmod 600 ~/.vault_pass.txt
ansible-vault encrypt ~/.vault_pass.txt

ansible-playbook -i inventory/offline/astrago.yaml --ask-vault-pass=~/.vault_pass.txt offline-repo.yml
ansible-playbook -i inventory/offline/astrago.yaml  --become --become-user=root --ask-vault-pass=~/.vault_pass.txt cluster.yml

