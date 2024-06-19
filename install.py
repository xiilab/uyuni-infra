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
        max_lines = stdscr.getmaxyx()[0] - 2  # Leave space for the "Press any key" message

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                output_lines.append(output.strip())
                if len(output_lines) > max_lines:
                    output_lines.pop(0)

                stdscr.erase()  # Use erase instead of clear to avoid full screen flicker
                _, w = stdscr.getmaxyx()
                for idx, line in enumerate(output_lines):
                    stdscr.addstr(idx, 0, line[:w - 1])
                stdscr.refresh()

        # Display the "Press any key to return to the menu" message
        if len(output_lines) < max_lines:
            stdscr.addstr(len(output_lines) + 1, 0, "Press any key to return to the menu")
        else:
            stdscr.addstr(max_lines, 0, "Press any key to return to the menu")
        stdscr.refresh()
        stdscr.getch()

    def run_command(self, stdscr, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.read_and_display_output(process, stdscr)
        process.stdout.close()
        process.wait()


class AstragoInstaller:
    def __init__(self):
        self.node_manager = NodeManager('kubespray/inventory/mycluster/astrago.yaml')
        self.command_runner = CommandRunner()
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
            if len(line) > w:
                line = line[:w - 1]
            x = w // 2 - len(line) // 2
            y = h // 2 - len(title) // 2 + idx - 10
            if y < h and x + len(line) < w:
                self.stdscr.addstr(y, x, line, curses.color_pair(2))
        self.stdscr.refresh()

    def print_menu(self, menu, selected_row_idx):
        self.stdscr.clear()
        self.print_banner()
        h, w = self.stdscr.getmaxyx()

        for idx, row in enumerate(menu):
            if len(row) > w:
                row = row[:w - 1]
            x = w // 2 - len(row) // 2
            y = h // 2 - len(menu) // 2 + idx
            if y < h:
                if idx == selected_row_idx:
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(y, x, row)
                    self.stdscr.attroff(curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, x, row)

        self.stdscr.refresh()

    def print_nodes(self, y, x, selected_index=-1):
        h, w = self.stdscr.getmaxyx()

        header = ["No", "Node Name", "IP Address", "Role", "Etcd"]
        header_widths = [5, 20, 15, 23, 6]
        total_width = sum(header_widths) + len(header) - 1
        if total_width > w:
            for i in range(len(header_widths)):
                header_widths[i] = max(1, header_widths[i] * (w - len(header) + 1) // total_width)

        line = '+'.join(['-' * header_width for header_width in header_widths])

        self.stdscr.addstr(y, x, '+' + line + '+')
        y += 1
        self.stdscr.addstr(y, x, '|' + '|'.join(header[i].center(header_widths[i]) for i in range(len(header))) + '|')
        y += 1
        self.stdscr.addstr(y, x, '+' + line + '+')

        for idx, row in enumerate(self.node_manager.nodes):
            new_row = [
                str(idx + 1).center(header_widths[0]),
                row['name'].center(header_widths[1]),
                row['ip'].center(header_widths[2]),
                row['role'].center(header_widths[3]),
                row['etcd'].center(header_widths[4])
            ]
            y += 1
            if y < h - 2:
                if selected_index == idx:
                    self.stdscr.addstr(y, x, '|' + '|'.join(new_row) + '|', curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, x, '|' + '|'.join(new_row) + '|')

        y += 1
        if y < h:
            self.stdscr.addstr(y, x, '+' + line + '+')
        self.stdscr.refresh()

    def remove_node(self):
        selected_index = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr("Space bar is to remove node, Enter is back")
            self.print_nodes(1, 0, selected_index)
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN and selected_index < len(self.node_manager.nodes) - 1:
                selected_index += 1
            elif key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break
            elif key == ord(' '):
                self.node_manager.remove_node(selected_index)
                if selected_index > 1:
                    selected_index -= 1

    def edit_node(self):
        selected_index = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr("Space bar is select node to edit, Enter is back")

            self.print_nodes(1, 0, selected_index)
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN and selected_index < len(self.node_manager.nodes) - 1:
                selected_index += 1
            elif key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == ord(' '):
                name, ip, role, etcd = self.add_node_query(self.node_manager.nodes[selected_index])
                self.node_manager.edit_node(selected_index, name, ip, role, etcd)
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break

    def add_node_query(self, node=None):
        self.stdscr.clear()
        x = 0
        y = 0

        if node:
            name = node['name']
            ip = node['ip']
            roles = node['role'].split(',')
            etcd = node['etcd']
        else:
            name = ""
            ip = ""
            roles = []
            etcd = "N"

        name = self.make_query(y + 0, x, f"Name [{name}]: ") or name
        ip = self.make_query(y + 1, x, f"IP Address [{ip}]: ") or ip

        role_options = ["kube-master", "kube-node"]
        etcd_options = ["Y", "N"]

        selected_roles = [role in roles for role in role_options]
        etcd_idx = etcd_options.index(etcd)
        role_idx = 0

        while True:
            self.stdscr.addstr(y + 2, x, "Role: ")
            for idx, option in enumerate(role_options):
                if selected_roles[idx]:
                    self.stdscr.addstr(y + 2, x + 7 + idx * 20, "[X] " + option,
                                       curses.color_pair(2) if idx == role_idx else 0)
                else:
                    self.stdscr.addstr(y + 2, x + 7 + idx * 20, "[ ] " + option,
                                       curses.color_pair(2) if idx == role_idx else 0)

            key = self.stdscr.getch()

            if key == curses.KEY_RIGHT:
                role_idx = (role_idx + 1) % len(role_options)
            elif key == curses.KEY_LEFT:
                role_idx = (role_idx - 1) % len(role_options)
            elif key == ord(' '):
                selected_roles[role_idx] = not selected_roles[role_idx]
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
        h, w = self.stdscr.getmaxyx()
        for idx, row in enumerate(menu):
            if len(row) > w:
                row = row[:w - 1]
            x = 0
            y = idx
            if y < h:
                if idx == selected_row_idx:
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(y, x, row)
                    self.stdscr.attroff(curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, x, row)
        self.stdscr.refresh()

    def setting_node_menu(self):
        self.stdscr.clear()
        current_row = 0
        menu = ["1. Add Node", "2. Remove Node", "3. Edit Node", "4. Back"]
        while True:
            self.print_sub_menu(current_row, menu)
            self.print_nodes(y=len(menu), x=0, selected_index=-1)
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.add_node()
                elif current_row == 1 and len(self.node_manager.nodes) > 0:
                    self.remove_node()
                elif current_row == 2 and len(self.node_manager.nodes) > 0:
                    self.edit_node()
                elif current_row == 3:
                    return

    def make_query(self, y, x, query):
        h, w = self.stdscr.getmaxyx()
        if y < h and x + len(query) < w:
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

    def astrago_menu(self):
        self.stdscr.clear()
        current_row = 0
        menu = ["1. Install Astrago", "2. Uninstall Astrago", "3. Back"]
        while True:
            self.print_sub_menu(current_row, menu)
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.install_astrago()
                elif current_row == 1:
                    self.command_runner.run_command(self.stdscr, ["bash", "deploy_astrago.sh", "destroy"])
                elif current_row == 2:
                    break

    def install_nfs(self):
        self.stdscr.clear()
        inventory_path = '/tmp/nfs_inventory'
        x = 0
        y = 0
        check_install = self.make_query(0, 0, "Are you sure install NFS-server? [y/N]: ")
        if check_install == 'Y' or check_install == 'y':
            ip_address = self.make_query(y + 1, x, "Input Server IP Address: ")
            base_path = self.make_query(y + 2, x, "Input NFS Base Path: ")
            password = self.make_query(y + 3, x, "Input Node's Password: ")
            inventory = {
                'all': {
                    'vars': {},
                    'hosts': {}
                }
            }
            inventory['all']['vars']['nfs_exports'] = [
                "{} *(rw,sync,no_subtree_check,no_root_squash)".format(base_path)]
            inventory['all']['hosts']['nfs-server'] = {
                'access_ip': ip_address,
                'ansible_host': ip_address,
                'ip': ip_address,
                'ansible_user': 'root'
            }
            with open(inventory_path, 'w') as f:
                yaml.dump(inventory, f, default_flow_style=False)
            self.command_runner.run_command(self.stdscr,
                                            ["ansible-playbook", "-i", inventory_path, "ansible/install-nfs.yml",
                                             "--extra-vars", "ansible_password={}".format(password)])

    def install_kubernetes(self):
        self.stdscr.clear()
        self.print_nodes(2, 0)
        check_install = self.make_query(0, 0, "Check Cluster Table. Are you sure install Kubernetes? [y/N]: ")
        if check_install == 'Y' or check_install == 'y':
            password = self.make_query(1, 0, "Input Node's Password: ")
            self.command_runner.run_command(self.stdscr, ["bash", "kubespray/deploy-kubespray.sh", password])

    def install_gpu_driver(self):
        self.stdscr.clear()
        self.print_nodes(2, 0)
        check_install = self.make_query(0, 0, "Check Cluster Table. Are you sure install Gpu Driver? [y/N]: ")
        if check_install == 'Y' or check_install == 'y':
            password = self.make_query(1, 0, "Input Node's Password: ")
            inventory = {
                'all': {
                    'vars': {
                        "nvidia_driver_branch": "535",
                        "nvidia_driver_package_state": "present"
                    },
                    'hosts': {}
                }
            }
            for node in self.node_manager.list_nodes():
                inventory['all']['hosts'][node['name']] = {
                    'ansible_host': node['ip'],
                    'ip': node['ip'],
                    'access_ip': node['ip']  # Assuming access_ip is the same as ip for simplicity
                }

            with open('/tmp/gpu_inventory', 'w') as f:
                yaml.dump(inventory, f, default_flow_style=False)

            self.command_runner.run_command(self.stdscr,
                                            ["ansible-playbook", "-u", "root", "-i", "/tmp/gpu_inventory",
                                             "ansible/install-gpu-driver.yml",
                                             "--extra-vars", "ansible_password={}".format(password)])

    def install_gpu_driver_menu(self):

        gpu_driver_menu = ["1. 470", "2. 535", "3. back"]
        current_row = 0
        while True:
            self.print_sub_menu(current_row, gpu_driver_menu)
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(gpu_driver_menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.install_gpu_driver("470")
                elif current_row == 1:
                    self.install_gpu_driver("535")
                elif current_row == 2:
                    break

    def main(self, stdscr):
        self.stdscr = stdscr
        main_menu = ["1. Setting Nodes",
                     "2. Install Kubernetes",
                     "3. Install Astrago",
                     "4. Install NFS",
                     "5. Install GPU Driver",
                     "6. Close"]
        curses.echo()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        current_row = 0

        self.print_menu(main_menu, current_row)

        while True:
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(main_menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.setting_node_menu()
                elif current_row == 1:
                    self.install_kubernetes()
                elif current_row == 2:
                    self.install_astrago()
                elif current_row == 3:
                    self.install_nfs()
                elif current_row == 4:
                    self.install_gpu_driver()
                elif current_row == 5:
                    break  # Exit the program

                self.stdscr.clear()
                self.print_menu(main_menu, current_row)
                continue

            self.print_menu(main_menu, current_row)


if __name__ == "__main__":
    installer = AstragoInstaller()
    curses.wrapper(installer.main)
