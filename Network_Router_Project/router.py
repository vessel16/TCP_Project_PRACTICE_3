import socket
import json
import threading
import time
import queue
import os
import sys

# Поднимаемся на уровень выше, чтобы импортировать routing.py из корня TCP_Project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from routing import build_graph, shortest_path

HOST = "127.0.0.1"

# Определяем, за какой роутер мы запускаемся (по умолчанию Router1)
ROUTER_NAME = sys.argv[1] if len(sys.argv) > 1 else "Router1"

# Загружаем топологию сети из корневой папки
with open("../network.json", "r", encoding="utf-8") as f:
    network = json.load(f)
GRAPH = build_graph(network)

# Словарь адресов и портов для всех 4 роутеров
ROUTER_ADDRS = {
    "Router1": ("127.0.0.1", 5000),
    "Router2": ("127.0.0.1", 5100),
    "Router3": ("127.0.0.1", 5200),
    "WirelessRouter": ("127.0.0.1", 5300),
}

# Порты, которые слушают сами клиенты (для приема сообщений)
CLIENT_ADDRS = {
    "Client1": ("127.0.0.1", 7001),
    "Client2": ("127.0.0.1", 7002),
    "Client3": ("127.0.0.1", 7003),
    "Client4": ("127.0.0.1", 7004),
    "Client5": ("127.0.0.1", 7005),
    "Client6": ("127.0.0.1", 7006),
    "Client7": ("127.0.0.1", 7007),
    "Client8": ("127.0.0.1", 7008),
}

# Настраиваем порты для текущего роутера
TCP_PORT = ROUTER_ADDRS[ROUTER_NAME][1]
UDP_PORT = TCP_PORT + 1000

# Загружаем базу клиентов
with open("clients.json", "r", encoding="utf-8") as file:
    clients = json.load(file)

connected_clients = {}

# Очередь сообщений с приоритетом.
message_queue = queue.PriorityQueue()

stats = {
    "tcp": 0,
    "udp": 0,
    "high": 0,
    "normal": 0,
    "intra_subnet": 0,
    "inter_subnet": 0,
    "files": 0,
}

def print_routing_table(start):
    """Вывод таблицы маршрутизации для текущего роутера"""
    print(f"\n[{start}] ROUTING TABLE")
    print(f"{'Destination':<18}{'Next hop':<18}{'Cost'}")
    print("-" * 50)
    for dest in GRAPH:
        if dest == start:
            continue
        path, cost = shortest_path(GRAPH, start, dest)
        next_hop = path[1] if len(path) > 1 else "-"
        print(f"{dest:<18}{next_hop:<18}{cost}")

def forward_packet(packet, target_router):
    """Пересылка пакета следующему роутеру"""
    addr = ROUTER_ADDRS[target_router]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(addr)
        s.send(packet.encode("utf-8"))
        s.close()
    except Exception as e:
        print(f"[{ROUTER_NAME}] Ошибка пересылки на {target_router}: {e}")

def send_to_client(target, message):
    """Отправка сообщения конечному клиенту"""
    # 1. Если клиент физически подключен к этому роутеру
    if target in connected_clients:
        client = connected_clients[target]
        if client["protocol"] == "TCP":
            try:
                client["socket"].send(message.encode())
            except Exception as e:
                print(f"[{ROUTER_NAME}] Ошибка отправки TCP клиенту {target}: {e}")
        elif client["protocol"] == "UDP":
            try:
                client["socket"].sendto(message.encode(), client["address"])
            except Exception as e:
                print(f"[{ROUTER_NAME}] Ошибка отправки UDP клиенту {target}: {e}")
        return

    # 2. Если клиент не подключен локально
    if target in CLIENT_ADDRS:
        target_addr = CLIENT_ADDRS[target]
        protocol = clients[target]["protocol"]
        print(f"[{ROUTER_NAME}] Прямая отправка клиенту {target} на {target_addr} ({protocol})")
        try:
            if protocol == "UDP":
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.sendto(message.encode(), target_addr)
                s.close()
            elif protocol == "TCP":
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(target_addr)
                s.send(message.encode())
                s.close()
        except Exception as e:
            print(f"[{ROUTER_NAME}] Ошибка прямой отправки: {e}")
    else:
        print(f"[{ROUTER_NAME}] Клиент {target} не подключён и нет его адреса.")

def send_file_to_client(target, file_data, filename):
    """Отправка файла клиенту."""
    if target not in connected_clients:
        print(f"[{ROUTER_NAME}] Клиент {target} не подключён локально.")
        return

    client = connected_clients[target]
    header = f"FILE|{filename}|{len(file_data)}"
    
    if client["protocol"] == "TCP":
        try:
            client["socket"].send(header.encode())
            client["socket"].send(file_data)
        except Exception as e:
            print(f"[{ROUTER_NAME}] Ошибка отправки файла TCP клиенту {target}: {e}")
    elif client["protocol"] == "UDP":
        try:
            client["socket"].sendto(header.encode(), client["address"])
            client["socket"].sendto(file_data, client["address"])
        except Exception as e:
            print(f"[{ROUTER_NAME}] Ошибка отправки файла UDP клиенту {target}: {e}")

