from telebot import TeleBot

TOKEN = '8957734826:AAGqRDleUdLICnkjuabbhWppz807q8JA9js'

bot = TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот на бесплатном хостинге! 🚀")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

bot.infinity_polling()
