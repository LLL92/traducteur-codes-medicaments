import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    """Traducteur de codes médicaments (CIS, CIP7, CIP13, DCI) — version web.

    Application interactive à trois modes : recherche par nom commercial
    ou substance, traduction directe d'un code, et comparaison d'un fichier
    d'identifiants au référentiel BDPM. Les données BDPM sont fournies par
    l'utilisateur au démarrage ; les résultats sont exportables en CSV.

    Variante destinée à l'exécution en navigateur (WebAssembly/Pyodide) :
    la recherche approximative utilise difflib (bibliothèque standard) au
    lieu de rapidfuzz, indisponible dans cet environnement.
    """
    import io
    import marimo as mo
    import pandas as pd
    import unicodedata
    from pathlib import Path
    from difflib import SequenceMatcher

    return Path, SequenceMatcher, io, mo, pd, unicodedata


@app.cell
def _(mo):
    # --- Design système : injecté une fois, s'applique à toute l'interface ---
    _CSS = """
    .gc-hero{
      background:linear-gradient(120deg,#0f766e 0%,#0e7c74 60%,#0891b2 100%);
      color:#fff; border-radius:16px; padding:26px 30px;
      box-shadow:0 14px 34px -16px rgba(13,148,136,.55);
    }
    .gc-hero h1{ margin:0 0 8px; font-size:1.85rem; font-weight:700;
      letter-spacing:-.02em; color:#fff; line-height:1.15; }
    .gc-hero p{ margin:0; color:rgba(255,255,255,.92); font-size:1rem;
      line-height:1.55; max-width:72ch; }
    .gc-hero b{ color:#fff; font-weight:650; }
    .gc-chips{ margin-top:18px; display:flex; gap:8px; flex-wrap:wrap; }
    .gc-chip{ background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.28);
      color:#fff; padding:4px 13px; border-radius:999px; font-size:.78rem;
      font-weight:600; letter-spacing:.01em; }

    .gc-steps{ display:flex; gap:14px; flex-wrap:wrap; margin-top:2px; }
    .gc-step{ flex:1 1 200px; border:1px solid var(--border,#e2e8f0);
      border-radius:13px; padding:16px 18px; background:var(--background,#fff);
      transition:border-color .15s ease, transform .15s ease; }
    .gc-step:hover{ border-color:#0d9488; transform:translateY(-2px); }
    .gc-num{ display:inline-flex; align-items:center; justify-content:center;
      width:30px; height:30px; border-radius:9px;
      background:linear-gradient(135deg,#0d9488,#0891b2); color:#fff;
      font-weight:700; font-size:.95rem; margin-bottom:11px; }
    .gc-step h4{ margin:0 0 5px; font-size:.98rem; font-weight:650;
      color:var(--foreground,#0f172a); }
    .gc-step p{ margin:0; font-size:.86rem; line-height:1.5;
      color:var(--muted-foreground,#64748b); }
    .gc-step code{ background:rgba(13,148,136,.1); padding:1px 5px;
      border-radius:4px; font-size:.85em; }

    .gc-section{ display:flex; align-items:center; gap:13px; margin:6px 0 2px; }
    .gc-badge{ width:36px; height:36px; border-radius:11px; flex:none;
      background:linear-gradient(135deg,#0d9488,#0891b2); color:#fff;
      display:flex; align-items:center; justify-content:center;
      font-weight:700; font-size:1.1rem;
      box-shadow:0 5px 14px -5px rgba(13,148,136,.6); }
    .gc-section h2{ margin:0; font-size:1.3rem; font-weight:680;
      color:var(--foreground,#0f172a); letter-spacing:-.01em; }
    .gc-section .gc-sub{ margin:2px 0 0; font-size:.84rem;
      color:var(--muted-foreground,#64748b); }

    .gc-hint{ border-left:3px solid #0d9488; background:rgba(13,148,136,.07);
      padding:12px 16px; border-radius:0 10px 10px 0; font-size:.92rem;
      line-height:1.6; color:#0f172a; }
    .gc-hint b{ color:#0d9488; font-weight:650; }
    .gc-hint code{ background:rgba(13,148,136,.14); padding:1px 6px;
      border-radius:5px; font-size:.85em; }

    /* ---- Visite guidée ---- */
    .gc-tour-head{ display:flex; align-items:center; justify-content:space-between;
      gap:12px; margin-bottom:10px; }
    .gc-tour-title{ font-weight:680; font-size:1.08rem;
      color:var(--foreground,#0f172a); letter-spacing:-.01em; }
    .gc-tour-step{ font-size:.76rem; font-weight:700; color:#0d9488;
      background:rgba(13,148,136,.12); padding:3px 11px; border-radius:999px;
      white-space:nowrap; }
    .gc-dots{ display:flex; gap:7px; margin-bottom:4px; }
    .gc-dot{ width:9px; height:9px; border-radius:50%;
      background:var(--border,#cbd5e1); transition:background .15s ease; }
    .gc-dot.on{ background:#0d9488; transform:scale(1.1); }

    /* Boutons de mode : plus de présence visuelle */
    /* Boutons marimo : plusieurs sélecteurs de secours (l'attribut exact varie) */
    .marimo-button, button.marimo-button,
    [data-testid="marimo-plugin-ui-button"] button,
    div:has(> button) > button {
      border-radius:13px !important;
      padding:18px 20px !important;
      min-height:60px !important;
      font-size:1.05rem !important;
      font-weight:700 !important;
    }

    /* ---- Cartes des 3 modes (mise en avant visuelle) ---- */
    .gc-modes{ display:flex; gap:14px; flex-wrap:wrap; margin:4px 0 18px; }
    .gc-mode{ flex:1 1 210px; border-radius:14px; padding:18px 20px;
      color:#fff; position:relative; overflow:hidden;
      box-shadow:0 10px 26px -12px rgba(13,148,136,.5); }
    .gc-mode.m1{ background:linear-gradient(135deg,#0d9488,#0891b2); }
    .gc-mode.m2{ background:linear-gradient(135deg,#0e7490,#2563eb); }
    .gc-mode.m3{ background:linear-gradient(135deg,#7c3aed,#0891b2); }
    .gc-mode .gc-mico{ font-size:1.7rem; line-height:1; margin-bottom:9px; display:block; }
    .gc-mode h4{ margin:0 0 5px; font-size:1.05rem; font-weight:700; color:#fff; }
    .gc-mode p{ margin:0; font-size:.9rem; line-height:1.55; color:rgba(255,255,255,.95); }
    .gc-mode{ cursor:default; }
    .gc-mode .gc-mtag{ display:inline-block; margin-top:10px; font-size:.72rem;
      font-weight:700; letter-spacing:.03em; text-transform:uppercase;
      background:rgba(255,255,255,.2); padding:3px 10px; border-radius:999px; }
    """
    mo.Html("<style>" + _CSS + "</style>")
    return


