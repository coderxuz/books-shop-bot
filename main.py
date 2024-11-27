import asyncio
import logging
import sys
from os import getenv
import re
import json


import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ContentType
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv("TOKEN")

API_URL = getenv("API_URL")
print(API_URL)

dp = Dispatcher()


def check_user_exist(user_id: int) -> bool:
    response = requests.get(f"{API_URL}/auth/tg-exist?telegram_id={user_id}")
    data = response.json()
    if response.status_code != 200:
        return False
    print(response.json())
    return data.get("exist")


with open("translations.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_translations(lang, key):
    return translations.get(lang, {}).get(key, translations["ru"].get(key))


class Tokens(StatesGroup):
    access_token = State()
    refresh_token = State()


class SignForm(StatesGroup):
    fio = State()
    phone = State()
    role = State()
    login = State()
    password = State()


class UserSettings(StatesGroup):
    lang = State()
    logged_in = State()


reply_keyboards = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="btn1")], [KeyboardButton(text="btn2")]]
)


async def get_use_lang(message: Message, user_data):
    return (
        user_data.get("lang")
        if user_data.get("lang")
        else message.from_user.language_code
    )


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    user_data = await state.get_data()
    logging.info(user_data)
    lang_code = await get_use_lang(message, user_data)
    if check_user_exist(message.from_user.id):
        await state.update_data(logged_in=True)
        await message.answer(
            get_translations(lang_code, "welcome"), reply_markup=reply_keyboards
        )
    else:
        await message.answer(get_translations(lang_code, "please_login"))


@dp.message(Command("lang"))
async def sign(message: Message, state: FSMContext):
    await message.answer(
        "Please select language / Пожалуйста, выберите язык / Tilni tanlang, ",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="English"),
                    KeyboardButton(text="O'zbek"),
                    KeyboardButton(text="Русский"),
                ]
            ],
            resize_keyboard=True,
        ),
    )


@dp.message(lambda msg: msg.text in ["English", "O'zbek", "Русский"])
async def set_language(message: Message, state: FSMContext):
    match message.text:
        case "English":
            lang = "en"
        case "O'zbek":
            lang = "uz"
        case "Русский":
            lang = "ru"
    await state.update_data(lang=lang)
    user_data = await state.get_data()
    if user_data.get("logged_in"):
        await message.answer(
            get_translations(lang, "welcome"), reply_markup=reply_keyboards
        )
    else:
        await message.answer(
            get_translations(lang, "please_login"), reply_markup=ReplyKeyboardRemove()
        )


@dp.message(Command("sign"))
async def sign(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = await get_use_lang(message, user_data)
    await message.answer(get_translations(lang_code, "provide_fullname"))
    await state.set_state(SignForm.fio)


@dp.message(SignForm.fio)
async def proccess_fio(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = await get_use_lang(message, user_data)
    regex_for_fio = r"^(?:[A-Za-zА-Яа-яЁёҚқҲҳЎўҒғ]+\s){2}[A-Za-zА-Яа-яЁёҚқҲҳЎўҒғ]+$"
    if not message.text or not re.match(regex_for_fio, message.text):
        return await message.answer(get_translations(lang_code, "provide_fullname"))
    await state.update_data(fio=message.text)
    await state.set_state(SignForm.phone)
    await message.answer(get_translations(lang_code, "provide_number"), reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_translations(lang_code, "share_number"), request_contact=True)],
            
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    ))

@dp.message(SignForm.phone,F.content_type == ContentType.CONTACT)
async def process_contact(message:Message, state:FSMContext):
    if not message.contact:
        return await message.answer("No contact was shared. Please share your contact.")
    phone_number = message.contact.phone_number
    user_data = await state.get_data()
    logging.info(f"{user_data} , 'in contact' ")
    lang_code = await get_use_lang(message, user_data)
    
    await state.update_data(phone=phone_number)
    
    await state.set_state(SignForm.role)
    await message.answer(
        get_translations(lang_code, "provide_role"),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=get_translations(lang_code, "seller")),
                    KeyboardButton(text=get_translations(lang_code, "user")),
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        ),
    )


@dp.message(SignForm.role)
async def proccess_role(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = await get_use_lang(message, user_data)
    if not message.text or message.text not in [
        get_translations(lang_code, "seller"),
        get_translations(lang_code, "user"),
    ]:
        await message.answer(get_translations(lang_code, "provide_role"))
        return
    if message.text == get_translations(lang_code, "seller"):
        await state.update_data(role="seller")
    elif message.text == get_translations(lang_code, "user"):
        await state.update_data(role="user")
    await message.answer(
        get_translations(lang_code, "provide_login")
    )
    await state.set_state(SignForm.login)

@dp.message(SignForm.login)
async def proccess_login(message:Message, state:FSMContext):
    user_data = await state.get_data()
    lang_code = await get_use_lang(message, user_data)
    regex_for_latin_number = "^[a-zA-Z]+$"
    if not message.text or not re.match(regex_for_latin_number, message.text):
        return await message.answer(get_translations(lang_code, "provide_login"))
    await state.update_data(login = message.text)
    await message(get_translations(lang_code, "provide_password"))
    await state.set_state(SignForm.password)


async def main():
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
