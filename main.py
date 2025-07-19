import asyncio
import requests
import nest_asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIG ---
TELEGRAM_TOKEN = "7779767864:AAEXVWIMis8hfrmmbiLA-Np-JTPlKUy-_MI"
GROQ_API_KEY = "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"
ACCESS_KEY = "mysecretkey"

PREDICTED_USERS = set()
LAST_SEEN_PERIOD = {}

nest_asyncio.apply()

# --- Fetch 200 Results ---
async def fetch_latest_results():
    results = []
    try:
        for page in range(1, 30):
            url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
            params = {"page": page, "pageSize": 100}
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            list_data = data.get("data", {}).get("list", [])
            if not list_data:
                break
            results.extend(list_data)
            if len(results) >= 200:
                break
        return results[:200]
    except Exception as e:
        print("❌ API Error:", e)
        return []

# --- GPT Prediction ---
async def predict_with_gpt(history_data):
    try:
        formatted_data = "\n".join([
            f"Period: {item['issueNumber']} | Number: {item['number']} | Color: {item['color']}"
            for item in history_data
        ])

        current_period = history_data[0]["issueNumber"]
        next_period = str(int(current_period) + 1)

        prompt = f"""
You are an expert in detecting advanced patterns in lottery-style game results. Below are past results. Each result contains: Period number, Number (1–9), and Color(s).

Your task is to:
- Analyze the data
- Predict result for the next period (current + 1)
Output strictly in this format:
Period: {next_period}
Number: <number>
Color: <color>
Size: <Big/Small>

Here is the data:
{formatted_data}
"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a powerful AI pattern analyst."},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        prediction = data["choices"][0]["message"]["content"].strip()
        print("🧠 GPT Prediction:", prediction)
        return prediction

    except Exception as e:
        print("❌ GPT Error:", e)
        return f"❌ GPT Error: {e}"

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or args[0] != ACCESS_KEY:
        await update.message.reply_text("❌ Invalid access key.")
        return

    chat_id = update.effective_chat.id
    if chat_id in PREDICTED_USERS:
        await update.message.reply_text("🔄 Already running prediction.")
        return

    PREDICTED_USERS.add(chat_id)
    await update.message.reply_text("✅ Prediction started!")

    async def monitor_results():
        global LAST_SEEN_PERIOD
        while chat_id in PREDICTED_USERS:
            results = await fetch_latest_results()
            if not results:
                await asyncio.sleep(3)
                continue

            current_period = results[0]['issueNumber']
            if LAST_SEEN_PERIOD.get(chat_id) != current_period:
                LAST_SEEN_PERIOD[chat_id] = current_period
                try:
                    prediction = await predict_with_gpt(results)
                    message = (
                        f"🔮 <b>Kalyugi Gand Faad Prediction</b>\n"
                        f"🕐 <b>Period:</b> {int(current_period) + 1}\n"
                        f"📥 <b>Results Fetched:</b> {len(results)}\n"
                        f"📊 <pre>{prediction}</pre>"
                    )
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
                except Exception as e:
                    print("❌ Telegram Send Error:", e)
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")
            await asyncio.sleep(3)

    asyncio.create_task(monitor_results())

# --- Stop Command ---
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in PREDICTED_USERS:
        PREDICTED_USERS.remove(chat_id)
        await update.message.reply_text("🛑 Prediction stopped.")
    else:
        await update.message.reply_text("😴 No prediction is running.")

# --- Main Function ---
async def run_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    await app.bot.set_my_commands([
        BotCommand("start", "Start prediction"),
        BotCommand("stop", "Stop prediction")
    ])

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(run_bot())