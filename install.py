import curses
import os
import subprocess

import yaml

nodes = []

main_menu = ["1. Install Kubernetes", "2. Install Astrago", "3. Install NFS", "4. Close"]


def print_menu(stdscr, selected_row_idx):
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    for idx, row in enumerate(main_menu):
        x = w // 2 - len(row) // 2
        y = h // 2 - len(main_menu) // 2 + idx
        if idx == selected_row_idx:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(y, x, row)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y, x, row)

    stdscr.refresh()


def print_nodes(stdscr):
    x = 30
    y = 0

    header = ["   No   ", "     Node Name     ", "   IP Address   ", "   Role   ", " Etcd "]
    line_num = len(header[0]) + len(header[1]) + len(header[2]) + len(header[3]) + len(header[4]) + len(header) + 1
    line = ''.center(line_num, '-')

    stdscr.addstr(y, x, line)
    y += 1
    stdscr.addstr(y, x, "|" + "|".join(header) + "|")
    y += 1
    stdscr.addstr(y, x, line)

    for idx, row in enumerate(nodes):
        new_row = [
            str(idx).center(len(header[0])),
            row[0].center(len(header[1])),
            row[1].center(len(header[2])),
            row[2].center(len(header[3])),
            row[3].center(len(header[4]))
        ]
        y += 1
        stdscr.addstr(y, x, "|" + "|".join(new_row) + "|")
    y += 1
    stdscr.addstr(y, x, line)


def add_node(stdscr):
    curses.echo()
    h, w = stdscr.getmaxyx()
    x = w // 2
    y = h // 2

    stdscr.addstr(y + 0, x, "Node Name: ")
    name = stdscr.getstr(y + 0, x + 11, 20).decode('utf-8')

    stdscr.addstr(y + 1, x, "IP Address: ")
    ip = stdscr.getstr(y + 1, x + 12, 20).decode('utf-8')

    role_options = ["Master", "Worker"]
    etcd_options = ["Y", "N"]

    selected_roles = [False, False]
    etcd_idx = 0
    role_idx = 0

    while True:
        stdscr.addstr(y + 2, x, "Role: ")
        for idx, option in enumerate(role_options):
            if selected_roles[idx]:
                stdscr.addstr(y + 2, x + 7 + idx * 10, "[X] " + option, curses.color_pair(2) if idx == role_idx else 0)
            else:
                stdscr.addstr(y + 2, x + 7 + idx * 10, "[ ] " + option, curses.color_pair(2) if idx == role_idx else 0)

        key = stdscr.getch()

        if key == curses.KEY_RIGHT:
            role_idx = (role_idx + 1) % len(role_options)
        elif key == curses.KEY_LEFT:
            role_idx = (role_idx - 1) % len(role_options)
        elif key == ord(' '):
            selected_roles[role_idx] = not selected_roles[role_idx]
            if not any(selected_roles):
                selected_roles[role_idx] = True  # Ensure at least one is selected
        elif key in [10, 13]:  # Enter key
            if any(selected_roles):
                break

    while True:
        stdscr.addstr(y + 3, x, f"Etcd: {etcd_options[etcd_idx]}".ljust(w - x), curses.color_pair(2))
        key = stdscr.getch()

        if key == curses.KEY_RIGHT:
            etcd_idx = (etcd_idx + 1) % len(etcd_options)
        elif key == curses.KEY_LEFT:
            etcd_idx = (etcd_idx - 1) % len(etcd_options)
        elif key in [10, 13]:  # Enter key
            break

    role = ",".join([role_options[i] for i in range(len(role_options)) if selected_roles[i]])
    nodes.append([name, ip, role, etcd_options[etcd_idx]])


def print_sub_menu(stdscr, selected_row_idx, menu):
    stdscr.clear()
    for idx, row in enumerate(menu):
        first_menu_x = 0
        first_menu_y = idx
        if idx == selected_row_idx:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(first_menu_y, first_menu_x, row)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(first_menu_y, first_menu_x, row)


