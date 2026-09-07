from aiogram.fsm.state import State, StatesGroup


class CouponInput(StatesGroup):
    waiting_code = State()

class TopupInput(StatesGroup):
    waiting_method = State()
    waiting_paid_bdt = State()
    waiting_coin_amount = State()
    waiting_transaction_id = State()

class SearchInput(StatesGroup):
    waiting_query = State()

class ReviewInput(StatesGroup):
    waiting_rating = State()
    waiting_review = State()

class SupportInput(StatesGroup):
    waiting_message = State()

class AdminBroadcast(StatesGroup):
    waiting_message = State()

class AdminForceJoin(StatesGroup):
    waiting_channel_id = State()
    waiting_title = State()
    waiting_invite_link = State()

class AdminProductEdit(StatesGroup):
    waiting_product_id = State()
    waiting_field = State()
    waiting_value = State()

class AdminSupportReply(StatesGroup):
    waiting_reply = State()


class AdminAddCategory(StatesGroup):
    waiting_name = State()


class AdminAddProduct(StatesGroup):
    waiting_category = State()
    waiting_name = State()
    waiting_description = State()
    waiting_price_coin = State()
    waiting_price_stars = State()
    waiting_file = State()  # admin forwards/sends file here -> bot copies to storage channel
    waiting_preview = State()  # optional preview/sample file, or /skip


class AdminCoin(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()


class AdminCoupon(StatesGroup):
    waiting_code = State()
    waiting_type = State()
    waiting_value = State()
    waiting_limit = State()


class AdminBan(StatesGroup):
    waiting_user_id = State()


class LinkGenInput(StatesGroup):
    waiting_content = State()
    waiting_options = State()
