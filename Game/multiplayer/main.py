import pygame
import sys
import os
import time
import network
import pyperclip
import json

# Імпорт STORIES з окремого файлу
from data.stories import STORIES

# --- Налаштування Pygame ---
pygame.init()
pygame.mixer.init()
pygame.key.set_repeat(200, 50)

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Кооперативна Візуальна Новела")

# --- Кольори ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
HOVER_COLOR = (51, 51, 51)
RED = (255, 0, 0)
GREEN = (0, 150, 0)
BLUE = (0, 0, 255)
TEXT_BOX_COLOR = (0, 0, 0, 180) # Напівпрозорий чорний для текстового поля

# Напівпрозорі кольори для фонів смуг
TRANSPARENT_BLACK = (0, 0, 0, 128)  # Чорний з 50% прозорістю

# Флаг що текст закінчився і відобразити появу кнопок вибору
text_display_complete = False

# --- Шляхи до асетів ---
ASSETS_DIR = "Game/assets"
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
DATA_DIR = "Game/data"
STORIES_DIR = "Game/stories"
STORY_ASSETS_DIR = os.path.join(IMAGES_DIR, "story_assets")
STORY_AUDIO_DIR = os.path.join(AUDIO_DIR, "story_audio") # <-- Додано шлях для аудіо історій

MENU_BACKGROUND_PATH = os.path.join(IMAGES_DIR, "main_menu.png")
CUSTOM_FONT_PATH = os.path.join(FONTS_DIR, "Attentica_4F_UltraLight.otf")
TEXT_FONT_PATH = os.path.join(FONTS_DIR, "PixelGosub.ttf")
MENU_MUSIC_PATH = os.path.join(AUDIO_DIR, "dark-ambient-music-312290_menu.mp3")

HOVER_SOUND_PATH = os.path.join(AUDIO_DIR, "button_hover.mp3")
CLICK_SOUND_PATH = os.path.join(AUDIO_DIR, "click-button-140881.mp3")

# Перевірка наявності файлів асетів (можна залишити)
if not os.path.exists(MENU_BACKGROUND_PATH):
    print(f"Помилка: Фонове зображення меню не знайдено за шляхом: {MENU_BACKGROUND_PATH}")
if not os.path.exists(CUSTOM_FONT_PATH):
    print(f"Помилка: Спеціальний шрифт не знайдено за шляхом: {CUSTOM_FONT_PATH}")
if not os.path.exists(MENU_MUSIC_PATH):
    print(f"Помилка: Музика меню не знайдено за шляхом: {MENU_MUSIC_PATH}")
if not os.path.exists(HOVER_SOUND_PATH):
    print(f"Помилка: Звук наведення не знайдено за шляхом: {HOVER_SOUND_PATH}")
if not os.path.exists(CLICK_SOUND_PATH):
    print(f"Помилка: Звук натискання не знайдено за шляхом: {CLICK_SOUND_PATH}")

