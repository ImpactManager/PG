# network.py

import socket
import threading
import json
import random
import string
import time # Додаємо імпорт time

# --- Конфігурація мережі ---
HEADER_SIZE = 64 # Розмір заголовка для довжини повідомлення
PORT = 12345
HOST = "0.0.0.0" # Слухаємо всі доступні інтерфейси

# --- Глобальні змінні для сервера (використовуються GameServer) ---
game_server = None
clients = {} # {client_socket: {"id": "...", "nickname": "...", "character": "...", "addr": ("ip", port)}}
current_lobby_code = None # Код поточного лобі (для відображення в GUI)

# --- Глобальні змінні для клієнта (використовуються GameClient) ---
game_client = None
connected_players_info = [] # Список для GUI: [{'id': 'client_1', 'nickname': 'Bob', 'character': 'Не обрано'}]
network_status_message = "" # Для відображення статусу мережі в GUI

# --- Функції для мережевого обміну ---
def send_json(sock, data):
    """
    Надсилає словник у форматі JSON через сокет.
    Попередньо надсилає довжину JSON-повідомлення.
    """
    try:
        json_data = json.dumps(data).encode('utf-8')
        message_length = len(json_data)
        send_length = str(message_length).encode('utf-8')
        send_length += b' ' * (HEADER_SIZE - len(send_length)) # Заповнюємо пробілами до HEADER_SIZE

        sock.sendall(send_length) # Надсилаємо довжину
        sock.sendall(json_data)   # Надсилаємо саме JSON-повідомлення
        # print(f"DEBUG SEND: Sent {data.get('type')} message of length {message_length} to {sock.getpeername()}") # Може бути занадто багато виводів
        return True
    except Exception as e:
        peername = "N/A"
        try: peername = sock.getpeername()
        except: pass
        print(f"ERROR SEND: Failed to send data to {peername}: {e}")
        return False