@app.cell
def _(mo):
    # --- Fabriques d'éléments d'interface réutilisables ---
    def titre_section(numero: str, titre: str, sous_titre: str):
        return mo.Html(
            f"""<div class="gc-section">
                  <div class="gc-badge">{numero}</div>
                  <div><h2>{titre}</h2><div class="gc-sub">{sous_titre}</div></div>
                </div>"""
        )

    def hint(html: str):
        return mo.Html(f'<div class="gc-hint">{html}</div>')

    return hint, titre_section


@app.cell
def _(mo):
    # --- État réactif du guide interactif ---
    get_etape, set_etape = mo.state(0)
    get_ex_recherche, set_ex_recherche = mo.state("")

    ETAPES_VISITE = [
        {
            "titre": "👋 Bienvenue",
            "corps": (
                "Cet outil **relie entre elles les différentes façons de nommer un "
                "même médicament** dans les bases françaises (CIS, CIP7, CIP13, DCI), "
                "à partir des fichiers officiels de l'ANSM.\n\n"
                "Suivez cette visite en **1 minute** — cliquez sur **Suivant ▶**."
            ),
        },
        {
            "titre": "1 · Chargez les données",
            "corps": (
                "Dans la **section 1**, déposez les **trois fichiers `.txt`** de la "
                "BDPM (ou collez le chemin de leur dossier).\n\n"
                "Les voyants passent au **vert ✅** à mesure qu'ils sont reconnus, "
                "puis les outils se **déverrouillent automatiquement**."
            ),
        },
        {
            "titre": "🔍 Rechercher un médicament",
            "corps": (
                "Vous connaissez un **nom** ? Tapez un nom commercial (`doliprane`) "
                "ou une substance / DCI (`paracétamol`). Fautes et accents tolérés.\n\n"
                "💡 Des **exemples cliquables** vous attendent dans l'onglet : un clic "
                "lance la recherche à votre place.\n\n"
                "⚠️ L'outil compare des **noms**, pas des usages : un mot de "
                "catégorie comme `antalgique` ne renverra rien — c'est normal."
            ),
        },
        {
            "titre": "🔢 Traduire · 📂 Comparer",
            "corps": (
                "**Traduire un code** : collez 7 (CIP7), 8 (CIS) ou 13 (CIP13) "
                "chiffres, l'origine est détectée seule.\n\n"
                "**Comparer ma base** : chargez un fichier, désignez la colonne des "
                "CIP13, exportez le résultat en CSV.\n\n"
                "**Vous êtes prêt·e !** Décochez l'interrupteur pour masquer la visite."
            ),
        },
    ]
    N_ETAPES = len(ETAPES_VISITE)
    return (
        ETAPES_VISITE,
        N_ETAPES,
        get_etape,
        get_ex_recherche,
        set_etape,
        set_ex_recherche,
    )


@app.cell
def _(mo):
    # --- En-tête + guide d'accueil statique (toujours disponible) ---
    _hero = mo.Html(
        """<div class="gc-hero">
          <h1>💊 Traducteur de codes médicaments</h1>
          <p>Un même médicament porte plusieurs numéros d'identification selon
          les bases de données. Cet outil retrouve, pour un médicament donné,
          <b>tous ses identifiants</b> à partir de la base publique officielle
          des médicaments (ANSM).</p>
          <div class="gc-chips">
            <span class="gc-chip">Source officielle (ANSM)</span>
            <span class="gc-chip">Données publiques</span>
            <span class="gc-chip">Gratuit, sans compte</span>
          </div>
        </div>"""
    )

    _guide = mo.accordion(
        {
            "📖 Comment utiliser l'outil, étape par étape": mo.md(
                """
**L'outil en une phrase.** Il relie entre elles les différentes façons de nommer
un même médicament dans les bases françaises, à partir des fichiers officiels de l'ANSM.

**Le déroulé :**

1. **Charger les données** *(section 1)* — glissez les trois fichiers `.txt` de la
   BDPM, ou collez le chemin du dossier qui les contient. Un voyant ✅ confirme
   chaque fichier reconnu. Tant que les trois ne sont pas là, les modes de
   recherche restent masqués.
2. **Choisir un mode** *(section 2)* — trois onglets, selon ce que vous avez en main :
    - **🔍 Rechercher un médicament** : vous connaissez un nom (commercial ou
      substance) et cherchez ses codes.
    - **🔢 Traduire un code** : vous avez un code et voulez son équivalent dans les
      autres bases de données.
    - **📂 Comparer ma base** : vous avez toute une liste de codes à vérifier d'un coup dans la base officielle.
3. **Lire et exporter** — les résultats s'affichent immédiatement ; la comparaison
   de base se télécharge en CSV.
"""
            ),
            "🧭 Comprendre les codes : CIS, CIP7, CIP13, DCI": mo.md(
                """
Un même médicament porte plusieurs identifiants, chacun avec son rôle :

| Code | Longueur | Ce qu'il identifie |
|------|----------|--------------------|
| **CIS** | 8 chiffres | La **spécialité** — le médicament « fiche produit » (une marque à un dosage). Clé pivot de la BDPM. |
| **CIP7** | 7 chiffres | Une **présentation** (un conditionnement précis), ancien format. |
| **CIP13** | 13 chiffres | La **même présentation** au format actuel (celui du code-barres des boîtes). |
| **DCI** | — | La **substance active** (ex. *paracétamol*), indépendante de la marque. |

**Une analogie :** le **CIS** est la fiche du produit, le **CIP13** est le code-barres
d'une boîte précise sur l'étagère, et la **DCI** est la molécule à l'intérieur. Un même
CIS peut avoir plusieurs présentations (CIP), et partager sa DCI avec des dizaines
d'autres médicaments.
"""
            ),
            "⚠️ Limites : ce que l'outil ne fait pas (et pourquoi)": mo.md(
                """
**La recherche compare des noms, pas des intentions.** Elle rapproche des suites
de lettres, pas des idées :

- ✅ `doliprane`, `parasetamol` (faute tolérée), `codéine` → fonctionnent.
- ❌ `antalgique`, `anti-douleur` → ne renvoient rien ici, c'est voulu.

C'est **volontaire** : l'outil préfère **ne rien répondre** plutôt que proposer une
correspondance plausible mais fausse.

"""
            ),
        }
    )

    mo.vstack([_hero, _guide], gap=1)
    return


