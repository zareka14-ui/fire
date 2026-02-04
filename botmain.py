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

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ТЕКСТ ПРОТИВОПОКАЗАНИЙ ---
CONTRA_TEXT = (
    "⚠️ **ПРОТИВОПОКАЗАНИЯ**\n\n"
    "Процедура не проводится при:\n"
    "— беременности\n"
    "— онкологических заболеваниях\n"
    "— острых воспалительных процессах\n"
    "— повышенной температуре\n"
    "— кожных заболеваниях в стадии обострения\n"
    "— серьёзных сердечно-сосудистых заболеваниях\n\n"
    "Если у вас есть сомнения — обязательно проконсультируйтесь со специалистом."
)

# --- СОСТОЯНИЯ ---
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_city = State()
    waiting_for_day_time = State()
    waiting_for_contra_ok = State()
    waiting_for_service = State()
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
            [KeyboardButton(text="📍 Уфа")],
            [KeyboardButton(text="📍 Ижевск")]
        ],
        resize_keyboard=True
    )

def contra_start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Прочитать противопоказания", callback_data="read_contra")]
    ])

def contra_accept_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я согласен(а)", callback_data="contra_ok")]
    ])

def services_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💆 Спина + ноги — 5000₽", callback_data="service_5000")],
        [InlineKeyboardButton(text="💆 Спина + ноги + грудь — 7000₽", callback_data="service_7000")],
        [InlineKeyboardButton(text="🔥 Комплекс — 15000₽", callback_data="service_15000")]
    ])

def payment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить через Сбер", url="https://www.sberbank.ru")],
    ])

# --- ХЭНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    text = (
        "✨ Добро пожаловать!\n\n"
        "Здесь вы можете записаться на телесные правки и огненный массаж.\n\n"
        "Нажмите кнопку ниже, чтобы начать запись 👇"
    )
    await message.answer(text, reply_markup=start_kb())

@dp.message(F.text == "🚀 Записаться на массаж")
async def start_form(message: types.Message, state: FSMContext):
    await message.answer("Введите ваше **ФИО**:", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name, F.text)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ваш **номер телефона** для связи:", parse_mode="Markdown")
    await state.set_state(Form.waiting_for_phone)

@dp.message(Form.waiting_for_phone, F.text)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Выберите **город**:", reply_markup=city_kb(), parse_mode="Markdown")
    await state.set_state(Form.waiting_for_city)

@dp.message(Form.waiting_for_city, F.text)
async def get_city(message: types.Message, state: FSMContext):
    if message.text not in ["📍 Уфа", "📍 Ижевск"]:
        return
    await state.update_data(city=message.text.replace("📍 ", ""))
    await message.answer("Напишите, пожалуйста, **удобный день и время** для записи (например: `15 марта после 18:00`):", parse_mode="Markdown")
    await state.set_state(Form.waiting_for_day_time)

@dp.message(Form.waiting_for_day_time, F.text)
async def get_day_time(message: types.Message, state: FSMContext):
    await state.update_data(day_time=message.text)
    await message.answer(
        "Перед продолжением ознакомьтесь с противопоказаниями:",
        reply_markup=contra_start_kb()
    )
    await state.set_state(Form.waiting_for_contra_ok)

@dp.callback_query(F.data == "read_contra")
async def show_contra(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        CONTRA_TEXT + "\n\nНажмите кнопку ниже, чтобы подтвердить согласие.",
        parse_mode="Markdown",
        reply_markup=contra_accept_kb()
    )

@dp.callback_query(F.data == "contra_ok")
async def contra_ok(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Спасибо за подтверждение.\n\nВыберите вариант услуги:",
        reply_markup=services_kb()
    )
    await state.set_state(Form.waiting_for_service)

@dp.callback_query(F.data.startswith("service_"))
async def choose_service(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    service_map = {
        "service_5000": "Спина + ноги — 5000₽",
        "service_7000": "Спина + ноги + грудь — 7000₽",
        "service_15000": "Комплекс — 15000₽"
    }
    service = service_map.get(callback.data)
    await state.update_data(service=service)

    text = (
        f"Вы выбрали:\n**{service}**\n\n"
        "Нажмите кнопку ниже для оплаты и после этого пришлите **скриншот чека**."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=payment_kb())
    await state.set_state(Form.waiting_for_payment_proof)

@dp.message(Form.waiting_for_payment_proof, F.photo)
async def get_payment_proof(message: types.Message, state: FSMContext):
    data = await state.get_data()

    # Отправка админу
    if ADMIN_ID:
        try:
            report = (
                "🔥 **НОВАЯ ЗАЯВКА НА МАССАЖ**\n\n"
                f"👤 **ФИО:** {data.get('name')}\n"
                f"📞 **Телефон:** {data.get('phone')}\n"
                f"📍 **Город:** {data.get('city')}\n"
                f"🗓 **Удобное время:** {data.get('day_time')}\n"
                f"💆 **Услуга:** {data.get('service')}\n"
                f"🆔 ID: `{message.from_user.id}`"
            )
            await bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
            await message.copy_to(ADMIN_ID)
            logger.info("Заявка отправлена админу")
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")

    await message.answer(
        "✨ **Спасибо!**\n\n"
        "Ваша заявка принята. Мы свяжемся с вами для подтверждения записи 💬",
        parse_mode="Markdown"
    )
    await state.clear()

# --- KEEP ALIVE ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()

    await bot.delete_webhook(drop_pending_updates=True)

    # Тест админу при старте
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "✅ Бот запущен и может отправлять сообщения админу")
        except Exception as e:
            logger.error(f"❌ Бот не может написать админу: {e}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
