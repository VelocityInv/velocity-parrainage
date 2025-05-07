// Récupération de l'utilisateur Telegram
const tg = window.Telegram.WebApp;
const user = tg.initDataUnsafe?.user;
const userId = user?.id;
const userName = user?.first_name || "invité";

// Afficher le nom
document.getElementById("user-name").textContent = userName;

// Charger les données du serveur
async function loadStats() {
  try {
    const res = await fetch(`/api/stats?user_id=${userId}`);
    const data = await res.json();

    document.getElementById("actifs").textContent = data.actifs;
    document.getElementById("position").textContent = data.position;
    document.getElementById("referral-link").textContent = data.link;
  } catch (err) {
    console.error("Erreur :", err);
    alert("Impossible de charger les données.");
  }
}

// Copier le lien
function copyLink() {
  const text = document.getElementById("referral-link").textContent;
  navigator.clipboard.writeText(text).then(() => {
    alert("Lien copié !");
  });
}

// Recharger
function reload() {
  loadStats();
}

loadStats(); // charger dès le début
