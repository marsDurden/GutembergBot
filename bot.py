from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup

import logging, configparser, sqlite3, json, locale
from datetime import date, time, datetime

from os.path import join

# Global settings
data_folder = 'data'
settings_path = 'settings.ini'
db_path = 'database.db'
matricole_path = join(data_folder, "matricole.json")

colonne = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']

locale.setlocale(locale.LC_TIME, "it_IT.utf8")

# Logging errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - line %(lineno)d - %(message)s',
                     level=logging.INFO)

config = configparser.ConfigParser()
config.read(settings_path)

def text_keyboard(chat_id, n_settimana, mode=0, ext_text=None):
    # Mode list
    # 0  | normal
    # 1  | alert corso sicurezza
    n_settimana = str(n_settimana)
    
    # Get week in database
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT id, settimana, lun, lunID, mar, marID, mer, merID, gio, gioID, ven, venID, sab, sabID, dom, domID FROM turns WHERE chat_id = ? AND settimana = ?", (chat_id, n_settimana))
    # variable row
    # 0     | id
    # 1     | # settimana
    # 2-end | turni giornalieri
    row = c.fetchone()
    id_turno = row[0]
    row = row[1:]
    
    c.execute("SELECT " + ', '.join(colonne) + " FROM turns WHERE chat_id = ? AND settimana = ?", (chat_id, n_settimana))
    turn_list = c.fetchone()
    
    # Skeleton text
    week = date.today().strftime("%Y-"+n_settimana+"-")
    text = []
    for i in range(1,7):
        text.append(datetime.strptime(week + str(i), "%Y-%W-%w").strftime("%d/%m"))  # Lunedì -> Sabato
    text.append(datetime.strptime(week + '0', "%Y-%W-%w").strftime("%d/%m"))        # Domenica
    text = "*Turni chiusura Pollaio*\n_{}° settimana dell'anno_\n#ChiChiude\n\n`%s Lunedì:    `[{}](tg://user?id={})\n" \
        "`%s Martedì:   `[{}](tg://user?id={})\n`%s Mercoledì: `[{}](tg://user?id={})\n`%s Giovedì:   `[{}](tg://user?id={})\n" \
        "`%s Venerdì:   `[{}](tg://user?id={})\n`%s Sabato:    `[{}](tg://user?id={})\n`%s Domenica:  `[{}](tg://user?id={})" % (*text,)
    
    # Make buttons
    c.execute("SELECT protected FROM turns WHERE chat_id = ? AND settimana = ?", (chat_id, n_settimana))
    if c.fetchone()[0] == "0":
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        i = 0; tot=0; line, keyboard = [[],[]]
        while i < 5:
            if turn_list[i] is None:
                line.append(InlineKeyboardButton(giorni[i], callback_data='1-'+n_settimana+'-'+str(id_turno)+'-'+str(i) ) )
            else:
                line.append(InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+n_settimana+'-'+str(id_turno)+'-'+str(i) ) )
                tot += 1
            i += 1
            if turn_list[i] is None:
                line.append(InlineKeyboardButton(giorni[i], callback_data='1-'+n_settimana+'-'+str(id_turno)+'-'+str(i) ) )
            else:
                line.append(InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+n_settimana+'-'+str(id_turno)+'-'+str(i) ) )
                tot += 1
            i += 1
            keyboard.append(line)
            line = []
        # 7 is prime -> no symmetry in buttons
        if turn_list[i] is None:
            keyboard.append([InlineKeyboardButton(giorni[i], callback_data='1-'+n_settimana+'-'+str(id_turno)+'-'+str(i) )] )
        else:
            keyboard.append([InlineKeyboardButton('Reset '+giorni[i], callback_data='2-'+n_settimana+'-'+str(id_turno)+'-'+str(i) )] )
            tot += 1
        # Add button for printing and blocking turns
        if tot == 7:
            keyboard.append([InlineKeyboardButton('Stampa i turni', callback_data='3-'+n_settimana+'-print' )] )
        
        # Add alert corso sicurezza
        if mode == 1:
            text += "\n\n*Non tutti i prenotati hanno fatto il corso sulla sicurezza*" + str(ext_text)
        
        text += "\n\nPrenotati qui sotto:"
    else:
        keyboard = [[InlineKeyboardButton('Stampa i turni', callback_data='3-'+n_settimana+'-print' )]]
    
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
    #context.bot.sendMessage(chat_id=update.message.chat_id, text="Ciao! Io gestisco i turni delle chiusure dell'Aula studio Pollaio")
    
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
    raise RuntimeError()
    # Get chat id
    chat_id = update.message.chat.id
    
    # Get current week number
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT settimana FROM turns WHERE chat_id = ? ORDER BY settimana DESC LIMIT 1", (chat_id,))
    n_settimana = c.fetchone()[0]
    con.close()
    
    # Create text, keyboard
    t, k = text_keyboard(chat_id, n_settimana)
    # Send message
    context.bot.sendMessage(chat_id=chat_id,
                            text=t,
                            reply_markup=k,
                            parse_mode=ParseMode.MARKDOWN)

