import curses
import os
import subprocess

import yaml


class NodeManager:
    def __init__(self, inventory_file):
        self.nodes = []
        self.inventory_file = inventory_file

        # Load nodes from inventory file if it exists
        if os.path.exists(self.inventory_file):
            with open(self.inventory_file, 'r') as f:
                inventory = yaml.safe_load(f)
                if inventory and 'all' in inventory and 'hosts' in inventory['all']:

                    for node_name, node_info in inventory['all']['hosts'].items():
                        print(inventory['all']['children']['kube-master']['hosts'].get(node_name))
                        print(node_info)
                        role = []
                        if node_name in inventory['all']['children']['kube-master']['hosts']:
                            role.append('kube-master')
                        if node_name in inventory['all']['children']['kube-node']['hosts']:
                            role.append('kube-node')
                        etcd = 'Y' if node_name in inventory['all']['children']['etcd']['hosts'] else 'N'
                        self.nodes.append({
                            'name': node_name,
                            'ip': node_info['ip'],
                            'role': ','.join(role),
                            'etcd': etcd
                        })

    def _save_to_file(self):
        inventory = {
            'all': {
                'children': {
                    'calico-rr': {'hosts': {}},
                    'etcd': {'hosts': {}},
                    'k8s-cluster': {
                        'children': {
                            'kube-master': {'hosts': {}},
                            'kube-node': {'hosts': {}}
                        }
                    },
                    'kube-master': {'hosts': {}},
                    'kube-node': {'hosts': {}}
                },
                'hosts': {}
            }
        }

        for node in self.nodes:
            inventory['all']['hosts'][node['name']] = {
                'ansible_host': node['ip'],
                'ip': node['ip'],
                'access_ip': node['ip']  # Assuming access_ip is the same as ip for simplicity
            }

            # Add node to appropriate group based on roles
            roles = node['role'].split(',')
            for role in roles:
                if role == 'kube-master':
                    inventory['all']['children']['kube-master']['hosts'][node['name']] = None
                elif role == 'kube-node':
                    inventory['all']['children']['kube-node']['hosts'][node['name']] = None

            # Add node to etcd group if applicable
            if node['etcd'] == 'Y':
                inventory['all']['children']['etcd']['hosts'][node['name']] = None

        with open(self.inventory_file, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)

    def add_node(self, name, ip, role, etcd):
        self.nodes.append({
            'name': name,
            'ip': ip,
            'role': role,
            'etcd': etcd
        })
        self._save_to_file()

    def remove_node(self, index):
        if 0 <= index < len(self.nodes):
            del self.nodes[index]
            self._save_to_file()

    def edit_node(self, index, name, ip, role, etcd):
        if 0 <= index < len(self.nodes):
            self.nodes[index]['name'] = name
            self.nodes[index]['ip'] = ip
            self.nodes[index]['role'] = role
            self.nodes[index]['etcd'] = etcd
            self._save_to_file()

    def list_nodes(self):
        return self.nodes

    def __str__(self):
        return yaml.dump(self.nodes, default_flow_style=False)


