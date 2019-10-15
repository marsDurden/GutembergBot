from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup

import logging, configparser, sqlite3, json, locale
from datetime import date, time, datetime

# Global settings
settings_path = 'settings.ini'
db_path = 'database.db'
matricole_path = "matricole.json"

locale.setlocale(locale.LC_TIME, "it_IT.utf8")

# Logging errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

config = configparser.ConfigParser()
config.read(settings_path)

def text_keyboard(chat_id, mode=0, data=None):
    # Mode list
    # 0  | normal
    # 1  | alert corso sicurezza
    
    # Get last week in database
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT id, settimana, lun, lunID, mar, marID, mer, merID, gio, gioID, ven, venID, sab, sabID, dom, domID FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
    # variable row
    # 0     | id
    # 1     | # settimana
    # 2-end | turni giornalieri
    row = c.fetchone()
    id_turno = row[0]
    row = row[1:]
    
    c.execute("SELECT lun, mar, mer, gio, ven, sab, dom FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
    turn_list = c.fetchone()
    
    # Skeleton text
    text = "*Turni chiusura Pollaio*\n_{}° settimana dell'anno_\n#ChiChiude\n\n`Lunedì:    `[{}](tg://user?id={})\n" + \
        "`Martedì:   `[{}](tg://user?id={})\n`Mercoledì: `[{}](tg://user?id={})\n`Giovedì:   `[{}](tg://user?id={})\n" + \
        "`Venerdì:   `[{}](tg://user?id={})\n`Sabato:    `[{}](tg://user?id={})\n`Domenica:  `[{}](tg://user?id={})"
    
    # Make buttons
    c.execute("SELECT protected FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
    if c.fetchone()[0] == "0":
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        i = 0; tot=0; line, keyboard = [[],[]]
        while i < 5:
            if turn_list[i] is None:
                line.append(InlineKeyboardButton(giorni[i], callback_data='1-'+str(id_turno)+'-'+str(i) ) )
            else:
                line.append(InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+str(id_turno)+'-'+str(i) ) )
                tot += 1
            i += 1
            if turn_list[i] is None:
                line.append(InlineKeyboardButton(giorni[i], callback_data='1-'+str(id_turno)+'-'+str(i) ) )
            else:
                line.append(InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+str(id_turno)+'-'+str(i) ) )
                tot += 1
            i += 1
            keyboard.append(line)
            line = []
        # 7 is prime -> no symmetry in buttons
        if turn_list[i] is None:
            keyboard.append([InlineKeyboardButton(giorni[i], callback_data='1-'+str(id_turno)+'-'+str(i) )] )
        else:
            keyboard.append([InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+str(id_turno)+'-'+str(i) )] )
            tot += 1
        # Add button for printing and blocking turns
        if tot == 7:
            keyboard.append([InlineKeyboardButton('Stampa i turni', callback_data='3-print' )] )
        
        # Add alert corso sicurezza
        if mode == 1:
            text += "\n\n*Non tutti i prenotati hanno fatto il corso sulla sicurezza*\n" + str(data)
        
        text += "\n\nPrenotati qui sotto:"
    else:
        keyboard = [[InlineKeyboardButton('Stampa i turni', callback_data='3-print' )]]
    
    con.close()
    
    return text.format(*row), InlineKeyboardMarkup(keyboard)

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

def turni(update, context):
    # Create text, keyboard
    chat_id = update.message.chat.id
    t, k = text_keyboard(chat_id)
    # Send message
    context.bot.sendMessage(chat_id=chat_id,
                            text=t,
                            reply_markup=k,
                            parse_mode=ParseMode.MARKDOWN)

def callback_turni(update, context):
    data = update.callback_query.data[2:].split('-')
    user_id = update.callback_query.from_user.id
    
    # Check protected
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT protected FROM turns WHERE id = ?", (data[0],))
    if c.fetchone()[0] == "0":
        # Get name of user
        name = update.callback_query.from_user.first_name + ' ' + update.callback_query.from_user.last_name
        if name == ' ':
            name = update.callback_query.from_user.username
        if name.replace(' ','') == ' ':
            name = update.callback_query.from_user.id
        
        # Filter name characters
        name = name.replace('_',' ').replace('*',' ').replace('`','').replace('~',' ')
        
        # Insert name
        colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
        c.execute("UPDATE turns SET " + colonne[int(data[1])] + " = ?, " + colonne[int(data[1])] + "ID = ? WHERE ID = ?", (name, user_id, data[0]) )
        con.commit()
        
        # Delete message
        try:
            context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                                message_id=update.callback_query.message.message_id)
        except:
            pass
        
        # Send new message to group
        chat_id = update.callback_query.message.chat.id
        # Create text, keyboard
        t, k = text_keyboard(chat_id)
        # Send message
        context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                parse_mode=ParseMode.MARKDOWN)
    con.close()

