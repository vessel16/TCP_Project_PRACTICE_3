import socket
import os

HOST = "127.0.0.1"
PORT = 5000
NAME = "Client7"  # Меняйте для каждого клиента

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
client_socket.send(f"REGISTER|{NAME}".encode())
response = client_socket.recv(1024)
print(response.decode())

while True:
    print("\nВведите 'FILE' для отправки файла или Enter для обычного сообщения.")
    mode = input("Режим (MSG/FILE): ").strip().upper()
    
    if mode == "FILE":
        target = input("Получатель: ")
        priority = input("Приоритет (1-8): ").strip()
        filepath = input("Путь к файлу: ").strip()
        
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                file_data = f.read()
            filename = os.path.basename(filepath)
            header = f"FILE|{target}|{filename}|{len(file_data)}\n".encode()
            client_socket.send(header + file_data)
            print(f"Файл {filename} отправлен.")
        else:
            print("Файл не найден.")
    else:
        target = input("Получатель: ")
        priority = input("Приоритет (1-8): ").strip()
        message = input("Сообщение: ")
        
        data = f"{target}|{priority}|{message}"
        client_socket.send(data.encode())
        
        if message.lower() == "exit":
            break

client_socket.close()