import os
import json
import csv
from flask import Flask, send_from_directory, request, jsonify, Response
from dotenv import load_dotenv
from telegram import Bot
from io import StringIO

load_dotenv("token.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CANAL_ID = os.getenv("CANAL_ID")
REFERRALS_FILE = "referrals.json"
ADMIN_KEY = "velocity2025admin"  # Change la clé secrète si tu veux plus de sécurité

bot = Bot(BOT_TOKEN)
app = Flask(__name__, static_folder="webapp")

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

# Route pour accéder aux données d'admin
@app.route("/admin")
def admin_dashboard():
    key = request.args.get("key")
    if key != ADMIN_KEY:
        return "Accès refusé", 403

    # Charger le fichier referrals.json
    if not os.path.exists(REFERRALS_FILE):
        return "Aucune donnée de parrainage."

    with open(REFERRALS_FILE, "r") as f:
        referrals = json.load(f)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Parrain ID", "Prénom", "Filleuls totaux", "Filleuls actifs"])

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
                user = await bot.get_chat_member(chat_id=CANAL_ID, user_id=int(parrain_id))
                name = user.user.first_name
            except:
                name = f"ID {parrain_id}"
            writer.writerow([parrain_id, name, len(filleuls), actifs])

    import asyncio
    asyncio.run(process())

    csv_output = output.getvalue()
    return Response(
        csv_output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=parrainage.csv"}
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