def process_message(sender, message):
    """Обработка входящих сообщений (поддерживает и старый формат, и SRP)"""
    
    if message.startswith("SRP|"):
        parts = message.split("|", 7)
        if len(parts) < 8:
            print(f"[{ROUTER_NAME}] Ошибка формата SRP.")
            return
        target = parts[3]
        priority_str = parts[5]
        text = parts[7]
        original_packet = message
    else:
        parts = message.split("|", 2)
        if len(parts) < 3:
            print(f"[{ROUTER_NAME}] Неверный формат сообщения.")
            return
        target = parts[0]
        priority_str = parts[1]
        text = parts[2]
        original_packet = message

    try:
        priority = int(priority_str)
    except ValueError:
        priority = 4

    if target not in clients:
        print(f"[{ROUTER_NAME}] Получатель {target} не найден.")
        return

    sender_info = clients[sender]
    target_info = clients[target]

    if sender_info["priority"] < priority:
        priority = sender_info["priority"]

    # --- ЛОГИКА МАРШРУТИЗАЦИИ (ДЕЙКСТРА) ---
    src_router = sender_info["router"]
    dst_router = target_info["router"]
    
    path, cost = shortest_path(GRAPH, src_router, dst_router)
    
    print()
    print(f"[{ROUTER_NAME}] ПОЛУЧЕНО СООБЩЕНИЕ")
    print(f"[{ROUTER_NAME}] Источник: {sender} | Назначение: {target}")
    print(f"[{ROUTER_NAME}] Кратчайший путь: {' -> '.join(path)}")
    print(f"[{ROUTER_NAME}] Стоимость маршрута: {cost}")

    if ROUTER_NAME not in path:
        return
        
    idx = path.index(ROUTER_NAME)
    
    # Если мы не последний в цепочке, пересылаем следующему
    if idx < len(path) - 1:
        next_router = path[idx + 1]
        print(f"[{ROUTER_NAME}] Пересылка следующему узлу: {next_router}")
        forward_packet(original_packet, next_router)
        return
    # --------------------------------------

    # Если мы дошли сюда, значит мы последний роутер (Edge Router)
    print(f"[{ROUTER_NAME}] Доставка клиенту {target}")
    print("Подсеть отправителя:", sender_info["subnet"])
    print("Подсеть получателя:", target_info["subnet"])
    print("Протокол отправителя:", sender_info["protocol"])
    print("Протокол получателя:", target_info["protocol"])
    print("Приоритет:", priority)

    if priority <= 2:
        print(f"[{ROUTER_NAME}] Приоритетное сообщение.")
        stats["high"] += 1
    else:
        stats["normal"] += 1

    if sender_info["subnet"] != target_info["subnet"]:
        print(f"[{ROUTER_NAME}] Выполняется межсетевой маршрут.")
        stats["inter_subnet"] += 1
    else:
        stats["intra_subnet"] += 1

    if sender_info["protocol"] != target_info["protocol"]:
        print(f"[{ROUTER_NAME}] Выполняется преобразование протокола.")

    if sender_info["protocol"] == "TCP":
        stats["tcp"] += 1
    else:
        stats["udp"] += 1

    message_queue.put((priority, time.time(), sender, target, "text", original_packet))

def process_file(sender, target, filename, file_data):
    if target not in clients:
        print(f"[{ROUTER_NAME}] Получатель {target} не найден.")
        return

    sender_info = clients[sender]
    target_info = clients[target]
    
    priority = sender_info["priority"]

    src_router = sender_info["router"]
    dst_router = target_info["router"]
    path, cost = shortest_path(GRAPH, src_router, dst_router)
    
    if ROUTER_NAME not in path:
        return
        
    idx = path.index(ROUTER_NAME)
    if idx < len(path) - 1:
        next_router = path[idx + 1]
        print(f"[{ROUTER_NAME}] Пересылка файла следующему узлу: {next_router}")
        raw_header = f"FILE|{target}|{filename}|{len(file_data)}\n".encode()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(ROUTER_ADDRS[next_router])
            s.send(raw_header + file_data)
            s.close()
        except Exception as e:
            print(f"Ошибка пересылки файла: {e}")
        return

    print()
    print(f"[{ROUTER_NAME}] ПОЛУЧЕН ФАЙЛ (Конечная точка)")
    print("Отправитель:", sender)
    print("Получатель:", target)
    print("Имя файла:", filename)
    print("Размер:", len(file_data), "байт")
    
    stats["files"] += 1
    message_queue.put((priority, time.time(), sender, target, "file", (filename, file_data)))

def message_worker():
    while True:
        priority, timestamp, sender, target, msg_type, payload = message_queue.get()
        
        time.sleep(0.1) 

        if msg_type == "text":
            send_to_client(target, payload)
        elif msg_type == "file":
            filename, file_data = payload
            send_file_to_client(target, file_data, filename)

        message_queue.task_done()