def receive_json(sock):
    """
    Отримує повідомлення у форматі JSON через сокет.
    Спочатку отримує довжину, потім саме повідомлення.
    """
    try:
        sock.settimeout(1.0) # Встановлюємо таймаут для recv, щоб потік не зависав назавжди
        
        # Отримання довжини повідомлення
        length_prefix = sock.recv(HEADER_SIZE)
        if not length_prefix:
            # Це означає, що інша сторона закрила з'єднання
            # print("DEBUG: receive_json - No length prefix received, connection closed by peer.")
            return None 
        
        message_length = int(length_prefix.strip()) # Перетворюємо байти на int, видаляючи пробіли
        
        # Отримання самого повідомлення частинами
        chunks = []
        bytes_recd = 0
        while bytes_recd < message_length:
            chunk = sock.recv(min(message_length - bytes_recd, 4096)) # Отримуємо по 4096 байт або залишок
            if chunk == b'':
                # З'єднання розірвано до отримання повного повідомлення
                print("DEBUG: receive_json - Socket connection broken before full message received.")
                return None 
            chunks.append(chunk)
            bytes_recd += len(chunk)
        
        full_data = b''.join(chunks)
        return json.loads(full_data.decode('utf-8'))
    except socket.timeout:
        # Це нормальна ситуація для потоків, які слухають, вони просто продовжать чекати
        # print("DEBUG: receive_json - Socket timeout, no data received.")
        return "TIMEOUT" # Спеціальне значення для обробки таймауту
    except json.JSONDecodeError as e:
        # Помилка декодування JSON (можливо, отримано пошкоджені дані)
        print(f"ERROR: receive_json - JSON decode error: {e}, Data: {full_data.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        # Будь-яка інша непередбачена помилка під час прийому
        print(f"ERROR: receive_json - Unexpected error during receive: {e}")
        return None

# --- Клас Сервера ---
class GameServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.client_id_counter = 0
        self.clients_lock = threading.Lock() # Для безпечного доступу до словника clients з різних потоків
        self.lobby_code = self._generate_lobby_code()
        
        global current_lobby_code
        current_lobby_code = self.lobby_code # Зберігаємо код лобі для GUI
        
        print(f"DEBUG SERVER: GameServer initialized. Lobby Code: {self.lobby_code}")

    def _generate_lobby_code(self, length=6):
        """Генерує випадковий буквено-цифровий код лобі."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def start(self):
        """Запускає сервер, починає слухати підключення."""
        global network_status_message
        if self.running:
            print("DEBUG SERVER: Server already running.")
            return False
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Дозволяє повторне використання адреси, щоб уникнути "Address already in use"
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            self.running = True
            
            print(f"DEBUG SERVER: Server listening on {self.host}:{self.port}. Lobby Code: {self.lobby_code}")
            network_status_message = f"Сервер запущено. Код лобі: {self.lobby_code}"
            
            # Запускаємо окремий потік для прийому нових підключень
            threading.Thread(target=self._accept_connections, daemon=True).start()
            print("DEBUG SERVER: Accept connections thread started.")
            return True
        except Exception as e:
            print(f"ERROR SERVER: Failed to start server: {e}")
            network_status_message = f"Помилка запуску сервера: {e}"
            self.stop() # Зупиняємо, якщо виникла помилка при запуску
            return False

    def stop(self):
        """Зупиняє сервер і закриває всі клієнтські з'єднання."""
        global network_status_message
        if not self.running:
            print("DEBUG SERVER: stop() called but server not running.")
            return
        
        print("DEBUG SERVER: Stopping server...")
        self.running = False # Встановлюємо флаг зупинки
        
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR) # Закриваємо обидва напрямки
                self.server_socket.close()
                print("DEBUG SERVER: Server socket closed.")
            except Exception as e:
                print(f"ERROR SERVER: Error closing server socket: {e}")
        
        # Закриваємо всі активні клієнтські з'єднання
        with self.clients_lock:
            # Створюємо копію ключів, бо словник буде змінюватися під час ітерації
            for client_sock in list(clients.keys()):
                try:
                    client_sock.shutdown(socket.SHUT_RDWR)
                    client_sock.close()
                    print(f"DEBUG SERVER: Client socket {clients[client_sock].get('id')} closed during server stop.")
                except Exception as e:
                    print(f"ERROR SERVER: Error closing client socket during stop: {e}")
            clients.clear() # Очищаємо словник клієнтів
            print("DEBUG SERVER: All client sockets cleared.")
            
        network_status_message = "Сервер зупинено."
        self._update_connected_players_info() # Оновлюємо GUI
        print("DEBUG SERVER: Server stopped successfully.")


    def _accept_connections(self):
        """Приймає нові підключення від клієнтів у нескінченному циклі."""
        print("DEBUG SERVER: _accept_connections thread running.")
        while self.running: # Продовжуємо працювати, поки сервер запущено
            try:
                # Встановлюємо невеликий таймаут для accept, щоб потік не блокувався назавжди
                # і міг перевіряти self.running
                self.server_socket.settimeout(0.5) 
                conn, addr = self.server_socket.accept() # Чекаємо на нове підключення
                
                self.client_id_counter += 1
                client_id = f"client_{self.client_id_counter}"
                
                with self.clients_lock:
                    clients[conn] = {"id": client_id, "nickname": "Невідомий", "character": "Не обрано", "addr": addr}
                print(f"Підключено нового клієнта: {addr} (ID: {client_id})")
                
                # Надсилаємо новому клієнту його унікальний ID
                send_json(conn, {"type": "CONNECTED", "clientId": client_id})
                print(f"DEBUG SERVER: Sent CONNECTED message to {client_id}")

                # Запускаємо окремий потік для обробки цього конкретного клієнта
                threading.Thread(target=self._handle_client, args=(conn, client_id, addr), daemon=True).start()
                print(f"DEBUG SERVER: Started handle_client thread for {client_id}")

            except socket.timeout:
                pass # Таймаут, продовжуємо чекати на наступній ітерації
            except Exception as e:
                if self.running: # Якщо помилка не через зупинку сервера
                    print(f"ERROR SERVER: Error accepting connection: {e}")
                break # Виходимо з циклу при фатальній помилці
        print("DEBUG SERVER: _accept_connections thread exited.")


    def _handle_client(self, conn, client_id, addr):
        """
        Обробляє повідомлення від конкретного клієнта в окремому потоці.
        """
        print(f"DEBUG SERVER: _handle_client thread started for {client_id}")
        connected = True
        try:
            while connected and self.running: # Продовжуємо працювати, поки клієнт підключений і сервер запущено
                data = receive_json(conn)
                print(f"DEBUG SERVER: Received raw data from {client_id}: {data}")

                if data is None: # Клієнт відключився або помилка
                    print(f"DEBUG SERVER: Client {client_id} disconnected (receive_json returned None).")
                    connected = False
                elif data == "TIMEOUT":
                    # print(f"DEBUG SERVER: Timeout for client {client_id}, still connected.") # Може бути занадто багато виводів
                    continue # Продовжуємо чекати
                else:
                    # Обробка отриманого повідомлення
                    if data.get("type") == "PLAYER_INFO":
                        nickname = data.get("nickname", "Невідомий")
                        character = data.get("character", "Не обрано")
                        
                        with self.clients_lock: # Захищаємо доступ до словника clients
                            if conn in clients:
                                clients[conn]["nickname"] = nickname
                                clients[conn]["character"] = character
                                print(f"Отримано інфо від {client_id}: {nickname}, {character}")
                        
                        self._update_connected_players_info() # Оновлюємо дані для GUI
                        self._broadcast_lobby_update() # Надсилаємо оновлення всім гравцям
                    # Додайте інші типи повідомлень від клієнтів (наприклад, вибір персонажа, готовність)
                    # elif data.get("type") == "CHARACTER_SELECT":
                    #    ...
                    print(f"DEBUG SERVER: Processed data from {client_id}.")

        except Exception as e:
            # Це дуже важливий блок: він ловить будь-які неочікувані помилки в потоці
            print(f"CRITICAL ERROR SERVER: Error handling client {client_id} ({addr}): {e}")
            connected = False # Позначаємо клієнта як відключеного
        finally:
            # Цей блок виконується завжди, незалежно від того, чи була помилка, чи клієнт відключився сам
            print(f"DEBUG SERVER: _handle_client thread for {client_id} exiting.")
            with self.clients_lock:
                if conn in clients:
                    del clients[conn] # Видаляємо клієнта зі списку
                    print(f"Клієнт {client_id} ({addr}) відключився.")
                try:
                    conn.shutdown(socket.SHUT_RDWR) # Надійно закриваємо з'єднання
                    conn.close()
                    print(f"DEBUG SERVER: Socket for {client_id} closed in finally block.")
                except OSError as e: # Ловимо помилки, якщо сокет вже був закритий
                    print(f"DEBUG SERVER: Error during socket close for {client_id} in finally block (already closed?): {e}")
            self._update_connected_players_info() # Оновлюємо GUI після відключення
            self._broadcast_lobby_update() # Повідомляємо інших гравців про зміни в лобі

    def _broadcast_lobby_update(self):
        """Надсилає оновлений список гравців усім підключеним клієнтам."""
        with self.clients_lock:
            players_data = [{'id': c["id"], 'nickname': c["nickname"], 'character': c["character"]} for c in clients.values()]
        
        global connected_players_info
        connected_players_info = players_data # Оновлюємо глобальний список для GUI сервера
        print(f"Оновлено список гравців: {connected_players_info}")

        message = {"type": "LOBBY_UPDATE", "players": players_data}
        with self.clients_lock:
            for client_sock, client_data in clients.items():
                print(f"DEBUG SERVER: Broadcasting LOBBY_UPDATE to {client_data['id']}")
                send_json(client_sock, message)
                # time.sleep(0.01) # Розкоментуйте для тестування, чи допомагає невелика затримка
        print("DEBUG SERVER: LOBBY_UPDATE broadcast complete.")

    def _update_connected_players_info(self):
        """Оновлює глобальний список гравців для відображення на GUI сервера."""
        with self.clients_lock:
            global connected_players_info
            connected_players_info = [{'id': c["id"], 'nickname': c["nickname"], 'character': c["character"]} for c in clients.values()]


