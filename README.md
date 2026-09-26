# brvm-data

Cours historiques et indicateurs techniques des **49 sociétés cotées** et des
**18 indices** de la **BRVM**, mis à jour automatiquement chaque jour de bourse.

Ces fichiers alimentent le serveur MCP `brvm-mcp`, qui sert les données à un
assistant d'analyse.

---

## Pourquoi ce dépôt existe

Le serveur MCP lisait auparavant les CSV du dépôt `Fredysessie/brvm-data-public`.
**Ce dépôt a été supprimé en septembre 2026**, sans préavis, et quatre outils sur
cinq sont tombés d'un coup.

Ce dépôt-ci reconstruit la même chaîne, mais sous notre contrôle. Point
important : le serveur MCP **ne calcule rien**, il recopie ces fichiers. Le RSI,
le Beta et les variations qu'il affiche sont ceux produits ici.

## Ce qu'il contient

```
data/{TICKER}/
    {TICKER}.daily.csv        une ligne par séance
    {TICKER}.weekly.csv       agrégé, semaine étiquetée au lundi de fin
    {TICKER}.monthly.csv      agrégé, dernier jour du mois
    {TICKER}.quarterly.csv    agrégé, dernier jour du trimestre
    {TICKER}.yearly.csv       agrégé, 31 décembre
    {TICKER}.indicator.csv    32 colonnes, une seule ligne : l'état du jour
```

Cours — colonnes `Date,Open,High,Low,Close,Volume`, dates ISO.
Agrégation : `Open` = première séance de la période, `Close` = dernière,
`High` = maximum, `Low` = minimum, `Volume` = somme.

## Couverture

| | Nombre | Historique |
|---|---|---|
| Actions | 49 | jusqu'à 28 ans (SNTS depuis 1998) |
| Indices | 18 | BRVM Composite depuis 1998, 6 651 séances |

Les sept indices sectoriels d'avant la réforme (`BRVMAG`, `BRVMAS`, `BRVMDI`,
`BRVMFI`, `BRVMIN`, `BRVMSP`, `BRVMTR`) sont **gelés au 31/12/2025** : ils ont
été remplacés par la nouvelle nomenclature. On les collecte quand même, leur
historique remonte à 1999.

## Les indicateurs

`{TICKER}.indicator.csv` porte 32 colonnes sur une seule ligne.

### Deux formats de variation, à ne pas confondre

| Colonne | Format | Exemple | Lu par |
|---|---|---|---|
| `Variation_Cours` | chaîne, virgule, `%`, signe explicite | `+2,83%` | `get_market_overview` pour compter hausses et baisses |
| `*_Variation` (6 fenêtres) | décimal | `-0.042553` | `screen_market` pour filtrer |

Se tromper de format casse le filtrage **en silence**, sans erreur visible.

### Méthodes de calcul

**RSI** — 14 jours, lissage de Wilder. Une moyenne mobile simple donnerait un
autre chiffre, qui ne correspondrait à aucun RSI publié ailleurs.
Vérifié au centième contre le RSI affiché par richbourse sur 11 titres :
écart moyen **0,00**.

**Beta 1 an** — covariance des rendements quotidiens du titre et de ceux du
**BRVM Composite**, divisée par la variance de ceux de l'indice, sur les 252
dernières séances communes. Laissé vide si le titre a décroché de la cote : un
Beta « 1 an » calculé sur 2019 pour un titre radié serait un chiffre faux
présenté comme frais.

**Fenêtres** — 1 semaine = 5 séances, 1 mois = 21, 1 an = 252, 3 ans = 756,
5 ans = 1260. `1er_Janvier` = depuis la première séance de l'année en cours.
Plus haut et plus bas viennent des colonnes `High` et `Low`, pas des clôtures.
La variation compare la dernière clôture à la **première clôture de la
fenêtre**.

