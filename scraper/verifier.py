# -*- coding: utf-8 -*-
"""Controle qualite de la collecte : comparaison avec l'ancien depot
et coherence des agregations."""
import csv, os, sys, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NOUVEAU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ANCIEN = "C:/Users/Yanick/Desktop/BRVM/brvm-data-public/data"


def lire(chemin):
    if not os.path.exists(chemin):
        return {}
    out = {}
    for r in csv.DictReader(open(chemin, encoding="utf-8")):
        out[r["Date"]] = (r["Open"], r["High"], r["Low"], r["Close"], r["Volume"])
    return out


def egal(a, b):
    try:
        return all(abs(float(x or 0) - float(y or 0)) < 0.01 for x, y in zip(a, b))
    except ValueError:
        return a == b


def comparer(ticker):
    print("=" * 66)
    print(ticker)
    n = lire(os.path.join(NOUVEAU, ticker, "%s.daily.csv" % ticker))
    a = lire(os.path.join(ANCIEN, ticker, "%s.daily.csv" % ticker))
    if not a:
        print("  pas d'ancien fichier, rien a comparer (%d seances collectees)" % len(n))
        return
    communes = sorted(set(n) & set(a))
    if not communes:
        print("  aucune date commune")
        return
    ecarts = [d for d in communes if not egal(n[d], a[d])]
    print("  ancien   : %5d seances, jusqu'au %s" % (len(a), max(a)))
    print("  nouveau  : %5d seances, jusqu'au %s" % (len(n), max(n)))
    print("  communes : %5d  |  ecarts : %d" % (len(communes), len(ecarts)))
    if ecarts:
        for d in ecarts[:5]:
            print("     %s  ancien=%s  nouveau=%s" % (d, a[d], n[d]))
    else:
        print("  -> identique sur toute la periode commune")
    nouvelles = sorted(set(n) - set(a))
    if nouvelles:
        print("  seances gagnees : %d (du %s au %s)" % (len(nouvelles), nouvelles[0], nouvelles[-1]))


def coherence(ticker):
    """Le total des volumes et la derniere cloture doivent se retrouver
    dans chaque agregation."""
    d = os.path.join(NOUVEAU, ticker)
    base = list(csv.DictReader(open(os.path.join(d, "%s.daily.csv" % ticker), encoding="utf-8")))
    if not base:
        return
    dernier_close = base[-1]["Close"]
    total_vol = sum(float(r["Volume"] or 0) for r in base)
    print("  agregations :")
    for per in ["weekly", "monthly", "quarterly", "yearly"]:
        rows = list(csv.DictReader(open(os.path.join(d, "%s.%s.csv" % (ticker, per)), encoding="utf-8")))
        v = sum(float(r["Volume"] or 0) for r in rows)
        ok_close = rows[-1]["Close"] == dernier_close
        ok_vol = abs(v - total_vol) < 1
        print("    %-10s %4d lignes  cloture finale %s  volume total %s"
              % (per, len(rows), "OK" if ok_close else "DIFFERENT", "OK" if ok_vol else "DIFFERENT"))


if __name__ == "__main__":
    cibles = [t.upper() for t in sys.argv[1:]] or ["NSBC", "SNTS", "BBGC"]
    for t in cibles:
        comparer(t)
        coherence(t)
        print()
