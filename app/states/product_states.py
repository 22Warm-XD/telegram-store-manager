from aiogram.fsm.state import State, StatesGroup


class ProductStates(StatesGroup):
    waiting_for_photos = State()
    waiting_for_title = State()
    waiting_for_size = State()
    waiting_for_price = State()
    waiting_for_condition = State()
    waiting_for_description = State()
    waiting_for_category = State()
    preview = State()

    editing_photos = State()
    editing_title = State()
    editing_size = State()
    editing_price = State()
    editing_condition = State()
    editing_description = State()
    editing_category = State()

    waiting_for_discount_price = State()

    importing_channel_posts = State()
    import_waiting_for_title = State()
    import_waiting_for_size = State()
    import_waiting_for_condition = State()
    import_waiting_for_price = State()
    import_waiting_for_category = State()

    waiting_for_store_color = State()
    waiting_for_store_avatar = State()
    waiting_for_store_cover = State()
