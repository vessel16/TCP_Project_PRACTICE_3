import socket


HOST = "127.0.0.1"
PORT = 5000

NAME = "Client1"


client_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

client_socket.connect((HOST, PORT))

client_socket.send(
    f"REGISTER|{NAME}".encode()
)

response = client_socket.recv(1024)
print(response.decode())


while True:
    target = input("Получатель: ")
    priority = input("Приоритет (NORMAL/HIGH): ").upper()
    message = input("Сообщение: ")

    data = f"{target}|{priority}|{message}"

    client_socket.send(data.encode())

    if message.lower() == "exit":
        break


client_socket.close()