def callback_turni(update, context):
    # Get parameters from context
    data = update.callback_query.data[2:].split('-')
    user_id = update.callback_query.from_user.id
    n_settimana = data[0]
    print(update.callback_query.data)
    
    # Check protected
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT protected FROM turns WHERE id = ?", (data[1],))
    if c.fetchone()[0] == "0":
        # Get name of user
        try:
            name = update.callback_query.from_user.first_name + ' ' + update.callback_query.from_user.last_name
        except:
            name = update.callback_query.from_user.username
        if name == None:
            name = update.callback_query.from_user.id
        
        # Filter name characters
        name = name.replace('_',' ').replace('*',' ').replace('`','').replace('~',' ')
        
        # Insert name
        c.execute("UPDATE turns SET " + colonne[int(data[2])] + " = ?, " + colonne[int(data[2])] + "ID = ? WHERE ID = ?", (name, user_id, data[1]) )
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
        t, k = text_keyboard(chat_id, n_settimana)
        # Send message
        context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                disable_notification=True,
                                parse_mode=ParseMode.MARKDOWN)
    con.close()

def reset_turni(update, context):
    data = update.callback_query.data[2:].split('-')
    user_id = str(update.callback_query.from_user.id)
    n_settimana = data[0]
    
    # Seelzione utente prenotato
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT " + colonne[int(data[1])] + "ID FROM turns WHERE ID = ?", (data[1],))
    turn_user_id = str(c.fetchone()[0])
    
    # Restrict reset access
    flag = False
    for admin_id in config['BOT']['admins'].split(','):
        if admin_id == user_id:
            flag = True
    if user_id == turn_user_id or flag:
        # Resetta il turno
        c.execute("UPDATE turns SET "+colonne[int(data[2])]+" = NULL, "+ colonne[int(data[2])] +"ID = NULL WHERE ID = ?", (data[1],))
        con.commit()
        # Delete message
        try:
            context.bot.deleteMessage(chat_id=update.callback_query.message.chat.id, 
                                message_id=update.callback_query.message.message_id)
        except:
            pass
        
        chat_id = update.callback_query.message.chat.id
        # Create text, keyboard
        t, k = text_keyboard(chat_id, n_settimana)
        # Send message
        context.bot.sendMessage(chat_id=chat_id,
                                text=t,
                                reply_markup=k,
                                disable_notification=True,
                                parse_mode=ParseMode.MARKDOWN)
    con.close()

