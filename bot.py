from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup

import logging, configparser, sqlite3
from datetime import date, time

# Global settings
settings_path = 'settings.ini'
db_path = 'database.db'

# Logging errors
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
    
    # Send start message
    context.bot.sendMessage(chat_id=update.message.chat_id, text="Ciao! Io gestisco i turni delle chiusure dell'Aula studio Pollaio")
    
    # Set new settimana
    inizializza_settimana(context, list_id=update.message.chat.id)

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
    context.bot.sendMessage(chat_id=update.message.chat_id,
                            text="Bot opensource fatto da @ThanksLory",
                            reply_markup=markup,
                            parse_mode=ParseMode.MARKDOWN)

def turni(update, context, chat_id=None):
    # Set chat_id
    chat_id = update.message.chat.id if chat_id is None else chat_id
    
    # Get last week in database
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT id, settimana, lun, mar, mer, gio, ven, sab, dom FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
    row = c.fetchone()
    id_turno = row[0]
    row = row[1:]
    # Skeleton text
    text = "*Turni chiusura Pollaio*\n_{}° settimana dell'anno_\n\nLunedì: {}\nMartedì: {}\nMercoledì: {}\nGiovedì: {}\nVenerdì: {}\nSabato: {}\nDomenica: {}\n\nPrenotati qui sotto:"
    
    # Make buttons
    giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    i = 0; keyboard = []
    for turn in row[1:]:
        if turn is None:
            keyboard.append([InlineKeyboardButton(giorni[i], callback_data='1-'+str(id_turno)+'-'+str(i))])
        else:
            keyboard.append([InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+str(id_turno)+'-'+str(i))])
        i += 1
    keyboard = InlineKeyboardMarkup(keyboard)
    
    # Send message
    context.bot.sendMessage(chat_id=chat_id,
                            text=text.format(*row),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.MARKDOWN)

def callback_turni(update, context):
    data = update.callback_query.data[2:].split('-')
    user_id = update.callback_query.from_user.id
    
    # Get name of user
    name = update.callback_query.from_user.first_name + ' ' + update.callback_query.from_user.last_name
    if name == ' ':
        name = update.callback_query.from_user.username
    if name.replace(' ','') == ' ':
        name = update.callback_query.from_user.id
    
    # Filter name characters
    name = name.replace('_',' ').replace('*',' ').replace('`','').replace('~',' ')
    
    # Insert name
    con = sqlite3.connect(db_path)
    c = con.cursor()
    colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
    c.execute("UPDATE turns SET " + colonne[int(data[1])] + " = ?, " + colonne[int(data[1])] + "ID = ? WHERE ID = ?", (name, user_id, data[0]) )
    con.commit()
    con.close()
    
    # Delete message
    context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                              message_id=update.callback_query.message.message_id)
    
    # Send new message to group
    turni(None, context, chat_id=update.callback_query.message.chat.id)

def reset_turni(update, context):
    data = update.callback_query.data[2:].split('-')
    user_id = str(update.callback_query.from_user.id)
    username = update.callback_query.from_user.username
    
    # Resetta i turni della settimana
    con = sqlite3.connect(db_path)
    c = con.cursor()
    colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
    c.execute("SELECT " + colonne[int(data[1])] + "ID FROM turns WHERE ID = ?", (data[0],))
    turn_user_id = str(c.fetchone()[0])
    
    # Restrict reset access
    flag = False
    for u_name in config['BOT']['admins'].split(','):
        if u_name == username:
            flag = True
    if user_id == turn_user_id or flag:
        c.execute("UPDATE turns SET " + colonne[int(data[1])] + " = NULL WHERE ID = ?", (data[0],))
        con.commit()
        con.close()
        # Delete message
        context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                                message_id=update.callback_query.message.message_id)
        
        # Send new message to group
        turni(None, context, chat_id=update.callback_query.message.chat.id)

def inizializza_settimana(context, list_id=None):
    week_number = date.today().strftime("%U")
    
    # Get alla chats
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT chat_id FROM utenti")
    id_list = c.fetchall() if list_id is None else [(str(list_id),)]
    for chat_id in id_list:
        chat_id = chat_id[0]
        # Set new week to null for all days
        c.execute("SELECT * FROM turns WHERE settimana = ? AND chat_id = ?", (week_number, chat_id ))
        if c.fetchone() is None:
            c.execute("INSERT INTO turns (chat_id, settimana, lun, mar, mer, gio, ven, sab, dom) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)",
                    (chat_id, week_number))
            con.commit()
            
            # Send new message to group
            turni(None, context, chat_id=chat_id)
    con.close()

def check_prenotazione(context):
    colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
    day_number = date.today().strftime("%w")
    week_number = date.today().strftime("%U")
    
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT chat_id FROM utenti")
    id_list = c.fetchall()
    for chat_id in id_list:
        chat_id = chat_id[0]
        c.execute("SELECT " + colonne[int(day_number)] + " FROM turns WHERE settimana = ? AND chat_id = ?", (week_number, chat_id ))
        if c.fetchone()[0] is None:
            # Send message to group
            turni(None, context, chat_id=chat_id)

def error(update, context):
    try:
        # Normal message
        context.bot.sendMessage(config['BOT']['adminID'],parse_mode=ParseMode.MARKDOWN, text=('*ERROR*\nID: `%s`\ntext: %s\ncaused error: _%s_' % (update.message.chat_id, update.message.text, context.error)))
        logging.warn('Update "%s" caused error "%s"' % (update.message.text, context.error))
    except:
        # Callback message
        context.bot.sendMessage(config['BOT']['adminID'],parse_mode=ParseMode.MARKDOWN, text=('*ERROR*\nID: `%s`\ntext: %s\ncaused error: _%s_' % (update.callback_query.message.chat_id, update.callback_query.data, context.error)))
        logging.warn('Update "%s" caused error "%s"' % (update.callback_query.data, context.error))

def main():
    updater = Updater(token=config['BOT']['token'], use_context=True) 
    
    dispatcher = updater.dispatcher
    
    # Bot commands
    dispatcher.add_handler(CommandHandler('start', start))
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
    
    # Periodic Job every Monday at 12:00
    updater.job_queue.run_daily(inizializza_settimana, time=time(12, 0, 0), days=(0,))
    
    # Periodic Job every Mon to Fri at 20:00
    updater.job_queue.run_daily(check_prenotazione, time=time(20, 0, 0), days=(0, 1, 2, 3, 4, 5, 6))
    #updater.job_queue.run_once(check_prenotazione, when=0)
    
    updater.start_polling()
    
    updater.idle()

if __name__ == '__main__':
    main()
