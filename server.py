# coding=utf-8
import datetime
import queue
import socket
import sys
import threading

file = queue.Queue()
free = queue.Queue(127)


def commands(number):
    return {
        0: 'START',
        1: 'BOTH',
        2: 'OK',
        3: 'SIDE TOP',
        4: 'SIDE BOTTOM',
        5: 'RESET',
        6: 'GO',
        7: 'INDEX',
        8: 'BAD INDEX',
        9: 'GOAL BOTTOM',
        10: 'GOAL TOP'
    }.get(number, 'error')


def analyze(hex_data):
    sr = hex_data[:6]
    hex_data = hex_data[6:]
    if hex_data == '00000000':
        return 'initial packet'
    game_id = int(hex_data[2:4], 16)
    player_id = int(hex_data[4:6], 16)
    action_id = int(hex_data[6:8], 16)
    length = int(hex_data[:2], 16)
    if length == 0:
        return sr + 'game {}, player {}, action {}'.format(game_id, player_id, commands(action_id))
    data = ''
    for i in range(length):
        data += str(int(hex_data[8 + i * 2:10 + i * 2], 16))
        data += " "
    return sr + 'game {}, player {}, action {}, data {}'.format(game_id, player_id, commands(action_id), data)


def write_to_file():
    log = open("log{}.txt".format(datetime.datetime.now().strftime("%d%m%y%H%M%S")), "w")
    while True:
        data = file.get()
        if data.startswith('send') or data.startswith('recv'):
            data = analyze(data)
        log.write(data + '\n')
        if data == 'close server':
            break
    log.close()


def get_hex(game_id, player_id, action, data=None):
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
    for i in len_data, game_id, player_id, action:
        result += format(i, 'x').zfill(2)
    return result + hex_data


def recv(sock, length):
    received = sock.recv(length)
    if not received:
        raise ConnectionError
    while len(received) < length:
        next_try = sock.recv(length - len(received))
        if not next_try:
            raise ConnectionError
        received += next_try
    return ''.join([format(i, 'x').zfill(2) for i in received])


def recv_all(sock):
    try:
        header = recv(sock, 4)
        data_length = int(header[:2], 16)
        if data_length > 0:
            data = recv(sock, data_length)
        else:
            data = ''
        file.put('recv: ' + header + data)
        return header + data
    except:
        raise ConnectionError


def send_all(sock, hex_data):
    try:
        bytes_to_send = bytes.fromhex(hex_data)
        length = len(bytes_to_send)
        sent = sock.send(bytes_to_send)
        while sent < length:
            next_try = sock.send(bytes_to_send[sent:])
            sent += next_try
        file.put('send: ' + hex_data)
    except:
        raise ConnectionError


def check(game_id, player_id, action, message):
    game = int(message[2:4], 16)
    player = int(message[4:6], 16)
    command = int(message[6:8], 16)
    if game != game_id or player != player_id or command != action:
        raise ValueError


def start(sock, game_id, player_id, text):
    try:
        data = recv_all(sock)
        check(0, 0, 0, data)
        side = 3 if text == 'TOP' else 4
        send_all(sock, get_hex(game_id, player_id, side))
        data = recv_all(sock)
        check(game_id, player_id, 2, data)
    except:
        raise ConnectionError


def can_bounce(number, connections):
    if number in (
            1, 2, 3, 5, 6, 7, 9, 18, 27, 36, 45, 54, 63, 72, 81, 91,
            92, 93, 95, 96, 97, 89, 80, 71, 62, 53, 44, 35, 26, 17
    ):
        return True
    for connection in connections:
        if number in connection:
            return True
    return False


def goal_side(number):
    if number < 102:
        return 10
    else:
        return 9


