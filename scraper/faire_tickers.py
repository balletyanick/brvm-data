# -*- coding: utf-8 -*-
"""Construit tickers.json a partir des anciens CSV, et ajoute les nouveaux titres.

Le champ URL_Ticker des anciens fichiers porte le suffixe pays (.ci, .sn, ...).
On le fige ici pour ne plus jamais dependre de l'ancien depot.
"""
import csv, json, os, sys, glob

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ANCIEN = "C:/Users/Yanick/Desktop/BRVM/brvm-data-public/data"
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tickers.json")

# Actions suivies par le serveur MCP (server.py, STOCK_TICKERS) + les nouvelles.
ACTIONS = [
    "ABJC", "BICB", "BICC", "BNBC", "BOAB", "BOABF", "BOAC", "BOAM", "BOAN", "BOAS",
    "CABC", "CBIBF", "CFAC", "CIEC", "ECOC", "ETIT", "FTSC", "LNBB", "NEIC", "NSBC",
    "NTLC", "ONTBF", "ORAC", "ORGT", "PALC", "PRSC", "SAFC", "SCRC", "SDCC", "SDSC",
    "SEMC", "SGBC", "SHEC", "SIBC", "SICC", "SIVC", "SLBC", "SMBC", "SNTS", "SOGC",
    "SPHC", "STAC", "STBC", "SVOC", "TTLC", "TTLS", "UNLC", "UNXC",
    "BBGC",   # Bridge Bank Group CI, premiere cotation le 24/09/2026
]

# Suffixes connus pour les titres absents de l'ancien depot.
MANUEL = {"BBGC": "BBGC.ci"}


def main():
    suffixes = {}
    for f in glob.glob(os.path.join(ANCIEN, "*", "*.indicator.csv")):
        t = os.path.basename(f).split(".")[0]
        try:
            row = next(csv.DictReader(open(f, encoding="utf-8")))
            u = (row.get("URL_Ticker") or "").strip()
            if u:
                suffixes[t] = u
        except Exception:
            pass

    table, manquants = {}, []
    for t in ACTIONS:
        u = suffixes.get(t) or MANUEL.get(t)
        if u:
            table[t] = u
        else:
            manquants.append(t)

    json.dump({"actions": table}, open(SORTIE, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    pays = {}
    for u in table.values():
        s = u.rsplit(".", 1)[-1]
        pays[s] = pays.get(s, 0) + 1

    print("tickers resolus : %d / %d" % (len(table), len(ACTIONS)))
    print("repartition par pays :", pays)
    if manquants:
        print("MANQUANTS (a renseigner dans MANUEL) :", manquants)
    print("ecrit dans", SORTIE)


if __name__ == "__main__":
    main()
