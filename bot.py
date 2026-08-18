import os
import re
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot-pronostics")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}


def api_get(endpoint, params=None):
    resp = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    errors = data.get("errors")
    if errors:
        logger.warning(f"API-Football errors sou '{endpoint}' (params={params}): {errors}")

    results_count = data.get("results", len(data.get("response", [])))
    logger.info(f"API-Football '{endpoint}' params={params} -> {results_count} rezilta")

    return data


def search_team(name):
    data = api_get("teams", {"search": name})
    results = data.get("response", [])
    if not results:
        return None
    return results[0]["team"]


def get_last_fixtures(team_id, count=5):
    data = api_get("fixtures", {"team": team_id, "last": count})
    return data.get("response", [])


def get_head_to_head(id1, id2, count=10):
    data = api_get("fixtures/headtohead", {"h2h": f"{id1}-{id2}", "last": count})
    return data.get("response", [])


def compute_form_score(fixtures, team_id):
    n = len(fixtures)
    if n == 0:
        return 0.0, 0.0, 0.0

    points = 0
    goals_for = 0
    goals_against = 0

    for f in fixtures:
        home_id = f["teams"]["home"]["id"]
        home_goals = f["goals"]["home"] or 0
        away_goals = f["goals"]["away"] or 0

        if home_id == team_id:
            gf, ga = home_goals, away_goals
        else:
            gf, ga = away_goals, home_goals

        goals_for += gf
        goals_against += ga

        if gf > ga:
            points += 3
        elif gf == ga:
            points += 1

    form_pct = points / (n * 3)
    avg_gf = goals_for / n
    avg_ga = goals_against / n
    return form_pct, avg_gf, avg_ga


def compute_h2h_score(h2h, id1, id2):
    wins1 = wins2 = draws = 0
    for f in h2h:
        home_id = f["teams"]["home"]["id"]
        away_id = f["teams"]["away"]["id"]
        hg = f["goals"]["home"] or 0
        ag = f["goals"]["away"] or 0

        if hg == ag:
            draws += 1
        else:
            winner_id = home_id if hg > ag else away_id
            if winner_id == id1:
                wins1 += 1
            elif winner_id == id2:
                wins2 += 1
    return wins1, draws, wins2


def build_prediction(team1, team2):
    id1, id2 = team1["id"], team2["id"]
    name1, name2 = team1["name"], team2["name"]

    fixtures1 = get_last_fixtures(id1, 5)
    fixtures2 = get_last_fixtures(id2, 5)
    h2h = get_head_to_head(id1, id2, 10)

    form1, gf1, ga1 = compute_form_score(fixtures1, id1)
    form2, gf2, ga2 = compute_form_score(fixtures2, id2)
    w1, d, w2 = compute_h2h_score(h2h, id1, id2)

    total_h2h = w1 + d + w2
    h2h_score1 = (w1 / total_h2h) if total_h2h else 0.33
    h2h_score2 = (w2 / total_h2h) if total_h2h else 0.33

    score1 = 0.6 * form1 + 0.4 * h2h_score1
    score2 = 0.6 * form2 + 0.4 * h2h_score2
    diff = score1 - score2

    if diff > 0.15:
        dc = f"1X — {name1} pa dwe pèdi"
        confidence = "Wo"
    elif diff < -0.15:
        dc = f"X2 — {name2} pa dwe pèdi"
        confidence = "Wo"
    elif abs(diff) <= 0.05:
        dc = "12 — match la louvri, nenpòt ekip ka genyen"
        confidence = "Mwayèn"
    else:
        leader = name1 if diff > 0 else name2
        code = "1X" if diff > 0 else "X2"
        dc = f"{code} — ti avantaj pou {leader}"
        confidence = "Mwayèn"

    avg_total_goals = (gf1 + ga1 + gf2 + ga2) / 2
    over_under = "Plis pase 2.5 gòl (Over 2.5)" if avg_total_goals > 2.5 else "Mwens pase 2.5 gòl (Under 2.5)"
    btts = "Wi — toude ekip gen chans fè gòl (BTTS)" if (gf1 > 0.8 and gf2 > 0.8) else "Non garanti (BTTS pa fyab)"

    no_data_warning = ""
    if len(fixtures1) == 0 and len(fixtures2) == 0 and total_h2h == 0:
        no_data_warning = (
            "\n⚠️ *Atansyon:* API-Football pa retounen okenn done pou 2 ekip sa yo. "
            "Sa ka vle di plan gratis la limite (kota rekèt/jou fin, oswa sezon aktyèl "
            "la pa disponib nan plan gratis la). Verifye sou dashboard.api-football.com.\n"
        )

    text = (
        f"⚽ *{name1}* vs *{name2}*\n\n"
        f"📊 Fòm {name1} (5 dènye): {form1*100:.0f}% | {gf1:.1f} mache / {ga1:.1f} bay\n"
        f"📊 Fòm {name2} (5 dènye): {form2*100:.0f}% | {gf2:.1f} mache / {ga2:.1f} bay\n"
        f"🤝 Head-to-head (10 dènye): {name1} {w1}V — {d}N — {w2}V {name2}\n\n"
        f"🎯 *Pwonostik Doub Chans:* {dc}\n"
        f"   Nivo konfyans: {confidence}\n"
        f"⚡ *Ekstra:* {over_under}\n"
        f"⚡ *BTTS:* {btts}\n"
        f"{no_data_warning}\n"
        f"⚠️ Sa s