def stampa_turni(update, context):
    user_id = str(update.callback_query.from_user.id)
    chat_id = str(update.callback_query.message.chat.id)
    n_settimana = update.callback_query.data.split('-')[1]
    
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
        week = date.today().strftime("%Y-"+str(n_settimana)+"-")
        row = ''
        for i in range(1,7):
            row += datetime.strptime(week + str(i), "%Y-%W-%w").strftime("%d/%m/%Y %A: {} [matricola {}]\n")
        row += datetime.strptime(week + '0', "%Y-%W-%w").strftime("%d/%m/%Y %A: {} [matricola {}]\n") # Domenica
        
        header = date.today().strftime("Elenco turni chiusura Aula Pollaio\n%U° settimana del %Y")
        
        con = sqlite3.connect(db_path)
        c = con.cursor()
        c.execute("SELECT lunID, marID, merID, gioID, venID, sabID, domID FROM turns WHERE chat_id = ? AND settimana = ?", (chat_id, n_settimana))
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
                no_corso += "\n" + user.first_name + " " + user.last_name
        
        # Tutti gli utenti hanno fatto il corso sulla sicurezza
        if not flag:
            # Set turni protected to 1 -> not modifiable
            c.execute("SELECT id FROM turns WHERE chat_id = ? AND settimana = ?", (chat_id, n_settimana))
            c.execute("UPDATE turns SET protected = 1 WHERE id = ?", (c.fetchone()[0],))
            con.commit()
            con.close()
            
            # Save file
            file_path = data_folder + '/' + week + 'turni.txt'
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
        t, k = text_keyboard(chat_id, n_settimana, mode=1, ext_text=no_corso) if flag else text_keyboard(chat_id, n_settimana)
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
            c.execute("INSERT INTO turns (chat_id, settimana, protected) VALUES (?, ?, 0)", (chat_id, week_number))
            con.commit()
        # Create text, keyboard
        t, k = text_keyboard(chat_id, week_number)
        # Send message
        context.bot.sendMessage(chat_id=chat_id,
                            text=t,
                            reply_markup=k,
                            parse_mode=ParseMode.MARKDOWN)
    con.close()

def check_prenotazione(context):
    # 0 - Sunday -> 6 - Saturday
    day_number = date.today().strftime("%w")
    week_number = date.today().strftime("%U")
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute("SELECT chat_id FROM utenti")
    id_list = c.fetchall()
    for chat_id in id_list:
        chat_id = chat_id[0]
        res = c.execute("SELECT " + colonne[int(day_number)] + " FROM turns WHERE settimana = ? AND chat_id = ?", (week_number, chat_id )).fetchone()
        if res is None or res[0] is None:
            # Create text, keyboard
            t, k = text_keyboard(chat_id)
            # Send message
            try:
                context.bot.sendMessage(chat_id=chat_id, text=t, reply_markup=k, parse_mode=ParseMode.MARKDOWN)
            except:
                pass
    con.close()

def error(update, context):
    try:
        # Normal message
        context.bot.sendMessage(config['BOT']['adminID'], parse_mode=ParseMode.MARKDOWN, text=('*ERROR*\nID: `%s`\ntext: %s\ncaused error: _%s_' % (update.message.chat_id, update.message.text, context.error)))
        logging.warn('Update "%s" caused error "%s"' % (update.message.text, context.error))
    except:
        # Callback message
        context.bot.sendMessage(config['BOT']['adminID'], parse_mode=ParseMode.MARKDOWN, text=('*ERROR*\nID: `%s`\ntext: %s\ncaused error: _%s_' % (update.callback_query.message.chat_id, update.callback_query.data, context.error)))
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
    # X-Y-other
    #
    # X | description
    # 0 | nothing
    # 1 | new name
    # 2 | reset turns
    # 3 | print turns
    #
    # Y: week of the year
    dispatcher.add_handler(CallbackQueryHandler(callback_turni, pattern='^1-'))
    dispatcher.add_handler(CallbackQueryHandler(reset_turni, pattern='^2-'))
    dispatcher.add_handler(CallbackQueryHandler(stampa_turni, pattern='^3-'))
    
    # log all errors
    dispatcher.add_error_handler(error)
    
    # New message
    # 0 - Monday -> 6 - Sunday
    updater.job_queue.run_daily(inizializza_settimana, time=time(8, 0, 0), days=(0,))
    updater.job_queue.run_daily(inizializza_settimana, time=time(19, 0, 0), days=(6,))
    
    # Check if prenotation is fullfilled
    # 0 - Monday -> 6 - Sunday
    updater.job_queue.run_daily(check_prenotazione, time=time(12, 0, 0),  days=(0, 1, 2, 3, 4, 5, 6))
    updater.job_queue.run_daily(check_prenotazione, time=time(19, 30, 0), days=(0, 1, 2, 3, 4, 5))
    #updater.job_queue.run_once(check_prenotazione, when=0)
    
    updater.start_polling()
    
    updater.idle()

if __name__ == '__main__':
    main()
