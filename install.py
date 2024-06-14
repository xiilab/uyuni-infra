import curses
import subprocess

nodes = []

main_menu = ["1. Install Kubernetes", "2. Install Astrago", "3. Install NFS", "4. Cancel"]


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

    header = ["   No   ", "     Node Name     ", "   IP Address   ", "   Role   "]
    line_num = len(header[0]) + len(header[1]) + len(header[2]) + len(header[3]) + len(header) + 1
    line = ''.center(line_num, '-')

    stdscr.addstr(y, x, line)
    y += 1
    stdscr.addstr(y, x, "|" + "|".join(header) + "|")
    y += 1
    stdscr.addstr(y, x, line)

    for idx, row in enumerate(nodes):
        new_row = [str(idx).center(len(header[0])), row[0].center(len(header[1])), row[1].center(len(header[2])),
                   row[2].center(len(header[3]))]
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

    stdscr.addstr(y + 2, x, "Role: ")
    role = stdscr.getstr(y + 2, x + 6, 20).decode('utf-8')

    nodes.append([name, ip, role])


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
    menu = ["1. Add Node", "2. Remove Node", "3. Edit Node", "4. Cancel"]
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
    while True:
        output = process.stdout.readline()
        if output:
            stdscr.addstr(stdscr.getyx()[0], 0, output)
            stdscr.refresh()
        error = process.stderr.readline()
        if error:
            stdscr.addstr(stdscr.getyx()[0], 0, error)
            stdscr.refresh()
        if output == '' and error == '' and process.poll() is not None:
            break


def install_kubernetes_menu(stdscr):
    stdscr.clear()
    current_row = 0
    menu = ["1. Setting Node", "2. Install Kubernetes", "3. Cancel"]
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
                stdscr.clear()
                stdscr.addstr(0, 0, "Installing Kubernetes...")
                stdscr.refresh()
                # Popen으로 실시간 출력
                process = subprocess.Popen(["sh", "kubespray/deploy-kubespray.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                read_and_display_output(process, stdscr)

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
    try:
        curses.initscr()
        curses.curs_set(False)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
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
    finally:
        curses.endwin()


curses.wrapper(main)