@app.cell
def _(N_ETAPES, mo, set_etape):
    # --- Contrôles de la visite guidée (stables : ne lisent pas l'étape courante) ---
    btn_prec = mo.ui.button(
        label="◀ Précédent",
        on_change=lambda _: set_etape(lambda v: max(0, v - 1)),
    )
    btn_suiv = mo.ui.button(
        label="Suivant ▶",
        on_change=lambda _: set_etape(lambda v: min(N_ETAPES - 1, v + 1)),
    )
    switch_visite = mo.ui.switch(value=False, label="Visite guidée")
    return btn_prec, btn_suiv, switch_visite


@app.cell
def _(ETAPES_VISITE, N_ETAPES, btn_prec, btn_suiv, get_etape, mo, switch_visite):
    # --- Affichage de la visite guidée (se met à jour à chaque clic) ---
    _ligne_switch = mo.hstack(
        [mo.md("### 🧭 Visite guidée"), switch_visite],
        justify="space-between",
        align="center",
    )

    if not switch_visite.value:
        _panneau = mo.callout(
            mo.vstack(
                [
                    _ligne_switch,
                    mo.md("*Nouveau ici ? Activez la visite guidée pour un tour en 1 minute.*"),
                ]
            ),
            kind="neutral",
        )
    else:
        _i = get_etape()
        _etape = ETAPES_VISITE[_i]
        _dots = "".join(
            f'<span class="gc-dot {"on" if k == _i else ""}"></span>'
            for k in range(N_ETAPES)
        )
        _entete = mo.Html(
            f"""<div class="gc-tour-head">
                  <span class="gc-tour-title">{_etape['titre']}</span>
                  <span class="gc-tour-step">Étape {_i + 1} / {N_ETAPES}</span>
                </div>
                <div class="gc-dots">{_dots}</div>"""
        )
        _controles = mo.hstack(
            [btn_prec, btn_suiv], justify="space-between", align="center"
        )
        _panneau = mo.callout(
            mo.vstack([_ligne_switch, _entete, mo.md(_etape["corps"]), _controles]),
            kind="neutral",
        )

    _panneau
    return


@app.cell
def _():
    # --- Référentiel des trois fichiers BDPM attendus ---
    COLONNES_BDPM = {
        "CIS_bdpm.txt": [
            "CIS", "DENOMINATION", "FORME_PHARMA", "VOIES_ADMIN", "STATUT_AMM",
            "TYPE_PROCEDURE_AMM", "ETAT_COMMERCIALISATION", "DATE_AMM",
            "STATUT_BDM", "NUM_AUTORISATION_EUROPEENNE", "TITULAIRES",
            "SURVEILLANCE_RENFORCEE",
        ],
        "CIS_CIP_bdpm.txt": [
            "CIS", "CIP7", "LIBELLE_PRESENTATION", "STATUT_ADMIN",
            "ETAT_COMMERCIALISATION_CIP", "DATE_DECLARATION_COMM",
            "CIP13", "AGREMENT_COLLECTIVITES", "TAUX_REMBOURSEMENT",
            "PRIX_EURO", "PRIX_INDICATION", "INDICATIONS_REMBOURSEMENT",
            "SOURCE_INDICATIONS",
        ],
        "CIS_COMPO_bdpm.txt": [
            "CIS", "ELEMENT_PHARMA", "CODE_SUBSTANCE", "DCI", "DOSAGE",
            "REF_DOSAGE", "NATURE_COMPOSANT", "NUM_LIAISON",
        ],
    }
    TAILLES_INDICATIVES = {
        "CIS_bdpm.txt": "≈ 4 Mo",
        "CIS_CIP_bdpm.txt": "≈ 30 Mo",
        "CIS_COMPO_bdpm.txt": "≈ 6 Mo",
    }


    def identifier_fichier(nom: str) -> str | None:
        """Rattache un nom de fichier déposé à l'un des trois attendus."""
        n = nom.lower()
        if "cis_cip" in n:
            return "CIS_CIP_bdpm.txt"
        if "cis_compo" in n:
            return "CIS_COMPO_bdpm.txt"
        if "cis" in n and "bdpm" in n:
            return "CIS_bdpm.txt"
        return None

    return COLONNES_BDPM, TAILLES_INDICATIVES, identifier_fichier


