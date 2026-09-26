# brvm-data

Cours historiques des 49 sociétés cotées à la **BRVM**, mis à jour
automatiquement chaque jour de bourse.

Ces fichiers alimentent le serveur MCP `brvm-mcp`, qui sert les données à un
assistant d'analyse.

---

## Pourquoi ce dépôt existe

Le serveur MCP lisait auparavant les CSV du dépôt `Fredysessie/brvm-data-public`.
**Ce dépôt a été supprimé en septembre 2026**, sans préavis, et quatre outils sur
cinq sont tombés d'un coup.

Ce dépôt-ci reconstruit la même chaîne, mais sous notre contrôle.

## Ce qu'il contient

```
data/{TICKER}/
    {TICKER}.daily.csv        une ligne par séance
    {TICKER}.weekly.csv       agrégé, semaine étiquetée au lundi de fin
    {TICKER}.monthly.csv      agrégé, dernier jour du mois
    {TICKER}.quarterly.csv    agrégé, dernier jour du trimestre
    {TICKER}.yearly.csv       agrégé, 31 décembre
```

Colonnes : `Date,Open,High,Low,Close,Volume`. Dates au format ISO.

Règle d'agrégation : `Open` = première séance de la période, `Close` = dernière,
`High` = maximum, `Low` = minimum, `Volume` = somme.

## Couverture

49 tickers, jusqu'à **28 ans d'historique** sur les plus anciens.

| Ticker | Séances | Depuis |
|---|---|---|
| SNTS | 6 515 | 1998 |
| BOAB | 5 443 | 2000 |
| CIEC | 5 445 | 1998 |
| SHEC | 4 945 | 1998 |
| BBGC | 2 | 2026 |

## Source

`richbourse.com`, endpoint du graphique d'analyse technique :

```
GET https://www.richbourse.com/common/mouvements/technique-donnees
    ?symbole={TICKER}&complet=1

En-têtes :
    User-Agent: Mozilla/5.0 (...)
    X-Requested-With: XMLHttpRequest
    Referer: https://www.richbourse.com/common/mouvements/technique/{TICKER}
```

Réponse JSON : `{ "ohlc": [[ts, O, H, L, C], ...], "volume": [[ts, V], ...], "complet": true }`.
Sans `&complet=1`, l'endpoint ne renvoie que 5 ans.

## Qualité des données

Contrôlées contre l'ancien dépôt sur 8 476 séances communes :

| Champ | Écarts |
|---|---|
| **Open** | **0** |
| **Close** | **0** |
| **Volume** | **0** |
| High / Low | 4 à 12 % des séances anciennes |

Les clôtures, les ouvertures et les volumes sont fiables. En revanche, **les
extrêmes intra-séance sont approximatifs sur les données anciennes** : avant
2013, la source ne fournit souvent que le corps de la bougie, c'est-à-dire
`High = max(Open, Close)` et `Low = min(Open, Close)`. La précision remonte
ensuite, jusqu'à 83-90 % de vrais extrêmes sur 2024-2026.

Conséquence : se fier aux clôtures pour tout calcul. Traiter les plus hauts et
plus bas sur fenêtres longues comme des approximations.

## Automatisation

`.github/workflows/maj.yml` tourne **du lundi au vendredi à 16h30 UTC**, après la
clôture de 15h00. Il collecte, écrit les CSV modifiés seulement, et commite.

Le job **échoue volontairement** dans deux cas :

- plus de la moitié des tickers en échec
- aucune donnée fraîche depuis plus de 3 jours ouvrés

C'est délibéré. Un serveur qui tombe franchement se répare ; un serveur qui sert
de vieilles données en silence fait prendre de mauvaises décisions.

## Lancer à la main

```bash
python scraper/collecte.py            # les 49 tickers
python scraper/collecte.py NSBC SNTS  # seulement ceux-là
python scraper/verifier.py NSBC       # contrôle qualité
```

Aucune dépendance : bibliothèque standard Python uniquement.

## Maintenance

| Événement | Action |
|---|---|
| Nouvelle société cotée | Ajouter à `scraper/tickers.json` et à `ACTIONS` dans `faire_tickers.py` |
| Fractionnement ou augmentation de capital | Vérifier si la source réajuste l'historique |
| **26 octobre 2026** | Fractionnement Sonatel, 1 action → 10 |
| Le workflow échoue | La source a probablement changé. Lire le journal du job |

## Titres à surveiller

- **SVOC** ne cote plus depuis le 10 mai 2019. À retirer de la liste.
- **SEMC** et **SICC** s'arrêtent au 15 septembre 2026 : titres peu liquides,
  pas d'anomalie.
