from aiogram import Router

from handlers import common, features, force_join, help, start, store, checkout, topup, wallet, referral, orders, linkgen
from handlers.admin import admin_router

root_router = Router(name="root")
root_router.include_router(common.router)
root_router.include_router(start.router)
root_router.include_router(help.router)
root_router.include_router(force_join.router)
root_router.include_router(features.router)
root_router.include_router(topup.router)
root_router.include_router(store.router)
root_router.include_router(checkout.router)
root_router.include_router(wallet.router)
root_router.include_router(referral.router)
root_router.include_router(orders.router)
root_router.include_router(linkgen.router)
root_router.include_router(admin_router)