def handle_tcp_client(client_socket, client_address):
    sender = None

    try:
        # Читаем первое сообщение
        first_message = client_socket.recv(4096).decode(errors='ignore')

        if first_message.startswith("REGISTER|"):
            # Это клиент регистрируется
            sender = first_message.split("|")[1]
            connected_clients[sender] = {
                "socket": client_socket,
                "address": client_address,
                "protocol": "TCP"
            }

            print()
            print(f"[{ROUTER_NAME}] TCP-клиент подключён: {sender} | Адрес: {client_address}")
            client_socket.send("Регистрация выполнена.".encode())

        elif first_message.startswith("SRP|"):
            # Это пакет от ДРУГОГО РОУТЕРА (транзитный трафик)
            parts = first_message.split("|", 7)
            if len(parts) >= 8:
                actual_sender = parts[2]  # Берем имя отправителя из пакета
                process_message(actual_sender, first_message)
                return # Обработали транзитный пакет и выходим

        while True:
            data = client_socket.recv(4096)
            if not data:
                break

            if data.startswith(b"FILE|"):
                header_end = data.find(b"\n")
                if header_end == -1: continue
                
                header = data[:header_end].decode()
                file_data = data[header_end+1:]
                
                parts = header.split("|")
                if len(parts) == 4:
                    process_file(sender, parts[1], parts[2], file_data)
            else:
                message = data.decode()
                process_message(sender, message)

    except Exception as error:
        print(f"[{ROUTER_NAME}] Ошибка: {error}")

    finally:
        if sender in connected_clients:
            del connected_clients[sender]
        client_socket.close()
        if sender:
            print(f"[{ROUTER_NAME}] Клиент {sender} отключён.")

def tcp_server():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind((HOST, TCP_PORT))
    tcp_socket.listen()
    print(f"[{ROUTER_NAME}] TCP ожидает подключения: {HOST}:{TCP_PORT}")

    while True:
        client_socket, client_address = tcp_socket.accept()
        thread = threading.Thread(target=handle_tcp_client, args=(client_socket, client_address))
        thread.start()

def udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, UDP_PORT))
    print(f"[{ROUTER_NAME}] UDP ожидает сообщения: {HOST}:{UDP_PORT}")

    while True:
        data, client_address = udp_socket.recvfrom(4096)
        message = data.decode(errors='ignore')

        if message.startswith("REGISTER|"):
            sender = message.split("|")[1]
            connected_clients[sender] = {
                "socket": udp_socket,
                "address": client_address,
                "protocol": "UDP"
            }
            print(f"\n[{ROUTER_NAME}] UDP-клиент подключён: {sender} | Адрес: {client_address}")
            udp_socket.sendto("Регистрация выполнена.".encode(), client_address)
            
        elif message.startswith("SRP|"):
            parts = message.split("|", 7)
            if len(parts) >= 8:
                actual_sender = parts[2]
                process_message(actual_sender, message)
                
        elif message.startswith("FILE|"):
            print(f"[{ROUTER_NAME}] Получен файл по UDP.")
            sender = None
            for name, client in connected_clients.items():
                if client["protocol"] == "UDP" and client["address"] == client_address:
                    sender = name
                    break
            if sender:
                header_end = data.find(b"\n")
                if header_end != -1:
                    header = data[:header_end].decode()
                    file_data = data[header_end+1:]
                    parts = header.split("|")
                    if len(parts) == 4:
                        process_file(sender, parts[1], parts[2], file_data)
        else:
            sender = None
            for name, client in connected_clients.items():
                if client["protocol"] == "UDP" and client["address"] == client_address:
                    sender = name
                    break
            if sender:
                process_message(sender, message)

def console_commands():
    while True:
        command = input()
        if command == "/stats":
            print("\n========== СТАТИСТИКА ==========")
            print(f"TCP: {stats['tcp']} | UDP: {stats['udp']}")
            print(f"HIGH: {stats['high']} | NORMAL: {stats['normal']}")
            print(f"Внутри подсети: {stats['intra_subnet']} | Межсетевых: {stats['inter_subnet']}")
            print(f"Сообщений в очереди: {message_queue.qsize()}")
        elif command == "/list":
            print("\nПодключённые клиенты:")
            for name, info in connected_clients.items():
                print(f"  {name} {info['protocol']} (P{clients[name]['priority']})")
        elif command == "/help":
            print("Команды: /list, /stats, /help")

if __name__ == "__main__":
    print_routing_table(ROUTER_NAME)
    
    threading.Thread(target=tcp_server).start()
    threading.Thread(target=udp_server).start()
    threading.Thread(target=console_commands, daemon=True).start()
    threading.Thread(target=message_worker, daemon=True).start()
    
    # Бесконечное ожидание, чтобы программа не закрылась
    while True:
        time.sleep(1)