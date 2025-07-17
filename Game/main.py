import pygame
import os
from data.stories import STORIES
import json

pygame.init()

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
MASTER_SOUND_VOLUME = 1

# Стани гри
MAIN_MENU = 0
SOLO_MODE_SELECT = 1
SOLO_MODE_CHARACTER_SELECT = 2 
GAMEPLAY = 3
OPTIONS = 4

selected_story_id = None # ID обраної історії
current_story_data = {}     # Завантажені дані поточної історії (з JSON файлу)

current_scene_id = None # ID поточної активної сцени
current_scene_data = {} # Дані поточної сцени (фон, текст, персонажі, вибори)
current_scene_background = None # Завантажене зображення фону поточної сцени
current_scene_music = None # Поточна фонова музика
scene_choice_buttons = [] # Список кнопок для виборів у поточній сцені
display_text = "" # Текст, який буде відображатися на екрані (для ефекту друку)
text_display_index = 0 # Індекс для анімації друку тексту
text_display_timer = 0 # Таймер для контролю швидкості друку тексту
TYPING_SPEED = 20 # Мілісекунди на символ (менше - швидше)
current_character = None # Зберігаємо поточного персонажа, який був обраний

# Поточний стан гри 
current_game_state = MAIN_MENU

SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
running = True

ASSETS_DIR = "Game/assets"
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
DATA_DIR = "Game/data"
STORIES_DIR = "Game/stories"
STORY_ASSETS_DIR = os.path.join(IMAGES_DIR, "story_assets")
STORY_AUDIO_DIR = os.path.join(AUDIO_DIR, "story_audio") 

MENU_BACKGROUND_PATH = os.path.join(IMAGES_DIR, "main_menu.png")
MENU_BACKGROUND = pygame.image.load(MENU_BACKGROUND_PATH).convert()
MENU_BACKGROUND = pygame.transform.scale(MENU_BACKGROUND, (SCREEN_WIDTH, SCREEN_HEIGHT))
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
LOADED_CHARACTER_IMAGES = {}

MAIN_MENU_FONT_PATH = os.path.join(FONTS_DIR, "Oswald-ExtraLight.ttf")
MAIN_MENU_BUTTON_FONT = pygame.font.Font(MAIN_MENU_FONT_PATH, 30)
MAIN_MENU_TITLE_FONT = pygame.font.Font(MAIN_MENU_FONT_PATH, 40)

MENU_BUTTON_HOVER_SOUND_PATH = os.path.join(AUDIO_DIR, "button_hover.mp3")
MENU_BUTTON_CLICK_SOUND_PATH = os.path.join(AUDIO_DIR, "click-button-140881.mp3")

MENU_BUTTON_HOVER_SOUND = pygame.mixer.Sound(MENU_BUTTON_HOVER_SOUND_PATH)
MENU_BUTTON_CLICK_SOUND = pygame.mixer.Sound(MENU_BUTTON_CLICK_SOUND_PATH)
MENU_BUTTON_HOVER_SOUND.set_volume(MASTER_SOUND_VOLUME)
MENU_BUTTON_CLICK_SOUND.set_volume(MASTER_SOUND_VOLUME)

LOBBY_FONT = pygame.font.Font(MAIN_MENU_FONT_PATH, 25)
# Кольори
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200) # При наведені
TRANSPARENT_BLACK = (0, 0, 0, 128) # Чорний з 50% прозорістю. Смуга вертикальна в меню

# КНОПКИ МЕНЮ 
MENU_BUTTON_COLOR = (0, 200, 0, 0) # Напівпрозорий
MENU_BUTTON_HOVER_COLOR = (0, 200, 0, 0)

# Кольори тексту
MENU_TEXT_COLOR = WHITE
MENU_TEXT_HOVER_COLOR = GRAY # Колір тексту при наведенні

