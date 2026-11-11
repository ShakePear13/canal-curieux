#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robot de mise à jour de Canal Curieux (sans IA, Python standard uniquement).

Lancé chaque semaine par GitHub Actions. Il :
  1. applique tes décisions prises sur le site (chaînes ajoutées / gardées / exclues, liens collés) ;
  2. vérifie les vidéos existantes (durée, date, vidéo supprimée, lecture intégrée autorisée) ;
  3. identifie les chaînes (identifiant YouTube UC…) ;
  4. ajoute les nouveautés des chaînes suivies (jamais de Shorts ni de directs) ;
  5. complète les séries à partir des playlists officielles des créateurs ;
  6. propose ~5 % de vidéos de chaînes « découvertes », citées par tes chaînes ou par les vidéos que tu as aimées ;
  7. compte les discussions Hacker News des vidéos anglaises ;
  8. écrit data/catalogue.json, data/chaines.json, data/series.json et data/journal.json.

Variables d'environnement : YT_API_KEY (obligatoire), SUPABASE_URL, SUPABASE_KEY, SYNC_CODE (facultatives).
"""
import collections
import datetime as dt
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import regles as R  # noqa: E402

RACINE = os.path.dirname(ICI)
DATA = os.path.join(RACINE, "data")
YT = "https://www.googleapis.com/youtube/v3/"
AUTRES = "Autres créateurs"

QUOTA = {"n": 0}
COUT = {"search": 100}
LOG = {"ajouts": collections.Counter(), "titres": [], "series": [], "decouvertes": [], "problemes": [],
       "indispo": 0, "reattribuees": 0, "boite": 0, "hn": 0, "chaines_identifiees": []}


# ------------------------------------------------------------------ outils
def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if not ("̀" <= c <= "ͯ"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")[:60] or "chaine"


def alnum(s):
    return re.sub(r"[^a-z0-9]", "", norm(s))


def aujourdhui():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def lire(nom, defaut):
    try:
        with open(os.path.join(DATA, nom), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defaut


def ecrire(nom, obj):
    with open(os.path.join(DATA, nom), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def probleme(msg):
    print("  ! " + msg)
    if msg not in LOG["problemes"]:
        LOG["problemes"].append(msg)


class ErreurApi(Exception):
    def __init__(self, code, raison, message):
        super().__init__(f"{code} {raison} {message}")
        self.code, self.raison = code, raison


class QuotaEpuise(Exception):
    pass


def http_json(url, corps=None, entetes=None, delai=30):
    """Seul point d'accès au réseau (remplacé par une simulation dans les tests)."""
    data = json.dumps(corps).encode() if corps is not None else None
    h = {"Accept": "application/json", "User-Agent": "canal-curieux-robot"}
    if data:
        h["Content-Type"] = "application/json"
    h.update(entetes or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8"))


def api(ressource, **params):
    """Appel à l'API YouTube officielle, avec décompte du quota."""
    cle = os.environ.get("YT_API_KEY", "")
    q = {k: v for k, v in params.items() if v is not None}
    q["key"] = cle
    QUOTA["n"] += COUT.get(ressource, 1)
    try:
        return http_json(YT + ressource + "?" + urllib.parse.urlencode(q))
    except urllib.error.HTTPError as e:
        raison, message = "", ""
        try:
            err = json.loads(e.read().decode("utf-8")).get("error", {})
            message = err.get("message", "")
            raison = (err.get("errors") or [{}])[0].get("reason", "")
        except Exception:
            pass
        if raison in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
            raise QuotaEpuise(message)
        raise ErreurApi(e.code, raison, message)


def duree_s(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    j, h, mi, s = (int(x or 0) for x in m.groups())
    return j * 86400 + h * 3600 + mi * 60 + s


def lots(seq, n=50):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def videos_infos(ids):
    """Détails de vidéos par lots de 50 (1 unité par lot). Les vidéos supprimées/privées sont absentes."""
    out = {}
    for lot in lots(dict.fromkeys(ids)):
        rep = api("videos", part="snippet,contentDetails,status,statistics", id=",".join(lot), maxResults=50)
        for it in rep.get("items", []):
            sn, st = it.get("snippet", {}), it.get("status", {})
            out[it["id"]] = {
                "id": it["id"],
                "t": (sn.get("title") or "").strip(),
                "cid": sn.get("channelId", ""),
                "ctitre": sn.get("channelTitle", ""),
                "p": sn.get("publishedAt", ""),
                "desc": sn.get("description", "") or "",
                "direct": sn.get("liveBroadcastContent", "none"),
                "d": duree_s(it.get("contentDetails", {}).get("duration", "")),
                "integrable": st.get("embeddable", True),
                "public": st.get("privacyStatus", "public") == "public",
                "vues": int(it.get("statistics", {}).get("viewCount", 0) or 0),
            }
    return out


def playlist_ids(pl, pages=1):
    """Identifiants des vidéos d'une playlist, dans l'ordre (1 unité par page de 50)."""
    ids, jeton = [], None
    for _ in range(pages):
        rep = api("playlistItems", part="contentDetails", playlistId=pl, maxResults=50, pageToken=jeton)
        ids += [it["contentDetails"]["videoId"] for it in rep.get("items", []) if it.get("contentDetails", {}).get("videoId")]
        jeton = rep.get("nextPageToken")
        if not jeton:
            break
    return ids


def dernieres_videos(ucid):
    """50 dernières vidéos longues d'une chaîne. « UULF… » = playlist sans Shorts ni directs ; repli sur « UU… »."""
    for prefixe in ("UULF", "UU"):
        try:
            return playlist_ids(prefixe + ucid[2:])
        except ErreurApi as e:
            if e.code != 404:
                raise
    return []


def acceptable(v, duree_min=None):
    if not v["public"] or v["direct"] != "none":
        return False
    if v["d"] < (duree_min or R.DUREE_MIN):
        return False
    t = norm(v["t"])
    return not any(m in t for m in R.MOTS_EXCLUS)


# ------------------------------------------------------------------ sous-thèmes et « Pourquoi »
def _touche(mot, t):
    if mot.startswith("="):
        return re.search(r"(?<![a-z'’])" + re.escape(mot[1:]) + r"(?![a-z])", t) is not None
    return re.search(r"(?<![a-z])" + re.escape(mot.strip()), t) is not None


def sous_themes(titre, theme):
    t = norm(titre) + " "
    permis = R.AUTORISES.get(theme, set())
    tags = []
    for tag, mots in R.REGLES:
        if tag in permis and tag not in tags and any(_touche(m, t) for m in mots):
            tags.append(tag)
    return tags[:3] or [R.DEFAUT.get(theme, "Divers")]


def pourquoi(ch):
    nom = ch.get("name", "")
    if nom in R.POURQUOI:
        return R.POURQUOI[nom]
    if ch.get("origin") == "mathieu":
        return "Ton choix · chaîne que tu as ajoutée"
    if ch.get("origin") == "découverte":
        return "Découverte · " + (ch.get("via") or "proche de tes chaînes")
    return "Sélection de départ"


# ------------------------------------------------------------------ catalogue
class Catalogue:
    def __init__(self, cat):
        self.cat = cat
        for k, lab in R.THEMES.items():
            if k not in cat:
                cat[k] = {"label": lab, "order": len(cat), "items": []}

    def tous(self):
        for k, c in self.cat.items():
            for it in c["items"]:
                yield k, it

    def ids(self):
        return {it["id"] for _, it in self.tous()}

    def compte_par_chaine(self):
        return collections.Counter(slug(it["c"]) for _, it in self.tous() if not it.get("x"))

    def total(self):
        return sum(1 for _, it in self.tous() if not it.get("x"))

    def ajouter(self, theme, v, ch_nom, langue, w, serie=None):
        if v["id"] in self.ids():
            return False
        if theme not in self.cat:
            theme = "sciences"
        it = {"id": v["id"], "t": v["t"], "c": ch_nom, "l": langue, "a": aujourdhui(), "w": w,
              "tags": sous_themes(v["t"], theme), "d": v["d"], "p": v["p"][:10]}
        if not v["integrable"]:
            it["e"] = 0
        if serie:
            it["s"] = serie
        self.cat[theme]["items"].append(it)
        LOG["ajouts"][theme] += 1
        LOG["titres"].append(f"{ch_nom} — {v['t']}")
        return True


# ------------------------------------------------------------------ 1. décisions prises sur le site
def lire_etat():
    url, cle, code = (os.environ.get(k, "").strip() for k in ("SUPABASE_URL", "SUPABASE_KEY", "SYNC_CODE"))
    if not (url and cle and code):
        print("Synchro non configurée : le robot tourne sans tes 👍 ni tes ajouts de chaînes.")
        return {}
    try:
        rep = http_json(url.rstrip("/") + "/rest/v1/rpc/cc_lire", corps={"p_code": code},
                        entetes={"apikey": cle, "Authorization": "Bearer " + cle})
        if rep is None:
            probleme("Code de synchro inconnu de la base : tes 👍 et ajouts de chaînes n'ont pas été lus.")
        return rep or {}
    except Exception as e:  # la base ne doit jamais bloquer la mise à jour
        probleme(f"Base de synchro injoignable ({type(e).__name__}) : passage sans tes 👍 ni tes ajouts.")
        return {}


def appliquer_decisions(etat, chans):
    for s, d in (etat.get("chans") or {}).items():
        if not isinstance(d, dict) or d.get("status") not in ("suivie", "exclue"):
            continue
        ch = chans.get(s)
        if ch is None:
            if not d.get("name"):
                continue
            ch = chans[s] = {"name": d["name"][:80], "cat": d.get("cat") if d.get("cat") in R.THEMES else "sciences",
                             "l": "en" if d.get("l") == "en" else "fr", "origin": "mathieu", "added": aujourdhui()}
        if d.get("url") and d["url"] != ch.get("url") and re.match(r"https://(www\.|m\.)?youtube\.com/", d["url"]):
            ch["url"] = d["url"]
            ch.pop("ucid", None)
            ch.pop("note", None)
        if ch.get("status") != d["status"]:
            ch["status"] = d["status"]
            if d["status"] == "suivie" and ch.get("origin") == "découverte":
                ch["note"] = "Découverte que tu as gardée."


# ------------------------------------------------------------------ 2. vérification de l'existant
def verifier_existant(C, chans):
    infos = videos_infos([it["id"] for _, it in C.tous()])
    par_ucid = {ch["ucid"]: ch for ch in chans.values() if ch.get("ucid")}
    for _, it in C.tous():
        v = infos.get(it["id"])
        if v is None or not v["public"]:
            if not it.get("x"):
                it["x"] = 1
                LOG["indispo"] += 1
            continue
        it.pop("x", None)
        it["d"], it["p"] = v["d"], v["p"][:10]
        if v["integrable"]:
            it.pop("e", None)
        else:
            it["e"] = 0
        if it["c"] == AUTRES:
            ch = par_ucid.get(v["cid"])
            if ch and ch.get("status") != "exclue":
                it["c"] = ch["name"]
                it.pop("c2", None)
                LOG["reattribuees"] += 1
            else:
                it["c2"] = v["ctitre"]
    return infos


# ------------------------------------------------------------------ 3. identification des chaînes
def _ressemble(a, b):
    a, b = alnum(a), alnum(b)
    return bool(a and b) and (a in b or b in a)


def _langue_chaine(ucid):
    """Langue dominante des titres récents d'une chaîne ('fr', 'en' ou None)."""
    vids = videos_infos(dernieres_videos(ucid)[:25])
    return langue_titres([v["t"] for v in vids.values()])


def identifier_chaines(C, chans, infos):
    votes = collections.defaultdict(collections.Counter)
    for _, it in C.tous():
        v = infos.get(it["id"])
        if v and it["c"] != AUTRES:
            votes[slug(it["c"])][(v["cid"], v["ctitre"])] += 1
    for s, ch in chans.items():
        # une chaîne reconnue seulement par son nom est contrôlée : ses titres doivent être dans la bonne langue
        if ch.get("ucid") and ch.get("note", "").startswith("Identifiée par son nom") and not ch.get("verif"):
            try:
                if _langue_chaine(ch["ucid"]) == ch.get("l", "fr"):
                    ch["verif"] = True
                else:
                    faux = ch.pop("ucid")
                    ch.pop("maj", None)
                    if faux in ch.get("url", ""):
                        ch.pop("url")
                    for c in C.cat.values():
                        c["items"] = [it for it in c["items"] if infos.get(it["id"], {}).get("cid") != faux]
                    ch["note"] = "Chaîne non identifiée : colle son lien YouTube dans l'onglet Chaînes."
                    probleme(f"{ch['name']} : mauvaise chaîne retirée, lien à fournir.")
                    continue
            except ErreurApi:
                pass
        if ch.get("ucid") or ch.get("status") == "exclue":
            continue
        url = ch.get("url", "")
        ucid, comment = None, ""
        m = re.search(r"/channel/(UC[\w-]{22})", url)
        if m:
            ucid, comment = m.group(1), "lien"
        if not ucid:  # la chaîne réelle de ses vidéos déjà au catalogue
            for (cid, titre), n in votes[s].most_common():
                if _ressemble(titre, ch["name"]):
                    ucid, comment = cid, "vidéos du catalogue"
                    break
        try:
            if not ucid and url:
                m = re.search(r"youtube\.com/(@[\w.\-]+)", url) or re.search(r"youtube\.com/(?:c/|user/)?([\w.\-]+)/?$", url)
                if m:
                    poignee = m.group(1) if m.group(1).startswith("@") else "@" + m.group(1)
                    rep = api("channels", part="id,snippet", forHandle=poignee)
                    if rep.get("items"):
                        ucid, comment = rep["items"][0]["id"], "lien"
            if not ucid:  # dernier recours : recherche par nom, nom strictement identique exigé
                rep = api("search", part="snippet", type="channel", q=ch["name"], maxResults=10,
                          regionCode="FR" if ch.get("l") == "fr" else None)
                memes = [i["snippet"]["channelId"] for i in rep.get("items", [])
                         if alnum(i["snippet"].get("title", "")) == alnum(ch["name"])]
                if memes:
                    det = api("channels", part="statistics", id=",".join(memes)).get("items", [])
                    det.sort(key=lambda c: int(c.get("statistics", {}).get("subscriberCount", 0) or 0), reverse=True)
                    if det and _langue_chaine(det[0]["id"]) == ch.get("l", "fr"):
                        ucid, comment = det[0]["id"], "nom"
                        ch["verif"] = True
                        ch["note"] = "Identifiée par son nom : ouvre le lien pour vérifier que c'est la bonne chaîne."
        except ErreurApi as e:
            probleme(f"{ch['name']} : identification impossible ({e.code}).")
        if ucid:
            ch["ucid"] = ucid
            if comment != "nom":
                ch.pop("note", None)
            if not re.search(r"/channel/UC", url):
                ch.setdefault("url", "https://www.youtube.com/channel/" + ucid)
            LOG["chaines_identifiees"].append(f"{ch['name']} ({comment})")
        else:
            ch["note"] = "Chaîne non identifiée : colle son lien YouTube dans l'onglet Chaînes."
            probleme(f"{ch['name']} : chaîne non identifiée, lien à fournir.")


# ------------------------------------------------------------------ 4. boîte de réception (liens collés)
def traiter_boite(etat, C, chans):
    boite = {k: v for k, v in (etat.get("inbox") or {}).items()
             if isinstance(v, dict) and re.fullmatch(r"[\w-]{11}", k) and k not in C.ids()}
    if not boite:
        return
    infos = videos_infos(boite)
    par_ucid = {ch["ucid"]: ch for ch in chans.values() if ch.get("ucid")}
    for vid, b in boite.items():
        v = infos.get(vid)
        if not v:
            probleme(f"Lien collé introuvable ou privé : {vid}")
            continue
        ch = par_ucid.get(v["cid"]) or chans.get(slug(b.get("c", "")))
        if ch and ch.get("status") == "exclue":
            continue
        nom = ch["name"] if ch else (b.get("c") or v["ctitre"])
        theme = (ch or {}).get("cat") or (b.get("cat") if b.get("cat") in R.THEMES else "sciences")
        if C.ajouter(theme, v, nom, (ch or {}).get("l") or b.get("l") or "fr", "Ajoutée par toi"):
            LOG["boite"] += 1


# ------------------------------------------------------------------ 5. nouveautés des chaînes suivies
def nouveautes(C, chans):
    compte = C.compte_par_chaine()
    suivies = [(s, ch) for s, ch in chans.items() if ch.get("status", "suivie") == "suivie" and ch.get("ucid")]
    # d'abord les chaînes déjà initialisées (vraies nouveautés), puis tes choix, puis les moins représentées
    suivies.sort(key=lambda x: ("maj" not in x[1], x[1].get("origin") != "mathieu", compte[x[0]]))
    ajoutes = 0
    for s, ch in suivies:
        if ajoutes >= R.MAX_PAR_PASSAGE:
            break  # les chaînes restantes seront traitées au prochain passage
        try:
            ids = dernieres_videos(ch["ucid"])
            connus = C.ids()
            infos = videos_infos([i for i in ids if i not in connus])
        except ErreurApi as e:
            probleme(f"{ch['name']} : vidéos illisibles ({e.code} {e.raison}).")
            continue
        cands = [v for v in infos.values() if acceptable(v) and v["cid"] == ch["ucid"]]
        cands.sort(key=lambda v: v["p"], reverse=True)
        if "maj" in ch:
            choisis = [v for v in cands if v["p"] > ch["maj"]][:R.MAX_PAR_CHAINE]
        else:
            limite = (dt.date.today() - dt.timedelta(days=30)).isoformat()
            choisis = [v for v in cands if v["p"][:10] >= limite][:R.MAX_PAR_CHAINE]
            manque = max(0, R.SOCLE_PAR_CHAINE - compte[s] - len(choisis))
            reste = sorted((v for v in cands if v not in choisis), key=lambda v: v["vues"], reverse=True)
            choisis += reste[:manque]
        for v in choisis[:max(0, R.MAX_PAR_PASSAGE - ajoutes)]:
            if C.ajouter(ch.get("cat", "sciences"), v, ch["name"], ch.get("l", "fr"), pourquoi(ch)):
                ajoutes += 1
        dates = [v["p"] for v in infos.values()] + [ch.get("maj", "")]
        ch["maj"] = max(dates) or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if ch.get("note", "").startswith("Chaîne trouvée, vidéos encore introuvables"):
            ch.pop("note")


# ------------------------------------------------------------------ 6. séries
VIDES = {"serie", "series", "cours", "course", "the", "les", "des", "une", "sur", "tout", "savoir", "avec", "pour", "vos", "mes"}


def _mots(s):
    return {m for m in re.findall(r"[a-z0-9]+", norm(s)) if (len(m) >= 4 or m.isdigit()) and m not in VIDES}


def completer_series(C, chans, registre):
    groupes = collections.defaultdict(list)
    for theme, it in C.tous():
        if it.get("s", {}).get("name") and not it.get("x"):
            groupes[it["s"]["name"]].append((theme, it))
    playlists = {}
    for nom, eps in groupes.items():
        ch = chans.get(slug(eps[0][1]["c"]))
        if not ch or not ch.get("ucid") or ch.get("status") == "exclue":
            continue
        reg = registre.setdefault(nom, {})
        try:
            if not reg.get("pl"):
                if reg.get("essai", "") > (dt.date.today() - dt.timedelta(days=56)).isoformat():
                    continue
                reg["essai"] = aujourdhui()
                if ch["ucid"] not in playlists:
                    rep = api("playlists", part="snippet", channelId=ch["ucid"], maxResults=50)
                    playlists[ch["ucid"]] = [(p["id"], p["snippet"].get("title", "")) for p in rep.get("items", [])]
                cible = _mots(nom) - _mots(ch["name"])
                classees = sorted(playlists[ch["ucid"]], key=lambda p: len(cible & _mots(p[1])), reverse=True)
                connus = {it["id"] for _, it in eps}
                for pl, titre in classees[:3]:
                    if not cible & _mots(titre):
                        break
                    contenu = playlist_ids(pl, pages=4)
                    if len(connus & set(contenu)) >= min(2, len(connus)):
                        reg.update(pl=pl, titre=titre)
                        break
                if not reg.get("pl"):
                    continue
            contenu = playlist_ids(reg["pl"], pages=4)
        except ErreurApi as e:
            probleme(f"Série « {nom} » : playlist illisible ({e.code}).")
            continue
        pos = {vid: i + 1 for i, vid in enumerate(contenu)}
        numerotes = [(it["s"].get("n"), pos.get(it["id"])) for _, it in eps if isinstance(it["s"].get("n"), int) and it["id"] in pos]
        coherent = bool(numerotes) and sum(1 for a, b in numerotes if a == b) >= 0.6 * len(numerotes)
        manquants = [vid for vid in contenu if vid not in C.ids()][:5]
        if not manquants:
            continue
        theme = eps[0][0]
        infos = videos_infos(manquants)
        suite = pourquoi(ch).split(" · ", 1)[-1]
        n = 0
        for vid in manquants:
            v = infos.get(vid)
            if not v or not acceptable(v):
                continue
            s = {"name": nom, "n": pos[vid]} if coherent else {"name": nom, "loose": True}
            if C.ajouter(theme, v, ch["name"], eps[0][1].get("l", ch.get("l", "fr")), "Fait partie d'une série · " + suite, serie=s):
                n += 1
        if n:
            LOG["series"].append(f"{nom} : +{n}")


MOTIF_EPISODE = re.compile(
    r"^(.{6,}?)[\s\-–—:|(\[,]*(?:#|n°\s*|ep(?:isode)?\.?\s*|partie\s*|part\s*|chapitre\s*|chapter\s*)(\d{1,3})\b", re.I)


def series_par_titres(C):
    """Nouvelle série dès que 2 vidéos d'une même chaîne ont le même début de titre suivi d'un numéro."""
    groupes = collections.defaultdict(list)
    for _, it in C.tous():
        if it.get("s") or it.get("x") or it["c"] == AUTRES:
            continue
        m = MOTIF_EPISODE.match(it["t"])
        if m and len(alnum(m.group(1))) >= 6:
            groupes[(it["c"], alnum(m.group(1)))].append((it, m.group(1).strip(" -–—:|([,"), int(m.group(2))))
    for (c, _), lst in groupes.items():
        if len({n for _, _, n in lst}) < 2:
            continue
        nom = f"{c} – {lst[0][1]}"
        for it, _, n in lst:
            it["s"] = {"name": nom, "n": n}
            if not it["w"].startswith("Fait partie"):
                it["w"] = "Fait partie d'une série · " + it["w"].split(" · ", 1)[-1]
        LOG["series"].append(f"{nom} : nouvelle série ({len(lst)} épisodes)")


# ------------------------------------------------------------------ 7. découvertes
FR = set("le la les des une est pour dans que qui pas sur avec pourquoi comment faut nous vous au du ce cette son ses mon "
         "ont sont plus tout entre chez leur fait etre avoir quand ou et en un je il elle".split())
EN = set("the of and to is in why how what with for you your this that are from was on it we my can not do does "
         "will have has who when about most ever best into our its an be".split())


def langue_titres(titres):
    fr = en = 0
    for t in titres:
        for m in re.findall(r"[a-z']+", norm(t)):
            fr += m in FR
            en += m in EN
    if max(fr, en) < 3:
        return None
    return "fr" if fr >= en else "en"


def decouvertes(C, chans, infos, etat):
    total = C.total()
    statut = {slug(ch["name"]): ch.get("status", "suivie") for ch in chans.values()}
    deja = sum(1 for _, it in C.tous() if not it.get("x") and statut.get(slug(it["c"])) == "suggérée")
    budget = int(total * R.PART_DECOUVERTES) - deja
    en_attente = sum(1 for ch in chans.values() if ch.get("status") == "suggérée")
    if budget < R.VIDEOS_PAR_DECOUVERTE or en_attente >= R.MAX_DECOUVERTES_EN_ATTENTE:
        return
    marques = etat.get("marks") or {}
    connus = {ch["ucid"] for ch in chans.values() if ch.get("ucid")}
    par_nom = {slug(ch["name"]): ch for ch in chans.values()}
    # candidats : ucid -> {source (nom de chaîne) : poids}
    cand = collections.defaultdict(dict)
    poignees = collections.defaultdict(dict)
    liens_video = collections.defaultdict(dict)

    def note(d, cle, source, poids):
        d[cle][source] = max(d[cle].get(source, 0), poids)

    for _, it in C.tous():
        v = infos.get(it["id"])
        src = par_nom.get(slug(it["c"]))
        if not v or not src or src.get("status") != "suivie":
            continue
        m = marques.get(it["id"]) or {}
        if m.get("r") == -1:
            continue
        poids = 3 if m.get("r") == 1 else 1.5 if m.get("seen") else 0.5 if src.get("origin") == "mathieu" else 0.25
        desc = v["desc"]
        for u in re.findall(r"youtube\.com/channel/(UC[\w-]{22})", desc):
            note(cand, u, src["name"], poids)
        for h in re.findall(r"youtube\.com/(@[\w.\-]{3,30})", desc):
            note(poignees, h.rstrip(".").lower(), src["name"], poids)
        for vid in re.findall(r"(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})", desc):
            note(liens_video, vid, src["name"], poids)
    try:
        # chaînes mises en avant par tes chaînes (relu tous les ~2 mois)
        limite = (dt.date.today() - dt.timedelta(days=R.SECTIONS_TOUS_LES_JOURS)).isoformat()
        for ch in chans.values():
            if ch.get("status", "suivie") != "suivie" or not ch.get("ucid"):
                continue
            if ch.get("sec", "") <= limite:
                rep = api("channelSections", part="snippet,contentDetails", channelId=ch["ucid"])
                amis = []
                for sct in rep.get("items", []):
                    if sct.get("snippet", {}).get("type", "").lower() == "multiplechannels":
                        amis += sct.get("contentDetails", {}).get("channels", [])
                ch["sec"], ch["amis"] = aujourdhui(), amis[:30]
            for u in ch.get("amis", []):
                note(cand, u, ch["name"], 2)
        # vidéos citées en description -> leur chaîne
        tries = sorted(liens_video, key=lambda k: -sum(liens_video[k].values()))[:100]
        for vid, v in videos_infos([i for i in tries if i not in infos]).items():
            for source, poids in liens_video[vid].items():
                note(cand, v["cid"], source, poids)
        for h in sorted(poignees, key=lambda k: -sum(poignees[k].values()))[:30]:
            rep = api("channels", part="id", forHandle=h)
            for c in rep.get("items", []):
                for source, poids in poignees[h].items():
                    note(cand, c["id"], source, poids)
    except ErreurApi as e:
        probleme(f"Découvertes : collecte incomplète ({e.code} {e.raison}).")
    # on écarte les chaînes déjà connues et les auto-citations
    propres = {}
    for u, sources in cand.items():
        if u in connus:
            continue
        score = sum(sources.values())
        if score >= 2:
            propres[u] = (score, sources)
    if not propres:
        return
    tries = sorted(propres, key=lambda u: -propres[u][0])[:50]
    details = {c["id"]: c for c in api("channels", part="snippet,statistics", id=",".join(tries)).get("items", [])}
    retenues = 0
    noms_connus = {alnum(ch["name"]) for ch in chans.values()}
    for u in tries:
        if retenues >= R.NOUVELLES_DECOUVERTES_PAR_PASSAGE or budget < R.VIDEOS_PAR_DECOUVERTE:
            break
        c = details.get(u)
        if not c:
            continue
        titre = c["snippet"].get("title", "")
        stats = c.get("statistics", {})
        if int(stats.get("subscriberCount", 0) or 0) < R.ABONNES_MIN_DECOUVERTE or int(stats.get("videoCount", 0) or 0) < 10:
            continue
        if any(m in norm(titre) for m in R.MAINSTREAM) or alnum(titre) in noms_connus or slug(titre) in chans:
            continue
        score, sources = propres[u]
        try:
            vids = videos_infos(dernieres_videos(u))
        except ErreurApi:
            continue
        bonnes = [v for v in vids.values() if acceptable(v, R.DUREE_MIN_DECOUVERTE) and v["cid"] == u and v["id"] not in C.ids()]
        langue = langue_titres([v["t"] for v in bonnes])
        if len(bonnes) < 3 or langue is None:
            continue
        principale = max(sources, key=sources.get)
        src = par_nom.get(slug(principale), {})
        qui = sorted(sources, key=sources.get, reverse=True)[:3]
        via = "citée par " + " et ".join([", ".join(qui[:-1]), qui[-1]] if len(qui) > 1 else qui)
        ch = chans[slug(titre)] = {"name": titre, "cat": src.get("cat", "sciences"), "l": langue, "status": "suggérée",
                                   "origin": "découverte", "added": aujourdhui(), "ucid": u, "via": via,
                                   "url": "https://www.youtube.com/channel/" + u,
                                   "note": "Découverte " + via + ". Garde-la ou exclus-la.",
                                   "maj": max(v["p"] for v in vids.values())}
        bonnes.sort(key=lambda v: v["vues"], reverse=True)
        for v in bonnes[:R.VIDEOS_PAR_DECOUVERTE]:
            if C.ajouter(ch["cat"], v, titre, langue, pourquoi(ch)):
                budget -= 1
        retenues += 1
        LOG["decouvertes"].append(f"{titre} ({via})")


def retirer_decouvertes_exclues(C, chans):
    exclues = {slug(ch["name"]) for ch in chans.values() if ch.get("status") == "exclue" and ch.get("origin") == "découverte"}
    if exclues:
        for c in C.cat.values():
            c["items"] = [it for it in c["items"] if slug(it["c"]) not in exclues]


# ------------------------------------------------------------------ 8. Hacker News (vidéos anglaises)
def hacker_news(C):
    limite = (dt.date.today() - dt.timedelta(days=120)).isoformat()
    a_voir = [it for _, it in C.tous() if it.get("l") == "en" and not it.get("x") and it.get("hnAt", "") < limite]
    a_voir.sort(key=lambda it: it.get("hnAt", ""))
    for it in a_voir[:R.HN_PAR_PASSAGE]:
        try:
            fils = set()
            for tag in ("story", "comment"):
                q = urllib.parse.urlencode({"query": '"' + it["id"] + '"', "tags": tag, "hitsPerPage": 50})
                rep = http_json("https://hn.algolia.com/api/v1/search?" + q, delai=15)
                for h in rep.get("hits", []):
                    texte = (h.get("url") or "") + " " + (h.get("comment_text") or "") + " " + (h.get("story_text") or "")
                    if it["id"] in texte:
                        fils.add(str(h.get("story_id") or h.get("objectID")))
            it["hn"], it["hnAt"] = len(fils), aujourdhui()
            LOG["hn"] += 1
        except Exception as e:
            probleme(f"Hacker News injoignable ({type(e).__name__}) : comptage reporté.")
            break


# ------------------------------------------------------------------ programme principal
def main():
    if not os.environ.get("YT_API_KEY"):
        print("ERREUR : la clé YT_API_KEY est absente (secret GitHub à créer).")
        return 2
    cat, chans = lire("catalogue.json", {}), lire("chaines.json", {})
    registre, journal = lire("series.json", {}), lire("journal.json", {})
    C = Catalogue(cat)
    avant = C.total()
    etat = lire_etat()
    etapes = [
        ("Décisions prises sur le site", lambda: appliquer_decisions(etat, chans)),
        ("Vérification des vidéos existantes", None),
        ("Identification des chaînes", None),
        ("Liens collés", lambda: traiter_boite(etat, C, chans)),
        ("Nouveautés des chaînes suivies", lambda: nouveautes(C, chans)),
        ("Séries (playlists)", lambda: completer_series(C, chans, registre)),
        ("Séries (titres)", lambda: series_par_titres(C)),
        ("Découvertes", None),
        ("Retrait des découvertes exclues", lambda: retirer_decouvertes_exclues(C, chans)),
        ("Hacker News", lambda: hacker_news(C)),
    ]
    infos = {}
    try:
        for nom, f in etapes:
            print("→ " + nom)
            if nom.startswith("Vérification"):
                infos = verifier_existant(C, chans)
            elif nom.startswith("Identification"):
                identifier_chaines(C, chans, infos)
                # une fois les chaînes identifiées, on rattache les « Autres créateurs » qui leur appartiennent
                par_ucid = {ch["ucid"]: ch for ch in chans.values() if ch.get("ucid") and ch.get("status") != "exclue"}
                for _, it in C.tous():
                    v = infos.get(it["id"])
                    if it["c"] == AUTRES and v and v["cid"] in par_ucid:
                        it["c"] = par_ucid[v["cid"]]["name"]
                        it.pop("c2", None)
                        LOG["reattribuees"] += 1
            elif nom == "Découvertes":
                decouvertes(C, chans, infos, etat)
            else:
                f()
    except QuotaEpuise:
        probleme("Quota YouTube du jour épuisé : passage interrompu, la suite se fera la semaine prochaine.")
    except ErreurApi as e:
        probleme(f"Erreur YouTube inattendue ({e}) : passage interrompu.")
        if e.code in (400, 403) and QUOTA["n"] <= 2:
            print("ERREUR : la clé API YouTube est refusée. Vérifie le secret YT_API_KEY.")
            return 2

    resume = {
        "date": aujourdhui(),
        "total": C.total(),
        "ajouts": dict(LOG["ajouts"]),
        "titres": LOG["titres"][:60],
        "series": LOG["series"],
        "decouvertes": LOG["decouvertes"],
        "indisponibles": LOG["indispo"],
        "reattribuees": LOG["reattribuees"],
        "liens_colles": LOG["boite"],
        "hn": LOG["hn"],
        "problemes": LOG["problemes"],
        "quota": QUOTA["n"],
    }
    journal = {"maj": aujourdhui(), "dernier": resume, "historique": ([resume] + journal.get("historique", []))[:12]}
    for k in ("titres",):
        for h in journal["historique"][1:]:
            h.pop(k, None)
    ecrire("catalogue.json", cat)
    ecrire("chaines.json", chans)
    ecrire("series.json", registre)
    ecrire("journal.json", journal)

    lignes = [f"## Canal Curieux — mise à jour du {resume['date']}",
              f"- {sum(LOG['ajouts'].values())} vidéo(s) ajoutée(s), {resume['total']} au catalogue",
              f"- Par thème : " + (", ".join(f"{R.THEMES.get(k, k)} +{n}" for k, n in LOG["ajouts"].items()) or "aucun ajout"),
              f"- Séries : " + ("; ".join(LOG["series"]) or "rien de nouveau"),
              f"- Découvertes : " + ("; ".join(LOG["decouvertes"]) or "aucune"),
              f"- Chaînes identifiées : {len(LOG['chaines_identifiees'])} · vidéos disparues : {LOG['indispo']} · "
              f"rattachées à leur chaîne : {LOG['reattribuees']} · Hacker News vérifiées : {LOG['hn']}",
              f"- Quota YouTube utilisé : {QUOTA['n']} unités sur 10 000",
              "- Points d'attention : " + ("; ".join(LOG["problemes"]) or "aucun")]
    print("\n".join(lignes))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n".join(lignes) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
