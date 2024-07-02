#!/bin/bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export LANGUAGE=C.UTF-8

CURRENT_DIR=$(dirname "$(realpath "$0")")

. /etc/os-release

IS_OFFLINE=${IS_OFFLINE:-false}

dpkg -s python3.11 &> /dev/null
if [ $? -eq 0 ]; then
    echo "Python 3.11 is already installed."
else
    # Install python and dependencies
    echo "===> Install python, venv, etc"
    if [ -e /etc/redhat-release ]; then
        # RHEL
        DNF_OPTS=
        if [[ $IS_OFFLINE = "true" ]]; then
            DNF_OPTS="--disablerepo=* --enablerepo=offline-repo"
        fi
        #sudo dnf install -y $DNF_OPTS gcc libffi-devel openssl-devel || exit 1

        if [[ "$VERSION_ID" =~ ^7.* ]]; then
            echo "FATAL: RHEL/CentOS 7 is not supported anymore."
            exit 1
        #elif [[ "$VERSION_ID" =~ ^8.* ]]; then
        #elif [[ "$VERSION_ID" =~ ^9.* ]]; then
        #else
        fi
        sudo dnf install -y $DNF_OPTS python3.11 || exit 1
        #sudo dnf install -y $DNF_OPTS python3.11-devel || exit 1
    else
        # Ubuntu
        sudo apt update
        PY=3.11
        case "$VERSION_ID" in
            20.04)
                if [ "${IS_OFFLINE}" = "false" ]; then
                    # Prepare for latest python3
                    sudo apt install -y software-properties-common
                    sudo add-apt-repository ppa:deadsnakes/ppa -y || exit 1
                    sudo apt update
                fi
                ;;
            24.04)
                PY=3.12
                ;;
        esac
        #sudo apt install -y python${PY}-dev gcc libffi-dev libssl-dev || exit 1
        sudo apt install -y python${PY}-venv || exit 1
    fi
fi

# Install sshpass if not already installed
if ! command -v sshpass &> /dev/null; then
    echo "===> Install sshpass"
    if [ -e /etc/redhat-release ]; then
        sudo dnf install -y sshpass || exit 1
    else
        sudo apt install -y sshpass || exit 1
    fi
else
    echo "sshpass is already installed."
fi

python3.11 -m venv ~/.venv/3.11
source ~/.venv/3.11/bin/activate
pip install -r "$CURRENT_DIR/kubespray/requirements.txt"
python3.11 $CURRENT_DIR/astrago_gui_installer.py
