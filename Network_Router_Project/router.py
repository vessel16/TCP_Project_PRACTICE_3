import socket
import json
import threading
import time
import queue
import os

HOST = "127.0.0.1"
TCP_PORT = 5000
UDP_PORT = 6000

with open("clients.json", "r", encoding="utf-8") as file:
    clients = json.load(file)

connected_clients = {}

# Очередь сообщений с приоритетом.
# Формат: (priority, timestamp, sender, target, message_type, payload)
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

def send_to_client(target, message):
    if target not in connected_clients:
        print(f"[ROUTER] Клиент {target} не подключён.")
        return

    client = connected_clients[target]

    if client["protocol"] == "TCP":
        try:
            client["socket"].send(message.encode())
        except Exception as e:
            print(f"[ROUTER] Ошибка отправки TCP клиенту {target}: {e}")
    elif client["protocol"] == "UDP":
        try:
            client["socket"].sendto(message.encode(), client["address"])
        except Exception as e:
            print(f"[ROUTER] Ошибка отправки UDP клиенту {target}: {e}")

def send_file_to_client(target, file_data, filename):
    """Отправка файла клиенту."""
    if target not in connected_clients:
        print(f"[ROUTER] Клиент {target} не подключён.")
        return

    client = connected_clients[target]
    header = f"FILE|{filename}|{len(file_data)}"
    
    if client["protocol"] == "TCP":
        try:
            client["socket"].send(header.encode())
            client["socket"].send(file_data)
        except Exception as e:
            print(f"[ROUTER] Ошибка отправки файла TCP клиенту {target}: {e}")
    elif client["protocol"] == "UDP":
        try:
            client["socket"].sendto(header.encode(), client["address"])
            client["socket"].sendto(file_data, client["address"])
        except Exception as e:
            print(f"[ROUTER] Ошибка отправки файла UDP клиенту {target}: {e}")

def process_message(sender, message):
    parts = message.split("|", 2)

    if len(parts) < 3:
        print("[ROUTER] Неверный формат сообщения.")
        return

    target = parts[0]
    priority_str = parts[1]
    text = parts[2]

    try:
        priority = int(priority_str)
    except ValueError:
        priority = 4

    if target not in clients:
        print(f"[ROUTER] Получатель {target} не найден.")
        return

    sender_info = clients[sender]
    target_info = clients[target]

    # Автоматический приоритет для бота, если он не указал
    if sender_info.get("type") == "bot":
        pass

    if sender_info["priority"] < priority:
        priority = sender_info["priority"]

    print()
    print("[ROUTER] ПОЛУЧЕНО СООБЩЕНИЕ")
    print("Отправитель:", sender)
    print("Получатель:", target)
    print("Подсеть отправителя:", sender_info["subnet"])
    print("Подсеть получателя:", target_info["subnet"])
    print("Протокол отправителя:", sender_info["protocol"])
    print("Протокол получателя:", target_info["protocol"])
    print("Приоритет:", priority)
    print("Сообщение:", text)

    if priority <= 2:
        print("[ROUTER] Приоритетное сообщение.")
        stats["high"] += 1
    else:
        stats["normal"] += 1

    if sender_info["subnet"] != target_info["subnet"]:
        print("[ROUTER] Выполняется межсетевой маршрут.")
        stats["inter_subnet"] += 1
    else:
        stats["intra_subnet"] += 1

    if sender_info["protocol"] != target_info["protocol"]:
        print("[ROUTER] Выполняется преобразование протокола.")

    if sender_info["protocol"] == "TCP":
        stats["tcp"] += 1
    else:
        stats["udp"] += 1

    message_queue.put((priority, time.time(), sender, target, "text", text))

def process_file(sender, target, filename, file_data):
    if target not in clients:
        print(f"[ROUTER] Получатель {target} не найден.")
        return

    sender_info = clients[sender]
    target_info = clients[target]
    priority = sender_info["priority"]

    print()
    print("[ROUTER] ПОЛУЧЕН ФАЙЛ")
    print("Отправитель:", sender)
    print("Получатель:", target)
    print("Имя файла:", filename)
    print("Размер:", len(file_data), "байт")
    print("Приоритет:", priority)

    stats["files"] += 1

    message_queue.put((priority, time.time(), sender, target, "file", (filename, file_data)))

