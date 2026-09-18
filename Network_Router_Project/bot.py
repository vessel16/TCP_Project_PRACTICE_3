import socket
import time
import random

HOST = "127.0.0.1"
PORT = 5000
NAME = "Bot1"

TARGETS = ["Client1", "Client2", "Client3", "Client4", "Client5", "Client6", "Client7"]
MESSAGES = [
    "Автоматическое уведомление 1",
    "Проверка связи",
    "Срочное сообщение от бота!",
    "Плановое задание выполнено",
    "Внимание: обнаружена аномалия",
]

def send_message(target, priority, message):
    try:
        bot_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bot_socket.connect((HOST, PORT))
        bot_socket.send(f"REGISTER|{NAME}".encode())
        response = bot_socket.recv(1024)
        
        data = f"{target}|{priority}|{message}"
        bot_socket.send(data.encode())
        
        bot_socket.close()
    except Exception as e:
        print(f"[BOT] Ошибка: {e}")

def bot_loop():
    while True:
        delay = random.randint(5, 15)
        time.sleep(delay)
        
        target = random.choice(TARGETS)
        priority = random.choice([1, 3, 5, 8])
        message = random.choice(MESSAGES)
        
        print(f"[BOT] Отправка сообщения для {target} с приоритетом {priority}")
        send_message(target, priority, message)

if __name__ == "__main__":
    print(f"[BOT] Бот {NAME} запущен. Отправка сообщений каждые 5-15 секунд.")
    bot_loop()