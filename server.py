import socket

HOST = "127.0.0.1"
PORT = 5000

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))

server_socket.listen(1)
print("Сервер запущен.")
print(f"Ожидание подключения по адресу {HOST}:{PORT}...")

client_socket, client_address = server_socket.accept()
print("Клиент подключён.")
print('Добро пожаловать на сервер!')
print("Адрес клиента:", client_address)

while True:
    data = client_socket.recv(1024)
    if not data:
        print("Клиент отключился.")
        break
    message = data.decode()
    print("Сообщение от клиента:", message)
    if message.lower() == "exit":
        print("Клиент завершил работу.")
        client_socket.send("Соединение завершено.".encode())
        break

    response = "Сервер получил сообщение: " + message
    client_socket.send(response.encode())


print("Сервер получил:", message)
client_socket.close()
server_socket.close()
print("Сервер завершил работу.")