def message_worker():
    while True:
        priority, timestamp, sender, target, msg_type, payload = message_queue.get()
        
        time.sleep(0.1) 

        if msg_type == "text":
            result = f"[P{priority}] {sender} → {target}: {payload}"
            send_to_client(target, result)
        elif msg_type == "file":
            filename, file_data = payload
            send_file_to_client(target, file_data, filename)

        message_queue.task_done()

def handle_tcp_client(client_socket, client_address):
    sender = None

    try:
        registration = client_socket.recv(1024).decode()

        if registration.startswith("REGISTER|"):
            sender = registration.split("|")[1]
            connected_clients[sender] = {
                "socket": client_socket,
                "address": client_address,
                "protocol": "TCP"
            }

            print()
            print("[ROUTER] TCP-клиент подключён:", sender)
            print("Адрес:", client_address)
            print("Подсеть:", clients[sender]["subnet"])
            print("Приоритет:", clients[sender]["priority"])

            client_socket.send("Регистрация выполнена.".encode())

        while True:
            data = client_socket.recv(4096)

            if not data:
                break

            if data.startswith(b"FILE|"):
                header_end = data.find(b"\n")
                if header_end == -1:
                    print("[ROUTER] Ошибка: неверный формат файла.")
                    continue
                
                header = data[:header_end].decode()
                file_data = data[header_end+1:]
                
                parts = header.split("|")
                if len(parts) == 4:
                    target = parts[1]
                    filename = parts[2]
                    process_file(sender, target, filename, file_data)
                else:
                    print("[ROUTER] Ошибка: неверный заголовок файла.")
            else:
                message = data.decode()
                process_message(sender, message)

    except Exception as error:
        print("[ROUTER] Ошибка:", error)

    finally:
        if sender in connected_clients:
            del connected_clients[sender]

        client_socket.close()
        print(f"[ROUTER] Клиент {sender} отключён.")

def tcp_server():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind((HOST, TCP_PORT))
    tcp_socket.listen()
    print(f"[ROUTER] TCP ожидает подключения: {HOST}:{TCP_PORT}")

    while True:
        client_socket, client_address = tcp_socket.accept()
        thread = threading.Thread(target=handle_tcp_client, args=(client_socket, client_address))
        thread.start()

def udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, UDP_PORT))
    print(f"[ROUTER] UDP ожидает сообщения: {HOST}:{UDP_PORT}")

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
            print()
            print("[ROUTER] UDP-клиент подключён:", sender)
            print("Адрес:", client_address)
            print("Подсеть:", clients[sender]["subnet"])
            print("Приоритет:", clients[sender]["priority"])
            udp_socket.sendto("Регистрация выполнена.".encode(), client_address)
        elif message.startswith("FILE|"):
            print("[ROUTER] Получен файл по UDP (упрощённая обработка).")
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
            print()
            print("========== СТАТИСТИКА ==========")
            print(f"TCP: {stats['tcp']}")
            print(f"UDP: {stats['udp']}")
            print(f"HIGH (P1-P2): {stats['high']}")
            print(f"NORMAL (P3-P8): {stats['normal']}")
            print(f"Файлов: {stats['files']}")
            print(f"Внутри подсети: {stats['intra_subnet']}")
            print(f"Межсетевых: {stats['inter_subnet']}")
            print(f"Сообщений в очереди: {message_queue.qsize()}")
        elif command == "/list":
            print()
            print("Подключённые клиенты:")
            for name, info in connected_clients.items():
                print(f"  {name} {info['protocol']} (P{clients[name]['priority']})")
        elif command == "/help":
            print("Команды: /list, /stats, /help")

tcp_thread = threading.Thread(target=tcp_server)
udp_thread = threading.Thread(target=udp_server)
console_thread = threading.Thread(target=console_commands, daemon=True)
worker_thread = threading.Thread(target=message_worker, daemon=True)

worker_thread.start()
console_thread.start()
tcp_thread.start()
udp_thread.start()