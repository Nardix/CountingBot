#!/usr/bin/env python
# pylint: disable=unused-argument

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import datetime as dt
from datetime import datetime as datet, timedelta
import pytz
from py2neo import Graph
import os
from dotenv import load_dotenv
import locale
import random
from QueryClass import Query
from telegram.error import Conflict, NetworkError
from telegram._utils.defaultvalue import DEFAULT_NONE

load_dotenv()
locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
graph = Graph(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD')))

TOKEN = os.getenv('TOKEN_ORIGINAL') #originale
#TOKEN = os.getenv('TOKEN_TEST')  #test

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    check = runQuery(Query.profilo(chat_id=update.effective_chat.id, user_id=user.id))
    if len(check)==0:
        data = update.effective_message.date.astimezone(pytz.timezone('Europe/Rome')).strftime('%Y-%m-%d %H:%M:%S')
        runQuery(Query.registrazione(chat_id=update.effective_chat.id, user_id=user.id, user_full_name=user.full_name, data=data))
        await runMessageUpdate(rf"*{user.full_name}* si è registrato/a!", update, parse_mode='Markdown')
    else:
        await runMessageUpdate(rf"*{user.full_name}* si è già registrato/a!", update, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    message = (
        "Per far si che il bot conti il tuo punteggio, registrati una sola volta digitando /start e ad ogni conteggio usa l'emoji 🔝, valgono anche gli stickers con questa emoji.\n\n"
        "lista comandi:\n\n"
        "/start per registrarti\n"
        "/profilo per vedere il tuo punteggio mensile, totale e il record di punteggio in un mese\n"
        "/classifica per vedere la classifica mensile\n"
        "/classifica_totale per vedere la classifica sul totale dei punteggi fatti\n"
        "/record per vedere la classifica dei record massimi raggiunti"
    )
    await runMessageUpdate(message, update)


async def reset(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    buffer1 = buffer2 = ""
    val_tot = 0
    content = runQuery(Query.winner(chat_id=chat_id))
    for i,user in enumerate(content):
        if i<3:
            buffer1 = buffer1 + f"{i+1}) *{user.get('nome')}* con {user.get('total')} punti\n"
        else:
            buffer2 = buffer2 + f"{i+1}) *{user.get('nome')}* con {user.get('total')} punti\n"
        val_tot+=user.get("total")

    message = (
        "🎉🎉🎉 *VINCITORI* 🎉🎉🎉\n\n"
        "- 🏆 *PODIO* 🏆 -\n\n"
        f"{buffer1}\n"
        "- 🎖️ *ALTRI* 🎖️ -\n\n"
        f"{buffer2}\n"
        f"I primi {len(content)} hanno effettuato un totale di {val_tot} punti questo mese.\n\n"
        "Le statistiche mensili sono state resettate, potete comunque vedere il totale dei punti con il comando /profilo"
    )

    await runMessageContext(message, context, parse_mode='Markdown', chat_id=chat_id)
    runQuery(Query.reset_all())


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and (update.message.text == "🔝" or (update.message.sticker != None and update.message.sticker.emoji == "🔝")):
        user = update.effective_user
        dataAsTimezone = update.effective_message.date.astimezone(pytz.timezone('Europe/Rome'))
        data = dataAsTimezone.strftime('%Y-%m-%d %H:%M:%S')
        dataAsYearMonth = dataAsTimezone.strftime('%Y-%m')
        dataReset = runQuery(Query.get_dataReset())[0].get('data')
        if datet.strptime(dataAsYearMonth, '%Y-%m') > datet.strptime(dataReset, '%Y-%m'):
            await reset(update.effective_chat.id, context)
            runQuery(Query.set_dataReset(data=dataAsYearMonth))
            logger.info("reset effettuato")
        content = runQuery(Query.controllo(chat_id=update.effective_chat.id, user_id=user.id, user_full_name=user.full_name, data=data))
        buffer = ""
        if len(content)!=0:
            if content[0].get('result')==1:
                buffer = "\n🎉 nuovo record 🎉"
            content2 = runQuery(Query.sorpasso(chat_id=update.effective_chat.id, total=content[0].get('total')-1))
            if len(content2)!=0:
                buffer = buffer + f"\n🏁 *{user.full_name}* ha appena superato *{content2[0].get('nome')}* 🏁"
            await runMessageUpdate(f"*{user.full_name}* punteggio incrementato! Per un totale di {content[0].get('total')} volte questo mese{buffer}", update, parse_mode='Markdown')
            if content[0].get('fulltotal')%100==0:
                await runMessageUpdate(f"🎉 *{user.full_name}* ha raggiunto {content[0].get('fulltotal')} punti totali, congratulazioni! 🎉", update, parse_mode='Markdown')
                await context.bot.send_voice(update.effective_chat.id, voice=open(victory_sound_choice(), 'rb'), reply_to_message_id=update.effective_message.message_id)
        else:    
            await runMessageUpdate(rf"*{user.full_name}* non sei ancora registrato! usa il comando /start per registrati", update, parse_mode='Markdown')


async def winner(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    await reset(chat_id, context)
    runQuery(Query.set_dataReset(data=datet.now().strftime('%Y-%m')))
    logger.info("winner effettuato")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    content = runQuery(Query.profilo(chat_id=update.effective_chat.id, user_id=user.id))
    if len(content)!=0:
        if content[0].get('u.total')==0:
            await runMessageUpdate(f"*{user.full_name}* non ha ancora fatto punti questo mese\n{content[0].get('u.fulltotal')} punti totali\n{content[0].get('u.record')} - record massimo in un mese", update, parse_mode='Markdown')
        else:
            await runMessageUpdate(f"*{user.full_name}* ha effettuato {content[0].get('u.total')} punti questo mese\n{content[0].get('u.fulltotal')} punti totali\nrecord massimo in un mese: {content[0].get('u.record')} punti", update, parse_mode='Markdown')
    else:
        await runMessageUpdate(f"*{user.full_name}* non sei ancora registrato! usa il comando /start per registrati", update, parse_mode='Markdown')


async def hallOfFame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    buffer = ""
    val_tot = 0
    content = runQuery(Query.classifica(chat_id=chat_id))
    if len(content)==0:
        await runMessageContext("Nessuno ha ancora fatto punti", context, chat_id=chat_id)
        return

    for i,user in enumerate(content):
        buffer = buffer + f"{i+1}) *{user.get('nome')}* con {user.get('total')} punti\n"
        val_tot+=user.get('total')

    month_name = datet.now().strftime("%B")
    message = (
        f"Classifica del mese di {month_name}\n\n"
        f"{buffer}\n"
        f"i primi {len(content)} hanno effettuato un totale di {val_tot} punti questo mese"
    )

    await runMessageContext(message, context, parse_mode='Markdown', chat_id=chat_id)


async def hallOfFameTotal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    buffer = ""
    val_tot = 0
    content = runQuery(Query.classifica_totale(chat_id=chat_id))
    if len(content)==0:
        await runMessageContext("Nessuno ha ancora fatto punti", context, chat_id=chat_id)
        return

    for i,user in enumerate(content):
        buffer = buffer + f"{i+1}) *{user.get('nome')}* con {user.get('fulltotal')} punti\n"
        val_tot+=user.get('fulltotal')

    message = (
        f"Classifica generale sul totale\n\n"
        f"{buffer}\n"
        f"i primi {len(content)} hanno effettuato un totale di {val_tot} punti"
    )

    await runMessageContext(message, context, parse_mode='Markdown', chat_id=chat_id)


async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    buffer = ""
    val_tot = 0
    content = runQuery(Query.record(chat_id=chat_id))
    if len(content)==0:
        await runMessageContext("Nessuno ha ancora fatto punti", context, chat_id=chat_id)
        return

    for i,user in enumerate(content):
        buffer = buffer + f"{i+1}) *{user.get('nome')}* con {user.get('record')} punti\n"
        val_tot+=user.get('record')

    message = (
        f"Classifica dei record massimi\n\n"
        f"{buffer}\n"
        f"totale dei primi {len(content)} record: {val_tot} punti"
    )

    await runMessageContext(message, context, parse_mode='Markdown', chat_id=chat_id)


async def on_bot_start(application: Application) -> None:
    chat_id = os.getenv('CHAT_ID')
    job_queue = application.job_queue

    if (datet.now() + timedelta(days=1)).day == 1:
        job_queue.run_monthly(
            winner,
            dt.time(hour=0,minute=0,tzinfo=pytz.timezone('Europe/Rome')),
            day=1,
            chat_id=chat_id,
            name=str(chat_id)
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Conflict):
        logger.error("Errore Conflict: due dispositivi accesi in contemporanea")
    if isinstance(context.error, NetworkError):
        logger.error("Errore NetworkError: errore di connessione")


def victory_sound_choice():
    audio_folder = "res/audio/victory"

    audio_files = [f for f in os.listdir(audio_folder) if os.path.isfile(os.path.join(audio_folder, f))]

    # Seleziona un file casuale
    random_audio_file = random.choice(audio_files)
    audio_path = os.path.join(audio_folder, random_audio_file).replace("\\", "/")
    return audio_path


def runQuery(query):
    try:
        content = graph.run(query).data()
    except:
        content = errorQuery(query)
    return content


def errorQuery(query):
    tentativi=0
    while True:
        try:
            tentativi+=1
            global graph
            graph = Graph(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD')))
            content = graph.run(query).data()
            return content
        except:
            logger.error("tentativo di connessione al database fallito" + str(tentativi))


async def runMessageUpdate(message: str, content: Update, parse_mode = DEFAULT_NONE):
    try:
        await content.message.reply_text(message, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Error sending message: {e}")


async def runMessageContext(message: str, content: ContextTypes.DEFAULT_TYPE, parse_mode = DEFAULT_NONE, chat_id = None):
    try:
        await content.bot.send_message(chat_id, text=message, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Error sending message: {e}")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).post_init(on_bot_start).build()
    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profilo", profile))
    application.add_handler(CommandHandler("classifica",hallOfFame))
    application.add_handler(CommandHandler("classifica_totale",hallOfFameTotal))
    application.add_handler(CommandHandler("record",record))
    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT | filters.Sticker.ALL & ~filters.COMMAND , echo))
    # on error - handle the error
    application.add_error_handler(error_handler)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()