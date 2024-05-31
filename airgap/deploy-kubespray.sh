CURRENT_DIR=$(dirname "$(realpath "$0")")
KUBESPRAY_DIR=$CURRENT_DIR/../kubespray

# Example
python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate
cd $KUBESPRAY_DIR
pip install -r $KUBESPRAY_DIR/requirements.txt
ansible-playbook -i inventory/offline/astrago.yaml offline-repo.yml
ansible-playbook -i inventory/offline/astrago.yaml  --become --become-user=root cluster.yml

