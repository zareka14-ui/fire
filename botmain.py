import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None
PORT = int(os.getenv("PORT", 8080))

# Ссылки на оплату (ЗАМЕНИ НА СВОИ)
SBER_LINK_5000 = "https://sberbank.com/sms/pbpn?requisiteNumber=79124591439"
SBER_LINK_7000 = "https://sberbank.com/sms/pbpn?requisiteNumber=79124591439"
SBER_LINK_15000 = "https://sberbank.com/sms/pbpn?requisiteNumber=79124591439"

# --- ТЕКСТ ПРОТИВОПОКАЗАНИЙ ---
CONTRA_TEXT = (
    "⚠️ **ПРОТИВОПОКАЗАНИЯ:**\n\n"
    "— беременность\n"
    "— онкологические заболевания\n"
    "— высокая температура\n"
    "— острые воспалительные процессы\n"
    "— кожные заболевания в стадии обострения\n"
    "— тромбозы, серьёзные сердечно-сосудистые заболевания\n\n"
    "При наличии сомнений — обязательно проконсультируйтесь со специалистом."
)

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- СОСТОЯНИЯ ---
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_city = State()
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_contra_confirm = State()
    waiting_for_payment_choice = State()
    waiting_for_payment_proof = State()

# --- КЛАВИАТУРЫ ---

def start_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚀 Записаться на массаж")]],
        resize_keyboard=True
    )

def city_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Уфа"), KeyboardButton(text="📍 Ижевск")]
        ],
        resize_keyboard=True
    )

def contra_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Прочитать противопоказания", callback_data="read_contra")],
        [InlineKeyboardButton(text="✅ Я ознакомлен(а)", callback_data="contra_ok")]
    ])

def payment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💆 Спина + ноги — 5000₽", url=SBER_LINK_5000)],
        [InlineKeyboardButton(text="💆 Спина + ноги + грудь — 7000₽", url=SBER_LINK_7000)],
        [InlineKeyboardButton(text="💆 Комплекс — 15000₽", url=SBER_LINK_15000)],
    ])

# --- ХЭНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    text = (
        "✨ **Запись на телесные правки и огненный массаж**\n\n"
        "Нажмите кнопку ниже, чтобы начать запись."
    )
    await message.answer(text, reply_markup=start_kb(), parse_mode="Markdown")

@dp.message(F.text == "🚀 Записаться на массаж")
async def start_form(message: types.Message, state: FSMContext):
    await message.answer("Шаг 1️⃣ Введите ваше **ФИО**:", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Registration.waiting_for_name)

@dp.message(Registration.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Шаг 2️⃣ Введите ваш **номер телефона** для связи:")
    await state.set_state(Registration.waiting_for_phone)

@dp.message(Registration.waiting_for_phone, F.text)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Шаг 3️⃣ Выберите **город**:", reply_markup=city_kb())
    await state.set_state(Registration.waiting_for_city)

@dp.message(Registration.waiting_for_city, F.text)
async def process_city(message: types.Message, state: FSMContext):
    if message.text not in ["📍 Уфа", "📍 Ижевск"]:
        return
    city = message.text.replace("📍 ", "")
    await state.update_data(city=city)
    await message.answer("Шаг 4️⃣ Введите удобный **день** (например: 12 марта):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.waiting_for_day)

@dp.message(Registration.waiting_for_day, F.text)
async def process_day(message: types.Message, state: FSMContext):
    await state.update_data(day=message.text)
    await message.answer("Шаг 5️⃣ Введите удобное **время** (например: 18:00):")
    await state.set_state(Registration.waiting_for_time)

@dp.message(Registration.waiting_for_time, F.text)
async def process_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer(
        "Перед оплатой ознакомьтесь с противопоказаниями:",
        reply_markup=contra_kb()
    )
    await state.set_state(Registration.waiting_for_contra_confirm)

@dp.callback_query(F.data == "read_contra")
async def show_contra(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(CONTRA_TEXT, parse_mode="Markdown")

@dp.callback_query(F.data == "contra_ok", Registration.waiting_for_contra_confirm)
async def contra_ok(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Шаг 6️⃣ Выберите вариант услуги и оплатите по ссылке:",
        reply_markup=payment_kb()
    )
    await callback.message.answer("После оплаты пришлите, пожалуйста, **скриншот чека** 📸", parse_mode="Markdown")
    await state.set_state(Registration.waiting_for_payment_proof)

@dp.message(Registration.waiting_for_payment_proof, F.photo | F.document)
async def process_payment_proof(message: types.Message, state: FSMContext):
    data = await state.get_data()

    # Сообщение админу
    if ADMIN_ID:
        try:
            report = (
                "🔥 **НОВАЯ ЗАЯВКА НА МАССАЖ**\n\n"
                f"👤 **ФИО:** {data.get('name')}\n"
                f"📞 **Телефон:** {data.get('phone')}\n"
                f"📍 **Город:** {data.get('city')}\n"
                f"🗓 **День:** {data.get('day')}\n"
                f"⏰ **Время:** {data.get('time')}\n"
                f"🆔 ID: `{message.from_user.id}`"
            )
            await bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
            await message.copy_to(ADMIN_ID)
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")

    await message.answer(
        "✅ **Спасибо!**\n\n"
        "Ваша заявка принята. Мы свяжемся с вами для подтверждения записи ✨",
        reply_markup=start_kb(),
        parse_mode="Markdown"
    )
    await state.clear()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
