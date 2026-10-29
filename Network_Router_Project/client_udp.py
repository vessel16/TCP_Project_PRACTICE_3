import socket
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto import xor_encrypt, xor_decrypt

NAME = sys.argv[1] if len(sys.argv) > 1 else "Client4"
MY_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 7004
HOST = "127.0.0.1"
PORT = 6000

def receiver(key):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, MY_PORT))
    while True:
        data, _ = s.recvfrom(4096)
        raw = data.decode()
        parts = raw.split("|")
        if len(parts) >= 8 and parts[0] == "SRP":
            try:
                text = xor_decrypt(parts[7], key)
                print(f"\n[{NAME}] Получено и расшифровано: {text}")
            except Exception as e:
                print(f"\n[{NAME}] Ошибка расшифровки: {e}")

if __name__ == "__main__":
    key = input("Введите ключ шифрования (например, 12345): ")
    threading.Thread(target=receiver, args=(key,), daemon=True).start()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(f"REGISTER|{NAME}".encode(), (HOST, PORT))
    
    while True:
        target = input("\nПолучатель: ")
        message = input("Сообщение: ")
        
        enc_hex = xor_encrypt(message, key)
        packet = f"SRP|DATA|{NAME}|{target}|UDP|4|1|{enc_hex}"
        
        client_socket.sendto(packet.encode(), (HOST, PORT))
        print(f"[{NAME}] Зашифровано: {enc_hex[:20]}...")

        if message.lower() == "exit":
            break