@app.cell
def _(mo):
    # --- Zone de dépôt : deux voies d'entrée, aucune codée en dur ---
    bdpm_upload = mo.ui.file(
        kind="area",
        multiple=True,
        filetypes=[".txt"],
        label="Glissez ici les fichiers BDPM",
    )
    chemin_bdpm = mo.ui.text(
        label="…ou collez le chemin du dossier qui les contient :",
        placeholder=r"ex. C:\Users\moi\Documents\BDPM\sources",
        full_width=True,
    )
    return bdpm_upload, chemin_bdpm


@app.cell
def _(
    COLONNES_BDPM,
    Path,
    TAILLES_INDICATIVES,
    bdpm_upload,
    chemin_bdpm,
    hint,
    identifier_fichier,
    mo,
    titre_section,
):
    # --- Résolution des sources : upload prioritaire, dossier en complément ---
    textes_bdpm: dict[str, str] = {}
    erreurs_depot: list[str] = []

    for _f in bdpm_upload.value or []:
        _canon = identifier_fichier(_f.name)
        if _canon is None:
            erreurs_depot.append(
                f"`{_f.name}` non reconnu — attendus : {', '.join(COLONNES_BDPM)}."
            )
        else:
            textes_bdpm[_canon] = _f.contents.decode("latin-1")

    if chemin_bdpm.value:
        _dossier = Path(chemin_bdpm.value.strip().strip('"'))
        if not _dossier.is_dir():
            erreurs_depot.append(f"Dossier introuvable : `{_dossier}`")
        else:
            for _canon in COLONNES_BDPM:
                if _canon not in textes_bdpm:
                    _p = _dossier / _canon
                    if _p.exists():
                        textes_bdpm[_canon] = _p.read_text(
                            encoding="latin-1", errors="replace"
                        )

    _manquants = [c for c in COLONNES_BDPM if c not in textes_bdpm]

    def _puce(canon):
        ok = canon in textes_bdpm
        return mo.md(
            f"{'✅' if ok else '⬜'} `{canon}` "
            f"<span style='color:var(--muted-foreground)'>"
            f"({TAILLES_INDICATIVES[canon]})</span>"
        )

    _statut = mo.hstack([_puce(c) for c in COLONNES_BDPM], justify="start", gap=2)

    _bloc_erreurs = (
        mo.callout(mo.md("\n\n".join(erreurs_depot)), kind="danger")
        if erreurs_depot else None
    )

    _aide = mo.accordion(
        {
            "❓ Où trouver ces fichiers ?": mo.md(
                "Sur la [page de téléchargement de la BDPM]"
                "(https://base-donnees-publique.medicaments.gouv.fr/telechargement) "
                "(ANSM). Téléchargez les trois fichiers `.txt` listés ci-dessus. "
                "Pour les fichiers volumineux, préférez l'option chemin de dossier "
                "au glisser-déposer (limite de dépôt : 100 Mo par fichier)."
            ),
            "🔎 Comment l'outil reconnaît-il un fichier ?": mo.md(
                "Par son **nom**, pas par son contenu : `CIS_bdpm.txt`, "
                "`CIS_CIP_bdpm.txt` et `CIS_COMPO_bdpm.txt`. Si vous les avez "
                "renommés, la casse et de légères variantes sont tolérées, mais "
                "gardez les mots-clés `cis`, `cip`, `compo`, `bdpm`."
            ),
        }
    )

    # Colonne gauche : dépôt des fichiers. Colonne droite : état + où trouver.
    _col_depot = mo.vstack([
        mo.md("**1. Déposez vos fichiers**"),
        bdpm_upload,
        chemin_bdpm,
    ])
    _col_etat = mo.vstack([
        mo.md("**2. Fichiers reconnus**"),
        _statut,
        *([_bloc_erreurs] if _bloc_erreurs else []),
    ])

    mo.vstack(
        [
            titre_section(
                "1", "Chargez les données de référence",
                "Les trois fichiers de la base publique des médicaments (ANSM) — dite « BDPM ».",
            ),
            _aide,
            hint(
                "<b>Comment démarrer.</b> Déposez les trois fichiers "
                "<code>.txt</code> fournis par l'ANSM (colonne de gauche). Chaque fichier "
                "reconnu passe au vert à droite. Une fois les trois présents, un résumé "
                "de vos données apparaît, et les outils de recherche s'activent plus bas."
            ),
            mo.hstack([_col_depot, _col_etat], widths=[1, 1], gap=1.5),
        ]
    )
    return (textes_bdpm,)


@app.cell
def _(io, pd):
    def _compter_colonnes(texte: str, sep="\t", n_sample=2000) -> dict[int, int]:
        counts: dict[int, int] = {}
        for i, ligne in enumerate(texte.splitlines()):
            if i >= n_sample:
                break
            n = len(ligne.split(sep))
            counts[n] = counts.get(n, 0) + 1
        return counts


    def charger_bdpm(texte: str, expected_names: list[str], sep="\t"):
        """
        Garde-fou : le nombre de colonnes est vérifié sur le fichier réel
        AVANT le chargement pandas — un décalage silencieux entre colonnes
        déclarées et réelles perdrait des données sans lever d'erreur.
        """
        counts = _compter_colonnes(texte, sep=sep)
        dominant_n = max(counts, key=counts.get)
        names, warning = expected_names, None
        if dominant_n != len(expected_names):
            warning = (
                f"{len(expected_names)} colonnes attendues, {dominant_n} "
                f"détectées (distribution : {counts})."
            )
            names = (
                expected_names
                + [f"EXTRA_{i}" for i in range(dominant_n - len(expected_names))]
                if dominant_n > len(expected_names)
                else expected_names[:dominant_n]
            )
        df = pd.read_csv(
            io.StringIO(texte), sep=sep, names=names,
            dtype=str, engine="python", on_bad_lines="skip",
        )
        return df, warning

    return (charger_bdpm,)