class Button:
    def __init__(self, text, x, y, width, height, action=None, 
                 base_color=MENU_BUTTON_COLOR, 
                 hover_color=MENU_BUTTON_HOVER_COLOR, 
                 text_color=MENU_TEXT_COLOR, 
                 text_hover_color=MENU_TEXT_HOVER_COLOR,
                 font=MAIN_MENU_BUTTON_FONT,
                 hover_sound=None,
                 click_sound=None,
                 ): 
        
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.text_hover_color = text_hover_color
        self.font = font

        self.hover_sound = hover_sound
        self.click_sound = click_sound

        self.is_hovered = False # Відстежуємо, чи наведено зараз на кнопку
        
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        
    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()

        was_hovered = self.is_hovered 
        self.is_hovered = self.rect.collidepoint(mouse_pos) 

        if self.is_hovered and not was_hovered and self.hover_sound:
            self.hover_sound.play()

        if self.rect.collidepoint(mouse_pos):
            current_bg_color = self.hover_color
            current_text_color = self.text_hover_color
        else:
            current_bg_color = self.base_color
            current_text_color = self.text_color
        
        self.image.fill(current_bg_color)
        
        text_surface = self.font.render(self.text, True, current_text_color) 
        text_rect = text_surface.get_rect(center=(self.rect.width / 2, self.rect.height / 2))
        self.image.blit(text_surface, text_rect)
        
        surface.blit(self.image, self.rect.topleft)

    def handle_event(self, event):

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                if self.rect.collidepoint(event.pos):
                    if self.click_sound:
                        self.click_sound.play()
                    if self.action:
                        self.action()



def start_new_game_solo_mode_select():
    """Коли натискаємо "Нова гра" """
    set_game_state(SOLO_MODE_SELECT)
    get_stories()

def quit_game():
    global running
    # Закриваємо мережеві з'єднання при виході
    running = False

def adjust_volume(delta):
    """Налаштування гучності"""
    global MASTER_SOUND_VOLUME 
    MASTER_SOUND_VOLUME = round(MASTER_SOUND_VOLUME + delta, 1) 
    MASTER_SOUND_VOLUME = max(0.0, min(1.0, MASTER_SOUND_VOLUME)) 

    pygame.mixer.music.set_volume(MASTER_SOUND_VOLUME) 

    if MENU_BUTTON_HOVER_SOUND:
        MENU_BUTTON_HOVER_SOUND.set_volume(MASTER_SOUND_VOLUME)
    if MENU_BUTTON_CLICK_SOUND:
        MENU_BUTTON_CLICK_SOUND.set_volume(MASTER_SOUND_VOLUME)

def handle_story_selection(story_id):
    """
    Обробляє вибір історії гравцем (для одиночної гри).
    Зберігає story_id і переходить до наступного стану.
    """
    global selected_story_id
    print(f"Обрано історію з ID: {story_id}")
    selected_story_id = story_id # Зберігаємо обрану історію
    
    # Після вибору історії, переходимо до вибору персонажа
    # Якщо вам не потрібен окремий екран вибору персонажа, можна замінити на GAMEPLAY
    set_game_state(SOLO_MODE_CHARACTER_SELECT) 

