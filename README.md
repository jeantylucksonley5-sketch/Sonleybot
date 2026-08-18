# Bot Telegram — Pwonostik Match

Bot sa a resevwa yon mesaj tankou `Real Madrid vs Barcelona`, li chèche estatistik
2 ekip yo (fòm 5 dènye match, head-to-head) sou API-Football, epi li retounen
yon pwonostik Doub Chans (1X / X2 / 12) plis Over/Under 2.5 gòl ak BTTS.

## Kontni dosye a
- bot.py -> kòd bot la
- requirements.txt -> lis pakè Python
- .env -> kle sekrè yo (Telegram token + API-Football key)

## Deplwaye sou Railway.app
1. Kreye kont sou railway.app
2. Nouvo pwojè -> konekte repo GitHub Sonleybot la
3. Nan Variables, ajoute TELEGRAM_BOT_TOKEN ak API_FOOTBALL_KEY
4. Start Command: python bot.py
5. Deploy

## Itilize bot la
Voye /start sou Telegram, epi voye Ekip1 vs Ekip2
