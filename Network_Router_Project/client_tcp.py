import socket
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto import xor_encrypt, xor_decrypt

# Позволяем запускать: python client_tcp.py Client1 7001
NAME = sys.argv[1] if len(sys.argv) > 1 else "Client1"
MY_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 7001

HOST = "127.0.0.1"
PORT = 5000 # Порт Router1 (по умолчанию для TCP-клиентов)

def receiver(key):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, MY_PORT))
    s.listen(5)
    while True:
        conn, _ = s.accept()
        raw = conn.recv(4096).decode()
        conn.close()
        # Ожидаем формат: SRP|DATA|Source|Target|Protocol|Priority|1|HEX
        parts = raw.split("|")
        if len(parts) >= 8 and parts[0] == "SRP":
            try:
                text = xor_decrypt(parts[7], key)
                print(f"\n[{NAME}] Получено и расшифровано: {text}")
            except Exception as e:
                print(f"\n[{NAME}] Ошибка расшифровки (неверный ключ?): {e}")

if __name__ == "__main__":
    key = input("Введите ключ шифрования (например, 12345): ")
    
    # Запускаем приемник в фоне
    threading.Thread(target=receiver, args=(key,), daemon=True).start()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    client_socket.send(f"REGISTER|{NAME}".encode())
    response = client_socket.recv(1024)
    print(response.decode())

    while True:
        target = input("\nПолучатель: ")
        message = input("Сообщение: ")
        
        # Шифруем сообщение
        enc_hex = xor_encrypt(message, key)
        
        # Формируем пакет по протоколу SRP
        packet = f"SRP|DATA|{NAME}|{target}|TCP|4|1|{enc_hex}"
        
        client_socket.send(packet.encode())
        print(f"[{NAME}] Зашифровано: {enc_hex[:20]}...")

        if message.lower() == "exit":
            break
    client_socket.close()