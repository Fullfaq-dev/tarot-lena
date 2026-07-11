from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    waiting_reading_question = State()
    waiting_custom_concern = State()
    waiting_profile_field = State()
    waiting_photo_mode = State()
    waiting_photo_custom_request = State()
    waiting_withdrawal_amount = State()
    waiting_withdrawal_wallet = State()
    waiting_memory_add = State()
    waiting_zen_question = State()
    waiting_rune_question = State()
    waiting_stone_query = State()
    waiting_bracelet_query = State()
    waiting_partner_birth_date = State()
    waiting_product_question = State()
    waiting_reading_followup = State()
