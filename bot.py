import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8779463761:AAHZDWENcK8JdpUofu8WL3iaXuXbqFhFP5s"  # Вставь токен от BotFather
DATA_FILE = "user_data.json"

# --- БАЗА ДАННЫХ (JSON для простоты) ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ЛОГИКА СИСТЕМЫ ---
def get_user(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "streak": 0,          # Дней подряд
            "last_date": "",      # Последняя дата тренировки
            "penalty": False,     # Флаг штрафа (если True, нормы х2)
            "stats": {"str": 1, "int": 1, "end": 1, "agi": 1},
            "points": 0,          # Свободные очки
            "completed_today": False,
            "rest_days": 2        # Всего 2 дня отдыха в неделю (пока просто счетчик)
        }
        save_data(data)
    return data[uid]

def update_user(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

def get_daily_targets(user):
    # Базовая норма
    pushups = 100
    squats = 100
    crunches = 100
    run_km = 10
    
    # Бонус от Силы (+5 отжиманий, приседаний, скручиваний за 1 очко Силы)
    bonus_str = (user["stats"]["str"] - 1) * 5
    pushups += bonus_str
    squats += bonus_str
    crunches += bonus_str
    
    # Штраф (х2)
    if user["penalty"]:
        pushups *= 2
        squats *= 2
        crunches *= 2
        run_km *= 2

    # Бонус от Интеллекта (чтение)
    reading = 0
    if user["stats"]["int"] > 1:
        reading = (user["stats"]["int"] - 1) * 2 # 2 страницы за уровень

    return {
        "pushups": pushups,
        "squats": squats,
        "crunches": crunches,
        "run": run_km,
        "reading": reading
    }

# --- КЛАВИАТУРЫ ---
def main_menu():
    kb = [
        [KeyboardButton(text="📜 Квест на сегодня"), KeyboardButton(text="👤 Статус")],
        [KeyboardButton(text="📈 Прокачка"), KeyboardButton(text="✅ Выполнил квест")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def stat_menu():
    kb = [
        [InlineKeyboardButton(text="💪 Сила (+5 к нормативу)", callback_data="up_str")],
        [InlineKeyboardButton(text="🧠 Интеллект (+2 стр. чтения)", callback_data="up_int")],
        [InlineKeyboardButton(text="🏃 Выносливость (+1 км бега)", callback_data="up_end")],
        [InlineKeyboardButton(text="🤸 Ловкость (пока заглушка)", callback_data="up_agi")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ХЭНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(
        f"⚡️ **СИСТЕМА АКТИВИРОВАНА** ⚡️\n\n"
        f"Приветствую, {message.from_user.first_name}.\n"
        f"Ты не просто пользователь. Ты создатель этой системы.\n"
        f"Твоя цель — ежедневный квест. Не выполнишь — Зона Наказания.\n\n"
        f"Используй меню ниже для управления.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "📜 Квест на сегодня")
async def show_quest(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user["completed_today"]:
        await message.answer("✅ Ты уже выполнил квест на сегодня. Отдыхай, Воин.")
        return

    targets = get_daily_targets(user)
    
    text = f"📜 **ЕЖЕДНЕВНЫЙ КВЕСТ**\n"
    if user["penalty"]:
        text += "⚠️ **ВНИМАНИЕ: ЗОНА НАКАЗАНИЯ!** Нормы удвоены!\n"
    text += f"\n"
    text += f"💪 Отжимания: {targets['pushups']}\n"
    text += f"🦵 Приседания: {targets['squats']}\n"
    text += f"🔥 Скручивания: {targets['crunches']}\n"
    text += f"🏃 Бег: {targets['run']} км\n"
    if targets['reading'] > 0:
        text += f"📖 Чтение: {targets['reading']} страниц\n"
    
    text += f"\nДедлайн: 23:59. Не подведи."
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👤 Статус")
async def show_status(message: types.Message):
    user = get_user(message.from_user.id)
    targets = get_daily_targets(user)
    
    text = f"👤 **СТАТУС**\n\n"
    text += f"🔥 Огонёк (Streak): {user['streak']} дней\n"
    text += f"📊 Свободные очки: {user['points']}\n\n"
    text += f"**ХАРАКТЕРИСТИКИ:**\n"
    text += f"💪 Сила: {user['stats']['str']}\n"
    text += f"🧠 Интеллект: {user['stats']['int']}\n"
    text += f"🏃 Выносливость: {user['stats']['end']}\n"
    text += f"🤸 Ловкость: {user['stats']['agi']}\n\n"
    text += f"*Текущий норматив:* {targets['pushups']} отжим., {targets['squats']} присед., {targets['crunches']} скруч., {targets['run']} км."
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📈 Прокачка")
async def show_upgrade(message: types.Message):
    user = get_user(message.from_user.id)
    if user["points"] <= 0:
        await message.answer("У тебя нет свободных очков. Выполняй квесты, чтобы получить их.")
        return
    
    await message.answer(
        f"У тебя {user['points']} очков. Куда вложим?",
        reply_markup=stat_menu()
    )

@dp.callback_query(F.data.startswith("up_"))
async def process_upgrade(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if user["points"] <= 0:
        await callback.answer("Нет очков!")
        return

    action = callback.data
    if action == "up_str":
        user["stats"]["str"] += 1
        user["points"] -= 1
        await callback.answer("Сила +1. Норматив увеличен!")
    elif action == "up_int":
        user["stats"]["int"] += 1
        user["points"] -= 1
        await callback.answer("Интеллект +1. Добавлено чтение!")
    elif action == "up_end":
        user["stats"]["end"] += 1
        user["points"] -= 1
        await callback.answer("Выносливость +1. Бег стал сложнее!")
    elif action == "up_agi":
        user["stats"]["agi"] += 1
        user["points"] -= 1
        await callback.answer("Ловкость +1. (Эффект в разработке)")
    
    update_user(callback.from_user.id, user)
    
    # Обновляем сообщение
    targets = get_daily_targets(user)
    await callback.message.edit_text(
        f"📈 **ПРОКАЧКА**\n\n"
        f"Осталось очков: {user['points']}\n"
        f"💪 Сила: {user['stats']['str']} (Норматив: {targets['pushups']})\n"
        f"🧠 Интеллект: {user['stats']['int']} (Чтение: {targets['reading']} стр.)\n"
        f"🏃 Выносливость: {user['stats']['end']} (Бег: {targets['run']} км)\n"
        f"🤸 Ловкость: {user['stats']['agi']}",
        reply_markup=stat_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "✅ Выполнил квест")
async def complete_quest(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user["completed_today"]:
        await message.answer("Ты уже закрыл квест сегодня. Не жульничай.")
        return

    # Начисляем награды
    user["completed_today"] = True
    user["streak"] += 1
    user["points"] += 3  # Даем 3 очка за выполнение
    user["penalty"] = False # Снимаем штраф, если был
    user["last_date"] = datetime.now().strftime("%Y-%m-%d")
    
    update_user(message.from_user.id, user)
    
    await message.answer(
        f"✅ **КВЕСТ ЗАКРЫТ!**\n\n"
        f"Ты получил 3 очка характеристик.\n"
        f"Огонёк: {user['streak']} дней.\n"
        f"Так держать, Охотник.",
        parse_mode="Markdown"
    )

# --- ЕЖЕДНЕВНАЯ ПРОВЕРКА (Штрафы) ---
async def daily_check():
    # Эта функция запускается каждый день в 00:00
    while True:
        now = datetime.now()
        # Ждем до полуночи
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        # В полночь проверяем всех
        data = load_data()
        for uid, user in data.items():
            if not user["completed_today"]:
                # Если не выполнил — штраф на следующий день
                user["penalty"] = True
                user["streak"] = 0 # Сбрасываем огонек
                update_user(uid, user)
                try:
                    await bot.send_message(
                        int(uid), 
                        "⚠️ **ВНИМАНИЕ!**\n\nТы не выполнил ежедневный квест.\nВход в **Зону Наказания** разрешен.\nЗавтра твои нормативы удвоены. Огонек сброшен.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass # Если пользователь заблокировал бота
            else:
                # Сбрасываем флаг выполнения на новый день
                user["completed_today"] = False
                update_user(uid, user)

# --- ЗАПУСК ---
async def main():
    # Запускаем фоновую задачу штрафов
    asyncio.create_task(daily_check())
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