def reset_turni(update, context):
    data = update.callback_query.data[2:].split('-')
    user_id = str(update.callback_query.from_user.id)
    
    # Seelzione utente prenotato
    con = sqlite3.connect(db_path)
    c = con.cursor()
    colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
    c.execute("SELECT " + colonne[int(data[1])] + "ID FROM turns WHERE ID = ?", (data[0],))
    turn_user_id = str(c.fetchone()[0])
    
    # Restrict reset access
    flag = False
    for admin_id in config['BOT']['admins'].split(','):
        if admin_id == user_id:
            flag = True
    if user_id == turn_user_id or flag:
        # Resetta il turno
        c.execute("UPDATE turns SET "+colonne[int(data[1])]+" = NULL, "+ colonne[int(data[1])] +"ID = NULL WHERE ID = ?", (data[0],))
        con.commit()
        # Delete message
        try:
            context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                                message_id=update.callback_query.message.message_id)
        except:
            pass
        
        chat_id = update.callback_query.message.chat.id
        # Create text, keyboard
        t, k = text_keyboard(chat_id)
        # Send message
        context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                parse_mode=ParseMode.MARKDOWN)
    con.close()

def stampa_turni(update, context):
    user_id = str(update.callback_query.from_user.id)
    chat_id = str(update.callback_query.message.chat.id)
    
    # Restrict access to admins
    flag = False
    for admin_id in config['BOT']['admins'].split(','):
        if admin_id == user_id:
            flag = True
    if flag:
        # Load file
        with open(matricole_path, encoding='utf-8', errors='ignore') as json_data:
            matricole = json.load(json_data, strict=False)
            json_data.close()
        
        # Create skeleton strings
        week = date.today().strftime("%Y-%U-")
        row = ''
        for i in range(1,7):
            row += datetime.strptime(week + str(i), "%Y-%W-%w").strftime("%d/%m/%Y %A: {} [matricola {}]\n")
        row += datetime.strptime(week + '0', "%Y-%W-%w").strftime("%d/%m/%Y %A: {} [matricola {}]\n") # Domenica
        
        header = "Elenco turni chiusura Aula Pollaio"
        
        con = sqlite3.connect(db_path)
        c = con.cursor()
        c.execute("SELECT lunID, marID, merID, gioID, venID, sabID, domID FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
        turn_list = c.fetchone()
        names = []; flag = False
        no_corso = ""
        for item in turn_list:
            try:
                names.append(matricole[item]['nome'])
                names.append(matricole[item]['matricola'])
            except:
                names.append('<nome>')
                names.append('<matricola>')
                flag = True
                
                user = context.bot.get_chat_member(chat_id, item).user
                no_corso += user.first_name + " " + user.last_name + "\n"
        
        # Tutti gli utenti hanno fatto il corso sulla sicurezza
        if not flag:
            # Set turni protected to 1 -> not modifiable
            c.execute("SELECT id FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
            c.execute("UPDATE turns SET protected = 1 WHERE id = ?", (c.fetchone()[0],))
            con.commit()
            con.close()
            
            # Save file
            file_path = week + 'turni.txt'
            with open(file_path, 'w') as f:
                f.write(header + '\n\n')
                f.write(row.format(*names))
                f.close()
            
            # Send file
            week_number = week.split('-')[1]
            text = "File con i turni definitivi\n{}° settimana\n#FileTurni"
            context.bot.send_document(chat_id=chat_id, document=open(file_path, 'rb'),
                                    caption=text.format(week_number),
                                    parse_mode=ParseMode.MARKDOWN)
        
        # Delete message
        try:
            context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                                message_id=update.callback_query.message.message_id)
        except:
            pass
        
        # Create text, keyboard
        t, k = text_keyboard(chat_id, mode=1, data=no_corso) if flag else text_keyboard(chat_id)
        # Send message
        context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                parse_mode=ParseMode.MARKDOWN)

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
            c.execute("INSERT INTO turns (chat_id, settimana, protected) VALUES (?, ?, 0)",
                    (chat_id, week_number))
            con.commit()
            # Create text, keyboard
            t, k = text_keyboard(chat_id)
            # Send message
            context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                parse_mode=ParseMode.MARKDOWN)
    con.close()

def check_prenotazione(context):
    colonne = ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab']
    # 0 - Sunday -> 6 - Saturday
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
            # Create text, keyboard
            t, k = text_keyboard(chat_id)
            # Send message
            context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                parse_mode=ParseMode.MARKDOWN)
    con.close()

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
    # 3 | print turns
    dispatcher.add_handler(CallbackQueryHandler(callback_turni, pattern='^1-'))
    dispatcher.add_handler(CallbackQueryHandler(reset_turni, pattern='^2-'))
    dispatcher.add_handler(CallbackQueryHandler(stampa_turni, pattern='^3-'))
    
    # log all errors
    #dispatcher.add_error_handler(error)
    
    # New message
    # 0 - Monday -> 6 - Sunday
    updater.job_queue.run_daily(inizializza_settimana, time=time(8, 0, 0), days=(0,))
    updater.job_queue.run_daily(inizializza_settimana, time=time(19, 0, 0), days=(6,))
    
    # Check if prenotation is fullfilled
    updater.job_queue.run_daily(check_prenotazione, time=time(12, 0, 0), days=(0, 1, 2, 3, 4, 5, 6))
    updater.job_queue.run_daily(check_prenotazione, time=time(19, 30, 0), days=(0, 1, 2, 3, 4, 5))
    #updater.job_queue.run_once(check_prenotazione, when=0)
    
    updater.start_polling()
    
    updater.idle()

if __name__ == '__main__':
    main()
