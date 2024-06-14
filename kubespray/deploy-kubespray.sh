CURRENT_DIR=$(dirname "$(realpath "$0")")
echo "$CURRENT_DIR"
#echo -n "Enter Node's root password: "
#read -s password

$CURRENT_DIR/setup-py.sh

apt install -y sshpass
python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate

pip install -r $CURRENT_DIR/requirements.txt

ansible-playbook -i $CURRENT_DIR/inventory/mycluster/astrago.yaml  --become --become-user=root $CURRENT_DIR/cluster.yml --extra-vars="ansible_password=$password"

