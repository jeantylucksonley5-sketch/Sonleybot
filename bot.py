import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Konfigirasyon Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Mesaj Byenveni
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Byenveni nan Bot Analiz Chart!**\n\n"
        "Voye yon deskripsyon oswa endikatè chart ou yo pou m ka analize yo.\n"
        "**Egzanp:**\n"
        "`RSI nan 25, trend la se downtrend, ak pri a toupre yon gwo sipò nan 1.0850`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Lojik Analiz Chart
async def analyze_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()
    
    rsi_val = None
    words = user_text.split()
    for i, word in enumerate(words):
        if "rsi" in word:
            for j in range(i, min(i + 3, len(words))):
                clean_word = words[j].replace(",", "").replace(":", "")
                if clean_word.isdigit():
                    rsi_val = int(clean_word)
                    break

    signal = "⏳ **TANN** (Neutre)"
    reasoning = []
    
    if rsi_val is not None:
        if rsi_val <= 30:
            signal = "📈 **ACHTE** (BUY)"
            reasoning.append(f"• RSI nan {rsi_val} (Oversold / Mache a desann li rive nan limit bottom).")
        elif rsi_val >= 70:
            signal = "📉 **VANN** (SELL)"
            reasoning.append(f"• RSI nan {rsi_val} (Overbought / Mache a monte li rive nan limit top).")
        else:
            reasoning.append(f"• RSI nan {rsi_val} (Nan mitan zone neutre).")

    if "support" in user_text or "sipò" in user_text:
        reasoning.append("• Pri a toupre yon nivo Sipò enpòtan.")
    if "resistance" in user_text or "rezistans" in user_text:
        reasoning.append("• Pri a toupre yon nivo Rezistans enpòtan.")

    if not reasoning:
        reasoning.append("• Tanpri mete plis enfòmasyon tankou valè RSI, Trend, oswa Nivo Sipò/Rezistans.")

    response = (
        f"📊 **ANALIZ SYAL LA:**\n\n"
        f"**Siyal Rekòmande:** {signal}\n\n"
        f"**Rezon:**\n" + "\n".join(reasoning) + "\n\n"
        f"⏱️ **Timeframe Rekòmande:** 15m oswa 1H pou konfime confirmation candle anvan w antre."
    )
    
    await update.message.reply_text(response, parse_mode="Markdown")

if __name__ == '__main__':
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Erè: BOT_TOKEN pa jwenn nan Variables yo!")
    else:
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), analyze_chart))
        app.run_polling()
      