# --- Завантаження асетів ---
try:
    MENU_BACKGROUND = pygame.image.load(MENU_BACKGROUND_PATH).convert()
    MENU_BACKGROUND = pygame.transform.scale(MENU_BACKGROUND, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error as e:
    print(f"Не вдалося завантажити фонове зображення меню: {e}")
    MENU_BACKGROUND = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    MENU_BACKGROUND.fill(BLACK)

try:
    CUSTOM_FONT = pygame.font.Font(CUSTOM_FONT_PATH, 40)
    BUTTON_FONT = pygame.font.Font(CUSTOM_FONT_PATH, 30)
    TEXT_INPUT_FONT = pygame.font.Font(CUSTOM_FONT_PATH, 25)
    GAME_TEXT_FONT = pygame.font.SysFont("Arial", 30)
    CHARACTER_NAME_FONT = pygame.font.Font(CUSTOM_FONT_PATH, 32)
except FileNotFoundError:
    print(f"Не вдалося завантажити спеціальний шрифт. Використано системний шрифт.")
    CUSTOM_FONT = pygame.font.SysFont("Arial", 40)
    BUTTON_FONT = pygame.font.SysFont("Arial", 30)
    TEXT_INPUT_FONT = pygame.font.SysFont("Arial", 25)
    GAME_TEXT_FONT = pygame.font.SysFont("Arial", 28)
    CHARACTER_NAME_FONT = pygame.font.SysFont("Arial", 32)


try:
    HOVER_SOUND = pygame.mixer.Sound(HOVER_SOUND_PATH)
    CLICK_SOUND = pygame.mixer.Sound(CLICK_SOUND_PATH)
except pygame.error as e:
    print(f"Не вдалося завантажити звукові ефекти: {e}")
    HOVER_SOUND = None
    CLICK_SOUND = None

# --- Глобальні змінні стану гри ---
class GameState:
    MENU = 0
    NEW_GAME_MODE_SELECT = 1
    LOBBY_MAIN = 2
    LOBBY_CREATE = 3
    LOBBY_JOIN = 4
    SOLO_MODE_STORY_SELECT = 5
    LOBBY_MODE_STORY_SELECT = 6
    GAMEPLAY = 7

current_state = GameState.MENU

player_nickname = ""
active_input_box = None 

copied_message_timer = 0
COPIED_MESSAGE_DURATION = 1.5

selected_story_id = None 

# --- ЗМІННІ ДЛЯ ГЕЙМПЛЕЮ ---
current_story_data = None
current_scene_id = None
current_background = None
current_characters = {}
current_text = ""
current_choices = []
text_display_index = 0
last_text_update_time = 0
TEXT_SPEED = 0.065
auto_advance_timer = 0
AUTO_ADVANCE_DURATION = 2

current_voice_over = None # <-- Додано: об'єкт Sound для поточної озвучки
current_background_music_path = None # <-- Додано: шлях до поточної фонової музики


# --- Клас Button (text_color за замовчуванням BLACK) ---
class Button:
    def __init__(self, text, x, y, width, height, action=None, text_color=BLACK, hover_color=HOVER_COLOR, font=BUTTON_FONT,
                 hover_sound=None, click_sound=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.text_color = text_color
        self.hover_color = hover_color
        self.font = font
        self.hovered = False
        self.last_hover_state = False

        self.hover_sound = hover_sound
        self.click_sound = click_sound

    def draw(self, surface):
        current_text_color = self.hover_color if self.hovered else self.text_color
        text_surface = self.font.render(self.text, True, current_text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            if self.hovered and not self.last_hover_state and self.hover_sound:
                self.hover_sound.play()
            self.last_hover_state = self.hovered

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.click_sound:
                    self.click_sound.play()
                if self.action:
                    self.action()
                return True
        return False

# --- Клас для поля вводу тексту (ЗМІНЕНО: курсор, прозорий фон, чорна рамка) ---
class TextInputBox:
    def __init__(self, x, y, w, h, text='', font=TEXT_INPUT_FONT, border_color=GRAY, bg_color=(0, 0, 0, 0), text_color=BLACK): 
        self.rect = pygame.Rect(x, y, w, h)
        self.border_color = border_color
        self.bg_color = bg_color
        self.text = text
        self.font = font
        self.text_color = text_color
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = time.time()
        self.cursor_blink_rate = 0.5 

        self.surface = pygame.Surface((w, h), pygame.SRCALPHA)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if not self.active: 
                    self.cursor_visible = True 
                    self.cursor_timer = time.time()
                self.active = True 
            else:
                self.active = False
        
        if event.type == pygame.KEYDOWN and self.active:
            self.cursor_visible = True 
            self.cursor_timer = time.time() 
            
            if event.key == pygame.K_RETURN:
                print(f"Введено: {self.text}")
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL or pygame.key.get_mods() & pygame.KMOD_GUI): 
                try:
                    pasted_text = pyperclip.paste()
                    self.text += pasted_text
                    if self.font.size(self.text)[0] > self.rect.width - 10:
                        self.text = self.text[:int(len(self.text) * (self.rect.width - 10) / self.font.size(self.text)[0])] 
                except pyperclip.PyperclipException as e:
                    print(f"Не вдалося вставити з буфера обміну: {e}")
            else:
                if event.unicode.isprintable():
                    self.text += event.unicode
                if self.font.size(self.text)[0] > self.rect.width - 10:
                    self.text = self.text[:-1]

    def draw(self, surface):
        self.surface.fill(self.bg_color)
        surface.blit(self.surface, self.rect.topleft)

        pygame.draw.rect(surface, self.border_color, self.rect, 2, border_radius=5)

        text_surface = self.font.render(self.text, True, self.text_color)
        surface.blit(text_surface, (self.rect.x + 5, self.rect.y + (self.rect.height - text_surface.get_height()) // 2))

        if self.active:
            if time.time() - self.cursor_timer > self.cursor_blink_rate:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = time.time()
            
            if self.cursor_visible:
                text_width = self.font.size(self.text)[0]
                cursor_x = self.rect.x + 5 + text_width
                cursor_y_top = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
                cursor_y_bottom = cursor_y_top + text_surface.get_height()
                pygame.draw.line(surface, self.text_color, (cursor_x, cursor_y_top), (cursor_x, cursor_y_bottom), 2)


# --- Функції для завантаження та відображення даних історії ---
def load_story(story_id):
    """Завантажує дані історії з JSON файлу."""
    global current_story_data, current_scene_id

    story_info = STORIES.get(story_id)
    if not story_info:
        print(f"Помилка: Історія з ID '{story_id}' не знайдена.")
        return False

    story_path = story_info['start_data_path']
    full_path = os.path.join(STORIES_DIR, os.path.basename(story_path))

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            current_story_data = json.load(f)
        current_scene_id = current_story_data.get("start_scene")
        print(f"Історія '{story_info['title']}' завантажена. Початкова сцена: {current_scene_id}")
        return True
    except FileNotFoundError:
        print(f"Помилка: Файл історії не знайдено за шляхом: {full_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"Помилка декодування JSON файлу історії: {e}")
        return False
    except Exception as e:
        print(f"Невідома помилка при завантаженні історії: {e}")
        return False

def load_scene(scene_id):
    """Завантажує та ініціалізує елементи поточної сцени."""
    global current_scene_id, current_background, current_characters, current_text, current_choices, text_display_index, last_text_update_time, auto_advance_timer
    global current_voice_over, current_background_music_path # <-- Додано
    text_display_complete = False
    if not current_story_data or scene_id not in current_story_data["scenes"]:
        print(f"Помилка: Сцена '{scene_id}' не знайдена в поточній історії.")
        set_game_state(GameState.MENU)
        return

    if scene_id == "menu_return":
        set_game_state(GameState.MENU)
        return

    current_scene_id = scene_id
    scene_data = current_story_data["scenes"][scene_id]
    print(f"Завантажено сцену: {current_scene_id} - '{scene_data.get('text', 'Без тексту')}'")

    # Завантаження фону
    background_image_path = scene_data.get("background")
    current_background = None
    if background_image_path:
        full_bg_path = os.path.join(STORY_ASSETS_DIR, background_image_path)
        try:
            temp_bg = pygame.image.load(full_bg_path).convert()
            current_background = pygame.transform.scale(temp_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"Помилка завантаження фону '{full_bg_path}': {e}")
        except FileNotFoundError:
            print(f"Фон '{full_bg_path}' не знайдено. Буде чорний фон.")

    # Завантаження та відтворення фонової музики сцени
    new_music_path = scene_data.get("background_music")
    if new_music_path and new_music_path != current_background_music_path:
        full_music_path = os.path.join(STORY_AUDIO_DIR, new_music_path)
        if os.path.exists(full_music_path):
            try:
                pygame.mixer.music.load(full_music_path)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1) # Відтворення у циклі
                current_background_music_path = new_music_path
                print(f"Відтворюється фонова музика: {new_music_path}")
            except pygame.error as e:
                print(f"Помилка відтворення музики фону '{full_music_path}': {e}")
        else:
            print(f"Фонова музика '{full_music_path}' не знайдена.")
            pygame.mixer.music.stop() # Зупиняємо, якщо файл не знайдено
            current_background_music_path = None
    elif not new_music_path and current_background_music_path: # Якщо нова сцена не має музики, а попередня мала
        pygame.mixer.music.stop()
        current_background_music_path = None
        print("Фонова музика зупинена.")

    # Завантаження та відтворення озвучки тексту
    new_voice_over_path = scene_data.get("voice_over")
    if current_voice_over and current_voice_over.get_num_channels() > 0: # Перевіряємо, чи грає попередній звук
        current_voice_over.stop() # Зупиняємо попередню озвучку

    current_voice_over = None # Скидаємо попередню озвучку
    if new_voice_over_path:
        full_voice_over_path = os.path.join(STORY_AUDIO_DIR, new_voice_over_path)
        if os.path.exists(full_voice_over_path):
            try:
                current_voice_over = pygame.mixer.Sound(full_voice_over_path)
                current_voice_over.play() # Відтворення озвучки
                print(f"Відтворюється озвучка: {new_voice_over_path}")
            except pygame.error as e:
                print(f"Помилка відтворення озвучки '{full_voice_over_path}': {e}")
        else:
            print(f"Озвучка '{full_voice_over_path}' не знайдена.")


    current_characters.clear()
    # TODO: Реалізувати завантаження та позиціонування зображень персонажів

    current_text = scene_data.get("text", "")
    current_choices.clear()
    text_display_index = 0
    last_text_update_time = time.time()
    auto_advance_timer = 0

    if "choices" in scene_data and len(scene_data["choices"]) > 0:
        choice_y_offset = SCREEN_HEIGHT * 0.55 # Кнопки починатимуться на 55% висоти екрану
        for i, choice in enumerate(scene_data["choices"]):
            choice_button = Button(
                choice["text"],
                SCREEN_WIDTH // 2 - 200,
                choice_y_offset + i * 60, # Відступ між кнопками
                400, 60,
                action=lambda next_s=choice["next_scene"]: handle_choice(next_s),
                text_color=WHITE, hover_color=GRAY,
                hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND
            )
            current_choices.append(choice_button)
    elif scene_data.get("auto_advance", False):
        auto_advance_timer = time.time() + AUTO_ADVANCE_DURATION


def handle_choice(next_scene_id):
    """Обробляє вибір гравця і переходить до наступної сцени."""
    print(f"Зроблено вибір. Перехід до сцени: {next_scene_id}")
    load_scene(next_scene_id)


def advance_text():
    """Просуває текст вперед або переходить до наступної сцени/виборів."""
    global text_display_index, auto_advance_timer

    if text_display_index < len(current_text):
        text_display_index = len(current_text)
    else:
        scene_data = current_story_data["scenes"][current_scene_id]
        if scene_data.get("auto_advance", False):
            if auto_advance_timer == 0:
                auto_advance_timer = time.time() + AUTO_ADVANCE_DURATION
        elif "choices" in scene_data and len(scene_data["choices"]) > 0:
            pass
        elif "next_scene" in scene_data:
            load_scene(scene_data["next_scene"])
        else:
            print("Кінець поточної гілки історії.")
            set_game_state(GameState.MENU)


# --- Функції для перемикання сцен ---
def set_game_state(state, story_id=None): 
    global current_state, active_input_box, player_nickname, selected_story_id
    global current_story_data, current_scene_id, current_background, current_characters, current_text, current_choices
    global text_display_index, last_text_update_time, auto_advance_timer
    global current_voice_over, current_background_music_path # <-- Додано
    
    if network.game_server:
        network.game_server.stop()
        network.game_server = None
    if network.game_client:
        network.game_client.stop()
        network.game_client = None
    network.connected_players_info.clear()
    network.network_status_message = ""
    network.current_lobby_code = None

    active_input_box = None 
    current_state = state
    print(f"Перехід до стану: {state}")

    if state == GameState.GAMEPLAY:
        selected_story_id = story_id
        print(f"Обрана історія: {STORIES[selected_story_id]['title'] if selected_story_id else 'Не обрано'}")
        if selected_story_id:
            if not load_story(selected_story_id):
                print(f"Помилка при завантаженні історії '{selected_story_id}'. Повернення до меню.")
                set_game_state(GameState.MENU)
            else:
                load_scene(current_story_data["start_scene"])
        else:
            print("Не обрано історію для початку геймплею.")
            set_game_state(GameState.MENU)
    else:
        selected_story_id = None 
        current_story_data = None
        current_scene_id = None
        current_background = None
        current_characters = {}
        current_text = ""
        current_choices = []
        text_display_index = 0
        last_text_update_time = 0
        auto_advance_timer = 0
        
        # Зупинка озвучки та фонової музики історії при виході з геймплею
        if current_voice_over:
            current_voice_over.stop()
            current_voice_over = None
        if pygame.mixer.music.get_busy() and current_background_music_path:
            pygame.mixer.music.stop()
        current_background_music_path = None


    # Логіка музики
    if state in [GameState.GAMEPLAY]:
        # Музика для геймплею буде завантажуватися в load_scene
        pass # Залишаємо відтворення музики для load_scene
    elif state == GameState.MENU:
        if not pygame.mixer.music.get_busy() or current_background_music_path: # Якщо немає музики або грає музика історії
            try:
                pygame.mixer.music.load(MENU_MUSIC_PATH)
                pygame.mixer.music.play(-1)
                current_background_music_path = None # Скидаємо шлях музики історії
            except pygame.error as e:
                print(f"Не вдалося відтворити музику меню: {e}")
    # Для інших станів (вибір режиму, лобі) музика меню продовжує грати, якщо вона була запущена,
    # і якщо не грала музика історії (current_background_music_path is None).


    if state == GameState.LOBBY_MAIN:
        global player_nickname_input_box
        initial_nickname = player_nickname if player_nickname else ''
        player_nickname_input_box = TextInputBox(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 50, 400, 50, text=initial_nickname, font=TEXT_INPUT_FONT, text_color=WHITE, border_color=WHITE)
    elif state == GameState.LOBBY_JOIN:
        global lobby_code_input_box
        lobby_code_input_box = TextInputBox(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 20, 400, 50, text='Введіть код лобі', font=TEXT_INPUT_FONT, text_color=WHITE, border_color=WHITE)


def start_new_game_mode_select():
    set_game_state(GameState.NEW_GAME_MODE_SELECT)

def start_solo_game():
    set_game_state(GameState.SOLO_MODE_STORY_SELECT)

def start_multiplayer_game():
    set_game_state(GameState.LOBBY_MAIN)

def exit_game():
    if network.game_server:
        network.game_server.stop()
    if network.game_client:
        network.game_client.stop()
    print("Вихід з гри...")
    pygame.quit()
    sys.exit()

def create_lobby_action():
    global player_nickname
    player_nickname = player_nickname_input_box.text.strip()
    if player_nickname and player_nickname != "Мій Нік":
        print(f"Створення лобі з ніком: {player_nickname}")
        set_game_state(GameState.LOBBY_CREATE)
        
        network.game_server = network.GameServer(network.HOST, network.PORT)
        network.game_server.start()
        
        time.sleep(0.1) 
        network.game_client = network.GameClient("127.0.0.1", network.PORT)
        if not network.game_client.connect(player_nickname, network.current_lobby_code):
            print("Помилка: Хост не зміг підключитися до власного сервера.")
            set_game_state(GameState.LOBBY_MAIN)
            network.network_status_message = "Помилка: Не вдалося запустити лобі."
        else:
            pass
    else:
        network.network_status_message = "Нікнейм не може бути порожнім або стандартним!"
        print("Нікнейм не може бути порожнім або стандартним!")

def join_lobby_action():
    global player_nickname
    player_nickname = player_nickname_input_box.text.strip()
    if player_nickname and player_nickname != "Мій Нік":
        print(f"Приєднання до лобі з ніком: {player_nickname}")
        set_game_state(GameState.LOBBY_JOIN)
    else:
        network.network_status_message = "Нікнейм не може бути порожнім або стандартним!"
        print("Нікнейм не може бути порожнім або стандартним!")

def start_game_from_lobby():
    if network.game_server and len(network.connected_players_info) > 0:
        print("Почати гру з лобі!")
        set_game_state(GameState.LOBBY_MODE_STORY_SELECT)
    else:
        print("Неможливо почати гру: не запущено сервер або немає гравців.")
        network.network_status_message = "Недостатньо гравців для початку гри."


def select_character():
    print("Відкрити вибір персонажа (ще не реалізовано)")

def submit_lobby_code():
    lobby_code = lobby_code_input_box.text.strip()
    if lobby_code and lobby_code != "Введіть код лобі":
        print(f"Спроба приєднатися до лобі з кодом: {lobby_code}")
        server_ip = "127.0.0.1" 
        
        if not network.game_client: 
            network.game_client = network.GameClient(server_ip, network.PORT)

        if network.game_client.connect(player_nickname, lobby_code):
            network.network_status_message = "Підключено, очікування лобі..."
        else:
            print("Не вдалося приєднатися до лобі.")
            network.network_status_message = "Не вдалося приєднатися до лобі. Перевірте код або IP."

    else:
        print("Код лобі не може бути порожнім або стандартним!")
        network.network_status_message = "Введіть дійсний код лобі."
    lobby_code_input_box.active = False

def copy_lobby_code():
    global copied_message_timer
    if network.current_lobby_code:
        try:
            pyperclip.copy(network.current_lobby_code)
            print(f"Код лобі '{network.current_lobby_code}' скопійовано!")
            copied_message_timer = time.time()
            if CLICK_SOUND:
                CLICK_SOUND.play()
        except pyperclip.PyperclipException as e:
            print(f"Не вдалося скопіювати код лобі: {e}")
            network.network_status_message = f"Помилка копіювання: {e}"
    else:
        print("Немає коду лобі для копіювання.")

def start_selected_story(story_id): 
    print(f"Почати обрану історію: {story_id}!")
    set_game_state(GameState.GAMEPLAY, story_id) 


# --- Ініціалізація полів вводу та кнопок ---
player_nickname_input_box = None
lobby_code_input_box = None

# Визначення ширини постійної центральної смуги
MENU_COLUMN_WIDTH = 500
MENU_COLUMN_X = (SCREEN_WIDTH - MENU_COLUMN_WIDTH) // 2

# --- Головний ігровий цикл ---
def main():
    global active_input_box, copied_message_timer, text_display_index, last_text_update_time, auto_advance_timer
    clock = pygame.time.Clock()

    # Кнопки головного меню
    new_game_button = Button("Нова Гра", MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 30, 300, 70, start_new_game_mode_select,
                          text_color=WHITE, hover_color=GRAY, 
                          hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    exit_button = Button("Вихід", MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50, 300, 70, exit_game,
                         text_color=WHITE, hover_color=GRAY,
                         hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    menu_buttons = [new_game_button, exit_button]

    # Кнопки вибору режиму нової гри
    solo_mode_button = Button("Соло", MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 50, 300, 70, start_solo_game,
                              text_color=WHITE, hover_color=GRAY,
                              hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    multiplayer_mode_button = Button("З друзями", MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 30, 300, 70, start_multiplayer_game,
                                     text_color=WHITE, hover_color=GRAY,
                                     hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    back_to_main_menu_from_mode_select_button = Button("Назад", MENU_COLUMN_X + 20, SCREEN_HEIGHT - 100, 150, 60, lambda: set_game_state(GameState.MENU),
                                                        text_color=WHITE, hover_color=GRAY,
                                                        hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)


    # Кнопки для LOBBY_MAIN (Мультиплеєр)
    create_game_button = Button("Створити гру", MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50, 300, 70, create_lobby_action,
                                 text_color=WHITE, hover_color=GRAY,
                                 hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    join_game_button = Button("Приєднатися", MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 130, 300, 70, join_lobby_action,
                               text_color=WHITE, hover_color=GRAY,
                               hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    back_to_mode_select_button_lobby_main = Button("Назад", MENU_COLUMN_X + 20, SCREEN_HEIGHT - 100, 150, 60, lambda: set_game_state(GameState.NEW_GAME_MODE_SELECT),
                                text_color=WHITE, hover_color=GRAY,
                                hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)

    # Кнопки для LOBBY_CREATE (позиції будуть коригуватися динамічно в draw)
    start_game_button_lobby = Button("Почати гру", 0, 0, 200, 70, start_game_from_lobby, 
                                     text_color=WHITE, hover_color=GRAY,
                                     hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    select_character_button = Button("Обрати персонажа", 0, 0, 300, 70, select_character, 
                                    text_color=WHITE, hover_color=GRAY,
                                    hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    back_from_create_lobby_button = Button("Назад", 0, 0, 150, 60, lambda: set_game_state(GameState.LOBBY_MAIN), 
                                          text_color=WHITE, hover_color=GRAY,
                                          hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)

    # Кнопки для LOBBY_JOIN (позиції будуть коригуватися динамічно в draw)
    submit_code_button = Button("Приєднатися", 0, 0, 200, 70, submit_lobby_code, 
                                text_color=WHITE, hover_color=GRAY,
                                hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    back_from_join_lobby_button = Button("Назад", 0, 0, 150, 60, lambda: set_game_state(GameState.LOBBY_MAIN), 
                                         text_color=WHITE, hover_color=GRAY,
                                         hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    
    # Кнопки для вибору історії (загальні для соло та лобі)
    story_buttons = []
    button_y_offset = -100 
    for story_id, story_data in STORIES.items():
        button = Button(
            f"{story_data['title']}", 
            MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - 200, 
            SCREEN_HEIGHT // 2 + button_y_offset, 
            400, 70, 
            action=lambda s_id=story_id: start_selected_story(s_id), 
            text_color=WHITE, hover_color=GRAY,
            hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND
        )
        story_buttons.append(button)
        button_y_offset += 80 

    # Кнопка "Назад" для екрану вибору історії (в соло режимі)
    back_from_solo_story_select_button = Button("Назад", MENU_COLUMN_X + 20, SCREEN_HEIGHT - 100, 150, 60, lambda: set_game_state(GameState.NEW_GAME_MODE_SELECT),
                                                text_color=WHITE, hover_color=GRAY,
                                                hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)
    # Кнопка "Назад" для екрану вибору історії (в мультиплеєрі, повернення в лобі)
    back_from_lobby_story_select_button = Button("Назад", MENU_COLUMN_X + 20, SCREEN_HEIGHT - 100, 150, 60, lambda: set_game_state(GameState.LOBBY_CREATE),
                                                 text_color=WHITE, hover_color=GRAY,
                                                 hover_sound=HOVER_SOUND, click_sound=CLICK_SOUND)


    # Музика меню
    try:
        pygame.mixer.music.load(MENU_MUSIC_PATH)
        pygame.mixer.music.play(-1)
    except pygame.error as e:
        print(f"Не вдалося завантажити або відтворити музику меню: {e}")


    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- Обробка кліків миші для полів вводу та скидання active_input_box ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked_on_input_box = False
                
                if current_state == GameState.LOBBY_MAIN and player_nickname_input_box:
                    if player_nickname_input_box.rect.collidepoint(event.pos):
                        mouse_clicked_on_input_box = True
                    player_nickname_input_box.handle_event(event) 

                if current_state == GameState.LOBBY_JOIN and lobby_code_input_box:
                    if lobby_code_input_box.rect.collidepoint(event.pos):
                        mouse_clicked_on_input_box = True
                    lobby_code_input_box.handle_event(event) 

                if current_state == GameState.GAMEPLAY:
                    if text_display_index < len(current_text) or \
                       (current_story_data and current_scene_id and \
                        current_story_data["scenes"][current_scene_id].get("auto_advance", False) and auto_advance_timer > 0):
                        advance_text()
                    elif current_story_data and current_scene_id and not current_choices:
                        scene_data = current_story_data["scenes"][current_scene_id]
                        if "next_scene" in scene_data:
                            load_scene(scene_data["next_scene"])
                        elif scene_data.get("auto_advance", False):
                            pass
                        else:
                            set_game_state(GameState.MENU)

                if not mouse_clicked_on_input_box:
                    if active_input_box:
                        active_input_box.active = False
                        active_input_box = None
                else: 
                    if current_state == GameState.LOBBY_MAIN and player_nickname_input_box and player_nickname_input_box.active:
                        active_input_box = player_nickname_input_box
                    elif current_state == GameState.LOBBY_JOIN and lobby_code_input_box and lobby_code_input_box.active:
                        active_input_box = lobby_code_input_box
                    else:
                        active_input_box = None


            # --- Обробка подій клавіатури ---
            if event.type == pygame.KEYDOWN:
                if active_input_box:
                    active_input_box.handle_event(event) 

                if event.key == pygame.K_ESCAPE:
                    if current_state == GameState.NEW_GAME_MODE_SELECT:
                        set_game_state(GameState.MENU)
                    elif current_state == GameState.LOBBY_MAIN:
                        set_game_state(GameState.NEW_GAME_MODE_SELECT)
                    elif current_state == GameState.LOBBY_CREATE:
                        set_game_state(GameState.LOBBY_MAIN)
                    elif current_state == GameState.LOBBY_JOIN:
                        set_game_state(GameState.LOBBY_MAIN)
                    elif current_state == GameState.SOLO_MODE_STORY_SELECT:
                        set_game_state(GameState.NEW_GAME_MODE_SELECT) 
                    elif current_state == GameState.LOBBY_MODE_STORY_SELECT:
                        if network.game_server:
                             set_game_state(GameState.LOBBY_CREATE)
                    elif current_state == GameState.GAMEPLAY:
                        set_game_state(GameState.MENU)
                        print("Повернення в головне меню з геймплею.")


            # --- Обробка подій для кнопок (MOUSEMOTION та MOUSEBUTTONDOWN) ---
            if current_state == GameState.MENU:
                for button in menu_buttons:
                    button.handle_event(event)
            elif current_state == GameState.NEW_GAME_MODE_SELECT:
                solo_mode_button.handle_event(event)
                multiplayer_mode_button.handle_event(event)
                back_to_main_menu_from_mode_select_button.handle_event(event)
            elif current_state == GameState.LOBBY_MAIN:
                create_game_button.handle_event(event)
                join_game_button.handle_event(event)
                back_to_mode_select_button_lobby_main.handle_event(event)
            elif current_state == GameState.LOBBY_CREATE:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if network.current_lobby_code:
                        code_area_rect_for_click = pygame.Rect(
                            MENU_COLUMN_X, 
                            150, 
                            MENU_COLUMN_WIDTH, 
                            100 
                        )
                        if code_area_rect_for_click.collidepoint(event.pos):
                            copy_lobby_code()
                start_game_button_lobby.handle_event(event)
                select_character_button.handle_event(event)
                back_from_create_lobby_button.handle_event(event)
            elif current_state == GameState.LOBBY_JOIN:
                submit_code_button.handle_event(event)
                back_from_join_lobby_button.handle_event(event)
            elif current_state == GameState.SOLO_MODE_STORY_SELECT:
                for button in story_buttons: 
                    button.handle_event(event)
                back_from_solo_story_select_button.handle_event(event)
            elif current_state == GameState.LOBBY_MODE_STORY_SELECT:
                for button in story_buttons: 
                    button.handle_event(event)
                back_from_lobby_story_select_button.handle_event(event)
            elif current_state == GameState.GAMEPLAY:
                for choice_button in current_choices:
                    choice_button.handle_event(event)


        # --- Оновлення логіки ---
        if copied_message_timer != 0 and time.time() - copied_message_timer > COPIED_MESSAGE_DURATION:
            copied_message_timer = 0
        
        if current_state == GameState.GAMEPLAY:
            if text_display_index < len(current_text):
                if time.time() - last_text_update_time > TEXT_SPEED:
                    text_display_index += 1
                    last_text_update_time = time.time()
            elif auto_advance_timer > 0 and time.time() >= auto_advance_timer:
                scene_data = current_story_data["scenes"][current_scene_id]
                if "next_scene" in scene_data:
                    load_scene(scene_data["next_scene"])
                else:
                    set_game_state(GameState.MENU)


        # --- Відмальовка ---
        if current_state == GameState.GAMEPLAY:
            if current_background:
                SCREEN.blit(current_background, (0, 0))
            else:
                SCREEN.fill(BLACK)
            
            # Відображення текстового поля
            text_box_height = SCREEN_HEIGHT // 4
            text_box_surface = pygame.Surface((SCREEN_WIDTH, text_box_height), pygame.SRCALPHA)
            text_box_surface.fill(TEXT_BOX_COLOR)
            SCREEN.blit(text_box_surface, (0, SCREEN_HEIGHT - text_box_height))

            # Відображення тексту
            display_text = current_text[:text_display_index]
            
            words = display_text.split(' ')
            lines = []
            current_line = ""
            max_text_width = SCREEN_WIDTH - 100

            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if GAME_TEXT_FONT.size(test_line)[0] < max_text_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)

            text_y_start = SCREEN_HEIGHT - text_box_height + 20
            for i, line in enumerate(lines):
                text_surface = GAME_TEXT_FONT.render(line, True, WHITE)
                SCREEN.blit(text_surface, (200, text_y_start + i * (GAME_TEXT_FONT.get_linesize() + 5))) # Позиція тексту

            for choice_button in current_choices:
                choice_button.draw(SCREEN)

        else:
            SCREEN.blit(MENU_BACKGROUND, (0, 0))

            menu_column_surface_bg = pygame.Surface((MENU_COLUMN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            menu_column_surface_bg.fill(TRANSPARENT_BLACK)
            SCREEN.blit(menu_column_surface_bg, (MENU_COLUMN_X, 0))

            if current_state == GameState.MENU:
                title_surface = CUSTOM_FONT.render("Моя Кооперативна ВН", True, WHITE) 
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, SCREEN_HEIGHT // 4))
                SCREEN.blit(title_surface, title_rect)

                for button in menu_buttons:
                    button.draw(SCREEN)
            
            elif current_state == GameState.NEW_GAME_MODE_SELECT:
                title_surface = CUSTOM_FONT.render("Оберіть режим гри", True, WHITE) 
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
                SCREEN.blit(title_surface, title_rect)

                solo_mode_button.draw(SCREEN)
                multiplayer_mode_button.draw(SCREEN)
                back_to_main_menu_from_mode_select_button.draw(SCREEN)

            elif current_state == GameState.LOBBY_MAIN:
                title_surface = CUSTOM_FONT.render("Налаштування лобі", True, WHITE) 
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, SCREEN_HEIGHT // 4 - 80))
                SCREEN.blit(title_surface, title_rect)

                nickname_prompt = BUTTON_FONT.render("Введіть ваш нікнейм:", True, WHITE) 
                SCREEN.blit(nickname_prompt, (player_nickname_input_box.rect.x, player_nickname_input_box.rect.y - 30))
                player_nickname_input_box.draw(SCREEN)

                create_game_button.draw(SCREEN)
                join_game_button.draw(SCREEN)
                back_to_mode_select_button_lobby_main.draw(SCREEN)

                if network.network_status_message:
                    status_text = BUTTON_FONT.render(network.network_status_message, True, RED if "Помилка" in network.network_status_message else WHITE)
                    SCREEN.blit(status_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - status_text.get_width() // 2, SCREEN_HEIGHT // 2 + 200))


            elif current_state == GameState.LOBBY_CREATE:
                title_surface = CUSTOM_FONT.render("Лобі: Очікування гравців", True, WHITE)
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, 100))
                SCREEN.blit(title_surface, title_rect)

                if network.current_lobby_code:
                    lobby_code_display_text = f"Код лобі: {network.current_lobby_code}"
                    lobby_code_surface = BUTTON_FONT.render(lobby_code_display_text, True, WHITE) 
                    
                    code_text_rect_check = lobby_code_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, 200))
                    if code_text_rect_check.collidepoint(pygame.mouse.get_pos()):
                        lobby_code_surface = BUTTON_FONT.render(lobby_code_display_text, True, GRAY)
                    
                    lobby_code_rect = lobby_code_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, 200))
                    SCREEN.blit(lobby_code_surface, lobby_code_rect)

                    if copied_message_timer != 0:
                        time_elapsed = time.time() - copied_message_timer
                        if time_elapsed < COPIED_MESSAGE_DURATION:
                            alpha = 255 - int(255 * (time_elapsed / COPIED_MESSAGE_DURATION))
                            if alpha < 0: alpha = 0
                            
                            copied_msg_surface = BUTTON_FONT.render("Код скопійовано!", True, GREEN)
                            copied_msg_surface.set_alpha(alpha)
                            copied_msg_rect = copied_msg_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, 250))
                            SCREEN.blit(copied_msg_surface, copied_msg_rect)
                else:
                    lobby_code_display = BUTTON_FONT.render("Генерація коду лобі...", True, WHITE)
                    SCREEN.blit(lobby_code_display, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - lobby_code_display.get_width() // 2, 200 - lobby_code_display.get_height() // 2))


                player_list_y_start = 350 
                list_title = BUTTON_FONT.render("Гравці:", True, WHITE) 
                SCREEN.blit(list_title, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - list_title.get_width() // 2, player_list_y_start))

                if network.connected_players_info:
                    for i, player_data in enumerate(network.connected_players_info):
                        player_text = BUTTON_FONT.render(f"{player_data['nickname']} ({player_data['character']})", True, WHITE)
                        SCREEN.blit(player_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - player_text.get_width() // 2, player_list_y_start + 40 + i * 25))
                else:
                    no_players_text = BUTTON_FONT.render("Немає підключених гравців...", True, WHITE)
                    SCREEN.blit(no_players_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - no_players_text.get_width() // 2, player_list_y_start + 40))

                status_text = BUTTON_FONT.render(network.network_status_message, True, RED if "Помилка" in network.network_status_message else WHITE)
                SCREEN.blit(status_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - status_text.get_width() // 2, SCREEN_HEIGHT - 500))


                start_game_button_lobby.rect.centerx = MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2
                start_game_button_lobby.rect.y = SCREEN_HEIGHT - 100 
                start_game_button_lobby.draw(SCREEN)

                select_character_button.rect.centerx = MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2
                select_character_button.rect.y = SCREEN_HEIGHT - 170 
                select_character_button.draw(SCREEN)
                
                back_from_create_lobby_button.rect.x = MENU_COLUMN_X + 20 
                back_from_create_lobby_button.rect.y = SCREEN_HEIGHT - 50
                back_from_create_lobby_button.draw(SCREEN)


            elif current_state == GameState.LOBBY_JOIN:
                title_surface = CUSTOM_FONT.render("Приєднатися до лобі", True, WHITE)
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, 100))
                SCREEN.blit(title_surface, title_rect)

                code_prompt = BUTTON_FONT.render("Введіть код лобі:", True, WHITE)
                SCREEN.blit(code_prompt, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - code_prompt.get_width() // 2, 200))
                
                lobby_code_input_box.rect.centerx = MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2
                lobby_code_input_box.rect.y = 230 
                lobby_code_input_box.border_color = WHITE 
                lobby_code_input_box.text_color = WHITE
                lobby_code_input_box.draw(SCREEN)

                submit_code_button.rect.centerx = MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2
                submit_code_button.rect.y = 300
                submit_code_button.draw(SCREEN)

                status_text = BUTTON_FONT.render(network.network_status_message, True, RED if "Помилка" in network.network_status_message else WHITE)
                SCREEN.blit(status_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - status_text.get_width() // 2, 400))


                if network.game_client and network.game_client.running:
                    player_list_y_start = 450
                    list_title = BUTTON_FONT.render("Гравці в лобі:", True, WHITE)
                    SCREEN.blit(list_title, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - list_title.get_width() // 2, player_list_y_start))
                    if network.connected_players_info:
                        for i, player_data in enumerate(network.connected_players_info):
                            player_text = BUTTON_FONT.render(f"{player_data['nickname']} ({player_data['character']})", True, WHITE)
                            SCREEN.blit(player_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - player_text.get_width() // 2, player_list_y_start + 40 + i * 25))
                    else:
                        no_players_text = BUTTON_FONT.render("Очікування гравців...", True, WHITE)
                        SCREEN.blit(no_players_text, (MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2 - no_players_text.get_width() // 2, player_list_y_start + 40))

                back_from_join_lobby_button.rect.x = MENU_COLUMN_X + 20
                back_from_join_lobby_button.rect.y = SCREEN_HEIGHT - 50
                back_from_join_lobby_button.draw(SCREEN)


            elif current_state == GameState.SOLO_MODE_STORY_SELECT:
                title_surface = CUSTOM_FONT.render("Оберіть історію (Соло)", True, WHITE) 
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
                SCREEN.blit(title_surface, title_rect)

                for button in story_buttons:
                    button.draw(SCREEN)
                back_from_solo_story_select_button.draw(SCREEN)

            elif current_state == GameState.LOBBY_MODE_STORY_SELECT:
                title_surface = CUSTOM_FONT.render("Оберіть історію (Лобі)", True, WHITE) 
                title_rect = title_surface.get_rect(center=(MENU_COLUMN_X + MENU_COLUMN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
                SCREEN.blit(title_surface, title_rect)

                for button in story_buttons:
                    button.draw(SCREEN)
                back_from_lobby_story_select_button.draw(SCREEN)


        pygame.display.flip()

        clock.tick(60)

    if network.game_server:
        network.game_server.stop()
    if network.game_client:
        network.game_client.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(FONTS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(STORIES_DIR, exist_ok=True)
    os.makedirs(STORY_ASSETS_DIR, exist_ok=True)
    os.makedirs(STORY_AUDIO_DIR, exist_ok=True) # <-- Додано створення папки для аудіо історій
    
    main()