@app.cell
def _(COLONNES_BDPM, charger_bdpm, hint, mo, textes_bdpm):
    _manquants = [c for c in COLONNES_BDPM if c not in textes_bdpm]
    mo.stop(
        _manquants,
        mo.callout(
            mo.md(
                "**En attente des fichiers :** "
                + ", ".join(f"`{c}`" for c in _manquants)
                + "\n\nLes onglets de recherche apparaîtront une fois les "
                "trois fichiers chargés."
            ),
            kind="info",
        ),
    )

    cis_df, _w1 = charger_bdpm(textes_bdpm["CIS_bdpm.txt"], COLONNES_BDPM["CIS_bdpm.txt"])
    cis_cip_df, _w2 = charger_bdpm(textes_bdpm["CIS_CIP_bdpm.txt"], COLONNES_BDPM["CIS_CIP_bdpm.txt"])
    cis_compo_df, _w3 = charger_bdpm(textes_bdpm["CIS_COMPO_bdpm.txt"], COLONNES_BDPM["CIS_COMPO_bdpm.txt"])

    _warnings = [
        f"⚠️ `{n}` : {w}"
        for n, w in zip(COLONNES_BDPM, [_w1, _w2, _w3]) if w
    ]

    _banniere = mo.hstack(
        [
            mo.stat(value=f"{len(cis_df):,}".replace(",", " "),
                    label="Médicaments (CIS)", caption="spécialités", bordered=True),
            mo.stat(value=f"{len(cis_cip_df):,}".replace(",", " "),
                    label="Présentations (CIP13)", caption="conditionnements", bordered=True),
            mo.stat(value=f"{cis_compo_df['DCI'].nunique():,}".replace(",", " "),
                    label="Substances (DCI)", caption="molécules distinctes", bordered=True),
        ],
        justify="space-around",
        widths="equal",
        gap=1,
    )

    mo.vstack(
        [
            *([mo.callout(mo.md("\n\n".join(_warnings)), kind="warn")] if _warnings else []),
            hint(
                "<b>✅ Vos trois fichiers sont chargés.</b> Voici ce qu'ils contiennent. "
                "Vous pouvez maintenant utiliser les outils de l'étape 2, plus bas."
            ),
            mo.md("**Vos données en un coup d'œil**"),
            _banniere,
        ]
    )
    return cis_cip_df, cis_compo_df, cis_df


@app.cell
def _(unicodedata):
    def normaliser(texte: str) -> str:
        """Minuscules + suppression des accents + espaces propres."""
        if not isinstance(texte, str):
            return ""
        texte = unicodedata.normalize("NFKD", texte)
        texte = "".join(c for c in texte if not unicodedata.combining(c))
        return " ".join(texte.lower().split())


    def normaliser_code(valeur) -> str:
        """Nettoie un code : espaces, suffixe '.0' d'Excel, non-chiffres."""
        if valeur is None:
            return ""
        s = str(valeur).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return "".join(c for c in s if c.isdigit())

    return normaliser, normaliser_code


@app.cell
def _(cis_compo_df, cis_df, normaliser):
    index_denom = [
        {"cle": normaliser(d), "type": "dénomination", "CIS": cis, "libelle": d}
        for cis, d in zip(cis_df["CIS"], cis_df["DENOMINATION"].fillna(""))
        if d
    ]

    dci_vers_cis = {}
    for _, _row in cis_compo_df.iterrows():
        _dci_norm = normaliser(_row["DCI"])
        if _dci_norm:
            dci_vers_cis.setdefault(_dci_norm, {"libelle": _row["DCI"], "cis_set": set()})
            dci_vers_cis[_dci_norm]["cis_set"].add(_row["CIS"])

    index_dci = [
        {"cle": k, "type": "DCI", "CIS_multiples": sorted(v["cis_set"]), "libelle": v["libelle"]}
        for k, v in dci_vers_cis.items()
    ]
    return index_dci, index_denom


@app.cell
def _(SequenceMatcher, index_dci, index_denom, normaliser):
    def _partial_ratio(court: str, long: str) -> float:
        """Équivalent de fuzz.partial_ratio via difflib (fenêtre glissante) :
        meilleure similarité entre la requête et une sous-chaîne de même longueur."""
        if not court or not long:
            return 0.0
        if len(court) >= len(long):
            return SequenceMatcher(None, court, long).ratio()
        n = len(court)
        meilleur = 0.0
        for i in range(len(long) - n + 1):
            r = SequenceMatcher(None, court, long[i:i + n]).ratio()
            if r > meilleur:
                meilleur = r
                if meilleur == 1.0:
                    break
        return meilleur

    def score_lexical(requete_norm: str, cle: str) -> float:
        if requete_norm in cle:
            return 1.0
        return _partial_ratio(requete_norm, cle)


    def recherche_lexicale(requete: str, top_k: int = 8, seuil: float = 0.75) -> list[dict]:
        requete_norm = normaliser(requete)
        if not requete_norm:
            return []
        resultats = []
        for entree in index_dci + index_denom:
            s = score_lexical(requete_norm, entree["cle"])
            if s >= seuil:
                resultats.append({**entree, "score": s})
        resultats.sort(key=lambda r: (-r["score"], r["type"] != "DCI"))
        return resultats[:top_k]

    return (recherche_lexicale,)