def go(sock, game_id, player_id, indexes):
    try:
        send_all(sock, get_hex(game_id, player_id, 6, indexes))
        data = recv_all(sock)
        check(game_id, player_id, 7, data)
        index = int(data[8:10], 16)
        while index not in indexes:
            send_all(sock, get_hex(game_id, player_id, 8))
            data = recv_all(sock)
            check(game_id, player_id, 7, data)
            index = int(data[8:10], 16)
        send_all(sock, get_hex(game_id, player_id, 2))
        data = recv_all(sock)
        check(game_id, player_id, 2, data)
        return index
    except:
        raise ConnectionError


def turn(first, second, last_point, connections, game_id, goal):
    first_sock, first_id, second_sock, second_id = first[0], first[1], second[0], second[1]
    indexes = get_valid_indexes(last_point, connections)
    if len(indexes) == 0:
        try:
            connections.clear()
            send_all(first_sock, get_hex(game_id, first_id, 5))
            send_all(second_sock, get_hex(game_id, second_id, 5))
            data = recv_all(first_sock)
            check(game_id, first_id, 2, data)
            data = recv_all(second_sock)
            check(game_id, second_id, 2, data)
            return 49, True
        except (ConnectionError, ValueError):
            return -1, False
    try:
        index = go(first_sock, game_id, first_id, indexes)
    except ConnectionError:
        return -1, False
    bounce = can_bounce(index, connections)
    connections.add(frozenset([last_point, index]))
    if len(get_valid_indexes(index, connections)) == 0:
        bounce = False
    try:
        send_all(second_sock, get_hex(game_id, second_id, 7, index))
        data = recv_all(second_sock)
        check(game_id, second_id, 2, data)
    except (ConnectionError, ValueError):
        return -1, False

    if index > 98:
        own = False
        connections.clear()
        g_side = goal_side(index)
        if g_side == 10 and goal == 'bottom':
            own = True
        elif g_side == 9 and goal == 'top':
            own = True
        try:
            send_all(first_sock, get_hex(game_id, first_id, g_side))
            send_all(second_sock, get_hex(game_id, second_id, g_side))
            data = recv_all(first_sock)
            check(game_id, first_id, 2, data)
            data = recv_all(second_sock)
            check(game_id, second_id, 2, data)
        except (ConnectionError, ValueError):
            return -1, False
        return 49, own
    return index, bounce


def game(top, bottom, stop, game_id):
    last_point = 49
    connections = set()
    while not stop.is_set():
        while not stop.is_set():
            result = turn(top, bottom, last_point, connections, game_id, 'top')
            last_point = result[0]
            if last_point == -1:
                file.put('close game {}, player {}'.format(game_id, top[1]))
                file.put('close game {}, player {}'.format(game_id, bottom[1]))
                top[0].close()
                bottom[0].close()
                free.put(game_id, top[1], bottom[1])
                return
            if not result[1]:
                break
        while not stop.is_set():
            result = turn(bottom, top, last_point, connections, game_id, 'bottom')
            last_point = result[0]
            if last_point == -1:
                file.put('close game {}, player {}'.format(game_id, top[1]))
                file.put('close game {}, player {}'.format(game_id, bottom[1]))
                top[0].close()
                bottom[0].close()
                free.put(game_id, top[1], bottom[1])
                return
            if not result[1]:
                break
    file.put('close game {}, player {}'.format(game_id, top[1]))
    file.put('close game {}, player {}'.format(game_id, bottom[1]))
    top[0].close()
    bottom[0].close()
    free.put(game_id, top[1], bottom[1])


def get_valid_indexes(index, connections):
    indexes = get_reachable_indexes(index)
    return [i for i in indexes if frozenset([index, i]) not in connections]


def get_indexes(index, *args):
    indexes = []
    for i in args:
        new_index = index + i
        indexes.append(new_index if new_index >= 0 else new_index + 105)
    return indexes


