import socket
import json
import threading


HOST = "127.0.0.1"
TCP_PORT = 5000
UDP_PORT = 6000


with open("clients.json", "r", encoding="utf-8") as file:
    clients = json.load(file)


connected_clients = {}


def send_to_client(target, message):
    if target not in connected_clients:
        print(f"[ROUTER] Клиент {target} не подключён.")
        return

    client = connected_clients[target]

    if client["protocol"] == "TCP":
        client["socket"].send(message.encode())

    elif client["protocol"] == "UDP":
        client["socket"].sendto(
            message.encode(),
            client["address"]
        )


def process_message(sender, message):
    parts = message.split("|", 2)

    if len(parts) != 3:
        print("[ROUTER] Неверный формат сообщения.")
        return

    target = parts[0]
    priority = parts[1]
    text = parts[2]

    if target not in clients:
        print(f"[ROUTER] Получатель {target} не найден.")
        return

    sender_info = clients[sender]
    target_info = clients[target]

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

    if priority == "HIGH":
        print("[ROUTER] Приоритетное сообщение.")

    if sender_info["subnet"] != target_info["subnet"]:
        print("[ROUTER] Выполняется межсетевой маршрут.")

    if sender_info["protocol"] != target_info["protocol"]:
        print("[ROUTER] Выполняется преобразование протокола.")

    result = f"[{priority}] {sender} → {target}: {text}"

    send_to_client(target, result)


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

            client_socket.send(
                "Регистрация выполнена.".encode()
            )

        while True:
            data = client_socket.recv(1024)

            if not data:
                break

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
    tcp_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    tcp_socket.bind((HOST, TCP_PORT))
    tcp_socket.listen()

    print(
        f"[ROUTER] TCP ожидает подключения: "
        f"{HOST}:{TCP_PORT}"
    )

    while True:
        client_socket, client_address = tcp_socket.accept()

        thread = threading.Thread(
            target=handle_tcp_client,
            args=(client_socket, client_address)
        )

        thread.start()


def udp_server():
    udp_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    udp_socket.bind((HOST, UDP_PORT))

    print(
        f"[ROUTER] UDP ожидает сообщения: "
        f"{HOST}:{UDP_PORT}"
    )

    while True:
        data, client_address = udp_socket.recvfrom(1024)

        message = data.decode()

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

            udp_socket.sendto(
                "Регистрация выполнена.".encode(),
                client_address
            )

        else:
            sender = None

            for name, client in connected_clients.items():
                if (
                    client["protocol"] == "UDP"
                    and client["address"] == client_address
                ):
                    sender = name

            if sender:
                process_message(sender, message)


tcp_thread = threading.Thread(target=tcp_server)
udp_thread = threading.Thread(target=udp_server)

tcp_thread.start()
udp_thread.start()