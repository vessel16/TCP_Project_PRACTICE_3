import socket
import os

HOST = "127.0.0.1"
PORT = 6000
NAME = "Client4"  # Меняйте для каждого клиента

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.sendto(f"REGISTER|{NAME}".encode(), (HOST, PORT))
data, address = client_socket.recvfrom(1024)
print(data.decode())

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
            client_socket.sendto(header + file_data, (HOST, PORT))
            print(f"Файл {filename} отправлен (упрощённо).")
        else:
            print("Файл не найден.")
    else:
        target = input("Получатель: ")
        priority = input("Приоритет (1-8): ").strip()
        message = input("Сообщение: ")
        
        data = f"{target}|{priority}|{message}"
        client_socket.sendto(data.encode(), (HOST, PORT))
        
        if message.lower() == "exit":
            break

client_socket.close()