class CommandRunner:
    def read_and_display_output(self, process, stdscr):
        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                output_lines.append(output)
                if len(output_lines) > 255:
                    output_lines.pop(0)
                stdscr.clear()
                h, w = stdscr.getmaxyx()
                for idx, line in enumerate(output_lines[-h + 3:]):
                    stdscr.addstr(idx, 0, line[:w - 1])
                stdscr.refresh()

    def run_command(self, stdscr, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.read_and_display_output(process, stdscr)
        process.stdout.close()
        process.wait()
        stdscr.addstr(stdscr.getyx()[0] + 1, 0, "Press any key to return to the menu")
        stdscr.getch()


class AstragoInstaller:
    def __init__(self):
        self.node_manager = NodeManager('kubespray/inventory/mycluster/astrago.yaml')
        self.command_runner = CommandRunner()
        self.main_menu = ["1. Install Kubernetes", "2. Install Astrago", "3. Install NFS", "4. Close"]
        self.stdscr = None

    def print_banner(self):
        self.stdscr.clear()
        title = [
            "    ___         __                         ",
            "   /   |  _____/ /__________ _____ _____   ",
            "  / /| | / ___/ __/ ___/ __ `/ __ `/ __ \\ ",
            " / ___ |(__  ) /_/ /  / /_/ / /_/ / /_/ /  ",
            "/_/  |_/____/\\__/_/   \\__,_/\\__, /\\____/   ",
            "                           /____/          ",
        ]
        h, w = self.stdscr.getmaxyx()
        for idx, line in enumerate(title):
            x = w // 2 - len(line) // 2
            y = h // 2 - len(title) // 2 + idx - 10
            self.stdscr.addstr(y, x, line, curses.color_pair(2))
        self.stdscr.refresh()

    def print_menu(self, selected_row_idx):
        self.stdscr.clear()
        self.print_banner()
        h, w = self.stdscr.getmaxyx()

        for idx, row in enumerate(self.main_menu):
            x = w // 2 - len(row) // 2
            y = h // 2 - len(self.main_menu) // 2 + idx
            if idx == selected_row_idx:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y, x, row)
                self.stdscr.attroff(curses.color_pair(1))
            else:
                self.stdscr.addstr(y, x, row)

        self.stdscr.refresh()

    def print_nodes(self, selected_index=-1):
        x = 30
        y = 0

        header = ["   No   ", "     Node Name     ", "   IP Address   ", "          Role          ", " Etcd "]
        line_num = len(header[0]) + len(header[1]) + len(header[2]) + len(header[3]) + len(header[4]) + len(header) + 1
        line = ''.center(line_num, '-')

        self.stdscr.addstr(y, x, line)
        y += 1
        self.stdscr.addstr(y, x, "|" + "|".join(header) + "|")
        y += 1
        self.stdscr.addstr(y, x, line)

        for idx, row in enumerate(self.node_manager.nodes):
            new_row = [
                str(idx + 1).center(len(header[0])),
                row['name'].center(len(header[1])),
                row['ip'].center(len(header[2])),
                row['role'].center(len(header[3])),
                row['etcd'].center(len(header[4]))
            ]
            y += 1
            if selected_index == idx:
                self.stdscr.addstr(y, x, "|" + "|".join(new_row) + "|",
                                   curses.color_pair(1))
            else:
                self.stdscr.addstr(y, x, "|" + "|".join(new_row) + "|")
        y += 1
        self.stdscr.addstr(y, x, line)
        self.stdscr.refresh()

    def remove_node(self):
        selected_index = 0
        while True:
            self.stdscr.clear()
            self.print_nodes(selected_index)
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN and selected_index < len(self.node_manager.nodes) - 1:
                selected_index += 1
            elif key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break
            elif key == ord(' '):
                self.node_manager.remove_node(selected_index)
                selected_index -= 1

    def edit_node(self):
        selected_index = 0
        while True:
            self.stdscr.clear()
            self.print_nodes(selected_index)
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN and selected_index < len(self.node_manager.nodes) - 1:
                selected_index += 1
            elif key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break
            elif key == ord(' '):
                name, ip, role, etcd = self.add_node_query()
                self.node_manager.edit_node(selected_index, name, ip, role, etcd)
                selected_index -= 1

    def add_node_query(self):
        self.stdscr.clear()
        x = 0
        y = 0

        name = self.make_query(y + 0, x, "Node Name: ")
        ip = self.make_query(y + 1, x, "IP Address: ")
        role_options = ["kube-master", "kube-node"]
        etcd_options = ["Y", "N"]

        selected_roles = [False, False]
        etcd_idx = 0
        role_idx = 0

        while True:
            self.stdscr.addstr(y + 2, x, "Role: ")
            for idx, option in enumerate(role_options):
                if selected_roles[idx]:
                    self.stdscr.addstr(y + 2, x + 7 + idx * 10, "[X] " + option,
                                       curses.color_pair(2) if idx == role_idx else 0)
                else:
                    self.stdscr.addstr(y + 2, x + 7 + idx * 10, "[ ] " + option,
                                       curses.color_pair(2) if idx == role_idx else 0)

            key = self.stdscr.getch()

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
            self.stdscr.addstr(y + 3, x, f"Etcd: {etcd_options[etcd_idx]}")
            key = self.stdscr.getch()

            if key == curses.KEY_RIGHT:
                etcd_idx = (etcd_idx + 1) % len(etcd_options)
            elif key == curses.KEY_LEFT:
                etcd_idx = (etcd_idx - 1) % len(etcd_options)
            elif key in [10, 13]:  # Enter key
                break

        role = ",".join([role_options[i] for i in range(len(role_options)) if selected_roles[i]])
        return name, ip, role, etcd_options[etcd_idx]


    def add_node(self):
        name, ip, role, etcd = self.add_node_query()
        self.node_manager.add_node(name, ip, role, etcd)


    def print_sub_menu(self, selected_row_idx, menu):
        self.stdscr.clear()
        for idx, row in enumerate(menu):
            first_menu_x = 0
            first_menu_y = idx
            if idx == selected_row_idx:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(first_menu_y, first_menu_x, row)
                self.stdscr.attroff(curses.color_pair(1))
            else:
                self.stdscr.addstr(first_menu_y, first_menu_x, row)
        self.stdscr.refresh()

    def install_kubernetes_menu(self):
        self.stdscr.clear()
        current_row = 0
        menu = ["1. Add Node", "2. Remove Node", "3. Edit Node", "4. Install Kubernetes", "5. Back"]
        while True:
            self.print_sub_menu(current_row, menu)
            self.print_nodes()
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.add_node()
                elif current_row == 1:
                    self.remove_node()
                elif current_row == 2:
                    self.edit_node()
                elif current_row == 3:
                    self.stdscr.clear()
                    self.stdscr.addstr(0, 0, "Installing Kubernetes...")
                    self.stdscr.addstr(1, 0, "Input Node's Password: ")
                    password = self.stdscr.getstr(1, 23, 20).decode('utf-8')
                    self.command_runner.run_command(self.stdscr, ["bash", "kubespray/deploy-kubespray.sh", password])
                    return
                elif current_row == 4:
                    return

    def make_query(self, y, x, query):
        self.stdscr.addstr(y, x, query)
        return self.stdscr.getstr(y, x + len(query), 20).decode('utf-8')

    def install_astrago(self):
        self.stdscr.clear()
        x = 0
        y = 0

        connected_url = self.make_query(y + 0, x, "Connected Url: ")
        nfs_server_ip = self.make_query(y + 1, x, "Enter the NFS Server IP Address: ")
        nfs_base_path = self.make_query(y + 2, x, "Enter the base path of NFS: ")

        with open('environments/prod/values.yaml') as f:
            helmfile_env = yaml.load(f, Loader=yaml.FullLoader)
            helmfile_env['externalIP'] = connected_url
            helmfile_env['nfs']['enabled'] = True
            helmfile_env['nfs']['server'] = nfs_server_ip
            helmfile_env['nfs']['basePath'] = nfs_base_path

        os.makedirs('environments/astrago', exist_ok=True)
        with open('environments/astrago/values.yaml', 'w') as file:
            yaml.dump(helmfile_env, file, default_flow_style=False, sort_keys=False)

        self.command_runner.run_command(self.stdscr, ["bash", "deploy_astrago.sh", "sync"])

    def install_nfs(self):
        self.command_runner.run_command(self.stdscr, ["ls", "-al"])

    def main(self, stdscr):
        self.stdscr = stdscr
        curses.echo()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        current_row = 0

        self.print_menu(current_row)

        while True:
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(self.main_menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.install_kubernetes_menu()
                elif current_row == 1:
                    self.install_astrago()
                elif current_row == 2:
                    self.install_nfs()
                elif current_row == 3:
                    break  # Exit the program

                self.stdscr.clear()
                self.print_menu(current_row)
                continue

            self.print_menu(current_row)


if __name__ == "__main__":
    installer = AstragoInstaller()
    curses.wrapper(installer.main)
# if __name__ == "__main__":
#     # Initialize NodeManager with the inventory file path
#     manager = NodeManager('inventory.yaml')
#
#     # Print nodes initially loaded from the inventory file
#     print("Nodes from inventory file:")
#     print(manager)
#
#     # Add nodes (example)
#     manager.add_node('node4', '192.168.56.14', 'kube-node', 'Y')
#     manager.add_node('node5', '192.168.56.15', 'kube-master,kube-node', 'N')
#
#     # Print nodes after adding
#     print("Nodes after adding:")
#     print(manager)
#
#     # Remove a node (example)
#     manager.remove_node(0)
#     print("Nodes after removing:")
#     print(manager)
#
#     # Edit a node (example)
#     manager.edit_node(0, 'node1', '10.0.0.1', 'kube-master', 'Y')
#     print("Nodes after editing:")
#     print(manager)