def setting_node_menu(stdscr):
    current_row = 0
    menu = ["1. Add Node", "2. Remove Node", "3. Edit Node", "4. Back"]
    while True:
        print_sub_menu(stdscr, current_row, menu)
        print_nodes(stdscr)
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0:
                add_node(stdscr)
            elif current_row == 1:
                return
            elif current_row == 2:
                return
            elif current_row == 3:
                return


def read_and_display_output(process, stdscr):
    h, w = stdscr.getmaxyx()
    output_lines = []
    while process.poll() is None:
        output = process.stdout.readline()
        if output:
            output_lines.append(output.decode('utf-8'))
            if len(output_lines) > 255:
                output_lines.pop(0)
            stdscr.clear()
            h, w = stdscr.getmaxyx()            
            for idx, line in enumerate(output_lines[-h+3:]):
                stdscr.addstr(idx, 0, line[:w-1])
            stdscr.refresh()


def create_inventory_file():
    inventory = {
        'all': {
            'hosts': {},
            'children': {
                'kube-master': {
                    'hosts': {}
                },
                'kube-node': {
                    'hosts': {}
                },
                'etcd': {
                    'hosts': {}
                },
                'k8s-cluster': {
                    'children': {
                        'kube-master': None,
                        'kube-node': None
                    }
                },
                'calico-rr': {
                    'hosts': {}
                }
            }
        }
    }

    for node in nodes:
        node_name, ip, role, etcd = node
        host_info = {
            'ansible_host': ip,
            'ip': ip,
            'access_ip': ip
        }
        inventory['all']['hosts'][node_name] = host_info
        if 'Master' in role:
            inventory['all']['children']['kube-master']['hosts'][node_name] = None
        if 'Worker' in role:
            inventory['all']['children']['kube-node']['hosts'][node_name] = None
        if etcd == 'Y':
            inventory['all']['children']['etcd']['hosts'][node_name] = None

    os.makedirs('kubespray/inventory/mycluster', exist_ok=True)
    with open('kubespray/inventory/mycluster/astrago.yaml', 'w') as file:
        yaml.dump(inventory, file, default_flow_style=False)


def install_kubernetes_menu(stdscr):
    stdscr.clear()
    current_row = 0
    menu = ["1. Setting Node", "2. Install Kubernetes", "3. Back"]
    while True:
        print_sub_menu(stdscr, current_row, menu)
        print_nodes(stdscr)
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0:
                setting_node_menu(stdscr)
            elif current_row == 1:
                create_inventory_file()
                stdscr.clear()
                stdscr.addstr(0, 0, "Installing Kubernetes...")
                stdscr.addstr(1, 0, "Input Node's Password: ")
                password = stdscr.getstr(1, 23, 20).decode('utf-8')
                

                # Popen으로 실시간 출력
                process = subprocess.Popen(["bash", "kubespray/deploy-kubespray.sh", password], stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           executable="/bin/bash")
                read_and_display_output(process, stdscr)
                process.stdout.close()
                process.wait()
                stdscr.addstr(stdscr.getyx()[0] + 1, 0, "Press any key to return to the menu")
                stdscr.getch()
                return
            elif current_row == 2:
                return


def install_astrago():
    subprocess.run(["echo", "Installing Astrago..."])
    # 실제 설치 명령을 여기에 추가


def install_nfs():
    subprocess.run(["echo", "Installing NFS..."])
    # 실제 설치 명령을 여기에 추가
    # subprocess.run(["sudo", "apt-get", "install", "-y", "nfs-kernel-server"])


def main(stdscr):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_WHITE)
    current_row = 0

    print_menu(stdscr, current_row)

    while True:
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(main_menu) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0:
                install_kubernetes_menu(stdscr)
            elif current_row == 1:
                install_astrago()
            elif current_row == 2:
                install_nfs()
            elif current_row == 3:
                break  # Exit the program

            stdscr.clear()
            print_menu(stdscr, current_row)
            continue

        print_menu(stdscr, current_row)


curses.wrapper(main)

