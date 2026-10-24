import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from keep_alive import keep_alive

# Inserisci qui i tuoi dati di configurazione
TOKEN = "8854040084:AAFsVQCtNgGJL-lDlS-wpW2G1aP8i_I2HRU"
ADMIN_ID = 8886429641  # Sostituisci con il tuo ID numerico di Telegram

# Stati per le conversazioni
WAITING_PHONE, WAITING_CODE, WAITING_SPAM_MSG, WAITING_SPAM_TIME = range(4)
WAITING_PAYPAL_NAME, WAITING_PAYPAL_YEAR = range(20, 22)
WAITING_BANK_NAME, WAITING_BANK_SELECT = range(22, 24)

# --- FUNZIONE START CON MESSAGGIO AGGIORNATO ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    text = (
        f"🚀 **Benvenuto su Boost Bot, {user_name}!**\n\n"
        f"✨ **Funzionalità disponibili:**\n"
        f"🤖 • Spam Bot\n"
        f"👤 • User Bot\n"
        f"📈 • Boost account per popolarità\n"
        f"🛡️ • Sicurezza da Telegram\n"
        f"💳 • **Creazione conti con nome personalizzato verificati**\n\n"
        f"👇 **Per prima cosa, seleziona per cosa vuoi usare il bot:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Boost Bot", callback_data="start_boost"),
         InlineKeyboardButton("🤖 Spam Bot", callback_data="start_spam")],
        [InlineKeyboardButton("🛡️ Sicurezza Telegram", callback_data="start_security"),
         InlineKeyboardButton("👤 User Bot", callback_data="start_user")],
        [InlineKeyboardButton("💳 Conti bancari custom nome", callback_data="menu_bank"),
         InlineKeyboardButton("🅿️ Conto PayPal", callback_data="menu_paypal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# --- GESTIONE COLLEGAMENTO ACCOUNT PER CONTI ---

async def check_account_linked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    is_linked = context.user_data.get("is_linked", False)
    
    if not is_linked:
        keyboard = [
            [InlineKeyboardButton("🔗 Collega account", callback_data="start_link")],
            [InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "⚠️ **Attenzione**\n\nPrima di creare conti bancari o Paypal con nome personalizzato devi collegare il tuo account.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        if query.data == "menu_paypal":
            keyboard = [
                [InlineKeyboardButton("➕ Crea conto PayPal", callback_data="create_paypal_start")],
                [InlineKeyboardButton("📊 Status conto", callback_data="show_status")],
                [InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")]
            ]
            await query.edit_message_text("🅿️ **Gestione Conto PayPal**\n\nScegli un'opzione:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            keyboard = [
                [InlineKeyboardButton("➕ Crea conto bancario", callback_data="create_bank_start")],
                [InlineKeyboardButton("📊 Status conto", callback_data="show_status")],
                [InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")]
            ]
            await query.edit_message_text("💳 **Gestione Conti Bancari**\n\nScegli un'opzione:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- FLUSSO CREAZIONE PAYPAL ---

async def start_paypal_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✍️ Inserisci il nome da mettere per il conto PayPal:")
    return WAITING_PAYPAL_NAME

async def receive_paypal_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['paypal_name'] = update.message.text
    
    years_keyboard = []
    row = []
    for year in range(2017, 2027):
        row.append(InlineKeyboardButton(str(year), callback_data=f"year_{year}"))
        if len(row) == 3:
            years_keyboard.append(row)
            row = []
    if row:
        years_keyboard.append(row)
    years_keyboard.append([InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")])
    
    await update.message.reply_text(
        "📅 Seleziona l'anno del conto:",
        reply_markup=InlineKeyboardMarkup(years_keyboard)
    )
    return WAITING_PAYPAL_YEAR

async def receive_paypal_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    year = query.data.split("_")[1]
    context.user_data['paypal_year'] = year
    context.user_data['account_type'] = 'PayPal'
    
    hours = random.randint(10, 24)
    context.user_data['estimated_time'] = f"Circa {hours} ore"
    context.user_data['status'] = "In fase di creazione"
    
    keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")]]
    
    await query.edit_message_text(
        f"ℹ️ **Info creazione conto paypal**\n\n"
        f"Conto in fase di creazione. Il tempo stimato varia dai 10 ore a 1 giorno.\n\n"
        f"📌 **Dettagli:**\n"
        f"- Nome conto: {context.user_data['paypal_name']}\n"
        f"- Anno: {year}\n"
        f"- Stato: In fase di creazione\n\n"
        f"*(Nota: questa è una simulazione, nessun conto reale viene creato)*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# --- FLUSSO CREAZIONE CONTO BANCARIO ---

async def start_bank_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✍️ Inserisci il nome da mettere per il conto bancario:")
    return WAITING_BANK_NAME

async def receive_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bank_custom_name'] = update.message.text
    
    banks = ["Intesa Sanpaolo", "UniCredit", "Banco BPM", "Postepay / BancoPosta", "BNL", "Fineco", "Mediolanum"]
    banks_keyboard = [[InlineKeyboardButton(bank, callback_data=f"bank_{bank}")] for bank in banks]
    banks_keyboard.append([InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")])
    
    await update.message.reply_text(
        "🏦 Seleziona la banca:",
        reply_markup=InlineKeyboardMarkup(banks_keyboard)
    )
    return WAITING_BANK_SELECT

async def receive_bank_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bank_name = query.data.replace("bank_", "")
    context.user_data['selected_bank'] = bank_name
    context.user_data['account_type'] = 'Bancario'
    
    hours = random.randint(20, 48) # Da 20 ore a 2 giorni
    days = hours // 24
    rem_hours = hours % 24
    context.user_data['estimated_time'] = f"{days} giorni e {rem_hours} ore" if days > 0 else f"{hours} ore"
    context.user_data['status'] = f"Stato creazione conto bancario ({bank_name})"
    
    keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")]]
    
    await query.edit_message_text(
        f"✅ Conto creato con successo (Simulato)!\n\n"
        f"📌 **Info creazione conto bancario**\n"
        f"- Banca: {bank_name}\n"
        f"- Nome conto: {context.user_data['bank_custom_name']}\n"
        f"- Tempo stimato rimanente: {context.user_data['estimated_time']}\n"
        f"- Stato: {context.user_data['status']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# --- SCHERMATA STATUS CONTO ---

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    acc_type = context.user_data.get('account_type', 'Nessuno')
    if acc_type == 'PayPal':
        name = context.user_data.get('paypal_name', 'N/D')
        year = context.user_data.get('paypal_year', 'N/D')
        status_text = (
            f"📊 **Status Conto PayPal**\n\n"
            f"• **Stato:** In fase di creazione\n"
            f"• **Nome conto:** {name}\n"
            f"• **Anno:** {year}\n"
            f"• **Tempo rimanente stimato:** {context.user_data.get('estimated_time', 'N/D')}"
        )
    elif acc_type == 'Bancario':
        name = context.user_data.get('bank_custom_name', 'N/D')
        bank = context.user_data.get('selected_bank', 'N/D')
        status_text = (
            f"📊 **Status Conto Bancario**\n\n"
            f"• **Stato creazione conto bancario ({bank}):** In corso\n"
            f"• **Nome conto:** {name}\n"
            f"• **Banca:** {bank}\n"
            f"• **Tempo rimanente stimato:** {context.user_data.get('estimated_time', 'N/D')}"
        )
    else:
        status_text = "❌ Nessun conto in fase di creazione trovato."
        
    keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_menu")]]
    await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

# --- MAIN FUNCTION ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_paypal = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_paypal_creation, pattern="^create_paypal_start$")],
        states={
            WAITING_PAYPAL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_paypal_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_bank = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_bank_creation, pattern="^create_bank_start$")],
        states={
            WAITING_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="^back_to_menu$"))
    
    app.add_handler(CallbackQueryHandler(check_account_linked, pattern="^(menu_bank|menu_paypal)$"))
    app.add_handler(CallbackQueryHandler(receive_paypal_year, pattern="^year_"))
    app.add_handler(CallbackQueryHandler(receive_bank_select, pattern="^bank_"))
    app.add_handler(CallbackQueryHandler(show_status, pattern="^show_status$"))

    app.add_handler(conv_paypal)
    app.add_handler(conv_bank)

    print("🤖 Booster Bot con ID admin, benvenuto rinnovato e gestione conti attivi...")
    keep_alive()
    app.run_polling()

if __name__ == "__main__":
    main()
