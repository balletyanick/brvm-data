# -*- coding: utf-8 -*-
"""Phase 1 — collecte des cours BRVM depuis richbourse.

Pour chaque ticker, recupere l'historique complet en JSON et ecrit cinq CSV :
  data/{T}/{T}.daily.csv      une ligne par seance
  data/{T}/{T}.weekly.csv     agrege, semaine etiquetee au lundi de fin
  data/{T}/{T}.monthly.csv    agrege, dernier jour du mois
  data/{T}/{T}.quarterly.csv  agrege, dernier jour du trimestre
  data/{T}/{T}.yearly.csv     agrege, 31 decembre

Aucune dependance externe : uniquement la bibliotheque standard.

Usage :
    python collecte.py              tous les tickers
    python collecte.py NSBC SNTS    seulement ceux-la
"""
import csv, datetime, io, json, os, sys, time, urllib.error, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_DATA = os.path.join(RACINE, "data")
TICKERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tickers.json")

BASE = "https://www.richbourse.com/common/mouvements/technique-donnees"
ENTETES = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}
PAUSE = 0.6          # secondes entre deux tickers
ESSAIS = 3           # tentatives par ticker
MIN_SEANCES = 2      # en dessous, on considere la reponse suspecte

COLONNES = ["Date", "Open", "High", "Low", "Close", "Volume"]


# ----------------------------------------------------------------- reseau

def recuperer(ticker):
    """Retourne [(date, o, h, l, c, v), ...] trie par date, ou leve une exception."""
    url = "%s?symbole=%s&complet=1" % (BASE, ticker)
    entetes = dict(ENTETES)
    entetes["Referer"] = "https://www.richbourse.com/common/mouvements/technique/%s" % ticker

    derniere = None
    for essai in range(1, ESSAIS + 1):
        try:
            req = urllib.request.Request(url, headers=entetes)
            with urllib.request.urlopen(req, timeout=40) as r:
                ctype = r.headers.get("Content-Type", "")
                brut = r.read()
            if "json" not in ctype:
                raise ValueError("reponse non JSON (%s)" % ctype[:40])
            d = json.loads(brut.decode("utf-8"))
            break
        except Exception as e:
            derniere = e
            if essai < ESSAIS:
                time.sleep(2 * essai)
    else:
        raise derniere

    cours = d.get("ohlc") or d.get("cours") or []
    volumes = {int(x[0]): x[1] for x in (d.get("volume") or []) if x and x[0] is not None}

    lignes = []
    for ligne in cours:
        if not ligne or ligne[0] is None:
            continue
        ts = int(ligne[0])
        jour = datetime.datetime.fromtimestamp(ts / 1000, datetime.UTC).date()
        if len(ligne) >= 5:
            o, h, b, c = ligne[1], ligne[2], ligne[3], ligne[4]
        else:                      # indices : [timestamp, cours]
            o = h = b = c = ligne[1]
        if c is None:
            continue
        lignes.append((jour, o, h, b, c, volumes.get(ts, 0)))

    lignes.sort(key=lambda x: x[0])
    return lignes


# ------------------------------------------------------------- agregation

def fin_semaine(d):
    """Lundi qui cloture la semaine, convention des anciens fichiers."""
    return d + datetime.timedelta(days=(7 - d.weekday()) % 7)


def fin_mois(d):
    if d.month == 12:
        return datetime.date(d.year, 12, 31)
    return datetime.date(d.year, d.month + 1, 1) - datetime.timedelta(days=1)