def get_reachable_indexes(index):
    N, NE, E, SE, S, SW, W, NW = -9, -8, 1, 10, 9, 8, -1, -10
    if index in range(9, 82, 9):
        return get_indexes(index, NE, E, SE)
    elif index in range(17, 90, 9):
        return get_indexes(index, NW, W, SW)
    elif index in (1, 2, 6, 7):
        return get_indexes(index, SW, S, SE)
    elif index in (91, 92, 96, 97):
        return get_indexes(index, NW, N, NE)
    elif index == 3:
        return get_indexes(index, NE, E, SW, S, SE)
    elif index == 5:
        return get_indexes(index, NW, W, SW, S, SE)
    elif index == 93:
        return get_indexes(index, NW, N, NE, E, SE)
    elif index == 95:
        return get_indexes(index, NW, N, NE, W, SW)
    elif (99 <= index <= 104) or index in (0, 8, 90, 98):
        return []
    else:
        return get_indexes(index, NW, N, NE, W, E, SW, S, SE)


def main(ip_family, port):
    sock = None
    try:
        if ip_family == 4:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
            file.put('start server')
        else:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("::", port))
            file.put('start server')
    except:
        if sock is not None:
            file.put('close server')
            sock.close()
        sys.stderr.write("error: can't bind\n")
        sys.exit(1)
    sock.listen(5)
    threading.Thread(target=write_to_file, args=[]).start()
    stop_game = threading.Event()
    threads = []
    for i in range(1, 128):
        free.put((i, i * 2 - 1, i * 2))
    client1 = None
    only_first = False
    try:
        while True:
            try:
                game_tuple = free.get_nowait()
            except queue.Empty:
                continue
            if len(threads) > 127:
                threads = [t for t in threads if t.is_alive()]
            game_id = game_tuple[0]
            first_player_id = game_tuple[1]
            second_player_id = game_tuple[2]
            client1, addr1 = sock.accept()
            file.put('connect: {}'.format(addr1))
            try:
                start(client1, game_id, first_player_id, "TOP")
                file.put('{}, game {}, id {}'.format(addr1, game_id, first_player_id))
            except ConnectionError:
                file.put('close: {}'.format(addr1))
                client1.close()
                free.put(game_tuple)
                continue
            only_first = True
            client2, addr2 = sock.accept()
            file.put('connect: {}'.format(addr2))
            try:
                start(client2, game_id, second_player_id, "BOTTOM")
                file.put('{}, game {}, id {}'.format(addr2, game_id, second_player_id))
            except ConnectionError:
                file.put('close game {}, player {}'.format(game_id, first_player_id))
                file.put('close game {}, player {}'.format(game_id, second_player_id))
                client1.close()
                client2.close()
                free.put(game_tuple)
                continue
            only_first = False
            try:
                send_all(client1, get_hex(game_id, first_player_id, 1))
                data = recv_all(client1)
                check(game_id, first_player_id, 2, data)
            except (ConnectionError, ValueError):
                file.put('close game {}, player {}'.format(game_id, first_player_id))
                file.put('close game {}, player {}'.format(game_id, second_player_id))
                client1.close()
                client2.close()
                free.put(game_tuple)
                continue
            try:
                send_all(client2, get_hex(game_id, second_player_id, 1))
                data = recv_all(client2)
                check(game_id, second_player_id, 2, data)
            except (ConnectionError, ValueError):
                file.put('close game {}, player {}'.format(game_id, first_player_id))
                file.put('close game {}, player {}'.format(game_id, second_player_id))
                client1.close()
                client2.close()
                free.put(game_tuple)
                continue
            threads.append(
                threading.Thread(target=game,
                                 args=[(client1, first_player_id), (client2, second_player_id), stop_game, game_id]))
            threads[-1].start()
    except KeyboardInterrupt:
        stop_game.set()
        for t in threads:
            t.join()
        if only_first:
            client1.close()
            file.put('close game player')
        sock.close()
        file.put('close server')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.stderr.write("provide ip family (4 or 6) and port\n")
        sys.exit(1)
    try:
        ip_family = int(sys.argv[1])
        assert ip_family == 4 or ip_family == 6
    except:
        sys.stderr.write("error: invalid ip family\n")
        sys.exit(1)

    try:
        port = int(sys.argv[2])
        assert port > 0
    except:
        sys.stderr.write("error: invalid port\n")
        sys.exit(1)
    main(ip_family, port)
