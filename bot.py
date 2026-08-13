# bot.py  —  pip install python-telegram-bot==21.6 requests
import os, math, requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_KEY = os.environ.get("FOOTBALL_API_KEY", "")   # api-football.com
SEUIL = 0.85  # 85% minimum pou voye yon siyal

# ---------- 1) Chèche done ----------
def get_fixtures(date: str):
    r = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": API_KEY},
        params={"date": date},
        timeout=20,
    )
    r.raise_for_status()
    return r.json().get("response", [])

def get_form(team_id: int):
    r = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": API_KEY},
        params={"team": team_id, "last": 10},
        timeout=20,
    )
    return r.json().get("response", [])

# ---------- 2) Model senp (Poisson) ----------
def moyen_bi(matchs, team_id):
    fo = fk = 0
    for m in matchs:
        h = m["teams"]["home"]["id"] == team_id
        fo += (m["goals"]["home"] or 0) if h else (m["goals"]["away"] or 0)
        fk += (m["goals"]["away"] or 0) if h else (m["goals"]["home"] or 0)
    n = max(len(matchs), 1)
    return fo / n, fk / n

def poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def probabilites(lam_h, lam_a, max_bi=8):
    p_h = p_d = p_a = p_over25 = 0.0
    for i in range(max_bi):
        for j in range(max_bi):
            p = poisson(i, lam_h) * poisson(j, lam_a)
            if i > j: p_h += p
            elif i == j: p_d += p
            else: p_a += p
            if i + j > 2.5: p_over25 += p
    return {"1": p_h, "X": p_d, "2": p_a, "Over 2.5": p_over25}

def analize(fixture):
    hid = fixture["teams"]["home"]["id"]
    aid = fixture["teams"]["away"]["id"]
    h_fo, h_fk = moyen_bi(get_form(hid), hid)
    a_fo, a_fk = moyen_bi(get_form(aid), aid)
    lam_h = max((h_fo + a_fk) / 2 * 1.10, 0.15)   # 10% avantaj lakay
    lam_a = max((a_fo + h_fk) / 2, 0.15)
    probs = probabilites(lam_h, lam_a)
    pari, konfyans = max(probs.items(), key=lambda kv: kv[1])
    return {
        "match": f'{fixture["teams"]["home"]["name"]} vs {fixture["teams"]["away"]["name"]}',
        "lig": fixture["league"]["name"],
        "pari": pari,
        "konfyans": konfyans,
        "detay": probs,
    }

# ---------- 3) Kòmand Telegram ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Bòt Analiz Foutbòl\n\n"
        "/match AAAA-MM-JJ – analize match jounen an\n"
        "/seuil 90 – chanje seuil konfyans (%)\n\n"
        "⚠️ Analiz statistik sèlman, pa gen garanti."
    )

async def seuil_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global SEUIL
    try:
        SEUIL = float(ctx.args[0]) / 100
        await update.message.reply_text(f"✅ Seuil mete a {SEUIL:.0%}")
    except Exception:
        await update.message.reply_text("Egzanp: /seuil 90")

async def match_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    date = ctx.args[0] if ctx.args else __import__("datetime").date.today().isoformat()
    await update.message.reply_text(f"🔎 M ap analize match {date}...")
    try:
        fixtures = get_fixtures(date)[:25]
    except Exception as e:
        return await update.message.reply_text(f"❌ Erè API: {e}")

    siyal = []
    for f in fixtures:
        try:
            r = analize(f)
            if r["konfyans"] >= SEUIL:
                siyal.append(r)
        except Exception:
            continue

    if not siyal:
        return await update.message.reply_text(
            f"Pa gen match ki rive nan {SEUIL:.0%} konfyans jodi a. Se yon bon siy — pa fòse pari."
        )

    siyal.sort(key=lambda r: -r["konfyans"])
    msg = f"📊 Siyal ≥ {SEUIL:.0%} ({date})\n\n"
    for r in siyal[:10]:
        msg += (
            f"🏆 {r['lig']}\n⚽ {r['match']}\n"
            f"🎯 Pari: {r['pari']}\n📈 Konfyans: {r['konfyans']:.1%}\n"
            f"   1: {r['detay']['1']:.0%} | X: {r['detay']['X']:.0%} | 2: {r['detay']['2']:.0%}\n\n"
        )
    msg += "⚠️ Enfòmasyon sèlman. Pari se risk."
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("match", match_cmd))
    app.add_handler(CommandHandler("seuil", seuil_cmd))
    app.run_polling()

if __name__ == "__main__":
    main()
    
