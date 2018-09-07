import tkinter as tk
import tkinter.font as tkf
import queue
import socket
import sys
import threading

icon = b'R0lGODlhEAAQAOf9AAAAfwABfwACfgADfgAEfQAFfQAGfAAHfAAIewAJewAKegALegAMeQANeQAOeAAPeAAQdwARdwASdgATdgAUdQAVdQAW' \
       b'dAAXdAAYcwAZcwAacgAbcgAccQAdcQAecAAfcAAgbwAhbwAibgAjbgAkbQAlbQAmbAAnbAAoawApawAqagAragAsaQAtaQAuaAAvaAAwZwAx' \
       b'ZwAyZgAzZgA0ZQA1ZQA2ZAA3ZAA4YwA5YwA6YgA7YgA8YQA9YQA+YAA/YABAXwBBXwBCXgBDXgBEXQBFXQBGXABIWwBJWwBKWgBLWgBMWQBN' \
       b'WQBOWABPWABQVwBRVwBSVgBTVgBUVQBVVQBWVABXVABYUwBZUwBaUgBbUgBcUQBdUQBeUABfUABgTwBhTwBiTgBjTgBkTQBlTQBmTABnTABo' \
       b'SwBpSwBqSgBrSgBsSQBtSQBuSABvSABwRwBxRwByRgBzRgB0RQB1RQB2RAB3RAB4QwB5QwB6QgB7QgB8QQB9QQB+QAB/QACAPwCBPwCCPgCD' \
       b'PgCEPQCFPQCGPACHPACIOwCJOwCKOgCLOgCMOQCNOQCOOACPOACQNwCRNwCSNgCTNgCUNQCVNQCXNACYMwCZMwCaMgCbMgCcMQCdMQCeMACf' \
       b'MACgLwChLwCjLgCkLQClLQCmLACnLACoKwCpKwCqKgCrKgCsKQCtKQCuKACvKACwJwCxJwCyJgCzJgC0JQC1JQC2JAC3JAC4IwC5IwC6IgC7' \
       b'IgC8IQC9IQC+IAC/IADAHwDBHwDCHgDDHgDEHQDFHQDGHADHHADIGwDJGwDKGgDLGgDMGQDNGQDOGADPGADQFwDRFwDSFgDTFgDUFQDVFQDW' \
       b'FADXFADYEwDZEwDaEgDbEgDcEQDdEQDeEADfEADgDwDhDwDiDgDjDgDkDQDlDQDmDADnDADoCwDpCwDqCgDrCgDsCQDtCQDuCADvCADwBwDx' \
       b'BwDyBgDzBgD0BQD1BQD2BAD3BAD4AwD5AwD6AgD7AgD8AQD9AQD+AQD/AP///////////ywAAAAAEAAQAAAIrgABCBRI4MMTNGq0qBAwsCGV' \
       b'bPf27eO3D58yHQ0B5LDHj5++e/jyTZw3pKEpfvcU9fjw4QWme/yCDRQwjV+0jABw8TNXQGAAavyE4RzGz9sAn9v43RoYIEYqffxMDUTAjt8n' \
       b'DkImWcPX0ZyIgRlglrMHtaO9XSga3tA3kSI9aYlOBMiYZV++VoaWbMA50A+/eRf4ZmzEL14DwQ0T8YPHAPFAQH8nOBbIZl89Do4DAgA7'


