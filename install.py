import curses
import os
import subprocess
from datetime import datetime
from pathlib import Path

import yaml


class DataManager:
    def __init__(self):
        self.nodes = []
        self.nfs_server = {
            'ip': '',
            'path': ''
        }
        self.save_nodes_file = 'nodes.yaml'
        self.save_nfs_server_file = 'nfs-servers.yaml'
        # Load nodes from inventory file if it exists
        if os.path.exists(self.save_nodes_file):
            with open(self.save_nodes_file, 'r') as f:
                self.nodes = yaml.safe_load(f)

        if os.path.exists(self.save_nfs_server_file):
            with open(self.save_nfs_server_file, 'r') as f:
                self.nfs_server = yaml.safe_load(f)

    def _save_to_nodes(self):
        with open(self.save_nodes_file, 'w') as f:
            yaml.dump(self.nodes, f, default_flow_style=False)

    def _save_to_nfs(self):
        with open(self.save_nfs_server_file, 'w') as f:
            yaml.dump(self.nfs_server, f, default_flow_style=False)

    def set_nfs_server(self, ip, path):
        self.nfs_server['ip'] = ip
        self.nfs_server['path'] = path
        self._save_to_nfs()

    def add_node(self, name, ip, role, etcd):
        self.nodes.append({
            'name': name,
            'ip': ip,
            'role': role,
            'etcd': etcd
        })
        self._save_to_nodes()

    def remove_node(self, index):
        if 0 <= index < len(self.nodes):
            del self.nodes[index]
            self._save_to_nodes()

    def edit_node(self, index, name, ip, role, etcd):
        if 0 <= index < len(self.nodes):
            self.nodes[index]['name'] = name
            self.nodes[index]['ip'] = ip
            self.nodes[index]['role'] = role
            self.nodes[index]['etcd'] = etcd
            self._save_to_nodes()

    def list_nodes(self):
        return self.nodes

    def __str__(self):
        return yaml.dump(self.nodes, default_flow_style=False)


class CommandRunner:

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.kubespray_inventory_path = Path.joinpath(Path.cwd(), 'kubespray/inventory/mycluster/astrago.yaml')
        self.nfs_inventory_path = '/tmp/nfs_inventory'
        self.gpu_inventory_path = '/tmp/gpu_inventory'

    def _save_kubespray_inventory(self):
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

        for node in self.data_manager.nodes:
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
        with open(self.kubespray_inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)

    def run_kubespray_install(self, password):
        self._save_kubespray_inventory()
        return self._run_command(["ansible-playbook",
                                  "-i", self.kubespray_inventory_path,
                                  "--become", "--become-user=root",
                                  "cluster.yml",
                                  "--extra-vars",
                                  "ansible_user=root ansible_password={}".format(password)],
                                 cwd='kubespray')

    def _run_command(self, cmd, cwd="."):
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)

    def run_install_astrago(self, connected_url):
        with open('environments/prod/values.yaml') as f:
            helmfile_env = yaml.load(f, Loader=yaml.FullLoader)
            helmfile_env['externalIP'] = connected_url
            helmfile_env['nfs']['enabled'] = True
            helmfile_env['nfs']['server'] = self.data_manager.nfs_server['ip']
            helmfile_env['nfs']['basePath'] = self.data_manager.nfs_server['path']

        os.makedirs('environments/astrago', exist_ok=True)
        with open('environments/astrago/values.yaml', 'w') as file:
            yaml.dump(helmfile_env, file, default_flow_style=False, sort_keys=False)
        os.putenv('KUBECONFIG', Path.joinpath(Path.cwd(), "kubespray/inventory/mycluster/artifacts/admin.conf"))
        return self._run_command([Path.joinpath(Path.cwd(), "tools/ubuntu/helmfile"), "-b",
                                  Path.joinpath(Path.cwd(), "tools/ubuntu/helm"), "-e", "astrago", "sync"])

    def _save_nfs_inventory(self):
        inventory = {
            'all': {
                'vars': {},
                'hosts': {}
            }
        }
        inventory['all']['vars']['nfs_exports'] = [
            "{} *(rw,sync,no_subtree_check,no_root_squash)".format(self.data_manager.nfs_server['path'])]
        inventory['all']['hosts']['nfs-server'] = {
            'access_ip': self.data_manager.nfs_server['ip'],
            'ansible_host': self.data_manager.nfs_server['ip'],
            'ip': self.data_manager.nfs_server['ip'],
            'ansible_user': 'root'
        }
        with open(self.nfs_inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)

    def run_install_nfs(self, password):
        self._save_nfs_inventory()
        return self._run_command(["ansible-playbook", "-i", self.nfs_inventory_path, "ansible/install-nfs.yml",
                                  "--extra-vars", "ansible_password={}".format(password)])

    def _save_gpudriver_inventory(self):
        inventory = {
            'all': {
                'vars': {
                    "nvidia_driver_branch": "535",
                    "nvidia_driver_package_state": "present"
                },
                'hosts': {}
            }
        }
        for node in self.data_manager.list_nodes():
            inventory['all']['hosts'][node['name']] = {
                'ansible_host': node['ip'],
                'ip': node['ip'],
                'access_ip': node['ip']  # Assuming access_ip is the same as ip for simplicity
            }

        with open(self.gpu_inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)

    def run_install_gpudriver(self, password):
        self._save_gpudriver_inventory()
        return self._run_command(
            ["ansible-playbook", "-u", "root", "-i", self.gpu_inventory_path,
             "ansible/install-gpu-driver.yml",
             "--extra-vars", "ansible_password={}".format(password)])


