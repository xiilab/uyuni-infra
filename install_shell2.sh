#!/bin/bash

nodes=()

function print_main_menu {
    clear
    echo "1. Install Kubernetes"
    echo "2. Install Astrago"
    echo "3. Install NFS"
    echo "4. Cancel"
}

function print_nodes {
    echo "-----------------------------------------------"
    printf "| %-5s | %-15s | %-15s | %-5s |\n" "No" "Node Name" "IP Address" "Role"
    echo "-----------------------------------------------"
    for i in "${!nodes[@]}"; do
        IFS=" " read -r name ip role <<< "${nodes[$i]}"
        printf "| %-5s | %-15s | %-15s | %-5s |\n" "$i" "$name" "$ip" "$role"
    done
    echo "-----------------------------------------------"
}

function add_node {
    read -p "Node Name: " name
    read -p "IP Address: " ip
    read -p "Role: " role
    nodes+=("$name $ip $role")
}

function setting_node_menu {
    while true; do
        clear
        echo "Node Settings"
        echo "1. Add Node"
        echo "2. Remove Node"
        echo "3. Edit Node"
        echo "4. Cancel"
        print_nodes
        read -p "Choose an option: " choice

        case $choice in
            1)
                add_node
                ;;
            2)
                read -p "Enter node number to remove: " num
                unset nodes[$num]
                nodes=("${nodes[@]}")  # Reindex array
                ;;
            3)
                read -p "Enter node number to edit: " num
                read -p "New Node Name: " name
                read -p "New IP Address: " ip
                read -p "New Role: " role
                nodes[$num]="$name $ip $role"
                ;;
            4)
                break
                ;;
            *)
                echo "Invalid option"
                ;;
        esac
    done
}

function install_kubernetes_menu {
    while true; do
        clear
        echo "Kubernetes Installation"
        echo "1. Setting Node"
        echo "2. Install Kubernetes"
        echo "3. Cancel"
        print_nodes
        read -p "Choose an option: " choice

        case $choice in
            1)
                setting_node_menu
                ;;
            2)
                clear
                echo "Installing Kubernetes..."
                sh kubespray/deploy-kubespray.sh
                #read -p "Press any key to return to the menu..."
                ;;
            3)
                break
                ;;
            *)
                echo "Invalid option"
                ;;
        esac
    done
}

function install_astrago {
    echo "Installing Astrago..."
    # 실제 설치 명령을 여기에 추가
}

function install_nfs {
    echo "Installing NFS..."
    # 실제 설치 명령을 여기에 추가
}

while true; do
    print_main_menu
    read -p "Choose an option: " choice

    case $choice in
        1)
            install_kubernetes_menu
            ;;
        2)
            install_astrago
            ;;
        3)
            install_nfs
            ;;
        4)
            echo "Exiting..."
            break
            ;;
        *)
            echo "Invalid option"
            ;;
    esac
done