class Game(tk.Canvas, object):
    MARGIN = 15
    SIDE = 40
    WIDTH = MARGIN * 2 + SIDE * 8
    HEIGHT = MARGIN * 2 + SIDE * 12
    OVAL = 7
    LINE_WIDTH = 15

    def __init__(self, parent, queue_read, queue_write):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT)
        self.parent = parent
        self.queue_read = queue_read
        self.queue_write = queue_write
        self.ovals = []
        self.points = []
        self.lines = []
        self.indexes = []
        self.last = 49
        self.turn = False
        self.draw_field()
        self.after(200, self.try_read)

    def draw_field(self):
        self.create_polygon(
            [self.MARGIN + self.SIDE * i for i in
             (0, 1, 3, 1, 3, 0, 5, 0, 5, 1, 8, 1, 8, 11, 5, 11, 5, 12, 3, 12, 3, 11, 0, 11)],
            fill="#228b22", outline="#000000", width=self.LINE_WIDTH
        )
        for i in range(1, 12):
            for j in range(9):
                self.add_oval(i, j)
        for i in (0, 12):
            for j in (3, 4, 5):
                self.add_oval(i, j)
        self.add_point(self.ovals[49], 49)
        self.itemconfig(self.ovals[49], fill="#ffffff")

    def add_oval(self, i, j):
        self.ovals.append(self.create_oval(
            self.MARGIN - self.OVAL + self.SIDE * j, self.MARGIN - self.OVAL + self.SIDE * i,
            self.MARGIN + self.OVAL + self.SIDE * j, self.MARGIN + self.OVAL + self.SIDE * i,
            fill="#808080"
        ))
        self.tag_bind(self.ovals[-1], "<Button-1>", self.on_click)

    def find_oval(self, x, y):
        for oval in self.ovals:
            coords = self.coords(oval)
            if (coords[0] <= x <= coords[2]) and (coords[1] <= y <= coords[3]):
                return oval
        return None

    def fill_ovals(self, indexes, color):
        for i in indexes:
            self.itemconfig(self.ovals[i], fill=color)

    def add_point(self, oval, index):
        coords = self.coords(oval)
        self.points.append(((coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2, index))

    def add_line(self, color):
        self.lines.append(self.create_line(
            self.points[0][0], self.points[0][1],
            self.points[1][0], self.points[1][1],
            width=self.LINE_WIDTH, fill=color
        ))
        self.tag_raise(self.ovals[self.points[0][2]])
        self.tag_raise(self.ovals[self.points[1][2]])

    def on_click(self, event):
        if not self.turn:
            return
        current_oval = self.find_oval(self.canvasx(event.x), self.canvasy(event.y))
        if not current_oval:
            return
        current_index = self.ovals.index(current_oval)
        if current_index not in self.indexes:
            return
        self.fill_ovals(self.indexes, "#808080")
        self.itemconfig(self.ovals[self.last], fill="#808080")
        self.itemconfig(self.ovals[current_index], fill="#ffffff")
        self.last = current_index
        self.draw_line(current_index, True)

    def draw_line(self, index, turn=False):
        self.add_point(self.ovals[index], index)
        if turn:
            self.add_line("#00008b")
            self.turn = False
            self.parent.set_turn(False)
            self.queue_write.put(str(index))
        else:
            self.add_line("#8b0000")
        self.points.pop(0)

    def reset(self):
        for line in self.lines:
            self.delete(line)
        self.lines.clear()
        self.points.clear()
        self.add_point(self.ovals[49], 49)
        self.fill_ovals(self.indexes, "#808080")
        self.indexes.clear()
        self.itemconfig(self.ovals[49], fill="#ffffff")
        self.itemconfig(self.ovals[self.last], fill="#808080")
        self.last = 49
        self.turn = False

    def try_read(self):
        try:
            data = self.queue_read.get_nowait()
            if data.startswith("INDEXES:"):
                self.indexes.clear()
                indexes = data.split(':')[1][:-1].split(',')
                for i in indexes:
                    self.indexes.append(int(i))
                self.fill_ovals(self.indexes, "#ffff00")
                self.turn = True
                self.parent.set_turn(True)
            elif data.startswith("GOAL"):
                self.reset()
                self.parent.set_result(data)
            elif data == "RESET":
                self.reset()
            elif data == "TOP" or data == "BOTTOM":
                self.parent.set_side(data)
            elif data.startswith("QUIT") or data.startswith('CAN'):
                self.parent.set_text(data)
                self.turn = False
            else:
                index = int(data)
                self.itemconfig(self.ovals[index], fill="#ffffff")
                self.itemconfig(self.ovals[self.last], fill="#808080")
                self.last = index
                self.draw_line(index)
        except queue.Empty:
            pass
        self.after(200, self.try_read)


class Program(tk.Frame, object):

    def __init__(self, parent, queue_read, queue_write):
        super().__init__(parent)
        self.parent = parent
        self.queue_write = queue_write
        self.result = tk.Label(self, text='0:0')
        self.turn = tk.Label(self, text='WAIT')
        self.side = ''
        self.game = Game(self, queue_read, queue_write)
        self.result.pack()
        self.game.pack()
        self.turn.pack()
        self.parent.protocol('WM_DELETE_WINDOW', self.close)

    def close(self):
        self.queue_write.put("CLOSE")
        self.parent.destroy()

    def set_turn(self, value):
        info = 'GO' if value else 'WAIT'
        self.turn.configure(text=self.side + info)

    def set_side(self, side):
        self.side = side + ': '
        self.turn.configure(text=self.side + 'WAIT')

    def set_text(self, message):
        self.turn.configure(text=message)

    def set_result(self, message):
        result = self.result.cget("text").split(":")
        top = int(result[0])
        bottom = int(result[1])
        if message.endswith("TOP"):
            top += 1
        else:
            bottom += 1
        self.result.configure(text='{} : {}'.format(top, bottom))


class SocketHelper(object):

    def __init__(self, ip, port):
        super().__init__()
        self.sock = None
        self.ip = ip
        self.port = port

    def connect(self):
        try:
            socket.inet_aton(self.ip)
            family = socket.AF_INET
        except OSError:
            family = socket.AF_INET6
        try:
            self.sock = socket.socket(family, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((ip, port))
            self.sock.settimeout(None)
        except:
            raise ConnectionError

    def recv(self, length):
        received = self.sock.recv(length)
        if not received:
            raise ConnectionError
        while len(received) < length:
            next_try = self.sock.recv(length - len(received))
            if not next_try:
                raise ConnectionError
            received += next_try
        return ''.join([format(i, 'x').zfill(2) for i in received])

    def recv_all(self):
        try:
            header = self.recv(4)
            data_length = int(header[:2], 16)
            if data_length > 0:
                data = self.recv(data_length)
            else:
                data = ''
            return header + data
        except socket.timeout:
            raise socket.timeout
        except:
            raise ConnectionError

    def send_all(self, hex_data):
        try:
            bytes_to_send = bytes.fromhex(hex_data)
            length = len(bytes_to_send)
            sent = self.sock.send(bytes_to_send)
            while sent < length:
                next_try = self.sock.send(bytes_to_send[sent:])
                sent += next_try
        except:
            raise ConnectionError

    def check(self, game_id, player_id, message):
        game = int(message[2:4], 16)
        player = int(message[4:6], 16)
        if game != game_id or player != player_id:
            raise ValueError

    def check_first(self, data):
        if len(data) != 8:
            raise ValueError
        length = int(data[:2], 16)
        game_id = int(data[2:4], 16)
        player_id = int(data[4:6], 16)
        action_id = int(data[6:8], 16)
        if length != 0 or (action_id != 3 and action_id != 4):
            raise ValueError

    def close(self):
        self.sock.close()

    def settimeout(self, time):
        self.sock.settimeout(time)


class Client(object):

    def __init__(self, root, ip, port):
        super().__init__()
        self.root = root
        self.ip = ip
        self.port = port
        self.queue_read = queue.Queue()
        self.queue_write = queue.Queue()
        self.program = Program(root, self.queue_write, self.queue_read)
        self.program.pack()
        self.thread = threading.Thread(target=self.client)
        self.thread.start()

    def get_hex(self, game, player, action, data=None):
        if data is not None:
            if type(data) is list:
                len_data = len(data)
                hex_data = ''
                for d in data:
                    hex_data += format(d, 'x').zfill(2)
            else:
                len_data = 1
                hex_data = format(data, 'x').zfill(2)
        else:
            len_data = 0
            hex_data = ''
        result = ''
        for i in len_data, game, player, action:
            result += format(i, 'x').zfill(2)
        return result + hex_data

    def client(self):
        START, BOTH, OK, SIDE_TOP, SIDE_BOTTOM, RESET, GO = 0, 1, 2, 3, 4, 5, 6
        INDEX, BAD_INDEX, GOAL_BOTTOM, GOAL_TOP = 7, 8, 9, 10

        sock = SocketHelper(ip, port)
        try:
            sock.connect()
        except ConnectionError:
            self.queue_write.put("CAN'T CONNECT")
            sock.close()
            return
        try:
            sock.send_all(self.get_hex(0, 0, 0))
            data = sock.recv_all()
            sock.check_first(data)
            game_id = int(data[2:4], 16)
            player_id = int(data[4:6], 16)
            command = int(data[6:8], 16)
            if command == SIDE_TOP:
                self.queue_write.put("TOP")
            else:
                self.queue_write.put("BOTTOM")
            sock.send_all(self.get_hex(game_id, player_id, OK))
        except (ConnectionError, ValueError):
            self.queue_write.put("QUIT")
            sock.close()
            return

        sock.settimeout(2)
        while True:
            try:
                data = sock.recv_all()
                try:
                    sock.check(game_id, player_id, data)
                    command = int(data[6:8], 16)
                    if command != BOTH:
                        raise ValueError
                except ValueError:
                    self.queue_write.put("QUIT")
                    sock.close()
                    return
                sock.send_all(self.get_hex(game_id, player_id, OK))
                break
            except socket.timeout:
                try:
                    info = self.queue_read.get_nowait()
                    if info == "CLOSE":
                        self.queue_write.put("QUIT")
                        sock.close()
                        return
                except queue.Empty:
                    pass
            except ConnectionError:
                self.queue_write.put("QUIT")
                sock.close()
                return
        sock.settimeout(None)

        try:
            while True:
                data = sock.recv_all()
                sock.check(game_id, player_id, data)
                command = int(data[6:8], 16)
                if command == GO:
                    indexes = ''
                    length = int(data[:2], 16)
                    for i in range(length):
                        indexes += str(int(data[8 + i * 2:10 + i * 2], 16))
                        indexes += ","
                    while True:
                        self.queue_write.put("INDEXES:" + indexes)
                        info = self.queue_read.get()
                        if info == "CLOSE":
                            self.queue_write.put("QUIT")
                            sock.close()
                            return
                        index = int(info)
                        sock.send_all(self.get_hex(game_id, player_id, INDEX, index))
                        data = sock.recv_all()
                        sock.check(game_id, player_id, data)
                        if int(data[6:8], 16) == OK:
                            break
                    sock.send_all(self.get_hex(game_id, player_id, OK))
                elif command == GOAL_TOP or command == GOAL_BOTTOM:
                    if command == GOAL_TOP:
                        self.queue_write.put("GOAL TOP")
                    else:
                        self.queue_write.put("GOAL BOTTOM")
                    sock.send_all(self.get_hex(game_id, player_id, OK))
                elif command == RESET:
                    self.queue_write.put("RESET")
                    sock.send_all(self.get_hex(game_id, player_id, OK))
                else:
                    self.queue_write.put(str(int(data[8:10], 16)))
                    sock.send_all(self.get_hex(game_id, player_id, OK))
        except (ConnectionError, ValueError):
            self.queue_write.put("QUIT")
            sock.close()
            return


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.stderr.write("provide ip and port\n")
        sys.exit(1)
    ip = sys.argv[1]
    try:
        port = int(sys.argv[2])
        assert port > 0
    except:
        sys.stderr.write("error: invalid port\n")
        sys.exit(1)

    root = tk.Tk()
    root.title('Paper soccer')
    root.iconphoto(root, tk.PhotoImage(data=icon))
    tkf.nametofont('TkDefaultFont').configure(size=20, weight=tkf.BOLD)
    client = Client(root, ip, port)
    root.mainloop()
