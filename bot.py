from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup

import logging, configparser, sqlite3
from datetime import date

# Global settings
settings_path = 'settings.ini'
db_path = 'database.db'


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

config = configparser.ConfigParser()
config.read(settings_path)

def start(update, context):
    # Inserisce il nuovo utente/gruppo nel database
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT * FROM utenti WHERE chat_id = ?", (update.message.chat.id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO utenti (chat_id) VALUES (?)", (update.message.chat.id,))
        con.commit()
    con.close()
    
    # Send home message
    home(update, context)

def stop(update, context):
    context.bot.sendMessage(chat_id=update.message.chat_id, text="Sei stato tolto dall'elenco degli utenti, per ricominciare premi /start")
    # Toglie la chat dal database
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("DELETE FROM utenti WHERE chat_id = ?", (update.message.chat.id,))
    con.commit()
    con.close()

def info(update, context):
    markup = [[InlineKeyboardButton('Source code on Github', url='https://github.com/marsDurden/GutembergBot')]]
    markup = InlineKeyboardMarkup(markup)
    context.bot.sendMessage(chat_id=update.message.chat_id, text="Bot opensource fatto da @ThanksLory")

def home(update, context):
    context.bot.sendMessage(chat_id=update.message.chat_id, text="Ciao! Io gestisco i turni delle chiusure dell'Aula studio Pollaio")
    inizializza_settimana(context)

def turni(update, context, chat_id=None):
    # Set chat_id
    chat_id = update.message.chat.id if chat_id is None else chat_id
    
    # Get last week in database
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT id, settimana, lun, mar, mer, gio, ven FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
    row = c.fetchone()
    id_turno = row[0]
    row = row[1:]
    # Skeleton text
    text = "*Turni chiusura Pollaio*\n_{}° settimana dell'anno_\n\nLunedì: {}\nMartedì: {}\nMercoledì: {}\nGiovedì: {}\nVenerdì: {}\n\nPrenotati qui sotto:"
    
    # Make buttons
    giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
    i = 0; keyboard = []
    for turn in row[1:]:
        if turn is None:
            keyboard.append([InlineKeyboardButton(giorni[i], callback_data='1-'+str(id_turno)+'-'+str(i))])
        i += 1
    keyboard.append([InlineKeyboardButton('- reset -', callback_data='2-'+str(id_turno))])
    keyboard = InlineKeyboardMarkup(keyboard)
    
    # Send message
    context.bot.sendMessage(chat_id=chat_id,
                            text=text.format(*row),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.MARKDOWN)

def callback_turni(update, context):
    data = update.callback_query.data[2:].split('-')
    
    # Get name of user
    name = update.callback_query.from_user.first_name + ' ' + update.callback_query.from_user.last_name
    if name == ' ':
        name = update.callback_query.from_user.username
    
    # Insert name
    con = sqlite3.connect(db_path)
    c = con.cursor()
    colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
    c.execute("UPDATE turns SET " + colonne[int(data[1])] + " = ? WHERE ID = ?", (name, data[0]) )
    con.commit()
    con.close()
    
    # Delete message
    context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                              message_id=update.callback_query.message.message_id)
    
    # Send new message to group
    turni(None, context, chat_id=update.callback_query.message.chat.id)

def reset_turni(update, context):
    data = update.callback_query.data[2:]
    
    # Resetta i turni della settimana
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("UPDATE turns SET lun=NULL, mar=NULL, mer=NULL, gio=NULL, ven=NULL, sab=NULL, dom=NULL WHERE ID = ?", (data,))
    con.commit()
    con.close()
    
    # Delete message
    context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                              message_id=update.callback_query.message.message_id)
    
    # Send new message to group
    turni(None, context, chat_id=update.callback_query.message.chat.id)
    

def inizializza_settimana(context):
    # Get alla chats
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT chat_id FROM utenti")
    id_list = c.fetchall()
    for chat_id in id_list:
        chat_id = chat_id[0]
        # Set new week to null for all days
        week_number = date.today().strftime("%U")
        c.execute("SELECT * FROM turns WHERE settimana = ? AND chat_id = ?", (week_number, chat_id ))
        if c.fetchone() is None:
            c.execute("INSERT INTO turns (chat_id, settimana, lun, mar, mer, gio, ven, sab, dom) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)",
                    (chat_id, week_number))
            con.commit()
    con.close()
    
    # Send new message to group
    turni(None, context, chat_id=chat_id)

def error(update, context):
    try:
        # Normal message
        context.bot.sendMessage(config['BOT']['adminID'],parse_mode=ParseMode.MARKDOWN, text=('*ERROR*\nID: `%s`\ntext: %s\ncaused error: _%s_' % (update.message.chat_id, update.message.text, context.error)))
        logger.warn('Update "%s" caused error "%s"' % (update.message.text, context.error))
    except:
        # Callback message
        context.bot.sendMessage(config['BOT']['adminID'],parse_mode=ParseMode.MARKDOWN, text=('*ERROR*\nID: `%s`\ntext: %s\ncaused error: _%s_' % (update.callback_query.message.chat_id, update.callback_query.data, context.error)))
        logger.warn('Update "%s" caused error "%s"' % (update.callback_query.data, context.error))

def main():
    updater = Updater(token=config['BOT']['token'], use_context=True) 
    
    dispatcher = updater.dispatcher
    
    # Bot commands
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('home', home))
    dispatcher.add_handler(CommandHandler('stop', stop))
    
    dispatcher.add_handler(CommandHandler('info', info))
    
    dispatcher.add_handler(CommandHandler('turni', turni))
    
    # Callback
    # 0 | nothing
    # 1 | new name
    # 2 | reset turns
    dispatcher.add_handler(CallbackQueryHandler(callback_turni, pattern='^1-'))
    dispatcher.add_handler(CallbackQueryHandler(reset_turni, pattern='^2-'))
    
    # log all errors
    dispatcher.add_error_handler(error)
    
    # Periodic Job every Monday at 8:00
    updater.job_queue.run_daily(inizializza_settimana, time=time(8, 0, 0), days=(0, 1, 2, 3, 4))
    #updater.job_queue.run_once(inizializza_settimana, 0) # test
    
    updater.start_polling()
    
    updater.idle()

if __name__ == '__main__':
    main()
