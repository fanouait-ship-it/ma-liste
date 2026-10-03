# Publier « Ma liste » en ligne + l'installer comme appli sur ton téléphone

## 1. Ce qui a changé dans `ma_liste.py`

Rien ne change si tu le lances comme avant (`python ma_liste.py`) : même comportement, même mode `--tel`.
Le nouveau **mode en ligne** s'active avec la variable `MA_LISTE_ONLINE=1` (ou `--online`) :

| Ajout | Détail |
|---|---|
| Mot de passe obligatoire | `MA_LISTE_PASSWORD` (10 caractères minimum). Demandé une fois par appareil, cookie sécurisé ensuite. Le script refuse de démarrer sans. |
| Plus d'exception « ce PC » | Derrière un hébergeur, toutes les connexions semblent locales : le mot de passe est donc exigé pour tout le monde. |
| Anti-devinette | 5 erreurs = blocage 5 min, plus 1 s de délai par erreur. |
| Port / dossier | `PORT` (donné par l'hébergeur) et `MA_LISTE_DATA` (dossier des données, sur disque persistant). |
| Appli installable (PWA) | Manifeste, icône, service worker (images en cache, pages utilisables avec une mauvaise connexion), bouton « 📲 Installer l'app ». Il faut du **HTTPS** (fourni par tous les hébergeurs ci-dessous). |
| `/healthz` | Répond `ok`, pour la surveillance de l'hébergeur. |
| En-têtes de sécurité | HSTS, anti-iframe, etc. |

Le mot de passe est la **seule** protection de ton site, qui sera public sur Internet : choisis une longue phrase
(ex. `trois-chats-bleus-mangent-du-riz-2026`), pas un mot simple.

Variables à définir chez l'hébergeur :

- `MA_LISTE_USER` → ton pseudo AniList
- `MA_LISTE_PASSWORD` → ton mot de passe
- (`MA_LISTE_ONLINE` et `MA_LISTE_DATA` sont déjà réglés dans le `Dockerfile`)

## 2. Où l'héberger : 3 options

| Option | Coût | Difficulté | À savoir |
|---|---|---|---|
| **A. Render** (recommandé) | environ 7 $/mois + 0,25 $/Go de disque | facile (tout se fait dans le navigateur) | Toujours allumé, HTTPS automatique. Un disque persistant exige l'offre payante. Vérifie les tarifs actuels sur render.com/pricing. |
| **B. Ton PC + Tailscale Funnel** | gratuit | moyen | Le site marche seulement quand ton PC est allumé et le script lancé. |
| **C. Serveur (VPS) avec Docker** | variable (Oracle Cloud propose une offre « Always Free », mais les places sont rares) | avancé | Plus de contrôle, plus de travail. |

---

## 3. Option A – Render, pas à pas

**Fichiers à avoir** (dossier téléchargé) : `ma_liste.py`, `Dockerfile`, `.dockerignore`, `render.yaml`.

1. **GitHub** : crée un compte sur github.com puis un dépôt **privé** (bouton *New*, coche *Private*).
2. Dans le dépôt : *Add file → Upload files*, glisse les 4 fichiers, puis *Commit changes*.
   (N'ajoute **pas** ton dossier `ma_liste_data`.)
3. **Render** : crée un compte sur render.com, connecte-le à GitHub.
4. *New → Blueprint*, choisis ton dépôt. Render lit `render.yaml` et prépare le service et le disque de 5 Go.
5. Render demande les deux valeurs : `MA_LISTE_USER` (ton pseudo AniList) et `MA_LISTE_PASSWORD` (ton mot de passe).
6. Valide : le premier déploiement dure quelques minutes. Tu obtiens une adresse du type
   `https://ma-liste-xxxx.onrender.com`.
7. Ouvre-la, entre ton mot de passe. **Le premier téléchargement des données est long** (fiches, personnages,
   images de tous tes titres) : laisse tourner, tu peux fermer la page. Les données restent sur le disque `/data`.
8. Clique sur **🔑 Compte** dans l'appli pour reconnecter ton compte AniList (modifier ta liste, favoris).
   Le token est gardé sur le disque du serveur.

*Sans Blueprint (manuel)* : *New → Web Service*, dépôt, **Language : Docker**, type d'instance **Starter**,
*Advanced → Add Disk* (Mount Path `/data`, 5 Go), ajoute les 2 variables, *Health Check Path* : `/healthz`.

**Mise à jour du script** : remplace `ma_liste.py` dans GitHub (*Add file → Upload files*, même nom) : Render redéploie tout seul.

---

## 4. Option B – Ton PC + Tailscale Funnel (gratuit)

Tailscale Funnel donne une adresse HTTPS publique qui pointe vers ton PC.

1. Installe Tailscale (tailscale.com) sur le PC et crée un compte.
2. Active **HTTPS** et **Funnel** pour ton réseau (suis la doc : tailscale.com/kb/1223/funnel).
3. Lance le script (PowerShell sous Windows) :
   ```powershell
   $env:MA_LISTE_ONLINE="1"
   $env:MA_LISTE_USER="TonPseudo"
   $env:MA_LISTE_PASSWORD="ta-longue-phrase-secrète"
   python ma_liste.py
   ```
   Sous Linux/Mac : `MA_LISTE_ONLINE=1 MA_LISTE_USER=TonPseudo MA_LISTE_PASSWORD='…' python3 ma_liste.py`
4. Dans un 2ᵉ terminal : `tailscale funnel 8765`. Il affiche ton adresse `https://ton-pc.xxxx.ts.net`.
5. Utilise cette adresse sur le téléphone. Tes données restent dans `ma_liste_data` à côté du script.

Si le PC s'éteint, le site s'arrête (l'appli installée affichera ce qu'elle a en cache).

---

## 5. Option C – Serveur avec Docker (résumé)

```bash
docker build -t ma-liste .
docker run -d --restart unless-stopped -p 8765:8765 -v ma_liste_data:/data \
  -e PORT=8765 -e MA_LISTE_USER=TonPseudo -e MA_LISTE_PASSWORD='ta-longue-phrase' ma-liste
```
Il faut ensuite un HTTPS devant (Caddy ou Cloudflare Tunnel), sinon le cookie sécurisé et l'installation de l'appli ne marcheront pas.

---

## 6. Installer l'appli sur le téléphone

Ouvre l'adresse HTTPS dans le navigateur, connecte-toi, puis :

- **Android (Chrome)** : touche le bouton orange **« 📲 Installer l'app »** qui apparaît en bas à droite,
  ou menu ⋮ → *Installer l'application* / *Ajouter à l'écran d'accueil*.
- **iPhone (Safari obligatoire)** : bouton Partager (carré avec flèche) → *Sur l'écran d'accueil* → *Ajouter*.

L'icône « Ma liste » apparaît sur l'écran d'accueil et s'ouvre en plein écran, comme une vraie appli.
Sur ordinateur, Chrome/Edge proposent aussi l'installation (icône dans la barre d'adresse).

## 7. Dépannage

| Problème | Solution |
|---|---|
| Le mot de passe est « incorrect » alors qu'il est bon | Tu es en `http://` : le cookie sécurisé ne passe qu'en HTTPS. Utilise l'adresse `https://`. |
| « Trop d'essais » | Attends 5 minutes. |
| Pas de bouton d'installation | Il faut HTTPS, et le bouton disparaît après 20 s : recharge la page. Sur iPhone, passe par *Partager*. |
| Les données disparaissent à chaque déploiement | Le disque n'est pas monté sur `/data` (vérifie *Disk → Mount Path*). |
| Le serveur s'arrête tout de suite | Regarde les logs : il manque `MA_LISTE_USER` ou `MA_LISTE_PASSWORD` (10 caractères minimum). |
| Changer le mot de passe | Modifie `MA_LISTE_PASSWORD` : tous les appareils devront se reconnecter. |
| Tester sur ton PC avant de publier | `MA_LISTE_ONLINE=1 MA_LISTE_USER=Pseudo MA_LISTE_PASSWORD=une-longue-phrase python ma_liste.py`, puis ouvre `http://localhost:8765` (localhost accepte le cookie sécurisé sous Chrome et Firefox). |