def fin_trimestre(d):
    m = ((d.month - 1) // 3 + 1) * 3
    return fin_mois(datetime.date(d.year, m, 1))


def fin_annee(d):
    return datetime.date(d.year, 12, 31)


def agreger(lignes, cle):
    """Regroupe les seances par periode. Open = premiere, Close = derniere,
    High = max, Low = min, Volume = somme."""
    paquets = {}
    ordre = []
    for jour, o, h, b, c, v in lignes:
        etiquette = cle(jour)
        if etiquette not in paquets:
            paquets[etiquette] = [o, h, b, c, v or 0]
            ordre.append(etiquette)
        else:
            p = paquets[etiquette]
            if h is not None:
                p[1] = h if p[1] is None else max(p[1], h)
            if b is not None:
                p[2] = b if p[2] is None else min(p[2], b)
            p[3] = c
            p[4] += (v or 0)
    return [(e, *paquets[e]) for e in sorted(ordre)]


# ---------------------------------------------------------------- ecriture

def nombre(x):
    """Entier si la valeur est entiere, sinon flottant. Vide si None."""
    if x is None:
        return ""
    f = float(x)
    return str(int(f)) if f.is_integer() else repr(f)


def ecrire(chemin, lignes):
    """Ecrit le CSV. Retourne True si le contenu a change, False sinon.

    Ne pas reecrire un fichier identique evite des commits vides et garde
    l'historique git lisible.
    """
    tampon = io.StringIO()
    w = csv.writer(tampon, lineterminator="\n")
    w.writerow(COLONNES)
    for jour, o, h, b, c, v in lignes:
        w.writerow([jour.isoformat(), nombre(o), nombre(h), nombre(b),
                    nombre(c), nombre(v)])
    contenu = tampon.getvalue()

    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            if f.read() == contenu:
                return False

    with open(chemin, "w", newline="", encoding="utf-8") as f:
        f.write(contenu)
    return True


def traiter(ticker):
    """Retourne (ok, message, derniere_date)."""
    try:
        lignes = recuperer(ticker)
    except Exception as e:
        return False, "reseau : %s" % e, None

    if len(lignes) < MIN_SEANCES:
        return False, "seulement %d seance(s), on ne remplace rien" % len(lignes), None

    dossier = os.path.join(DOSSIER_DATA, ticker)
    os.makedirs(dossier, exist_ok=True)

    jeux = {
        "daily": lignes,
        "weekly": agreger(lignes, fin_semaine),
        "monthly": agreger(lignes, fin_mois),
        "quarterly": agreger(lignes, fin_trimestre),
        "yearly": agreger(lignes, fin_annee),
    }
    modifies = 0
    for periode, jeu in jeux.items():
        if ecrire(os.path.join(dossier, "%s.%s.csv" % (ticker, periode)), jeu):
            modifies += 1

    marque = "" if modifies else "  (inchange)"
    return True, "%5d seances, du %s au %s%s" % (
        len(lignes), lignes[0][0], lignes[-1][0], marque), lignes[-1][0]


# -------------------------------------------------------------------- main

def main():
    table = json.load(open(TICKERS, encoding="utf-8"))["actions"]
    demandes = [t.upper() for t in sys.argv[1:]] or sorted(table)

    os.makedirs(DOSSIER_DATA, exist_ok=True)
    print("Collecte de %d ticker(s)\n" % len(demandes))

    ok, echecs, dates = 0, [], []
    for i, t in enumerate(demandes, 1):
        reussi, message, derniere = traiter(t)
        etat = "OK  " if reussi else "ECHEC"
        print("  [%2d/%2d] %-6s %s %s" % (i, len(demandes), t, etat, message))
        if reussi:
            ok += 1
            if derniere:
                dates.append(derniere)
        else:
            echecs.append((t, message))
        if i < len(demandes):
            time.sleep(PAUSE)

    print("\n%d/%d reussis" % (ok, len(demandes)))
    if echecs:
        print("Echecs :")
        for t, m in echecs:
            print("   %-6s %s" % (t, m))

    # --- garde-fous : le job doit echouer bruyamment ---------------------

    if ok < len(demandes) / 2:
        print("\nALERTE : plus de la moitie des tickers en echec, collecte cassee.")
        sys.exit(1)

    if dates:
        plus_recente = max(dates)
        aujourdhui = datetime.datetime.now(datetime.UTC).date()
        ouvres = 0
        j = plus_recente
        while j < aujourdhui:
            j += datetime.timedelta(days=1)
            if j.weekday() < 5:
                ouvres += 1
        print("Seance la plus recente collectee : %s (%d jour(s) ouvre(s) de retard)"
              % (plus_recente, ouvres))
        if ouvres > 3:
            print("\nALERTE : aucune donnee fraiche depuis plus de 3 jours ouvres.")
            print("La source a probablement change. Ne pas faire confiance aux CSV.")
            sys.exit(1)


if __name__ == "__main__":
    main()
