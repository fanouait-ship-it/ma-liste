#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ma liste Animés & Mangas – interface style Crunchyroll, 100 % hors ligne (v4.4).

Aucune dépendance à installer.

v4.5 : « tout télécharger » — chaque animé / manga présent (ma liste, toutes les versions des franchises,
tendances) a sa fiche complète, ses images et ses personnages. Les fiches ou images manquantes sont
détectées et retéléchargées automatiquement, et une fiche ouverte sans données est récupérée à la demande.

Utilisation :
    python ma_liste.py MonPseudo      (la 1re fois, le pseudo est mémorisé)
    python ma_liste.py                (ensuite)
    python ma_liste.py --tel          (+ accès depuis le téléphone, même Wi-Fi, protégé par un code)

v4.9 : fiche d'œuvre au style du profil (bannière, onglets collants, cartes) et interactive (filtres, graphiques survolables, flèches, couleur d'accent).
v4.6 : fiches animé / manga immersives plein écran (style AniList) : bannière, panneau « ma liste » en verre,
onglets Aperçu / Personnages / Staff / Franchise / Épisodes, colonne d'informations et tags.

Onglets : Accueil, Animés, Mangas, Calendrier, Saisons, Catalogue, Profil.

Onglet « Accueil » : bannière des animés TENDANCE, « Continuer à regarder » et des rangées
(tendances de la semaine, populaires de la saison, saison prochaine, mieux notés) renouvelées
automatiquement chaque semaine. Ces animés sont téléchargés comme les autres (synopsis, infos,
personnages, staff…) et apparaissent aussi dans le Catalogue (filtre « Tendances de la semaine »).
Chaque semaine, l'Accueil est remplacé par de nouvelles tendances, mais les précédentes ne sont jamais supprimées :
elles deviennent de simples animés du Catalogue (sans catégorie spéciale).

Onglet « Saisons » : TOUT ce qui sort pendant la saison précédente, la saison en cours et la saison suivante
(sans limite : séries, films, OVA, ONA, spéciaux…), fiches complètes + personnages + images. Téléchargé automatiquement
à chaque changement de saison (et mis à jour chaque semaine). Les saisons passées ne sont jamais supprimées.

« Catalogue » : tous les animés et mangas téléchargés (ma liste + toutes les versions des franchises),
avec un filtre en haut : Tout / Animés / Mangas, recherche, genre, format, statut dans ma liste et tri.
Bouton « ⬇ Télécharger des titres » : choisis un nombre (ex. 5), animés ou mangas, populaires ou mieux notés :
le script télécharge autant de NOUVEAUX titres (absents du catalogue) avec fiche complète, personnages, staff et images.
Leurs versions liées (autres saisons, films, OVA, mangas…) sont téléchargées aussi.
Ils ne sont jamais supprimés et se consultent comme tous les autres titres du Catalogue.

Chaque animé / manga a sa PAGE dédiée (clic sur la jaquette) :
  bannière, jaquette HD (zoomable), synopsis, bande-annonce, infos complètes,
  TOUTES LES VERSIONS de la franchise (séries, saisons, films, OVA, mangas, light novels…),
  personnages + doubleurs, staff, liste d'épisodes, statistiques, recommandations, liens.

Accueil « Continuer à regarder » (bannière + bouton +1),
Onglet « Calendrier » (style Crunchyroll / AniList) : prochaine sortie en direct, vues Jour / Semaine / Mois,
ma liste ou TOUT le programme AniList (filtre plateforme, populaires, ajout rapide à ma liste),
« Recommandé pour toi » et modification de ta liste (statut, progression, note) :
clique sur 🔑 Compte en haut pour connecter ton compte (une seule fois).

Cœur ♥ sur chaque jaquette (et sur les fiches) : ajoute / retire un favori, synchronisé avec AniList
(compte connecté via 🔑 Compte requis pour modifier ; les favoris existants s'affichent sans connexion).

Onglet « Profil » : bio, avatar, bannière, favoris, statistiques détaillées
(statuts, notes, formats, genres, tags, studios, années…) et historique d'activité.

Tout est sauvegardé dans le dossier « ma_liste_data » (consultable sans internet).
Rafraîchissement automatique tous les 7 jours + bouton « Rafraîchir ».

v5.0 – MODE EN LIGNE + APPLI TÉLÉPHONE (PWA) :
    MA_LISTE_ONLINE=1 MA_LISTE_USER=MonPseudo MA_LISTE_PASSWORD=un-long-mot-de-passe python ma_liste.py
    (ou : python ma_liste.py --online, avec les variables MA_LISTE_USER / MA_LISTE_PASSWORD définies)
  - le serveur écoute sur le port donné par l'hébergeur (variable PORT) et exige TOUJOURS le mot de passe
    (y compris pour les connexions « locales » qui, derrière un hébergeur, viennent en réalité d'Internet) ;
  - MA_LISTE_DATA = dossier des données (à mettre sur un disque persistant chez l'hébergeur) ;
  - l'appli est installable sur le téléphone (manifeste + service worker + icônes), en HTTPS uniquement ;
  - /healthz répond « ok » sans mot de passe (surveillance de l'hébergeur).
Sans ces réglages, le script se comporte exactement comme avant.
"""
import base64
import datetime
import hashlib
import html
import http.cookies
import ipaddress
import json
import math
import os
import re
import secrets
import socket
import sys
import time
import threading
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ONLINE = "--online" in sys.argv[1:] or os.environ.get("MA_LISTE_ONLINE", "").strip().lower() in ("1", "true", "yes", "oui")
MOT_DE_PASSE = "Fanoumanhwa45510"   # mot de passe du mode en ligne (10 caractères minimum). La variable MA_LISTE_PASSWORD, si elle existe, est prioritaire.
ONLINE_PASSWORD = (os.environ.get("MA_LISTE_PASSWORD") or MOT_DE_PASSE).strip() if ONLINE else ""
ONLINE_SESS = hashlib.sha256(("ma-liste-session:" + ONLINE_PASSWORD).encode("utf-8")).hexdigest() if ONLINE else ""
BASE = Path(os.environ.get("MA_LISTE_DATA") or "") if (ONLINE and os.environ.get("MA_LISTE_DATA")) \
    else Path(__file__).resolve().parent / "ma_liste_data"
IMG = BASE / "img"
DETAILS = BASE / "details"
CHARDIR = BASE / "characters"
DATA_FILE = BASE / "data.json"
INDEX_FILE = BASE / "index.json"
PROFILE_FILE = BASE / "profile.json"
CONF_FILE = BASE / "config.json"
PORT = int(os.environ.get("PORT") or 8765) if ONLINE else 8765   # en ligne : l'hébergeur impose le port
PHONE_MODE = False        # True = accessible depuis le téléphone à chaque lancement (sinon : python ma_liste.py --tel)
LAN = PHONE_MODE or ONLINE or "--tel" in sys.argv[1:]
HOST = "0.0.0.0" if LAN else "127.0.0.1"   # 127.0.0.1 = ce PC uniquement (comportement d'origine)
PIN_COOKIE = "ml_auth"
LOCAL_ADDRS = {"127.0.0.1", "::1"}         # ce PC : jamais de code demandé
LOGIN_FAILS = {}                           # ip -> (échecs, bloqué jusqu'à)
REFRESH_SECONDS = 7 * 24 * 3600
DATA_VERSION = 5          # change => re-téléchargement automatique au prochain lancement
CHAR_INFO = True          # télécharge la fiche complète de chaque personnage (False = désactivé)
CHAR_BATCH = 8            # personnages demandés par requête
CHARACTERS = 12           # personnages téléchargés par titre (0 = aucun)
DETAIL_BATCH = 3          # fiches demandées par requête
RELATED_DEPTH = 6         # niveaux d'œuvres liées téléchargées (0 = seulement ma liste, 1-3 conseillé)
EXTRA_TTL = 30 * 24 * 3600  # les fiches d'œuvres liées sont rafraîchies tous les 30 jours
COMPLETE_ALL = True        # vérifie et complète TOUTES les fiches / images / personnages présents
REFETCH_DETAILS = False     # True = re-télécharger toutes les fiches à chaque rafraîchissement
PROFILE_TTL = 24 * 3600     # le profil (bio, favoris, activité) est actualisé une fois par jour
ACTIVITY_PAGES = 10         # pages d'activité AniList téléchargées (50 par page)
FRANCHISE_RELS = {"SEQUEL", "PREQUEL", "PARENT", "SIDE_STORY", "SPIN_OFF", "ADAPTATION",
                  "ALTERNATIVE", "SOURCE", "SUMMARY", "COMPILATION", "CONTAINS"}
API = "https://graphql.anilist.co"
USER = ""

LIST_QUERY = """
query ($user: String, $type: MediaType, $chunk: Int) {
  MediaListCollection(userName: $user, type: $type, chunk: $chunk, perChunk: 500) {
    hasNextChunk
    lists { entries {
      status progress score(format: POINT_10) updatedAt
      media {
        id siteUrl format status episodes chapters genres averageScore
        title { romaji english }
        coverImage { extraLarge }
        startDate { year }
        nextAiringEpisode { episode airingAt }
      }
    } }
  }
}
"""

DETAIL_QUERY = """
query ($ids: [Int], $per: Int, $nc: Int) {
  Page(perPage: $per) {
    media(id_in: $ids) {
      id type format status season seasonYear episodes duration chapters volumes updatedAt
      source countryOfOrigin isAdult genres synonyms bannerImage siteUrl idMal
      averageScore meanScore popularity favourites
      description(asHtml: true)
      title { romaji english native }
      coverImage { extraLarge color }
      startDate { year month day } endDate { year month day }
      nextAiringEpisode { episode airingAt }
      trailer { id site }
      studios { edges { isMain node { name isAnimationStudio } } }
      tags { name rank isMediaSpoiler }
      rankings { rank type context allTime }
      externalLinks { site url type }
      characters(perPage: $nc, sort: [ROLE, RELEVANCE]) {
        edges { role node { id name { full native } image { large } }
                voiceActors(language: JAPANESE) { id name { full } image { large } } }
      }
      staff(perPage: 12, sort: [RELEVANCE]) { edges { role node { id name { full } image { large } } } }
      relations { edges { relationType(version: 2)
        node { id type format status episodes chapters title { romaji english }
               coverImage { large } startDate { year } } } }
      recommendations(perPage: 10, sort: RATING_DESC) { nodes { rating
        mediaRecommendation { id type format status episodes chapters averageScore
                              title { romaji english } coverImage { large } startDate { year } } } }
      streamingEpisodes { title url site }
      stats { scoreDistribution { score amount } statusDistribution { status amount } }
    }
  }
}
"""

CHAR_QUERY = """
query ($ids: [Int], $per: Int) {
  Page(perPage: $per) {
    characters(id_in: $ids) {
      id siteUrl favourites gender age bloodType
      name { full native alternative alternativeSpoiler }
      image { large }
      description(asHtml: true)
      dateOfBirth { year month day }
      media(perPage: 15, sort: [POPULARITY_DESC]) {
        edges { characterRole
          voiceActors(language: JAPANESE) { id name { full } image { large } }
          node { id type format title { romaji english } coverImage { large } startDate { year } } }
      }
    }
  }
}
"""

lock = threading.Lock()
state = {"running": False, "message": "", "error": ""}
data_lock = threading.Lock()
CONF = {}


def save_conf():
    CONF_FILE.write_text(json.dumps(CONF), encoding="utf-8")
    try:
        CONF_FILE.chmod(0o600)  # le token AniList reste privé
    except OSError:
        pass


class ApiError(Exception):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------- Téléchargement
def anilist(query, variables, token=None):
    body = json.dumps({"query": query, "variables": variables}).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "ma-liste/4.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    for attempt in range(5):
        try:
            req = urllib.request.Request(API, body, headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.load(r)
            if not j.get("data"):
                raise ApiError(400)
            return j["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(min(int(e.headers.get("Retry-After", "30")), 90))
                continue
            if e.code >= 500 and attempt < 4:
                time.sleep(2 * (attempt + 1))
                continue
            raise ApiError(e.code)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            if attempt < 4:  # coupure réseau / réponse tronquée : on réessaie
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError("Trop de requêtes, réessaie dans quelques minutes.")


def fetch_list(user, mtype):
    out, chunk = {}, 1
    while True:
        try:
            coll = anilist(LIST_QUERY, {"user": user, "type": mtype, "chunk": chunk})["MediaListCollection"]
        except ApiError as e:
            if e.code in (403, 404):
                raise RuntimeError(f"Utilisateur « {user} » introuvable ou liste privée.")
            raise
        for lst in coll["lists"]:
            for e in lst["entries"]:
                m = e["media"]
                if m["id"] in out:  # doublon via une liste personnalisée
                    continue
                t = m["title"]
                nxt = m.get("nextAiringEpisode")
                out[m["id"]] = {
                    "id": m["id"], "type": mtype,
                    "title": t.get("english") or t.get("romaji") or "?",
                    "romaji": t.get("romaji"),
                    "cover_url": (m.get("coverImage") or {}).get("extraLarge"),
                    "status": e["status"], "progress": e["progress"] or 0,
                    "total": m["episodes"] if mtype == "ANIME" else m["chapters"],
                    "media_status": m["status"], "format": m["format"],
                    "genres": m["genres"] or [], "score": e["score"],
                    "avg": m["averageScore"], "year": (m["startDate"] or {}).get("year"),
                    "url": m["siteUrl"], "updated": e["updatedAt"] or 0,
                    "next_ep": nxt["episode"] if nxt else None,
                    "next_at": nxt["airingAt"] if nxt else None,
                }
        if not coll.get("hasNextChunk"):
            return list(out.values())
        chunk += 1
        time.sleep(0.7)


def fetch_details(ids):
    try:
        return anilist(DETAIL_QUERY, {"ids": ids, "per": len(ids), "nc": CHARACTERS})["Page"]["media"]
    except ApiError:
        if len(ids) == 1:
            return []
        out = []  # requête trop lourde : on réessaie titre par titre
        for i in ids:
            out += fetch_details([i])
            time.sleep(0.7)
        return out


def fetch_characters(ids):
    try:
        return anilist(CHAR_QUERY, {"ids": ids, "per": len(ids)})["Page"]["characters"]
    except ApiError:
        if len(ids) == 1:
            return []
        out = []  # requête trop lourde : on réessaie personnage par personnage
        for i in ids:
            out += fetch_characters([i])
            time.sleep(0.7)
        return out


def _birth(x):
    """Date de naissance d'un personnage (l'année est souvent inconnue)."""
    x = x or {}
    return {"y": x.get("year"), "m": x.get("month"), "d": x.get("day")} if x.get("month") or x.get("year") else None


def slim_char(c, hi):
    """Réduit la fiche d'un personnage à ce qui est affiché + images à télécharger."""
    cid = c["id"]
    img, url = None, (c.get("image") or {}).get("large")
    if url:
        img = f"char_{cid}.jpg"
        hi.append((url, img))
    media = []
    for e in (c.get("media") or {}).get("edges", []):
        n = e.get("node") or {}
        if not n.get("id"):
            continue
        cu = (n.get("coverImage") or {}).get("large")
        if cu:
            hi.append((cu, f"cover_{n['id']}.jpg"))
        vas = []
        for v in (e.get("voiceActors") or [])[:3]:
            vimg, vurl = None, (v.get("image") or {}).get("large")
            if vurl:
                vimg = f"staff_{v['id']}.jpg"
                hi.append((vurl, vimg))
            vas.append({"id": v["id"], "name": v["name"]["full"], "img": vimg})
        media.append({"id": n["id"], "type": n.get("type"), "format": n.get("format"), "title": _title(n.get("title")),
                      "year": (n.get("startDate") or {}).get("year"), "role": e.get("characterRole"), "va": vas})
    nm = c["name"]
    return {"id": cid, "name": nm["full"], "native": nm.get("native"),
            "alt": nm.get("alternative") or [], "alt_spoiler": nm.get("alternativeSpoiler") or [],
            "description": c.get("description"), "gender": c.get("gender"), "age": c.get("age"),
            "blood": c.get("bloodType"), "birth": _birth(c.get("dateOfBirth")),
            "favourites": c.get("favourites"), "url": c.get("siteUrl"), "img": img, "media": media}


def char_refs(c):
    r = {c.get("img")}
    for m in c.get("media", []):
        r.add(f"cover_{m['id']}.jpg")
        r.update(v.get("img") for v in m.get("va", []))
    r.discard(None)
    return r


def wanted_chars(ids):
    """Personnages à télécharger : ceux des fiches de ma liste + les personnages favoris du profil."""
    out = set()
    for i in ids:
        out.update(c["id"] for c in load_json(DETAILS / f"{i}.json", {}).get("characters", []))
    out.update(n["id"] for n in (load_json(PROFILE_FILE, {}).get("favourites") or {}).get("characters", []))
    return out


def char_gap(i):
    """Fiche de personnage absente, périmée, illisible ou dont la photo / celles des doubleurs manquent."""
    f = CHARDIR / f"{i}.json"
    if not fresh(f):
        return True
    c = load_json(f, None)
    if not c or "media" not in c:
        return True
    names = [c.get("img")] + [v.get("img") for m in c.get("media", []) for v in m.get("va", [])]
    return any(n and not img_ok(n) for n in names)


def download_characters(ids, dlr):
    CHARDIR.mkdir(parents=True, exist_ok=True)
    need = [i for i in sorted(ids) if char_gap(i)]
    bad = streak = 0
    for k in range(0, len(need), CHAR_BATCH):
        state["message"] = f"Fiches des personnages {min(k + CHAR_BATCH, len(need))}/{len(need)}…"
        hi = []
        try:
            for c in fetch_characters(need[k:k + CHAR_BATCH]):
                save_json(CHARDIR / f"{c['id']}.json", slim_char(c, hi))
            streak = 0
        except Exception:
            bad += 1
            streak += 1
            if streak >= 6:
                break
        dlr.add(hi)
        time.sleep(0.7)


def character_file(cid):
    """Fiche d'un personnage : lue sur le disque, sinon téléchargée à la demande (si internet)."""
    f = CHARDIR / f"{cid}.json"
    if f.is_file():
        return f
    try:
        CHARDIR.mkdir(parents=True, exist_ok=True)
        IMG.mkdir(parents=True, exist_ok=True)
        hi = []
        for c in fetch_characters([cid]):
            save_json(f, slim_char(c, hi))
        for url, name in hi:
            dl(url, name)
    except Exception:
        return None
    return f if f.is_file() else None


def media_file(mid):
    """Fiche d'une œuvre : lue sur le disque, sinon téléchargée à la demande (si internet)."""
    f = DETAILS / f"{mid}.json"
    d = load_json(f, None)
    if d and "id" in d and "characters" in d:  # fiche présente : pas de requête (consultable hors ligne)
        return f
    try:
        DETAILS.mkdir(parents=True, exist_ok=True)
        IMG.mkdir(parents=True, exist_ok=True)
        hi, low = [], {}
        old = load_json(f, None) or {}
        for m in fetch_details([mid]):
            save_json(f, slim(m, hi, low, bool(old.get("extra", True))))
        for url, name in hi:
            dl(url, name)
        for name, url in low.items():
            dl(url, name)
        build_index()
    except Exception:
        pass
    return f if f.is_file() else None


def _date(x):
    return {"y": x.get("year"), "m": x.get("month"), "d": x.get("day")} if x and x.get("year") else None


def _title(t):
    return (t or {}).get("english") or (t or {}).get("romaji") or "?"


def stub(n, low):
    """Résumé d'une œuvre liée / recommandée (+ jaquette moyenne à télécharger en dernier recours)."""
    c = (n.get("coverImage") or {}).get("large")
    if c:
        low[f"cover_{n['id']}.jpg"] = c
    return {"id": n["id"], "type": n["type"], "format": n.get("format"), "title": _title(n.get("title")),
            "status": n.get("status"), "year": (n.get("startDate") or {}).get("year"),
            "count": n.get("episodes") if n["type"] == "ANIME" else n.get("chapters")}


def slim(m, hi, low, extra):
    """Réduit la fiche AniList à ce qui est affiché et prépare les images à télécharger."""
    trailer = embed = None
    tr = m.get("trailer")
    if tr and tr.get("id"):
        site = (tr.get("site") or "").lower()
        if site == "youtube":
            trailer = "https://www.youtube.com/watch?v=" + tr["id"]
            embed = "https://www.youtube-nocookie.com/embed/" + tr["id"]
        elif site == "dailymotion":
            trailer = "https://www.dailymotion.com/video/" + tr["id"]
            embed = "https://www.dailymotion.com/embed/video/" + tr["id"]
    banner = None
    if m.get("bannerImage"):
        banner = f"banner_{m['id']}.jpg"
        hi.append((m["bannerImage"], banner))
    ci = m.get("coverImage") or {}
    cover = None
    if ci.get("extraLarge"):
        cover = f"cover_{m['id']}.jpg"
        hi.append((ci["extraLarge"], cover))

    chars = []
    for e in m["characters"]["edges"]:
        n = e["node"]
        url = (n.get("image") or {}).get("large")
        img = None
        if url:
            img = f"char_{n['id']}.jpg"
            hi.append((url, img))
        vas = []
        for v in (e.get("voiceActors") or [])[:2]:
            vimg, vurl = None, (v.get("image") or {}).get("large")
            if vurl:
                vimg = f"staff_{v['id']}.jpg"
                hi.append((vurl, vimg))
            vas.append({"id": v["id"], "name": v["name"]["full"], "img": vimg})
        chars.append({"id": n["id"], "name": n["name"]["full"], "native": n["name"].get("native"),
                      "role": e["role"], "img": img, "va": vas})

    staff = []
    for e in m["staff"]["edges"]:
        n = e["node"]
        simg, surl = None, (n.get("image") or {}).get("large")
        if surl:
            simg = f"staff_{n['id']}.jpg"
            hi.append((surl, simg))
        staff.append({"id": n["id"], "name": n["name"]["full"], "role": e["role"], "img": simg})

    studios = sorted((e for e in m["studios"]["edges"] if e["node"]["isAnimationStudio"]),
                     key=lambda e: not e["isMain"])
    nxt = m.get("nextAiringEpisode")
    st = m.get("stats") or {}
    return {
        "id": m["id"], "mupd": m.get("updatedAt"), "type": m["type"], "title": m["title"], "synonyms": m["synonyms"] or [],
        "description": m["description"], "format": m["format"], "status": m["status"],
        "season": m["season"], "season_year": m["seasonYear"], "episodes": m["episodes"],
        "duration": m["duration"], "chapters": m["chapters"], "volumes": m["volumes"],
        "source": m["source"], "country": m["countryOfOrigin"], "adult": m["isAdult"],
        "genres": m["genres"] or [], "avg": m["averageScore"], "popularity": m["popularity"],
        "favourites": m["favourites"], "start": _date(m["startDate"]), "end": _date(m["endDate"]),
        "studios": [e["node"]["name"] for e in studios], "trailer": trailer, "trailer_embed": embed,
        "tags": [{"name": t["name"], "rank": t["rank"], "spoiler": t["isMediaSpoiler"]} for t in m["tags"] or []],
        "rankings": [{"rank": r["rank"], "type": r["type"], "context": r["context"], "all_time": r["allTime"]}
                     for r in m["rankings"] or []],
        "links": [{"site": l["site"], "url": l["url"], "type": l["type"]} for l in m["externalLinks"] or []],
        "characters": chars, "staff": staff,
        "relations": [dict(stub(e["node"], low), relation=e["relationType"]) for e in m["relations"]["edges"]],
        "recs": [dict(stub(r["mediaRecommendation"], low), rating=r["rating"],
                      avg=r["mediaRecommendation"].get("averageScore"))
                 for r in (m.get("recommendations") or {}).get("nodes", []) if r.get("mediaRecommendation")],
        "eps": [{"title": s["title"], "url": s["url"]} for s in m.get("streamingEpisodes") or []],
        "stats": {"scores": [{"score": x["score"], "amount": x["amount"]} for x in st.get("scoreDistribution") or []],
                  "status": [{"status": x["status"], "amount": x["amount"]} for x in st.get("statusDistribution") or []]},
        "next": {"episode": nxt["episode"], "at": nxt["airingAt"]} if nxt else None,
        "mal": m.get("idMal"), "color": ci.get("color"), "cover": cover,
        "url": m["siteUrl"], "banner": banner, "extra": extra,
    }


def img_ok(name):
    try:
        return (IMG / name).stat().st_size > 0
    except OSError:
        return False


def dl(url, name):
    path = IMG / name
    if img_ok(name):
        return
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ma-liste/3.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if not data:
                raise ValueError("image vide")
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
            return
        except Exception:
            time.sleep(1 + attempt)  # sinon réessayé au prochain rafraîchissement


class Downloader:
    """Téléchargement d'images en parallèle, sans doublons."""

    def __init__(self):
        self.pool = ThreadPoolExecutor(8)
        self.futs, self.names = [], set()

    def add(self, pairs):
        for url, name in pairs:
            if url and name not in self.names:
                self.names.add(name)
                self.futs.append(self.pool.submit(dl, url, name))

    def wait(self):
        for n, f in enumerate(self.futs, 1):
            f.result()
            if n % 25 == 0:
                state["message"] = f"Images {n}/{len(self.futs)}…"
        self.pool.shutdown()


def image_refs(d):
    r = {d.get("banner"), d.get("cover")}
    for c in d.get("characters", []):
        r.add(c.get("img"))
        r.update(v.get("img") for v in c.get("va", []))
    r.update(s.get("img") for s in d.get("staff", []))
    r.update(f"cover_{x['id']}.jpg" for x in d.get("relations", []) + d.get("recs", []))
    r.discard(None)
    return r


def items_ids(items):
    return [i["id"] for i in items]


def cleanup(items, keep):
    """Supprime fiches et images qui ne servent plus."""
    used = {i["img"] for i in items}
    used |= profile_images(load_json(PROFILE_FILE, {}))
    for f in DETAILS.glob("*.json"):
        if not f.stem.isdigit() or int(f.stem) not in keep:
            f.unlink()
            continue
        used |= image_refs(load_json(f, {}))
    if CHARDIR.is_dir():
        keep_c = wanted_chars(set(keep) | set(items_ids(items)) | trend_ids())
        for f in CHARDIR.glob("*.json"):
            if not f.stem.isdigit() or int(f.stem) not in keep_c:
                f.unlink()
                continue
            used |= char_refs(load_json(f, {}))
    for f in IMG.iterdir():
        if f.is_file() and f.name not in used:
            f.unlink()


def build_index():
    """Index léger de toutes les œuvres connues + liens entre elles (pour afficher les franchises)."""
    idx, stubs = {}, {}
    for f in DETAILS.glob("*.json"):
        d = load_json(f, None)
        if not d or "id" not in d:
            continue
        idx[d["id"]] = {"id": d["id"], "type": d["type"], "format": d["format"], "title": _title(d["title"]),
                        "year": (d.get("start") or {}).get("y"), "status": d["status"],
                        "count": d["episodes"] if d["type"] == "ANIME" else d["chapters"],
                        "rels": [[r["id"], r["relation"]] for r in d.get("relations", [])]}
        for r in d.get("relations", []) + d.get("recs", []):
            stubs.setdefault(r["id"], r)
    for rid, r in stubs.items():
        if rid not in idx:
            idx[rid] = {k: r.get(k) for k in ("id", "type", "format", "title", "year", "status", "count")}
            idx[rid]["rels"] = []
    save_json(INDEX_FILE, idx)


def fresh(path):
    try:
        return time.time() - path.stat().st_mtime < EXTRA_TTL
    except OSError:
        return False


def own_images(d):
    """Images propres à une fiche (bannière, jaquette, personnages, doubleurs, staff)."""
    r = {d.get("banner"), d.get("cover")}
    for c in d.get("characters", []):
        r.add(c.get("img"))
        r.update(v.get("img") for v in c.get("va", []))
    r.update(x.get("img") for x in d.get("staff", []))
    r.discard(None)
    return r


def details_gaps(ids):
    """Fiches absentes / illisibles / incomplètes, ou dont des images manquent sur le disque."""
    need = []
    for i in ids:
        d = load_json(DETAILS / f"{i}.json", None)
        if (not d or "id" not in d or "characters" not in d or "staff" not in d
                or any(not img_ok(n) for n in own_images(d))):
            need.append(i)
    return need


def missing_details(ids):
    """Titres dont la fiche n'est pas encore sur le disque (simple vérification des fichiers, instantanée)."""
    if REFETCH_DETAILS:
        return list(ids)
    need = []
    for i in ids:
        d = load_json(DETAILS / f"{i}.json", None)
        if not d or d.get("extra"):
            need.append(i)
    return need


def save_data(user, items, done):
    """Écrit data.json en gardant les modifications faites localement pendant le téléchargement."""
    with data_lock:
        old = {i["id"]: i for i in load_json(DATA_FILE, {}).get("items", [])}
        for it in items:
            o = old.get(it["id"])
            if o and o.get("updated", 0) > it.get("updated", 0):
                it.update({k: o[k] for k in ("status", "progress", "score", "updated") if k in o})
        save_json(DATA_FILE, {"user": user, "version": DATA_VERSION, "updated": int(time.time()),
                              "airing_updated": int(time.time()), "details_done": done, "items": items})


def _refresh(user):
    try:
        items = []
        for mtype, label in (("ANIME", "animés"), ("MANGA", "mangas")):
            state["message"] = f"Téléchargement de la liste des {label}…"
            items += fetch_list(user, mtype)
        IMG.mkdir(parents=True, exist_ok=True)
        DETAILS.mkdir(parents=True, exist_ok=True)

        dlr = Downloader()
        for it in items:
            it["img"] = f"cover_{it['id']}.jpg"
            dlr.add([(it.pop("cover_url", None), it["img"])])
        # sauvegarde précoce : la liste reste utilisable même si on interrompt la suite
        save_data(user, items, False)

        low, fails, got = {}, 0, set()

        def run(ids, label, extra):
            nonlocal fails
            bad = streak = 0
            for k in range(0, len(ids), DETAIL_BATCH):
                state["message"] = f"{label} {min(k + DETAIL_BATCH, len(ids))}/{len(ids)}…"
                hi = []
                try:
                    for m in fetch_details(ids[k:k + DETAIL_BATCH]):
                        save_json(DETAILS / f"{m['id']}.json", slim(m, hi, low, extra))
                        got.add(m["id"])
                    streak = 0
                except Exception:
                    bad += 1   # ce lot est sauté, on continue avec les suivants
                    streak += 1
                    if streak >= 6:   # réseau vraiment coupé : on arrête, ce sera repris plus tard
                        break
                dlr.add(hi)
                time.sleep(0.7)
            fails += bad

        list_ids = [i["id"] for i in items]
        need0 = sorted(set(missing_details(list_ids)) | set(details_gaps(list_ids)))  # absentes ou incomplètes seulement
        run(need0, "Fiches détaillées", False)

        # œuvres liées (suites, films, mangas, light novels…) : toutes les versions
        attempted, frontier = set(list_ids), set(list_ids)
        for depth in range(RELATED_DEPTH):
            new = set()
            for i in frontier:
                d = load_json(DETAILS / f"{i}.json", {})
                new.update(r["id"] for r in d.get("relations", []) if r["relation"] in FRANCHISE_RELS)
            new -= attempted
            if not new:
                break
            attempted |= new
            gaps = set(details_gaps(sorted(new)))
            need = [i for i in sorted(new) if i in gaps or not fresh(DETAILS / f"{i}.json")]
            run(need, f"Autres versions (niveau {depth + 1}) ", True)
            frontier = new

        if TREND_COUNT > 0 and trending_due():
            try:
                _trend_fetch(dlr, low)
            except Exception:
                pass  # facultatif : réessayé au prochain passage
        if seasons_due():
            try:
                _season_fetch(dlr, low)
            except Exception:
                pass  # facultatif : réessayé au prochain passage
        attempted |= trend_ids()

        if COMPLETE_ALL:  # dernier passage : tout ce qui est présent doit avoir sa fiche complète
            todo = [i for i in details_gaps(sorted(attempted - got))]
            mine = set(list_ids)
            for flag in (False, True):
                grp = []
                for i in todo:
                    d = load_json(DETAILS / f"{i}.json", None)
                    ex = bool(d.get("extra")) if d and "extra" in d else i not in mine
                    if ex == flag:
                        grp.append(i)
                if grp:
                    run(grp, "Réparation des fiches", flag)

        state["message"] = "Profil…"
        try:
            refresh_profile(user, dlr)
        except Exception:
            pass  # le profil est facultatif : il sera réessayé plus tard
        try:
            fav_fetch(user)
        except Exception:
            pass  # favoris : resynchronisés plus tard

        if CHAR_INFO:
            try:
                download_characters(wanted_chars(attempted if COMPLETE_ALL else set(list_ids) | trend_ids()), dlr)
            except Exception:
                pass  # facultatif : réessayé au prochain rafraîchissement ou à l'ouverture d'un personnage

        dlr.add([(url, name) for name, url in low.items()])  # jaquettes moyennes si pas de version HD
        dlr.wait()
        build_index()
        cleanup(items, attempted)
        complete = fails == 0 and not any(not (DETAILS / f"{i}.json").is_file() for i in attempted)
        save_data(user, items, complete)
        state["message"] = "Liste mise à jour ✔" if complete else "Mise à jour partielle (certaines fiches manquent)"
    except RuntimeError as e:
        state["error"] = str(e)
    except Exception as e:
        state["error"] = f"Connexion impossible ({e}). Les données hors ligne sont conservées."
    finally:
        state["running"] = False


def start_refresh(user):
    with lock:
        if state["running"]:
            return False
        state.update(running=True, message="Connexion…", error="")
    threading.Thread(target=_refresh, args=(user,), daemon=True).start()
    return True


def auto_loop():
    """Toutes les heures : rafraîchit si la liste a plus de 7 jours (ou si version/utilisateur change),
    et met à jour les horaires de sortie toutes les 3 h."""
    while True:
        d = load_json(DATA_FILE, {})
        age = time.time() - d.get("updated", 0)
        if (d.get("user") != USER or d.get("version") != DATA_VERSION or age > REFRESH_SECONDS
                or (not d.get("details_done") and age > 6 * 3600)):
            start_refresh(USER)
        elif not state["running"] and time.time() - d.get("airing_updated", d.get("updated", 0)) > 3 * 3600:
            try:
                update_airing()
            except Exception:
                pass
        if not state["running"] and time.time() - load_json(PROFILE_FILE, {}).get("fetched", 0) > PROFILE_TTL:
            try:
                refresh_profile(USER)
            except Exception:
                pass
        if not state["running"] and trending_due() and time.time() - trend_tried["t"] > 3000:
            trend_tried["t"] = time.time()
            start_trending()   # nouvelle semaine => nouvelles tendances
        if not state["running"] and seasons_due() and time.time() - season_tried["t"] > 3000:
            season_tried["t"] = time.time()
            start_seasons()    # changement de saison => télécharge la nouvelle saison (+ mise à jour hebdomadaire)
        time.sleep(3600)


# ---------------------------------------------------------------- Horaires de sortie (léger)
AIRING_QUERY = """
query ($ids: [Int], $per: Int) {
  Page(perPage: $per) { media(id_in: $ids) { id status episodes nextAiringEpisode { episode airingAt } } }
}
"""


def update_airing():
    """Met à jour prochain épisode / statut de sortie des animés en cours (1 requête pour 50 titres)."""
    d = load_json(DATA_FILE, {})
    ids = [i["id"] for i in d.get("items", [])
           if i["type"] == "ANIME" and i["media_status"] in ("RELEASING", "NOT_YET_RELEASED")
           and i["status"] in ("CURRENT", "REPEATING", "PLANNING", "PAUSED")]
    found = {}
    for k in range(0, len(ids), 50):
        for m in anilist(AIRING_QUERY, {"ids": ids[k:k + 50], "per": 50})["Page"]["media"]:
            found[m["id"]] = m
        time.sleep(0.7)
    with data_lock:
        d = load_json(DATA_FILE, {})
        for i in d.get("items", []):
            m = found.get(i["id"])
            if m:
                nxt = m.get("nextAiringEpisode")
                i.update(media_status=m["status"], total=m["episodes"] or i.get("total"),
                         next_ep=nxt["episode"] if nxt else None, next_at=nxt["airingAt"] if nxt else None)
        d["airing_updated"] = int(time.time())
        save_json(DATA_FILE, d)


# ---------------------------------------------------------------- Programme complet des sorties (onglet Calendrier)
SCHED_FILE = BASE / "schedule.json"
SCHED_TTL = 3 * 3600        # une semaine du programme est re-téléchargée au bout de 3 h
sched_lock = threading.Lock()
sched_pool = ThreadPoolExecutor(4)
SCHEDULE_QUERY = """
query ($from: Int, $to: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    airingSchedules(airingAt_greater: $from, airingAt_lesser: $to, sort: TIME) {
      airingAt episode
      media {
        id format episodes isAdult countryOfOrigin genres averageScore popularity siteUrl
        title { romaji english }
        coverImage { large }
        studios(isMain: true) { nodes { name } }
        externalLinks { site type }
      }
    }
  }
}
"""


def fetch_schedule(a, b):
    """Tous les épisodes d'animés diffusés entre les timestamps a (inclus) et b (exclu)."""
    out, page = [], 1
    while True:
        pg = anilist(SCHEDULE_QUERY, {"from": a - 1, "to": b, "page": page})["Page"]
        for s in pg["airingSchedules"]:
            m = s.get("media")
            if not m or m.get("isAdult"):
                continue
            t = m["title"]
            studios = (m.get("studios") or {}).get("nodes") or []
            plats = sorted({l["site"] for l in (m.get("externalLinks") or [])
                            if l.get("type") == "STREAMING" and l.get("site")})
            mid = m["id"]
            have = (IMG / f"cover_{mid}.jpg").exists()
            out.append({"id": mid, "ep": s["episode"], "at": s["airingAt"],
                        "title": t.get("english") or t.get("romaji") or "?",
                        "total": m.get("episodes"), "fmt": m.get("format"),
                        "genres": (m.get("genres") or [])[:3], "score": m.get("averageScore"),
                        "pop": m.get("popularity") or 0,
                        "studio": studios[0]["name"] if studios else "",
                        "plat": plats, "cover": (m.get("coverImage") or {}).get("large"),
                        "url": m.get("siteUrl"), "cc": m.get("countryOfOrigin"),
                        "img": f"cover_{mid}.jpg" if have else f"sch_{mid}.jpg"})
        if not pg["pageInfo"]["hasNextPage"] or page >= 25:
            return out
        page += 1
        time.sleep(0.7)


def get_schedule(a, b, force=False):
    """Programme d'une semaine : cache disque (schedule.json), consultable hors ligne une fois chargé."""
    now = time.time()
    with sched_lock:  # une seule série de requêtes à la fois (limite de débit AniList)
        cache = load_json(SCHED_FILE, {})
        e = cache.get(str(a))
        if e and not force and (now - e["at"] < SCHED_TTL or e["at"] > e["to"] + 3600):
            return {"items": e["items"], "at": e["at"]}
        try:
            items = fetch_schedule(a, b)
        except Exception:
            if e:  # hors ligne : on garde la dernière version connue
                return {"items": e["items"], "at": e["at"], "stale": True}
            raise
        cache[str(a)] = {"at": int(now), "to": b, "items": items}
        for k in [k for k, v in cache.items() if v["to"] < now - 60 * 86400]:
            del cache[k]
        save_json(SCHED_FILE, cache)
    for it in items:  # jaquettes téléchargées en arrière-plan pour le mode hors ligne
        if it["img"].startswith("sch_") and it["cover"]:
            sched_pool.submit(dl, it["cover"], it["img"])
    return {"items": items, "at": int(now)}


# ---------------------------------------------------------------- Tendances (onglet Accueil, renouvelées chaque semaine)
TREND_FILE = BASE / "trending.json"
TREND_VERSION = 1
TREND_COUNT = 12            # animés par rangée de l'Accueil (0 = désactiver les tendances)
TREND_TTL = 7 * 24 * 3600   # une fiche « tendance » est re-téléchargée au bout de 7 jours
SEASONS = ["WINTER", "SPRING", "SUMMER", "FALL"]
SEASON_FR = {"WINTER": "Hiver", "SPRING": "Printemps", "SUMMER": "Été", "FALL": "Automne"}
TREND_QUERY = """
query ($sort: [MediaSort], $season: MediaSeason, $year: Int, $page: Int, $per: Int, $pop: Int) {
  Page(page: $page, perPage: $per) {
    media(type: ANIME, isAdult: false, format_in: [TV, TV_SHORT, MOVIE, ONA],
          sort: $sort, season: $season, seasonYear: $year, popularity_greater: $pop) { id }
  }
}
"""
trend_tried = {"t": 0}


def week_key(now=None):
    y, w, _ = datetime.date.fromtimestamp(now or time.time()).isocalendar()
    return f"{y}-W{w:02d}"


def season_of(now, shift=0):
    t = time.localtime(now)
    n = (t.tm_mon - 1) // 3 + shift
    return SEASONS[n % 4], t.tm_year + n // 4


def trend_plan(now):
    """Les rangées de l'Accueil. 'Les mieux notés' change de page chaque semaine pour varier."""
    wk = datetime.date.fromtimestamp(now).isocalendar()[1]
    cs, cy = season_of(now)
    ns, ny = season_of(now, 1)
    return [
        ("trending", "Tendances de la semaine", "les plus suivis en ce moment", {"sort": ["TRENDING_DESC"]}),
        ("season", f"Populaires · {SEASON_FR[cs]} {cy}", "la saison en cours",
         {"sort": ["POPULARITY_DESC"], "season": cs, "year": cy}),
        ("next", f"Bientôt · {SEASON_FR[ns]} {ny}", "la saison prochaine",
         {"sort": ["POPULARITY_DESC"], "season": ns, "year": ny}),
        ("top", "Les mieux notés", "une sélection différente chaque semaine",
         {"sort": ["SCORE_DESC"], "pop": 60000, "page": wk % 4 + 1}),
    ]


def trend_now_ids():
    """Animés affichés cette semaine sur l'Accueil."""
    if TREND_COUNT <= 0:
        return set()
    return {i for s in load_json(TREND_FILE, {}).get("sections", []) for i in s.get("ids", [])}


def trend_ids():
    """Tous les animés « tendance » à conserver : ceux de cette semaine + toutes les semaines passées.
    Ils ne sont JAMAIS supprimés : ils restent dans le Catalogue avec leur fiche complète."""
    d = load_json(TREND_FILE, {})
    return set(d.get("archive", [])) | trend_now_ids() | extra_ids() | season_ids()   # + titres du bouton du Catalogue + saisons


def trending_due():
    if TREND_COUNT <= 0:
        return False
    d = load_json(TREND_FILE, {})
    if d.get("v") != TREND_VERSION or not d.get("sections") or d.get("week") != week_key():
        return True
    return not d.get("ok", True) and time.time() - d.get("updated", 0) > 6 * 3600


def younger(path, ttl):
    try:
        return time.time() - path.stat().st_mtime < ttl
    except OSError:
        return False


def fetch_trend_ids(var, exclude):
    v = {"sort": var["sort"], "season": var.get("season"), "year": var.get("year"), "pop": var.get("pop"),
         "page": var.get("page", 1), "per": min(50, TREND_COUNT + 12)}
    media = anilist(TREND_QUERY, {k: x for k, x in v.items() if x is not None})["Page"]["media"]
    return [m["id"] for m in media if m["id"] not in exclude][:TREND_COUNT]


def _trend_fetch(dlr, low, force=False):
    """Choisit les animés de la semaine, télécharge leurs fiches complètes (+ images) et écrit trending.json."""
    now = time.time()
    plan = trend_plan(now)
    oldsec = {s["key"]: s for s in load_json(TREND_FILE, {}).get("sections", [])}
    sections, seen, errors = [], set(), 0
    for key, title, sub, var in plan:
        state["message"] = f"Tendances : {title}…"
        try:
            ids = fetch_trend_ids(var, seen)
        except Exception:
            errors += 1
            if key in oldsec:  # hors ligne / erreur : on garde la rangée précédente
                sections.append(oldsec[key])
                seen.update(oldsec[key]["ids"])
            continue
        if ids:
            sections.append({"key": key, "title": title, "sub": sub, "ids": ids})
            seen.update(ids)
        time.sleep(0.7)
    if errors == len(plan) or not sections:
        raise RuntimeError("Tendances indisponibles (connexion ?).")

    ids = [i for s in sections for i in s["ids"]]
    need = []
    for i in ids:
        f = DETAILS / f"{i}.json"
        d = load_json(f, None)
        if not d or "id" not in d or (d.get("extra") and (force or not younger(f, TREND_TTL))):
            need.append(i)
    bad = 0
    for k in range(0, len(need), DETAIL_BATCH):
        state["message"] = f"Tendances : fiches {min(k + DETAIL_BATCH, len(need))}/{len(need)}…"
        hi = []
        try:
            for m in fetch_details(need[k:k + DETAIL_BATCH]):
                save_json(DETAILS / f"{m['id']}.json", slim(m, hi, low, True))
        except Exception:
            bad += 1
            if bad >= 3:
                break
        dlr.add(hi)
        time.sleep(0.7)
    old = load_json(TREND_FILE, {})
    archive = list(old.get("archive", []))
    for i in [x for s in old.get("sections", []) for x in s.get("ids", [])] + ids:
        if i not in archive:
            archive.append(i)   # les tendances passées rejoignent définitivement le catalogue
    save_json(TREND_FILE, {"v": TREND_VERSION, "week": week_key(now), "updated": int(now),
                           "ok": bad == 0 and errors == 0, "sections": sections, "archive": archive})
    return ids


def keep_ids(list_ids):
    """Fiches à conserver : ma liste + ses franchises (déjà sur le disque) + les tendances."""
    keep, frontier = set(list_ids), set(list_ids)
    for _ in range(RELATED_DEPTH):
        new = set()
        for i in frontier:
            d = load_json(DETAILS / f"{i}.json", {})
            new.update(r["id"] for r in d.get("relations", []) if r["relation"] in FRANCHISE_RELS)
        new -= keep
        if not new:
            break
        keep |= new
        frontier = new
    return keep | trend_ids()


def refresh_trending(force=False):
    IMG.mkdir(parents=True, exist_ok=True)
    DETAILS.mkdir(parents=True, exist_ok=True)
    dlr, low = Downloader(), {}
    ids = _trend_fetch(dlr, low, force)
    if CHAR_INFO:
        try:
            download_characters(wanted_chars(set(ids)), dlr)
        except Exception:
            pass
    dlr.add([(url, name) for name, url in low.items()])
    dlr.wait()
    build_index()
    items = load_json(DATA_FILE, {}).get("items", [])
    if items:  # nettoyage des fiches inutiles (les tendances passées sont conservées)
        cleanup(items, keep_ids(items_ids(items)))


def _trend_job(force):
    try:
        refresh_trending(force)
        state["message"] = "Tendances mises à jour ✔" if load_json(TREND_FILE, {}).get("ok") else \
            "Tendances mises à jour (certaines fiches manquent)"
    except RuntimeError as e:
        state["error"] = str(e)
    except Exception as e:
        state["error"] = f"Connexion impossible ({e}). Les données hors ligne sont conservées."
    finally:
        state["running"] = False


def start_trending(force=False):
    with lock:
        if state["running"]:
            return False
        state.update(running=True, message="Tendances de la semaine…", error="")
    threading.Thread(target=_trend_job, args=(force,), daemon=True).start()
    return True


# ---------------------------------------------------------------- Téléchargement à la demande (bouton du Catalogue)
EXTRA_FILE = BASE / "catalog_extra.json"   # titres ajoutés au catalogue via le bouton : jamais supprimés
EXTRA_MAX = 200                            # maximum de titres par téléchargement
extra_lock = threading.Lock()
EXTRA_QUERY = """
query ($type: MediaType, $formats: [MediaFormat], $sort: [MediaSort], $pop: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(type: $type, isAdult: false, format_in: $formats, sort: $sort, popularity_greater: $pop) { id }
  }
}
"""
EXTRA_FORMATS = {"ANIME": ["TV", "TV_SHORT", "MOVIE", "ONA", "OVA"], "MANGA": ["MANGA", "ONE_SHOT"]}
EXTRA_SORTS = {"POP": (["POPULARITY_DESC"], 0), "SCORE": (["SCORE_DESC"], 15000)}   # (tri, popularité minimale)


def extra_ids():
    return set(load_json(EXTRA_FILE, {}).get("ids", []))


def extra_add(ids):
    with extra_lock:
        cur = list(load_json(EXTRA_FILE, {}).get("ids", []))
        cur += [i for i in ids if i not in cur]
        save_json(EXTRA_FILE, {"ids": cur, "updated": int(time.time())})


def pick_new(n, mtype, sort):
    """Les n premiers titres du classement qui ne sont pas encore dans le catalogue."""
    order, pop = EXTRA_SORTS[sort]
    known = {i["id"] for i in load_json(DATA_FILE, {}).get("items", [])} | trend_ids()
    known |= {int(f.stem) for f in DETAILS.glob("*.json") if f.stem.isdigit()}
    out, page, bad = [], 1, 0
    while len(out) < n and page <= 60:
        state["message"] = f"Catalogue : recherche de titres… {len(out)}/{n}"
        v = {"type": mtype, "formats": EXTRA_FORMATS[mtype], "sort": order, "page": page}
        if pop:
            v["pop"] = pop
        try:
            res = anilist(EXTRA_QUERY, v)["Page"]
        except Exception:
            bad += 1
            if bad >= 3:
                break
            time.sleep(2)
            continue
        for m in res["media"]:
            if m["id"] not in known and m["id"] not in out:
                out.append(m["id"])
                if len(out) >= n:
                    break
        if not res["pageInfo"]["hasNextPage"]:
            break
        page += 1
        time.sleep(0.7)
    if not out and bad >= 3:
        raise RuntimeError("Connexion impossible : rien n'a été téléchargé.")
    return out


def _extra_job(n, mtype, sort):
    word = "animé" if mtype == "ANIME" else "manga"
    try:
        IMG.mkdir(parents=True, exist_ok=True)
        DETAILS.mkdir(parents=True, exist_ok=True)
        ids = pick_new(n, mtype, sort)
        if not ids:
            state["message"] = "Aucun nouveau titre à télécharger : tout est déjà dans ton catalogue."
            return
        dlr, low, got, bad = Downloader(), {}, [], 0

        def grab(batch, label):
            """Télécharge les fiches de ce lot ; renvoie True si le réseau semble coupé."""
            nonlocal bad
            for k in range(0, len(batch), DETAIL_BATCH):
                state["message"] = f"{label} {min(k + DETAIL_BATCH, len(batch))}/{len(batch)}…"
                hi, saved = [], []
                try:
                    for m in fetch_details(batch[k:k + DETAIL_BATCH]):
                        save_json(DETAILS / f"{m['id']}.json", slim(m, hi, low, True))
                        saved.append(m["id"])
                except Exception:
                    bad += 1
                if saved:
                    extra_add(saved)   # enregistré tout de suite : le nettoyage ne les supprimera jamais
                    got.extend(saved)
                dlr.add(hi)
                if bad >= 3:
                    return True
                time.sleep(0.7)
            return False

        down = grab(ids, "Catalogue : fiches")
        # œuvres liées : saisons, films, OVA, suites, mangas, light novels… (comme pour ma liste)
        attempted, frontier = set(ids), set(ids)
        for depth in range(RELATED_DEPTH):
            if down:
                break
            new = set()
            for i in frontier:
                d = load_json(DETAILS / f"{i}.json", {})
                new.update(r["id"] for r in d.get("relations", []) if r["relation"] in FRANCHISE_RELS)
            new -= attempted
            if not new:
                break
            attempted |= new
            have = [i for i in new if i not in set(details_gaps([i]))]   # déjà complètes sur le disque
            if have:
                extra_add(have)    # déjà là : on les protège simplement du nettoyage
            need = sorted(set(new) - set(have))
            if need:
                down = grab(need, f"Catalogue : autres versions (niveau {depth + 1})")
            frontier = new
        if CHAR_INFO and got:
            try:
                download_characters(wanted_chars(set(got)), dlr)
            except Exception:
                pass  # facultatif : repris au prochain rafraîchissement ou à l'ouverture d'un personnage
        state["message"] = "Catalogue : images…"
        dlr.add([(url, name) for name, url in low.items()])
        dlr.wait()
        build_index()
        items = load_json(DATA_FILE, {}).get("items", [])
        if items:
            cleanup(items, keep_ids(items_ids(items)))
        if not got:
            state["error"] = "Connexion impossible : rien n'a été téléchargé."
        else:
            rel = len(got) - len(ids)
            state["message"] = f"{len(ids)} {word}{'s' if len(ids) > 1 else ''} ajouté{'s' if len(ids) > 1 else ''} au catalogue ✔"
            if rel > 0:
                state["message"] += f" (+ {rel} autre(s) version(s) liée(s))"
            elif len(got) < len(ids):
                state["message"] += f" ({len(ids) - len(got)} manquant(s) : réessaie)"
    except RuntimeError as e:
        state["error"] = str(e)
    except Exception as e:
        state["error"] = f"Connexion impossible ({e}). Les données hors ligne sont conservées."
    finally:
        state["running"] = False


def start_extra(n, mtype, sort):
    with lock:
        if state["running"]:
            return False
        state.update(running=True, message="Catalogue : recherche de titres…", error="")
    threading.Thread(target=_extra_job, args=(n, mtype, sort), daemon=True).start()
    return True


# ---------------------------------------------------------------- Saisons (onglet Saisons : précédente / en cours / suivante)
SEASON_FILE = BASE / "seasons.json"
SEASON_VERSION = 1
SEASON_TTL = 7 * 24 * 3600   # fiches de la saison en cours / suivante re-téléchargées chaque semaine (notes, épisodes…)
SEASON_QUERY = """
query ($season: MediaSeason, $year: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(type: ANIME, isAdult: false, season: $season, seasonYear: $year, sort: [POPULARITY_DESC, ID]) { id }
  }
}
"""
season_tried = {"t": 0}


def season_key(season, year):
    return f"{year}-{season}"


def season_plan(now=None):
    """Les 3 saisons à garder à jour : précédente, en cours, suivante."""
    now = now or time.time()
    out = []
    for shift, role in ((-1, "prev"), (0, "cur"), (1, "next")):
        se, y = season_of(now, shift)
        out.append({"key": season_key(se, y), "season": se, "year": y, "role": role,
                    "label": f"{SEASON_FR[se]} {y}"})
    return out


def season_ids():
    """Tous les animés de toutes les saisons téléchargées (jamais supprimés)."""
    return {i for v in load_json(SEASON_FILE, {}).get("seasons", {}).values() for i in v.get("ids", [])}


def seasons_due():
    d = load_json(SEASON_FILE, {})
    if d.get("v") != SEASON_VERSION:
        return True
    have = d.get("seasons", {})
    if any(p["key"] not in have for p in season_plan()):   # changement de saison => nouvelle saison à télécharger
        return True
    if d.get("week") != week_key():                         # mise à jour hebdomadaire
        return True
    return not d.get("ok", True) and time.time() - d.get("updated", 0) > 6 * 3600


def fetch_season_ids(p):
    """TOUS les animés d'une saison, page après page (aucune limite)."""
    out, page, bad = [], 1, 0
    while page <= 40:
        state["message"] = f"Saisons : {p['label']} — liste des titres ({len(out)})…"
        try:
            res = anilist(SEASON_QUERY, {"season": p["season"], "year": p["year"], "page": page})["Page"]
        except Exception:
            bad += 1
            if bad >= 3:
                raise
            time.sleep(2)
            continue
        out += [m["id"] for m in res["media"] if m["id"] not in out]
        if not res["pageInfo"]["hasNextPage"]:
            break
        page += 1
        time.sleep(0.7)
    return out


def _season_fetch(dlr, low, force=False):
    """Liste TOUS les titres des 3 saisons, télécharge les fiches manquantes, écrit seasons.json."""
    IMG.mkdir(parents=True, exist_ok=True)
    DETAILS.mkdir(parents=True, exist_ok=True)
    now = time.time()
    plan = season_plan(now)
    old = load_json(SEASON_FILE, {})
    seasons = dict(old.get("seasons", {})) if old.get("v") == SEASON_VERSION else {}
    errors = 0
    for p in plan:
        try:
            ids = fetch_season_ids(p)
        except Exception:
            errors += 1   # hors ligne : on garde ce qu'on a
            continue
        if ids:
            seasons[p["key"]] = {"season": p["season"], "year": p["year"], "label": p["label"], "ids": ids}
        time.sleep(0.7)
    if errors == len(plan) and not seasons:
        raise RuntimeError("Saisons indisponibles (connexion ?).")
    save_json(SEASON_FILE, {"v": SEASON_VERSION, "week": old.get("week") if old.get("v") == SEASON_VERSION else None,
                            "updated": int(now), "ok": False, "seasons": seasons})   # listes enregistrées tout de suite

    keys = {p["key"]: p for p in plan}
    wanted = []
    for k, v in seasons.items():
        live = k in keys and keys[k]["role"] in ("cur", "next")   # seules ces 2 saisons évoluent encore
        for i in v["ids"]:
            f = DETAILS / f"{i}.json"
            d = load_json(f, None)
            if (not d or "id" not in d or "characters" not in d or "staff" not in d
                    or (live and (force or not younger(f, SEASON_TTL)))):
                wanted.append(i)
    wanted = list(dict.fromkeys(wanted))
    bad = streak = 0
    for k in range(0, len(wanted), DETAIL_BATCH):
        state["message"] = f"Saisons : fiches {min(k + DETAIL_BATCH, len(wanted))}/{len(wanted)}…"
        hi = []
        try:
            for m in fetch_details(wanted[k:k + DETAIL_BATCH]):
                save_json(DETAILS / f"{m['id']}.json", slim(m, hi, low, True))
            streak = 0
        except Exception:
            bad += 1
            streak += 1
            if streak >= 4:   # réseau vraiment coupé : on s'arrête, ce sera repris plus tard
                dlr.add(hi)
                break
        dlr.add(hi)
        time.sleep(0.7)
    save_json(SEASON_FILE, {"v": SEASON_VERSION, "week": week_key(now), "updated": int(now),
                            "ok": bad == 0 and errors == 0, "seasons": seasons})
    return {i for v in seasons.values() for i in v["ids"]}


def refresh_seasons(force=False):
    dlr, low = Downloader(), {}
    allids = _season_fetch(dlr, low, force)
    if CHAR_INFO:
        try:
            download_characters(wanted_chars(allids), dlr)
        except Exception:
            pass   # facultatif : repris au prochain rafraîchissement ou à l'ouverture d'un personnage
    state["message"] = "Saisons : images…"
    dlr.add([(url, name) for name, url in low.items()])
    dlr.wait()
    build_index()
    items = load_json(DATA_FILE, {}).get("items", [])
    if items:
        cleanup(items, keep_ids(items_ids(items)))


def _season_job(force):
    try:
        refresh_seasons(force)
        state["message"] = "Saisons mises à jour ✔" if load_json(SEASON_FILE, {}).get("ok") else \
            "Saisons mises à jour (certaines fiches manquent : réessaie plus tard)"
    except RuntimeError as e:
        state["error"] = str(e)
    except Exception as e:
        state["error"] = f"Connexion impossible ({e}). Les données hors ligne sont conservées."
    finally:
        state["running"] = False


def start_seasons(force=False):
    with lock:
        if state["running"]:
            return False
        state.update(running=True, message="Saisons…", error="")
    threading.Thread(target=_season_job, args=(force,), daemon=True).start()
    return True


def seasons_payload(sel=None):
    d = load_json(SEASON_FILE, {})
    have = d.get("seasons", {})
    roles = {p["key"]: p["role"] for p in season_plan()}
    order = {"next": 0, "cur": 1, "prev": 2}
    metas = [{"key": k, "label": v.get("label", k), "role": roles.get(k, "old"), "count": len(v.get("ids", [])),
              "ord": v.get("year", 0) * 10 + SEASONS.index(v.get("season", "WINTER"))} for k, v in have.items()]
    metas.sort(key=lambda m: -m["ord"])
    cur = next((m["key"] for m in metas if m["role"] == "cur"), metas[0]["key"] if metas else None)
    sel = sel if sel in have else cur
    items = []
    if sel:
        for rank, i in enumerate(have[sel].get("ids", [])):
            c = trend_card(i)
            if c:
                c["rk"] = rank
                items.append(c)
    return {"updated": d.get("updated", 0), "ok": d.get("ok", True), "running": state["running"],
            "seasons": metas, "sel": sel, "items": items,
            "total": len(have[sel]["ids"]) if sel else 0}


_tcard = {}


def trend_card(i):
    f = DETAILS / f"{i}.json"
    try:
        mt = f.stat().st_mtime
    except OSError:
        return None
    c = _tcard.get(i)
    if not c or c[0] != mt:
        d = load_json(f, None)
        if not d or "id" not in d:
            return None
        desc = re.sub(r"~!.*?!~", " ", d.get("description") or "", flags=re.S)
        desc = " ".join(html.unescape(re.sub(r"<[^>]*>", " ", desc)).split())
        if len(desc) > 260:
            desc = desc[:260].rsplit(" ", 1)[0] + "…"
        nxt = d.get("next")
        c = (mt, {"id": d["id"], "type": d["type"], "title": _title(d["title"]),
                  "romaji": (d["title"] or {}).get("romaji"), "format": d.get("format"),
                  "year": (d.get("start") or {}).get("y"), "genres": (d.get("genres") or [])[:3], "gall": d.get("genres") or [],
                  "sd": ((d.get("start") or {}).get("y") or 0) * 10000 + ((d.get("start") or {}).get("m") or 0) * 100
                        + ((d.get("start") or {}).get("d") or 0),
                  "avg": d.get("avg"), "ms": d.get("status"), "count": d.get("episodes"), "desc": desc,
                  "bfile": d.get("banner"), "next_at": nxt["at"] if nxt else None,
                  "next_ep": nxt["episode"] if nxt else None})
        _tcard[i] = c
    card = dict(c[1])
    card["banner"] = bool(card.pop("bfile") and (IMG / f"banner_{i}.jpg").is_file())
    return card


def trending_payload():
    d = load_json(TREND_FILE, {})
    secs = []
    for s in d.get("sections", []):
        items = [c for c in (trend_card(i) for i in s.get("ids", [])) if c]
        if items:
            secs.append({"key": s["key"], "title": s["title"], "sub": s.get("sub", ""), "items": items})
    return {"week": d.get("week"), "updated": d.get("updated", 0), "sections": secs, "running": state["running"]}


# ---------------------------------------------------------------- Compte AniList + modification de la liste
VALID_STATUS = {"CURRENT", "PLANNING", "COMPLETED", "DROPPED", "PAUSED", "REPEATING"}
SAVE_FIELDS = "id status progress score(format: POINT_10) updatedAt"
ENTRY_QUERY = "query ($id: Int) { Media(id: $id) { mediaListEntry { id } } }"
DELETE_MUT = "mutation ($id: Int) { DeleteMediaListEntry(id: $id) { deleted } }"
META_QUERY = """
query ($id: Int) { Media(id: $id) {
  id type format status episodes chapters genres averageScore siteUrl
  title { romaji english } startDate { year } coverImage { extraLarge }
  nextAiringEpisode { episode airingAt }
} }
"""


def auth_info():
    return {"connected": bool(CONF.get("token")), "name": CONF.get("viewer")}


def auth_set(req):
    tok = (req.get("token") or "").strip()
    if not tok:
        CONF.pop("token", None)
        CONF.pop("viewer", None)
        save_conf()
        return 200, auth_info()
    try:
        name = anilist("query { Viewer { name } }", {}, tok)["Viewer"]["name"]
    except ApiError:
        return 400, {"error": "Token refusé. Vérifie qu'il est complet."}
    except Exception:
        return 502, {"error": "Connexion impossible."}
    if name.lower() != USER.lower():
        return 400, {"error": f"Ce token est celui du compte « {name} », mais la liste affichée est celle de « {USER} »."}
    CONF.update(token=tok, viewer=name)
    save_conf()
    return 200, auth_info()


def _item_from_media(m, cover=True):
    typ = m["type"]
    nxt = m.get("nextAiringEpisode")
    return {"id": m["id"], "type": typ, "title": _title(m["title"]), "romaji": m["title"].get("romaji"),
            "img": f"cover_{m['id']}.jpg", "status": "PLANNING", "progress": 0, "score": 0,
            "total": m["episodes"] if typ == "ANIME" else m["chapters"],
            "media_status": m["status"], "format": m["format"], "genres": m.get("genres") or [],
            "avg": m.get("averageScore"), "year": (m.get("startDate") or {}).get("year"),
            "url": m.get("siteUrl"), "updated": int(time.time()),
            "next_ep": nxt["episode"] if nxt else None, "next_at": nxt["airingAt"] if nxt else None}


def meta_for(mid):
    """Infos d'une œuvre pas encore dans la liste (fiche locale, sinon AniList)."""
    m = anilist(META_QUERY, {"id": mid})["Media"]
    url = (m.get("coverImage") or {}).get("extraLarge")
    if url:
        dl(url, f"cover_{mid}.jpg")
    return _item_from_media(m)


def apply_entry(req):
    token = CONF.get("token")
    if not token:
        return 401, {"error": "not_connected"}
    try:
        mid = int(req.get("id"))
    except (TypeError, ValueError):
        return 400, {"error": "Identifiant invalide."}
    cur = next((i for i in load_json(DATA_FILE, {}).get("items", []) if i["id"] == mid), None)
    try:
        if req.get("remove"):
            ent = anilist(ENTRY_QUERY, {"id": mid}, token)["Media"]["mediaListEntry"]
            if ent:
                anilist(DELETE_MUT, {"id": ent["id"]}, token)
            with data_lock:
                d = load_json(DATA_FILE, {})
                d["items"] = [i for i in d.get("items", []) if i["id"] != mid]
                save_json(DATA_FILE, d)
            return 200, {"ok": True, "removed": mid}

        meta = cur or meta_for(mid)
        total = meta.get("total")
        status = req.get("status")
        if status is not None and status not in VALID_STATUS:
            return 400, {"error": "Statut invalide."}
        progress = req.get("progress")
        base = cur["status"] if cur else "PLANNING"
        if progress is None:
            progress = cur["progress"] if cur else 0
            status = status or base
            if status == "COMPLETED" and total:
                progress = total
        else:
            progress = max(0, int(progress))
            if total:
                progress = min(progress, total)
            if not status:
                status = base
                if total and progress >= total:
                    status = "COMPLETED"
                elif status == "PLANNING" and progress > 0:
                    status = "CURRENT"
                elif status == "COMPLETED" and total and progress < total:
                    status = "CURRENT"
        v = {"id": mid, "status": status, "progress": progress}
        decl = args = ""
        if req.get("score") is not None:
            v["score"] = max(0, min(100, int(round(float(req["score"]) * 10))))
            decl, args = ", $score: Int", ", scoreRaw: $score"
        q = (f"mutation ($id: Int, $status: MediaListStatus, $progress: Int{decl}) "
             f"{{ SaveMediaListEntry(mediaId: $id, status: $status, progress: $progress{args}) {{ {SAVE_FIELDS} }} }}")
        res = anilist(q, v, token)["SaveMediaListEntry"]
        with data_lock:
            d = load_json(DATA_FILE, {})
            items = d.setdefault("items", [])
            it = next((i for i in items if i["id"] == mid), None)
            if it is None:
                it = dict(meta)
                items.append(it)
            it.update(status=res["status"], progress=res["progress"], score=res["score"] or 0,
                      updated=res["updatedAt"] or int(time.time()))
            save_json(DATA_FILE, d)
        return 200, {"ok": True, "item": it}
    except ApiError as e:
        if e.code == 401:
            return 401, {"error": "Token refusé : reconnecte ton compte (bouton 🔑)."}
        return 502, {"error": f"Modification refusée (HTTP {e.code})."}
    except RuntimeError as e:
        return 429, {"error": str(e)}
    except Exception:
        return 502, {"error": "Pas de connexion : modification non enregistrée."}


# ---------------------------------------------------------------- Favoris AniList (cœur ♥ : fiches œuvres + personnages)
FAV_FILE = BASE / "favourites.json"
FAV_TTL = 6 * 3600          # resynchronisation des favoris depuis AniList toutes les 6 h (et à chaque « Rafraîchir »)
FAV_QUERY = """
query ($name: String, $page: Int) {
  User(name: $name) { favourites {
    anime(page: $page, perPage: 50) { pageInfo { hasNextPage } nodes { id } }
    manga(page: $page, perPage: 50) { pageInfo { hasNextPage } nodes { id } }
    characters(page: $page, perPage: 50) { pageInfo { hasNextPage } nodes { id } }
  } }
}
"""
FAV_MEDIA_QUERY = """
query ($id: Int) { Media(id: $id) {
  id type format isFavourite title { romaji english } startDate { year } coverImage { large }
} }
"""
FAV_CHAR_QUERY = """
query ($id: Int) { Character(id: $id) { id isFavourite name { full } image { large } } }
"""
FAV_TOGGLE = """
mutation ($a: Int, $m: Int, $c: Int) {
  ToggleFavourite(animeId: $a, mangaId: $m, characterId: $c) { anime { pageInfo { total } } }
}
"""
fav_lock = threading.Lock()
fav_busy = {"on": False}


FAV_VERSION = 2   # v1 (sans personnages) => resynchronisation automatique


def _fav_read():
    d = load_json(FAV_FILE, {})
    if (d.get("user") or "").lower() != USER.lower():
        return {"v": FAV_VERSION, "ids": [], "chars": [], "fetched": 0, "user": USER}
    old = d.get("v") != FAV_VERSION   # ancien fichier : les favoris personnages n'y sont pas => on force le re-téléchargement
    return {"v": FAV_VERSION, "ids": d.get("ids", []), "chars": d.get("chars", []),
            "fetched": 0 if old else d.get("fetched", 0), "user": USER}


def fav_fetch(user):
    """Télécharge TOUS les favoris (animés, mangas, personnages) du compte (pagination) et les enregistre."""
    ids, chars, page = set(), set(), 1
    while page <= 40:
        f = anilist(FAV_QUERY, {"name": user, "page": page})["User"]["favourites"]
        more = False
        for k, dest in (("anime", ids), ("manga", ids), ("characters", chars)):
            blk = f.get(k) or {}
            dest.update(n["id"] for n in (blk.get("nodes") or []) if n)
            more = more or bool((blk.get("pageInfo") or {}).get("hasNextPage"))
        if not more:
            break
        page += 1
        time.sleep(0.5)
    with fav_lock:
        save_json(FAV_FILE, {"v": FAV_VERSION, "ids": sorted(ids), "chars": sorted(chars), "fetched": int(time.time()), "user": user})
    return ids


def fav_payload():
    d = _fav_read()
    stale = time.time() - d["fetched"] > FAV_TTL
    if stale and not fav_busy["on"]:
        fav_busy["on"] = True

        def job():
            try:
                fav_fetch(USER)
            except Exception:
                pass  # hors ligne : on garde les favoris enregistrés
            finally:
                fav_busy["on"] = False
        threading.Thread(target=job, daemon=True).start()
    return {"ids": d["ids"], "chars": d["chars"], "syncing": bool(stale or fav_busy["on"])}


def _profile_fav_update(key, node, want):
    """Met à jour les favoris du profil local (onglet Profil > Favoris). key : anime / manga / characters."""
    if not profile_lock.acquire(timeout=5):
        return  # un rafraîchissement du profil est en cours : il reprendra les favoris depuis AniList
    try:
        p = load_json(PROFILE_FILE, None)
        if not p:
            return
        fav = p.setdefault("favourites", {})
        lst = [n for n in (fav.get(key) or []) if n.get("id") != node["id"]]
        if want:
            lst.insert(0, node)
        fav[key] = lst
        save_json(PROFILE_FILE, p)
    finally:
        profile_lock.release()


def fav_set(req):
    """Ajoute / retire un favori (œuvre ou personnage) sur AniList.
    Idempotent : on lit l'état réel côté AniList avant de basculer."""
    token = CONF.get("token")
    if not token:
        return 401, {"error": "not_connected"}
    try:
        mid = int(req.get("id"))
    except (TypeError, ValueError):
        return 400, {"error": "Identifiant invalide."}
    is_char = req.get("kind") == "character"
    want = bool(req.get("value"))
    try:
        if is_char:
            c = anilist(FAV_CHAR_QUERY, {"id": mid}, token)["Character"]
            cur, var, key = bool(c.get("isFavourite")), {"c": mid}, "characters"
            url = (c.get("image") or {}).get("large")
            node = {"id": mid, "name": c["name"]["full"], "img": f"char_{mid}.jpg" if url else None}
            ids_key = "chars"
        else:
            m = anilist(FAV_MEDIA_QUERY, {"id": mid}, token)["Media"]
            cur, key = bool(m.get("isFavourite")), "anime" if m["type"] == "ANIME" else "manga"
            var = {"a": mid} if m["type"] == "ANIME" else {"m": mid}
            url = (m.get("coverImage") or {}).get("large")
            node = {"id": mid, "type": m["type"], "format": m.get("format"), "title": _title(m["title"]),
                    "year": (m.get("startDate") or {}).get("year")}
            ids_key = "ids"
        if cur != want:
            anilist(FAV_TOGGLE, var, token)
        with fav_lock:
            d = _fav_read()
            ids = set(d[ids_key])
            ids.add(mid) if want else ids.discard(mid)
            d[ids_key] = sorted(ids)
            save_json(FAV_FILE, d)
        if want and url:
            dl(url, f"char_{mid}.jpg" if is_char else f"cover_{mid}.jpg")
        _profile_fav_update(key, node, want)
        return 200, {"ok": True, "id": mid, "kind": "character" if is_char else "media",
                     "favourite": want, "key": key, "node": node}
    except ApiError as e:
        if e.code == 401:
            return 401, {"error": "Token refusé : reconnecte ton compte (bouton 🔑)."}
        return 502, {"error": f"Modification des favoris refusée (HTTP {e.code})."}
    except RuntimeError as e:
        return 429, {"error": str(e)}
    except Exception:
        return 502, {"error": "Pas de connexion : favori non enregistré."}


# ---------------------------------------------------------------- Recommandations
_rec = {"m": None, "r": {}}


def recommend(mtype):
    """Œuvres recommandées par AniList pour tes titres les mieux notés, absentes de ta liste."""
    try:
        key = DATA_FILE.stat().st_mtime
    except OSError:
        return []
    if _rec["m"] != key:
        _rec.update(m=key, r={})
    if mtype in _rec["r"]:
        return _rec["r"][mtype]
    items = load_json(DATA_FILE, {}).get("items", [])
    mine = {i["id"] for i in items}
    acc = {}
    for i in items:
        if i["type"] != mtype:
            continue
        sc = i.get("score") or 0
        if not sc and i["status"] == "COMPLETED" and (i.get("avg") or 0) >= 75:
            sc = 7  # pas noté mais terminé et bien classé
        if sc < 7:
            continue
        det = load_json(DETAILS / f"{i['id']}.json", None)
        if not det:
            continue
        for r in det.get("recs", []):
            if r["id"] in mine or r.get("type") != mtype:
                continue
            w = (sc - 5) * (1 + math.log1p(max(r.get("rating") or 0, 0)))
            a = acc.setdefault(r["id"], {"w": 0, "r": r, "b": []})
            a["w"] += w
            a["b"].append((sc, i["title"]))
    out = []
    for a in sorted(acc.values(), key=lambda a: -a["w"])[:40]:
        r = dict(a["r"])
        r["because"] = [t for _, t in sorted(a["b"], reverse=True)[:2]]
        out.append(r)
    _rec["r"][mtype] = out
    return out


# ---------------------------------------------------------------- Profil AniList
PROFILE_QUERY = """
query ($name: String) {
  User(name: $name) {
    id name siteUrl bannerImage about(asHtml: true)
    avatar { large }
    options { profileColor }
    favourites {
      anime(perPage: 50) { nodes { id type format title { romaji english } coverImage { large } startDate { year } } }
      manga(perPage: 50) { nodes { id type format title { romaji english } coverImage { large } startDate { year } } }
      characters(perPage: 50) { nodes { id name { full } image { large } } }
      staff(perPage: 50) { nodes { id name { full } image { large } } }
      studios(perPage: 50) { nodes { id name siteUrl } }
    }
  }
}
"""

PROFILE_STATS = """
query ($name: String) {
  User(name: $name) {
    createdAt
    statistics {
      anime { count meanScore standardDeviation minutesWatched episodesWatched }
      manga { count meanScore standardDeviation chaptersRead volumesRead }
    }
  }
}
"""

FOLLOW_QUERY = """
query ($id: Int) {
  a: Page(perPage: 1) { pageInfo { total } followers(userId: $id) { id } }
  b: Page(perPage: 1) { pageInfo { total } following(userId: $id) { id } }
}
"""

ACTIVITY_QUERY = """
query ($id: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    activities(userId: $id, type: MEDIA_LIST, sort: ID_DESC) {
      ... on ListActivity { status progress createdAt media { id type title { romaji english } } }
    }
  }
}
"""

profile_lock = threading.Lock()


def _try(query, variables):
    """Requête facultative : un échec ne doit jamais bloquer le reste du profil."""
    try:
        return anilist(query, variables)
    except Exception:
        return None


def _hname(url, prefix):
    return f"{prefix}_{hashlib.md5(url.encode()).hexdigest()[:10]}.jpg" if url else None


def fetch_activity(uid):
    out = []
    for page in range(1, ACTIVITY_PAGES + 1):
        pg = anilist(ACTIVITY_QUERY, {"id": uid, "page": page})["Page"]
        for a in pg["activities"]:
            m = (a or {}).get("media")
            if not m:
                continue
            out.append({"t": a["createdAt"], "id": m["id"], "type": m["type"], "title": _title(m.get("title")),
                        "st": a.get("status"), "pr": a.get("progress")})
        if not pg["pageInfo"]["hasNextPage"]:
            break
        time.sleep(0.7)
    return out


def profile_images(p):
    """Noms des images utilisées par le profil (pour le nettoyage)."""
    r = {p.get("avatar"), p.get("banner")}
    f = p.get("favourites") or {}
    r.update(f"cover_{n['id']}.jpg" for k in ("anime", "manga") for n in f.get(k, []))
    r.update(n.get("img") for k in ("characters", "staff") for n in f.get(k, []))
    r.discard(None)
    return r


def refresh_profile(user, dlr=None):
    """Télécharge le profil : bio, avatar, bannière, favoris, stats AniList, abonnés, activité récente.
    Léger (≈ 15 requêtes) : ne retélécharge ni la liste ni les fiches."""
    if not profile_lock.acquire(blocking=False):
        return False
    try:
        u = anilist(PROFILE_QUERY, {"name": user})["User"]
        imgs = []

        def media(n):
            c = (n.get("coverImage") or {}).get("large")
            if c:
                imgs.append((c, f"cover_{n['id']}.jpg"))
            return {"id": n["id"], "type": n.get("type"), "format": n.get("format"),
                    "title": _title(n.get("title")), "year": (n.get("startDate") or {}).get("year")}

        def person(n, prefix):
            url = (n.get("image") or {}).get("large")
            img = f"{prefix}_{n['id']}.jpg" if url else None
            if url:
                imgs.append((url, img))
            return {"id": n["id"], "name": n["name"]["full"], "img": img}

        fav = u.get("favourites") or {}

        def nodes(k):
            return [n for n in ((fav.get(k) or {}).get("nodes") or []) if n]

        avatar = (u.get("avatar") or {}).get("large")
        banner = u.get("bannerImage")
        if avatar:
            imgs.append((avatar, _hname(avatar, "pf_avatar")))
        if banner:
            imgs.append((banner, _hname(banner, "pf_banner")))
        old = load_json(PROFILE_FILE, {})
        p = {
            "id": u["id"], "name": u["name"], "url": u.get("siteUrl"), "about": u.get("about") or "",
            "color": (u.get("options") or {}).get("profileColor"),
            "avatar": _hname(avatar, "pf_avatar"), "banner": _hname(banner, "pf_banner"),
            "favourites": {
                "anime": [media(n) for n in nodes("anime")],
                "manga": [media(n) for n in nodes("manga")],
                "characters": [person(n, "char") for n in nodes("characters")],
                "staff": [person(n, "staff") for n in nodes("staff")],
                "studios": [{"id": n["id"], "name": n["name"], "url": n.get("siteUrl")} for n in nodes("studios")],
            },
            "created": old.get("created"), "official": old.get("official"),
            "followers": old.get("followers"), "following": old.get("following"),
            "activity": old.get("activity", []),
        }
        time.sleep(0.7)
        st = _try(PROFILE_STATS, {"name": user})
        if st and st.get("User"):
            p["created"] = st["User"].get("createdAt")
            p["official"] = st["User"].get("statistics")
        time.sleep(0.7)
        fl = _try(FOLLOW_QUERY, {"id": u["id"]})
        if fl:
            p["followers"] = (fl.get("a") or {}).get("pageInfo", {}).get("total")
            p["following"] = (fl.get("b") or {}).get("pageInfo", {}).get("total")
        time.sleep(0.7)
        try:
            p["activity"] = fetch_activity(u["id"])
        except Exception:
            pass  # on garde l'ancien historique
        p["fetched"] = int(time.time())
        save_json(PROFILE_FILE, p)
        if dlr is not None:
            dlr.add(imgs)
        else:
            with ThreadPoolExecutor(8) as pool:
                list(pool.map(lambda x: dl(*x), imgs))
        return True
    finally:
        profile_lock.release()


_px = {}


def profile_extra():
    """Infos tirées des fiches détaillées (durée, studios, tags, staff…) pour les statistiques du profil."""
    out = {}
    for it in load_json(DATA_FILE, {}).get("items", []):
        mid = it["id"]
        f = DETAILS / f"{mid}.json"
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        c = _px.get(mid)
        if not c or c[0] != mt:
            d = load_json(f, {})
            tags = sorted((t for t in d.get("tags", []) if not t.get("spoiler") and (t.get("rank") or 0) >= 40),
                          key=lambda t: -(t.get("rank") or 0))
            c = (mt, {"dur": d.get("duration"), "vol": d.get("volumes"), "src": d.get("source"),
                      "ctry": d.get("country"), "studios": d.get("studios") or [],
                      "tags": [t["name"] for t in tags[:15]],
                      "staff": [s["name"] for s in d.get("staff", [])]})
            _px[mid] = c
        out[mid] = c[1]
    return out


# ---------------------------------------------------------------- Franchise
_idx = {"m": None, "d": {}, "adj": {}}
_cat = {}


def get_index():
    try:
        m = INDEX_FILE.stat().st_mtime
    except OSError:
        return {}, {}
    if _idx["m"] != m:
        d = {int(k): v for k, v in load_json(INDEX_FILE, {}).items()}
        adj = {}
        for k, v in d.items():
            for rid, rel in v.get("rels", []):
                if rel in FRANCHISE_RELS and rid in d:
                    adj.setdefault(k, set()).add(rid)
                    adj.setdefault(rid, set()).add(k)
        _idx.update(m=m, d=d, adj=adj)
    return _idx["d"], _idx["adj"]


def avg_of(mid):
    """Note moyenne d'une œuvre d'après sa fiche locale (mise en cache)."""
    f = DETAILS / f"{mid}.json"
    try:
        mt = f.stat().st_mtime
    except OSError:
        return None
    c = _cat.get(mid)
    if not c or c[0] != mt:
        d = load_json(f, {})
        c = (mt, {"genres": d.get("genres") or [], "avg": d.get("avg"),
                  "romaji": (d.get("title") or {}).get("romaji")})
        _cat[mid] = c
    return c[1]["avg"]


def franchise(mid):
    idx, adj = get_index()
    if mid not in idx:
        return {"nodes": []}
    seen, queue = {mid}, [mid]
    while queue and len(seen) < 150:
        for n in adj.get(queue.pop(0), ()):
            if n not in seen:
                seen.add(n)
                queue.append(n)
    direct = {rid: rel for rid, rel in idx[mid].get("rels", [])}
    nodes = []
    for n in seen:
        v = {k: x for k, x in idx[n].items() if k != "rels"}
        v["avg"] = avg_of(n)
        if n in direct:
            v["rel"] = direct[n]
        nodes.append(v)
    return {"nodes": nodes}


# ---------------------------------------------------------------- Catalogue
def catalogue():
    """Toutes les œuvres connues localement : ma liste + toutes les versions téléchargées (suites, films, mangas…)."""
    idx, _ = get_index()
    mine = {i["id"]: i for i in load_json(DATA_FILE, {}).get("items", [])}
    out = {}
    for mid, i in mine.items():
        out[mid] = {"id": mid, "type": i["type"], "title": i["title"], "romaji": i.get("romaji"),
                    "format": i.get("format"), "year": i.get("year"), "genres": i.get("genres") or [],
                    "avg": i.get("avg"), "ms": i.get("media_status"), "count": i.get("total")}
    for mid, v in idx.items():
        if mid in out:
            continue
        f = DETAILS / f"{mid}.json"
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue  # simple suggestion sans fiche complète : pas dans le catalogue
        c = _cat.get(mid)
        if not c or c[0] != mt:
            d = load_json(f, {})
            c = (mt, {"genres": d.get("genres") or [], "avg": d.get("avg"),
                      "romaji": (d.get("title") or {}).get("romaji")})
            _cat[mid] = c
        out[mid] = {"id": mid, "type": v["type"], "title": v["title"], "romaji": c[1]["romaji"],
                    "format": v.get("format"), "year": v.get("year"), "genres": c[1]["genres"],
                    "avg": c[1]["avg"], "ms": v.get("status"), "count": v.get("count")}
    for mid in trend_now_ids():   # seules les tendances de CETTE semaine sont marquées ;
        if mid in out:            # les semaines passées deviennent des animés normaux du catalogue
            out[mid]["tr"] = 1
    return {"items": list(out.values())}


# ---------------------------------------------------------------- Serveur local
def lan_ips():
    """Adresses de ce PC sur le réseau local (pour afficher l'adresse à taper sur le téléphone)."""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))   # aucun paquet n'est envoyé : sert juste à trouver la bonne carte réseau
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


CGNAT = ipaddress.ip_network("100.64.0.0/10")   # adresses des VPN type Tailscale

LOGIN_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Ma liste</title><style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0b0b0f;color:#fff;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
form{background:#16171c;padding:28px;border-radius:12px;width:min(340px,90vw);text-align:center}
h1{color:#f47521;font-size:22px;letter-spacing:.5px;margin:0 0 8px}
p{color:#9a9aa5;font-size:14px;line-height:1.5;margin:0 0 6px}
input{width:100%;box-sizing:border-box;font-size:26px;letter-spacing:8px;text-align:center;padding:10px;border-radius:8px;border:1px solid #2c2d36;background:#1b1c22;color:#fff;margin:12px 0 4px}
button{width:100%;padding:12px;border:0;border-radius:8px;background:#f47521;color:#111;font-weight:700;font-size:15px;cursor:pointer}
#e{color:#ff6b6b;min-height:22px;font-size:13px}
</style></head><body>
<form id="f"><h1>MA LISTE</h1><p>Entre le code affiché dans la fenêtre du script sur ton PC. Il ne sera demandé qu'une fois sur ce téléphone.</p>
<input id="p" inputmode="numeric" autocomplete="off" autofocus maxlength="12"><div id="e"></div><button>Entrer</button></form>
<script>
document.getElementById("f").onsubmit=async e=>{
  e.preventDefault();
  let r;
  try{r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json","X-Ma-Liste":"1"},body:JSON.stringify({pin:document.getElementById("p").value.trim()})})}
  catch(x){document.getElementById("e").textContent="Serveur injoignable.";return}
  if(r.ok){location.reload();return}
  const j=await r.json().catch(()=>({}));
  document.getElementById("e").textContent=j.error||"Code incorrect.";
};
</script></body></html>"""


def login_html():
    if not ONLINE:
        return LOGIN_PAGE
    return (LOGIN_PAGE
            .replace("Entre le code affiché dans la fenêtre du script sur ton PC. Il ne sera demandé qu'une fois sur ce téléphone.",
                     "Entre ton mot de passe. Il ne sera demandé qu'une fois sur cet appareil.")
            .replace('<input id="p" inputmode="numeric" autocomplete="off" autofocus maxlength="12">',
                     '<input id="p" type="password" autocomplete="current-password" autofocus maxlength="128">')
            .replace("font-size:26px;letter-spacing:8px;", "font-size:20px;letter-spacing:0;"))


def pin_value():
    return ONLINE_PASSWORD if ONLINE else CONF.get("pin")


def sess_value():
    return ONLINE_SESS if ONLINE else CONF.get("sess")


SEC_HEADERS = {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
               "Strict-Transport-Security": "max-age=31536000"}


def mime(b):
    return "image/png" if b[:4] == b"\x89PNG" else "image/webp" if b[:4] == b"RIFF" else "image/jpeg"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, ctype, body, cache=False, headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", "max-age=86400")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        if ONLINE:
            for k, v in SEC_HEADERS.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def client_ip(self):
        """En ligne, le serveur est derrière le proxy de l'hébergeur : on lit l'adresse ajoutée par ce proxy (la dernière)."""
        if ONLINE:
            fwd = self.headers.get("X-Forwarded-For", "")
            if fwd.strip():
                return fwd.split(",")[-1].strip()
        return self.client_address[0]

    def host_ok(self):
        if ONLINE:   # nom de domaine de l'hébergeur : le mot de passe protège l'accès
            return True
        # protège contre les sites web qui tenteraient d'appeler le serveur local (« DNS rebinding »)
        name, _, port = self.headers.get("Host", "").rpartition(":")
        name = name.lower()
        if port != str(PORT):
            return False
        if name in ("127.0.0.1", "localhost"):
            return True
        if not LAN:
            return False
        try:   # mode téléphone : seules les adresses privées (Wi-Fi maison, VPN) sont acceptées, jamais un nom de site
            ip = ipaddress.ip_address(name)
            return ip.is_private or ip in CGNAT
        except ValueError:
            me = socket.gethostname().lower()
            return name in (me, me + ".local")

    def authed(self):
        """Ce PC n'a jamais besoin de code. Un autre appareil doit avoir saisi le code (cookie)."""
        if not LAN or (not ONLINE and self.client_address[0] in LOCAL_ADDRS):
            return True
        try:
            m = http.cookies.SimpleCookie(self.headers.get("Cookie", "")).get(PIN_COOKIE)
        except http.cookies.CookieError:
            return False
        sess = sess_value()
        return bool(m and sess) and secrets.compare_digest(m.value.encode(), sess.encode())

    def login(self, req):
        ip = self.client_ip()
        n, until = LOGIN_FAILS.get(ip, (0, 0))
        if until > time.time():
            return self.send_obj(429, {"error": "Trop d'essais. Réessaie dans quelques minutes."})
        pin = str(req.get("pin") or "").encode()
        if LAN and pin_value() and secrets.compare_digest(pin, pin_value().encode()):
            LOGIN_FAILS.pop(ip, None)
            cookie = f"{PIN_COOKIE}={sess_value()}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000"
            if ONLINE:
                cookie += "; Secure"
            return self.reply(200, "application/json", b"{}", headers={"Set-Cookie": cookie})
        if ONLINE:
            time.sleep(1)   # ralentit les essais de mots de passe
        n += 1
        LOGIN_FAILS[ip] = (0, time.time() + 300) if n >= 5 else (n, 0)   # 5 erreurs => blocage 5 min
        self.send_obj(403, {"error": "Mot de passe incorrect." if ONLINE else "Code incorrect."})

    def send_obj(self, code, obj):
        self.reply(code, "application/json", json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if not self.host_ok():
            return self.reply(403, "text/plain", b"")
        p = self.path.split("?")[0]
        if ONLINE and p in PUBLIC_FILES:   # le navigateur lit ces fichiers sans cookie : ils ne contiennent rien de privé
            ctype, body, extra = PUBLIC_FILES[p]
            return self.reply(200, ctype, body, headers=extra)
        if p == "/healthz":
            return self.reply(200, "text/plain", b"ok")
        if not self.authed():
            if p == "/":
                return self.reply(200, "text/html; charset=utf-8", login_html().encode("utf-8"),
                                  headers={"Cache-Control": "no-store"})
            return self.reply(401, "text/plain", b"")
        if p == "/":
            self.reply(200, "text/html; charset=utf-8", PAGE.encode("utf-8"), headers={"X-Ml-App": "1"})
        elif p == "/api/data":
            self.send_obj(200, load_json(DATA_FILE, {"items": [], "updated": 0}))
        elif p == "/api/status":
            self.send_obj(200, state)
        elif p == "/api/auth":
            self.send_obj(200, auth_info())
        elif p == "/api/favourites":
            self.send_obj(200, fav_payload())
        elif p == "/api/profile":
            self.send_obj(200, {"profile": load_json(PROFILE_FILE, {}), "extra": profile_extra()})
        elif p == "/api/catalogue":
            self.send_obj(200, catalogue())
        elif p == "/api/trending":
            self.send_obj(200, trending_payload())
        elif p == "/api/seasons":
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            self.send_obj(200, seasons_payload((q.get("k") or [None])[0]))
        elif p == "/api/schedule":
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            try:
                a, b = int(q["from"][0]), int(q["to"][0])
                if not 0 < b - a <= 8 * 86400:
                    raise ValueError
            except (KeyError, IndexError, ValueError):
                return self.send_obj(400, {"error": "Paramètres invalides."})
            try:
                self.send_obj(200, get_schedule(a, b, "force" in q))
            except Exception:
                self.send_obj(502, {"error": "Programme indisponible (connexion ?)."})
        elif p.startswith("/api/media/"):
            n = Path(p).name
            f = media_file(int(n)) if n.isdigit() else None
            if f:
                self.reply(200, "application/json", f.read_bytes())
            else:
                self.reply(404, "application/json", b"{}")
        elif p.startswith("/api/character/"):
            n = Path(p).name
            f = character_file(int(n)) if n.isdigit() else None
            if f:
                self.reply(200, "application/json", f.read_bytes())
            else:
                self.reply(404, "application/json", b"{}")
        elif p.startswith("/api/franchise/"):
            n = Path(p).name
            self.send_obj(200, franchise(int(n)) if n.isdigit() else {"nodes": []})
        elif p.startswith("/api/recommend/"):
            t = Path(p).name.upper()
            self.send_obj(200, {"items": recommend(t) if t in ("ANIME", "MANGA") else []})
        elif p.startswith("/img/"):
            f = IMG / Path(p).name
            if f.is_file():
                b = f.read_bytes()
                self.reply(200, mime(b), b, cache=True)
            else:
                self.reply(404, "text/plain", b"")
        else:
            self.reply(404, "text/plain", b"")

    def do_POST(self):
        # en-tête personnalisé obligatoire : un autre site ne peut pas l'envoyer
        if not self.host_ok() or self.headers.get("X-Ma-Liste") != "1":
            return self.reply(403, "text/plain", b"")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            req = {}
        if self.path == "/login":
            return self.login(req)
        if not self.authed():
            return self.reply(401, "text/plain", b"")
        if self.path == "/api/refresh":
            start_refresh(USER)
            self.send_obj(200, {"ok": True})
        elif self.path == "/api/auth":
            self.send_obj(*auth_set(req))
        elif self.path == "/api/entry":
            self.send_obj(*apply_entry(req))
        elif self.path == "/api/favourite":
            self.send_obj(*fav_set(req))
        elif self.path == "/api/profile/refresh":
            if state["running"]:
                return self.send_obj(409, {"error": "Un téléchargement est en cours : le profil sera mis à jour à la fin."})
            try:
                ok = refresh_profile(USER)
                self.send_obj(200 if ok else 409, {"ok": True} if ok else {"error": "Actualisation déjà en cours."})
            except RuntimeError as e:
                self.send_obj(429, {"error": str(e)})
            except ApiError:
                self.send_obj(502, {"error": "Demande de profil refusée (pseudo introuvable ?)."})
            except Exception:
                self.send_obj(502, {"error": "Connexion impossible."})
        elif self.path == "/api/trending/refresh":
            if start_trending(force=True):
                self.send_obj(200, {"ok": True})
            else:
                self.send_obj(409, {"error": "Un téléchargement est déjà en cours."})
        elif self.path == "/api/seasons/refresh":
            if start_seasons(force=True):
                self.send_obj(200, {"ok": True})
            else:
                self.send_obj(409, {"error": "Un téléchargement est déjà en cours."})
        elif self.path == "/api/catalogue/download":
            try:
                n = int(req.get("n"))
            except (TypeError, ValueError):
                n = 0
            mtype, sort = req.get("type"), req.get("sort") or "POP"
            if not 1 <= n <= EXTRA_MAX or mtype not in EXTRA_FORMATS or sort not in EXTRA_SORTS:
                self.send_obj(400, {"error": f"Choisis un nombre entre 1 et {EXTRA_MAX}."})
            elif start_extra(n, mtype, sort):
                self.send_obj(200, {"ok": True})
            else:
                self.send_obj(409, {"error": "Un téléchargement est déjà en cours."})
        elif self.path == "/api/airing":
            try:
                update_airing()
                self.send_obj(200, {"ok": True})
            except Exception:
                self.send_obj(502, {"error": "Connexion impossible pour les horaires."})
        else:
            self.reply(404, "text/plain", b"")


# ---------------------------------------------------------------- Interface
PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0b0f">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Ma liste">
<title>Ma liste</title>
<style>
:root{--bg:#0b0b0f;--card:#1b1c22;--acc:#f47521;--mut:#9a9aa5;--hh:60px}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:#fff;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{position:sticky;top:0;z-index:10;display:flex;flex-wrap:wrap;align-items:center;gap:14px;padding:12px 4vw;background:rgba(11,11,15,.96);border-bottom:1px solid #23232b}
.logo{color:var(--acc);font-weight:800;font-size:22px;letter-spacing:.5px;cursor:pointer}
.tabs button{background:none;border:0;color:var(--mut);font-size:15px;font-weight:600;padding:8px 12px;cursor:pointer;border-bottom:3px solid transparent}
.tabs button.on{color:#fff;border-color:var(--acc)}
.sp{flex:1}
input,select{background:#1b1c22;color:#fff;border:1px solid #2c2d36;border-radius:6px;padding:8px 10px;font-size:14px}
#rf{background:var(--acc);color:#111;border:0;border-radius:6px;padding:9px 14px;font-weight:700;cursor:pointer}
#rf:disabled{opacity:.7;cursor:wait}
.spin::before{content:"";display:inline-block;width:10px;height:10px;margin-right:8px;border:2px solid #111;border-top-color:transparent;border-radius:50%;animation:r .8s linear infinite}
@keyframes r{to{transform:rotate(360deg)}}
#info{font-size:12px;color:var(--mut)}
.pill{background:#3a2a10;color:#ffb35c;border-radius:10px;padding:2px 8px;margin-left:6px}
.row{padding:0 4vw;margin:26px 0}
.row h2{font-size:20px;margin:0 0 8px}.row h2 small{color:var(--mut);font-weight:400;font-size:14px;margin-left:6px}
.wrap{position:relative}
.arr{position:absolute;top:0;bottom:46px;width:44px;border:0;background:#000b;color:#fff;font-size:28px;cursor:pointer;opacity:0;transition:opacity .15s;z-index:2}
.wrap:hover .arr{opacity:1}.arr.l{left:-4vw}.arr.r{right:-4vw}
@media(hover:none){.arr{display:none}}
.strip{display:flex;gap:14px;overflow-x:auto;padding:8px 2px 14px;scroll-snap-type:x proximity;scrollbar-width:none}
.strip::-webkit-scrollbar{display:none}
a.card{flex:0 0 160px;cursor:pointer;scroll-snap-align:start;color:inherit;text-decoration:none;display:block}
.poster{position:relative;aspect-ratio:2/3;background:var(--card);border-radius:6px;overflow:hidden;transition:transform .15s}
.card:hover .poster{transform:scale(1.05);box-shadow:0 6px 20px #000a}
.poster img{width:100%;height:100%;object-fit:cover;display:block}
.badge{position:absolute;top:6px;left:6px;background:var(--acc);color:#111;font-size:11px;font-weight:700;padding:2px 6px;border-radius:3px}
.bar{position:absolute;left:0;right:0;bottom:0;height:4px;background:#0008}.bar i{display:block;height:100%;background:var(--acc)}
.t{margin-top:8px;font-size:14px;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.s{font-size:12px;color:var(--mut);margin-top:2px}
#empty{text-align:center;color:var(--mut);margin:15vh 4vw}

/* ---------- liste style AniList (onglets Animés / Mangas) ---------- */
.lwrap{max-width:1240px;margin:0 auto}
.lsum{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:6px}
.lsum>div{flex:1 1 150px;position:relative;overflow:hidden;background:linear-gradient(135deg,#252630,#16171c);border:1px solid #2a2b34;border-radius:14px;padding:14px 18px}
.lsum>div::after{content:"";position:absolute;right:-24px;top:-24px;width:80px;height:80px;border-radius:50%;background:var(--acc);opacity:.08}
.lsum b{display:block;font-size:26px;line-height:1.1}.lsum span{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
.lsum>div:first-child b{color:var(--acc)}
.lsum>.lsegw{flex:1 1 100%;padding:10px 18px}.lsegw::after{display:none}
.lseg{display:flex;gap:3px;height:8px;border-radius:5px;overflow:hidden}.lseg i{display:block;height:100%;min-width:4px}
.ltb{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0 16px;position:sticky;top:var(--hh);z-index:5;padding:10px 4px;background:rgba(11,11,15,.82);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid #ffffff10}
.lsp{flex:1}
.lpill{display:inline-flex;align-items:center;gap:7px;background:#1b1c22;color:#c9c9d2;border:1px solid #2a2b34;border-radius:20px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;transition:.15s}
.lpill i{width:8px;height:8px;border-radius:50%;background:var(--c,#677b94)}
.lpill b{font-size:11px;background:#0005;border-radius:10px;padding:1px 7px}
.lpill:hover{border-color:var(--c,var(--acc));color:#fff}
.lpill.on{background:var(--c,var(--acc));border-color:var(--c,var(--acc));color:#111}.lpill.on i{background:#111}.lpill.on b{background:#0003}
.ltb select,.lbt{background:#1b1c22;color:#fff;border:1px solid #2f303a;border-radius:8px;padding:7px 10px;font-size:13px}
.lbt{cursor:pointer;min-width:34px}.lbt:hover{border-color:var(--acc)}.lbt.on{background:var(--acc);color:#111;border-color:var(--acc)}
.lh,.lr{display:grid;grid-template-columns:5px 64px minmax(0,1fr) 70px 250px 130px;gap:16px;align-items:center}
.lh{padding:0 14px 8px;color:var(--mut);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.lh span[data-lsort]{cursor:pointer}.lh span.on{color:#fff}
@keyframes lin{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.lr{position:relative;cursor:pointer;padding:10px 14px;background:linear-gradient(90deg,color-mix(in srgb,var(--c) 11%,var(--card)),var(--card) 42%);border:1px solid transparent;border-radius:14px;margin-bottom:8px;animation:lin .4s both;animation-delay:var(--d,0ms);transition:transform .15s,border-color .15s,box-shadow .15s}
.lr:hover{border-color:color-mix(in srgb,var(--c) 55%,transparent);transform:translateX(3px);box-shadow:0 8px 24px #0008}
@media(prefers-reduced-motion:reduce){.lr{animation:none}.lr:hover{transform:none}}
.ld{width:5px;height:84px;border-radius:3px;background:var(--c)}
.lc{width:64px;height:92px;object-fit:cover;border-radius:8px;background:#111;box-shadow:0 4px 12px #000a}
.lt{min-width:0}.lt b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:15px}
.lro{display:block;color:var(--mut);font-size:12px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lch{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.lch em{font-style:normal;font-size:11px;padding:2px 9px;border-radius:10px;background:color-mix(in srgb,var(--c) 18%,#14151a);color:#dcdce4;cursor:pointer}
.lch em:hover{background:var(--c);color:#111}
.ln{text-align:center}.ln small{display:block;font-size:10px;color:var(--mut);margin-top:3px;text-transform:uppercase}
.lsc{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;border-radius:50%;font-weight:800;font-size:15px;background:#2a2b33;color:#8d8d99;border:0;appearance:none;-webkit-appearance:none;text-align:center;text-align-last:center;padding:0;cursor:pointer}
.lsc.s-hi{background:#1f6b3a;color:#9dffb9}.lsc.s-mid{background:#7a6212;color:#ffe27a}.lsc.s-lo{background:#7a2234;color:#ffb0c0}
.lsel{background:transparent;border:0;color:var(--c);font-weight:700;font-size:12px;cursor:pointer;padding:0;max-width:120px}
.lsel option{background:#1b1c22;color:#fff}
.lp{display:flex;flex-direction:column;gap:6px;font-size:12px;color:var(--mut)}
.lp1{display:flex;justify-content:space-between;align-items:center}
.lpb{height:7px;background:#2a2b33;border-radius:4px;overflow:hidden}.lpb i{display:block;height:100%;border-radius:4px;background:linear-gradient(90deg,var(--c),color-mix(in srgb,var(--c) 60%,#fff));transition:width .4s}
.lp2{display:flex;align-items:center;gap:6px;min-height:24px;flex-wrap:wrap}
.lbd{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;background:#3a2a12;color:#ffb866}
.lbd.ok{background:#16341f;color:#8ee6a6}.lbd.nx{background:#14283a;color:#8cc8ff}
.lpl,.lmn{border:0;border-radius:6px;font-weight:800;font-size:12px;padding:4px 10px;cursor:pointer}
.lpl{margin-left:auto;background:var(--acc);color:#111}.lpl:hover{filter:brightness(1.15)}
.lmn{background:#2a2b33;color:#ddd;padding:4px 8px}.lmn:hover{background:#3a3b45}
.lf{font-size:12px;color:var(--mut);line-height:1.6}.lf b{display:block;color:#fff;font-size:13px}
.lf .lav{color:#ffd24d;font-weight:700}
.lmore{display:block;margin:20px auto;background:#1b1c22;color:#fff;border:1px solid #2f303a;border-radius:24px;padding:10px 28px;font-weight:700;cursor:pointer}.lmore:hover{border-color:var(--acc);color:var(--acc)}
.lg{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:20px 16px}.lg a.card{flex:none;animation:lin .4s both;animation-delay:var(--d,0ms)}
.lg .poster{box-shadow:inset 0 -4px 0 var(--c,transparent)}
@media(max-width:900px){.lh,.lr{grid-template-columns:5px 56px minmax(0,1fr) 200px}.lh span:nth-child(4),.lh span:nth-child(6),.ln,.lf{display:none}}
@media(max-width:620px){.lh{display:none}.lr{grid-template-columns:5px 52px minmax(0,1fr);gap:10px}.lp{grid-column:2/-1}.lc{width:52px;height:74px}.ld{height:74px}.lsum b{font-size:20px}.lg{grid-template-columns:repeat(auto-fill,minmax(105px,1fr))}}

/* ---------- page personnage ---------- */
.cpg{max-width:1120px;margin:0 auto 70px;padding:28px 18px 0}
.cname{margin:6px 0 4px;font-size:34px;line-height:1.1}
.chead{display:flex;gap:30px;align-items:flex-start;margin-top:22px}
.cphoto{width:auto;height:auto;max-width:min(100%,420px);max-height:80vh;flex:none;object-fit:contain;border-radius:10px;background:var(--card);box-shadow:0 14px 40px #000c;cursor:zoom-in;display:block}
.cinfo{min-width:0;flex:1}
.cinfo .kpis{margin-top:0}
.cdesc{font-size:15px;line-height:1.7;color:#d8d8de;max-width:860px;margin-top:16px}
.cinfo .kpis+.cdesc{margin-top:18px}
.spo{background:#3b3d49;color:transparent;border-radius:3px;cursor:pointer;padding:0 2px;transition:background .15s}
.spo *{color:transparent}
.spo:hover{background:#4a4d5c}
.cpg.spoon .spo,.spo.on{background:#2a2b33;color:#d8d8de;cursor:default}
.cpg.spoon .spo b,.spo.on b{color:#fff}
.cdesc b{color:#fff}
.cva{display:flex;align-items:center;gap:7px;margin-top:3px;font-size:12px;color:#c4c4cc}
.cva img{width:24px;height:24px;border-radius:50%;object-fit:cover}
.vc .role{display:block;color:var(--acc);font-size:12px;margin-top:2px}
@media(max-width:700px){.chead{flex-direction:column;align-items:center}.cphoto{max-width:100%}.cinfo{width:100%}}

/* ---------- page dédiée ---------- */
.hero{height:360px;background:#1b1c22 center/cover no-repeat}
.pg{max-width:1120px;margin:-190px auto 70px;padding:0 18px;position:relative}
.back{background:#000a;color:#fff;border:1px solid #ffffff2a;border-radius:20px;padding:7px 14px;cursor:pointer;font-size:13px;margin-bottom:16px}
.back:hover{background:var(--acc);color:#111;border-color:var(--acc)}
.head{display:flex;gap:30px;align-items:flex-end}
.cov{width:250px;flex:none;aspect-ratio:2/3;object-fit:cover;border-radius:10px;background:var(--card);box-shadow:0 14px 40px #000c;cursor:zoom-in}
.hi{min-width:0;flex:1}
.hi h1{margin:0 0 4px;font-size:36px;line-height:1.1;text-shadow:0 2px 12px #000}
.alt{color:#c4c4cc;font-size:14px;margin:0 0 10px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.chip{display:inline-block;background:#262731;border-radius:12px;padding:3px 10px;margin:3px 5px 3px 0;font-size:12px}
.chip small{color:var(--mut)}
.chip.hl{background:var(--acc);color:#111;font-weight:700}
.chip.adult{background:#7a1f2b}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.kpis div{background:#16171cdd;border:1px solid #2a2b33;border-radius:8px;padding:8px 14px;min-width:92px}
.kpis b{display:block;font-size:20px}.kpis span{font-size:11px;color:var(--mut)}
.mine{background:#16171cee;border-left:3px solid var(--acc);padding:10px 14px;border-radius:6px;font-size:14px;margin:12px 0;max-width:560px}
.mine.off{border-color:#555;color:var(--mut)}
.pb{height:6px;background:#2a2b33;border-radius:3px;margin:8px 0 6px;overflow:hidden}.pb i{display:block;height:100%;background:var(--acc)}
.btns{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.btn{background:var(--acc);color:#111;font-weight:700;font-size:13px;padding:9px 15px;border-radius:6px;text-decoration:none;border:0;cursor:pointer}
.btn.ghost{background:#262731;color:#fff;font-weight:600}
#trbox{margin-top:18px}
#trbox iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;background:#000}
.snav{position:sticky;top:var(--hh);z-index:5;display:flex;gap:4px;overflow-x:auto;margin:26px -18px 0;padding:8px 18px;background:rgba(11,11,15,.96);border-bottom:1px solid #23232b;scrollbar-width:none}
.snav a{color:var(--mut);text-decoration:none;font-size:14px;font-weight:600;padding:6px 12px;border-radius:16px;white-space:nowrap}
.snav a:hover{background:#262731;color:#fff}
.sec{margin-top:34px;scroll-margin-top:calc(var(--hh) + 56px)}
.sec h2{margin:0 0 14px;font-size:21px;border-left:4px solid var(--acc);padding-left:10px}
.sec h3{margin:20px 0 10px;font-size:15px;color:var(--acc)}
.syn{font-size:15px;line-height:1.7;color:#d8d8de;max-width:860px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:4px 26px}
.grid div{display:flex;flex-direction:column;border-bottom:1px solid #26272f;padding:7px 0;font-size:13.5px}
.grid span{color:var(--mut);font-size:12px}
.spoil{display:none}.show .spoil{display:inline-block}
.tgl{font-size:13px;color:var(--mut);display:block;margin:10px 0;cursor:pointer}
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:16px}
a.vc{display:block;color:inherit;text-decoration:none;font-size:13px}
.vc .p{position:relative;aspect-ratio:2/3;background:var(--card);border-radius:8px;overflow:hidden;transition:transform .15s}
.vc:hover .p{transform:translateY(-4px);box-shadow:0 8px 22px #000b}
.vc .p img{width:100%;height:100%;object-fit:cover;display:block}
.vc.cur .p{outline:3px solid var(--acc)}
.vc .tag{position:absolute;left:6px;bottom:6px;background:#000c;border-radius:4px;padding:2px 6px;font-size:11px}
.vc .tag.cur{top:6px;bottom:auto;background:var(--acc);color:#111;font-weight:700}
.vc b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-top:7px;font-weight:600}
.vc span.m{display:block;color:var(--mut);font-size:12px;margin-top:2px}
.vc em{display:block;font-style:normal;color:var(--acc);font-size:12px;margin-top:2px}
.chars{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:22px 16px}
.ch{font-size:13px;text-align:center}
.ch>img{width:128px;height:128px;aspect-ratio:1/1;object-fit:cover;object-position:center top;border-radius:50%;background:transparent;display:block;margin:0 auto;border:0;outline:0;box-shadow:none;transition:transform .15s}
.ch:hover>img{transform:scale(1.05)}
a.ch,div.ch{cursor:pointer}
.ch b{display:block;margin-top:8px;font-weight:600}.ch>span{color:var(--mut);font-size:12px}
.va{display:flex;align-items:center;justify-content:center;gap:7px;margin-top:6px;color:#c4c4cc;font-size:12px;text-align:left}
.va img{width:28px;height:28px;border-radius:50%;object-fit:cover;background:var(--card);cursor:zoom-in}
.eps a{display:block;color:#d8d8de;text-decoration:none;padding:6px 0;border-bottom:1px solid #26272f;font-size:14px}
.eps a:hover{color:var(--acc)}
details summary{cursor:pointer;color:var(--acc);font-weight:600;margin:6px 0 10px}
.vb{display:flex;align-items:flex-end;gap:8px;height:150px;max-width:520px}
.vb div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;font-size:11px;color:var(--mut)}
.vb i{display:block;width:100%;background:var(--acc);border-radius:3px 3px 0 0;min-height:2px}
.hb{max-width:520px}
.hb div{display:flex;align-items:center;gap:10px;font-size:13px;margin:6px 0}
.hb span{width:90px;color:var(--mut)}.hb u{display:block;height:10px;background:var(--acc);border-radius:3px;text-decoration:none}
.links{display:flex;flex-wrap:wrap;gap:8px}
.note{color:var(--mut);font-size:13px;font-style:italic}
.loading{text-align:center;color:var(--mut);padding:30vh 0}
#lb{position:fixed;inset:0;background:#000e;display:none;z-index:40;align-items:center;justify-content:center;flex-direction:column;cursor:zoom-out;padding:20px}
#lb.on{display:flex}
#lb img{max-width:96vw;max-height:88vh;object-fit:contain;border-radius:6px}
#lb p{color:#ccc;margin:10px 0 0;font-size:14px}
@media(max-width:700px){
  .hero{height:250px}.pg{margin-top:-120px}
  .head{flex-direction:column;align-items:flex-start;gap:16px}.cov{width:160px}.hi h1{font-size:26px}
}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#222;border:1px solid #444;padding:10px 16px;border-radius:8px;display:none;z-index:50;max-width:90vw}

/* accueil : bannière « continuer » */
#hero{display:none;margin:18px 4vw 0}
.hero2{position:relative;height:340px;border-radius:14px;overflow:hidden;background:#16171c}
.hbg{position:absolute;inset:-24px;background:center/cover;filter:blur(26px) brightness(.55)}
.hban{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hshade{position:absolute;inset:0;background:linear-gradient(90deg,#0b0b0f 6%,#0b0b0fcc 38%,transparent 80%),linear-gradient(0deg,#0b0b0f,transparent 45%)}
.hc{position:absolute;left:34px;bottom:32px;max-width:min(560px,62%)}
.hl{color:var(--acc);font-weight:800;font-size:12px;letter-spacing:1.5px}
.hc h2{margin:6px 0;font-size:32px;line-height:1.1;text-shadow:0 2px 12px #000}
.hm{color:#d8d8de;font-size:14px;margin-bottom:10px}
.hc .pb{max-width:360px}
.hbt{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.btn:disabled{opacity:.5;cursor:default}
.hcov{position:absolute;right:34px;bottom:32px;height:78%;aspect-ratio:2/3;object-fit:cover;border-radius:10px;box-shadow:0 10px 30px #000c}
.hdots{position:absolute;right:20px;top:14px;display:flex;gap:7px;align-items:center}
.hdots i{width:8px;height:8px;border-radius:50%;background:#ffffff55;cursor:pointer}.hdots i.on{background:var(--acc)}
.hdots button{background:#0009;color:#fff;border:0;border-radius:50%;width:26px;height:26px;cursor:pointer}
.plus{position:absolute;top:6px;right:6px;display:none;background:var(--acc);color:#111;border:0;border-radius:4px;font-weight:800;font-size:12px;padding:3px 7px;cursor:pointer;z-index:2}
.plus.x{background:#000b;color:#fff}
.card:hover .plus{display:block}
@media(hover:none){.plus{display:block}}
.why{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.acc{background:#262731;color:#fff;border:1px solid #33343e;border-radius:6px;padding:9px 12px;font-weight:600;cursor:pointer;font-size:13px}
.acc.ok{border-color:#2e8b57;color:#7fe0a3}
.btn.ghost.on{background:var(--acc);color:#111}
/* éditeur de ma liste */
.mine.edit{max-width:640px}
.er{display:flex;align-items:center;gap:10px;margin:7px 0;flex-wrap:wrap}
.er label{width:120px;color:var(--mut);font-size:12px}
.stp{display:inline-flex;align-items:center;gap:4px}
.stp input{width:68px;text-align:center}
.sm{background:#262731;color:#fff;border:1px solid #33343e;border-radius:6px;width:32px;height:34px;font-size:16px;cursor:pointer}
.sm2{padding:7px 12px;font-size:12px}
/* connexion du compte */
#cm{position:fixed;inset:0;background:#000c;display:none;z-index:45;align-items:center;justify-content:center;padding:14px}
#cm.on{display:flex}
.cmb{position:relative;background:#16171c;border-radius:12px;max-width:580px;width:100%;padding:26px;max-height:92vh;overflow-y:auto}
.cmb h3{margin:0 0 10px}
.cmb p,.cmb ol{font-size:14px;line-height:1.65;color:#d8d8de}
.cmb ol{padding-left:20px}
.cmb input{width:100%;margin:4px 0 8px}
.cmb code{background:#262731;padding:2px 6px;border-radius:4px;font-size:12px;word-break:break-all}
.cmb a{color:var(--acc)}.cmb a.btn{color:#111}
.x{position:absolute;top:10px;right:10px;width:34px;height:34px;border-radius:50%;border:0;background:#262731;color:#fff;cursor:pointer}
#toast a{color:var(--acc);font-weight:700;margin-left:10px}
@media(max-width:700px){.hero2{height:300px}.hcov{display:none}.hc{left:18px;bottom:20px;max-width:92%}.hc h2{font-size:24px}}
/* profil */
[hidden]{display:none!important}
a.ch{display:block;color:inherit;text-decoration:none}
.pban{height:280px;background:#14151a center/cover no-repeat}
.prof{max-width:1240px;margin:0 auto;padding:0 24px 80px}
.phead{display:flex;gap:22px;align-items:flex-end;flex-wrap:wrap;margin-top:-68px;position:relative}
.pavw{width:128px;height:128px;flex:none;border-radius:8px;overflow:hidden;border:0;box-shadow:none;background:transparent;cursor:zoom-in}
.pavw .pav{width:100%;height:100%;object-fit:cover;object-position:center;display:block}
.pavw .pav.ph{display:flex;align-items:center;justify-content:center;font-size:52px;font-weight:800;color:var(--acc);cursor:default}
.pi{flex:1;min-width:220px;padding-bottom:4px}
.pi h1{margin:0;font-size:30px;font-weight:800;line-height:1.15;text-shadow:0 2px 12px #000}
.pmeta{display:flex;flex-wrap:wrap;gap:2px 18px;margin-top:6px;font-size:13px;color:#b4b4bd}
.pmeta b{color:#fff;font-weight:700}
.pact{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding-bottom:4px}
.prof .btn{display:inline-block;border-radius:4px;text-transform:uppercase;letter-spacing:.6px;font-size:12px;padding:10px 16px}
.prof .btn.ghost{background:none;border:1px solid #3a3b45;padding:9px 15px;color:#fff}
.prof .btn.ghost:hover{border-color:var(--acc);color:var(--acc)}
.prof .btn:disabled{opacity:.55;cursor:default}
.sw{display:flex;gap:6px;align-items:center;margin-left:6px;padding-left:14px;border-left:1px solid #2a2b33}
.sw button{width:16px;height:16px;border-radius:50%;border:2px solid transparent;cursor:pointer;padding:0;transition:transform .15s}
.sw button:hover{transform:scale(1.2)}.sw button.on{border-color:#fff}
.fkbar{display:flex;flex-wrap:wrap;gap:8px;margin-top:26px}
.fkbar button{background:#13141a;border:1px solid #23242c;color:var(--mut);font-weight:700;font-size:13px;padding:8px 16px;border-radius:20px;cursor:pointer;transition:background .2s,color .2s,border-color .2s,transform .15s}
.fkbar button small{margin-left:7px;font-weight:500;opacity:.7}
.fkbar button:hover{color:#fff;border-color:var(--acc);transform:translateY(-1px)}
.fkbar button.on{background:var(--acc);border-color:var(--acc);color:#111}
.fkbody{animation:fkin .3s ease}
@keyframes fkin{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.fkgrid>*{animation:fkpop .35s ease both}
.fkgrid>*:nth-child(2){animation-delay:.03s}.fkgrid>*:nth-child(3){animation-delay:.06s}.fkgrid>*:nth-child(4){animation-delay:.09s}
.fkgrid>*:nth-child(5){animation-delay:.12s}.fkgrid>*:nth-child(6){animation-delay:.15s}.fkgrid>*:nth-child(n+7){animation-delay:.18s}
@keyframes fkpop{from{opacity:0;transform:scale(.94)}to{opacity:1;transform:none}}
.pnav{position:sticky;top:var(--hh);z-index:5;display:flex;gap:2px;overflow-x:auto;margin-top:20px;background:rgba(11,11,15,.96);backdrop-filter:blur(6px);border-bottom:1px solid #23242c;scrollbar-width:none}
.pnav button{background:none;border:0;border-bottom:3px solid transparent;margin-bottom:-1px;color:var(--mut);font-size:12.5px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;padding:15px 20px;cursor:pointer;white-space:nowrap}
.pnav button:hover{color:#fff}
.pnav button.on{color:#fff;border-bottom-color:var(--acc)}
.pbody{animation:pfin .25s ease}
@keyframes pfin{from{opacity:0}to{opacity:1}}
.play{display:grid;grid-template-columns:320px minmax(0,1fr);gap:28px;margin-top:26px;align-items:start}
.pside{display:flex;flex-direction:column;gap:20px}
.pmain{min-width:0}
.pmain>*+*{margin-top:30px}
.prof .pcard,.prof .sec.pcard{background:#13141a;border:1px solid #23242c;border-radius:8px;padding:18px 20px}
.prof .sec.pcard{margin-top:20px}
.pcard h3,.pcard h4{margin:0;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--mut)}
.pcard h4{margin:16px 0 2px;color:var(--acc)}
.pch{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:14px}
.pch .tog{margin:0}
.lnk{display:inline-block;background:none;border:0;padding:0;color:var(--acc);font-weight:700;font-size:13px;cursor:pointer}
.lnk:hover{text-decoration:underline}
.pcard>.lnk{margin-top:14px}
.shd{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px}
.shd h2{margin:0;font-size:20px;font-weight:800}
.shd h2 small,.prof .sec h2 small{color:var(--mut);font-weight:500;font-size:14px;margin-left:8px}
.prof .sec h2{border:0;padding:0;font-size:20px;font-weight:800;margin:0 0 14px}
.prof .sec h2 .btn{margin-left:12px;vertical-align:middle}
.srow{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid #1d1e25;font-size:14px}
.srow:last-of-type{border-bottom:0}
.srow span{color:#b4b4bd}.srow b{font-weight:700}
.about{max-height:150px;overflow:hidden;margin-top:12px;font-size:14px;line-height:1.65;color:#d0d0d8}
.about.fade:not(.open){-webkit-mask-image:linear-gradient(#000 65%,transparent);mask-image:linear-gradient(#000 65%,transparent)}
.about.open{max-height:none}
.about a{color:var(--acc)}
.about h1,.about h2,.about h3{font-size:15px;margin:10px 0 4px;text-transform:none;letter-spacing:0;color:#fff}
.about img{display:none}
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}
.mini div{background:#0f1015;border:1px solid #1f2027;border-radius:6px;padding:10px 12px}
.mini b{display:block;font-size:22px;font-weight:800}
.mini span{font-size:11px;color:var(--mut)}
.prof .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:0 0 6px}
.prof .kpis div{background:#13141a;border:1px solid #23242c;border-radius:8px;padding:14px 16px;min-width:0}
.prof .kpis b{font-size:24px;font-weight:800}
.prof .kpis span{display:block;margin-top:2px;font-size:11px;text-transform:uppercase;letter-spacing:.7px}
.tog{display:inline-flex;gap:2px;background:#0f1015;border:1px solid #2a2b33;border-radius:6px;padding:3px;margin:0 0 18px}
.tog button{background:none;border:0;color:var(--mut);padding:6px 14px;font-weight:700;font-size:13px;border-radius:4px;cursor:pointer}
.tog button:hover{color:#fff}
.tog button.on{background:var(--acc);color:#111}
.pgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}
.pgrid>.sec{margin-top:0!important}
.seg{display:flex;height:12px;border-radius:6px;overflow:hidden;gap:2px;margin:6px 0 12px}
.seg button{border:0;padding:0;cursor:pointer;min-width:6px;transition:filter .15s}
.seg button:hover{filter:brightness(1.3)}
.leg{display:flex;flex-wrap:wrap;gap:4px 16px}
.leg button{background:none;border:0;color:#d8d8de;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:6px;padding:3px 0}
.leg button:hover{color:#fff}
.leg i{width:10px;height:10px;border-radius:2px;display:inline-block}
.leg small{color:var(--mut)}
.pbl button{display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;color:#d8d8de;font-size:13px;padding:6px;border-radius:4px;cursor:pointer;text-align:left}
.pbl button:hover{background:#1b1c22}
.pl{width:110px;flex:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#b4b4bd}
.pt{flex:1;display:block;height:6px;background:#1d1e25;border-radius:3px;overflow:hidden}
.pt u{display:block;height:100%;background:var(--acc);border-radius:3px;text-decoration:none}
.pbl b{width:34px;text-align:right}
.pcol{display:flex;align-items:stretch;gap:6px;height:200px;overflow-x:auto;padding-bottom:2px}
.pc{flex:1 0 30px;min-width:30px;display:flex;flex-direction:column;align-items:center;background:none;border:0;color:var(--mut);font-size:11px;cursor:pointer;padding:0}
div.pc{cursor:default}
.pc b{font-size:11px;color:#d8d8de;height:16px}
.pc .bw{flex:1;width:100%;display:flex;align-items:flex-end}
.pc i{display:block;width:100%;background:var(--acc);border-radius:2px 2px 0 0;transition:filter .15s}
.pc:hover i{filter:brightness(1.3)}
.pc span{height:18px;line-height:18px}
.tbl{display:flex;flex-direction:column}
.tr{display:grid;grid-template-columns:1fr 90px 90px 100px;gap:8px;align-items:center;background:none;border:0;border-bottom:1px solid #1d1e25;color:#d8d8de;padding:10px 6px;font-size:14px;text-align:left;cursor:pointer;width:100%}
.tr:hover{background:#181920}
.tr.hd{cursor:default;color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #2a2b33}
.tr.hd:hover{background:none}
.tr>span:not(.tn){text-align:right}
.tn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.th{background:none;border:0;color:var(--mut);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;cursor:pointer;text-align:right;padding:0}
.th.on{color:var(--acc)}
.heatw{overflow-x:auto;padding:4px 0 8px}
.hmo,.heat{display:flex;gap:3px;width:max-content}
.hmo span{width:11px;font-size:10px;color:var(--mut);white-space:nowrap;height:14px}
.hw{display:flex;flex-direction:column;gap:3px}
.hz{width:11px;height:11px;border-radius:2px;background:#1f2027;display:block;cursor:pointer}
.hz.off{background:none;cursor:default}
.prof .hz.l1{background:color-mix(in srgb,var(--acc) 25%,#1f2027)}
.prof .hz.l2{background:color-mix(in srgb,var(--acc) 45%,#1f2027)}
.prof .hz.l3{background:color-mix(in srgb,var(--acc) 70%,#1f2027)}
.prof .hz.l4{background:var(--acc)}
.hz:not(.off):hover{outline:1px solid #fff}
.hleg{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--mut)}
.hleg .hz{cursor:default}
a.ev2{display:flex;gap:18px;align-items:stretch;padding:14px 18px;background:#13141a;border:1px solid #23242c;border-left:4px solid var(--ec,#677b94);border-radius:10px;margin-bottom:12px;color:inherit;text-decoration:none;transition:background .15s,transform .15s}
a.ev2:hover{background:#1a1b22;transform:translateX(3px)}
.ev2>img{width:84px;height:120px;flex:none;object-fit:cover;border-radius:6px;background:var(--card)}
.ebody{flex:1;min-width:0;display:flex;flex-direction:column;gap:5px}
.etop{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.eact{font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;color:var(--ec)}
.etype{font-size:11px;padding:2px 9px;border-radius:10px;background:#262731;color:#c4c4cc}
.ett{font-size:17px;font-weight:700;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.eprg{font-size:14px;color:#d8d8de}.eprg b{color:#fff}
.ebar{height:6px;background:#23242c;border-radius:3px;overflow:hidden;max-width:360px}
.ebar i{display:block;height:100%;border-radius:3px}
.emeta{font-size:12.5px;color:var(--mut)}
.echips{display:flex;gap:6px;flex-wrap:wrap;margin-top:2px}
.echip{font-size:11.5px;padding:3px 10px;border-radius:12px;border:1px solid #2f303a;color:#d0d0d8}
.etime{flex:none;text-align:right;display:flex;flex-direction:column;gap:3px;min-width:78px}
.etime b{font-size:17px}.etime span{font-size:12px;color:var(--mut)}
@media(max-width:600px){.ev2>img{width:60px;height:88px}.etime{display:none}.ett{font-size:15px}}
.adh{margin:22px 0 8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--mut)}
.dn{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
.dnsvg{position:relative;width:170px;height:170px;flex:none}
.dnsvg svg{transform:rotate(-90deg);width:100%;height:100%}
.dnsvg circle{fill:none;stroke-width:20;cursor:pointer;transition:stroke-width .15s,opacity .15s}
.dnsvg circle.hv{stroke-width:27}.dnsvg.hov circle:not(.hv){opacity:.3}
.dnc{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none}
.dnc b{font-size:28px}.dnc span{font-size:12px;color:var(--mut)}
.dn .leg{flex-direction:column;flex-wrap:nowrap}
.pscroll{display:flex;gap:16px;overflow-x:auto;padding-bottom:8px;scroll-snap-type:x proximity;scrollbar-width:none;-ms-overflow-style:none}
.pscroll::-webkit-scrollbar{display:none}
.pscroll>.vc{flex:0 0 150px;scroll-snap-align:start}
.fq{width:100%;max-width:420px;margin:6px 0 4px}
#dr{position:fixed;inset:0;background:#000c;display:none;z-index:45;align-items:flex-start;justify-content:center;padding:4vh 14px;overflow-y:auto}
#dr.on{display:flex}
.drb{position:relative;background:#16171c;border-radius:10px;max-width:1000px;width:100%;padding:26px}
.drb h3{margin:0 0 12px;font-size:20px;padding-right:40px}
.drb h3 small{color:var(--mut);font-weight:400}
@media(max-width:900px){.play{grid-template-columns:1fr}.pside{order:2}}
@media(max-width:700px){
  .prof{padding:0 14px 70px}.pban{height:170px}
  .pavw{width:96px;height:96px}.phead{margin-top:-52px;gap:14px}.pi h1{font-size:24px}
  .sw{border:0;margin:0;padding:0}.pnav button{padding:13px 14px}
  .tr{grid-template-columns:1fr 56px 70px 78px}.pl{width:90px}.mini b{font-size:18px}
}
.btn.fvb.on{color:#ff4d6d;border-color:#ff4d6d}
.fvi{display:none;position:absolute;top:6px;right:6px;z-index:3;width:26px;height:26px;border-radius:50%;background:#000c;color:#ff4d6d;align-items:center;justify-content:center;pointer-events:none}
.fvi.on{display:flex}
.fvi svg{width:15px;height:15px;fill:currentColor}
.fvi.on~.plus{top:38px}
.ch{position:relative}
.ch>.fvi{top:0;right:calc(50% - 64px)}
.rt{position:absolute;right:6px;bottom:8px;z-index:1;background:#000c;color:#ffd24d;font-size:11px;font-weight:700;padding:2px 6px;border-radius:4px}
/* calendrier (refonte v4.4) */
.cx{max-width:1320px;margin:0 auto;padding:22px 4vw 90px}
.cxhd{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;margin-bottom:16px}
.cxhd h1{margin:0;font-size:30px}
.cxpills{display:flex;gap:8px;flex-wrap:wrap}
.cxpills span{background:#13141a;border:1px solid #23242c;border-radius:20px;padding:5px 13px;font-size:13px;color:var(--mut)}
.cxpills b{color:#fff}.cxpills em{color:var(--acc);font-style:normal;font-weight:700}
/* bandeau prochaine sortie */
.cxh{position:relative;display:flex;gap:26px;align-items:center;overflow:hidden;border-radius:14px;background:#13141a;border:1px solid #23242c;padding:26px;min-height:240px;margin-bottom:8px}
.cxhb{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.4}
.cxhs{position:absolute;inset:0;background:linear-gradient(90deg,#0b0b0fee 8%,#0b0b0f99 55%,#0b0b0f55)}
.cxh>:not(.cxhb):not(.cxhs){position:relative}
.cxhp{flex:none;width:130px;aspect-ratio:2/3;border-radius:8px;overflow:hidden;box-shadow:0 10px 30px #000b;background:var(--card)}
.cxhp img{width:100%;height:100%;object-fit:cover;display:block}
.cxhi{flex:1;min-width:0}
.cxk{font-size:11px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;color:var(--acc)}
.cxhi h2{margin:6px 0 4px;font-size:30px;line-height:1.15;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cxhi p{margin:0 0 6px;color:#d8d8de}
.cxcd{font-size:38px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:1px;margin:2px 0 14px}
.cxhi .btn{display:inline-block;text-decoration:none}
.cxhn{flex:none;width:300px;display:flex;flex-direction:column;gap:6px;background:#0b0b0fb0;border:1px solid #ffffff14;border-radius:10px;padding:12px}
.cxhn a{display:flex;gap:10px;align-items:center;color:inherit;text-decoration:none;padding:4px;border-radius:6px}
.cxhn a:hover{background:#ffffff12}
.cxhn img{width:34px;height:48px;object-fit:cover;border-radius:4px;flex:none;background:var(--card)}
.cxhn b{font-size:13px;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cxhn small{color:var(--mut);font-size:12px;text-transform:capitalize}
/* titres de section */
.cxdh{margin:24px 0 12px;font-size:17px}
.cxdh small{color:var(--mut);font-weight:400;font-size:13px;margin-left:10px;text-transform:none}
.cxdd{text-transform:capitalize}
.cxscroll{overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none}
.cxscroll::-webkit-scrollbar{display:none}
.cxstrip{display:flex;gap:14px;padding:4px 2px 8px}
.cxstrip .cxs{flex:0 0 138px}
/* flèches de défilement */
.cxwrap{position:relative}
.cxar{position:absolute;top:0;bottom:44px;margin:auto 0;z-index:3;width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;padding:0;color:#fff;cursor:pointer;
  background:rgba(14,14,19,.82);border:1px solid #ffffff26;box-shadow:0 4px 16px #000a;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);
  transition:opacity .2s,transform .15s,background .15s,color .15s}
.cxar.l{left:6px}.cxar.r{right:6px}
.cxar:hover{background:var(--acc);border-color:var(--acc);color:#111;transform:scale(1.1)}
.cxar:active{transform:scale(.95)}
.cxar.off{opacity:0;pointer-events:none}
.cxwl .cxar{display:none}
@media(hover:none){.cxar{display:none!important}}
/* barre d'outils */
.cxbar{position:sticky;top:var(--hh);z-index:6;background:rgba(11,11,15,.97);padding:12px 0;border-bottom:1px solid #23232b;margin:22px 0 16px;display:flex;flex-direction:column;gap:10px}
.cxr1,.cxr2{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px}
.cxbar .tog{margin:0}.cxbar .sp{flex:1}
.cxnav{display:flex;align-items:center;gap:6px}
.cxlab{font-size:16px;margin-left:8px;text-transform:capitalize;white-space:nowrap}
.cxr2 input{flex:1 1 220px;max-width:340px}
.cxchip{background:#13141a;border:1px solid #23242c;color:var(--mut);font-weight:700;font-size:13px;padding:7px 14px;border-radius:20px;cursor:pointer}
.cxchip:hover{color:#fff;border-color:var(--acc)}.cxchip.on{background:var(--acc);border-color:var(--acc);color:#111}
.cxstat{font-size:12px;color:var(--mut);margin-left:auto}
/* onglets des jours */
.cxdays{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;margin-bottom:6px}
.cxd{display:flex;flex-direction:column;align-items:center;gap:1px;background:#13141a;border:1px solid #23242c;border-radius:10px;padding:10px 4px 12px;color:var(--mut);cursor:pointer;transition:background .15s,border-color .15s}
.cxd:hover{border-color:#3a3b45;color:#fff}
.cxd small{font-size:12px;text-transform:uppercase;letter-spacing:.8px;font-weight:700}
.cxd b{font-size:24px;color:#fff;line-height:1.2}
.cxd i{font-style:normal;font-size:11px;font-weight:700;background:#262731;color:#c4c4cc;border-radius:10px;padding:1px 9px;margin-top:3px}
.cxd i.hot{background:#4a2a12;color:#ffb35c}
.cxd.today small{color:var(--acc)}
.cxd.on{background:var(--acc);border-color:var(--acc);color:#111}
.cxd.on small,.cxd.on b{color:#111}.cxd.on i{background:#0003;color:#111}
/* frise horaire (vue Jour) */
.cxtl{display:flex;flex-direction:column;gap:2px}
.cxslot{display:grid;grid-template-columns:78px minmax(0,1fr);gap:14px}
.cxslot.past{opacity:.62}
.cxsl{padding-top:6px;text-align:right}
.cxsl b{font-size:18px;font-variant-numeric:tabular-nums}.cxsl small{display:block;font-size:11px;color:var(--mut)}
.cxsg{position:relative;display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;padding:0 0 16px 18px;border-left:2px solid #23242c}
.cxsg::before{content:"";position:absolute;left:-7px;top:12px;width:12px;height:12px;border-radius:50%;background:var(--bg);border:2px solid var(--acc)}
.cxnow{display:flex;align-items:center;gap:10px;color:var(--acc);font-weight:800;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:4px 0 12px}
.cxnow::after{content:"";flex:1;height:2px;background:linear-gradient(90deg,var(--acc),transparent)}
/* carte large */
.cxr{display:flex;gap:14px;background:#13141a;border:1px solid #23242c;border-left:3px solid #3a3b45;border-radius:10px;padding:10px;min-width:0;transition:background .15s,transform .15s}
.cxr:hover{background:#191a21;transform:translateY(-2px)}
.cxr.ok{border-left-color:#7bd555}.cxr.late{border-left-color:var(--acc)}.cxr.soon{border-left-color:#3db4f2}
.cxr.ok .cxp img{opacity:.5}
.cxp{position:relative;flex:none;width:86px;aspect-ratio:2/3;border-radius:6px;overflow:hidden;background:var(--card);display:block}
.cxp img{width:100%;height:100%;object-fit:cover;display:block}
.cxmine{position:absolute;top:5px;right:5px;width:20px;height:20px;border-radius:50%;background:var(--acc);color:#111;font-size:11px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px #000a}
.cxbd{flex:1;min-width:0;display:flex;flex-direction:column;gap:5px}
.cxtop{display:flex;align-items:center;gap:8px;justify-content:space-between}
.cxep{font-size:12px;font-weight:800;color:var(--acc);text-transform:uppercase;letter-spacing:.5px}
.cxn{color:#fff;text-decoration:none;font-weight:700;font-size:15px;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cxn:hover{color:var(--acc)}
.cxm{font-size:12px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cxg{display:flex;gap:5px;flex-wrap:wrap}
.cxg span{font-size:11px;background:#1d1e26;color:#b8b8c2;border-radius:10px;padding:2px 8px}
.cxg .cxpl{background:#0e2a3a;color:#6cc8f5}.cxg .cxpl.cr{background:#3a1d0a;color:#ff9a4d;font-weight:700}
.cxfoot{display:flex;align-items:center;gap:10px;margin-top:auto}
.cxtm{font-weight:800;font-size:15px;font-variant-numeric:tabular-nums}
.cxpg{flex:1;height:4px;background:#262731;border-radius:3px;overflow:hidden;min-width:30px}.cxpg i{display:block;height:100%;background:var(--acc)}
.cxst{font-size:11px;font-weight:700;padding:2px 9px;border-radius:10px;background:#262731;color:#c4c4cc;white-space:nowrap}
.cxst.ok{background:#1e3a26;color:#7bd555}.cxst.late{background:#4a2a12;color:#ffb35c}.cxst.soon{background:#12303f;color:#6cc8f5}
.cxb1{margin-left:auto;background:var(--acc);color:#111;border:0;border-radius:5px;font-weight:800;font-size:12px;padding:5px 11px;cursor:pointer}
.cxb2{margin-left:auto;background:#1d1e26;color:#fff;border:1px solid #33343e;border-radius:5px;font-weight:700;font-size:12px;padding:5px 10px;cursor:pointer}
.cxb2:hover{border-color:var(--acc);color:var(--acc)}
.cxb1:disabled,.cxb2:disabled{opacity:.5;cursor:wait}
/* carte affiche */
.cxs{min-width:0;display:flex;flex-direction:column;gap:6px}
.cxsp{position:relative;display:block;aspect-ratio:2/3;border-radius:7px;overflow:hidden;background:var(--card);transition:transform .15s,box-shadow .15s}
.cxs:hover .cxsp{transform:translateY(-3px);box-shadow:0 8px 22px #000b}
.cxsp img{width:100%;height:100%;object-fit:cover;display:block}
.cxs.ok .cxsp img{opacity:.5}
.cxtime{position:absolute;left:5px;top:5px;background:#000c;color:#fff;font-size:11px;font-weight:800;padding:2px 6px;border-radius:4px;font-variant-numeric:tabular-nums}
.cxsep{position:absolute;left:0;right:0;bottom:0;padding:18px 6px 7px;background:linear-gradient(transparent,#000d);font-size:11px;font-weight:800;color:#fff}
.cxsbar{position:absolute;left:0;right:0;bottom:0;height:3px;background:#3a3b45}
.cxsbar.ok{background:#7bd555}.cxsbar.late{background:var(--acc)}.cxsbar.soon{background:#3db4f2}
.cxsn{color:#fff;text-decoration:none;font-size:12.5px;font-weight:600;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cxsn:hover{color:var(--acc)}
.cxsf{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.cxsf .cxb1,.cxsf .cxb2{padding:3px 8px;font-size:11px}
/* vue Semaine */
.cxw{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:12px;align-items:start}
.cxcol{background:#101117;border:1px solid #1d1e25;border-radius:10px;padding:10px;min-width:0}
.cxcol.today{border-color:var(--acc)}
.cxcol header{display:flex;align-items:baseline;gap:8px;border-bottom:1px solid #1d1e25;padding-bottom:8px;margin-bottom:10px}
.cxcol header span{font-size:12px;color:var(--mut);text-transform:capitalize}
.cxcol header b{font-size:20px}.cxcol.today header b{color:var(--acc)}
.cxcol header small{margin-left:auto;color:var(--mut);font-size:11px}
.cxlist{display:flex;flex-direction:column;gap:14px}
.cxe{color:#6c6d79;font-size:13px;margin:6px 0}.cxe a{color:var(--acc)}
/* vue Mois */
.cxmh{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:6px;color:var(--mut);font-size:12px;text-align:center;text-transform:capitalize}
.cxmg{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}
.cxmc{background:#101117;border:1px solid #1d1e25;border-radius:8px;min-height:112px;padding:6px;display:flex;flex-direction:column;gap:5px;cursor:pointer;min-width:0}
.cxmc:hover{border-color:#3a3b45}.cxmc.out{opacity:.4}.cxmc.today{border-color:var(--acc)}.cxmc.sel{background:#1a1b22;border-color:#fff}
.cxmn{font-size:12px;font-weight:700;color:#c4c4cc}.cxmc.today .cxmn{color:var(--acc)}
.cxmz{display:flex;flex-wrap:wrap;gap:3px}
.cxmi{width:34px;aspect-ratio:2/3;border-radius:3px;overflow:hidden;background:var(--card);border-bottom:2px solid #3a3b45}
.cxmi.ok{border-bottom-color:#7bd555;opacity:.6}.cxmi.late{border-bottom-color:var(--acc)}.cxmi.soon{border-bottom-color:#3db4f2}
.cxmi img{width:100%;height:100%;object-fit:cover;display:block}
.cxmm{font-size:11px;color:var(--mut)}.cxmcnt{display:none}
.cxgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
/* chargement / erreur */
.cxsk{height:130px;border-radius:10px;background:linear-gradient(90deg,#13141a 25%,#1b1c24 50%,#13141a 75%);background-size:200% 100%;animation:cxsh 1.2s linear infinite}
@keyframes cxsh{to{background-position:-200% 0}}
.cxerr{color:#ffb35c;background:#2a1a0c;border:1px solid #4a2a12;border-radius:8px;padding:12px 14px}
@media(max-width:1100px){.cxw{grid-template-columns:1fr}.cxwl .cxar{display:flex}.cxlist{flex-direction:row;padding-bottom:6px}.cxlist .cxs{flex:0 0 128px}.cxlist .cxe,.cxlist .cxsk{flex:1}}
@media(max-width:1000px){.cxmc{min-height:60px;align-items:center}.cxmz,.cxmm{display:none}.cxmcnt{display:block;font-weight:800;color:var(--acc)}}
@media(max-width:900px){.cxh{flex-wrap:wrap;padding:18px}.cxhn{width:100%}.cxhp{width:96px}.cxhi h2{font-size:22px}.cxcd{font-size:28px}}
@media(max-width:700px){.cxbar{position:static}.cxslot{grid-template-columns:1fr;gap:4px}.cxsl{text-align:left;display:flex;gap:8px;align-items:baseline}.cxsg{padding-left:12px;grid-template-columns:1fr}.cxd b{font-size:19px}.cxd small{font-size:10px}.cxstat{margin-left:0}}
/* catalogue */
.catp{max-width:1240px;margin:0 auto;padding:24px 4vw 80px}
.catp h1{margin:0;font-size:28px}
.ctbar{position:sticky;top:var(--hh);z-index:6;background:rgba(11,11,15,.97);padding:12px 0 14px;margin-top:10px;border-bottom:1px solid #23232b}
.cttyp{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.cttyp button{background:#13141a;border:1px solid #23242c;color:var(--mut);font-weight:700;font-size:14px;padding:8px 18px;border-radius:20px;cursor:pointer;transition:background .2s,color .2s,border-color .2s}
.cttyp button small{margin-left:7px;font-weight:500;opacity:.7}
.cttyp button:hover{color:#fff;border-color:var(--acc)}
.cttyp button.on{background:var(--acc);border-color:var(--acc);color:#111}
.ctflt{display:flex;gap:8px;flex-wrap:wrap}
.ctflt input{flex:1;min-width:200px}
.catp .vgrid{margin-top:20px}
.ctdlh{margin-top:12px}
.ctdlb{display:none;flex-wrap:wrap;align-items:center;gap:8px;margin-top:10px;padding:12px 14px;background:#13141a;border:1px solid #23242c;border-radius:10px}
.ctdlb.on{display:flex}
.ctdlb input{width:84px}
.ctdlb small{flex:1 1 100%;color:var(--mut);font-size:12px;line-height:1.4}
#ct-more{text-align:center;margin-top:24px}
/* saisons */
.ssp{max-width:1240px;margin:0 auto;padding:24px 4vw 80px}
.ssp h1{margin:0;font-size:28px}
.ssch{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 4px}
.ssch button{background:#13141a;border:1px solid #23242c;color:var(--mut);font-weight:700;font-size:14px;padding:8px 16px;border-radius:20px;cursor:pointer;transition:background .2s,color .2s,border-color .2s}
.ssch button small{margin-left:7px;font-weight:500;opacity:.75}
.ssch button em{font-style:normal;font-size:11px;margin-left:7px;padding:2px 7px;border-radius:10px;background:#ffffff18}
.ssch button:hover{color:#fff;border-color:var(--acc)}
.ssch button.on{background:var(--acc);border-color:var(--acc);color:#111}
.ssch button.on em{background:#00000022}
.ssbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:10px 0 0;color:var(--mut);font-size:13px}
.ssflt{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.ssflt input{flex:1;min-width:200px}
.ssp .vgrid{margin-top:20px}
#ss-more{text-align:center;margin-top:24px}
/* accueil (tendances de la semaine) */
.acp{padding:18px 4vw 60px}
.acp .hero2{height:400px;margin-top:6px}
.acp .hc{max-width:min(640px,64%)}
.acp .hs{color:#d8d8de;font-size:14px;line-height:1.45;margin:2px 0 4px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.achd{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:28px 0 12px}
.achd h2{margin:0;font-size:20px}.achd small{color:var(--mut);font-size:13px}
.acbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:14px;color:var(--mut);font-size:13px}
.vc .rk{position:absolute;left:0;top:0;z-index:2;min-width:30px;padding:3px 9px 3px 7px;background:var(--acc);color:#111;font-weight:800;font-size:13px;border-radius:0 0 8px 0}
@media(max-width:700px){.acp .hero2{height:340px}.acp .hc{max-width:92%}.acp .hs{-webkit-line-clamp:2}}

/* ---------- fiche animé / manga : plein écran immersif (style AniList) ---------- */
body.mpg header{position:fixed;left:0;right:0;top:0;border-bottom-color:transparent;background:linear-gradient(#0b0b0fe6,#0b0b0f00) border-box;transition:background .3s,border-color .3s}
body.mpg.sc header{background:rgba(11,11,15,.96);border-bottom-color:#23232b}
body.mpg .pg{padding-top:var(--hh)}
.mp{width:100%}
.mh{position:relative;display:flex;min-height:max(580px,92vh);overflow:hidden;background:#0b0b0f}
.mh-bg{position:absolute;inset:0;background:center 25%/cover no-repeat;animation:mhz 28s ease-out both}
.mh-bg.soft{filter:blur(46px) brightness(.55) saturate(1.3);transform:scale(1.25);animation:none}
@keyframes mhz{from{transform:scale(1.07)}to{transform:scale(1)}}
.mh-shade{position:absolute;inset:0;background:
  radial-gradient(70% 90% at 10% 105%,color-mix(in srgb,var(--mc) 38%,transparent),transparent 70%),
  linear-gradient(0deg,var(--bg) 1%,rgba(11,11,15,.62) 38%,rgba(11,11,15,.25) 75%),
  linear-gradient(90deg,rgba(11,11,15,.82),rgba(11,11,15,.1) 70%)}
.mh-in{position:relative;flex:1;display:flex;flex-direction:column;justify-content:space-between;gap:26px;padding:calc(var(--hh) + 18px) 4vw 64px;max-width:1900px;margin:0 auto;width:100%}
.mh .back{margin:0;backdrop-filter:blur(8px)}
.mh-main{display:grid;grid-template-columns:auto minmax(0,1fr) minmax(290px,390px);gap:clamp(22px,3vw,48px);align-items:end}
.mh-cov{width:clamp(170px,17vw,300px);aspect-ratio:2/3;object-fit:cover;border-radius:12px;background:var(--card);box-shadow:0 22px 60px #000d,0 0 0 1px #ffffff14;cursor:zoom-in}
.mh-txt{min-width:0}
.mh-txt .chips{margin:0 0 10px}
.mh-txt h1{margin:0;font-size:clamp(30px,4.4vw,64px);line-height:1.04;font-weight:800;letter-spacing:-.5px;text-shadow:0 3px 22px #000b}
.mh-txt .alt{margin:8px 0 0;color:#cfcfd8;font-size:clamp(13px,1.2vw,16px)}
.mh-meta{margin:14px 0 0;color:#e6e6ec;font-size:14px;font-weight:600}
.mh-meta i{font-style:normal;color:var(--acc);margin:0 4px}
.mh-syn{margin:14px 0 0;max-width:760px;color:#dcdce3;font-size:14.5px;line-height:1.65;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;text-shadow:0 1px 8px #000a}
.mh-txt .btns{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}
.mh-txt .btn{padding:11px 18px;font-size:13.5px;border-radius:8px}
.mh-txt .btn.ghost{background:#ffffff1c;backdrop-filter:blur(8px);border:1px solid #ffffff22}
.mh-txt .btn.ghost:hover{background:#ffffff33}
.mh-txt .btn.ghost.on{background:var(--acc);color:#111}
.mh-side{background:rgba(14,15,20,.58);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid #ffffff1c;border-radius:16px;padding:18px;box-shadow:0 18px 50px #0009}
.mh-k{display:flex;align-items:center;gap:8px;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #ffffff17}
.mh-k>div{flex:1;text-align:center;min-width:0}
.mh-k b{display:block;font-size:19px}
.mh-k span{font-size:10.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.7px}
.ring{flex:none!important;width:76px;height:76px;border-radius:50%;display:flex!important;flex-direction:column;align-items:center;justify-content:center;background:radial-gradient(closest-side,#14151b 78%,transparent 80%),conic-gradient(var(--acc) calc(var(--p)*1%),#ffffff22 0)}
.ring b{font-size:20px!important;line-height:1}
.ring span{font-size:9px!important;letter-spacing:0!important}
.mh-side .mine{background:none;border:0;padding:0;margin:0;max-width:none}
.mh-side .er label{width:96px}
.mh-side select{max-width:100%}
.mh-down{position:absolute;left:50%;bottom:12px;transform:translateX(-50%);background:none;border:0;color:#ffffffb0;font-size:30px;cursor:pointer;animation:mhb 2s ease-in-out infinite;z-index:2}
@keyframes mhb{50%{transform:translate(-50%,7px)}}
.mp-tabs{position:sticky;top:var(--hh);z-index:6;display:flex;gap:2px;overflow-x:auto;padding:0 4vw;background:rgba(11,11,15,.93);backdrop-filter:blur(10px);border-bottom:1px solid #23242c;scrollbar-width:none;scroll-margin-top:var(--hh)}
.mp-tabs::-webkit-scrollbar{display:none}
.mp-tab{background:none;border:0;border-bottom:3px solid transparent;margin-bottom:-1px;color:var(--mut);font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;padding:17px 20px;cursor:pointer;white-space:nowrap;transition:color .15s}
.mp-tab small{background:#ffffff14;border-radius:9px;padding:1px 7px;margin-left:5px;font-size:11px}
.mp-tab:hover{color:#fff}.mp-tab.on{color:#fff;border-bottom-color:var(--acc)}
.mp-wrap{display:grid;grid-template-columns:270px minmax(0,1fr);gap:clamp(24px,3vw,48px);max-width:1900px;margin:0 auto;padding:30px 4vw 90px;align-items:start}
.mp-card{background:#13141a;border:1px solid #23242c;border-radius:12px;padding:6px 18px 10px;margin-bottom:16px}
.mp-card.pad{padding:16px 18px}
.mp-sh3{margin:0 0 10px;font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:1.1px;color:var(--mut)}
.mp-card:not(.pad) .mp-sh3{margin:14px 0 4px}
h3.mp-sh3.o{margin:26px 0 12px;color:var(--acc)}
.si div{display:flex;flex-direction:column;padding:9px 0;border-bottom:1px solid #1f2027;font-size:13.5px}
.si div:last-child{border-bottom:0}
.si span{color:var(--mut);font-size:11.5px;margin-bottom:1px}
.mp-side .chip{margin:3px 5px 3px 0}
.tg{display:flex;justify-content:space-between;gap:8px;padding:6px 0;border-bottom:1px solid #1f2027;font-size:13px}
.tg small{color:var(--mut)}
#tagbox .tg.spoil{display:none}#tagbox.show .tg.spoil{display:flex}
.mp-pane{display:none}.mp-pane.on{display:block;animation:mpf .25s ease both}
@keyframes mpf{from{opacity:0;transform:translateY(6px)}}
.mp-s{margin-bottom:38px}
.mp-sh{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:14px}
.mp-h{margin:0;font-size:19px;font-weight:800}
.mp-s .syn{max-width:none;font-size:15.5px}
.rks{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:26px}
.rk{background:#13141a;border:1px solid #23242c;border-radius:10px;padding:8px 14px;font-size:13px;color:#d8d8de}
.rk b{color:var(--acc);margin-right:4px}
.rrow{display:flex;gap:14px;overflow-x:auto;padding:2px 2px 12px;scrollbar-width:thin}
.rc{flex:0 0 min(310px,82vw);display:flex;background:#13141a;border:1px solid #23242c;border-radius:10px;overflow:hidden;color:inherit;text-decoration:none;transition:transform .15s,border-color .15s}
.rc:hover{transform:translateY(-3px);border-color:#3a3b45}
.rc img{width:84px;aspect-ratio:2/3;object-fit:cover;flex:none;background:var(--card)}
.rc .tx{padding:11px 13px;display:flex;flex-direction:column;gap:3px;min-width:0}
.rc small{color:var(--acc);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.6px}
.rc b{font-size:14px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.rc span{color:var(--mut);font-size:12px}
.cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
.cc{position:relative;display:flex;justify-content:space-between;min-height:96px;background:#13141a;border:1px solid #23242c;border-radius:10px;overflow:hidden;color:inherit;text-decoration:none;transition:border-color .15s,transform .15s}
a.cc:hover{border-color:var(--acc);transform:translateY(-2px)}
.cc .cl{display:flex;min-width:0}
.cc .cl>img{width:68px;height:96px;object-fit:cover;object-position:center 22%;flex:none;background:var(--card);cursor:inherit}
.cc .cl .tx{padding:11px 13px;display:flex;flex-direction:column;justify-content:space-between;min-width:0}
.cc .cr{text-align:right}
.cc b{font-size:13.5px;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cc span{color:var(--mut);font-size:12px}
.cc>.fvi{left:6px;right:auto}
.mp-main .eps{max-width:760px}
.mp-main .vgrid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
#trbox:empty{display:none}
#trbox:not(:empty){position:fixed;inset:0;z-index:60;background:#000d;display:flex;align-items:center;justify-content:center;padding:4vw}
.trm{position:relative;width:min(1180px,100%)}
.trm iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:12px;background:#000;display:block}
.trm .note{text-align:center;margin-top:10px}
.trm .x{position:absolute;top:-44px;right:0;background:#ffffff1f;color:#fff;border:0;border-radius:50%;width:36px;height:36px;font-size:16px;cursor:pointer}
@media(max-width:1180px){
  .mh-main{grid-template-columns:auto minmax(0,1fr)}
  .mh-side{grid-column:1/-1}
}
@media(max-width:900px){
  .mp-wrap{grid-template-columns:1fr}
  .mp-side{order:2}
  .cgrid{grid-template-columns:1fr}
}
@media(max-width:640px){
  .mh{min-height:0}
  .mh-in{padding-bottom:54px}
  .mh-main{grid-template-columns:1fr}
  .mh-cov{width:150px}
  .mp-tab{padding:15px 13px}
}

/* ===== fiche œuvre v4.9 : style du profil, interactive ===== */
.mx{padding-bottom:80px}
.mx-ban{position:relative;height:320px;overflow:hidden;background:#14151a}
.mx-bg{position:absolute;inset:0;background:center/cover no-repeat}
.mx-bg.soft{filter:blur(32px) brightness(.55);transform:scale(1.25)}
.mx-sh{position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,11,15,.35),rgba(11,11,15,.1) 45%,var(--bg) 100%)}
.mx-ban .back{position:absolute;z-index:2;left:max(24px,calc((100% - 1240px)/2 + 24px));top:calc(var(--hh) + 14px)}
.mx-c{max-width:1240px;margin:0 auto;padding:0 24px}
.mx-head{display:flex;gap:28px;align-items:flex-end;flex-wrap:wrap;margin-top:-150px;position:relative}
.mx-cov{width:210px;flex:none;aspect-ratio:2/3;object-fit:cover;border-radius:8px;background:var(--card);box-shadow:0 14px 40px #000c;border:1px solid #ffffff14;cursor:zoom-in;transition:transform .2s}
.mx-cov:hover{transform:scale(1.03)}
.mx-ti{flex:1;min-width:260px;padding-bottom:4px}
.mx-ch{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}.mx-ch .chip{margin:0}
.mx-ti h1{margin:0;font-size:32px;font-weight:800;line-height:1.12;text-shadow:0 2px 12px #000}
.mx .alt{margin:6px 0 0;font-size:13.5px;color:#b4b4bd}
.mx .pmeta{margin-top:10px;font-size:14px;color:#d0d0d8}
.mx .pmeta i{font-style:normal;color:var(--acc);margin:0 5px}
.mx-gs{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}.mx-gs .chip{margin:0;border:1px solid #2f303a;background:#13141a}
.mx .pact{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:16px;padding:0}
.mx .btn{display:inline-block;border-radius:4px;text-transform:uppercase;letter-spacing:.6px;font-size:12px;padding:10px 16px;font-weight:700;transition:transform .15s,filter .15s}
.mx .btn:hover{transform:translateY(-1px);filter:brightness(1.08)}
.mx .btn.ghost{background:none;border:1px solid #3a3b45;color:#fff;padding:9px 15px}
.mx .btn.ghost:hover{border-color:var(--acc);color:var(--acc)}
.mx .btn.fvb.on{color:#ff4d6d;border-color:#ff4d6d}
.mx .mp-tabs{position:sticky;top:var(--hh);margin-top:24px;padding:0;background:rgba(11,11,15,.96);backdrop-filter:blur(6px)}
.mx .mp-tab{padding:15px 20px;font-size:12.5px;letter-spacing:.7px}
.mx .play{margin-top:26px}
.mx-main{min-width:0}
.mx .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:0 0 26px}
.mx .kpis div{background:#13141a;border:1px solid #23242c;border-radius:8px;padding:14px 16px;min-width:0;transition:transform .15s,border-color .15s}
.mx .kpis div:hover{transform:translateY(-2px);border-color:var(--acc)}
.mx .kpis b{font-size:22px;font-weight:800}.mx .kpis span{display:block;margin-top:2px;font-size:11px;text-transform:uppercase;letter-spacing:.7px}
.mx .mp-card,.mx .pcard{background:#13141a;border:1px solid #23242c;border-radius:8px;padding:18px 20px;margin-bottom:16px}
.mx .mp-card:not(.pad) .mp-sh3{margin:0 0 6px}
.mx .si div{flex-direction:row;justify-content:space-between;align-items:baseline;gap:14px;padding:9px 0;border-bottom:1px solid #1d1e25}
.mx .si div:last-child{border:0}.mx .si span{margin:0;flex:none}.mx .si b{text-align:right;font-weight:600}
.mx-mine .mine{background:none;border:0;padding:0;margin:12px 0 0;max-width:none;font-size:13px}
.mx-mine .er{flex-direction:column;align-items:stretch;gap:4px;margin:10px 0}.mx-mine .er label{width:auto}
.mx-mine .stp{display:flex;gap:4px}.mx-mine .stp input{width:auto;flex:1}
.mx .mp-h{font-size:20px;font-weight:800}
.mx-bar{display:flex;flex-wrap:wrap;align-items:center;gap:12px 16px;margin-bottom:16px}
.mx-bar .tog{margin:0}.mx-bar .fq{margin:0}
.mx .cc{transition:transform .15s,border-color .15s}
.mx .tog small{opacity:.7}
.mx[data-tab]:not([data-tab="ov"]) .mx-gt{display:none}
.igrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}.igrid .mp-card{margin:0}
@media(max-width:700px){
  .mx-c{padding:0 14px}.mx-ban{height:210px}
  .mx-head{margin-top:-100px;flex-direction:column;align-items:center;text-align:center;gap:16px}
  .mx-cov{width:150px}.mx-ti h1{font-size:25px}
  .mx .pmeta,.mx-ch,.mx-gs,.mx .pact{justify-content:center}
  .mx .mp-tab{padding:13px 14px}
}

/* ===== v4.10 : interface adaptée au téléphone ===== */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
button,a,select,input,summary{touch-action:manipulation;-webkit-tap-highlight-color:transparent}
.tabs svg{display:none;width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}

@media(max-width:900px){
  :root{--navh:calc(60px + env(safe-area-inset-bottom,0px))}
  body{padding-bottom:var(--navh);overflow-x:hidden}
  /* en-tête compact : logo + compte + rafraîchir ; recherche / genre sur une 2e ligne (accueil seulement) */
  header{gap:8px 10px;padding:calc(8px + env(safe-area-inset-top,0px)) 14px 8px}
  .logo{font-size:19px}
  #info{display:none}
  #acc{order:2}#rf{order:3}
  #q{order:4;flex:1 1 56%;min-width:0}
  #g{order:5;flex:1 1 34%;min-width:0}
  #acc,#rf{padding:8px 12px;font-size:13px;border-radius:8px;white-space:nowrap}
  #acc{max-width:34vw;overflow:hidden;text-overflow:ellipsis}
  #rf{max-width:42vw;overflow:hidden;text-overflow:ellipsis}
  /* navigation : barre d'onglets fixée en bas, avec icônes */
  .tabs{position:fixed;left:0;right:0;bottom:0;z-index:30;display:flex;background:rgba(13,13,18,.97);
    -webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-top:1px solid #23232b;padding:0 4px env(safe-area-inset-bottom,0px)}
  .tabs button{flex:1 1 0;min-width:0;display:flex;flex-direction:column;align-items:center;gap:3px;padding:9px 2px 8px;font-size:10px;font-weight:600;border:0;border-top:2px solid transparent}
  .tabs button span{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .tabs button svg{display:block}
  .tabs button.on{color:var(--acc);border-top-color:var(--acc)}
  #toast{bottom:calc(var(--navh) + 12px)}
  /* catalogue : filtres moins envahissants */
  .ctbar{position:static}
  .ctflt input{flex:1 1 100%;min-width:0}
  .ctflt select{flex:1 1 45%;min-width:0}
  .ssflt input{flex:1 1 100%;min-width:0}
  .ssflt select{flex:1 1 45%;min-width:0}
  /* fiche œuvre : « Ma liste » en premier (onglet Informations), genres / tags après le contenu */
  .mx .play{gap:16px}
  .mx .pside{display:contents}
  .mx .play .pcard,.mx .play .mp-card{margin-bottom:0}
  .mx-mine{order:0}
  .mx-main{order:1}
  .mx .pside>.mx-gt{order:2}
  .mx[data-tab]:not([data-tab="ov"]) .mx-mine{display:none}
}

@media(max-width:700px){
  input,select{font-size:16px}   /* évite le zoom automatique d'iPhone dans les champs */
  #q{flex-basis:44%}#g{flex-basis:46%}
  /* boutons faciles à toucher */
  .btn,.mx .btn,.prof .btn,.cx .btn{min-height:42px;line-height:1.2;display:inline-flex;align-items:center;justify-content:center;text-align:center}
  .sm{width:44px;height:44px}
  .stp input{height:44px}
  .mx .pact{width:100%}
  .mx .pact .btn{flex:1 1 calc(50% - 8px)}
  .mx .pact .btn:first-child{flex-basis:100%}
  .mx .sw{display:none}          /* couleur d'accent : réglable depuis la page Profil */
  .sw{width:100%;justify-content:center;margin:0;padding:4px 0 0;border:0;gap:12px}
  .sw button{width:26px;height:26px}
  /* pastilles sur les affiches : plus petites, sans chevauchement */
  .plus:not(.x),.fvi.on~.plus:not(.x){top:auto;bottom:14px;left:6px;right:auto;min-width:36px;min-height:30px;font-size:13px}
  .badge{font-size:10px;max-width:calc(100% - 12px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .poster:has(.fvi.on) .badge{max-width:calc(100% - 44px)}   /* laisse la place au cœur des favoris */
  body.mpg.sc header{background:#0b0b0f}
  .vc .tag{font-size:10px;padding:2px 5px;max-width:calc(100% - 58px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .rt{font-size:10px;padding:2px 5px}
  /* affiches : 3 par ligne, rangées plus serrées */
  .vgrid,.mx-main .vgrid,.catp .vgrid{grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:14px 10px}
  .vc b{font-size:12px}
  .pscroll>.vc{flex-basis:118px}
  .strip{gap:10px}
  a.card{flex-basis:128px}
  .t{font-size:13px}
  /* fenêtres */
  .drb{padding:18px 14px}
  .cmb{padding:20px 16px}
  .cx{padding:14px 14px 40px}
  .catp{padding:16px 14px 40px}
  .ssp{padding:16px 14px 40px}
  .acp{padding:12px 14px 30px}
}
</style></head><body>
<header id="hd">
  <span class="logo" id="logo">MA LISTE</span>
  <div class="tabs">
    <button id="tH"><svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8v9a2 2 0 0 1-2 2h-4v-7H9v7H5a2 2 0 0 1-2-2z"/></svg><span>Accueil</span></button>
    <button id="tA"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg><span>Animés</span></button>
    <button id="tM"><svg viewBox="0 0 24 24"><path d="M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z"/><path d="M4 20a2 2 0 0 0 2 2h13"/></svg><span>Mangas</span></button>
    <button id="tC"><svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/></svg><span>Calendrier</span></button>
    <button id="tS"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg><span>Saisons</span></button>
    <button id="tG"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg><span>Catalogue</span></button>
    <button id="tP"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg><span>Profil</span></button>
  </div>
  <div class="sp"></div>
  <input id="q" type="search" placeholder="Rechercher…">
  <select id="g"><option value="">Tous les genres</option></select>
  <span id="info"></span>
  <button id="acc" class="acc">🔑 Compte</button>
  <button id="rf">⟳ Rafraîchir</button>
</header>
<div id="home" style="display:none"><div id="hero"></div><div id="rows"></div><div id="empty" style="display:none"></div></div>
<main id="page" style="display:none"></main>
<div id="lb"><img alt=""><p></p></div>
<div id="cm"><div class="cmb"><button class="x" id="cmx">✕</button><div id="cmbody"></div></div></div>
<div id="dr"><div class="drb"><button class="x" id="drx">✕</button><div id="drbody"></div></div></div>
<div id="toast"></div>
<script>
const $=s=>document.querySelector(s);
let DATA={items:[],updated:0},TAB="ANIME",Q="",G="",onHome=true,SCROLL=0,RUN=false,AUTH={connected:false,name:null},REC={};
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const MS={FINISHED:"Terminé",RELEASING:"En cours de sortie",NOT_YET_RELEASED:"Pas encore sorti",CANCELLED:"Annulé",HIATUS:"En pause"};
const LS={CURRENT:"En cours",REPEATING:"Revu / relu",PLANNING:"Prévu",COMPLETED:"Terminé",PAUSED:"En pause",DROPPED:"Abandonné"};
const MONTHS=["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."];
const FMT={TV:"Série TV",TV_SHORT:"Série TV courte",MOVIE:"Film",SPECIAL:"Spécial",OVA:"OVA",ONA:"ONA",MUSIC:"Clip musical",MANGA:"Manga",NOVEL:"Roman",ONE_SHOT:"One-shot"};
const SEASON={WINTER:"Hiver",SPRING:"Printemps",SUMMER:"Été",FALL:"Automne"};
const SRC={ORIGINAL:"Original",MANGA:"Manga",LIGHT_NOVEL:"Light novel",VISUAL_NOVEL:"Visual novel",VIDEO_GAME:"Jeu vidéo",NOVEL:"Roman",WEB_NOVEL:"Web novel",DOUJINSHI:"Doujinshi",ANIME:"Anime",LIVE_ACTION:"Live action",GAME:"Jeu",COMIC:"Comics",MULTIMEDIA_PROJECT:"Projet multimédia",PICTURE_BOOK:"Livre illustré",OTHER:"Autre"};
const CTRY={JP:"Japon",KR:"Corée du Sud",CN:"Chine",TW:"Taïwan"};
const REL={SEQUEL:"Suite",PREQUEL:"Préquelle",SIDE_STORY:"Histoire parallèle",SPIN_OFF:"Spin-off",ADAPTATION:"Adaptation",ALTERNATIVE:"Version alternative",PARENT:"Histoire principale",CHARACTER:"Même personnage",SUMMARY:"Résumé",SOURCE:"Œuvre source",COMPILATION:"Compilation",CONTAINS:"Contient",OTHER:"Autre"};
const FRANCH=new Set(["SEQUEL","PREQUEL","PARENT","SIDE_STORY","SPIN_OFF","ADAPTATION","ALTERNATIVE","SOURCE","SUMMARY","COMPILATION","CONTAINS"]);
const ROLE={MAIN:"Principal",SUPPORTING:"Secondaire",BACKGROUND:"Figurant"};
const nice=s=>s?String(s).replace(/_/g," ").toLowerCase().replace(/^./,c=>c.toUpperCase()):"";
const fm=(m,k)=>(k&&m[k])||nice(k);
const dstr=o=>o&&o.y?[o.d,o.m?MONTHS[o.m-1]:null,o.y].filter(Boolean).join(" "):"";
const fdate=t=>new Date(t*1000).toLocaleDateString("fr-FR",{day:"numeric",month:"short"});
const unit=i=>i.type==="ANIME"?"Ép.":"Chap.";
const prog=i=>`${unit(i)} ${i.progress}/${i.total??"?"}`;
const num=n=>Number(n).toLocaleString("fr-FR");
const jget=async u=>{try{const r=await fetch(u);return r.ok?await r.json():null}catch(e){return null}};
const rateB=a=>`<span class="rt">★ ${a?(a/10).toFixed(1):"?"}</span>`;
const FAVS=new Set();   // œuvres : id numérique ; personnages : "c"+id
const favKey=(id,ch)=>ch?"c"+id:id;
const HEART=`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>`;
const heartI=(id,ch)=>{const k=favKey(id,ch);return `<span class="fvi${FAVS.has(k)?" on":""}" data-fvi="${k}" title="Dans tes favoris">${HEART}</span>`};
const favTitle=k=>FAVS.has(k)?"Retirer des favoris":"Ajouter aux favoris";
const favBtn=(id,ch)=>{const k=favKey(id,ch);return `<button class="btn ghost fvb${FAVS.has(k)?" on":""}" data-fav="${k}" title="${favTitle(k)}">${FAVS.has(k)?"♥ Favori":"♡ Favori"}</button>`};
const imgErr=`onerror="this.style.visibility='hidden'"`;

/* ---------- accueil ---------- */
function cats(t){
  const a=t==="ANIME";
  return [
    [a?"En cours de visionnage":"En cours de lecture",i=>["CURRENT","REPEATING"].includes(i.status)],
    ["Non commencé",i=>i.progress===0&&["PLANNING","CURRENT","PAUSED"].includes(i.status)&&i.media_status!=="NOT_YET_RELEASED"],
    ["Pas encore sorti",i=>i.media_status==="NOT_YET_RELEASED"],
    [a?"À voir":"À lire",i=>i.status==="PLANNING"],
    ["En pause",i=>i.status==="PAUSED"],
    ["Terminés",i=>i.status==="COMPLETED"],
    ["Abandonnés",i=>i.status==="DROPPED"]];
}
const WEEK=604800;
/* prochain épisode futur (projeté chaque semaine si les données sont anciennes) */
function nextUp(i){
  if(i.type!=="ANIME"||!i.next_at||!i.next_ep)return null;
  let ep=i.next_ep,at=i.next_at;const now=Date.now()/1000;
  if(at<=now){const w=Math.floor((now-at)/WEEK)+1;ep+=w;at+=w*WEEK}
  if(i.total&&ep>i.total)return null;
  return {ep,at};
}
/* dernier épisode / chapitre disponible */
function avail(i){
  if(i.type!=="ANIME")return i.total??null;
  if(i.media_status==="NOT_YET_RELEASED"&&!i.next_at)return 0;
  const n=nextUp(i);
  if(n)return n.ep-1;
  if(i.next_ep&&i.next_at&&!i.total)return i.next_ep+Math.floor((Date.now()/1000-i.next_at)/WEEK);
  return i.total??null;
}
const behind=i=>{const a=avail(i);return a==null?null:a-i.progress};
const canPlus=i=>["CURRENT","REPEATING"].includes(i.status)&&(!i.total||i.progress<i.total);

function card(i){
  let badge="";
  if(i.media_status==="NOT_YET_RELEASED")badge="Bientôt";
  else if(i.next_ep)badge=`Ép. ${i.next_ep} · ${fdate(i.next_at)}`;
  const pct=i.total?Math.min(100,i.progress/i.total*100):0;
  const pl=canPlus(i)?`<button class="plus" data-bump="${i.id}" title="Marquer ${i.type==="ANIME"?"l'épisode":"le chapitre"} suivant comme ${i.type==="ANIME"?"vu":"lu"}">+1</button>`:"";
  return `<a class="card" href="#/m/${i.id}"><div class="poster"><img loading="lazy" decoding="async" src="/img/${esc(i.img)}" alt="" ${imgErr}>${badge?`<span class="badge">${esc(badge)}</span>`:""}${rateB(i.avg)}${heartI(i.id)}${pl}${pct?`<div class="bar"><i style="width:${pct}%"></i></div>`:""}</div><div class="t">${esc(i.title)}</div><div class="s">${prog(i)}</div></a>`;
}

/* ----- bannière « Continuer à regarder / lire » ----- */
let HI=0,HP=false;
function heroItems(){
  return DATA.items.filter(i=>i.type===TAB&&["CURRENT","REPEATING"].includes(i.status)&&canPlus(i))
    .map(i=>({i,b:behind(i)}))
    .sort((x,y)=>((y.b>0)-(x.b>0))||(y.i.updated-x.i.updated)).slice(0,6).map(x=>x.i);
}
function renderHero(){
  const el=$("#hero"),list=[];
  if(!list.length){el.innerHTML="";el.style.display="none";return}
  el.style.display="block";
  HI=((HI%list.length)+list.length)%list.length;
  const i=list[HI],A=i.type==="ANIME",b=behind(i),nx=nextUp(i);
  const word=A?"Épisode":"Chapitre",pl=n=>A?(n>1?"épisodes":"épisode"):(n>1?"chapitres":"chapitre");
  let meta=`${word} ${i.progress+1}`,can=true;
  if(b!=null){
    if(b>0)meta+=` · ${b} ${pl(b)} à rattraper`;
    else{meta=`À jour (${unit(i)} ${i.progress})`+(nx?` · ép. ${nx.ep} le ${fdate(nx.at)}`:"");can=false}
  }
  const pct=i.total?Math.min(100,i.progress/i.total*100):0;
  el.innerHTML=`<div class="hero2"><div class="hbg" style="background-image:url('/img/${esc(i.img)}')"></div>
    <img class="hban" src="/img/banner_${i.id}.jpg" alt="" onerror="this.remove()"><div class="hshade"></div>
    <div class="hc"><div class="hl">${A?"CONTINUER À REGARDER":"CONTINUER À LIRE"}</div><h2>${esc(i.title)}</h2>
      <div class="hm">${esc(meta)}</div><div class="pb"><i style="width:${pct}%"></i></div><div class="s">${prog(i)}</div>
      <div class="hbt"><a class="btn" href="#/m/${i.id}">▶ Ouvrir la fiche</a>
      <button class="btn ghost" data-bump="${i.id}"${can?"":" disabled"}>${can?`+1 ${A?"vu":"lu"}`:"✓ À jour"}</button></div></div>
    <img class="hcov" src="/img/${esc(i.img)}" alt="" ${imgErr}>
    ${list.length>1?`<div class="hdots"><button data-hnav="-1">‹</button>${list.map((_,k)=>`<i class="${k===HI?"on":""}" data-dot="${k}"></i>`).join("")}<button data-hnav="1">›</button></div>`:""}</div>`;
}
$("#hero").onclick=e=>{
  const b=e.target.closest("[data-bump]");if(b&&!b.disabled){bump(+b.dataset.bump,1);return}
  const d=e.target.closest("[data-dot]");if(d){HI=+d.dataset.dot;renderHero();return}
  const n=e.target.closest("[data-hnav]");if(n){HI+=+n.dataset.hnav;renderHero()}
};
$("#hero").onmouseenter=()=>HP=true;
$("#hero").onmouseleave=()=>HP=false;

/* ----- recommandations ----- */
const IGN=()=>{try{return new Set(JSON.parse(localStorage.getItem("ml_ign")||"[]"))}catch(e){return new Set()}};
const ignAdd=id=>{const s=IGN();s.add(id);try{localStorage.setItem("ml_ign",JSON.stringify([...s]))}catch(e){}};
function recCard(x){
  const meta=[fm(FMT,x.format),x.year].filter(Boolean).join(" · ");
  return `<a class="card" href="#/m/${x.id}"><div class="poster"><img loading="lazy" src="/img/cover_${x.id}.jpg" alt="" ${imgErr}>${rateB(x.avg)}<button class="plus x" data-dismiss="${x.id}" title="Pas intéressé">✕</button></div><div class="t">${esc(x.title)}</div><div class="s">${esc(meta)}</div><div class="s why">Parce que : ${esc((x.because||[]).join(", "))}</div></a>`;
}
function recRow(){
  const r=REC[TAB];if(!r||Q||G)return "";
  const ign=IGN();
  const list=r.filter(x=>!ign.has(x.id)&&!DATA.items.some(i=>i.id===x.id)).slice(0,24);
  if(!list.length)return "";
  return `<section class="row" data-n="rec"><h2>Recommandé pour toi<small>d'après tes meilleures notes</small></h2><div class="wrap"><button class="arr l">‹</button><div class="strip">${list.map(recCard).join("")}</div><button class="arr r">›</button></div></section>`;
}
async function loadRec(t=TAB,force=false){
  if(REC[t]!==undefined&&!force)return;
  const r=await jget("/api/recommend/"+t);
  REC[t]=r?r.items:[];
  if(onHome&&TAB===t)render();
}

/* ---------- liste style AniList ---------- */
const PR=(()=>{try{return JSON.parse(localStorage.getItem("ml_list")||"{}")}catch(e){return {}}})();
const LST=Object.assign({ANIME:"ALL",MANGA:"ALL"},PR.st||{});
let LFMT=PR.fmt||"",LSORT=PR.sort||"updated",LDIR=PR.dir||-1,LVIEW=PR.view||"list",LMAX=60;
const lsave=()=>{try{localStorage.setItem("ml_list",JSON.stringify({st:LST,fmt:LFMT,sort:LSORT,dir:LDIR,view:LVIEW}))}catch(e){}};
const SORTS={updated:"Dernière modification",title:"Titre",score:"Ma note",avg:"Note moyenne",progress:"Progression",year:"Année"};
const LSTAT=[["ALL","Tout"],["CURRENT","En cours"],["PLANNING","Prévus"],["COMPLETED","Terminés"],["PAUSED","En pause"],["DROPPED","Abandonnés"]];
const inStat=(i,k)=>k==="ALL"||(k==="CURRENT"?["CURRENT","REPEATING"].includes(i.status):i.status===k);
function lsKey(i){
  switch(LSORT){
    case "title":return (i.title||"").toLowerCase();
    case "score":return i.score||0;
    case "avg":return i.avg||0;
    case "progress":return i.total?i.progress/i.total:i.progress;
    case "year":return i.year||0;
    default:return i.updated||0;
  }
}
const sc10=n=>n>=8?"s-hi":n>=6?"s-mid":"s-lo";
function lrow(i,k){
  const A=i.type==="ANIME",c=STCOL[i.status]||"#677b94",live=["CURRENT","REPEATING"].includes(i.status);
  const pct=i.total?Math.min(100,i.progress/i.total*100):0,bh=behind(i),nx=nextUp(i);
  const alt=i.romaji&&i.romaji!==i.title?`<span class="lro">${esc(i.romaji)}</span>`:"";
  const chips=(i.genres||[]).slice(0,3).map(g=>`<em data-lg="${esc(g)}" title="Filtrer : ${esc(g)}">${esc(g)}</em>`).join("");
  let badge="";
  if(i.media_status==="NOT_YET_RELEASED")badge=`<span class="lbd nx">Bientôt</span>`;
  else if(live&&bh>0)badge=`<span class="lbd">${bh} ${A?"ép.":"chap."} à rattraper</span>`;
  else if(live&&bh===0)badge=`<span class="lbd ok">À jour</span>`;
  if(nx)badge+=`<span class="lbd nx">Ép. ${nx.ep} · ${fdate(nx.at)}</span>`;
  const btn=canPlus(i)?`${i.progress>0?`<button class="lmn" data-lminus="${i.id}" title="Retirer 1">−</button>`:""}<button class="lpl" data-bump="${i.id}" title="Marquer le suivant comme ${A?"vu":"lu"}">+1</button>`:"";
  const sopt=Object.entries(LS).map(([v,n])=>`<option value="${v}"${v===i.status?" selected":""}>${n}</option>`).join("");
  const nopt=[0,1,2,3,4,5,6,7,8,9,10].map(v=>`<option value="${v}"${v===(i.score||0)?" selected":""}>${v||"–"}</option>`).join("");
  const up=i.updated?new Date(i.updated*1000).toLocaleDateString("fr-FR",{day:"numeric",month:"short",year:"numeric"}):"";
  return `<div class="lr" style="--c:${c};--d:${Math.min(k,14)*22}ms" data-go="${i.id}"><span class="ld"></span><img class="lc" loading="lazy" src="/img/${esc(i.img)}" alt="" ${imgErr}>
    <div class="lt"><b>${esc(i.title)}</b>${alt}<div class="lch">${chips}</div></div>
    <div class="ln"><select class="lsc ${i.score?sc10(i.score):""}" data-lscore="${i.id}" title="Changer ma note">${nopt}</select><small>Ma note</small></div>
    <div class="lp"><div class="lp1"><select class="lsel" data-lsel="${i.id}" title="Changer le statut">${sopt}</select><span>${esc(prog(i))}</span></div><div class="lpb"><i style="width:${pct}%"></i></div><div class="lp2">${badge}${btn}</div></div>
    <div class="lf"><b>${esc(i.format?fm(FMT,i.format):"")}</b>${esc([i.year,MS[i.media_status]].filter(Boolean).join(" · "))}<br>${i.avg?`<span class="lav">★ ${(i.avg/10).toFixed(1)}</span> `:""}${up?`<span title="Dernière modification">· ${esc(up)}</span>`:""}</div></div>`;
}
function lsum(base,A){
  const eps=base.reduce((a,i)=>a+(i.progress||0),0),sc=base.filter(i=>i.score>0);
  const mean=sc.length?(sc.reduce((a,i)=>a+i.score,0)/sc.length).toFixed(1):"–";
  const seg=["CURRENT","COMPLETED","PAUSED","DROPPED","PLANNING","REPEATING"].map(k=>[k,base.filter(i=>i.status===k).length]).filter(x=>x[1]);
  return `<div class="lsum"><div><b>${num(base.length)}</b><span>${A?"Animés":"Mangas"}</span></div><div><b>${num(eps)}</b><span>${A?"Épisodes vus":"Chapitres lus"}</span></div><div><b>${num(base.filter(i=>i.status==="COMPLETED").length)}</b><span>Terminés</span></div><div><b>${mean}</b><span>Note moyenne</span></div>${seg.length?`<div class="lsegw"><div class="lseg">${seg.map(([k,n])=>`<i style="flex:${n};background:${STCOL[k]}" title="${esc(LS[k])} : ${n}"></i>`).join("")}</div></div>`:""}</div>`;
}
function lcsv(list){
  const q=v=>'"'+String(v??"").replace(/"/g,'""')+'"';
  const rows=[["Titre","Type","Statut","Progression","Total","Note","Format","Année","Genres"]].concat(list.map(i=>[i.title,i.type,LS[i.status]||i.status,i.progress,i.total??"",i.score||"",i.format||"",i.year||"",(i.genres||[]).join(", ")]));
  const blob=new Blob(["\ufeff"+rows.map(r=>r.map(q).join(";")).join("\r\n")],{type:"text/csv;charset=utf-8"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="ma_liste_"+TAB.toLowerCase()+".csv";a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function lcur(){
  const q=Q.toLowerCase(),base=DATA.items.filter(i=>i.type===TAB&&(!G||i.genres.includes(G))&&(!LFMT||i.format===LFMT)&&(!q||(i.title+" "+(i.romaji||"")).toLowerCase().includes(q)));
  return {base,list:base.filter(i=>inStat(i,LST[TAB])).sort((x,y)=>{const a=lsKey(x),b=lsKey(y);return (a<b?-1:a>b?1:0)*LDIR})};
}
function render(){
  const root=$("#rows"),A=TAB==="ANIME";
  const fmts=[...new Set(DATA.items.filter(i=>i.type===TAB&&i.format).map(i=>i.format))].sort();
  if(LFMT&&!fmts.includes(LFMT))LFMT="";
  const {base,list}=lcur(),st=LST[TAB],shown=list.slice(0,LMAX);
  const pills=LSTAT.map(([k,n])=>`<button class="lpill${k===st?" on":""}"${k!=="ALL"?` style="--c:${STCOL[k]}"`:""} data-lst="${k}">${k!=="ALL"?"<i></i>":""}${n}<b>${base.filter(i=>inStat(i,k)).length}</b></button>`).join("");
  const fsel=`<select id="lfmt"><option value="">Tous les formats</option>${fmts.map(f=>`<option value="${f}"${f===LFMT?" selected":""}>${esc(fm(FMT,f))}</option>`).join("")}</select>`;
  const ssel=`<select id="lso">${Object.entries(SORTS).map(([k,n])=>`<option value="${k}"${k===LSORT?" selected":""}>${n}</option>`).join("")}</select>`;
  const tb=`<div class="ltb">${pills}<span class="lsp"></span>${fsel}${ssel}<button class="lbt" data-ldir title="Inverser l'ordre">${LDIR>0?"↑":"↓"}</button><button class="lbt${LVIEW==="list"?" on":""}" data-lview="list" title="Vue liste">☰</button><button class="lbt${LVIEW==="grid"?" on":""}" data-lview="grid" title="Vue grille">▦</button><button class="lbt" data-lcsv title="Exporter en CSV">⬇ CSV</button></div>`;
  let body;
  if(LVIEW==="grid")body=`<div class="lg">${shown.map((i,k)=>card(i).replace('<a class="card"',`<a class="card" style="--c:${STCOL[i.status]||"#677b94"};--d:${Math.min(k,14)*22}ms"`)).join("")}</div>`;
  else{
    const h=(k,n)=>`<span data-lsort="${k}" class="${LSORT===k?"on":""}">${n}${LSORT===k?(LDIR>0?" ↑":" ↓"):""}</span>`;
    body=`<div class="lh"><span></span><span></span>${h("title","Titre")}${h("score","Note")}${h("progress","Progression")}${h("year","Infos")}</div>${shown.map(lrow).join("")}`;
  }
  const more=list.length>shown.length?`<button class="lmore" data-lmore>Afficher plus (${list.length-shown.length})</button>`:"";
  root.innerHTML=`<div class="lwrap">${lsum(base,A)}${tb}${body}${more}${st==="ALL"?recRow():""}</div>`;
  const e=$("#empty");e.style.display=list.length?"none":"block";
  e.textContent=DATA.items.length?"Aucun résultat — essaie un autre filtre.":"Aucune donnée pour l'instant. Clique sur « Rafraîchir » (connexion internet requise la 1re fois).";
  renderHero();
}

/* ---------- page dédiée ---------- */
function descHtml(h){
  if(!h)return "<i>Pas de synopsis.</i>";
  return h.replace(/~![\s\S]*?!~/g,"").split(/(<[^>]*>)/).map(p=>{
    const m=p.match(/^<(\/?)(br|i|b|em|strong)\s*\/?>$/i);
    if(m)return `<${m[1]}${m[2].toLowerCase()}>`;
    return p.startsWith("<")?"":p.replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }).join("");
}
const GROUPS=["Séries animées","Films","OVA, ONA & spéciaux","Mangas","Light novels / romans"];
const kind=n=>n.type==="ANIME"
  ?(n.format==="MOVIE"?"Films":(!n.format||["TV","TV_SHORT"].includes(n.format))?"Séries animées":"OVA, ONA & spéciaux")
  :(n.format==="NOVEL"?"Light novels / romans":"Mangas");
function vcard(n,cur){
  const mine=DATA.items.find(x=>x.id===n.id);
  const meta=[fm(FMT,n.format),n.year,n.count?n.count+(n.type==="ANIME"?" ép.":" chap."):""].filter(Boolean).join(" · ");
  return `<a class="vc${n.id===cur?" cur":""}" href="#/m/${n.id}"><div class="p"><img loading="lazy" src="/img/cover_${n.id}.jpg" alt="" ${imgErr}>${n.id===cur?'<span class="tag cur">Actuel</span>':""}${mine?`<span class="tag">${esc(LS[mine.status]||"")}</span>`:""}${rateB(n.avg||(mine&&mine.avg))}${heartI(n.id)}</div><b>${esc(n.title)}</b><span class="m">${esc(meta)}</span>${n.rel&&n.id!==cur?`<em>${esc(REL[n.rel]||nice(n.rel))}</em>`:""}</a>`;
}
function bars(d,A){
  const st=d.stats||{};let out="";
  const sc=(st.scores||[]).slice().sort((a,b)=>a.score-b.score);
  if(sc.length){
    const mx=Math.max(...sc.map(x=>x.amount),1);
    out+=`<h3>Répartition des notes</h3><div class="vb">${sc.map(x=>`<div title="${num(x.amount)} votes"><i style="height:${Math.round(x.amount/mx*100)}%"></i>${x.score/10}</div>`).join("")}</div>`;
  }
  const ss=(st.status||[]).slice().sort((a,b)=>b.amount-a.amount);
  if(ss.length){
    const mx=Math.max(...ss.map(x=>x.amount),1);
    out+=`<h3>Utilisateurs</h3><div class="hb">${ss.map(x=>`<div><span>${esc(LS[x.status]||nice(x.status))}</span><u style="width:${Math.max(2,x.amount/mx*60)}%"></u>${num(x.amount)}</div>`).join("")}</div>`;
  }
  return out;
}
function mxStats(d){
  const st=d.stats||{},ss=(st.status||[]).slice().sort((a,b)=>b.amount-a.amount),sc=(st.scores||[]).slice().sort((a,b)=>a.score-b.score);
  let out="";
  if(ss.length){
    const tot=ss.reduce((a,x)=>a+x.amount,0),R=80,C=2*Math.PI*R;let off=0;
    const col=x=>STCOL[x.status]||"#677b94";
    const arcs=ss.map(x=>{const len=x.amount/tot*C,c=`<circle cx="100" cy="100" r="${R}" stroke="${col(x)}" stroke-dasharray="${Math.max(len-2,.5)} ${C}" stroke-dashoffset="${-off}" data-st="${x.status}" data-n="${num(x.amount)}"/>`;off+=len;return c}).join("");
    const leg=ss.map(x=>`<button data-st="${x.status}" data-n="${num(x.amount)}"><i style="background:${col(x)}"></i>${esc(LS[x.status]||nice(x.status))} <b>${num(x.amount)}</b> <small>${Math.round(x.amount/tot*100)}%</small></button>`).join("");
    out+=`<h3 class="mp-sh3">Utilisateurs</h3><div class="dn" data-tot="${num(tot)}"><div class="dnsvg"><svg viewBox="0 0 200 200">${arcs}</svg><div class="dnc"><b>${num(tot)}</b><span>membres</span></div></div><div class="leg">${leg}</div></div>`;
  }
  if(sc.length){
    const mx=Math.max(...sc.map(x=>x.amount),1);
    out+=`<h3 class="mp-sh3 o">Répartition des notes</h3><div class="pcol">${sc.map(x=>`<div class="pc" title="${num(x.amount)} votes"><b>${x.amount>=1000?Math.round(x.amount/1000)+"k":x.amount}</b><div class="bw"><i style="height:${Math.round(x.amount/mx*100)}%"></i></div><span>${x.score/10}</span></div>`).join("")}</div>`;
  }
  return out;
}
function mxFilter(pane){
  if(!pane)return;
  const f=pane.querySelector(".mx-fq"),q=f?f.value.trim().toLowerCase():"",on=pane.querySelector("[data-mxpill].on"),at=on&&on.dataset.val?on.dataset.attr:null,val=on?on.dataset.val:"";
  pane.querySelectorAll("[data-q]").forEach(e=>{e.hidden=!!((q&&!e.dataset.q.includes(q))||(at&&e.dataset[at]!==val))});
}
function pageHtml(id,d,f){
  const nodes=(f&&f.nodes)||[];
  const node=nodes.find(n=>n.id===id);
  const mine=DATA.items.find(x=>x.id===id);
  const type=(d&&d.type)||(mine&&mine.type)||(node&&node.type)||"ANIME";
  const A=type==="ANIME";
  if(!d&&!mine&&!node)return `<div class="pg" style="margin-top:30px"><button class="back" data-back>← Retour à la liste</button><h1>Fiche indisponible</h1><p class="note">Cette œuvre n'a pas encore été téléchargée. Lance un rafraîchissement avec internet.</p></div>`;
  const t=(d&&d.title)||{english:mine?mine.title:(node&&node.title),romaji:mine&&mine.romaji};
  const name=t.english||t.romaji||(node&&node.title)||"?";
  const alt=[t.romaji,t.native].filter(x=>x&&x!==name).join(" · ");
  const pick=d||{};
  const fmt=pick.format||(mine&&mine.format)||(node&&node.format);
  const status=pick.status||(mine&&mine.media_status)||(node&&node.status);
  const avg=pick.avg||(mine&&mine.avg);
  const nxt=pick.next||(mine&&mine.next_ep?{episode:mine.next_ep,at:mine.next_at}:null);
  const year=(d&&d.season_year)||(mine&&mine.year)||(node&&node.year)||"";
  const links=(d&&d.links||[]).slice().sort((a,b)=>(b.type==="STREAMING")-(a.type==="STREAMING"));
  const auth=d?(d.staff||[]).filter(s=>/story|art/i.test(s.role)).slice(0,3).map(s=>esc(s.name)).join(", "):"";
  const studio=d?(d.studios||[]).join(", "):"";

  /* ---- fond immersif ---- */
  const bg=d&&d.banner
    ?`<div class="mh-bg" style="background-image:url('/img/${esc(d.banner)}')"></div>`
    :`<div class="mh-bg soft" style="background-image:url('/img/cover_${id}.jpg')"></div>`;

  /* ---- méta + puces ---- */
  const meta=[
    fmt?esc(fm(FMT,fmt)):"",
    d&&d.season&&d.season_year?esc((SEASON[d.season]||"")+" "+d.season_year):(year||""),
    d?(A?(d.episodes?d.episodes+" ép."+(d.duration?" × "+d.duration+" min":""):""):(d.chapters?d.chapters+" chap.":(d.volumes?d.volumes+" vol.":""))):"",
    A?esc(studio):esc(auth)
  ].filter(Boolean).join(" <i>•</i> ");
  const chips=[
    status?`<span class="chip hl">${esc(MS[status]||nice(status))}</span>`:"",
    nxt?`<span class="chip">Ép. ${nxt.episode} · ${esc(fdate(nxt.at))}</span>`:"",
    d&&d.adult?`<span class="chip adult">18+</span>`:""
  ].join("");

  /* ---- panneau « ma liste » (mêmes ids qu'avant : #ed, #e-st, #e-pg, #e-sc, #e-bar, #a-st) ---- */
  let mineBlock;
  const nxInfo=nxt?`Prochain épisode : ${nxt.episode} (${fdate(nxt.at)})`:"";
  if(mine){
    const pct=mine.total?Math.min(100,mine.progress/mine.total*100):0;
    const st=Object.keys(LS).map(k=>`<option value="${k}"${k===mine.status?" selected":""}>${LS[k]}</option>`).join("");
    const sc=Array.from({length:11},(_,k)=>`<option value="${k}"${k===Math.round(mine.score||0)?" selected":""}>${k?k+" / 10":"—"}</option>`).join("");
    mineBlock=`<div class="mine edit" id="ed" data-id="${id}">
      <div class="er"><label>Statut</label><select id="e-st">${st}</select></div>
      <div class="er"><label>${A?"Épisodes vus":"Chapitres lus"}</label><span class="stp"><button class="sm" data-step="-1">−</button><input id="e-pg" type="number" min="0"${mine.total?` max="${mine.total}"`:""} value="${mine.progress}"><button class="sm" data-step="1">+</button></span><span class="s">/ ${mine.total??"?"}</span></div>
      <div class="er"><label>Ma note</label><select id="e-sc">${sc}</select></div>
      <div class="pb"><i id="e-bar" style="width:${pct}%"></i></div>
      <div class="s">${esc(nxInfo)}${mine.updated?`${nxInfo?" · ":""}Dernière activité : ${new Date(mine.updated*1000).toLocaleDateString("fr-FR")}`:""}</div>
      <div class="er" style="margin-top:8px"><button class="btn ghost sm2" data-remove>Retirer de ma liste</button>${AUTH.connected?"":`<span class="s">Connecte ton compte (🔑) pour enregistrer les modifications.</span>`}</div></div>`;
  }else{
    mineBlock=`<div class="mine off" id="ed" data-id="${id}"><div class="er"><label>Pas dans ma liste</label>
      <select id="a-st"><option value="PLANNING">Prévu</option><option value="CURRENT">En cours</option><option value="COMPLETED">Terminé</option></select>
      <button class="btn sm2" data-add>＋ Ajouter à ma liste</button></div>${nxInfo?`<div class="s">${esc(nxInfo)}</div>`:""}</div>`;
  }

  /* ---- boutons d'action ---- */
  let btns="";
  if(d&&d.trailer_embed)btns+=`<button class="btn" data-trailer="${esc(d.trailer_embed)}">▶ Bande-annonce</button>`;
  btns+=favBtn(id);
  btns+=links.filter(l=>l.type==="STREAMING").slice(0,4).map(l=>`<a class="btn ghost" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join("");
  if(d&&d.mal)btns+=`<a class="btn ghost" href="https://myanimelist.net/${A?"anime":"manga"}/${d.mal}" target="_blank" rel="noopener">MyAnimeList ↗</a>`;

  /* ---- statistiques rapides (hero) ---- */
  const mk=(v,l)=>v||v===0?`<div><b>${v}</b><span>${l}</span></div>`:"";
  const ring=avg?`<div class="ring" style="--p:${avg}"><b>${(avg/10).toFixed(1)}</b><span>/ 10</span></div>`:"";
  const quick=ring+(d?mk(d.popularity?num(d.popularity):"","Membres")+mk(d.favourites?num(d.favourites):"","Favoris"):"");

  /* ---- colonne d'informations (style AniList) ---- */
  const si=(k,v)=>v||v===0?`<div><span>${k}</span><b>${v}</b></div>`:"";
  let info;
  if(d){
    info=[
      si("Format",esc(fm(FMT,d.format))),
      A?si("Épisodes",d.episodes):si("Chapitres",d.chapters),
      A?si("Durée",d.duration?d.duration+" min / épisode":""):si("Volumes",d.volumes),
      si("Statut",esc(MS[d.status]||"")),
      A&&d.season?si("Saison",esc(SEASON[d.season]+" "+(d.season_year||""))):"",
      si("Début",dstr(d.start)),si("Fin",dstr(d.end)),
      A?si("Studio",esc(studio)):si("Auteur(s)",auth),
      si("Source",d.source?esc(fm(SRC,d.source)):""),
      si("Pays d'origine",d.country?esc(CTRY[d.country]||d.country):""),
      si("Score moyen",d.avg?(d.avg/10).toFixed(1)+" / 10":""),
      si("Popularité",d.popularity?num(d.popularity)+" membres":""),
      si("Favoris",d.favourites?num(d.favourites):""),
      si("Romaji",esc(t.romaji||"")),si("Anglais",esc(t.english||"")),si("Natif",esc(t.native||"")),
      (d.synonyms||[]).length?si("Autres titres",d.synonyms.map(esc).join("<br>")):"",
      si("Public",d.adult?"Adulte (18+)":"")
    ].join("");
  }else{
    info=si("Format",esc(fm(FMT,fmt)))+si("Année",year)+si("Statut",esc(MS[status]||""))+si("Score moyen",avg?(avg/10).toFixed(1)+" / 10":"");
  }
  const genres=d?(d.genres||[]):((mine&&mine.genres)||[]);
  const tg=d?(d.tags||[]).slice().sort((a,b)=>b.rank-a.rank).slice(0,40):[];
  const hasSp=tg.some(x=>x.spoiler);
  const side=
    ""+
    (genres.length?`<div class="mp-card pad mx-gt"><h3 class="mp-sh3">Genres</h3>${genres.map(g=>`<span class="chip hl">${esc(g)}</span>`).join("")}</div>`:"")+
    (tg.length?`<div class="mp-card pad mx-gt"><h3 class="mp-sh3">Tags</h3><div id="tagbox">${tg.map(x=>`<div class="tg${x.spoiler?" spoil":""}"><span>${esc(x.name)}</span><small>${x.rank}%</small></div>`).join("")}</div>${hasSp?`<label class="tgl"><input type="checkbox" id="spo"> Afficher les tags spoilers</label>`:""}</div>`:"")+
    "";

  /* ---- composants de contenu ---- */
  const ms=(h,body,more)=>body?`<section class="mp-s"><div class="mp-sh"><h2 class="mp-h">${h}</h2>${more||""}</div>${body}</section>`:"";
  const ccard=c=>{const v=(c.va||[])[0];return `<a class="cc" data-q="${esc((c.name+" "+(c.va||[]).map(v=>v.name).join(" ")).toLowerCase())}" data-role="${esc(c.role||"")}" href="#/c/${c.id}"><div class="cl"><img loading="lazy" src="/img/${esc(c.img||"")}" alt="" ${imgErr}><div class="tx"><b>${esc(c.name)}</b><span>${ROLE[c.role]||""}</span></div></div>${v?`<div class="cl cr"><div class="tx"><b>${esc(v.name)}</b><span>Japonais</span></div><img loading="lazy" src="/img/${esc(v.img||"")}" alt="" ${imgErr}></div>`:""}${heartI(c.id,true)}</a>`};
  const scard=s=>`<div class="cc" data-q="${esc((s.name+" "+s.role).toLowerCase())}"><div class="cl"><img loading="lazy" data-zoom data-cap="${esc(s.name)}" src="/img/${esc(s.img||"")}" alt="" ${imgErr}><div class="tx"><b>${esc(s.name)}</b><span>${esc(s.role)}</span></div></div></div>`;
  const chars=(d&&d.characters)||[],staff=(d&&d.staff)||[],eps=(d&&d.eps)||[];
  const more=(k,n,lim)=>n>lim?`<button class="lnk" data-pt="${k}">Voir tout (${n}) →</button>`:"";

  const relN=nodes.filter(n=>n.id!==id).sort((a,b)=>(!!b.rel)-(!!a.rel)||(a.year||9999)-(b.year||9999)).slice(0,14);
  const relRow0=relN.length?`<div class="rrow">${relN.map(n=>{
    const m2=[fm(FMT,n.format),n.year,n.count?n.count+(n.type==="ANIME"?" ép.":" chap."):""].filter(Boolean).join(" · ");
    return `<a class="rc" href="#/m/${n.id}"><img loading="lazy" src="/img/cover_${n.id}.jpg" alt="" ${imgErr}><div class="tx"><small>${esc(n.rel?(REL[n.rel]||nice(n.rel)):kind(n))}</small><b>${esc(n.title)}</b><span>${esc(m2)}</span></div></a>`}).join("")}</div>`:"";

  const relRow=relRow0?scrollRow("rrow",relRow0.replace(/^<div class="rrow">|<\/div>$/g,"")):"";
  const grp=(h,rows)=>{const r=rows.filter(Boolean).join("");return r?`<div class="mp-card"><h3 class="mp-sh3">${h}</h3><div class="si">${r}</div></div>`:""};
  let igrid="",prgrid="";
  if(d){
    const pl=(()=>{const a=d.start,b=d.end;if(!a||!b)return "";const m=(b.y-a.y)*12+((b.m||1)-(a.m||1));if(m<1)return "Moins d'un mois";const y=Math.floor(m/12),r=m%12;return [y?y+(y>1?" ans":" an"):"",r?r+" mois":""].filter(Boolean).join(" ")})();
    const ss=(d.stats&&d.stats.status||[]).slice().sort((x,y)=>y.amount-x.amount),tot=ss.reduce((q,x)=>q+x.amount,0),votes=((d.stats&&d.stats.scores)||[]).reduce((q,x)=>q+x.amount,0);
    const tm=A&&d.episodes&&d.duration?d.episodes*d.duration:0;
    prgrid=[
      grp("Production",[A?si("Studio(s)",esc(studio)):si("Auteur(s)",auth),si("Source",d.source?esc(fm(SRC,d.source)):""),si("Pays d'origine",d.country?esc(CTRY[d.country]||d.country):"")]),
      grp("Équipe principale",(d.staff||[]).slice(0,12).map(x=>si(esc(x.role||"Staff"),esc(x.name))))
    ].join("");
    igrid=[
      grp("Général",[si("Type",A?"Animé":"Manga"),si("Format",esc(fm(FMT,d.format))),A?si("Épisodes",d.episodes):si("Chapitres",d.chapters),A?si("Durée par épisode",d.duration?d.duration+" min":""):si("Volumes",d.volumes),si("Durée totale",tm?durF(tm):""),si("Statut",esc(MS[d.status]||"")),si("Public",d.adult?"Adulte (18+)":"Tout public")]),
      grp(A?"Diffusion":"Publication",[A&&d.season?si("Saison",esc(SEASON[d.season]+" "+(d.season_year||""))):"",si("Début",dstr(d.start)),si("Fin",dstr(d.end)),si(A?"Durée de diffusion":"Durée de publication",pl),nxt?si("Prochain épisode","Ép. "+nxt.episode+" · "+esc(new Date(nxt.at*1000).toLocaleString("fr-FR",{dateStyle:"long",timeStyle:"short"}))):""]),
      grp("Titres",[si("Romaji",esc(t.romaji||"")),si("Anglais",esc(t.english||"")),si("Natif",esc(t.native||"")),(d.synonyms||[]).length?si("Autres titres",d.synonyms.map(esc).join("<br>")):""]),
      grp("Communauté",[si("Score moyen",d.avg?(d.avg/10).toFixed(1)+" / 10":""),si("Popularité",d.popularity?num(d.popularity)+" membres":""),si("Favoris",d.favourites?num(d.favourites):""),si("Votes",votes?num(votes):"")].concat(ss.map(x=>si(esc(LS[x.status]||nice(x.status)),num(x.amount)+" · "+Math.round(x.amount/tot*100)+" %")))),
    ].join("");
  }else igrid=grp("Général",[si("Format",esc(fm(FMT,fmt))),si("Année",year),si("Statut",esc(MS[status]||"")),si("Score moyen",avg?(avg/10).toFixed(1)+" / 10":"")]);
  let co="",ov="";
  if(d&&(d.rankings||[]).length)ov+=`<div class="rks">${d.rankings.slice(0,6).map(r=>`<span class="rk"><b>#${r.rank}</b> ${esc(r.context)}</span>`).join("")}</div>`;
  ov+=ms("Synopsis",d?`<div class="syn">${descHtml(d.description)}</div>`:`<span class="note">Fiche détaillée non téléchargée. Clique sur « Rafraîchir » avec une connexion internet.</span>`);
  ov+=igrid?`<div class="igrid">${igrid}</div>`:"";
  if(d){
    const b=mxStats(d);
    co+=ms("Statistiques",b?`<div class="mp-card pad">${b}</div>`:"");
    co+=ms("Si tu aimes celui-ci",(d.recs||[]).length?`<div class="cxwrap"><button class="cxar l off" data-cxar="-1" aria-label="Précédent">${CXL}</button><div class="cxscroll pscroll">${d.recs.map(r=>vcard(r,id).replace("</b>",`</b>${r.rating?`<span class="m">👍 ${r.rating}</span>`:""}`)).join("")}</div><button class="cxar r off" data-cxar="1" aria-label="Suivant">${CXR}</button></div>`:"");
  }
  const other=(d&&d.relations||[]).filter(r=>!FRANCH.has(r.relation));
  if(other.length)ov+=ms("Autres œuvres liées",other.map(r=>`<a class="chip" style="text-decoration:none;color:#fff" href="#/m/${r.id}">${esc(REL[r.relation]||nice(r.relation))} : ${esc(r.title)}</a>`).join(""));

  const mxk=(v,l)=>v||v===0?`<div><b>${v}</b><span>${l}</span></div>`:"";
  const totMin=A&&d&&d.episodes&&d.duration?d.episodes*d.duration:0;
  if(d)ov=`<div class="kpis">${mxk(avg?"★ "+(avg/10).toFixed(1):"","Score moyen")}${mxk(d.popularity?num(d.popularity):"","Membres")}${mxk(d.favourites?num(d.favourites):"","Favoris")}${A?mxk(d.episodes,"Épisodes"):mxk(d.chapters,"Chapitres")}${totMin?mxk(durF(totMin),"Durée totale"):""}</div>`+ov;
  let fr="";
  if(nodes.length>1){
    const byK={};nodes.forEach(n=>(byK[kind(n)]=byK[kind(n)]||[]).push(n));
    const ks=GROUPS.filter(g=>byK[g]),all=nodes.slice().sort((a,b)=>(a.year||9999)-(b.year||9999)||a.id-b.id);
    fr=`<div class="mx-bar"><div class="tog"><button class="on" data-mxpill data-attr="k" data-val="">Tout<small> ${nodes.length}</small></button>${ks.map(g=>`<button data-mxpill data-attr="k" data-val="${esc(g)}">${g}<small> ${byK[g].length}</small></button>`).join("")}</div></div><div class="vgrid fkgrid">${all.map(n=>vcard(n,id).replace('<a class="vc','<a data-q="" data-k="'+esc(kind(n))+'" class="vc')).join("")}</div>`;
  }
  const rolesP=[...new Set(chars.map(c=>c.role).filter(Boolean))];
  const chBar=`<div class="mx-bar"><input class="fq mx-fq" type="search" placeholder="Rechercher un personnage ou un doubleur…">${rolesP.length>1?`<div class="tog"><button class="on" data-mxpill data-attr="role" data-val="">Tous</button>${rolesP.map(r=>`<button data-mxpill data-attr="role" data-val="${r}">${ROLE[r]||nice(r)}</button>`).join("")}</div>`:""}</div>`;
  const stBar=`<div class="mx-bar"><input class="fq mx-fq" type="search" placeholder="Rechercher un membre du staff…"></div>`;
  const T=[
    {k:"ov",h:"Informations générales",html:ov},
    {k:"pr",h:"Production",html:prgrid?`<div class="igrid">${prgrid}</div>`:""},
    {k:"ch",h:"Personnages"+(chars.length?` <small>${chars.length}</small>`:""),html:chars.length?chBar+`<div class="cgrid fkgrid">${chars.map(ccard).join("")}</div>`:""},
    {k:"st",h:"Staff"+(staff.length?` <small>${staff.length}</small>`:""),html:staff.length?stBar+`<div class="cgrid fkgrid">${staff.map(scard).join("")}</div>`:""},
    {k:"fr",h:"Franchise"+(nodes.length>1?` <small>${nodes.length}</small>`:""),html:fr},
    {k:"co",h:"Communauté",html:co},
    {k:"ep",h:"Épisodes"+(eps.length?` <small>${eps.length}</small>`:""),html:A&&eps.length?`<div class="mp-card pad eps">${eps.map(e=>`<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>`).join("")}</div>`:""}
  ].filter(x=>x.html);

  const back=PREV==="#/cal"?"← Retour au calendrier":PREV==="#/accueil"?"← Retour à l'accueil":PREV==="#/catalogue"?"← Retour au catalogue":PREV==="#/saisons"?"← Retour aux saisons":PREV==="#/profil"?"← Retour au profil":"← Retour aux "+(TAB==="MANGA"?"mangas":"animés");
  const strm=links.filter(l=>l.type==="STREAMING"),cr=strm.find(l=>/crunchyroll/i.test(l.site))||strm[0];
  const trB=d&&d.trailer_embed?`data-trailer="${esc(d.trailer_embed)}"`:"";
  const act=(cr?`<a class="btn" href="${esc(cr.url)}" target="_blank" rel="noopener">▶ Regarder sur ${esc(cr.site)}</a>`:"")+(trB?`<button class="btn ghost" ${trB}>▶ Bande-annonce</button>`:"")+favBtn(id);
  const acU=pfAcc(),acC=/^#[0-9a-f]{6}$/i.test(acU)?acU:"";
  const sws=`<div class="sw" title="Couleur d'accent">${["",...SWC.filter(c=>c!=="#f47521")].map(c=>`<button data-mxacc="${c}" style="background:${c||"#f47521"}" class="${c===acC?"on":""}"></button>`).join("")}</div>`;
  const bgU=d&&d.banner?`/img/${esc(d.banner)}`:`/img/cover_${id}.jpg`;
  const gt=genres.slice(0,5).map(g=>`<span class="chip">${esc(g)}</span>`).join("");
  return `<div class="mp mx" style="--acc:${acC||"#f47521"}">
    <div class="mx-ban"><div class="mx-bg${d&&d.banner?"":" soft"}" style="background-image:url('${bgU}')"></div><div class="mx-sh"></div><button class="back" data-back>${back}</button></div>
    <div class="mx-c">
      <div class="mx-head">
        <img class="mx-cov" data-zoom data-cap="${esc(name)}" src="/img/cover_${id}.jpg" alt="" ${imgErr}>
        <div class="mx-ti">
          <div class="mx-ch">${chips}</div>
          <h1>${esc(name)}</h1>${alt?`<p class="alt">${esc(alt)}</p>`:""}
          <div class="pmeta"><span>${meta}</span></div>
          ${gt?`<div class="mx-gs">${gt}</div>`:""}
          <div class="pact">${act}${sws}</div>
        </div>
      </div>
      <nav class="mp-tabs" id="mp-body">${T.map((x,i)=>`<button class="mp-tab${i?"":" on"}" data-pt="${x.k}">${x.h}</button>`).join("")}</nav>
      <div class="play">
        <aside class="pside"><div class="pcard mx-mine"><h3>Ma liste</h3>${mineBlock}</div>${side}</aside>
        <div class="mx-main">${T.map((x,i)=>`<div class="mp-pane${i?"":" on"}" data-pane="${x.k}">${x.html}</div>`).join("")}</div>
      </div>
    </div>
    <div id="trbox"></div></div>`;
}
async function showPage(id){
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";
  P.innerHTML='<div class="loading">Chargement…</div>';scrollTo(0,0);
  const [d,f]=await Promise.all([jget("/api/media/"+id),jget("/api/franchise/"+id)]);
  if(location.hash!=="#/m/"+id)return;
  P.innerHTML=pageHtml(id,d,f);cxArrows();P.querySelectorAll("img").forEach(m=>{if(!m.complete)m.addEventListener("load",cxArrows,{once:true})});
  const t=d&&d.title?(d.title.english||d.title.romaji):((DATA.items.find(x=>x.id===id)||{}).title);
  document.title=(t||"Fiche")+" – Ma liste";
  scrollTo(0,0);
}

/* ----- page personnage ----- */
function charDesc(h){
  if(!h)return "<i>Pas de description.</i>";
  h=h.replace(/~![\s\S]*?!~/g,"").replace(/<span[^>]*markdown_spoiler[^>]*>[\s\S]*?<\/span>/gi,"").replace(/__([^_]+?)__/g,"<b>$1</b>");
  return descHtml(h).replace(/(<br>\s*){3,}/g,"<br><br>");
}
const CKEY={race:"Race",species:"Espèce",height:"Taille",weight:"Poids",occupation:"Profession",profession:"Profession",birthday:"Anniversaire",affiliation:"Affiliation",affiliations:"Affiliations",hair:"Cheveux","hair color":"Cheveux",eyes:"Yeux","eye color":"Yeux",status:"Statut",title:"Titre",class:"Classe",rank:"Rang",nationality:"Nationalité",hometown:"Ville natale",birthplace:"Lieu de naissance",family:"Famille",relatives:"Famille",abilities:"Capacités",ability:"Capacité",bust:"Poitrine",waist:"Taille (tour)",hip:"Hanches",sign:"Signe",zodiac:"Signe",likes:"Aime",dislikes:"N'aime pas",hobbies:"Loisirs",hobby:"Loisirs",nickname:"Surnom",nicknames:"Surnoms",alias:"Alias",aliases:"Alias",position:"Poste",school:"École",grade:"Classe",rank:"Rang"};
const ckNorm=k=>k.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z ]/g,"").trim();
const SPO_O="\u0001",SPO_C="\u0002";
const spo=t=>t.split(SPO_O).join('<span class="spo" data-spoi>').split(SPO_C).join("</span>");
/* sort les lignes « Clé : valeur » de la description (race, taille…) ; les spoilers sont gardés, masqués */
function charSplit(h){
  if(!h)return {props:[],rest:"",spoil:false};
  h=h.replace(/<span[^>]*markdown_spoiler[^>]*>(?:<span>)?([\s\S]*?)(?:<\/span>)?<\/span>/gi,SPO_O+"$1"+SPO_C)
     .replace(/~!([\s\S]*?)!~/g,SPO_O+"$1"+SPO_C)
     .replace(/__([^_]+?)__/g,"<b>$1</b>").replace(/\*\*([^*]+?)\*\*/g,"<b>$1</b>")
     .replace(/<\/?p[^>]*>/gi,"<br>").replace(/\r?\n/g,"<br>");
  const lines=h.split(/<br\s*\/?>/i),props=[],rest=[];
  const strip=t=>t.replace(/<[^>]*>/g,"").replace(/&nbsp;/g," ").replace(/\s+/g," ").trim();
  for(const ln of lines){
    const t=strip(ln);
    if(!t){rest.push(ln);continue}
    const m=t.match(/^([^:：\u0001\u0002]{2,28}?)\s*[:：]\s*(.*)$/);
    const boldKey=/^\s*(<[^>]+>\s*)*<(b|strong)>/i.test(ln);
    if(m&&m[1].split(" ").length<=4&&(boldKey||t.length<=100)){
      if(m[2])props.push([m[1],m[2]]);
      continue;
    }
    rest.push(ln);
  }
  return {props,rest:rest.join("<br>"),spoil:h.includes(SPO_O)};
}
const AGE_K=new Set(["age"]),BLOOD_K=new Set(["blood type","blood","groupe sanguin","bloodtype"]),GEN_K=new Set(["gender","sex","genre","sexe"]),BIRTH_K=new Set(["birth","date of birth","naissance"]);
function charHtml(c){
  const sp=charSplit(c.description);
  const take=set=>{const i=sp.props.findIndex(x=>set.has(ckNorm(x[0].replace(/[\u0001\u0002]/g,""))));return i<0?"":sp.props.splice(i,1)[0][1]};
  const pa=take(AGE_K),pb=take(BLOOD_K),pg=take(GEN_K),pbi=take(BIRTH_K);
  const birth=c.birth?[c.birth.d,c.birth.m?MONTHS[c.birth.m-1]:null,c.birth.y].filter(Boolean).join(" "):"";
  const UNK="Unknown";
  const base=[];
  const g=c.gender||pg;if(g)base.push(["Genre",esc(g)]);
  base.push(["Âge",esc(c.age||"")||spo(esc(pa))||UNK]);
  const bi=birth||pbi;if(bi)base.push(["Naissance",esc(bi)]);
  base.push(["Groupe sanguin",esc(c.blood||"")||spo(esc(pb))||UNK]);
  if(c.favourites)base.push(["Favoris",esc(num(c.favourites))]);
  const seen=new Set(base.map(x=>ckNorm(x[0])));
  const extra=[];
  for(const [k0,v] of sp.props){
    const k=k0.replace(/[\u0001\u0002]/g,"").trim(),n=ckNorm(k);
    if(!n||seen.has(n))continue;seen.add(n);
    extra.push([CKEY[n]||(k.charAt(0).toUpperCase()+k.slice(1)),spo(esc(v))]);
  }
  const info=base.concat(extra);
  const altS=(c.alt_spoiler||[]).filter(Boolean);
  const alts=[esc(c.native||"")].concat((c.alt||[]).map(esc)).filter(Boolean).concat(altS.map(a=>spo(SPO_O+esc(a)+SPO_C)));
  const hasSpo=sp.spoil||altS.length||info.some(x=>x[1].includes("data-spoi"));
  const desc=sp.rest?spo(descHtml(sp.rest).replace(/^(\s*<br>)+|(<br>\s*)+$/g,"").replace(/(<br>\s*){3,}/g,"<br><br>")):"";
  const cards=(c.media||[]).map(m=>vcard(m,0).replace("</b>",`</b><span class="role">${esc(ROLE[m.role]||"")}</span>`+(m.va||[]).slice(0,1).map(v=>`<span class="cva"><img src="/img/${esc(v.img||"")}" alt="" ${imgErr}>${esc(v.name)}</span>`).join("")));
  return `<div class="cpg"><button class="back" data-hback>← Retour</button>
    <h1 class="cname">${esc(c.name)}</h1>${alts.length?`<p class="alt">${alts.join(" · ")}</p>`:""}
    <div class="chead"><img class="cphoto" data-zoom data-cap="${esc(c.name)}" src="/img/${esc(c.img||"")}" alt="" ${imgErr}>
      <div class="cinfo"><div class="kpis">${info.map(([k,v])=>`<div><b>${v}</b><span>${esc(k)}</span></div>`).join("")}</div>
        <div class="cdesc">${desc||"<i>Pas de description.</i>"}</div>
        <div class="btns">${favBtn(c.id,true)}${hasSpo?`<button class="btn ghost" data-spo>👁 Voir les spoilers</button>`:""}</div></div></div>
    ${cards.length?`<section class="sec"><h2>Apparitions<small style="color:var(--mut);font-weight:400;font-size:14px;margin-left:8px">${cards.length}</small></h2><div class="vgrid">${cards.join("")}</div></section>`:""}</div>`;
}
async function showChar(id){
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";
  P.innerHTML='<div class="loading">Chargement…</div>';scrollTo(0,0);
  const c=await jget("/api/character/"+id);
  if(location.hash!=="#/c/"+id)return;
  if(!c||!c.id){P.innerHTML=`<div class="cpg"><button class="back" data-hback>← Retour</button><h1>Fiche indisponible</h1><p class="note">Ce personnage n'a pas encore été téléchargé. Lance un rafraîchissement avec internet.</p></div>`;return}
  P.innerHTML=charHtml(c);document.title=c.name+" – Ma liste";scrollTo(0,0);
}

/* ----- catalogue : tous les animés et mangas ----- */
let CTDL={n:5,t:"ANIME",s:"POP",open:false};
let CAT={type:"ALL",q:"",g:"",f:"",l:"",s:"title",n:60},CATD=null,CATY=0,CALY=0,PREV="",CURR="";
function catFmtOpts(){
  const fs=[...new Set(CATD.filter(n=>CAT.type==="ALL"||n.type===CAT.type).map(n=>n.format).filter(Boolean))].sort((a,b)=>fm(FMT,a).localeCompare(fm(FMT,b)));
  if(CAT.f&&!fs.includes(CAT.f))CAT.f="";
  return `<option value="">Tous les formats</option>`+fs.map(x=>`<option value="${esc(x)}"${CAT.f===x?" selected":""}>${esc(fm(FMT,x))}</option>`).join("");
}
function catList(){
  const mine=new Map(DATA.items.map(i=>[i.id,i])),q=CAT.q.trim().toLowerCase();
  const l=CATD.filter(n=>{
    if(CAT.type!=="ALL"&&n.type!==CAT.type)return false;
    if(CAT.g&&!(n.genres||[]).includes(CAT.g))return false;
    if(CAT.f&&n.format!==CAT.f)return false;
    const m=mine.get(n.id);
    if(CAT.l==="TREND"&&!n.tr)return false;
    if(CAT.l==="IN"&&!m)return false;
    if(CAT.l==="OUT"&&m)return false;
    if(CAT.l&&CAT.l!=="IN"&&CAT.l!=="OUT"&&CAT.l!=="TREND"&&(!m||m.status!==CAT.l))return false;
    if(q&&!((n.title||"")+" "+(n.romaji||"")).toLowerCase().includes(q))return false;
    return true;
  });
  const S={title:(a,b)=>a.title.localeCompare(b.title),new:(a,b)=>(b.year||0)-(a.year||0)||a.title.localeCompare(b.title),
    old:(a,b)=>(a.year||9999)-(b.year||9999)||a.title.localeCompare(b.title),score:(a,b)=>(b.avg||0)-(a.avg||0)||a.title.localeCompare(b.title)};
  return l.sort(S[CAT.s]||S.title);
}
function catHtml(){
  const T=[["ALL","Tout"],["ANIME","Animés"],["MANGA","Mangas"]];
  const cnt=k=>k==="ALL"?CATD.length:CATD.filter(n=>n.type===k).length;
  const gset=[...new Set(CATD.flatMap(n=>n.genres||[]))].sort();
  const o=(v,t,c)=>`<option value="${v}"${c===v?" selected":""}>${t}</option>`;
  const dt=CAT.type==="ALL"?CTDL.t:CAT.type;
  return `<div class="catp"><h1>Catalogue</h1><p class="note" id="ct-sub"></p>
    <div class="ctdlh"><button class="btn" data-ctdlt>⬇ Télécharger des titres</button></div>
    <div class="ctdlb${CTDL.open?" on":""}" id="ct-dl"><span>Télécharger</span>
      <input id="dl-n" type="number" min="1" max="200" value="${CTDL.n}">
      <select id="dl-t">${o("ANIME","animés",dt)}${o("MANGA","mangas",dt)}</select>
      <select id="dl-s">${o("POP","les plus populaires",CTDL.s)}${o("SCORE","les mieux notés",CTDL.s)}</select>
      <button class="btn" data-ctdl>Télécharger</button>
      <small>Seuls des titres NOUVEAUX sont comptés (absents de ton catalogue). Leurs autres saisons, films et mangas liés sont téléchargés en plus, avec fiche complète, personnages, staff et images. Ils restent ensuite consultables hors ligne.</small></div>
    <div class="ctbar"><div class="cttyp">${T.map(([k,l])=>`<button class="${CAT.type===k?"on":""}" data-cttype="${k}">${l}<small>${num(cnt(k))}</small></button>`).join("")}</div>
    <div class="ctflt"><input id="ct-q" type="search" placeholder="Rechercher dans le catalogue…" value="${esc(CAT.q)}">
      <select id="ct-g"><option value="">Tous les genres</option>${gset.map(x=>`<option${CAT.g===x?" selected":""}>${esc(x)}</option>`).join("")}</select>
      <select id="ct-f"></select>
      <select id="ct-l">${o("","Tout le catalogue",CAT.l)}${o("TREND","🔥 Tendances de la semaine",CAT.l)}${o("IN","Dans ma liste",CAT.l)}${o("OUT","Pas dans ma liste",CAT.l)}${Object.keys(LS).map(k=>o(k,"Ma liste : "+LS[k],CAT.l)).join("")}</select>
      <select id="ct-s">${o("title","Titre (A → Z)",CAT.s)}${o("new","Année (récents d'abord)",CAT.s)}${o("old","Année (anciens d'abord)",CAT.s)}${o("score","Score moyen",CAT.s)}</select></div></div>
    <div class="vgrid" id="ct-grid"></div><div id="ct-more"></div></div>`;
}
function catDraw(){
  const g=$("#ct-grid");if(!g||!CATD)return;
  const l=catList();
  g.innerHTML=l.slice(0,CAT.n).map(n=>vcard(n,0)).join("");
  $("#ct-sub").textContent=l.length?`${num(l.length)} titre${l.length>1?"s":""}`:"";
  $("#ct-more").innerHTML=l.length>CAT.n?`<button class="btn ghost" data-ctmore>Afficher plus (${num(l.length-CAT.n)})</button>`:(l.length?"":'<p class="note">Aucun résultat pour ces filtres.</p>');
}
async function showCatalogue(){
  const same=CURR==="#/catalogue",y=same?scrollY:CATY;
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";
  document.title="Catalogue – Ma liste";
  const draw=()=>{P.innerHTML=catHtml();$("#ct-f").innerHTML=catFmtOpts();catDraw();scrollTo(0,y)};
  if(CATD){if(!same)draw()}  /* données déjà en mémoire : affichage immédiat, sans écran de chargement */
  else{P.innerHTML='<div class="loading">Chargement…</div>';scrollTo(0,0)}
  const r=await jget("/api/catalogue");  /* mise à jour discrète en arrière-plan */
  if(location.hash!=="#/catalogue")return;
  const had=CATD,fresh=r?r.items:(CATD||[]);
  const sg=a=>a.map(n=>n.id+(n.tr||"")).join();
  const changed=!had||had.length!==fresh.length||sg(had)!==sg(fresh);
  CATD=fresh;
  if(changed)draw();
}
$("#page").addEventListener("click",e=>{
  if(location.hash!=="#/catalogue")return;
  const b=e.target.closest("[data-cttype]");
  if(b){
    CAT.type=b.dataset.cttype;CAT.n=60;
    document.querySelectorAll("[data-cttype]").forEach(x=>x.classList.toggle("on",x===b));
    $("#ct-f").innerHTML=catFmtOpts();catDraw();return;
  }
  if(e.target.closest("[data-ctmore]")){CAT.n+=60;catDraw()}
});
$("#page").addEventListener("click",async e=>{
  if(location.hash!=="#/catalogue")return;
  if(e.target.closest("[data-ctdlt]")){CTDL.open=!CTDL.open;const p=$("#ct-dl");if(p)p.classList.toggle("on",CTDL.open);return}
  const b=e.target.closest("[data-ctdl]");
  if(!b)return;
  const n=Math.round(+$("#dl-n").value),t=$("#dl-t").value,s=$("#dl-s").value;
  if(!(n>=1&&n<=200)){toast("Choisis un nombre entre 1 et 200.");return}
  CTDL.n=n;CTDL.t=t;CTDL.s=s;
  b.disabled=true;
  const r=await post("/api/catalogue/download",{n,type:t,sort:s});
  b.disabled=false;
  if(r&&r.error)toast(r.error);
  else{toast(`Téléchargement de ${n} ${t==="MANGA"?"manga":"animé"}${n>1?"s":""}…`);watch()}
});
$("#page").addEventListener("input",e=>{if(e.target.id==="ct-q"){CAT.q=e.target.value;CAT.n=60;catDraw()}});
$("#page").addEventListener("change",e=>{
  const k={"ct-g":"g","ct-f":"f","ct-l":"l","ct-s":"s"}[e.target.id];
  if(k){CAT[k]=e.target.value;CAT.n=60;catDraw()}
});


/* ----- saisons : précédente / en cours / suivante (téléchargées à chaque changement de saison) ----- */
let SS={k:"",q:"",g:"",f:"",s:"pop",l:"",n:60},SSD=null,SSY=0;
const ssOn=()=>location.hash==="#/saisons";
const SSROLE={next:"Prochaine",cur:"En cours",prev:"Précédente"};
function ssList(){
  const mine=new Map(DATA.items.map(i=>[i.id,i])),q=SS.q.trim().toLowerCase();
  const l=SSD.items.filter(n=>{
    if(SS.g&&!(n.gall||[]).includes(SS.g))return false;
    if(SS.f&&n.format!==SS.f)return false;
    const m=mine.get(n.id);
    if(SS.l==="IN"&&!m)return false;
    if(SS.l==="OUT"&&m)return false;
    if(q&&!((n.title||"")+" "+(n.romaji||"")).toLowerCase().includes(q))return false;
    return true;
  });
  const S={pop:(a,b)=>a.rk-b.rk,title:(a,b)=>a.title.localeCompare(b.title),score:(a,b)=>(b.avg||0)-(a.avg||0)||a.rk-b.rk,
    date:(a,b)=>(a.sd||99999999)-(b.sd||99999999)||a.rk-b.rk};
  return l.sort(S[SS.s]||S.pop);
}
function ssHtml(){
  if(!SSD)return `<div class="ssp"><div class="loading">Chargement…</div></div>`;
  const o=(v,t,c)=>`<option value="${v}"${c===v?" selected":""}>${t}</option>`;
  const ms=SSD.seasons;
  if(!ms.length)return `<div class="ssp"><h1>Saisons</h1><div class="ssbar"><span>${SSD.running?"Téléchargement des saisons en cours…":"Aucune saison téléchargée pour l'instant."}</span><button class="btn ghost sm2" data-ssrf${SSD.running?" disabled":""}>⬇ Télécharger les saisons</button></div></div>`;
  const gset=[...new Set(SSD.items.flatMap(n=>n.gall||[]))].sort();
  const fs=[...new Set(SSD.items.map(n=>n.format).filter(Boolean))].sort((a,b)=>fm(FMT,a).localeCompare(fm(FMT,b)));
  const when=SSD.updated?new Date(SSD.updated*1000).toLocaleDateString("fr-FR",{day:"numeric",month:"long"}):"";
  return `<div class="ssp"><h1>Saisons</h1>
    <div class="ssch">${ms.map(m=>`<button class="${m.key===SSD.sel?"on":""}" data-ssk="${m.key}">${esc(m.label)}${SSROLE[m.role]?`<em>${SSROLE[m.role]}</em>`:""}<small>${num(m.count)}</small></button>`).join("")}</div>
    <div class="ssbar"><span id="ss-sub"></span><span>Tout le contenu de la saison · mis à jour le ${esc(when)} · nouvelle saison téléchargée automatiquement</span><button class="btn ghost sm2" data-ssrf${SSD.running?" disabled":""}>↻ Mettre à jour</button></div>
    <div class="ssflt"><input id="ss-q" type="search" placeholder="Rechercher dans cette saison…" value="${esc(SS.q)}">
      <select id="ss-g"><option value="">Tous les genres</option>${gset.map(x=>`<option${SS.g===x?" selected":""}>${esc(x)}</option>`).join("")}</select>
      <select id="ss-f"><option value="">Tous les formats</option>${fs.map(x=>`<option value="${esc(x)}"${SS.f===x?" selected":""}>${esc(fm(FMT,x))}</option>`).join("")}</select>
      <select id="ss-l">${o("","Tout",SS.l)}${o("IN","Dans ma liste",SS.l)}${o("OUT","Pas dans ma liste",SS.l)}</select>
      <select id="ss-s">${o("pop","Popularité",SS.s)}${o("date","Date de sortie",SS.s)}${o("score","Score moyen",SS.s)}${o("title","Titre (A → Z)",SS.s)}</select></div>
    <div class="vgrid" id="ss-grid"></div><div id="ss-more"></div></div>`;
}
function ssDraw(){
  const g=$("#ss-grid");if(!g||!SSD||!SSD.items)return;
  const l=ssList();
  g.innerHTML=l.slice(0,SS.n).map(n=>vcard(n,0)).join("");
  $("#ss-sub").textContent=`${num(l.length)} titre${l.length>1?"s":""}`+(l.length!==SSD.total?` sur ${num(SSD.total)}`:"");
  $("#ss-more").innerHTML=l.length>SS.n?`<button class="btn ghost" data-ssmore>Afficher plus (${num(l.length-SS.n)})</button>`:(l.length?"":'<p class="note">Aucun résultat pour ces filtres.</p>');
}
async function ssLoad(k){
  const r=await jget("/api/seasons"+(k?"?k="+encodeURIComponent(k):""));
  if(!ssOn())return;
  if(r){SSD=r;SS.k=r.sel||""}else if(!SSD)SSD={seasons:[],items:[],updated:0,running:false,total:0};
  const P=$("#page"),y=scrollY;
  P.innerHTML=ssHtml();ssDraw();scrollTo(0,y);
}
async function showSaisons(){
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";
  document.title="Saisons – Ma liste";
  const y=/^#\/[mc]\//.test(CURR)?SSY:0;
  if(SSD){P.innerHTML=ssHtml();ssDraw();scrollTo(0,y)}
  else{P.innerHTML=ssHtml();scrollTo(0,0)}
  await ssLoad(SS.k);
  if(ssOn()&&y)scrollTo(0,y);
}
$("#page").addEventListener("click",async e=>{
  if(!ssOn())return;
  let b;
  if((b=e.target.closest("[data-ssk]"))){SS.k=b.dataset.ssk;SS.n=60;SS.g="";SS.f="";
    document.querySelectorAll("[data-ssk]").forEach(x=>x.classList.toggle("on",x===b));
    const g=$("#ss-grid");if(g)g.innerHTML='<div class="loading">Chargement…</div>';
    await ssLoad(SS.k);return}
  if(e.target.closest("[data-ssmore]")){SS.n+=60;ssDraw();return}
  if((b=e.target.closest("[data-ssrf]"))){
    b.disabled=true;
    const r=await post("/api/seasons/refresh");
    if(r&&r.error){toast(r.error);b.disabled=false}else{toast("Téléchargement des saisons…");watch()}
  }
});
$("#page").addEventListener("input",e=>{if(ssOn()&&e.target.id==="ss-q"){SS.q=e.target.value;SS.n=60;ssDraw()}});
$("#page").addEventListener("change",e=>{
  if(!ssOn())return;
  const k={"ss-g":"g","ss-f":"f","ss-l":"l","ss-s":"s"}[e.target.id];
  if(k){SS[k]=e.target.value;SS.n=60;ssDraw()}
});

/* ----- accueil : tendances de la semaine (téléchargées par le script, renouvelées chaque semaine) ----- */
let ACD=null,ACI=0,ACY=0,ACS="",PRY=0;
const accOn=()=>location.hash==="#/accueil";
const accSig=r=>r.updated+"|"+r.sections.map(s=>s.items.length+"/"+s.items.filter(x=>x.banner).length).join(",");
function accHeroList(){
  const t=ACD&&ACD.sections.find(s=>s.key==="trending"),all=t?t.items:[];
  const hide=new Set(accContList().map(i=>i.id));   // pas de doublon avec « Continuer à regarder »
  const free=all.filter(x=>!hide.has(x.id)),b=free.filter(x=>x.banner);
  return (b.length>=3?b:free).slice(0,6);
}
function accHero(){
  const l=accHeroList();if(!l.length)return "";
  ACI=((ACI%l.length)+l.length)%l.length;
  const n=l[ACI],t=ACD.sections.find(s=>s.key==="trending"),rank=(t?t.items.findIndex(x=>x.id===n.id):-1)+1;
  const mine=DATA.items.find(x=>x.id===n.id);
  const meta=[fm(FMT,n.format),n.year,(n.genres||[]).join(", "),n.avg?"★ "+(n.avg/10).toFixed(1):""].filter(Boolean).join(" · ");
  const add=mine?`<button class="btn ghost" disabled>✓ ${esc(LS[mine.status]||"Dans ma liste")}</button>`:`<button class="btn ghost" data-acadd="${n.id}">+ À voir</button>`;
  return `<div class="hero2" id="ac-hero"><div class="hbg" style="background-image:url('/img/cover_${n.id}.jpg')"></div>
    <img class="hban" src="/img/banner_${n.id}.jpg" alt="" onerror="this.remove()"><div class="hshade"></div>
    <div class="hc"><div class="hl">🔥 TENDANCE${rank?" N°"+rank:""}</div><h2>${esc(n.title)}</h2><div class="hm">${esc(meta)}</div>
      ${n.desc?`<p class="hs">${esc(n.desc)}</p>`:""}
      <div class="hbt"><a class="btn" href="#/m/${n.id}">▶ Voir la fiche</a>${add}</div></div>
    <img class="hcov" src="/img/cover_${n.id}.jpg" alt="" ${imgErr}>
    ${l.length>1?`<div class="hdots"><button data-acn="-1">‹</button>${l.map((_,k)=>`<i class="${k===ACI?"on":""}" data-acd="${k}"></i>`).join("")}<button data-acn="1">›</button></div>`:""}</div>`;
}
function accHeroDraw(){const el=$("#ac-hero");if(el)el.outerHTML=accHero()}
const accRow=(title,sub,inner)=>`<section><div class="achd"><h2>${title}</h2>${sub?`<small>${sub}</small>`:""}</div>${scrollRow("pscroll",inner)}</section>`;
function accContList(){
  return DATA.items.filter(i=>i.type==="ANIME"&&["CURRENT","REPEATING"].includes(i.status)&&canPlus(i))
    .map(i=>({i,b:behind(i)})).sort((x,y)=>((y.b>0)-(x.b>0))||(y.i.updated-x.i.updated)).slice(0,14).map(x=>x.i);
}
function accCont(){
  const l=accContList();
  if(!l.length)return "";
  return accRow("Continuer à regarder",`${l.length} en cours`,l.map(i=>vcard({id:i.id,type:i.type,format:i.format,year:i.year,count:i.total,avg:i.avg,title:i.title},0)).join(""));
}
function accHtml(){
  if(!ACD)return `<div class="acp"><div class="loading">Chargement…</div></div>`;
  const secs=ACD.sections,wk=(ACD.week||"").split("-W")[1];
  const when=ACD.updated?new Date(ACD.updated*1000).toLocaleDateString("fr-FR",{day:"numeric",month:"long"}):"";
  const bar=`<div class="acbar"><span>${secs.length?`Sélection de la semaine ${esc(wk||"")} · mise à jour le ${esc(when)} · renouvelée automatiquement chaque semaine`:"Aucune tendance téléchargée pour l'instant."}</span><button class="btn ghost sm2" data-acrf${ACD.running?" disabled":""}>${secs.length?"↻ Renouveler":"⬇ Télécharger les tendances"}</button></div>`;
  const seen=new Set(accContList().map(i=>i.id));   // déjà affichés dans « Continuer à regarder »
  const rows=secs.map(s=>{
    const its=s.items.map((n,k)=>({n,k})).filter(x=>!seen.has(x.n.id));   // retire les doublons
    its.forEach(x=>seen.add(x.n.id));                                      // la 1re rangée qui l'affiche « gagne »
    if(!its.length)return "";
    return accRow(esc(s.title),esc(s.sub),its.map(x=>{
      const c=vcard(x.n,0);
      return s.key==="trending"?c.replace('<div class="p">',`<div class="p"><span class="rk">${x.k+1}</span>`):c;
    }).join(""));
  }).join("");
  return `<div class="acp">${accHero()}${bar}${accCont()}${rows}</div>`;
}
function accRedraw(){const P=$("#page"),y=scrollY;P.innerHTML=accHtml();scrollTo(0,y);cxArrows()}
async function showAccueil(){
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";
  document.title="Accueil – Ma liste";
  const y=/^#\/[mc]\//.test(CURR)?ACY:0;
  P.innerHTML=accHtml();scrollTo(0,y);cxArrows();
  const r=await jget("/api/trending");
  if(!accOn())return;
  const sig=r?accSig(r):"";
  if(r){const same=ACD&&accSig(ACD)===sig&&ACS===DATA.updated+"|"+DATA.items.length;ACD=r;ACS=DATA.updated+"|"+DATA.items.length;if(!same){P.innerHTML=accHtml();scrollTo(0,y);cxArrows()}}
  else if(!ACD){ACD={sections:[],updated:0,week:"",running:false};P.innerHTML=accHtml()}
}
setInterval(()=>{if(accOn()&&!document.hidden&&!document.querySelector("#ac-hero:hover")){ACI++;accHeroDraw()}},8000);
$("#page").addEventListener("click",async e=>{
  if(!accOn())return;
  let b;
  if((b=e.target.closest("[data-cxar]"))){const sc=b.parentNode.querySelector(".cxscroll");sc.scrollBy({left:+b.dataset.cxar*sc.clientWidth*.8,behavior:"smooth"});return}
  if((b=e.target.closest("[data-acn]"))){ACI+=+b.dataset.acn;accHeroDraw();return}
  if((b=e.target.closest("[data-acd]"))){ACI=+b.dataset.acd;accHeroDraw();return}
  if((b=e.target.closest("[data-acadd]"))){
    e.preventDefault();b.disabled=true;
    const r=await saveEntry(+b.dataset.acadd,{status:"PLANNING"});
    if(r){toast("Ajouté à ta liste « À voir » ✔");if(accOn())accRedraw()}else b.disabled=false;
    return;
  }
  if((b=e.target.closest("[data-acrf]"))){
    b.disabled=true;
    const r=await post("/api/trending/refresh");
    if(r&&r.error){toast(r.error);b.disabled=false}else{toast("Téléchargement des nouvelles tendances…");watch()}
  }
});

/* ----- calendrier des sorties (refonte v4.4 : style Crunchyroll + AniList) ----- */
let CALV={v:"day",scope:"mine",src:"CUR",off:0,day:null,q:"",plat:"",pop:false};
const CAL_SRC={CUR:["CURRENT","REPEATING"],PLAN:["CURRENT","REPEATING","PLANNING"],ALL:["CURRENT","REPEATING","PLANNING","PAUSED","COMPLETED"]};
const POP_MIN=3000;               // « Populaires » = au moins 3000 personnes l'ont dans leur liste AniList
const SCH={w:{},busy:false,loading:false,err:false};   // programme complet AniList, mis en cache par semaine
const D0=d=>{const x=new Date(d);x.setHours(0,0,0,0);return x};
const addD=(d,n)=>{const x=new Date(d);x.setDate(x.getDate()+n);return x};
const monOf=d=>{const x=D0(d);return addD(x,-((x.getDay()+6)%7))};
const ts=d=>d.getTime()/1000;
const hhmm=t=>new Date(t*1000).toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"});
const cdCore=s=>{s=Math.max(0,Math.floor(s));const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?d+" j "+h+" h":h?h+" h":Math.max(1,m)+" min"};   // ex. « 4 j 4 h » (sans minutes ni secondes)
function inT(t){return "dans "+cdCore(t-Date.now()/1000)}
const cdTxt=s=>cdCore(s);
const dayName=(d,long)=>{
  const t=D0(new Date()),diff=Math.round((D0(d)-t)/864e5),lab=d.toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long"});
  return long&&diff===0?"Aujourd'hui · "+lab:long&&diff===1?"Demain · "+lab:lab;
};
const dayShort=t=>new Date(t*1000).toLocaleDateString("fr-FR",{weekday:"short",day:"numeric"});
const fmtL=f=>FMT[f]||nice(f)||"";
/* rangée défilante : pas de barre grise, de belles flèches à la place */
const CXL='<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>';
const CXR='<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>';
const scrollRow=(cls,inner,extra)=>`<div class="cxwrap${extra?" "+extra:""}"><button class="cxar l off" data-cxar="-1" aria-label="Précédent">${CXL}</button><div class="cxscroll ${cls}">${inner}</div><button class="cxar r off" data-cxar="1" aria-label="Suivant">${CXR}</button></div>`;

/* ---- événements : ma liste (calculés chaque semaine depuis le prochain épisode annoncé) ---- */
function mkMine(i,n,at){return {id:i.id,title:i.title,ep:n,at,total:i.total,fmt:i.format,genres:i.genres||[],score:i.avg,pop:0,studio:"",plat:[],mine:i,img:"/img/"+i.img,fb:"",url:"#/m/"+i.id,ext:false}}
function mineEvents(t0,t1,src){
  const inc=CAL_SRC[src||CALV.src]||CAL_SRC.CUR,ev=[];
  for(const i of DATA.items){
    if(i.type!=="ANIME"||!inc.includes(i.status)||!i.next_at||!i.next_ep)continue;
    const a=Math.max(1,Math.ceil(i.next_ep+(t0-i.next_at)/WEEK));let b=Math.floor(i.next_ep+(t1-1-i.next_at)/WEEK);
    if(i.total)b=Math.min(b,i.total);
    for(let n=a;n<=b;n++)ev.push(mkMine(i,n,i.next_at+(n-i.next_ep)*WEEK));
  }
  return ev;
}
/* ---- événements : programme complet AniList ---- */
function schedEvents(t0,t1){
  const mine=new Map(DATA.items.map(i=>[i.id,i])),ev=[];
  for(const k in SCH.w)for(const s of SCH.w[k].items){
    if(s.at<t0||s.at>=t1)continue;
    const i=mine.get(s.id),m=i&&i.type==="ANIME"?i:null;
    ev.push({id:s.id,title:m?m.title:s.title,ep:s.ep,at:s.at,total:s.total||(m&&m.total)||null,fmt:s.fmt,genres:s.genres||[],score:s.score,pop:s.pop||0,studio:s.studio||"",plat:s.plat||[],mine:m,img:m?"/img/"+m.img:"/img/"+s.img,fb:s.cover||"",url:m?"#/m/"+s.id:s.url,ext:!m});
  }
  return ev;
}
function filt(ev){
  const q=CALV.q.trim().toLowerCase();
  return ev.filter(e=>{
    if(q&&!(e.title.toLowerCase().includes(q)||(e.mine&&(e.mine.romaji||"").toLowerCase().includes(q))))return false;
    if(CALV.scope==="all"){
      if(CALV.plat&&!e.plat.includes(CALV.plat))return false;
      if(CALV.pop&&!e.mine&&e.pop<POP_MIN)return false;
    }
    return true;
  });
}
function calEvents(t0,t1){
  const ev=filt(CALV.scope==="all"?schedEvents(t0,t1):mineEvents(t0,t1));
  return ev.sort((x,y)=>x.at-y.at||(!!y.mine-!!x.mine)||y.pop-x.pop||x.title.localeCompare(y.title));
}
const evState=e=>e.mine&&e.ep<=e.mine.progress?["ok","✓ Vu"]:e.at<=Date.now()/1000?(e.mine?["late","À voir"]:["out","Sorti"]):["soon",inT(e.at)];

/* ---- briques d'affichage ---- */
function cxFb(el){const f=el.dataset.fb;if(f&&!el.dataset.t){el.dataset.t=1;el.src=f}else el.style.visibility="hidden"}
const cimg=e=>`<img loading="lazy" decoding="async" src="${esc(e.img)}" data-fb="${esc(e.fb||"")}" alt="" onerror="cxFb(this)">`;
const lnk=e=>e.ext?`href="${esc(e.url||"#")}" target="_blank" rel="noopener"`:`href="${esc(e.url)}"`;
const stAt=(e,st)=>st[0]==="soon"?` data-at="${e.at}"`:"";
const platChips=e=>[...e.plat].sort((a,b)=>(b==="Crunchyroll")-(a==="Crunchyroll")).slice(0,2).map(x=>`<span class="cxpl${x==="Crunchyroll"?" cr":""}">${esc(x)}</span>`).join("");
function acts(e,st){
  if(e.mine)return st[0]==="late"&&e.ep===e.mine.progress+1?`<button class="cxb1" data-calbump="${e.id}" title="Marquer l'épisode ${e.ep} comme vu">+1 vu</button>`:"";
  return e.ext?`<button class="cxb2" data-caladd="${e.id}" title="Ajouter à ma liste (À voir)">＋ Ma liste</button>`:"";
}
function emptyBox(txt){
  if(CALV.scope==="all"&&SCH.loading)return '<div class="cxsk"></div>';
  return `<p class="cxe">${esc(txt)}${CALV.scope==="mine"?' <a href="#" data-calscope="all">Voir tout le programme</a>':""}</p>`;
}
/* carte large (vue Jour / détail du mois) */
function rowCard(e){
  const st=evState(e),i=e.mine,pg=i&&i.total?Math.min(100,i.progress/i.total*100):0;
  const meta=[fmtL(e.fmt),e.studio].filter(Boolean).join(" · ")+(e.score?` · ★ ${(e.score/10).toFixed(1)}`:"");
  return `<article class="cxr ${st[0]}"><a class="cxp" ${lnk(e)}>${cimg(e)}${i?`<span class="cxmine" title="Dans ma liste : ${esc(LS[i.status]||"")}">♥</span>`:""}</a>
<div class="cxbd"><div class="cxtop"><span class="cxep">Épisode ${e.ep}${e.total?" / "+e.total:""}</span><span class="cxst ${st[0]}"${stAt(e,st)}>${esc(st[1])}</span></div>
<a class="cxn" ${lnk(e)}>${esc(e.title)}</a>${meta?`<div class="cxm">${esc(meta)}</div>`:""}
<div class="cxg">${e.genres.slice(0,2).map(g=>`<span>${esc(g)}</span>`).join("")}${platChips(e)}</div>
<div class="cxfoot"><span class="cxtm">${hhmm(e.at)}</span>${pg?`<span class="cxpg" title="Ma progression : ${i.progress}/${i.total}"><i style="width:${pg}%"></i></span>`:""}${acts(e,st)}</div></div></article>`;
}
/* carte affiche (vue Semaine / rattrapage) */
function posterCard(e){
  const st=evState(e),i=e.mine;
  return `<div class="cxs ${st[0]}"><a class="cxsp" ${lnk(e)}>${cimg(e)}<span class="cxtime">${hhmm(e.at)}</span>${i?'<span class="cxmine">♥</span>':""}<span class="cxsep">Ép. ${e.ep}${e.total?" / "+e.total:""}</span><span class="cxsbar ${st[0]}"></span></a>
<a class="cxsn" ${lnk(e)} title="${esc(e.title)}">${esc(e.title)}</a><div class="cxsf"><span class="cxst ${st[0]}"${stAt(e,st)}>${esc(st[1])}</span>${acts(e,st)}</div></div>`;
}

/* ---- période affichée ---- */
function calRange(){
  const today=D0(new Date());
  if(CALV.v==="month"){const f=new Date(today.getFullYear(),today.getMonth()+CALV.off,1),last=new Date(f.getFullYear(),f.getMonth()+1,0);return {a:monOf(f),b:addD(monOf(last),7),f}}
  const a=addD(monOf(today),CALV.off*7);return {a,b:addD(a,7)};
}
function calLabel(r){
  const f=(d,o)=>d.toLocaleDateString("fr-FR",o);
  if(CALV.v==="month")return f(r.f,{month:"long",year:"numeric"});
  return f(r.a,{day:"numeric",month:"short"})+" – "+f(addD(r.b,-1),{day:"numeric",month:"short",year:"numeric"});
}

/* ---- vues ---- */
function timeline(es,isToday){
  if(!es.length)return emptyBox("Aucune sortie ce jour-là.");
  const now=Date.now()/1000,slots=[];
  es.forEach(e=>{const h=new Date(e.at*1000).getHours();let s=slots[slots.length-1];if(!s||s.h!==h){s={h,es:[]};slots.push(s)}s.es.push(e)});
  let out="",marked=!isToday;
  const mark=`<div class="cxnow"><span>Maintenant · ${hhmm(now)}</span></div>`;
  for(const s of slots){
    if(!marked&&s.es[0].at>now){out+=mark;marked=true}
    out+=`<section class="cxslot${s.es.every(e=>e.at<=now)?" past":""}"><div class="cxsl"><b>${String(s.h).padStart(2,"0")}:00</b><small>${s.es.length} ép.</small></div><div class="cxsg">${s.es.map(rowCard).join("")}</div></section>`;
  }
  if(!marked)out+=mark;
  return `<div class="cxtl">${out}</div>`;
}
function viewDay(r,by){
  const today=dkey(Date.now()/1000),keys=Array.from({length:7},(_,k)=>dkey(ts(addD(r.a,k))));
  if(!CALV.day||!keys.includes(CALV.day))CALV.day=keys.includes(today)?today:keys[0];
  const tabs=keys.map((key,k)=>{
    const d=addD(r.a,k),es=by[key]||[],hot=es.some(e=>evState(e)[0]==="late");
    return `<button class="cxd${key===CALV.day?" on":""}${key===today?" today":""}" data-calday="${key}"><small>${d.toLocaleDateString("fr-FR",{weekday:"short"})}</small><b>${d.getDate()}</b><i${hot?' class="hot"':""}>${es.length}</i></button>`}).join("");
  const es=by[CALV.day]||[];
  return `<div class="cxdays">${tabs}</div><h2 class="cxdh cxdd">${esc(dayName(new Date(CALV.day+"T12:00:00"),true))}<small>${es.length} sortie${es.length>1?"s":""}</small></h2>${timeline(es,CALV.day===today)}`;
}
function viewWeek(r,by){
  const today=dkey(Date.now()/1000);
  return `<div class="cxw">${Array.from({length:7},(_,k)=>{
    const d=addD(r.a,k),key=dkey(ts(d)),es=by[key]||[];
    return `<section class="cxcol${key===today?" today":""}"><header><span>${d.toLocaleDateString("fr-FR",{weekday:"long"})}</span><b>${d.getDate()}</b><small>${es.length?es.length+" sortie"+(es.length>1?"s":""):""}</small></header>${scrollRow("cxlist",es.length?es.map(posterCard).join(""):emptyBox("Aucune sortie"),"cxwl")}</section>`}).join("")}</div>`;
}
function viewMonth(r,by){
  const today=dkey(Date.now()/1000),ym=dkey(ts(r.f)).slice(0,7);
  const sel=CALV.day||(today.slice(0,7)===ym?today:null);
  const names=Array.from({length:7},(_,k)=>`<span>${addD(r.a,k).toLocaleDateString("fr-FR",{weekday:"short"})}</span>`).join("");
  let cells="";
  for(let d=r.a;d<r.b;d=addD(d,1)){
    const key=dkey(ts(d)),es=by[key]||[];
    const top=es.slice().sort((x,y)=>(!!y.mine-!!x.mine)||y.pop-x.pop).slice(0,4);
    cells+=`<div class="cxmc${key.slice(0,7)!==ym?" out":""}${key===today?" today":""}${key===sel?" sel":""}" data-calday="${key}"><span class="cxmn">${d.getDate()}</span><div class="cxmz">${top.map(e=>`<span class="cxmi ${evState(e)[0]}" title="${esc(e.title)}">${cimg(e)}</span>`).join("")}</div>${es.length>4?`<span class="cxmm">+${es.length-4} autres</span>`:""}${es.length?`<span class="cxmcnt">${es.length}</span>`:""}</div>`;
  }
  const es=sel?by[sel]||[]:[];
  const det=sel?`<h2 class="cxdh cxdd">${esc(dayName(new Date(sel+"T12:00:00"),true))}<small>${es.length} sortie${es.length>1?"s":""}</small></h2>${es.length?`<div class="cxgrid">${es.map(rowCard).join("")}</div>`:emptyBox("Aucune sortie ce jour-là.")}`:"";
  return `<div class="cxmh">${names}</div><div class="cxmg">${cells}</div>${det}`;
}
function calBody(){
  const r=calRange(),by={};
  calEvents(ts(r.a),ts(r.b)).forEach(e=>{const k=dkey(e.at);(by[k]=by[k]||[]).push(e)});
  const hasAny=Object.keys(by).length>0;
  if(CALV.scope==="all"&&SCH.err&&!SCH.loading&&!hasAny)
    return '<p class="cxerr">Le programme AniList est indisponible pour le moment (connexion ?). <button class="btn ghost sm2" data-calretry>Réessayer</button></p>';
  return CALV.v==="month"?viewMonth(r,by):CALV.v==="week"?viewWeek(r,by):viewDay(r,by);
}

/* ---- bandeau « prochaine sortie », rattrapage, barre d'outils ---- */
function heroHtml(){
  const now=Date.now()/1000,up=mineEvents(now,now+21*86400,"CUR").filter(e=>e.at>now).sort((a,b)=>a.at-b.at);
  if(!up.length)return "";
  const e=up[0],i=e.mine,nx=up.slice(1,5),d=new Date(e.at*1000);
  return `<section class="cxh"><img class="cxhb" src="/img/banner_${i.id}.jpg" alt="" onerror="this.remove()"><div class="cxhs"></div>
<a class="cxhp" href="#/m/${i.id}"><img src="/img/${esc(i.img)}" alt="" ${imgErr}></a>
<div class="cxhi"><span class="cxk">Prochaine sortie</span><h2>${esc(i.title)}</h2>
<p>Épisode ${e.ep}${i.total?" / "+i.total:""} · ${esc(d.toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long"}))} à ${hhmm(e.at)}</p>
<div class="cxcd" data-cd="${e.at}">${cdTxt(e.at-now)}</div><a class="btn" href="#/m/${i.id}">Voir la fiche</a></div>
${nx.length?`<aside class="cxhn"><span class="cxk">Ensuite</span>${nx.map(n=>`<a href="#/m/${n.id}"><img src="/img/${esc(n.mine.img)}" alt="" ${imgErr}><span><b>${esc(n.title)}</b><small>Ép. ${n.ep} · ${esc(dayShort(n.at))} · ${hhmm(n.at)}</small></span></a>`).join("")}</aside>`:""}</section>`;
}
function lateHtml(){
  const lates=DATA.items.filter(i=>i.type==="ANIME"&&["CURRENT","REPEATING"].includes(i.status)&&(behind(i)||0)>0).sort((a,b)=>behind(b)-behind(a));
  if(!lates.length)return "";
  const nb=lates.reduce((s,i)=>s+behind(i),0);
  return `<section><h2 class="cxdh">À rattraper<small>${nb} épisode${nb>1?"s":""} · ${lates.length} titre${lates.length>1?"s":""}</small></h2>${scrollRow("cxstrip",lates.map(i=>`<div class="cxs late"><a class="cxsp" href="#/m/${i.id}"><img loading="lazy" src="/img/${esc(i.img)}" alt="" ${imgErr}><span class="cxtime">Ép. ${i.progress+1}</span><span class="cxsep">−${behind(i)} ép. de retard</span><span class="cxsbar late"></span></a><a class="cxsn" href="#/m/${i.id}" title="${esc(i.title)}">${esc(i.title)}</a><div class="cxsf"><span class="cxst late">Vu : ${i.progress}</span><button class="cxb1" data-calbump="${i.id}" title="Marquer l'épisode ${i.progress+1} comme vu">+1 vu</button></div></div>`).join(""))}</section>`;
}
function pillsHtml(){
  const t0=D0(new Date()),now=Date.now()/1000,wk=monOf(t0);
  const tE=mineEvents(ts(t0),ts(addD(t0,1)),"CUR"),wE=mineEvents(ts(wk),ts(addD(wk,7)),"CUR");
  const toSee=tE.filter(e=>e.at<=now&&e.ep>e.mine.progress).length;
  return `<div class="cxpills"><span><b>${tE.length}</b> aujourd'hui${toSee?` · <em>${toSee} à voir</em>`:""}</span><span><b>${wE.length}</b> cette semaine</span></div>`;
}
function platOpts(){
  const c={};
  for(const k in SCH.w)for(const s of SCH.w[k].items)for(const p of s.plat||[])c[p]=(c[p]||0)+1;
  const names=Object.keys(c).sort((a,b)=>(b==="Crunchyroll")-(a==="Crunchyroll")||c[b]-c[a]).slice(0,16);
  if(CALV.plat&&!names.includes(CALV.plat))names.push(CALV.plat);
  return '<option value="">Toutes les plateformes</option>'+names.map(n=>`<option value="${esc(n)}"${CALV.plat===n?" selected":""}>${esc(n)}</option>`).join("");
}
function statusText(){
  if(CALV.scope==="all")return SCH.loading?"⏳ Chargement du programme AniList…":SCH.err?"⚠ Programme incomplet (connexion ?)":"Programme complet AniList · tous les animés diffusés";
  const upd=DATA.airing_updated?new Date(DATA.airing_updated*1000).toLocaleString("fr-FR",{dateStyle:"short",timeStyle:"short"}):"jamais";
  return "Horaires de ma liste mis à jour le "+upd;
}
function toolbarHtml(r){
  const tg=(arr,cur,attr)=>arr.map(([k,l])=>`<button class="${cur===k?"on":""}" data-${attr}="${k}">${l}</button>`).join("");
  const so=[["CUR","En cours"],["PLAN","En cours + À voir"],["ALL","Toute ma liste"]].map(([k,l])=>`<option value="${k}"${CALV.src===k?" selected":""}>${l}</option>`).join("");
  const filters=CALV.scope==="all"
    ?`<select id="cx-plat" title="Plateforme de streaming">${platOpts()}</select><button class="cxchip${CALV.pop?" on":""}" data-calpop title="Masquer les titres peu suivis">★ Populaires</button>`
    :`<select id="cl-src" title="Animés affichés">${so}</select>`;
  return `<div class="cxbar"><div class="cxr1"><div class="tog">${tg([["day","Jour"],["week","Semaine"],["month","Mois"]],CALV.v,"calv")}</div>
<div class="cxnav"><button class="btn ghost sm2" data-calnav="-1" title="Précédent">‹</button><button class="btn ghost sm2" data-calnav="0">Aujourd'hui</button><button class="btn ghost sm2" data-calnav="1" title="Suivant">›</button><b class="cxlab">${esc(calLabel(r))}</b></div>
<span class="sp"></span><div class="tog">${tg([["mine","Ma liste"],["all","Tout le programme"]],CALV.scope,"calscope")}</div></div>
<div class="cxr2"><input id="cx-q" type="search" placeholder="Rechercher un animé…" value="${esc(CALV.q)}">${filters}<span class="cxstat" id="cx-stat">${esc(statusText())}</span><button class="btn ghost sm2" data-airing title="Actualiser les horaires">↻ Actualiser</button></div></div>`;
}
function calHtml(){
  const r=calRange();
  return `<div class="cx"><div class="cxhd"><h1>Calendrier</h1>${pillsHtml()}</div>${heroHtml()}${lateHtml()}${toolbarHtml(r)}<div id="cx-body">${calBody()}</div></div>`;
}
const onCal=()=>location.hash==="#/cal";
function fullRedraw(){if(!onCal())return;const y=scrollY;$("#page").innerHTML=calHtml();scrollTo(0,y);cxTick()}
function cxBody(){
  if(!onCal())return;const b=$("#cx-body");if(!b)return;
  const y=scrollY;b.innerHTML=calBody();scrollTo(0,y);
  const s=$("#cx-stat");if(s)s.textContent=statusText();
  const p=$("#cx-plat");if(p)p.innerHTML=platOpts();
  cxTick();
}
function cxArrows(){
  document.querySelectorAll(".cxwrap").forEach(w=>{
    const sc=w.querySelector(".cxscroll"),l=w.querySelector(".cxar.l"),r=w.querySelector(".cxar.r");
    if(!sc||!l||!r)return;
    const can=sc.scrollWidth>sc.clientWidth+2;
    l.classList.toggle("off",!can||sc.scrollLeft<=2);
    r.classList.toggle("off",!can||sc.scrollLeft+sc.clientWidth>=sc.scrollWidth-2);
  });
}
/* compte à rebours en direct + états « dans X min » */
function cxTick(){
  if(!onCal())return;
  const now=Date.now()/1000;let stale=false;
  document.querySelectorAll(".cxcd[data-cd]").forEach(el=>{
    const s=+el.dataset.cd-now;
    if(s>0)el.textContent=cdTxt(s);
    else if(!el.dataset.done){el.dataset.done=1;el.textContent="Disponible !";setTimeout(fullRedraw,4000)}
  });
  document.querySelectorAll(".cxst[data-at]").forEach(el=>{if(+el.dataset.at<=now)stale=true;else el.textContent=inT(+el.dataset.at)});
  if(stale)cxBody();
  cxArrows();
}
setInterval(()=>{if(onCal()&&!document.hidden)cxTick()},1000);

/* ---- chargement du programme complet (semaine par semaine, depuis le serveur local) ---- */
async function schedLoad(force){
  if(CALV.scope!=="all"||SCH.busy)return;
  const r=calRange(),sig=CALV.v+CALV.off,now=Date.now()/1000,need=[];
  for(let d=r.a;d<r.b;d=addD(d,7)){const w=SCH.w[ts(d)];if(force||!w||(w.end>now&&now-w.at>3*3600))need.push(d)}
  if(!need.length){SCH.loading=false;cxBody();return}
  SCH.busy=true;SCH.loading=true;SCH.err=false;cxBody();
  for(const d of need){
    const a=ts(d),b=ts(addD(d,7)),j=await jget(`/api/schedule?from=${a}&to=${b}${force?"&force=1":""}`);
    if(!onCal())break;
    if(j&&j.items)SCH.w[a]={items:j.items,at:j.at,end:b};else SCH.err=true;
    cxBody();
  }
  SCH.busy=false;SCH.loading=false;cxBody();
  if(onCal()&&CALV.scope==="all"&&!SCH.err&&sig!==CALV.v+CALV.off)schedLoad();   // la période a changé pendant le chargement
}

/* ---- interactions ---- */
document.addEventListener("scroll",e=>{if((onCal()||accOn()||location.hash==="#/profil"||/^#\/m\//.test(location.hash))&&e.target.classList&&e.target.classList.contains("cxscroll"))cxArrows()},true);
addEventListener("resize",()=>{if(onCal()||accOn()||location.hash==="#/profil"||/^#\/m\//.test(location.hash))cxArrows()});
$("#page").addEventListener("click",async e=>{
  if(!onCal())return;
  let b;
  if((b=e.target.closest("[data-cxar]"))){const sc=b.parentNode.querySelector(".cxscroll");sc.scrollBy({left:+b.dataset.cxar*sc.clientWidth*.8,behavior:"smooth"});return}
  if((b=e.target.closest("[data-calv]"))){CALV.v=b.dataset.calv;CALV.off=0;CALV.day=null;fullRedraw();schedLoad();return}
  if((b=e.target.closest("[data-calscope]"))){e.preventDefault();CALV.scope=b.dataset.calscope;CALV.day=null;fullRedraw();schedLoad();return}
  if((b=e.target.closest("[data-calnav]"))){const n=+b.dataset.calnav;CALV.off=n?CALV.off+n:0;CALV.day=null;fullRedraw();schedLoad();return}
  if((b=e.target.closest("[data-calday]"))){const k=b.dataset.calday;CALV.day=CALV.v==="month"&&CALV.day===k?null:k;cxBody();return}
  if((b=e.target.closest("[data-calpop]"))){CALV.pop=!CALV.pop;b.classList.toggle("on",CALV.pop);cxBody();return}
  if((b=e.target.closest("[data-calretry]"))){SCH.err=false;schedLoad();return}
  if((b=e.target.closest("[data-calbump]"))){e.preventDefault();b.disabled=true;await bump(+b.dataset.calbump,1);fullRedraw();return}
  if((b=e.target.closest("[data-caladd]"))){
    e.preventDefault();b.disabled=true;
    const r=await saveEntry(+b.dataset.caladd,{status:"PLANNING"});
    if(r){toast("Ajouté à ta liste « À voir » ✔");fullRedraw()}else b.disabled=false;
  }
});
$("#page").addEventListener("input",e=>{if(e.target.id==="cx-q"&&onCal()){CALV.q=e.target.value;cxBody()}});
$("#page").addEventListener("change",e=>{
  if(!onCal())return;
  if(e.target.id==="cl-src"){CALV.src=e.target.value;cxBody()}
  else if(e.target.id==="cx-plat"){CALV.plat=e.target.value;cxBody()}
});
function showCal(){
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";P.innerHTML=calHtml();scrollTo(0,/^#\/[mc]\//.test(CURR)?CALY:0);
  document.title="Calendrier – Ma liste";cxTick();
  if(Date.now()/1000-(DATA.airing_updated||0)>3600)refreshAiring(true);
  schedLoad();
}
async function refreshAiring(quiet){
  const r=await post("/api/airing");
  if(r.error){if(!quiet)toast(r.error);return}
  await load();
  if(!onCal())return;
  fullRedraw();
  if(!quiet){toast("Horaires mis à jour ✔");schedLoad(true)}
}

/* ----- profil (interactif) ----- */
let PF={tab:"ov",ovt:"ANIME",type:"ANIME",grp:"genres",metric:"n",all:false,act:"ALL",day:null,actN:60,fq:"",fk:"anime"};
let PD=null,PX={},DR={},DRN=0,DRC=null,DRS="score";
const STORDER=["CURRENT","REPEATING","COMPLETED","PAUSED","DROPPED","PLANNING"];
const STCOL={CURRENT:"#7bd555",REPEATING:"#9256f3",COMPLETED:"#3db4f2",PAUSED:"#f79a63",DROPPED:"#e85d75",PLANNING:"#c063ff"};
const ACTV={"watched episode":"Épisode","read chapter":"Chapitre","rewatched episode":"Épisode revu","reread chapter":"Chapitre relu","plans to watch":"Prévu à voir","plans to read":"Prévu à lire","completed":"Terminé","dropped":"Abandonné","paused watching":"Mis en pause","paused reading":"Mis en pause","rewatched":"Revu en entier","reread":"Relu en entier"};
const LEN={
  ANIME:[[1,"1 épisode"],[6,"2–6 ép."],[13,"7–13 ép."],[26,"14–26 ép."],[52,"27–52 ép."],[100,"53–100 ép."],[1e9,"100+ ép."]],
  MANGA:[[1,"1 chapitre"],[10,"2–10 chap."],[30,"11–30 chap."],[60,"31–60 chap."],[100,"61–100 chap."],[200,"101–200 chap."],[1e9,"200+ chap."]]};
const dkey=t=>{const d=new Date(t*1000);return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")};
const dreg=(title,items)=>{const k="d"+(++DRN);DR[k]={title,ids:items.map(i=>i.id)};return k};
const pmins=i=>i.type==="ANIME"?i.progress*(((PX[i.id]||{}).dur)||24):0;
const durF=m=>m>=1440?(m/1440).toFixed(1).replace(".",",")+" j":m>=60?Math.round(m/60)+" h":Math.round(m)+" min";
const f2=x=>x.toFixed(2).replace(".",",");
const lenLabel=i=>{const n=i.total;if(!n)return "Inconnue";return LEN[i.type].find(b=>n<=b[0])[1]};
const profOf=()=>(PD&&PD.profile)||{};

function pstats(list){
  const sc=list.filter(i=>i.score>0).map(i=>i.score);
  const mean=sc.length?sc.reduce((a,b)=>a+b,0)/sc.length:0;
  const sd=sc.length?Math.sqrt(sc.reduce((a,b)=>a+(b-mean)*(b-mean),0)/sc.length):0;
  return {n:list.length,units:list.reduce((a,i)=>a+i.progress,0),mins:list.reduce((a,i)=>a+pmins(i),0),mean,sd,sc:sc.length};
}
function agg(list,keys){
  const m=new Map();
  for(const i of list){
    for(const k of new Set(keys(i)||[])){
      if(k==null||k==="")continue;
      let a=m.get(k);if(!a){a={k,items:[],n:0,sum:0,sn:0,t:0};m.set(k,a)}
      a.items.push(i);a.n++;if(i.score>0){a.sum+=i.score;a.sn++}
      a.t+=i.type==="ANIME"?pmins(i):i.progress;
    }
  }
  return [...m.values()].map(a=>({...a,mean:a.sn?a.sum/a.sn:0}));
}
function bucket(list,fn){const m={};list.forEach(i=>{const k=fn(i);if(k!=null&&k!=="")(m[k]=m[k]||[]).push(i)});return m}
const rowsOf=m=>Object.entries(m).map(([label,items])=>({label,items})).sort((a,b)=>b.items.length-a.items.length);

/* bio : on garde un HTML très restreint (pas d'images, liens http(s) uniquement) */
function aboutHtml(h){
  const ok=/^(br|p|b|i|em|strong|u|s|center|h[1-6]|ul|ol|li|blockquote|code|pre|hr|div|span)$/i;
  return String(h).replace(/<(script|style|iframe)[\s\S]*?<\/\1>/gi,"").split(/(<[^>]*>)/).map(p=>{
    if(!p.startsWith("<"))return p.replace(/</g,"&lt;").replace(/>/g,"&gt;");
    const m=p.match(/^<(\/?)([a-z0-9]+)([^>]*)>$/i);if(!m)return "";
    const t=m[2].toLowerCase();
    if(t==="a"){
      if(m[1])return "</a>";
      const href=m[3].match(/href=["'](https?:\/\/[^"']+)["']/i);
      return href?`<a href="${href[1]}" target="_blank" rel="noopener">`:"<a>";
    }
    return ok.test(t)?`<${m[1]}${t}>`:"";
  }).join("");
}

/* ----- briques de graphiques (tout est cliquable : ouvre la liste des titres) ----- */
function kpiRow(type,list){
  const A=type==="ANIME",s=pstats(list),off=(profOf().official||{})[A?"anime":"manga"]||{};
  const k=(v,l)=>`<div><b>${v}</b><span>${l}</span></div>`;
  return `<div class="kpis">${k(num(s.n),A?"Animés":"Mangas")}${k(num(s.units),A?"Épisodes vus":"Chapitres lus")}${A?k(durF(s.mins),"Temps de visionnage"):(off.volumesRead?k(num(off.volumesRead),"Volumes lus"):"")}${k(s.sc?f2(s.mean):"—","Note moyenne")}${k(s.sc?f2(s.sd):"—","Écart-type")}</div>`;
}
function statusBar(list){
  const seg=STORDER.map(s=>({s,items:list.filter(i=>i.status===s)})).filter(x=>x.items.length);
  if(!seg.length)return `<p class="note">Aucune entrée.</p>`;
  seg.forEach(x=>{x.k=dreg(LS[x.s],x.items)});
  return `<div class="seg">${seg.map(x=>`<button style="flex:${x.items.length};background:${STCOL[x.s]}" data-dr="${x.k}" title="${esc(LS[x.s])} : ${x.items.length}"></button>`).join("")}</div>
  <div class="leg">${seg.map(x=>`<button data-dr="${x.k}"><i style="background:${STCOL[x.s]}"></i>${esc(LS[x.s])} <b>${x.items.length}</b> <small>${Math.round(x.items.length/list.length*100)}%</small></button>`).join("")}</div>`;
}
function barList(rows){
  rows=rows.filter(r=>r.items.length);
  if(!rows.length)return `<p class="note">Pas de données (fiches détaillées non téléchargées ?).</p>`;
  const mx=Math.max(...rows.map(r=>r.items.length));
  return `<div class="pbl">${rows.map(r=>`<button data-dr="${dreg(r.label,r.items)}"><span class="pl" title="${esc(r.label)}">${esc(r.label)}</span><span class="pt"><u style="width:${Math.max(3,r.items.length/mx*100)}%"></u></span><b>${r.items.length}</b></button>`).join("")}</div>`;
}
function colChart(rows,tt){
  if(!rows.some(r=>r.items.length))return `<p class="note">Pas de données.</p>`;
  const mx=Math.max(1,...rows.map(r=>r.items.length));
  return `<div class="pcol">${rows.map(r=>{
    const c=r.items.length,h=`<b>${c||""}</b><div class="bw"><i style="height:${Math.round(c/mx*100)}%"></i></div><span>${esc(r.label)}</span>`;
    return c?`<button class="pc" data-dr="${dreg(tt(r.label),r.items)}" title="${esc(r.label)} : ${c}">${h}</button>`:`<div class="pc">${h}</div>`;
  }).join("")}</div>`;
}
function groupTable(list,A){
  const gs=A?[["genres","Genres"],["tags","Tags"],["studios","Studios"],["staff","Staff"]]:[["genres","Genres"],["tags","Tags"],["staff","Staff"]];
  if(!gs.some(g=>g[0]===PF.grp))PF.grp="genres";
  const KF={genres:i=>i.genres,tags:i=>(PX[i.id]||{}).tags,studios:i=>(PX[i.id]||{}).studios,staff:i=>(PX[i.id]||{}).staff};
  const rows=agg(list,KF[PF.grp]);
  const SO={n:(a,b)=>b.n-a.n||b.mean-a.mean,mean:(a,b)=>b.mean-a.mean||b.n-a.n,t:(a,b)=>b.t-a.t||b.n-a.n};
  rows.sort(SO[PF.metric]||SO.n);
  const total=rows.length,shown=PF.all?rows:rows.slice(0,15);
  const th=(m,l)=>`<button class="th${PF.metric===m?" on":""}" data-pfm="${m}">${l}${PF.metric===m?" ▾":""}</button>`;
  const tl=A?durF:(n=>num(n)+" chap.");
  const tabs=`<div class="tog">${gs.map(([k,l])=>`<button class="${PF.grp===k?"on":""}" data-pfg="${k}">${l}</button>`).join("")}</div>`;
  if(!total)return tabs+`<p class="note">Pas de données pour cette catégorie (fiches détaillées non téléchargées ?).</p>`;
  return tabs+`<div class="tbl"><div class="tr hd"><span>${esc(gs.find(g=>g[0]===PF.grp)[1])}</span>${th("n","Nombre")}${th("mean","Note moy.")}${th("t",A?"Temps":"Lus")}</div>${shown.map(r=>`<button class="tr" data-dr="${dreg(r.k,r.items)}"><span class="tn">${esc(r.k)}</span><span>${r.n}</span><span>${r.mean?f2(r.mean):"—"}</span><span>${tl(r.t)}</span></button>`).join("")}</div>${total>15?`<button class="btn ghost sm2" style="margin-top:10px" data-pfall>${PF.all?"Réduire":"Voir tout ("+total+")"}</button>`:""}`;
}

/* ----- activité : heatmap + liste ----- */
function actData(){
  const a=profOf().activity||[];
  if(a.length)return {list:a,real:true};
  return {list:DATA.items.filter(i=>i.updated).map(i=>({t:i.updated,id:i.id,type:i.type,title:i.title,txt:`${LS[i.status]||""} · ${prog(i)}`})),real:false};
}
const actTxt=a=>a.txt||(["watched episode","read chapter","rewatched episode","reread chapter"].includes(a.st)?`${ACTV[a.st]} ${a.pr||""}`:(ACTV[a.st]||nice(a.st)));
function heat(l,real){
  const cnt={};l.forEach(a=>{const k=dkey(a.t);cnt[k]=(cnt[k]||0)+1});
  const mx=Math.max(1,...Object.values(cnt));
  const today=new Date();today.setHours(0,0,0,0);
  const start=new Date(today);start.setDate(start.getDate()-((start.getDay()+6)%7)-52*7);
  let cols="",mo="",prev=-1;
  for(let w=0;w<53;w++){
    const mon=new Date(start);mon.setDate(start.getDate()+w*7);
    const mm=mon.getMonth();mo+=`<span>${mm!==prev?MONTHS[mm]:""}</span>`;prev=mm;
    let cells="";
    for(let d=0;d<7;d++){
      const dt=new Date(start);dt.setDate(start.getDate()+w*7+d);
      if(dt>today){cells+=`<i class="hz off"></i>`;continue}
      const k=dkey(dt.getTime()/1000),c=cnt[k]||0,lv=c?Math.min(4,Math.ceil(c/mx*4)):0;
      cells+=`<i class="hz l${lv}"${PF.day===k?' style="outline:2px solid #fff"':""} data-day="${k}" title="${esc(dt.toLocaleDateString("fr-FR",{day:"numeric",month:"long",year:"numeric"}))} : ${c} activité${c>1?"s":""}"></i>`;
    }
    cols+=`<div class="hw">${cells}</div>`;
  }
  const total=l.filter(a=>a.t>=start.getTime()/1000).length;
  return `<div class="heatw"><div class="hmo">${mo}</div><div class="heat">${cols}</div></div>
  <div class="hleg"><span>Moins</span><i class="hz l0"></i><i class="hz l1"></i><i class="hz l2"></i><i class="hz l3"></i><i class="hz l4"></i><span>Plus</span></div>
  <p class="note">${total} activité${total>1?"s":""} sur l'année · ${real?"d'après ton historique récent":"d'après la dernière modification de chaque titre (historique pas encore téléchargé)"} · clique sur un jour pour le détail.</p>`;
}
const ACTCOL={"watched episode":"#3db4f2","read chapter":"#3db4f2","rewatched episode":"#9256f3","reread chapter":"#9256f3","rewatched":"#9256f3","reread":"#9256f3","completed":"#7bd555","dropped":"#e85d75","paused watching":"#f79a63","paused reading":"#f79a63","plans to watch":"#c063ff","plans to read":"#c063ff"};
function relT(t){
  const d=Date.now()/1000-t;
  if(d<90)return "à l'instant";if(d<3600)return "il y a "+Math.round(d/60)+" min";
  if(d<86400)return "il y a "+Math.round(d/3600)+" h";
  if(d<86400*30)return "il y a "+Math.round(d/86400)+" j";
  if(d<86400*365)return "il y a "+Math.round(d/86400/30)+" mois";
  return "il y a "+Math.round(d/86400/365)+" an"+(d>=86400*365*1.5?"s":"");
}
function actList(l){
  if(!l.length)return `<p class="note">Aucune activité.</p>`;
  let last="",out="";
  for(const a of l){
    const k=dkey(a.t),dt=new Date(a.t*1000);
    if(k!==last){last=k;out+=`<h3 class="adh">${esc(dt.toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long",year:"numeric"}))}</h3>`}
    const mine=DATA.items.find(x=>x.id===a.id),A=a.type==="ANIME";
    const col=ACTCOL[a.st]||"#677b94";
    const tot=mine&&mine.total,nums=String(a.pr||"").match(/\d+/g),cur=nums?+nums[nums.length-1]:null;
    const pc=(cur!=null&&tot)?Math.min(100,Math.round(cur/tot*100)):null;
    const what=a.txt?esc(a.txt):esc(actTxt(a));
    const prg=cur!=null?`<span class="eprg">${A?"Épisode":"Chapitre"} <b>${esc(a.pr)}</b>${tot?` sur ${tot}`:""}${pc!=null?` · ${pc} %`:""}</span>`:"";
    const bar=pc!=null?`<div class="ebar"><i style="width:${pc}%;background:${col}"></i></div>`:"";
    const meta=mine?[mine.format?fm(FMT,mine.format):"",mine.year||"",(mine.genres||[]).slice(0,3).join(", ")].filter(Boolean).join(" · "):"";
    const chips=mine?`<span class="echip">${esc(LS[mine.status]||"")}</span>${mine.score?`<span class="echip">★ ${mine.score}</span>`:""}`:"";
    out+=`<a class="ev2" href="#/m/${a.id}" style="--ec:${col}"><img src="/img/cover_${a.id}.jpg" alt="" ${imgErr}><div class="ebody"><div class="etop"><span class="eact">${what}</span><span class="etype">${A?"Animé":"Manga"}</span></div><b class="ett">${esc(a.title)}</b>${prg}${bar}${meta?`<span class="emeta">${esc(meta)}</span>`:""}${chips?`<div class="echips">${chips}</div>`:""}</div><div class="etime"><b>${dt.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}</b><span>${relT(a.t)}</span></div></a>`;
  }
  return out;
}

/* ----- onglets du profil ----- */
function favM(n){
  const mine=DATA.items.find(x=>x.id===n.id);
  const meta=[fm(FMT,n.format),n.year].filter(Boolean).join(" · ");
  return `<a class="vc" data-q="${esc(n.title.toLowerCase())}" href="#/m/${n.id}"><div class="p"><img loading="lazy" src="/img/cover_${n.id}.jpg" alt="" ${imgErr}>${mine?`<span class="tag">${esc(LS[mine.status]||"")}</span>`:""}${rateB(mine&&mine.avg)}${heartI(n.id)}</div><b>${esc(n.title)}</b><span class="m">${esc(meta)}</span></a>`;
}
const favP=(p,kind)=>{const im=`<img loading="lazy" src="/img/${esc(p.img||"")}" alt="" ${imgErr}><b>${esc(p.name)}</b>`,q=esc(p.name.toLowerCase());return kind==="character"?`<a class="ch" data-q="${q}" href="#/c/${p.id}">${im}</a>`:`<div class="ch" data-q="${q}" style="cursor:default">${im}</div>`};

/* ----- profil v2 ----- */
const SWC=["#3db4f2","#c063ff","#fc9dd6","#ef881a","#e13333","#4ca56f","#f47521"];
const pfAcc=()=>{try{return localStorage.getItem("pfacc")||""}catch(e){return ""}};
function donut(list){
  const seg=STORDER.map(s=>({s,items:list.filter(i=>i.status===s)})).filter(x=>x.items.length);
  if(!seg.length)return `<p class="note">Aucune entrée.</p>`;
  const R=80,C=2*Math.PI*R,tot=list.length;let off=0;
  const arcs=seg.map(x=>{const len=x.items.length/tot*C;
    const c=`<circle cx="100" cy="100" r="${R}" stroke="${STCOL[x.s]}" stroke-dasharray="${Math.max(len-2,.5)} ${C}" stroke-dashoffset="${-off}" data-dr="${dreg(LS[x.s],x.items)}" data-st="${x.s}" data-n="${x.items.length}"/>`;off+=len;return c}).join("");
  const leg=seg.map(x=>`<button data-dr="${dreg(LS[x.s],x.items)}" data-st="${x.s}" data-n="${x.items.length}"><i style="background:${STCOL[x.s]}"></i>${esc(LS[x.s])} <b>${x.items.length}</b> <small>${Math.round(x.items.length/tot*100)}%</small></button>`).join("");
  return `<div class="dn" data-tot="${tot}"><div class="dnsvg"><svg viewBox="0 0 200 200">${arcs}</svg><div class="dnc"><b>${tot}</b><span>titres</span></div></div><div class="leg">${leg}</div></div>`;
}
function dnSet(box,st,n){
  box.querySelectorAll("circle").forEach(x=>x.classList.toggle("hv",!!st&&x.dataset.st===st));
  box.querySelector(".dnsvg").classList.toggle("hov",!!st);
  box.querySelector(".dnc").innerHTML=st?`<b>${n}</b><span>${esc(LS[st])}</span>`:`<b>${box.dataset.tot}</b><span>titres</span>`;
}
function streaks(l){
  const days=new Set(l.map(a=>dkey(a.t))),ks=[...days].sort();let best=0,run=0,prev=null;
  ks.forEach(k=>{const d=new Date(k+"T12:00:00");run=(prev&&Math.round((d-prev)/864e5)===1)?run+1:1;best=Math.max(best,run);prev=d});
  let cur=0;const d=new Date();d.setHours(12,0,0,0);
  if(!days.has(dkey(d/1000)))d.setDate(d.getDate()-1);
  while(days.has(dkey(d/1000))){cur++;d.setDate(d.getDate()-1)}
  return {best,cur,days:days.size};
}
/* avatar : supprime automatiquement les barres noires / transparentes sur les bords */
function fixAvatar(im){
  if(im.dataset.fx||!im.naturalWidth)return;im.dataset.fx=1;
  try{
    const w=im.naturalWidth,h=im.naturalHeight,c=document.createElement("canvas");c.width=w;c.height=h;
    const g=c.getContext("2d",{willReadFrequently:true});g.drawImage(im,0,0);
    const px=g.getImageData(0,0,w,h).data;
    /* transparent ou presque noir = « vide » */
    const L=(x,y)=>{const i=(y*w+x)*4;return px[i+3]<60?0:(px[i]+px[i+1]+px[i+2])/3};
    const dark=(n,at)=>{let s=0,m=0;for(let j=0;j<n;j++){const v=at(j);s+=v;if(v>m)m=v}return s/n<42&&m<110};
    const cut=(len,n,at)=>{let k=0;while(k<len*.35&&dark(n,j=>at(k,j)))k++;return k>=len*.35?0:(k?k+1:0)};
    const t=cut(h,w,(k,j)=>L(j,k)),b=cut(h,w,(k,j)=>L(j,h-1-k)),l=cut(w,h,(k,j)=>L(k,j)),r=cut(w,h,(k,j)=>L(w-1-k,j));
    if(!(t||b||l||r))return;
    const sw=w-l-r,sh=h-t-b;if(sw<20||sh<20)return;
    const o=document.createElement("canvas");o.width=sw;o.height=sh;
    o.getContext("2d").drawImage(c,l,t,sw,sh,0,0,sw,sh);
    const url=o.toDataURL("image/jpeg",.92);
    PF.avFix={src:im.dataset.orig,url};im.src=url;
  }catch(e){}
}
function pfAfter(){
  const im=$("#pf-av");
  if(im&&!(PF.avFix&&PF.avFix.src===im.dataset.orig)){if(im.complete)fixAvatar(im);else im.addEventListener("load",()=>fixAvatar(im),{once:true})}
  PF.lastTab=PF.tab;
  cxArrows();
  document.querySelectorAll("#page .pscroll img").forEach(m=>{if(!m.complete)m.addEventListener("load",cxArrows,{once:true})});
}

function ovHtml(){
  const L=t=>DATA.items.filter(i=>i.type===t),an=L("ANIME"),ma=L("MANGA"),all=DATA.items;
  const {list,real}=actData(),p=profOf(),f=p.favourites||{},sk=streaks(list);
  const sA=pstats(an),sM=pstats(ma);
  const row=(l,v)=>`<div class="srow"><span>${l}</span><b>${v}</b></div>`;
  /* colonne gauche : à propos, statistiques, genres */
  const about=p.about?`<div class="pcard"><h3>À propos</h3><div class="about" id="pf-about">${aboutHtml(p.about)}</div><button class="lnk" id="pf-abtn" data-about>Tout afficher</button></div>`:"";
  const stats=`<div class="pcard"><h3>Statistiques</h3>
    <h4>Animés</h4>${row("Titres",num(sA.n))}${row("Épisodes vus",num(sA.units))}${row("Temps de visionnage",durF(sA.mins))}${row("Note moyenne",sA.sc?f2(sA.mean):"—")}
    <h4>Mangas</h4>${row("Titres",num(sM.n))}${row("Chapitres lus",num(sM.units))}${row("Note moyenne",sM.sc?f2(sM.mean):"—")}
    <button class="lnk" data-go="ANIME">Statistiques détaillées →</button></div>`;
  const gs=agg(all,i=>i.genres).sort((a,b)=>b.n-a.n).slice(0,8);
  const genres=gs.length?`<div class="pcard"><h3>Genres</h3><div style="margin-top:10px">${barList(gs.map(g=>({label:g.k,items:g.items})))}</div></div>`:"";
  /* colonne principale */
  const cur=all.filter(i=>i.status==="CURRENT").sort((a,b)=>(b.updated||0)-(a.updated||0)).slice(0,14);
  const curH=cur.length?`<section><div class="shd"><h2>En cours<small>${cur.length}</small></h2></div><div class="cxwrap"><button class="cxar l off" data-cxar="-1" aria-label="Précédent">${CXL}</button><div class="cxscroll pscroll">${cur.map(i=>{const pc=i.total?Math.min(100,Math.round(i.progress/i.total*100)):0;
    return `<a class="vc" href="#/m/${i.id}"><div class="p"><img loading="lazy" src="/img/${esc(i.img)}" alt="" ${imgErr}>${rateB(i.avg)}${heartI(i.id)}<div class="bar"><i style="width:${pc}%"></i></div></div><b>${esc(i.title)}</b><span class="m">${esc(prog(i))}</span></a>`}).join("")}</div><button class="cxar r off" data-cxar="1" aria-label="Suivant">${CXR}</button></div></section>`:"";
  const T=PF.ovt==="MANGA"?"MANGA":"ANIME",lt=T==="ANIME"?an:ma;
  const tg=`<div class="tog"><button class="${T==="ANIME"?"on":""}" data-pfov="ANIME">Animés</button><button class="${T==="MANGA"?"on":""}" data-pfov="MANGA">Mangas</button></div>`;
  const dist=`<div class="pcard"><div class="pch"><h3>Répartition</h3>${tg}</div>${lt.length?donut(lt):'<p class="note">Aucune entrée.</p>'}</div>`;
  const mini=(v,l)=>`<div><b>${v}</b><span>${l}</span></div>`;
  const act=`<div class="pcard"><div class="pch"><h3>Activité</h3><button class="lnk" data-pf="act">Détail →</button></div><div class="mini">${mini(sk.cur,"Série en cours (jours)")}${mini(sk.best,"Record (jours)")}${mini(sk.days,"Jours actifs")}</div>${heat(list,real)}</div>`;
  return `<div class="play"><aside class="pside">${about}${stats}${genres}</aside><div class="pmain">${curH}${dist}${act}</div></div>`;
}
function statsHtml(){
  const A=PF.type==="ANIME",list=DATA.items.filter(i=>i.type===PF.type);
  const tg=`<div class="tog"><button class="${A?"on":""}" data-pft="ANIME">Animés</button><button class="${A?"":"on"}" data-pft="MANGA">Mangas</button></div>`;
  if(!list.length)return `<div style="margin-top:26px">${tg}<p class="note">Aucun ${A?"animé":"manga"} dans ta liste.</p></div>`;
  const sc=Array.from({length:10},(_,k)=>({label:String(k+1),items:list.filter(i=>Math.round(i.score||0)===k+1)}));
  const unr=list.filter(i=>!i.score).length;
  const lm=bucket(list,lenLabel);
  const lens=LEN[PF.type].map(b=>b[1]).concat("Inconnue").filter(k=>lm[k]).map(k=>({label:k,items:lm[k]}));
  const ym=bucket(list,i=>i.year);
  const years=Object.keys(ym).sort().map(k=>({label:k,items:ym[k]}));
  const srcm=A?bucket(list,i=>{const s=(PX[i.id]||{}).src;return s?fm(SRC,s):""}):bucket(list,i=>{const c=(PX[i.id]||{}).ctry;return c?(CTRY[c]||c):""});
  return `<div style="margin-top:26px">${tg}</div>`+kpiRow(PF.type,list)+
    `<section class="sec pcard"><h2>Répartition par statut</h2>${statusBar(list)}</section>`+
    `<section class="sec pcard"><h2>Notes<small>${unr} sans note</small></h2>${colChart(sc,l=>"Note "+l+" / 10")}</section>`+
    `<div class="pgrid" style="margin-top:20px"><section class="sec pcard"><h2>Formats</h2>${barList(rowsOf(bucket(list,i=>i.format?fm(FMT,i.format):"")))}</section>`+
    `<section class="sec pcard"><h2>Longueur</h2>${barList(lens)}</section></div>`+
    `<section class="sec pcard"><h2>Genres, tags &amp; plus</h2>${groupTable(list,A)}</section>`+
    `<section class="sec pcard"><h2>Année de sortie</h2>${colChart(years,l=>"Sortis en "+l)}</section>`+
    `<section class="sec pcard"><h2>${A?"Source":"Pays d'origine"}</h2>${barList(rowsOf(srcm))}</section>`;
}
function favHtml(){
  const f=profOf().favourites||{};
  const KINDS=[["anime","Animés"],["manga","Mangas"],["characters","Personnages"],["staff","Staff"],["studios","Studios"]];
  const cnt=k=>(f[k]||[]).length,n=KINDS.reduce((a,[k])=>a+cnt(k),0);
  if(!n)return `<p class="note" style="margin-top:24px">Aucun favori téléchargé. Clique sur « Actualiser le profil » (connexion internet requise).</p>`;
  const avail=KINDS.filter(([k])=>cnt(k));
  if(!cnt(PF.fk))PF.fk=avail[0][0];
  const pill=(k,l,c)=>`<button class="${PF.fk===k?"on":""}" data-pffk="${k}">${l}<small>${c}</small></button>`;
  const pills=`<div class="fkbar">${avail.map(([k,l])=>pill(k,l,cnt(k))).join("")}</div>`;
  const sc=(h,arr,fn,cls)=>arr&&arr.length?`<section class="sec"><h2>${h}<small>${arr.length}</small></h2><div class="${cls} fkgrid">${arr.map(fn).join("")}</div></section>`:"";
  const studios=(f.studios||[]).length?`<section class="sec"><h2>Studios<small>${f.studios.length}</small></h2><div class="fkgrid">${f.studios.map(s=>`<span class="chip" data-q="${esc(s.name.toLowerCase())}">${esc(s.name)}</span>`).join("")}</div></section>`:"";
  const parts={anime:sc("Animés",f.anime,favM,"vgrid"),manga:sc("Mangas",f.manga,favM,"vgrid"),
    characters:sc("Personnages",f.characters,p=>favP(p,"character"),"chars"),staff:sc("Staff",f.staff,p=>favP(p,"staff"),"chars"),studios};
  const body=parts[PF.fk];
  return `${pills}<div class="fkbody" key="${PF.fk}">${body}</div>`;
}
function actHtml(){
  const {list,real}=actData();
  const l=list.filter(a=>PF.act==="ALL"||a.type===PF.act).sort((a,b)=>b.t-a.t);
  const shown=PF.day?l.filter(a=>dkey(a.t)===PF.day):l;
  const tg=`<div class="tog">${[["ALL","Tout"],["ANIME","Animés"],["MANGA","Mangas"]].map(([k,t])=>`<button class="${PF.act===k?"on":""}" data-pfact="${k}">${t}</button>`).join("")}</div>`;
  const dayBar=PF.day?`<p class="note" style="margin-top:16px">Jour sélectionné : ${esc(new Date(PF.day+"T12:00:00").toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long",year:"numeric"}))} · ${shown.length} activité${shown.length>1?"s":""} <button class="btn ghost sm2" data-pfday0>✕ Tout afficher</button></p>`:"";
  return `<div style="margin-top:26px">${tg}</div><div class="pcard">${heat(l,real)}</div>${dayBar}${actList(shown.slice(0,PF.actN))}`+(shown.length>PF.actN?`<button class="btn ghost" style="margin-top:14px" data-pfmore>Afficher plus (${shown.length-PF.actN})</button>`:"");
}
function profHead(){
  const p=profOf(),has=!!p.name,name=p.name||DATA.user||"Profil";
  const COL={blue:"#3db4f2",purple:"#c063ff",pink:"#fc9dd6",orange:"#ef881a",red:"#e13333",green:"#4ca56f",gray:"#677b94"};
  const col=COL[p.color]||(/^#[0-9a-f]{6}$/i.test(p.color||"")?p.color:"#3db4f2");
  const mine=pfAcc(),acc=/^#[0-9a-f]{6}$/i.test(mine)?mine:col;
  const ban=p.banner?`<div class="pban" style="background-image:linear-gradient(180deg,rgba(11,11,15,.35),rgba(11,11,15,.1) 45%,var(--bg) 100%),url('/img/${esc(p.banner)}')"></div>`:`<div class="pban" style="background-image:linear-gradient(180deg,${acc}55,var(--bg) 100%)"></div>`;
  const asrc=(PF.avFix&&PF.avFix.src===p.avatar)?PF.avFix.url:"/img/"+esc(p.avatar||"");
  const av=p.avatar?`<div class="pavw"><img class="pav" id="pf-av" data-zoom data-cap="${esc(name)}" data-orig="${esc(p.avatar)}" src="${asrc}" alt="" ${imgErr}></div>`:`<div class="pavw"><div class="pav ph">${esc((name[0]||"?").toUpperCase())}</div></div>`;
  const meta=[
    p.created?`<span>Membre depuis ${esc(new Date(p.created*1000).toLocaleDateString("fr-FR",{month:"long",year:"numeric"}))}</span>`:"",
    Number.isFinite(p.followers)?`<span><b>${num(p.followers)}</b> abonnés</span>`:"",
    Number.isFinite(p.following)?`<span><b>${num(p.following)}</b> abonnements</span>`:"",
    p.fetched?`<span>Mis à jour le ${esc(new Date(p.fetched*1000).toLocaleDateString("fr-FR"))}</span>`:""
  ].join("");
  const btns=`<button class="btn" data-pfsync>↻ Actualiser</button>`;
  const sw=`<div class="sw" title="Couleur d'accent">${[col,...SWC].map((c,k)=>`<button data-pfacc="${k?c:""}" style="background:${c}" class="${(k?mine===c:!mine)?"on":""}" title="${k?c:"Couleur du profil"}"></button>`).join("")}</div>`;
  const note=has?"":`<p class="note" style="margin-top:16px">Profil pas encore téléchargé : clique sur « Actualiser » (connexion internet requise). Les statistiques ci-dessous sont calculées depuis ta liste locale.</p>`;
  return {ban,acc,head:`<div class="phead">${av}<div class="pi"><h1>${esc(name)}</h1><div class="pmeta">${meta}</div></div><div class="pact">${btns}${sw}</div></div>${note}`};
}
function profHtml(){
  const tabs=[["ov","Aperçu"],["st","Statistiques"],["fav","Favoris"],["act","Activité"]];
  const nav=`<nav class="pnav">${tabs.map(([k,l])=>`<button class="${PF.tab===k?"on":""}" data-pf="${k}">${l}</button>`).join("")}</nav>`;
  const body=PF.tab==="st"?statsHtml():PF.tab==="fav"?favHtml():PF.tab==="act"?actHtml():ovHtml();
  const h=profHead();
  return `${h.ban}<div class="prof" style="--acc:${h.acc}">${h.head}${nav}<div class="pbody">${body}</div></div>`;
}
function pfFilter(){
  const q=(PF.fq||"").trim().toLowerCase();
  document.querySelectorAll("#page [data-q]").forEach(e=>{e.hidden=!!q&&!e.dataset.q.includes(q)});
}
function pfRender(){
  if(location.hash!=="#/profil")return;
  const y=scrollY;DR={};DRN=0;
  $("#page").innerHTML=profHtml();pfAfter();
  const a=$("#pf-about"),b=$("#pf-abtn");
  if(a&&b){if(a.scrollHeight<=a.clientHeight+4)b.style.display="none";else a.classList.add("fade")}
  pfFilter();scrollTo(0,y);
}
async function loadProfile(){
  const r=await jget("/api/profile");
  PD=r||PD||{profile:{},extra:{}};PX=PD.extra||{};
}
async function showProfile(){
  $("#home").style.display="none";
  const P=$("#page");P.style.display="block";
  document.title="Profil – Ma liste";const y0=/^#\/[mc]\//.test(CURR)?PRY:0;scrollTo(0,0);PF.lastTab=null;
  if(PD){pfRender();scrollTo(0,y0)}else P.innerHTML='<div class="loading">Chargement…</div>';
  await loadProfile();
  if(location.hash==="#/profil")pfRender();
}
async function pfSync(){
  const b=$("[data-pfsync]");if(b){b.disabled=true;b.textContent="Actualisation…"}
  const r=await post("/api/profile/refresh");
  if(r.error)toast(r.error);else toast("Profil mis à jour ✔");
  await loadProfile();pfRender();
}

/* fenêtre « liste des titres » ouverte par un clic sur une barre / une ligne */
const dcard=i=>`<a class="vc" href="#/m/${i.id}"><div class="p"><img loading="lazy" src="/img/${esc(i.img)}" alt="" ${imgErr}><span class="tag">${esc(LS[i.status]||"")}</span>${rateB(i.avg)}${heartI(i.id)}</div><b>${esc(i.title)}</b><span class="m">${esc(prog(i))}${i.score?" · ★ "+i.score:""}</span></a>`;
function drawDrill(){
  const ids=new Set(DRC.ids),l=DATA.items.filter(i=>ids.has(i.id));
  const S={score:(a,b)=>(b.score||0)-(a.score||0)||a.title.localeCompare(b.title),title:(a,b)=>a.title.localeCompare(b.title),recent:(a,b)=>(b.updated||0)-(a.updated||0)};
  l.sort(S[DRS]||S.score);
  const opt=(k,t)=>`<option value="${k}"${DRS===k?" selected":""}>${t}</option>`;
  $("#drbody").innerHTML=`<h3>${esc(DRC.title)} <small>${l.length}</small></h3><div class="er"><label>Trier par</label><select id="dr-s">${opt("score","Ma note")}${opt("title","Titre")}${opt("recent","Dernière activité")}</select></div><div class="vgrid" style="margin-top:12px">${l.map(dcard).join("")}</div>`;
}
function openDrill(k){const d=DR[k];if(!d)return;DRC=d;drawDrill();$("#dr").classList.add("on");$("#dr").scrollTop=0}
const closeDrill=()=>$("#dr").classList.remove("on");
$("#drx").onclick=closeDrill;
$("#dr").onclick=e=>{if(e.target.id==="dr")closeDrill()};
$("#drbody").onchange=e=>{if(e.target.id==="dr-s"){DRS=e.target.value;drawDrill()}};

async function profClick(e){
  if(location.hash!=="#/profil")return;
  const t=e.target;let b;
  if((b=t.closest("[data-cxar]"))){const sc=b.parentNode.querySelector(".cxscroll");sc.scrollBy({left:+b.dataset.cxar*sc.clientWidth*.8,behavior:"smooth"});return}
  if((b=t.closest("[data-dr]"))){openDrill(b.dataset.dr);return}
  if((b=t.closest("[data-pf]"))){PF.tab=b.dataset.pf;PF.day=null;pfRender();return}
  if((b=t.closest("[data-go]"))){PF.type=b.dataset.go;PF.tab="st";pfRender();scrollTo(0,0);return}
  if((b=t.closest("[data-pft]"))){PF.type=b.dataset.pft;pfRender();return}
  if((b=t.closest("[data-pfg]"))){PF.grp=b.dataset.pfg;PF.all=false;pfRender();return}
  if((b=t.closest("[data-pfm]"))){PF.metric=b.dataset.pfm;pfRender();return}
  if(t.closest("[data-pfall]")){PF.all=!PF.all;pfRender();return}
  if((b=t.closest("[data-day]"))){PF.day=b.dataset.day;PF.tab="act";pfRender();return}
  if((b=t.closest("[data-pfact]"))){PF.act=b.dataset.pfact;PF.day=null;pfRender();return}
  if((b=t.closest("[data-pfov]"))){PF.ovt=b.dataset.pfov;pfRender();return}
  if((b=t.closest("[data-pffk]"))){PF.fk=b.dataset.pffk;pfRender();return}
  if((b=t.closest("[data-pfacc]"))){try{b.dataset.pfacc?localStorage.setItem("pfacc",b.dataset.pfacc):localStorage.removeItem("pfacc")}catch(e){}pfRender();return}
  if(t.closest("[data-pfday0]")){PF.day=null;pfRender();return}
  if(t.closest("[data-pfmore]")){PF.actN+=60;pfRender();return}
  if(t.closest("[data-about]")){const a=$("#pf-about"),btn=$("#pf-abtn");a.classList.toggle("open");btn.textContent=a.classList.contains("open")?"Réduire":"Tout afficher";return}
  if(t.closest("[data-pfsync]")){await pfSync()}
}
$("#page").addEventListener("click",profClick);
$("#page").addEventListener("mouseover",e=>{
  const t=e.target.closest?e.target.closest("[data-st]"):null;
  document.querySelectorAll(".dn").forEach(b=>{if(t&&b.contains(t))dnSet(b,t.dataset.st,t.dataset.n);else dnSet(b,null)});
});
$("#page").addEventListener("input",e=>{if(e.target.classList&&e.target.classList.contains("mx-fq"))mxFilter(e.target.closest(".mp-pane"));if(e.target.id==="pf-fq"){PF.fq=e.target.value;pfFilter()}});

function setTabs(){
  const fk=(PREV==="#/cal"||PREV==="#/accueil")&&/^#\/[mc]\//.test(location.hash),cal=location.hash==="#/cal"||(fk&&PREV==="#/cal"),ac=location.hash==="#/accueil"||(fk&&PREV==="#/accueil"),fc=PREV==="#/catalogue"&&/^#\/[mc]\//.test(location.hash),cg=location.hash==="#/catalogue"||fc,fs=PREV==="#/saisons"&&/^#\/[mc]\//.test(location.hash),sn=location.hash==="#/saisons"||fs,pr=location.hash==="#/profil"||(PREV==="#/profil"&&/^#\/[mc]\//.test(location.hash))||(/^#\/c\/\d+/.test(location.hash)&&!fc&&!fk&&!fs),o=cal||ac||pr||cg||sn;
  $("#tH").className=ac?"on":"";
  $("#tA").className=!o&&TAB==="ANIME"?"on":"";
  $("#tM").className=!o&&TAB==="MANGA"?"on":"";
  $("#tC").className=cal?"on":"";
  $("#tG").className=cg?"on":"";
  $("#tS").className=sn?"on":"";
  $("#tP").className=pr?"on":"";
  const hs=o||/^#\/m\/\d+/.test(location.hash);
  $("#q").style.display=hs?"none":"";
  $("#g").style.display=hs?"none":"";
}
function route(){
  const h=location.hash;
  if(CURR==="#/catalogue"&&h!=="#/catalogue")CATY=scrollY;
  if(CURR==="#/saisons"&&h!=="#/saisons")SSY=scrollY;
  if(CURR==="#/cal"&&h!=="#/cal")CALY=scrollY;
  if(CURR==="#/accueil"&&h!=="#/accueil")ACY=scrollY;
  if(CURR==="#/profil"&&h!=="#/profil")PRY=scrollY;
  const m=h.match(/^#\/m\/(\d+)/),ch=h.match(/^#\/c\/(\d+)/),c=h==="#/cal",pf=h==="#/profil",cg=h==="#/catalogue",ac=h==="#/accueil",ss=h==="#/saisons";
  document.body.classList.toggle("mpg",!!m);
  if(cg||c||ac||pf||ss)PREV=h;else if(!/^#\/[mc]\//.test(h))PREV="";
  if(m||ch||c||pf||cg||ac||ss){
    if(onHome){SCROLL=scrollY;onHome=false}
    if(m)showPage(+m[1]);else if(ch)showChar(+ch[1]);else if(pf)showProfile();else if(cg)showCatalogue();else if(ac)showAccueil();else if(ss)showSaisons();else showCal();
  }else{
    onHome=true;
    $("#page").style.display="none";$("#page").innerHTML="";$("#home").style.display="";
    document.title="Ma liste";scrollTo(0,SCROLL);
  }
  setTabs();CURR=h;
}
const leave=()=>{if(!onHome){SCROLL=0;location.hash=""}};
function zoom(src,cap){
  const lb=$("#lb");lb.querySelector("img").src=src;lb.querySelector("p").textContent=cap||"";lb.classList.add("on");
}
$("#lb").onclick=()=>$("#lb").classList.remove("on");

/* ----- modification de ma liste (synchronisée en ligne) ----- */
const post=async(u,b)=>{
  try{
    const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json","X-Ma-Liste":"1"},body:JSON.stringify(b||{})});
    return await r.json();
  }catch(e){return {error:"Serveur injoignable."}}
};
async function saveEntry(id,patch){
  if(!AUTH.connected){openConn();return null}
  const r=await post("/api/entry",Object.assign({id},patch));
  if(r.error){
    if(r.error==="not_connected"){AUTH.connected=false;accBtn();openConn()}else toast(r.error);
    return null;
  }
  if(r.removed)DATA.items=DATA.items.filter(x=>x.id!==id);
  else{
    const k=DATA.items.findIndex(x=>x.id===id);
    if(k>=0)DATA.items[k]=Object.assign(DATA.items[k],r.item);else DATA.items.push(r.item);
  }
  REC={};render();loadRec(TAB,true);
  return r;
}
async function bump(id,d=1){
  const i=DATA.items.find(x=>x.id===id);if(!i)return;
  const r=await saveEntry(id,{progress:Math.max(0,i.progress+d)});
  if(r&&r.item)toast(`${unit(i)} ${r.item.progress} enregistré${r.item.status==="COMPLETED"?" · terminé 🎉":""}`,d>0?"Annuler":null,()=>bump(id,-1));
}
const edId=()=>+$("#ed").dataset.id;
function syncEd(i){
  if(!$("#e-st")||edId()!==i.id)return;
  $("#e-st").value=i.status;$("#e-pg").value=i.progress;$("#e-sc").value=String(Math.round(i.score||0));
  $("#e-bar").style.width=(i.total?Math.min(100,i.progress/i.total*100):0)+"%";
}
async function edSave(patch){
  const id=edId(),r=await saveEntry(id,patch);
  const j=DATA.items.find(x=>x.id===id);if(j)syncEd(j);
  if(r)toast("Enregistré ✔");
}
let EDT;
$("#page").onclick=async e=>{
  const ar=e.target.closest("[data-cxar]");
  if(ar&&/^#\/m\//.test(location.hash)){const sc=ar.parentNode.querySelector(".cxscroll");sc.scrollBy({left:+ar.dataset.cxar*sc.clientWidth*.8,behavior:"smooth"});return}
  const mp=e.target.closest("[data-mxpill]");
  if(mp){const pn=mp.closest(".mp-pane");pn.querySelectorAll("[data-mxpill]").forEach(x=>x.classList.toggle("on",x===mp));mxFilter(pn);return}
  const sw=e.target.closest("[data-mxacc]");
  if(sw){const c=sw.dataset.mxacc;try{c?localStorage.setItem("pfacc",c):localStorage.removeItem("pfacc")}catch(x){}
    const m=document.querySelector(".mx");m.style.setProperty("--acc",c||"#f47521");m.querySelectorAll("[data-mxacc]").forEach(b=>b.classList.toggle("on",b===sw));return}
  const z=e.target.closest("[data-zoom]");
  if(z&&z.style.visibility!=="hidden"){zoom(z.getAttribute("src"),z.dataset.cap);return}
  if(e.target.closest("[data-back]")){location.hash=PREV||"";return}
  const sb=e.target.closest("[data-spo]");
  if(sb){const pg=sb.closest(".cpg"),on=pg.classList.toggle("spoon");sb.textContent=on?"🙈 Masquer les spoilers":"👁 Voir les spoilers";return}
  const si=e.target.closest("[data-spoi]");
  if(si){si.classList.toggle("on");return}
  if(e.target.closest("[data-hback]")){if(history.length>1)history.back();else location.hash=/^#\/c\//.test(location.hash)?"#/profil":"";return}
  const s=e.target.closest("[data-sc]");
  if(s){e.preventDefault();const el=document.getElementById(s.dataset.sc);if(el)el.scrollIntoView({behavior:"smooth"});return}
  if(e.target.closest("[data-trclose]")||e.target.id==="trbox"){$("#trbox").innerHTML="";return}
  const pt=e.target.closest("[data-pt]");
  if(pt){
    e.preventDefault();const k=pt.dataset.pt;
    document.querySelectorAll("#page .mp-tab").forEach(b=>b.classList.toggle("on",b.dataset.pt===k));
    document.querySelectorAll("#page .mp-pane").forEach(p=>p.classList.toggle("on",p.dataset.pane===k));
    const mxr=document.querySelector("#page .mx");if(mxr)mxr.dataset.tab=k;
    const bar=$("#mp-body");
    if(bar){const y=bar.getBoundingClientRect().top+scrollY-$("#hd").offsetHeight;if(scrollY>y+2)scrollTo({top:y})}
    return;
  }
  const t=e.target.closest("[data-trailer]");
  if(t){
    $("#trbox").innerHTML=`<div class="trm"><button class="x" data-trclose aria-label="Fermer">✕</button><iframe src="${esc(t.dataset.trailer)}" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe><p class="note">Si la vidéo ne s'affiche pas, vérifie ta connexion internet.</p></div>`;
    return;
  }
  const st=e.target.closest("[data-step]");
  if(st){
    const inp=$("#e-pg"),mx=inp.max?+inp.max:Infinity;
    inp.value=Math.min(mx,Math.max(0,+inp.value+ +st.dataset.step));
    clearTimeout(EDT);EDT=setTimeout(()=>edSave({progress:+inp.value}),500);return;
  }
  if(e.target.closest("[data-remove]")){
    if(!confirm("Retirer cette œuvre de ta liste ?"))return;
    const id=edId();if(await saveEntry(id,{remove:true}))showPage(id);return;
  }
  if(e.target.closest("[data-add]")){
    const id=edId(),r=await saveEntry(id,{status:$("#a-st").value});
    if(r){toast("Ajouté à ta liste ✔");showPage(id)}return;
  }
  if(e.target.closest("[data-airing]"))refreshAiring(false);
};
$("#page").onchange=e=>{
  const id=e.target.id;
  if(id==="spo")$("#tagbox").classList.toggle("show",e.target.checked);
  else if(id==="e-st")edSave({status:e.target.value});
  else if(id==="e-pg")edSave({progress:+e.target.value||0});
  else if(id==="e-sc")edSave({score:+e.target.value});
};

/* ----- favoris ♥ : uniquement depuis la page d'une œuvre ou d'un personnage (synchronisés avec AniList) ----- */
const favParse=k=>{k=String(k);return k[0]==="c"?{id:+k.slice(1),ch:true}:{id:+k,ch:false}};
function syncFavDom(){
  document.querySelectorAll("[data-fav]").forEach(el=>{
    const raw=el.dataset.fav,k=raw[0]==="c"?raw:+raw,on=FAVS.has(k);
    el.classList.toggle("on",on);
    el.textContent=on?"♥ Favori":"♡ Favori";
    el.title=favTitle(k);
  });
  document.querySelectorAll("[data-fvi]").forEach(el=>{
    const raw=el.dataset.fvi;el.classList.toggle("on",FAVS.has(raw[0]==="c"?raw:+raw));
  });
}
const FAVBUSY=new Set();
async function toggleFav(raw){
  const {id,ch}=favParse(raw),k=favKey(id,ch);
  if(!AUTH.connected){openConn();return}
  if(FAVBUSY.has(k))return;
  FAVBUSY.add(k);
  const want=!FAVS.has(k);
  want?FAVS.add(k):FAVS.delete(k);syncFavDom();
  const r=await post("/api/favourite",{id,kind:ch?"character":"media",value:want});
  FAVBUSY.delete(k);
  if(r.error){
    want?FAVS.delete(k):FAVS.add(k);syncFavDom();
    if(r.error==="not_connected"){AUTH.connected=false;accBtn();openConn()}else toast(r.error);
    return;
  }
  const f=PD&&PD.profile&&PD.profile.favourites;
  if(f&&r.node&&r.key){f[r.key]=(f[r.key]||[]).filter(n=>n.id!==id);if(want)f[r.key].unshift(r.node)}
  toast(want?"Ajouté aux favoris ♥":"Retiré des favoris");
}
let FAVTRY=0;
async function loadFavs(){
  const r=await jget("/api/favourites");
  if(!r)return;
  FAVS.clear();(r.ids||[]).forEach(x=>FAVS.add(x));(r.chars||[]).forEach(x=>FAVS.add("c"+x));syncFavDom();
  if(r.syncing&&FAVTRY++<5)setTimeout(loadFavs,3500);
}
document.addEventListener("click",e=>{
  const b=e.target.closest&&e.target.closest("[data-fav]");
  if(!b)return;
  e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
  toggleFav(b.dataset.fav);
},true);

/* ----- connexion du compte ----- */
function accBtn(){
  const b=$("#acc");b.textContent=AUTH.connected?"● "+(AUTH.name||"Connecté"):"🔑 Compte";
  b.classList.toggle("ok",!!AUTH.connected);
}
function openConn(){
  const body=$("#cmbody");
  if(AUTH.connected){
    body.innerHTML=`<h3>Mon compte</h3><p>Connecté en tant que <b>${esc(AUTH.name||"")}</b>. Tes modifications (progression, statut, note) sont synchronisées en ligne.</p><button class="btn ghost" id="cout">Se déconnecter</button>`;
  }else{
    body.innerHTML=`<h3>Connexion du compte</h3>
      <p>Pour modifier ta liste depuis cette page (+1 épisode, statut, note), connecte ton compte. Le token reste sur ton ordinateur, dans <code>ma_liste_data/config.json</code>.</p>
      <ol><li>Ouvre <a href="https://anilist.co/settings/developer" target="_blank" rel="noopener">la page développeur</a> et clique « Create New Client ».</li>
      <li>Nom : ce que tu veux. Redirect URL : <code>https://anilist.co/api/v2/oauth/pin</code> puis enregistre.</li>
      <li>Colle ici le <b>Client ID</b> affiché :<input id="cid" placeholder="ex. 12345"><a class="btn" id="cgo" target="_blank" rel="noopener" href="#">Obtenir mon token</a></li>
      <li>Autorise l'accès, copie le long token affiché et colle-le ici :<input id="ctk" placeholder="Token"><button class="btn" id="csv">Connecter</button></li></ol>`;
  }
  $("#cm").classList.add("on");
}
$("#cmx").onclick=()=>$("#cm").classList.remove("on");
$("#cm").onclick=e=>{if(e.target.id==="cm")$("#cm").classList.remove("on")};
$("#cmbody").oninput=e=>{
  if(e.target.id==="cid")$("#cgo").href="https://anilist.co/api/v2/oauth/authorize?client_id="+encodeURIComponent(e.target.value.trim())+"&response_type=token";
};
$("#cmbody").onclick=async e=>{
  if(e.target.id==="csv"){
    const r=await post("/api/auth",{token:$("#ctk").value});
    if(r.error){toast(r.error);return}
    AUTH=r;accBtn();$("#cm").classList.remove("on");toast("Compte connecté ✔");
    if(!onHome&&location.hash.startsWith("#/m/"))showPage(+location.hash.slice(4));
  }else if(e.target.id==="cout"){
    const r=await post("/api/auth",{token:""});AUTH=r;accBtn();$("#cm").classList.remove("on");toast("Compte déconnecté");
  }
};
$("#acc").onclick=openConn;
async function loadAuth(){const a=await jget("/api/auth");if(a)AUTH=a;accBtn()}

/* ---------- divers ---------- */
function genres(){
  const set=[...new Set(DATA.items.flatMap(i=>i.genres))].sort();
  $("#g").innerHTML=`<option value="">Tous les genres</option>`+set.map(x=>`<option>${esc(x)}</option>`).join("");
  $("#g").value=set.includes(G)?G:"";
}
function stamp(){
  const d=DATA.updated?new Date(DATA.updated*1000).toLocaleString("fr-FR",{dateStyle:"medium",timeStyle:"short"}):"jamais";
  const nx=DATA.updated?new Date((DATA.updated+7*86400)*1000).toLocaleDateString("fr-FR"):"—";
  $("#info").innerHTML=`Mis à jour : ${d}${navigator.onLine?"":'<span class="pill">Hors ligne</span>'}`;
  $("#info").title=`Prochain rafraîchissement automatique après le ${nx}`;
}
let TT;
function toast(m,label,fn){
  const t=$("#toast");
  t.innerHTML=`<span>${esc(m)}</span>`+(label?` <a href="#" id="tact">${esc(label)}</a>`:"");
  t.style.display="block";
  if(label)$("#tact").onclick=e=>{e.preventDefault();t.style.display="none";fn()};
  clearTimeout(TT);TT=setTimeout(()=>t.style.display="none",label?7000:5000);
}
async function load(){DATA=await (await fetch("/api/data")).json();genres();render();stamp()}
async function watch(){
  let s;try{s=await (await fetch("/api/status")).json()}catch(e){return}
  const rf=$("#rf");
  if(s.running){RUN=true;rf.disabled=true;rf.classList.add("spin");rf.textContent=s.message;setTimeout(watch,800);return}
  rf.disabled=false;rf.classList.remove("spin");rf.textContent="⟳ Rafraîchir";
  if(RUN){
    RUN=false;
    if(s.error)toast(s.error);else if(s.message)toast(s.message);
    await load();
    REC={};loadRec(TAB,true);FAVTRY=0;loadFavs();
    if(!onHome)route();
  }
}
const hh=()=>document.documentElement.style.setProperty("--hh",$("#hd").offsetHeight+"px");
addEventListener("resize",hh);
if(window.ResizeObserver)new ResizeObserver(hh).observe($("#hd"));
addEventListener("scroll",()=>document.body.classList.toggle("sc",scrollY>30),{passive:true});
$("#rf").onclick=async()=>{await post("/api/refresh");watch()};
$("#logo").onclick=()=>{ACY=0;if(accOn())scrollTo(0,0);else location.hash="#/accueil"};
$("#tH").onclick=()=>{ACY=0;location.hash="#/accueil"};
$("#tA").onclick=()=>{TAB="ANIME";leave();render();setTabs();loadRec()};
$("#tM").onclick=()=>{TAB="MANGA";leave();render();setTabs();loadRec()};
$("#tC").onclick=()=>{location.hash="#/cal"};
$("#tS").onclick=()=>{location.hash="#/saisons"};
$("#tG").onclick=()=>{if(PREV!=="#/catalogue")CATY=0;location.hash="#/catalogue"};
$("#tP").onclick=()=>{location.hash="#/profil"};
$("#q").oninput=e=>{leave();Q=e.target.value;render()};
$("#g").onchange=e=>{leave();G=e.target.value;render()};
$("#rows").onclick=e=>{
  const ps=e.target.closest("[data-lst]");
  if(ps){LST[TAB]=ps.dataset.lst;LMAX=60;lsave();render();return}
  const vw=e.target.closest("[data-lview]");
  if(vw){LVIEW=vw.dataset.lview;lsave();render();return}
  if(e.target.closest("[data-ldir]")){LDIR=-LDIR;lsave();render();return}
  const hs=e.target.closest("[data-lsort]");
  if(hs){const k=hs.dataset.lsort;if(LSORT===k)LDIR=-LDIR;else{LSORT=k;LDIR=k==="title"?1:-1}lsave();render();return}
  if(e.target.closest("[data-lcsv]")){lcsv(lcur().list);toast("Export CSV téléchargé ✔");return}
  if(e.target.closest("[data-lmore]")){LMAX+=60;render();return}
  const lg=e.target.closest("[data-lg]");
  if(lg){G=lg.dataset.lg;$("#g").value=G;LMAX=60;render();scrollTo(0,0);return}
  const mn=e.target.closest("[data-lminus]");
  if(mn){bump(+mn.dataset.lminus,-1);return}
  const go=e.target.closest("[data-go]");
  if(go&&!e.target.closest("select,button")){location.hash="#/m/"+go.dataset.go;return}
  if(e.target.classList.contains("arr")){
    const s=e.target.parentNode.querySelector(".strip");
    s.scrollBy({left:(e.target.classList.contains("r")?1:-1)*s.clientWidth*.8,behavior:"smooth"});return;
  }
  const b=e.target.closest("[data-bump]");
  if(b){e.preventDefault();bump(+b.dataset.bump,1);return}
  const x=e.target.closest("[data-dismiss]");
  if(x){e.preventDefault();ignAdd(+x.dataset.dismiss);render()}
};
$("#rows").onchange=async e=>{
  const t=e.target;
  if(t.id==="lfmt"){LFMT=t.value;LMAX=60;lsave();render()}
  else if(t.id==="lso"){LSORT=t.value;LDIR=LSORT==="title"?1:-1;lsave();render()}
  else if(t.dataset.lsel){if(!(await saveEntry(+t.dataset.lsel,{status:t.value})))render()}
  else if(t.dataset.lscore){if(!(await saveEntry(+t.dataset.lscore,{score:+t.value})))render()}
};
addEventListener("keydown",e=>{if(e.key==="/"&&onHome&&!/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)){e.preventDefault();$("#q").focus()}});
document.onkeydown=e=>{if(e.key==="Escape"){const tb=$("#trbox");if(tb)tb.innerHTML="";$("#lb").classList.remove("on");$("#cm").classList.remove("on");closeDrill()}};
addEventListener("hashchange",route);
addEventListener("hashchange",closeDrill);
addEventListener("online",stamp);addEventListener("offline",stamp);
setInterval(()=>{if(onHome&&!HP&&!document.hidden){HI++;renderHero()}},9000);
(async()=>{hh();if(!location.hash)history.replaceState(null,"","#/accueil");try{await load()}catch(e){}loadAuth();loadFavs();route();loadRec();watch()})();
</script></body></html>
"""


# ---------------------------------------------------------------- Appli téléphone (PWA) – mode en ligne uniquement
MANIFEST = {
    "name": "Ma liste – Animés & Mangas", "short_name": "Ma liste", "description": "Ma liste d'animés et de mangas",
    "start_url": "/", "scope": "/", "display": "standalone", "orientation": "any", "lang": "fr",
    "background_color": "#0b0b0f", "theme_color": "#0b0b0f",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

SW_JS = r"""
const V = "ml-v1", IMGC = "ml-img-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== V && k !== IMGC) await caches.delete(k);
  await self.clients.claim();
})()));
async function trim(c) {
  const ks = await c.keys();
  if (ks.length > 2500) for (const k of ks.slice(0, 300)) await c.delete(k);
}
async function swr(e) {                       // images : affichées tout de suite depuis le cache, mises à jour en arrière-plan
  const c = await caches.open(IMGC), hit = await c.match(e.request);
  const net = fetch(e.request).then(r => { if (r.ok) { c.put(e.request, r.clone()); trim(c); } return r; }).catch(() => null);
  e.waitUntil(net);
  return hit || (await net) || Response.error();
}
async function netFirst(r) {                  // pages et données : réseau d'abord, cache si hors connexion
  const c = await caches.open(V);
  try {
    const resp = await fetch(r);
    if (resp.ok && (r.mode !== "navigate" || resp.headers.get("X-Ml-App") === "1")) c.put(r, resp.clone());
    return resp;
  } catch (err) {
    const hit = (await c.match(r)) || (r.mode === "navigate" ? await c.match("/") : null);
    if (hit) return hit;
    throw err;
  }
}
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin) return;
  if (u.pathname.startsWith("/img/")) return e.respondWith(swr(e));
  if (["/api/status", "/api/schedule", "/api/auth", "/healthz", "/login"].includes(u.pathname)) return;
  if (r.mode === "navigate" || u.pathname.startsWith("/api/")) e.respondWith(netFirst(r));
});
"""

PWA_HEAD = ('<link rel="manifest" href="/manifest.webmanifest">\n'
            '<link rel="icon" type="image/png" href="/icon-192.png">\n'
            '<link rel="apple-touch-icon" href="/icon-192.png">\n')

PWA_BODY = """
<button id="mlInstall" hidden style="position:fixed;right:14px;bottom:calc(76px + env(safe-area-inset-bottom,0px));z-index:55;background:#f47521;color:#111;border:0;border-radius:999px;padding:10px 16px;font:700 14px system-ui,sans-serif;box-shadow:0 4px 16px #0009;cursor:pointer">📲 Installer l'app</button>
<script>
if("serviceWorker" in navigator)addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));
(()=>{let dip=null;const b=document.getElementById("mlInstall");
addEventListener("beforeinstallprompt",e=>{e.preventDefault();dip=e;b.hidden=false;setTimeout(()=>{b.hidden=true},20000)});
b.onclick=async()=>{b.hidden=true;if(dip){dip.prompt();try{await dip.userChoice}catch(x){}dip=null}};
addEventListener("appinstalled",()=>{b.hidden=true})})();
</script>
"""

ICON_192 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAADuElEQVR42u3dMWobQRSA4e1dhBCUYIwwCal1gBTpfAB3anQAt4HcwufwOXQOnyMHyKtMKkOk3Zl5bz742xDY/bxvJc3OLn9+f5UubnEIBJAAEkACSAJIAAkgASQBJIAEkACSABJAAkgASQAJIAEkgASQBJAAEkACSAJIAAkgASQBJIAEkACSABJAAkgArd/5tH95vDsednorDkgcFoDe6/Xp/tePLzc3H/ROcYjiQAGEThFGywgD6/vnj0z8b3HQRhhqnQHFaEfhmuIAzgso/oAIuL6+16Gl432PybXWLOt4P9QNkLvmde+p5wIUfzHO+rr1uggtLj8uQvkAOd9bNAsgH74qfRxbfPfjO6FkgI6HnZO9RXFgARJAAAEEEEAAAQSQAAIIIIAAAggggAQQQAABBNBsgOJ/nGH5LEAb/kw9w6NnAG2+zqH2M2gANVoo8/xwCxBAV620iolW714eoNZL9YpNNID6rPUsM9EA6rZYuMZEA6jzavPsEw2gIR5XyPt1EUCjPO8SE+3nt08AAXTVA1Pxr3JNNIBGfOIu0UQDaNBHNrNMNICGfuZ3/IkGUIKHxkeeaADl2HXgfNqPOdEAyrRtxfPD7WgTDaBk+56MtkgNoJQb54wz0QBKvPPSCBMNoNxbd3WfaABV2Put40/6ANXZPLDLIjWASu0+2X6RGkClALWfaAAVBNRyogFUFlCbiQZQZUANJhpA9QFt+pM+QLMA2miRGkATAdpikRpA0wFad6IBBBBAABlhALmJBsjHeIB8kQgQQH7KAMiPqQBZzgGQBWUAWdIKEEAW1QPksR6APFgIkEebAbK5gs0VALK9C0A2mALIFncA2WQTIIBaLf4CaBZANhoHyKsOAPKyFYCyAPK6J4C8cA4gr7wEKAsgL90F6EJAXvsN0IWAaswsgPoAKjOzAGoNqNjMAqgdoNEWfwGUCVD8j4UvPAAJIIAAAggggAACSAABBBBAAAEEEEACCCCAAAIIIICKAHp5vHOyy+wl2gHQ+bR3srcoDuwUgCIne4u6nMo+gMqv7WpfHNKJAL0+3Tvl6xaHdCJALkI1Lj89AcVfzAzLTBsUh7HX5acnIB/HUn/4GgKQ74SSfvczEKDyz2ptOrn6XntGATTgjt0p7po73vcMBwijjHSGA/TvUIvRfjzs9FYckBEGVg5AShRAAkgACSABJAEkgASQAJIAEkACSABJAAkgASSAJIAEkAASQAJIAkgACSABJAEkgASQAJIAEkACSABJAAkgAaT0/QVqM8zkNW6meQAAAABJRU5ErkJggg==")
ICON_512 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAIAAAB7GkOtAAANXElEQVR42u3dwU1jZxSA0dnPIkIoWAghaxDrFMCCHQV4lw0FeGspXVCH66AO15EC8kdIs5pMYDCP9/wd6VRA7vVn33iev/z91zcAgr74EwAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAIgL8CgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAgAD4KwAIAAACAIAAACAAAAgAAAIAgABwDPvN1Ys///gdFu37MNtrAeDHnh+vnx4ux7Z8/fobnLAx5GPUx8DbegHwun+9u1vdXpx5XaBmjP0YfiUQgKLxJsjrPryUYKyD1wQB8NIPMoAAeOkHGUAATsBhu76/Obfe8BpjWcbKeN0QgBN542+l4a18FBCAxb/x981OeM93Rn0UEIClvvq7+MP7/6+ABgjA8r7g79UfjtUA/1xAAJb0IAdLC8flYRICsIz3/nYVPoLPAQLg7g/+fwAC4NUfNAABmAPf+IRpvhvq1UYA/Gsv8G/EEIAZHH/sJEzJIUgA5sJzfmD65wV55REAxx9wCEIAPolv/sBnfSPI648AePsPPgQgAN7+gw8BCIC3/+BDAALg7T/4EIAAeOgbeEgcAvBOu7uVxYM5GMvoFUkA3H/AFQgBcP8BVyAEwPd/wHeBEABPfobT5BnRAjAd+wZz43VJAAQABAAB+DD7zZVlg7kZi+nVSQAEAAQAARAAEAAEwFeAwBeBEAABAAFAAAQABEAAEAAQAAFAAEAABAABAAEQAAQABEAABEAAQAAEQAAAARAAAQAEQAAEABAAARAAQAAEQAAAARAAAQAEQAAEABAAARAAQAAEQAAAARAAAQAEQAAEABAAARAAQAAEQAAAARAAAQABQAAEAAQAARAAEAAEQABAABAAAQABEAB/BQEAARAABAAEQAAQABAAAUAAQAAEAAEAARAAAeC1a/n0cHl7ceZPgQAIgAAU1/KwXe/uVv4aCIAACEB0LZ8fr+9vzv1NEAABEIDoWroIIQACIADdtTxs1/6MCIAACEB3LZ8fr30UQAAEQAC6a/n0cOmvhAAIgABE19JFCAEQAAFIr6WLEAIgAAKQXksXIQRAAASgu5YuQgiAAAhAei33mysXIQRAAASgu5YeIIEACIAAdNfysF17gAQCIAAC0F1LFyEEQAAEIL2WLkIIgAAIQHctXYQQAAEQgPRaugghAAIgAN219CMzCIAACEB6Lf3IDAIgAAKQXks/MoMACIAAdNfSRcikeXUSAAFIr6WLkElDAAQgvZYuQiYNARCA7lp6pKhJQwAEIL2WfmTGpCEAApBeSz8yY9IQAAHorqWLkElDAAQgvZYuQiYNARCA9Fq6CJk0BEAAumvpImTSEAABSK+lR4qaNAHwVxCA9Fp6gIRJEwAEoLuWfmTGpAkAApBeSxchkyYACEB6LV2ETJoAIADdtXQRMmkCgACk19JFyKQJAALQXUs/MmPSBAABSK+lH5kxaQKAAKTX0o/MmDQBQAC6a+kiZNIEQAAEIL2WLkImTQAEgPRaugiZNAEQALpr6ZGiJk0ABID0WvqRGZMmAAJAei39yIxJEwABoLuWLkImTQAEgPRaugiZNAEQANJr6SJk0gRAAOiupYuQSRMAAbCW6bX0SFGTJgACYC3TPEDCpAmAAFjLLj8yY9IEQACs5TcXIVNh0gRAAKylixAmTQAEwFq6CGHSBEAArKWLECZNAATAWiY+CrgImTQBEABr2eVHZkyaAAiAtUzzIzMmTQAEwFq6CJkckyYAAmAtXYQwaQIgANbSRQiTJgACYC1DFyHzZtIEQACsZfoi5KOASRMAAbCW6YuQcTJpAiAA1tJFCJMmAAJgLV2EMGkCIADW0kXIpCEAAmAtXYRMGgIgANby1HmkqEkTAAGwlmkeIGHSBEAArGX6IlR+gIRJEwABsJYuQtGLkEkTAAGwlkQvQiZNAATAWhK9CJk0ARAAa0n0ImTSBEAArCU/+ChQuAiZNAEQAGvJfz5A4rQvQiZNAATAWvI/D5A41YuQSRMAAbCWRC9CJk0ABMBaEr0ImTQBEABrSfQiZNIEQACsJW++CJ3GSJs0ARAAa8kvXoSW/lHApAmAAFhL3nURMmkCgABYSwEwaQKAAFhLJyCTJgAIgLX0P4FNmgAIgFd2a+lroCZNAAQAa+kfgpk0ARAArKVHQZg0ARAArKWbj0kTAAEQAGPj5mPSBEAABAA3H5MmAAIgAEzBT0IiAAJgLYtv/P0oPAIgANYyp3DzMWkCIADWkujNx6QJgABYS6I3H5MmAAJgLYnefEyaAAiAtXTzid58TJoACIC1TN98TKNJEwABsJbFhzqYLpMmAAJgLXMPdXDzMWkCIADW0s0HkyYAAmAt3XxMmjkRAAGwlm4+Jg0BEABr6eZj0hAAAbCWC7z5eONv0gRAAKxl7uZTfqiDSRMAAbCW0ZuPhzqYNAEQAGvp5oNJEwABsJZuPpg0ARAAa+nmg0kTAAGwlovnQZ4mTQAEwFoW3/i7+Zg0ARAAa5nj5mPSBEAArKWbDyZNAATAWrr5YNIEQACspZsPJk0ABMBauvlg0gRAAKzlAm8+RsWkCYAAWMviQx38pzdpAiAA1rK1ln68xaQJgACQW0s3H5MmAAJAcS3dfEyaAAgAubV08zFpAiAA5NbSzcekCYAAUFxLP95i0gRAAMitpR9vMWkCIADk1tKPt5g0ARAAASiupZuPSRMABCC3lm4+Jk0AEIDcWrr5mDQBQACKa+lBniZNABCA3Fr68RaTJgAIQHEt3XxMmgAgALm1dPMxaQKAAOTW0s3HpAkAAlBcSzcfkyYACEBuLd18TJoA+CsIQG4tPcjTpCEAAlBcSz/eYtIQAAHIraUfbzFpCIAA5NbSzcekIQACUFxLNx+ThgAIQG4t3XxMGgIgALm1dPMxaQiAABTX0o+3mDQEQABya+nHW0waAiAAubX04y0mzauTAAhAcS3dfBAAARCA3Fq6+SAAAiAAubV080EABEAAimvpQZ4IgAAIQG4t/XgLAiAAAlBcSzcfBEAABCC3lm4+CIAACEBuLd18EAABEIDiWrr5IAACIAC5tXTzQQAEQABya+lBngiAAAhAcS39eAsCIAACkFtLP96CAAiAAOTW0s0HARAAASiupZsPAiAAApBbSzcfBEAABCC3lm4+CIAACEBxLf14CwIgAAKQW0s/3oIACIAA5NbSj7cgAAIgAMW1dPNBAARAAAABEAABAARAAAQAEAABEABAAARAAAABEAABAARAAAQAEAABEABAAARAAAABEAABAAFAAAQABAABEAAQAARAAEAAEAABAAEQAAQABEAAEAAQAAFAAEAABAABAAEQAAQABEAABAAQAAEQAEAABEAAAAEQAAEABEAABAAQAAEQAEAABEAAAAEQAAEABEAABAAQAAEQAEAABEAAAAEQAAEABEAAPsN+c2XZYG7GYnp1EgABAAFAAAQABAABOC7LBnPjdUkABAAEAAHwRSDwFSAE4OieHi6tHMzHWEmvSwIwkefHaysH8zFW0uuSAEzn9uLM1sEcjGX0iiQAk9rdrSwezMFYRq9IAuAKBO4/CIArELj/IAC+CwS+/4MA+BAA3v4jAD4EgLf/AuBP4EMAePsvAPgQAN7+CwBvcX9zbhthSmPpvPIIwCwctmsLCVMaS+eVRwAcgsDxBwHwjGgI8ORnAZjpIcg3guCjv/nj+CMAGgBe/READ4kDD31DAGZiv7myq3BcY628tgjAYj4HuAXBsS4/3vsLgP8fAO7+CMByGuC7ofCeb3x69RcA/0YM/GsvBGCxHwU8Lwhe/5wfb/wF4AQ/Cvi/AvDzi783/gIgA+ClHwGQAfDSjwCc5D8X2N2tlIDm6/4Yfl/wFwD+LcF4E+Q7oxS+2TlG3eu+APCzh0m8GNsCi/Z9mO21AAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAC4K8AIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAIAD+CgACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAwC/7B2bD6kXFMuzIAAAAAElFTkSuQmCC")
PUBLIC_FILES = {
    "/manifest.webmanifest": ("application/manifest+json", json.dumps(MANIFEST, ensure_ascii=False).encode("utf-8"), {"Cache-Control": "no-cache"}),
    "/sw.js": ("application/javascript; charset=utf-8", SW_JS.encode("utf-8"), {"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"}),
    "/icon-192.png": ("image/png", ICON_192, {"Cache-Control": "max-age=604800"}),
    "/icon-512.png": ("image/png", ICON_512, {"Cache-Control": "max-age=604800"}),
}
if ONLINE:
    PAGE = PAGE.replace("<title>Ma liste</title>", PWA_HEAD + "<title>Ma liste</title>", 1).replace("</body></html>", PWA_BODY + "</body></html>")


def main():
    global USER
    if ONLINE and len(ONLINE_PASSWORD) < 10:
        sys.exit("Mode en ligne : définis la variable MA_LISTE_PASSWORD (10 caractères minimum, plus c'est long mieux c'est).")
    BASE.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(exist_ok=True)
    DETAILS.mkdir(exist_ok=True)
    CONF.update(load_json(CONF_FILE, {}))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if ONLINE and not args and os.environ.get("MA_LISTE_USER", "").strip():
        args = [os.environ["MA_LISTE_USER"].strip()]
    if args:
        new = args[0].strip()
        if new.lower() != (CONF.get("user") or "").lower():
            CONF.pop("token", None)  # autre compte : ancien token invalide
            CONF.pop("viewer", None)
        CONF["user"] = new
    if not CONF.get("user"):
        if ONLINE:
            sys.exit("Mode en ligne : définis la variable MA_LISTE_USER (ton pseudo AniList).")
        CONF["user"] = input("Ton pseudo : ").strip()
    save_conf()
    USER = CONF["user"]

    if ONLINE:
        for k in ("pin", "sess"):   # d'anciens réglages du mode téléphone ne servent plus : le mot de passe vient de l'environnement
            CONF.pop(k, None)
        save_conf()
    elif LAN:
        if not CONF.get("pin") or not CONF.get("sess"):   # code à 6 chiffres, généré une seule fois
            CONF["pin"] = f"{secrets.randbelow(10 ** 6):06d}"
            CONF["sess"] = secrets.token_hex(16)
            save_conf()
        LOCAL_ADDRS.update(lan_ips())

    threading.Thread(target=auto_loop, daemon=True).start()
    url = f"http://127.0.0.1:{PORT}"
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Ma liste → {url}   (Ctrl+C pour quitter)")
    if ONLINE:
        print(f"Mode EN LIGNE : écoute sur {HOST}:{PORT}, mot de passe obligatoire, données dans {BASE}")
    elif LAN:
        print("\nMode téléphone ACTIVÉ (même Wi-Fi que ce PC) :")
        for ip in lan_ips():
            print(f"   sur le téléphone, ouvre : http://{ip}:{PORT}")
        print(f"   code demandé la 1re fois : {CONF['pin']}\n")
    if not ONLINE:
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nÀ bientôt !")


if __name__ == "__main__":
    main()
