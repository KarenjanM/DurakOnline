import logging
import os
from aiogram import Bot, Dispatcher
from durak_interface import DurakInterface
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from database import UsersDatabase, PartnersDatabase
from dotenv import load_dotenv

load_dotenv()

meta = MetaData()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot)
connect_cb = CallbackData('connect', 'action', 'chat_id', 'username')
engine = create_engine('sqlite:///users.db', echo=True)
users = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String),
    Column('chat_id', Integer, unique=True))

partners = Table(
    'partners', meta,
    Column('chat_id', Integer, primary_key=True),
    Column('partner_chat_id', Integer)
)
conn = engine.connect()
meta.create_all(engine)


users_db = UsersDatabase(connection=conn, table=users)
partners_db = PartnersDatabase(connection=conn, table=partners)

durak_interface = DurakInterface(bot=bot, partners_db=partners_db, users_db=users_db)
durak_games = dict()
