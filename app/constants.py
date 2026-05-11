from __future__ import annotations

from app.database.models import ProductCategory

MAIN_MENU_CATALOG = "Каталог"
MAIN_MENU_STORE = "Открыть магазин"
MAIN_MENU_REVIEWS = "Отзывы"
MAIN_MENU_SUPPORT = "Поддержка"
MAIN_MENU_ADMIN = "Админ-панель"
MAIN_MENU_BACK = "Назад"

ADMIN_MENU_ADD = "Добавить новый товар"
ADMIN_MENU_IMPORT = "Импорт из канала"
ADMIN_MENU_ACTIVE = "Активные объявления"
ADMIN_MENU_SOLD = "Проданные товары"

BUTTON_WRITE_ADMIN = "Написать админу"
BUTTON_DONE = "Готово"
BUTTON_CANCEL = "Отмена"
BUTTON_PUBLISH = "Опубликовать в канал и бот"
BUTTON_SAVE_BOT_ONLY = "Добавить только в бот"
BUTTON_EDIT = "Изменить"
BUTTON_DISCOUNT = "Сделать скидку"
BUTTON_REMOVE_DISCOUNT = "Удалить скидку"
BUTTON_MARK_SOLD = "Товар продан"
BUTTON_DELETE_FROM_LIST = "Удалить из списка"
BUTTON_BACK_TO_PREVIEW = "Назад к предпросмотру"

PAGE_SIZE = 10

CATEGORY_ORDER: tuple[ProductCategory, ...] = (
    ProductCategory.SHOES,
    ProductCategory.CLOTHING,
    ProductCategory.ACCESSORIES,
)
