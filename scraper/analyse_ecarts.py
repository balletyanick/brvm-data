# -*- coding: utf-8 -*-
"""Pourquoi les High/Low different de l'ancien depot ?

Hypothese : l'endpoint graphique de richbourse ne renvoie pas les vrais
extremes intra-seance pour les donnees anciennes, mais seulement le corps de
la bougie, c'est-a-dire High = max(Open, Close) et Low = min(Open, Close).
"""
import csv, os, sys, collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NOUVEAU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ANCIEN = "C:/Users/Yanick/Desktop/BRVM/brvm-data-public/data"


def lire(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


for ticker in sys.argv[1:] or ["NSBC", "SNTS"]:
    n = lire(os.path.join(NOUVEAU, ticker, "%s.daily.csv" % ticker))
    a = {r["Date"]: r for r in lire(os.path.join(ANCIEN, ticker, "%s.daily.csv" % ticker))}

    print("=" * 70)
    print(ticker)

    # 1. le corps de la bougie explique-t-il nos valeurs ?
    colles, vrais = 0, 0
    par_annee = collections.Counter()
    vrais_par_annee = collections.Counter()
    for r in n:
        o, h, b, c = f(r["Open"]), f(r["High"]), f(r["Low"]), f(r["Close"])
        if None in (o, h, b, c):
            continue
        an = r["Date"][:4]
        par_annee[an] += 1
        if h == max(o, c) and b == min(o, c):
            colles += 1
        else:
            vrais += 1
            vrais_par_annee[an] += 1
    total = colles + vrais
    print("  seances ou High/Low = corps de la bougie : %d / %d (%.1f%%)"
          % (colles, total, 100 * colles / total if total else 0))

    # 2. a partir de quand les vrais extremes apparaissent-ils ?
    print("  part de seances avec de vrais extremes, par annee :")
    for an in sorted(par_annee):
        tot, vr = par_annee[an], vrais_par_annee[an]
        if tot >= 20:
            print("     %s : %5.1f%%  (%d/%d)" % (an, 100 * vr / tot, vr, tot))

    # 3. verifier l'hypothese sur les ecarts avec l'ancien
    if a:
        conforme, autre = 0, []
        for r in n:
            d = r["Date"]
            if d not in a:
                continue
            o, h, b, c = f(r["Open"]), f(r["High"]), f(r["Low"]), f(r["Close"])
            ao, ah, ab, ac = (f(a[d]["Open"]), f(a[d]["High"]), f(a[d]["Low"]), f(a[d]["Close"]))
            if (h, b) == (ah, ab):
                continue
            # l'ancien contient-il un extreme plus large, et le notre le corps ?
            if h == max(o, c) and b == min(o, c) and ah >= h and ab <= b and (o, c) == (ao, ac):
                conforme += 1
            else:
                autre.append((d, (ao, ah, ab, ac), (o, h, b, c)))
        print("  ecarts expliques par l'hypothese : %d" % conforme)
        print("  ecarts NON expliques             : %d" % len(autre))
        for x in autre[:5]:
            print("     %s  ancien=%s  nouveau=%s" % x)
    print()