# --- Клас Клієнта ---
class GameClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None
        self.running = False
        self.client_id = None
        print(f"DEBUG CLIENT: GameClient initialized with host={host}, port={port}")

    def connect(self, nickname, lobby_code_to_join=None):
        """
        Підключається до сервера та надсилає інформацію про гравця.
        """
        global network_status_message
        print(f"DEBUG CLIENT: Attempting to connect to {self.host}:{self.port} for lobby {lobby_code_to_join}...")
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("DEBUG CLIENT: Socket created. Connecting to {self.host}:{self.port}...")
            self.client_socket.connect((self.host, self.port))
            self.running = True
            print("DEBUG CLIENT: Successfully connected to server.")

            # *** ЗМІНА ТУТ: Спочатку отримуємо CONNECTED, потім запускаємо слухача ***

            # Чекаємо на повідомлення CONNECTED від сервера, щоб отримати свій client_id
            initial_data = receive_json(self.client_socket)
            
            if initial_data is None:
                print("DEBUG CLIENT: Initial connection: Server disconnected or error during initial receive.")
                self.stop()
                network_status_message = "Помилка підключення: сервер відключився під час ініціалізації."
                return False
            elif initial_data == "TIMEOUT":
                print("DEBUG CLIENT: Initial connection: Timeout waiting for CONNECTED message.")
                self.stop()
                network_status_message = "Помилка підключення: таймаут очікування відповіді від сервера."
                return False
            elif isinstance(initial_data, dict) and initial_data.get("type") == "CONNECTED":
                self.client_id = initial_data.get("clientId")
                print(f"DEBUG CLIENT: Received Client ID from server: {self.client_id}")
            else:
                # Якщо отримали щось інше, ніж очікуваний словник CONNECTED
                print(f"DEBUG CLIENT: Did not receive expected CONNECTED message from server. Received: {initial_data}")
                self.stop()
                network_status_message = "Помилка підключення: не отримано очікуваний ID від сервера."
                return False

            # Надсилаємо інформацію про гравця після отримання ID
            player_info_message = {
                "type": "PLAYER_INFO",
                "clientId": self.client_id,
                "nickname": nickname,
                "character": "Не обрано" # Поки що персонаж не обирається
            }
            if not send_json(self.client_socket, player_info_message):
                print("DEBUG CLIENT: Failed to send PLAYER_INFO.")
                self.stop()
                network_status_message = "Помилка підключення: не вдалося надіслати дані гравця."
                return False

            # *** ЗМІНА ТУТ: ТІЛЬКИ ТЕПЕР запускаємо потік для прослуховування ***
            threading.Thread(target=self._listen_for_messages, daemon=True).start()
            print("DEBUG CLIENT: Listener thread started (after initial handshake).")


            network_status_message = "Підключено до лобі. Очікування інших гравців..."
            print("DEBUG CLIENT: Client connect successful.")
            return True
        except ConnectionRefusedError:
            print(f"DEBUG CLIENT: Connection refused. Server not running or wrong address/port.")
            network_status_message = "Відмова у підключенні. Сервер не запущений або невірний код лобі/IP."
        except Exception as e:
            print(f"DEBUG CLIENT: An error occurred during connection: {e}")
            network_status_message = f"Помилка підключення: {e}"
        self.stop() # Забезпечуємо зупинку, якщо підключення не вдалося
        return False

    def _listen_for_messages(self):
        """
        Постійно слухає повідомлення від сервера.
        """
        print("DEBUG CLIENT: Listener thread started. Waiting for data...")
        while self.running:
            try:
                data = receive_json(self.client_socket)
                # print(f"DEBUG CLIENT: Received raw data from server: {data}") # Може бути занадто багато виводів

                if data is None:
                    print("DEBUG CLIENT: Server disconnected or no data received (data is None).")
                    self.stop() # Зупиняємо клієнт, якщо сервер відключився
                    break
                elif data == "TIMEOUT":
                    continue # Просто продовжуємо чекати
                else:
                    # Обробка отриманого повідомлення від сервера
                    if data.get("type") == "LOBBY_UPDATE":
                        players = data.get("players", [])
                        global connected_players_info
                        connected_players_info = players
                        print(f"DEBUG CLIENT: Received LOBBY_UPDATE from server: {connected_players_info}")
                    # Додайте інші типи повідомлень від сервера (наприклад, START_GAME)
                    # elif data.get("type") == "START_GAME":
                    #    ...
                    print(f"DEBUG CLIENT: Processed server message: {data.get('type')}")

            except Exception as e:
                print(f"CRITICAL ERROR CLIENT: Error in listener thread: {e}")
                self.stop()
                break
        print("DEBUG CLIENT: Listener thread loop exited.")


    def send_message(self, message):
        """
        Надсилає повідомлення на сервер (не використовується GUI напряму, але може бути корисно).
        """
        if self.client_socket and self.running:
            return send_json(self.client_socket, message)
        return False

    def stop(self):
        """
        Зупиняє клієнт та закриває з'єднання.
        """
        global network_status_message
        if not self.running:
            print("DEBUG CLIENT: stop() called but client not running.")
            return
        
        print("DEBUG CLIENT: Stopping client...")
        self.running = False # Встановлюємо флаг зупинки
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR) # Закриваємо обидва напрямки
                self.client_socket.close()
                print("DEBUG CLIENT: Client socket closed.")
            except Exception as e:
                print(f"ERROR CLIENT: Error closing client socket: {e}")
        network_status_message = "Відключено від лобі."
        global connected_players_info
        connected_players_info = [] # Очищаємо список гравців
        print("DEBUG CLIENT: Client stopped successfully.")