**Valorisation et Capital_Echange** — dépendent du nombre de titres, relevé sur
la fiche société de richbourse et stocké dans `scraper/actions.json`. Laissés
**vides** quand ce nombre est inconnu, jamais estimés.

## Sources

Cours des actions :

```
GET https://www.richbourse.com/common/mouvements/technique-donnees
    ?symbole={TICKER}&complet=1
    Referer: https://www.richbourse.com/common/mouvements/technique/{TICKER}
```
Réponse : `{ "ohlc": [[ts, O, H, L, C], ...], "volume": [[ts, V], ...] }`

Cours des indices — **autre endpoint, autre paramètre, autre clé** :

```
GET https://www.richbourse.com/common/mouvements/indice-donnees
    ?alias_indice={ALIAS}&complet=1
    Referer: https://www.richbourse.com/common/mouvements/indice/{ALIAS}
```
Réponse : `{ "cours": [[ts, valeur], ...] }` — 2 cases par ligne, pas de volume.
L'alias est le nom long (`BRVM-COMPOSITE`), pas le ticker court (`BRVMC`). La
table de correspondance est dans `scraper/indices.json`.

Nombre de titres :
`https://www.richbourse.com/common/apprendre/details-societe/{TICKER}`,
champ « Nombre de titres ».

Dans les trois cas, `User-Agent` de navigateur et `X-Requested-With:
XMLHttpRequest` obligatoires. Sans `&complet=1`, l'endpoint ne renvoie que 5 ans.

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
clôture de 15h00 :

1. `faire_actions.py` — relève le nombre de titres
2. `collecte.py` — 49 actions + 18 indices
3. `indicateurs.py` — RSI, Beta, variations
4. `controle_rsi.py` — compare le RSI à la référence (n'arrête pas le job)
5. commit des fichiers réellement modifiés

Le job **échoue volontairement** dans quatre cas :

- plus de la moitié des tickers en échec à la collecte
- plus de la moitié en échec au calcul des indicateurs
- la fiche société n'est plus lisible
- aucune donnée fraîche depuis plus de 3 jours ouvrés

C'est délibéré. Un serveur qui tombe franchement se répare ; un serveur qui sert
de vieilles données en silence fait prendre de mauvaises décisions.

## Lancer à la main

```bash
python scraper/collecte.py              # 49 actions + 18 indices
python scraper/collecte.py NSBC BRVMC   # seulement ceux-là
python scraper/indicateurs.py           # après la collecte, jamais avant
python scraper/verifier.py NSBC         # contrôle qualité des cours
python scraper/controle_rsi.py          # RSI contre la référence richbourse
python scraper/faire_actions.py         # régénère scraper/actions.json
```

Aucune dépendance : bibliothèque standard Python uniquement.

## Maintenance

| Événement | Action |
|---|---|
| Nouvelle société cotée | Ajouter à `scraper/tickers.json`, à `ACTIONS` dans `faire_tickers.py`, et à `STOCK_TICKERS` dans le serveur MCP |
| Nouvel indice | Ajouter à `scraper/indices.json` (ticker court → alias long) |
| Augmentation de capital | `faire_actions.py` la rattrape au prochain passage, la ligne est marquée `CHANGEMENT` dans le journal |
| **26 octobre 2026** | Fractionnement Sonatel, 1 action → 10. Vérifier ce jour-là si la source réajuste l'historique des cours ; `actions.json` se met à jour tout seul |
| Le workflow échoue | La source a probablement changé. Lire le journal du job |

## Titres à surveiller

- **SVOC** ne cote plus depuis le 10 mai 2019. Déjà retiré du serveur MCP,
  conservé ici pour l'historique. Son `indicator.csv` porte les valeurs de 2019
  et son Beta est vide, à dessein.
- **BBGC** (Bridge Bank) cote depuis le 24/09/2026 : pas encore de RSI ni de
  Beta, l'historique est trop court.
- **SEMC** et **SICC** s'arrêtent au 15 septembre 2026 : titres peu liquides,
  pas d'anomalie.
