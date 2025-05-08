import os
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from dotenv import load_dotenv
from aiogram.utils import executor

load_dotenv()  # Charge les variables si en local

BOT_TOKEN = os.getenv("BOT_TOKEN")
CANAL_ID = os.getenv("CANAL_ID")

# Chargement des variables d'environnement
load_dotenv(dotenv_path="token.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CANAL_ID = os.getenv("CANAL_ID")  # ex: @VelocityInvestments

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation du bot et du dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Fichier de stockage des parrainages
REFERRALS_FILE = "referrals.json"

# Charger les données existantes
if os.path.exists(REFERRALS_FILE):
    with open(REFERRALS_FILE, "r") as f:
        try:
            referrals = json.load(f)
        except:
            referrals = {}
else:
    referrals = {}

# Commande /start
@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    args = message.text.split(" ")
    referrer_id = None

    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != user_id:
                if str(referrer_id) not in referrals:
                    referrals[str(referrer_id)] = []
                if user_id not in referrals[str(referrer_id)]:
                    referrals[str(referrer_id)].append(user_id)

                    # Sauvegarde
                    with open(REFERRALS_FILE, "w") as f:
                        json.dump(referrals, f, indent=2)
        except:
            pass

    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    canal_url = "https://t.me/VelocityInvestments"
    first_name = message.from_user.first_name

    # 👉 Bouton WebApp
    webapp_url = "https://velocity-parrainage.onrender.com"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="🚀 Ouvrir l'application", web_app={"url": webapp_url})]
    ])

    await message.answer(
        f"👋 Bienvenue <b>{first_name}</b> !\n\n"
        f"👉 Rejoins le canal Telegram pour valider ton parrainage :\n"
        f"📲 <a href='{canal_url}'>{canal_url}</a>\n\n"
        f"Voici également ton lien de parrainage unique 👇\n"
        f"<code>{referral_link}</code>\n\n"
        f"📌 <b>Liste des commandes disponibles :</b>\n"
        f"/start – Revenir à ce message\n"
        f"/stats – Voir combien de personnes tu as parrainées\n"
        f"/top – Classement des parrains\n",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

# Commande /stats
@router.message(Command("stats"))
async def stats_handler(message: Message):
    user_id = str(message.from_user.id)
    filleuls = referrals.get(user_id, [])

    if not filleuls:
        await message.answer("Tu n’as encore parrainé personne.")
        return

    bot = message.bot

    # Étape 1 : Compter les filleuls actifs de cet utilisateur
    actifs = 0
    for fid in filleuls:
        try:
            status = await bot.get_chat_member(CANAL_ID, fid)
            if status.status in ["member", "administrator", "creator"]:
                actifs += 1
        except:
            pass

    # Étape 2 : Construire un classement global
    classement = []
    for parrain_id, filleuls_list in referrals.items():
        actifs_par_parrain = 0
        for fid in filleuls_list:
            try:
                status = await bot.get_chat_member(CANAL_ID, fid)
                if status.status in ["member", "administrator", "creator"]:
                    actifs_par_parrain += 1
            except:
                pass
        classement.append((parrain_id, actifs_par_parrain))

    # Étape 3 : Trier le classement (du + au -)
    classement.sort(key=lambda x: x[1], reverse=True)

    # Étape 4 : Trouver la position du parrain actuel
    position = next((i + 1 for i, (pid, _) in enumerate(classement) if pid == user_id), None)

    await message.answer(
        f"📊 <b>Statistiques de parrainage</b> :\n\n"
        f"👥 Parrainés au total : <b>{len(filleuls)}</b>\n"
        f"✅ Encore abonnés au canal : <b>{actifs}</b>\n"
        f"🏆 Ta position dans le classement : <b>#{position}</b>",
        parse_mode=ParseMode.HTML
    )

# Commande /top
@router.message(Command("top"))
async def top_handler(message: Message):
    bot = message.bot
    classement = []

    # Construire la liste (parrain_id, nombre d'actifs)
    for parrain_id, filleuls in referrals.items():
        actifs = 0
        for fid in filleuls:
            try:
                status = await bot.get_chat_member(CANAL_ID, fid)
                if status.status in ["member", "administrator", "creator"]:
                    actifs += 1
            except:
                pass
        classement.append((parrain_id, actifs))

    # Trier par nombre d'actifs décroissant
    classement.sort(key=lambda x: x[1], reverse=True)

    # Construire le message à afficher
    if not classement or all(actifs == 0 for _, actifs in classement):
        await message.answer("Aucun parrain actif pour le moment.")
        return

    message_text = "🏆 <b>Top 5 Parrains - Filleuls actifs</b>\n\n"
    top_limit = min(5, len(classement))
    for i in range(top_limit):
        parrain_id, actifs = classement[i]
        try:
            user = await bot.get_chat_member(chat_id=message.chat.id, user_id=int(parrain_id))
            name = user.user.first_name
        except:
            name = f"ID {parrain_id}"
        message_text += f"{i + 1}. {name} – <b>{actifs}</b> actifs\n"

    await message.answer(message_text, parse_mode=ParseMode.HTML)

# Lancement du bot
async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

