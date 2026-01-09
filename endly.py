import asyncio
import json
import random
from pathlib import Path
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===  ТОКЕН ===
API_TOKEN ="8541059856:AAG1mOsebPWXvQHFVd-1s_aUoMTq24i-QyU"

# Инициализация бота
bot = Bot(token="8541059856:AAG1mOsebPWXvQHFVd-1s_aUoMTq24i-QyU")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM
class LearningStates(StatesGroup):
    waiting_for_translation = State()
    adding_word = State()

# Класс для работы с данными
class UserData:
    def __init__(self):
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        self.words_file = self.data_dir / 'words.json'
        self.load_data()
    
    def load_data(self):
        if self.words_file.exists():
            with open(self.words_file, 'r', encoding='utf-8') as f:
                self.words = json.load(f)
        else:
            self.words = {}
    
    def save_data(self):
        with open(self.words_file, 'w', encoding='utf-8') as f:
            json.dump(self.words, f, ensure_ascii=False, indent=2)
    
    def get_user_words(self, user_id):
        user_id = str(user_id)
        return self.words.get(user_id, {})
    
    def add_user_word(self, user_id, english, russian):
        user_id = str(user_id)
        if user_id not in self.words:
            self.words[user_id] = {}
        self.words[user_id][english] = russian
        self.save_data()
        return True
    
    def remove_user_word(self, user_id, english):
        user_id = str(user_id)
        if user_id in self.words and english in self.words[user_id]:
            del self.words[user_id][english]
            self.save_data()
            return True
        return False



# ========== КОМАНДЫ БОТА ==========

# Стартовая команда
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = f"""🇬🇧 Привет, {message.from_user.first_name}!
Добро пожаловать к Engly!

📚 Доступные команды:
/start - Начать
/add_word - Добавить слово
/my_words - Мои слова
/practice - Практика
/quiz - Викторина
/help - Помощь

Выберите действие или введите команду!"""
    await message.answer(welcome_text)

# Помощь
@dp.message(Command('help'))
async def cmd_help(message: Message):
    help_text = """📖 Помощь по командам:

• /add_word - Добавить слово для изучения
• /my_words - Посмотреть все слова
• /practice - Практика перевода
• /quiz - Викторина с выбором ответа
• /help - Эта справка

Пример добавления слова:
apple - яблоко
house - дом
book - книга"""
    await message.answer(help_text)

# Добавление слова
@dp.message(Command('add_word'))
async def cmd_add_word(message: Message, state: FSMContext):
    await message.answer("Введите слово на английском и перевод через дефис:\n\nПример: apple - яблоко")
    await state.set_state(LearningStates.adding_word)

# Обработка добавления слова
@dp.message(LearningStates.adding_word)
async def process_add_word(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        if ' - ' in text:
            parts = text.split(' - ', 1)
        elif '-' in text:
            parts = text.split('-', 1)
        else:
            await message.answer("Используйте формат: английское слово - перевод")
            return
        
        if len(parts) != 2:
            await message.answer("Неверный формат. Пример: apple - яблоко")
            return
        
        english = parts[0].strip().lower()
        russian = parts[1].strip().lower()
        
        if not english or not russian:
            await message.answer("Оба поля должны быть заполнены")
            return
        
        user_data.add_user_word(message.from_user.id, english, russian)
        
        await message.answer(f"✅ Слово добавлено!\n\n🇬🇧 {english}\n🇷🇺 {russian}")
        
        # Кнопки для дальнейших действий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_more")],
            [InlineKeyboardButton(text="📚 Мои слова", callback_data="my_words_list")]
        ])
        await message.answer("Что дальше?", reply_markup=keyboard)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error adding word: {e}")
        await message.answer("Ошибка при добавлении слова")
        await state.clear()

# Показать слова пользователя
@dp.message(Command('my_words'))
async def cmd_my_words(message: Message):
    words = user_data.get_user_words(message.from_user.id)
    
    if not words:
        await message.answer("У вас пока нет слов. Добавьте первое слово с помощью /add_word")
        return
    
    words_list = "📚 Ваши слова:\n\n"
    for i, (eng, rus) in enumerate(words.items(), 1):
        words_list += f"{i}. 🇬🇧 {eng} - 🇷🇺 {rus}\n"
    
    # Кнопки для удаления (первые 5 слов)
    keyboard_buttons = []
    word_items = list(words.items())[:5]
    
    for eng, rus in word_items:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"❌ Удалить '{eng}'", 
                callback_data=f"remove_{eng}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔁 Практиковать", callback_data="practice_now"),
        InlineKeyboardButton(text="🎯 Викторина", callback_data="quiz_now")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(words_list, reply_markup=keyboard)

# Удаление слова
@dp.callback_query(F.data.startswith("remove_"))
async def remove_word_callback(callback: CallbackQuery):
    english_word = callback.data.replace("remove_", "")
    
    if user_data.remove_user_word(callback.from_user.id, english_word):
        await callback.message.answer(f"✅ Слово '{english_word}' удалено!")
    else:
        await callback.answer("Слово не найдено")
    
    await callback.answer()

# Практика
@dp.message(Command('practice'))
async def cmd_practice(message: Message, state: FSMContext):
    await start_practice_session(message, state)