@app.cell
def _(cis_cip_df, cis_compo_df, cis_df, normaliser_code):
    def traduire_cis(cis: str) -> dict:
        """Moteur de correspondance exact (inchangé depuis v2)."""
        denom_row = cis_df.loc[cis_df["CIS"] == cis]
        cip_rows = cis_cip_df.loc[cis_cip_df["CIS"] == cis]
        compo_rows = cis_compo_df.loc[cis_compo_df["CIS"] == cis]
        return {
            "CIS": cis,
            "denomination": denom_row["DENOMINATION"].iloc[0] if not denom_row.empty else None,
            "presentations": [
                {"CIP7": r["CIP7"], "CIP13": r["CIP13"],
                 "libelle": r["LIBELLE_PRESENTATION"]}
                for _, r in cip_rows.iterrows()
            ],
            "substances_dci": [
                {"DCI": r["DCI"], "dosage": r["DOSAGE"]} for _, r in compo_rows.iterrows()
            ],
        }


    def detecter_type_code(saisie: str) -> tuple[str | None, str]:
        """7 chiffres → CIP7, 8 → CIS, 13 → CIP13."""
        code = normaliser_code(saisie)
        types = {7: "CIP7", 8: "CIS", 13: "CIP13"}
        return types.get(len(code)), code


    def traduire_code(saisie: str) -> dict:
        """Traduit un code quel que soit son référentiel d'origine."""
        type_code, code = detecter_type_code(saisie)
        if type_code is None:
            return {"erreur": (
                f"« {saisie} » ne correspond à aucun format connu : "
                "un code CIP7 fait 7 chiffres, un CIS 8, un CIP13 13."
            )}
        if type_code == "CIS":
            cis = code if (cis_df["CIS"] == code).any() else None
        else:
            lignes = cis_cip_df.loc[cis_cip_df[type_code] == code]
            cis = lignes["CIS"].iloc[0] if not lignes.empty else None
        if cis is None:
            return {"erreur": (
                f"Code {type_code} `{code}` introuvable dans la BDPM. "
                "Vérifiez la saisie ou la fraîcheur du fichier BDPM."
            )}
        return {"type_code": type_code, "code": code, **traduire_cis(cis)}

    return traduire_cis, traduire_code


@app.cell
def _(get_ex_recherche, mo, set_ex_recherche):
    # --- Champ de recherche, PILOTABLE par les exemples cliquables (via mo.state) ---
    requete_input = mo.ui.text(
        value=get_ex_recherche(),
        on_change=set_ex_recherche,
        label="Nom commercial ou substance (DCI) :",
        placeholder="ex. codéine, doliprane, parasetamol",
        full_width=True,
    )
    return (requete_input,)


@app.cell
def _(mo, set_ex_recherche):
    # --- Exemples cliquables : un clic remplit le champ et lance la recherche ---
    _exemples = ["doliprane", "paracétamol", "ibuprofène", "codéine", "amoxicilline"]
    boutons_ex_recherche = mo.ui.array(
        [
            mo.ui.button(label=f"🔎 {ex}", on_change=lambda v, ex=ex: set_ex_recherche(ex))
            for ex in _exemples
        ]
    )
    return (boutons_ex_recherche,)


@app.cell
def _(mo):
    # --- Champ de saisie d'un code (onglet Traduire) ---
    code_input = mo.ui.text(
        label="Code CIS, CIP7 ou CIP13 :",
        placeholder="ex. 3400930000001",
        full_width=True,
    )
    return (code_input,)


@app.cell
def _(mo):
    # --- Entrées de l'onglet Comparer (isolées : jamais recréées par un exemple) ---
    fichier_upload = mo.ui.file(
        kind="area",
        filetypes=[".txt", ".csv", ".tsv"],
        label="Glissez votre base (txt / CSV / TSV)",
    )
    chemin_input = mo.ui.text(
        label="…ou chemin d'un fichier volumineux (ex. Open Medic, > 100 Mo) :",
        placeholder=r"ex. C:\...\OPEN_MEDIC_2024.CSV",
        full_width=True,
    )
    return chemin_input, fichier_upload


@app.cell
def _(Path, chemin_input, fichier_upload, io, mo, pd):
    def _detecter_separateur(premiere_ligne: str) -> str:
        candidats = {"\t": premiere_ligne.count("\t"),
                     ";": premiere_ligne.count(";"),
                     ",": premiere_ligne.count(",")}
        return max(candidats, key=candidats.get)


    def _lire(buffer_texte) -> pd.DataFrame:
        premiere_ligne = buffer_texte.readline()
        sep = _detecter_separateur(premiere_ligne)
        buffer_texte.seek(0)
        return pd.read_csv(buffer_texte, sep=sep, dtype=str,
                           engine="python", on_bad_lines="skip")


    base_utilisateur, erreur_lecture = None, None
    if fichier_upload.value:
        try:
            _brut = fichier_upload.value[0].contents
            try:
                _texte = _brut.decode("utf-8")
            except UnicodeDecodeError:
                _texte = _brut.decode("latin-1")
            base_utilisateur = _lire(io.StringIO(_texte))
        except Exception as e:
            erreur_lecture = f"Lecture impossible : {e}"
    elif chemin_input.value:
        _p = Path(chemin_input.value.strip().strip('"'))
        if not _p.exists():
            erreur_lecture = f"Fichier introuvable : `{_p}`"
        else:
            try:
                with open(_p, encoding="utf-8", errors="replace") as _f:
                    base_utilisateur = _lire(_f)
            except Exception as e:
                erreur_lecture = f"Lecture impossible : {e}"

    statut_fichier = (
        mo.callout(erreur_lecture, kind="danger") if erreur_lecture
        else mo.callout(
            f"✅ Base chargée : {len(base_utilisateur):,} lignes, "
            f"{len(base_utilisateur.columns)} colonnes.", kind="success")
        if base_utilisateur is not None
        else mo.md("*Aucune base chargée pour l'instant.*")
    )
    return base_utilisateur, statut_fichier


@app.cell
def _(base_utilisateur, mo):
    colonne_codes = (
        mo.ui.dropdown(
            options=list(base_utilisateur.columns),
            label="Colonne contenant vos codes CIP13 :",
        )
        if base_utilisateur is not None
        else None
    )
    return (colonne_codes,)


