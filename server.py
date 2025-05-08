import os
import json
from flask import Flask, request, jsonify, send_from_directory, Response
from dotenv import load_dotenv
from telegram import Bot, Update
from aiogram.dispatcher import Dispatcher  # Ajout de l'importation
from io import StringIO
import asyncio
import logging

load_dotenv("token.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CANAL_ID = os.getenv("CANAL_ID")
REFERRALS_FILE = "referrals.json"
ADMIN_KEY = "velocity2025admin"

bot = Bot(BOT_TOKEN)
app = Flask(__name__, static_folder="webapp")

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Serve static files
@app.route("/")
def root():
    return send_from_directory("webapp", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("webapp", path)

# API de données pour stats
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

# Webhook handling function
def webhook(update: Update):
    dispatcher = Dispatcher(bot, update, workers=4)  # Ici, Dispatcher est utilisé pour gérer les mises à jour
    dispatcher.process_update(update)

@app.route("/webhook", methods=["POST"])
def webhook_handler():
    if request.method == "POST":
        json_str = request.get_data().decode("UTF-8")
        update = Update.de_json(json.loads(json_str), bot)
        webhook(update)
        return "ok"

if __name__ == "__main__":
    # Set Webhook on Telegram
    webhook_url = os.getenv("WEBHOOK_URL")  # Vous devez définir l'URL correcte du webhook
    bot.set_webhook(url=webhook_url + "/webhook")
    
    # Run the Flask app on Render, make sure to use the appropriate port
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

