from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    waiting_reading_question = State()
    waiting_custom_concern = State()
    waiting_profile_field = State()
    waiting_photo_mode = State()
    waiting_photo_custom_request = State()
    waiting_referral_withdrawal = State()
