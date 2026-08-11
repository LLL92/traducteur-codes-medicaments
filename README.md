# Traducteur de codes médicaments — interopérabilité BDPM / standards internationaux

Outil et analyses autour de l'interopérabilité des codifications pharmaceutiques
françaises (CIS, CIP7, CIP13, DCI) et de leur mise en correspondance avec les
référentiels ouverts BDPM (ANSM) et Open Medic (CNAM).

Le projet comporte deux volets :

- un **outil interactif** de traduction de codes médicaments, utilisable en local
  ou en ligne, sans installation côté utilisateur ;
- une série de **scripts d'analyse** sur les données ouvertes (recouvrement
  BDPM / Open Medic, codes orphelins, qualité et mappabilité des correspondances).

## Structure du dépôt

```
app/          L'outil interactif (notebooks marimo)
analyses/     Les scripts d'analyse des données ouvertes
  resultats/  Les sorties produites par les scripts (.json / .txt)
docs/         La version web de l'outil (export WebAssembly, déployable en statique)
```

## L'outil

`app/traducteur_codes_medicaments.py` — version locale. Trois modes :
recherche par nom commercial ou substance, traduction directe d'un code
(CIS / CIP7 / CIP13), et comparaison d'un fichier d'identifiants au référentiel.
Résultats exportables en CSV.

`app/traducteur_codes_medicaments_web.py` — variante pour exécution en navigateur
(WebAssembly / Pyodide), utilisée pour le déploiement web.

`app/piste_ia_recherche_intelligente.py` — prototype exploratoire d'une couche
d'assistance à la recherche, écarté de l'outil final (conservé à titre documentaire).

### Lancer l'outil en local

```
uv run marimo run app/traducteur_codes_medicaments.py
```

Au démarrage, l'outil demande les trois fichiers de la BDPM
(`CIS_bdpm.txt`, `CIS_CIP_bdpm.txt`, `CIS_COMPO_bdpm.txt`), à déposer par
glisser-déposer ou en indiquant leur dossier.

## Les analyses

Les scripts de `analyses/` s'exécutent indépendamment. Ils attendent les
fichiers sources dans un dossier `data/` (voir ci-dessous) et écrivent leurs
sorties dans `analyses/resultats/`.

```
uv run python analyses/04_serie_temporelle_orphelins.py
```

## Données

Les données ne sont pas incluses dans le dépôt. Les télécharger séparément :

- **BDPM** (base de données publique des médicaments, ANSM) :
  https://base-donnees-publique.medicaments.gouv.fr/
- **Open Medic** (dépenses de médicaments, CNAM) :
  https://www.assurance-maladie.ameli.fr/etudes-et-donnees/open-medic-base-complete-depenses-medicaments

Placer les fichiers dans un dossier `data/` à la racine du projet.

## Dépendances

Gérées avec [uv](https://github.com/astral-sh/uv). Les versions sont figées dans
`uv.lock`.

```
uv sync
```

## Licence

Licence à confirmer.