class AstragoInstaller:
    def __init__(self):
        self.data_manager = DataManager()
        self.command_runner = CommandRunner(self.data_manager)
        self.stdscr = None

    def read_and_display_output(self, process):
        output_lines = []

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                output_lines.append(output.strip())
                max_lines = self.stdscr.getmaxyx()[0] - 2
                if len(output_lines) > max_lines:
                    output_lines = output_lines[-max_lines:]
                self.stdscr.erase()  # Use erase instead of clear to avoid full screen flicker
                _, w = self.stdscr.getmaxyx()
                for idx, line in enumerate(output_lines):
                    self.stdscr.addstr(idx, 0, line[:w - 1])
                self.stdscr.refresh()
        process.stdout.close()
        process.wait()
        # Display the "Press any key to return to the menu" message
        output_lines.append("Press any key to return to the menu")
        h, w = self.stdscr.getmaxyx()
        for idx, line in enumerate(output_lines[-h + 1:]):
            self.stdscr.addstr(idx, 0, line[:w - 1])
        self.stdscr.refresh()
        curses.flushinp()
        self.stdscr.getch()

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
        if datetime.today().month == 10 and datetime.today().day == 31:
            title = [
                " ▄▄▄        ██████ ▄▄▄█████▓ ██▀███   ▄▄▄        ▄████  ▒█████  ",
                "▒████▄    ▒██    ▒ ▓  ██▒ ▓▒▓██ ▒ ██▒▒████▄     ██▒ ▀█▒▒██▒  ██▒",
                "▒██  ▀█▄  ░ ▓██▄   ▒ ▓██░ ▒░▓██ ░▄█ ▒▒██  ▀█▄  ▒██░▄▄▄░▒██░  ██▒",
                "░██▄▄▄▄██   ▒   ██▒░ ▓██▓ ░ ▒██▀▀█▄  ░██▄▄▄▄██ ░▓█  ██▓▒██   ██░",
                " ▓█   ▓██▒▒██████▒▒  ▒██▒ ░ ░██▓ ▒██▒ ▓█   ▓██▒░▒▓███▀▒░ ████▓▒░",
                " ▒▒   ▓▒█░▒ ▒▓▒ ▒ ░  ▒ ░░   ░ ▒▓ ░▒▓░ ▒▒   ▓▒█░ ░▒   ▒ ░ ▒░▒░▒░ ",
                "  ▒   ▒▒ ░░ ░▒  ░ ░    ░      ░▒ ░ ▒░  ▒   ▒▒ ░  ░   ░   ░ ▒ ▒░ ",
                "  ░   ▒   ░  ░  ░    ░        ░░   ░   ░   ▒   ░ ░   ░ ░ ░ ░ ▒  ",
                "  ░  ░      ░              ░           ░  ░      ░     ░ ░      ",
            ]

        h, w = self.stdscr.getmaxyx()
        for idx, line in enumerate(title):
            line = line[:w - 1]
            x = w // 2 - len(line) // 2
            y = h // 2 - len(title) // 2 + idx - 10
            if 0 <= y < h and 0 <= x < w:
                self.stdscr.addstr(y, x, line[:w], curses.color_pair(2))
        self.stdscr.refresh()

    def print_menu(self, menu, selected_row_idx):
        self.stdscr.clear()
        self.print_banner()
        h, w = self.stdscr.getmaxyx()
        x = w // 2 - len(max(menu, key=len)) // 2
        for idx, row in enumerate(menu):
            y = h // 2 - len(menu) // 2 + idx
            if 0 <= y < h and 0 <= x < w:
                if idx == selected_row_idx:
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(y, x, row[:w])
                    self.stdscr.attroff(curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, x, row[:w])
        self.stdscr.refresh()

    def print_table(self, y, x, header, data, selected_index=-1):
        h, w = self.stdscr.getmaxyx()
        header_widths = [len(col) for col in header]
        data_widths = [[len(str(value)) for value in row] for row in data]

        if data_widths:
            max_widths = [max(header_widths[i], *[row[i] for row in data_widths]) for i in range(len(header))]
        else:
            max_widths = header_widths[:]

        total_width = sum(max_widths) + len(header) - 1
        if total_width > w:
            for i in range(len(max_widths)):
                max_widths[i] = max(1, max_widths[i] * (w - len(header) + 1) // total_width)

        line = '+'.join(['-' * width for width in max_widths])

        self.stdscr.addstr(y, x, '+' + line + '+')
        y += 1
        self.stdscr.addstr(y, x, '|' + '|'.join(header[i].center(max_widths[i]) for i in range(len(header))) + '|')
        y += 1
        self.stdscr.addstr(y, x, '+' + line + '+')

        for idx, row in enumerate(data):
            new_row = [str(col).center(max_widths[i]) for i, col in enumerate(row)]
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

    def print_nfs_server_table(self, y, x):
        header = ["IP Address", "Base Path"]
        data = [(
            self.data_manager.nfs_server['ip'],
            self.data_manager.nfs_server['path']
        )]
        self.print_table(y, x, header, data)

    def print_nodes_table(self, y, x, selected_index=-1):
        header = ["No", "Node Name", "IP Address", "Role", "Etcd"]
        data = []
        for idx, row in enumerate(self.data_manager.nodes):
            data.append((
                str(idx + 1),
                row['name'],
                row['ip'],
                row['role'],
                row['etcd']
            ))
        self.print_table(y, x, header, data, selected_index)

    def remove_node(self):
        selected_index = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr("Press the space bar to remove a node, Enter to go back")
            self.print_nodes_table(1, 0, selected_index)
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN and selected_index < len(self.data_manager.nodes) - 1:
                selected_index += 1
            elif key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break
            elif key == ord(' '):
                self.data_manager.remove_node(selected_index)
                if selected_index > 1:
                    selected_index -= 1

    def edit_node(self):
        selected_index = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr("Press the space bar to select a node to edit, Enter to go back")

            self.print_nodes_table(1, 0, selected_index)
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN and selected_index < len(self.data_manager.nodes) - 1:
                selected_index += 1
            elif key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == ord(' '):
                name, ip, role, etcd = self.add_node_query(self.data_manager.nodes[selected_index])
                self.data_manager.edit_node(selected_index, name, ip, role, etcd)
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
                    self.stdscr.addstr(y + 2, x + 7 + idx * 20, "[V] " + option,
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
        self.data_manager.add_node(name, ip, role, etcd)

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

    def make_query(self, y, x, query, length=20):
        h, w = self.stdscr.getmaxyx()
        if y < h and x + len(query) < w:
            self.stdscr.addstr(y, x, query)
        return self.stdscr.getstr(y, x + len(query), length).decode('utf-8')

    def install_astrago(self):
        self.stdscr.clear()
        nfs_server_ip = self.data_manager.nfs_server['ip']
        nfs_base_path = self.data_manager.nfs_server['path']

        if not nfs_server_ip or not nfs_base_path:
            self.stdscr.addstr(0, 0, "You have to set the NFS server")
            self.stdscr.addstr(1, 0, "Press any key to return to the menu")
            self.stdscr.getch()
            return None

        x = 0
        y = 0

        connected_url = self.make_query(y + 0, x, "Connected Url: ")
        self.read_and_display_output(self.command_runner.run_install_astrago(connected_url))

    def install_nfs(self):

        self.stdscr.clear()
        x = 0
        y = 0
        self.print_nfs_server_table(y + 2, 0)
        check_install = self.make_query(0, 0, "Are you sure you want to install NFS-server? [y/N]: ")
        if check_install == 'Y' or check_install == 'y':
            password = self.make_query(y + 1, x, "Input Node's Password: ")
            self.read_and_display_output(self.command_runner.run_install_nfs(password))

    def install_gpu_driver(self):
        self.stdscr.clear()
        self.print_nodes_table(2, 0)
        check_install = self.make_query(0, 0,
                                        "Install the GPU Driver? "
                                        "The system will reboot after installation [y/N]: ")
        if check_install == 'Y' or check_install == 'y':
            password = self.make_query(1, 0, "Input Node's Password: ")
            self.read_and_display_output(self.command_runner.run_install_gpudriver(password))

    def install_kubernetes(self):
        self.stdscr.clear()
        self.print_nodes_table(2, 0)

        check_install = self.make_query(0, 0,
                                        "Check the Node Table. Are you sure you want to install Kubernetes? [y/N]: ")
        if check_install == 'Y' or check_install == 'y':
            password = self.make_query(1, 0, "Input Node's Password: ")
            self.read_and_display_output(self.command_runner.run_kubespray_install(password))

    def setting_node_menu(self):
        self.stdscr.clear()
        current_row = 0
        menu = ["1. Add Node", "2. Remove Node", "3. Edit Node", "4. Back"]
        while True:
            self.print_sub_menu(current_row, menu)
            self.print_nodes_table(len(menu), 0, selected_index=-1)
            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    self.add_node()
                elif current_row == 1 and len(self.data_manager.nodes) > 0:
                    self.remove_node()
                elif current_row == 2 and len(self.data_manager.nodes) > 0:
                    self.edit_node()
                elif current_row == 3:
                    return

    def set_nfs_query(self, nfs_server=None):
        self.stdscr.clear()
        x = 0
        y = 0
        ip = nfs_server['ip']
        path = nfs_server['path']
        ip = self.make_query(y + 0, x, f"IP Address [{ip}]: ") or ip
        path = self.make_query(y + 1, x, f"Base Path [{path}]: ") or path
        return ip, path

    def setting_nfs_menu(self):
        self.stdscr.clear()
        current_row = 0
        menu = ["1. Setting NFS Server", "2. Install NFS Server(Optional)", "3. Back"]
        while True:
            self.print_sub_menu(current_row, menu)
            self.print_nfs_server_table(y=len(menu), x=0)

            key = self.stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    ip, path = self.set_nfs_query(self.data_manager.nfs_server)
                    self.data_manager.set_nfs_server(ip, path)
                elif current_row == 1:
                    self.install_nfs()
                elif current_row == 2:
                    break

    def install_astrago_menu(self):
        menu = ["1. Set NFS Server", "2. Install Astrago", "3. Back"]
        self.navigate_menu(menu, {
            0: self.setting_nfs_menu,
            1: self.install_astrago
        })

    def install_kubernetes_menu(self):
        menu = ["1. Set Nodes", "2. Install Kubernetes", "3. Install GPU Driver (Optional)", "4. Back"]
        self.navigate_menu(menu, {
            0: self.setting_node_menu,
            1: self.install_kubernetes,
            2: self.install_gpu_driver
        })

    def navigate_menu(self, menu, handlers):
        current_row = 0
        self.print_menu(menu, current_row)
        while True:
            key = self.stdscr.getch()
            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row in handlers:
                    handlers[current_row]()
                if current_row == len(menu) - 1:
                    break
            self.print_menu(menu, current_row)

    def main(self, stdscr):
        self.stdscr = stdscr
        main_menu = ["1. Kubernetes",
                     "2. Astrago",
                     "3. Close"]
        curses.echo()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        self.navigate_menu(main_menu, {
            0: self.install_kubernetes_menu,
            1: self.install_astrago_menu
        })


if __name__ == "__main__":
    installer = AstragoInstaller()
    curses.wrapper(installer.main)