async def start_practice_session(message: Message, state: FSMContext):
    words = user_data.get_user_words(message.from_user.id)
    
    if not words:
        await message.answer("Сначала добавьте слова с помощью /add_word")
        return
    
    # Выбираем случайное русское слово
    russian_words = list(words.values())
    random_russian = random.choice(russian_words)
    
    # Находим английское слово
    correct_english = None
    for eng, rus in words.items():
        if rus == random_russian:
            correct_english = eng
            break
    
    if not correct_english:
        await message.answer("Ошибка: не найден перевод")
        return
    
    await state.update_data(correct_answer=correct_english)
    await state.set_state(LearningStates.waiting_for_translation)
    
    await message.answer(f"📝 Переведите на английский:\n\n🇷🇺 {random_russian}")

# Проверка перевода в практике
@dp.message(LearningStates.waiting_for_translation)
async def check_translation(message: Message, state: FSMContext):
    user_answer = message.text.strip().lower()
    data = await state.get_data()
    correct_answer = data.get('correct_answer', '')
    
    if user_answer == correct_answer:
        response = f"✅ Правильно!\n🇬🇧 {correct_answer}"
        
        # Случайный комплимент
        compliments = ["Отлично!", "Прекрасно!", "Великолепно!", "Так держать!", "Идеально!"]
        response += f"\n\n{random.choice(compliments)}"
    else:
        response = f"❌ Почти правильно!\nПравильно: 🇬🇧 {correct_answer}"
    
    await message.answer(response)
    
    # Предлагаем продолжить
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Еще слово", callback_data="practice_more")],
        [InlineKeyboardButton(text="📚 Мои слова", callback_data="my_words_list")],
        [InlineKeyboardButton(text="🎯 Викторина", callback_data="quiz_now")]
    ])
    
    await message.answer("Продолжим?", reply_markup=keyboard)
    await state.clear()

# Викторина
@dp.message(Command('quiz'))
async def cmd_quiz(message: Message):
    await start_quiz_session(message)

async def start_quiz_session(message: Message):
    words = user_data.get_user_words(message.from_user.id)
    
    if not words or len(words) < 3:
        await message.answer("Для викторины нужно минимум 3 слова. Добавьте слова через /add_word")
        return
    
    # Выбираем случайное английское слово
    english_word = random.choice(list(words.keys()))
    correct_translation = words[english_word]
    
    # Собираем варианты ответов
    all_translations = list(words.values())
    wrong_translations = [t for t in all_translations if t != correct_translation]
    
    if len(wrong_translations) < 3:
        # Дублируем, если мало уникальных переводов
        while len(wrong_translations) < 3:
            wrong_translations.append(random.choice(all_translations))
    
    # Выбираем 3 неправильных варианта
    wrong_options = random.sample(wrong_translations, min(3, len(wrong_translations)))
    
    # Создаем все варианты
    options = wrong_options + [correct_translation]
    random.shuffle(options)
    
    # Определяем индекс правильного ответа
    correct_index = options.index(correct_translation)
    
    # Создаем клавиатуру
    keyboard_buttons = []
    for i, option in enumerate(options):
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=option, 
                callback_data=f"quiz_answer_{i}_{correct_index}_{english_word}"
            )
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(f"🇬🇧 Выберите перевод слова:\n\n<b>{english_word}</b>", 
                         reply_markup=keyboard, 
                         parse_mode='HTML')

# Обработка ответов в викторине
@dp.callback_query(F.data.startswith("quiz_answer_"))
async def process_quiz_answer(callback: CallbackQuery):
    try:
        # Извлекаем данные из callback
        parts = callback.data.split('_')
        if len(parts) < 5:
            await callback.answer("Ошибка в данных")
            return
        
        user_choice = int(parts[2])
        correct_index = int(parts[3])
        english_word = '_'.join(parts[4:])
        
        # Получаем перевод
        words = user_data.get_user_words(callback.from_user.id)
        correct_translation = words.get(english_word, "неизвестно")
        
        if user_choice == correct_index:
            response = f"✅ Правильно!\n🇬🇧 {english_word} = 🇷🇺 {correct_translation}"
            
            # Случайная похвала
            praises = ["Отличная работа!", "Вы умничка!", "Блестяще!", "Супер!", "Верно!"]
            response += f"\n\n{random.choice(praises)}"
        else:
            response = f"❌ Неправильно\nПравильный ответ: 🇷🇺 {correct_translation}"
        
        # Редактируем сообщение с результатом
        await callback.message.edit_text(response)
        
        # Кнопки для продолжения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Новая викторина", callback_data="quiz_now")],
            [InlineKeyboardButton(text="📚 Мои слова", callback_data="my_words_list")],
            [InlineKeyboardButton(text="📝 Практика", callback_data="practice_now")]
        ])
        
        await callback.message.answer("Что дальше?", reply_markup=keyboard)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Quiz error: {e}")
        await callback.answer("Произошла ошибка")

# ========== ОБРАБОТЧИКИ INLINE КНОПОК ==========

@dp.callback_query(F.data == "add_more")
async def add_more_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите слово и перевод через дефис:")
    await state.set_state(LearningStates.adding_word)
    await callback.answer()

@dp.callback_query(F.data == "my_words_list")
async def my_words_list_callback(callback: CallbackQuery):
    await cmd_my_words(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "practice_now")
async def practice_now_callback(callback: CallbackQuery, state: FSMContext):
    await start_practice_session(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "practice_more")
async def practice_more_callback(callback: CallbackQuery, state: FSMContext):
    await start_practice_session(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "quiz_now")
async def quiz_now_callback(callback: CallbackQuery):
    await start_quiz_session(callback.message)
    await callback.answer()

# ========== ЗАПУСК БОТА ==========

async def main():
    print("Бот запускается...")
    print("Для остановки нажмите Ctrl+C")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nБот остановлен")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())