@app.cell
def _(base_utilisateur, cis_cip_df, cis_df, colonne_codes, normaliser_code, pd):
    def comparer_base():
        """Jointure de la colonne choisie sur le pivot CIP13 de la BDPM."""
        if base_utilisateur is None or colonne_codes is None or not colonne_codes.value:
            return None, None
        codes = (
            base_utilisateur[colonne_codes.value]
            .map(normaliser_code)
            .to_frame(name="CODE_SAISI")
        )
        referentiel = cis_cip_df[["CIP13", "LIBELLE_PRESENTATION", "CIS"]].merge(
            cis_df[["CIS", "DENOMINATION"]], on="CIS", how="left"
        )
        resultat = codes.merge(
            referentiel, left_on="CODE_SAISI", right_on="CIP13", how="left"
        )
        resultat["TROUVE"] = resultat["CIP13"].notna().map({True: "oui", False: "non"})
        resultat = resultat[
            ["CODE_SAISI", "TROUVE", "CIP13", "LIBELLE_PRESENTATION", "DENOMINATION", "CIS"]
        ]
        stats = {
            "total": len(resultat),
            "trouves": int((resultat["TROUVE"] == "oui").sum()),
        }
        stats["taux"] = 100 * stats["trouves"] / stats["total"] if stats["total"] else 0.0
        return resultat, stats

    resultat_comparaison, stats_comparaison = comparer_base()
    return resultat_comparaison, stats_comparaison


@app.cell
def _(boutons_ex_recherche, hint, mo, pd, recherche_lexicale, requete_input, traduire_cis):
    def _bloc_cis(cis: str, score: float, origine: str):
        detail = traduire_cis(cis)
        cip_str = ", ".join(
            f"CIP13 `{p['CIP13']}`" for p in detail["presentations"] if p.get("CIP13")
        ) or "aucune présentation CIP référencée"
        dci_str = ", ".join(
            f"{s['DCI']} ({s['dosage']})" for s in detail["substances_dci"] if s.get("DCI")
        ) or "composition non trouvée"
        return mo.md(
            f"""
            ---
            **{detail['denomination']}** — CIS `{cis}`  
            *Correspondance {origine} — score lexical : {score:.2f}*

            - **Présentations :** {cip_str}
            - **Substances (DCI) :** {dci_str}
            """
        )


    def _vue_recherche():
        if not requete_input.value:
            return mo.md("*Tapez un nom, ou cliquez un exemple ci-dessus. "
                         "Les fautes et accents sont tolérés ; en revanche un mot "
                         "de catégorie comme « antalgique » ne renverra rien.*")
        candidats = recherche_lexicale(requete_input.value, top_k=8)
        if not candidats:
            return mo.callout(
                f"Aucun résultat pour « {requete_input.value} ». "
                "Essayez un nom de médicament ou de substance active — les fautes "
                "de frappe sont tolérées.",
                kind="warn",
            )
        blocs = []
        for c in candidats:
            if c["type"] == "DCI":
                blocs.append(mo.md(
                    f"#### 🧪 Substance : **{c['libelle']}** "
                    f"({len(c['CIS_multiples'])} médicament(s))"))
                for cis in c["CIS_multiples"][:5]:
                    blocs.append(_bloc_cis(cis, c["score"], "sur la DCI"))
                if len(c["CIS_multiples"]) > 5:
                    blocs.append(mo.md(
                        f"*… et {len(c['CIS_multiples']) - 5} autre(s).*"))
            else:
                blocs.append(_bloc_cis(c["CIS"], c["score"], "sur la dénomination"))
        return mo.vstack(blocs)

    _exemples_ui = mo.hstack(
        [mo.md("**Essayez :**"), boutons_ex_recherche],
        justify="start", align="center", gap=0.5, wrap=True,
    )

    def _lignes_export_recherche():
        """Aplatit les résultats de recherche en lignes CSV exportables."""
        if not requete_input.value:
            return None
        lignes = []
        for c in recherche_lexicale(requete_input.value, top_k=8):
            cis_list = c["CIS_multiples"] if c["type"] == "DCI" else [c["CIS"]]
            for cis in cis_list:
                det = traduire_cis(cis)
                for p in (det["presentations"] or [{}]):
                    lignes.append({
                        "RECHERCHE": requete_input.value,
                        "TYPE_MATCH": c["type"],
                        "SCORE": round(c["score"], 3),
                        "DENOMINATION": det["denomination"],
                        "CIS": cis,
                        "CIP7": p.get("CIP7", ""),
                        "CIP13": p.get("CIP13", ""),
                        "LIBELLE_PRESENTATION": p.get("libelle", ""),
                        "DCI": " + ".join(
                            s["DCI"] for s in det["substances_dci"] if s.get("DCI")
                        ),
                    })
        return pd.DataFrame(lignes) if lignes else None

    _df_export_rech = _lignes_export_recherche()
    _bloc_export_rech = (
        mo.download(
            data=_df_export_rech.to_csv(index=False).encode("utf-8"),
            filename="recherche_resultats.csv",
            label="⬇ Télécharger ces résultats (ouvrable dans Excel)",
        )
        if _df_export_rech is not None and not _df_export_rech.empty
        else mo.md("")
    )

    vue_recherche = mo.vstack([
        hint(
            "<b>Recherche par nom.</b> Tapez un nom de médicament (ex. "
            "<code>doliprane</code>) ou de substance active (ex. <code>paracétamol</code>) "
            "— ou cliquez un exemple. Les fautes de frappe et les accents sont tolérés. "
            "À noter : l'outil compare des noms, pas des usages — un mot comme "
            "<code>antalgique</code> (une catégorie, pas un nom) ne donnera donc "
            "aucun résultat."
        ),
        _exemples_ui,
        requete_input,
        _vue_recherche(),
        _bloc_export_rech,
    ])
    return (vue_recherche,)


