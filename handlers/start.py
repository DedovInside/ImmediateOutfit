"""
Хендлер /start - приветственное сообщение.
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards.inline import start_keyboard

router = Router()

WELCOME_TEXT = (
    "Привет! 👋 Я помогу тебе быстро выбрать образ на день - "
    "без долгих раздумий перед шкафом.\n\n"
    "Больше не нужно стоять и сомневаться - "
    "за пару вопросов подберу образ, который будет "
    "уместным, комфортным и придаст уверенности.\n\n"
    "Я учитываю:\n"
    "- куда ты идёшь\n"
    "- формат дня\n"
    "- твой стиль\n\n"
    "Ответь на несколько коротких вопросов - "
    "и я предложу готовые варианты образов ✨\n\n"
    "Готов начать?"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=start_keyboard())

