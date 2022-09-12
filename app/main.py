from aiogram import Dispatcher, executor
from create_bot import dp, bot, WEBHOOK_URL
from handlers import command_handlers, cbq_handlers, message_handlers

command_handlers.register_command_handlers(dp)
cbq_handlers.register_cbq_handlers(dp)
message_handlers.register_message_handlers(dp)


async def on_startup(dp: Dispatcher):
    print('startup')
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp: Dispatcher):
    print('shutdown')
    await bot.delete_webhook()


executor.start_webhook(dispatcher=dp,
                       webhook_path='/',
                       skip_updates=True,
                       on_startup=on_startup,
                       on_shutdown=on_shutdown)