@app.cell
def _(code_input, hint, mo, pd, traduire_code):
    def _vue_code():
        if not code_input.value:
            return mo.md("*Saisissez un code ci-dessus (7, 8 ou 13 chiffres) : "
                         "le référentiel d'origine est détecté automatiquement.*")
        res = traduire_code(code_input.value)
        if "erreur" in res:
            return mo.callout(res["erreur"], kind="warn")
        pres = "\n".join(
            f"- CIP7 `{p['CIP7']}` · CIP13 `{p['CIP13']}` — {p['libelle']}"
            for p in res["presentations"]
        ) or "- aucune présentation référencée"
        dci = ", ".join(
            f"{s['DCI']} ({s['dosage']})" for s in res["substances_dci"] if s.get("DCI")
        ) or "composition non trouvée"
        return mo.md(
            f"""
            ### {res['denomination']}
            *Code {res['type_code']} `{res['code']}` reconnu → CIS `{res['CIS']}`*

            **Présentations :**
            {pres}

            **Substances (DCI) :** {dci}
            """
        )

    def _lignes_export_code():
        if not code_input.value:
            return None
        res = traduire_code(code_input.value)
        if "erreur" in res:
            return None
        lignes = []
        dci = " + ".join(s["DCI"] for s in res["substances_dci"] if s.get("DCI"))
        for p in (res["presentations"] or [{}]):
            lignes.append({
                "CODE_SAISI": res["code"],
                "TYPE_CODE": res["type_code"],
                "DENOMINATION": res["denomination"],
                "CIS": res["CIS"],
                "CIP7": p.get("CIP7", ""),
                "CIP13": p.get("CIP13", ""),
                "LIBELLE_PRESENTATION": p.get("libelle", ""),
                "DCI": dci,
            })
        return pd.DataFrame(lignes) if lignes else None

    _df_export_code = _lignes_export_code()
    _bloc_export_code = (
        mo.download(
            data=_df_export_code.to_csv(index=False).encode("utf-8"),
            filename="traduction_code_resultat.csv",
            label="⬇ Télécharger ce résultat (ouvrable dans Excel)",
        )
        if _df_export_code is not None and not _df_export_code.empty
        else mo.md("")
    )

    vue_code = mo.vstack([
        hint(
            "<b>Traduction d'un numéro.</b> Collez un identifiant de médicament : "
            "l'outil reconnaît tout seul son type d'après sa longueur (7, 8 ou 13 "
            "chiffres) et affiche tous ses équivalents dans les autres bases."
        ),
        code_input,
        _vue_code(),
        _bloc_export_code,
    ])
    return (vue_code,)


@app.cell
def _(
    chemin_input,
    colonne_codes,
    fichier_upload,
    hint,
    mo,
    resultat_comparaison,
    stats_comparaison,
    statut_fichier,
):
    _elements = [
        hint(
            "<b>Vérification d'une liste complète.</b> Chargez votre fichier "
            "(txt, CSV ou Excel exporté en CSV) et indiquez quelle colonne contient "
            "les codes à 13 chiffres. Chaque ligne est vérifiée dans la base officielle, "
            "puis vous téléchargez le résultat complet."
        ),
        fichier_upload,
        chemin_input,
        statut_fichier,
    ]
    if colonne_codes is not None:
        _elements.append(colonne_codes)
    if resultat_comparaison is not None:
        _elements.append(mo.callout(
            f"**{stats_comparaison['trouves']:,} / {stats_comparaison['total']:,}** "
            f"codes retrouvés dans la BDPM "
            f"({stats_comparaison['taux']:.1f} % de correspondance).",
            kind="info",
        ))
        _elements.append(mo.ui.table(resultat_comparaison, page_size=15))
        _elements.append(mo.download(
            data=resultat_comparaison.to_csv(index=False).encode("utf-8"),
            filename="traduction_resultats.csv",
            label="⬇ Télécharger les résultats (ouvrable dans Excel)",
        ))

    vue_comparaison = mo.vstack(_elements)
    return (vue_comparaison,)


@app.cell
def _(mo):
    # --- État du mode actif (navigation par cartes-boutons) ---
    get_mode, set_mode = mo.state("recherche")
    return get_mode, set_mode


@app.cell
def _(mo, set_mode):
    # --- Trois boutons-cartes cliquables (ne lisent pas l'état -> pas de cycle) ---
    btn_mode_recherche = mo.ui.button(
        label="### 🔍 Je connais un nom",
        on_change=lambda _: set_mode("recherche"),
        kind="success", full_width=True,
    )
    btn_mode_code = mo.ui.button(
        label="### 🔢 J'ai un numéro",
        on_change=lambda _: set_mode("code"),
        kind="info", full_width=True,
    )
    btn_mode_compare = mo.ui.button(
        label="### 📂 J'ai une liste entière",
        on_change=lambda _: set_mode("compare"),
        kind="info", full_width=True,
    )
    return btn_mode_code, btn_mode_compare, btn_mode_recherche


@app.cell
def _(
    btn_mode_code,
    btn_mode_compare,
    btn_mode_recherche,
    get_mode,
    mo,
    titre_section,
    vue_code,
    vue_comparaison,
    vue_recherche,
):
    _mode = get_mode()

    # descriptif sous chaque bouton (aide à choisir sans cliquer)
    _nom_mode = {
        "recherche": "🔍 Recherche par nom",
        "code": "🔢 Traduction d'un numéro",
        "compare": "📂 Vérification d'une liste",
    }[_mode]
    _desc = {
        "recherche": "Tapez un nom de médicament ou de substance pour retrouver tous ses identifiants.",
        "code": "Collez un identifiant (7, 8 ou 13 chiffres) pour obtenir tous ses équivalents.",
        "compare": "Chargez un fichier de codes à vérifier d'un coup, puis téléchargez le résultat.",
    }[_mode]

    _boutons = mo.hstack(
        [btn_mode_recherche, btn_mode_code, btn_mode_compare],
        widths="equal", gap=0.8,
    )

    _vue = {
        "recherche": vue_recherche,
        "code": vue_code,
        "compare": vue_comparaison,
    }[_mode]

    mo.vstack(
        [
            titre_section(
                "2", "Explorez et traduisez",
                "Choisissez ce que vous avez en main :",
            ),
            _boutons,
            mo.callout(mo.md(f"**{_nom_mode}** — {_desc}"), kind="info"),
            _vue,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
