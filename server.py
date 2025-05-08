import os
import json
import threading
from flask import Flask, send_from_directory, request, jsonify, Response
from dotenv import load_dotenv
from telegram import Bot
from io import StringIO
import asyncio

load_dotenv("token.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CANAL_ID = os.getenv("CANAL_ID")
REFERRALS_FILE = "referrals.json"
ADMIN_KEY = "velocity2025admin"

bot = Bot(BOT_TOKEN)
app = Flask(__name__, static_folder="webapp")

# Variable globale pour éviter les conflits de polling
polling_active = False

# Servir les fichiers statiques
@app.route("/")
def root():
    return send_from_directory("webapp", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("webapp", path)

# API de données
@app.route("/api/stats")
def api_stats():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id manquant"}), 400

    # Charger les données
    if os.path.exists(REFERRALS_FILE):
        with open(REFERRALS_FILE, "r") as f:
            referrals = json.load(f)
    else:
        referrals = {}

    filleuls = referrals.get(user_id, [])
    actifs = 0

    for fid in filleuls:
        try:
            status = bot.get_chat_member(CANAL_ID, fid)
            if status.status in ["member", "administrator", "creator"]:
                actifs += 1
        except:
            pass

    # Classement
    classement = []
    for parrain_id, filleuls_list in referrals.items():
        actifs_count = 0
        for fid in filleuls_list:
            try:
                status = bot.get_chat_member(CANAL_ID, fid)
                if status.status in ["member", "administrator", "creator"]:
                    actifs_count += 1
            except:
                pass
        classement.append((parrain_id, actifs_count))

    classement.sort(key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (pid, _) in enumerate(classement) if pid == user_id), None)

    link = f"https://t.me/VelocityParrainBot?start={user_id}"

    return jsonify({
        "actifs": actifs,
        "position": position or "-",
        "link": link
    })

# Admin page pour générer un fichier texte
@app.route("/admin")
def admin_dashboard():
    key = request.args.get("key")
    if key != ADMIN_KEY:
        return "Accès refusé", 403

    if not os.path.exists(REFERRALS_FILE):
        return "Aucune donnée de parrainage."

    with open(REFERRALS_FILE, "r") as f:
        referrals = json.load(f)

    output = StringIO()
    output.write("Parrain ID | Prénom | Filleuls totaux | Filleuls actifs\n")
    output.write("="*60 + "\n")

    async def process():
        for parrain_id, filleuls in referrals.items():
            actifs = 0
            for fid in filleuls:
                try:
                    member = await bot.get_chat_member(CANAL_ID, fid)
                    if member.status in ["member", "administrator", "creator"]:
                        actifs += 1
                except:
                    pass
            try:
                user = await bot.get_chat(chat_id=CANAL_ID, user_id=int(parrain_id))
                name = user.first_name
            except:
                name = f"ID {parrain_id}"
            output.write(f"{parrain_id} | {name} | {len(filleuls)} | {actifs}\n")

    asyncio.run(process())

    text_output = output.getvalue()
    return Response(
        text_output,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=parrainage.txt"}
    )

# Fonction pour démarrer le bot, avec verrouillage de polling
def start_bot():
    global polling_active
    if polling_active:
        print("Bot is already running.")
        return

    polling_active = True
    from aiogram import Dispatcher

    dp = Dispatcher(bot)
    dp.start_polling()

if __name__ == "__main__":
    # Démarre uniquement le bot dans un thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    # Lancer Flask en mode serveur web
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