def load_scene(scene_id):
    """
    Завантажує та відображає дані для вказаної сцени.
    """
    global current_scene_id, current_scene_data, current_scene_background, \
           current_scene_music, display_text, text_display_index, text_display_timer, \
           scene_choice_buttons, TYPING_SPEED # Додайте TYPING_SPEED, якщо змінюватимете її тут

    # Перевірка, чи завантажена історія та чи існує в ній сцена
    if not current_story_data or scene_id not in current_story_data.get("scenes", {}):
        print(f"Помилка: Сцена '{scene_id}' не знайдена в поточній історії.")
        return

    current_scene_id = scene_id
    current_scene_data = current_story_data["scenes"][scene_id]

    # Скидання анімації тексту
    display_text = current_scene_data.get("text", "")
    text_display_index = 0
    text_display_timer = pygame.time.get_ticks()

    # Завантаження фону
    background_path = os.path.join(STORY_ASSETS_DIR, current_scene_data.get("background", ""))
    try:
        temp_background = pygame.image.load(background_path).convert_alpha()
        current_scene_background = pygame.transform.scale(temp_background, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except pygame.error as e:
        print(f"Помилка завантаження фону '{background_path}': {e}")
        current_scene_background = None # або завантажити фон за замовчуванням

    # Завантаження музики
    music_path = os.path.join(STORY_AUDIO_DIR, current_scene_data.get("background_music", ""))
    if os.path.exists(music_path):
        if current_scene_music != music_path: # Завантажувати та відтворювати лише якщо музика змінилась
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(MASTER_SOUND_VOLUME)
            pygame.mixer.music.play(-1) # -1 означає зациклення
            current_scene_music = music_path
    else:
        if current_scene_music: # Зупинити попередню музику, якщо нова відсутня
            pygame.mixer.music.stop()
            current_scene_music = None
        print(f"Попередження: Музика фону не знайдена: {music_path}")

    # Створення кнопок вибору для сцени
    scene_choice_buttons.clear()
    choices = current_scene_data.get("choices", [])
    
    # Визначаємо, чи потрібне голосування (якщо ця змінна залишилась)
    # Якщо ви видалили voting_active, то просто ігноруйте цю частину
    # requires_vote = current_scene_data.get("requires_vote", False) # Ця змінна зараз не використовується для логіки

    if choices:
        choice_y_start = SCREEN_HEIGHT - 100 - (len(choices) * 60)
        for i, choice in enumerate(choices):
            button = Button(
                text=choice["text"],
                x=SCREEN_WIDTH // 2 - 150,
                y=choice_y_start + i * 60,
                width=300,
                height=50,
                action=lambda next_scene=choice["next_scene"]: load_scene(next_scene), # При кліку просто завантажуємо наступну сцену
                text_color=WHITE,
                text_hover_color=GRAY,
                hover_sound=MENU_BUTTON_HOVER_SOUND,
                click_sound=MENU_BUTTON_CLICK_SOUND
            )
            scene_choice_buttons.append(button)
    else:
        # Якщо немає виборів, і сцена не auto_advance, можливо, це кінець історії або чекаємо наступну дію
        if not current_scene_data.get("auto_advance", False):
            print(f"Сцена '{scene_id}' не має виборів та не є 'auto_advance'.")

def load_story_data(story_id):
    """
    Завантажує дані історії з JSON файлу.
    """
    global current_story_data 

    if story_id in STORIES:
        story_file_name = os.path.basename(STORIES[story_id]["start_data_path"])
        full_path = os.path.join(STORIES_DIR, story_file_name)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                current_story_data = json.load(f)
            print(f"Історія: Завантажено дані для '{STORIES[story_id]['title']}' з {full_path}")
            return True
        except FileNotFoundError:
            print(f"Помилка: Файл історії не знайдено за шляхом: {full_path}")
            current_story_data = {}
            return False
        except json.JSONDecodeError:
            print(f"Помилка: Невірний формат JSON у файлі: {full_path}")
            current_story_data = {}
            return False
    else:
        print(f"Помилка: Історія з ID '{story_id}' не знайдена в STORIES.")
        current_story_data = {}
        return False

def set_game_state(state):
    """
    Встановлює новий стан гри.
    """
    global current_game_state, selected_story_id 
    old_state = current_game_state
    current_game_state = state

    # Логіка для переходу до геймплею
    if state == GAMEPLAY:
        if selected_story_id: # Якщо історія вже обрана
            # Завантажуємо дані обраної історії
            if load_story_data(selected_story_id):
                # Встановлюємо першу сцену історії
                if current_story_data and "start_scene" in current_story_data:
                    load_scene(current_story_data["start_scene"])
                else:
                    print(f"Помилка: Історія {selected_story_id} не має 'start_scene'. Повертаюсь в меню.")
                    set_game_state(MAIN_MENU)
            else:
                print(f"Помилка: Не вдалося завантажити дані для історії {selected_story_id}. Повертаюсь в меню.")
                set_game_state(MAIN_MENU)
        else:
            print("Помилка: Немає обраної історії для початку геймплею. Повертаюсь в меню.")
            set_game_state(MAIN_MENU)

solo_game_button = Button(
    text="Нова гра", 
    x=SCREEN_WIDTH // 2 - 150, 
    y=SCREEN_HEIGHT // 2 - 60, 
    width=300, 
    height=70, 
    action=start_new_game_solo_mode_select,
    text_color=MENU_TEXT_COLOR, 
    text_hover_color=MENU_TEXT_HOVER_COLOR,
    hover_sound=MENU_BUTTON_HOVER_SOUND,
    click_sound=MENU_BUTTON_CLICK_SOUND
)

options_button = Button(
    text="Налаштування",
    x=SCREEN_WIDTH // 2 - 150,
    y=SCREEN_HEIGHT // 2 + 60,
    width=300,
    height=70,
    action=lambda: set_game_state(OPTIONS), 
    text_color=MENU_TEXT_COLOR, 
    text_hover_color=MENU_TEXT_HOVER_COLOR,
    hover_sound=MENU_BUTTON_HOVER_SOUND,
    click_sound=MENU_BUTTON_CLICK_SOUND
)

# Кнопки для зміни гучності
volume_up_button = Button(
    text=">",
    x=SCREEN_WIDTH // 2 - 0, 
    y=SCREEN_HEIGHT // 2 - 120,
    width=40,
    height=40,
    action=lambda: adjust_volume(0.1), 
    text_color=MENU_TEXT_COLOR,
    text_hover_color=MENU_TEXT_HOVER_COLOR,
    hover_sound=MENU_BUTTON_HOVER_SOUND,
    click_sound=MENU_BUTTON_CLICK_SOUND
)

volume_down_button = Button(
    text="<",
    x=SCREEN_WIDTH // 2 - 40, 
    y=SCREEN_HEIGHT // 2 - 120,
    width=40,
    height=40,
    action=lambda: adjust_volume(-0.1), 
    text_color=MENU_TEXT_COLOR,
    text_hover_color=MENU_TEXT_HOVER_COLOR,
    hover_sound=MENU_BUTTON_HOVER_SOUND,
    click_sound=MENU_BUTTON_CLICK_SOUND
)

exit_button = Button(
    text="Вихід", 
    x=SCREEN_WIDTH // 2 - 150, 
    y=SCREEN_HEIGHT // 2 + 120, 
    width=300, 
    height=70, 
    action=quit_game,
    text_color=MENU_TEXT_COLOR, 
    text_hover_color=MENU_TEXT_HOVER_COLOR,
    hover_sound=MENU_BUTTON_HOVER_SOUND,
    click_sound=MENU_BUTTON_CLICK_SOUND
)

back_to_main_menu_button = Button(
    text="Назад",
    x=SCREEN_WIDTH // 2 - 150,
    y=SCREEN_HEIGHT - 80,
    width=300,
    height=70,
    action=lambda: set_game_state(MAIN_MENU), 
    text_color=MENU_TEXT_COLOR, 
    text_hover_color=MENU_TEXT_HOVER_COLOR,
    hover_sound=MENU_BUTTON_HOVER_SOUND,
    click_sound=MENU_BUTTON_CLICK_SOUND
)

button_y_start = SCREEN_HEIGHT // 2 - 100 # Початкова позиція для першої кнопки
button_spacing = 80 # Відстань між кнопками

def get_stories():
    global solo_mode_select_buttons # Додайте global, якщо змінюєте список
    solo_mode_select_buttons.clear() # Очищаємо список кнопок перед додаванням
    button_y_start = SCREEN_HEIGHT // 2 - 100
    button_spacing = 80

    for i, (story_id, story_info) in enumerate(STORIES.items()):
        # Важливо: використовуємо story_id=story_id у lambda, щоб захопити правильне значення
        button = Button(
            text=story_info["title"],
            x=SCREEN_WIDTH // 2 - 150,
            y=button_y_start + i * button_spacing,
            width=300,
            height=70,
            action=lambda s_id=story_id: handle_story_selection(s_id),
            text_color=MENU_TEXT_COLOR,
            text_hover_color=MENU_TEXT_HOVER_COLOR,
            hover_sound=MENU_BUTTON_HOVER_SOUND,
            click_sound=MENU_BUTTON_CLICK_SOUND,
        )
        solo_mode_select_buttons.append(button)
        
    back_button = Button(
        text="Назад",
        x=SCREEN_WIDTH // 2 - 150,
        y=button_y_start + len(STORIES) * button_spacing + 20, # Розміщуємо нижче кнопок історій
        width=300,
        height=70,
        action=lambda: set_game_state(MAIN_MENU),
        text_color=MENU_TEXT_COLOR,
        text_hover_color=MENU_TEXT_HOVER_COLOR,
        hover_sound=MENU_BUTTON_HOVER_SOUND,
        click_sound=MENU_BUTTON_CLICK_SOUND,
    )
    solo_mode_select_buttons.append(back_button)
        
def get_characters():
    for i, (character) in enumerate(STORIES.items()):
        button = Button(
            text=character["characters"],
            x=SCREEN_WIDTH // 2 - 150, # Зміщено вліво, щоб не конфліктувати з іншими кнопками
            y=button_y_start + i * button_spacing,
            width=300,
            height=70,
            # action=lambda sid=story_id: select_coop_story(sid), # Передаємо story_id
            text_color=MENU_TEXT_COLOR, 
            text_hover_color=MENU_TEXT_HOVER_COLOR,
            hover_sound=MENU_BUTTON_HOVER_SOUND,
            click_sound=MENU_BUTTON_CLICK_SOUND
        )
        characters_select_buttons.append(button)

# Вертикальна смуга в меню
# transparent_band_surface = pygame.Surface((600, SCREEN_HEIGHT), pygame.SRCALPHA)
# transparent_band_X = SCREEN_WIDTH // 2 - 600 // 2
# transparent_band_Y = 0
# transparent_band_surface.fill(TRANSPARENT_BLACK)

# Кнопки за станами гри
characters_select_buttons = [back_to_main_menu_button] 
main_menu_buttons = [solo_game_button, options_button, exit_button]
solo_mode_select_buttons = [back_to_main_menu_button]
options_buttons = [volume_down_button, volume_up_button, back_to_main_menu_button]

while running:
    current_time = pygame.time.get_ticks()

    # ОБРОБКА ПОДІЙ
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Обробка кліків по кнопках в залежності від стану гри
        # Ця логіка обробки подій для кнопок має бути тут
        if current_game_state == MAIN_MENU:
            for button in main_menu_buttons:
                button.handle_event(event)
        elif current_game_state == SOLO_MODE_SELECT:
            for button in solo_mode_select_buttons:
                button.handle_event(event)
        elif current_game_state == SOLO_MODE_CHARACTER_SELECT:
            for button in characters_select_buttons:
                button.handle_event(event)
        elif current_game_state == OPTIONS:
            for button in options_buttons:
                button.handle_event(event) 
        elif current_game_state == GAMEPLAY:
            # Обробка кліків по кнопках вибору сцени
            for button in scene_choice_buttons:
                button.handle_event(event)
            
            # Логіка "промотування" тексту швидше, якщо клікнули
            if event.type == pygame.MOUSEBUTTONDOWN and text_display_index < len(display_text):
                text_display_index = len(display_text) # Промотати весь текст
                text_display_timer = current_time # Оновити таймер, щоб не було миттєвого переходу, якщо є auto_advance

    # МАЛЮВАННЯ

    # Малюємо основний фон залежно від стану гри
    if current_game_state == GAMEPLAY:
        if current_scene_background:
            SCREEN.blit(current_scene_background, (0, 0))
    else: # Для всіх меню-станів
        SCREEN.blit(MENU_BACKGROUND, (0, 0))
        
        # Логіка для визначення ширини смуги (для меню-станів)
        band_width = 0
        if current_game_state == MAIN_MENU:
            band_width = 600
        elif current_game_state == SOLO_MODE_SELECT:
            band_width = 600 
        elif current_game_state == SOLO_MODE_CHARACTER_SELECT:
            band_width = 1920 
        elif current_game_state == OPTIONS:
            band_width = 600 

        # Малюємо смугу, тільки якщо ширина > 0 (і ми в одному з меню)
        if band_width > 0:
            dynamic_band_surface = pygame.Surface((band_width, SCREEN_HEIGHT), pygame.SRCALPHA)
            dynamic_band_surface.fill(TRANSPARENT_BLACK)
            
            dynamic_band_X = SCREEN_WIDTH // 2 - band_width // 2
            dynamic_band_Y = 0
            
            SCREEN.blit(dynamic_band_surface, (dynamic_band_X, dynamic_band_Y))

    # МАЛЮВАННЯ ІНШИХ ЕЛЕМЕНТІВ

    if current_game_state == MAIN_MENU:
        title_surface = MAIN_MENU_TITLE_FONT.render("Меню", True, WHITE) 
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
        SCREEN.blit(title_surface, title_rect)

        for button in main_menu_buttons:
            button.draw(SCREEN)

    elif current_game_state == SOLO_MODE_SELECT:
        title_surface = MAIN_MENU_TITLE_FONT.render("Обери главу", True, WHITE) 
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
        SCREEN.blit(title_surface, title_rect)

        for button in solo_mode_select_buttons:
            button.draw(SCREEN)

    elif current_game_state == SOLO_MODE_CHARACTER_SELECT:
        title_surface = MAIN_MENU_TITLE_FONT.render("Обери персонажа", True, WHITE) 
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
        SCREEN.blit(title_surface, title_rect)

        for button in characters_select_buttons:
            button.draw(SCREEN) 

    elif current_game_state == OPTIONS:
        title_surface = MAIN_MENU_TITLE_FONT.render("Налаштування", True, WHITE) 
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4 - 50))
        SCREEN.blit(title_surface, title_rect)

        volume_text = MAIN_MENU_BUTTON_FONT.render(f"Загальна гучність: {int(MASTER_SOUND_VOLUME * 100)}", True, WHITE)
        volume_text_rect = volume_text.get_rect(center=(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 100)) 
        SCREEN.blit(volume_text, volume_text_rect)

        for button in options_buttons:
            button.draw(SCREEN) 

    elif current_game_state == GAMEPLAY: 
        # Відображення текстового поля
        text_bg_rect = pygame.Rect(50, SCREEN_HEIGHT - 250, SCREEN_WIDTH - 100, 200)
        pygame.draw.rect(SCREEN, TRANSPARENT_BLACK, text_bg_rect, border_radius=10)

        # Анімація друку тексту
        if text_display_index < len(display_text):
            if current_time - text_display_timer > TYPING_SPEED:
                text_display_index += 1
                text_display_timer = current_time
        else: # Текст повністю надруковано
            if current_scene_data.get("auto_advance", False) and current_scene_data.get("next_scene"):
                auto_advance_delay = current_scene_data.get("auto_advance_delay", 3000)
                if current_time - text_display_timer > auto_advance_delay:
                    load_scene(current_scene_data["next_scene"])

        rendered_text = display_text[:text_display_index]
        
        words = rendered_text.split(' ')
        lines = []
        current_line = ""
        text_font = LOBBY_FONT
        for word in words:
            test_line = current_line + word + " "
            if text_font.size(test_line)[0] < (SCREEN_WIDTH - 120): 
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line) 

        text_y_start = SCREEN_HEIGHT - 230
        for i, line in enumerate(lines):
            text_surface = text_font.render(line, True, WHITE)
            text_rect = text_surface.get_rect(midtop=(SCREEN_WIDTH // 2, text_y_start + i * text_font.get_linesize()))
            SCREEN.blit(text_surface, text_rect)

        # Відображення кнопок вибору (якщо не auto_advance і текст повністю надрукований)
        if not current_scene_data.get("auto_advance", False) and text_display_index >= len(display_text):
            for button in scene_choice_buttons:
                button.draw(SCREEN)
    
    pygame.display.flip()
    clock.tick(FPS)