import socket


HOST = "127.0.0.1"
PORT = 6000

NAME = "Client4"


client_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

client_socket.sendto(
    f"REGISTER|{NAME}".encode(),
    (HOST, PORT)
)

data, address = client_socket.recvfrom(1024)
print(data.decode())


while True:
    target = input("Получатель: ")
    priority = input("Приоритет (NORMAL/HIGH): ").upper()
    message = input("Сообщение: ")

    data = f"{target}|{priority}|{message}"

    client_socket.sendto(
        data.encode(),
        (HOST, PORT)
    )

    if message.lower() == "exit":
        break


client_socket.close()