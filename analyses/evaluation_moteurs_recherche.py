import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    """
    Évaluation quantitative des moteurs de recherche — approche NLP vs approche lexicale

    Protocole :
      - Jeu de test de ~43 requêtes annotées à la main, réparties en
        6 catégories (DCI exactes, DCI avec fautes, noms commerciaux,
        commerciaux avec fautes, classes thérapeutiques hors périmètre,
        requêtes hors domaine).
      - Pour chaque requête, la vérité terrain est soit une sous-chaîne
        qui DOIT apparaître dans les résultats (requête "dans le périmètre"),
        soit AUCUN résultat attendu (requête "hors périmètre" : le bon
        comportement est l'abstention).
      - Métriques standard de recherche d'information :
          Précision = réponses correctes / réponses données
          Rappel    = réponses correctes / requêtes dans le périmètre
          F1        = moyenne harmonique des deux
        + taux d'abstention correcte sur les requêtes hors périmètre
          (c'est LA métrique qui sépare v1 et v3 : la v1 répond toujours).

    Une réponse fausse à une requête dans le périmètre pénalise à la fois
    la précision (réponse donnée mais fausse) et le rappel (bonne réponse
    manquée) — c'est le comportement standard de ces métriques.

    Dépendances : uv add rapidfuzz
    Optionnel (section v1) : sentence-transformers + torch (déjà installés
    pour la v1 du projet).
    """
    import io
    import marimo as mo
    import pandas as pd
    import unicodedata
    from pathlib import Path
    from rapidfuzz import fuzz

    return Path, fuzz, io, mo, pd, unicodedata


@app.cell
def _(mo):
    mo.md("""
    # 📏 Évaluation quantitative — v1 (sémantique) vs v3 (lexicale)

    Ce notebook mesure les deux moteurs de recherche sur le **même jeu
    de test annoté**, avec les métriques standard de recherche
    d'information (précision, rappel, F1), plus le **taux d'abstention
    correcte** — la capacité à ne *rien* renvoyer quand la requête
    sort du périmètre (ex. « antalgique »), là où la v1 renvoyait
    toujours un top-N avec des scores trompeurs.
    """)
    return


@app.cell
def _():
    # =====================================================================
    # JEU DE TEST — vérité terrain annotée à la main
    # ---------------------------------------------------------------------
    # attendu : sous-chaîne (normalisée) qui doit apparaître dans au moins
    #           un des libellés renvoyés. None = aucun résultat attendu
    #           (le bon comportement est l'abstention).
    # Modifiable librement : ajouter des cas ne demande qu'une ligne.
    # =====================================================================
    JEU_DE_TEST = [
        # --- 1. DCI exactes -------------------------------------------------
        {"requete": "paracétamol",      "attendu": "paracetamol",    "categorie": "DCI exacte"},
        {"requete": "ibuprofène",       "attendu": "ibuprofene",     "categorie": "DCI exacte"},
        {"requete": "amoxicilline",     "attendu": "amoxicilline",   "categorie": "DCI exacte"},
        {"requete": "codéine",          "attendu": "codeine",        "categorie": "DCI exacte"},
        {"requete": "oméprazole",       "attendu": "omeprazole",     "categorie": "DCI exacte"},
        {"requete": "metformine",       "attendu": "metformine",     "categorie": "DCI exacte"},
        {"requete": "tramadol",         "attendu": "tramadol",       "categorie": "DCI exacte"},
        {"requete": "morphine",         "attendu": "morphine",       "categorie": "DCI exacte"},
        {"requete": "atorvastatine",    "attendu": "atorvastatine",  "categorie": "DCI exacte"},
        # --- 2. DCI avec fautes de frappe ------------------------------------
        {"requete": "parasetamol",      "attendu": "paracetamol",    "categorie": "DCI avec faute"},
        {"requete": "ibuprophene",      "attendu": "ibuprofene",     "categorie": "DCI avec faute"},
        {"requete": "amoxiciline",      "attendu": "amoxicilline",   "categorie": "DCI avec faute"},
        {"requete": "omeprazol",        "attendu": "omeprazole",     "categorie": "DCI avec faute"},
        {"requete": "tramadole",        "attendu": "tramadol",       "categorie": "DCI avec faute"},
        {"requete": "atorvastatin",     "attendu": "atorvastatine",  "categorie": "DCI avec faute"},
        # --- 3. Noms commerciaux ---------------------------------------------
        {"requete": "doliprane",        "attendu": "doliprane",      "categorie": "Nom commercial"},
        {"requete": "efferalgan",       "attendu": "efferalgan",     "categorie": "Nom commercial"},
        {"requete": "spasfon",          "attendu": "spasfon",        "categorie": "Nom commercial"},
        {"requete": "levothyrox",       "attendu": "levothyrox",     "categorie": "Nom commercial"},
        {"requete": "kardegic",         "attendu": "kardegic",       "categorie": "Nom commercial"},
        {"requete": "augmentin",        "attendu": "augmentin",      "categorie": "Nom commercial"},
        {"requete": "imodium",          "attendu": "imodium",        "categorie": "Nom commercial"},
        {"requete": "smecta",           "attendu": "smecta",         "categorie": "Nom commercial"},
        {"requete": "ventoline",        "attendu": "ventoline",      "categorie": "Nom commercial"},
        {"requete": "voltarene",        "attendu": "voltarene",      "categorie": "Nom commercial"},
        {"requete": "aspirine",         "attendu": "aspirine",       "categorie": "Nom commercial"},
        # --- 4. Noms commerciaux avec fautes ----------------------------------
        {"requete": "dolipran",         "attendu": "doliprane",      "categorie": "Commercial avec faute"},
        {"requete": "efferalgant",      "attendu": "efferalgan",     "categorie": "Commercial avec faute"},
        {"requete": "ventolinne",       "attendu": "ventoline",      "categorie": "Commercial avec faute"},
        {"requete": "cardegic",         "attendu": "kardegic",       "categorie": "Commercial avec faute"},
        {"requete": "smekta",           "attendu": "smecta",         "categorie": "Commercial avec faute"},
        # --- 5. Classes thérapeutiques (hors périmètre lexical) ---------------
        # Le bon comportement est de NE RIEN renvoyer : aucune de ces notions
        # n'est un nom de médicament ni une DCI. La v1 répondait quand même.
        {"requete": "antalgique",       "attendu": None, "categorie": "Classe thérapeutique"},
        {"requete": "antibiotique",     "attendu": None, "categorie": "Classe thérapeutique"},
        {"requete": "anti-inflammatoire", "attendu": None, "categorie": "Classe thérapeutique"},
        {"requete": "antidépresseur",   "attendu": None, "categorie": "Classe thérapeutique"},
        {"requete": "somnifère",        "attendu": None, "categorie": "Classe thérapeutique"},
        {"requete": "médicament contre la tension", "attendu": None, "categorie": "Classe thérapeutique"},
        # --- 6. Hors domaine ---------------------------------------------------
        {"requete": "bonjour",          "attendu": None, "categorie": "Hors domaine"},
        {"requete": "voiture",          "attendu": None, "categorie": "Hors domaine"},
        {"requete": "azertyuiop",       "attendu": None, "categorie": "Hors domaine"},
    ]
    return (JEU_DE_TEST,)


@app.cell
def _(mo):
    chemin_bdpm_eval = mo.ui.text(
        label="Chemin du dossier contenant les fichiers BDPM :",
        placeholder=r"ex. C:\Users\moi\Documents\BDPM\sources",
        full_width=True,
    )
    chemin_bdpm_eval
    return (chemin_bdpm_eval,)


@app.cell
def _(Path, chemin_bdpm_eval, io, mo, pd):
    # --- Chargement BDPM (CIS + COMPO suffisent pour la recherche) ---
    COLONNES = {
        "CIS_bdpm.txt": [
            "CIS", "DENOMINATION", "FORME_PHARMA", "VOIES_ADMIN", "STATUT_AMM",
            "TYPE_PROCEDURE_AMM", "ETAT_COMMERCIALISATION", "DATE_AMM",
            "STATUT_BDM", "NUM_AUTORISATION_EUROPEENNE", "TITULAIRES",
            "SURVEILLANCE_RENFORCEE",
        ],
        "CIS_COMPO_bdpm.txt": [
            "CIS", "ELEMENT_PHARMA", "CODE_SUBSTANCE", "DCI", "DOSAGE",
            "REF_DOSAGE", "NATURE_COMPOSANT", "NUM_LIAISON",
        ],
    }

    mo.stop(
        not chemin_bdpm_eval.value,
        mo.callout("Indique le dossier BDPM ci-dessus pour lancer l'évaluation.", kind="info"),
    )
    _dossier = Path(chemin_bdpm_eval.value.strip().strip('"'))
    _absents = [n for n in COLONNES if not (_dossier / n).exists()]
    mo.stop(
        _absents,
        mo.callout(f"Fichier(s) introuvable(s) dans `{_dossier}` : {', '.join(_absents)}", kind="danger"),
    )

    def _compter_colonnes(texte, sep="\t", n_sample=2000):
        counts = {}
        for i, ligne in enumerate(texte.splitlines()):
            if i >= n_sample:
                break
            n = len(ligne.split(sep))
            counts[n] = counts.get(n, 0) + 1
        return counts

    def _charger(nom):
        texte = (_dossier / nom).read_text(encoding="latin-1", errors="replace")
        names = COLONNES[nom]
        dominant = max(_compter_colonnes(texte), key=_compter_colonnes(texte).get)
        if dominant != len(names):
            names = (names + [f"EXTRA_{i}" for i in range(dominant - len(names))]
                     if dominant > len(names) else names[:dominant])
        return pd.read_csv(io.StringIO(texte), sep="\t", names=names,
                           dtype=str, engine="python", on_bad_lines="skip")

    cis_df = _charger("CIS_bdpm.txt")
    cis_compo_df = _charger("CIS_COMPO_bdpm.txt")
    mo.callout(
        f"✅ BDPM chargée : {len(cis_df):,} médicaments, "
        f"{cis_compo_df['DCI'].nunique():,} DCI distinctes.",
        kind="success",
    )
    return cis_compo_df, cis_df


@app.cell
def _(unicodedata):
    def normaliser(texte: str) -> str:
        if not isinstance(texte, str):
            return ""
        texte = unicodedata.normalize("NFKD", texte)
        texte = "".join(c for c in texte if not unicodedata.combining(c))
        return " ".join(texte.lower().split())

    return (normaliser,)


@app.cell
def _(cis_compo_df, cis_df, fuzz, normaliser):
    # --- Moteur v3 : identique au notebook principal -----------------------
    index_denom = [
        {"cle": normaliser(d), "libelle": d}
        for d in cis_df["DENOMINATION"].fillna("") if d
    ]
    index_dci = [
        {"cle": normaliser(d), "libelle": d}
        for d in cis_compo_df["DCI"].dropna().unique() if normaliser(d)
    ]

    def rechercher_v3(requete: str, top_k: int = 5, seuil: float = 0.75) -> list[str]:
        """Renvoie les libellés des meilleurs candidats, ou [] (abstention)."""
        q = normaliser(requete)
        if not q:
            return []
        scores = []
        for entree in index_dci + index_denom:
            s = 1.0 if q in entree["cle"] else fuzz.partial_ratio(q, entree["cle"]) / 100.0
            if s >= seuil:
                scores.append((s, entree["libelle"]))
        scores.sort(key=lambda x: -x[0])
        return [lib for _, lib in scores[:top_k]]

    return index_denom, rechercher_v3


@app.cell
def _(JEU_DE_TEST, mo, normaliser, pd):
    # --- Harnais d'évaluation (indépendant du moteur évalué) ----------------
    def evaluer(moteur, nom_moteur: str) -> tuple[pd.DataFrame, dict]:
        """
        Applique le jeu de test à un moteur `moteur(requete) -> list[str]`.

        Verdicts par requête :
          ✅ correct    — dans le périmètre, la sous-chaîne attendue apparaît
          ✅ abstention — hors périmètre, aucun résultat renvoyé (voulu)
          ❌ manqué     — dans le périmètre, aucun résultat (rappel ↓)
          ❌ faux       — résultats renvoyés mais tous faux (précision ↓ et,
                          si la requête était dans le périmètre, rappel ↓)
        """
        lignes = []
        for cas in JEU_DE_TEST:
            resultats = moteur(cas["requete"])
            if cas["attendu"] is None:
                verdict = "✅ abstention" if not resultats else "❌ faux"
            elif not resultats:
                verdict = "❌ manqué"
            else:
                trouve = any(
                    normaliser(cas["attendu"]) in normaliser(r) for r in resultats
                )
                verdict = "✅ correct" if trouve else "❌ faux"
            lignes.append({
                "requête": cas["requete"],
                "catégorie": cas["categorie"],
                "attendu": cas["attendu"] or "(abstention)",
                "obtenu (top 3)": " | ".join(resultats[:3]) or "—",
                "verdict": verdict,
            })
        detail = pd.DataFrame(lignes)

        en_perimetre = [c for c in JEU_DE_TEST if c["attendu"] is not None]
        hors_perimetre = [c for c in JEU_DE_TEST if c["attendu"] is None]
        v = detail["verdict"]
        tp = int((v == "✅ correct").sum())
        reponses_donnees = int((v.isin(["✅ correct"])).sum() + (v == "❌ faux").sum())
        abstentions_ok = int((v == "✅ abstention").sum())

        metriques = {
            "moteur": nom_moteur,
            "précision": tp / reponses_donnees if reponses_donnees else 0.0,
            "rappel": tp / len(en_perimetre) if en_perimetre else 0.0,
            "abstention_correcte": abstentions_ok / len(hors_perimetre) if hors_perimetre else 0.0,
        }
        p, r = metriques["précision"], metriques["rappel"]
        metriques["F1"] = 2 * p * r / (p + r) if (p + r) else 0.0
        return detail, metriques


    def afficher_metriques(m: dict):
        return mo.hstack(
            [
                mo.stat(value=f"{m['précision']:.0%}", label="Précision",
                        caption="réponses correctes / réponses données"),
                mo.stat(value=f"{m['rappel']:.0%}", label="Rappel",
                        caption="réponses correctes / requêtes dans le périmètre"),
                mo.stat(value=f"{m['F1']:.0%}", label="F1"),
                mo.stat(value=f"{m['abstention_correcte']:.0%}", label="Abstention correcte",
                        caption="hors périmètre sans réponse"),
            ],
            justify="space-around",
        )

    return afficher_metriques, evaluer


@app.cell
def _(afficher_metriques, evaluer, mo, rechercher_v3):
    detail_v3, metriques_v3 = evaluer(rechercher_v3, "v3 lexicale")

    _par_categorie = (
        detail_v3.assign(ok=detail_v3["verdict"].str.startswith("✅"))
        .groupby("catégorie")["ok"].agg(["sum", "count"])
        .assign(taux=lambda d: (100 * d["sum"] / d["count"]).round(0).astype(int).astype(str) + " %")
        .rename(columns={"sum": "réussies", "count": "total"})
        .reset_index()
    )

    mo.vstack(
        [
            mo.md("## Résultats — moteur v3 (lexical, rapidfuzz, seuil 0,75)"),
            afficher_metriques(metriques_v3),
            mo.md("### Par catégorie"),
            mo.ui.table(_par_categorie, selection=None),
            mo.md("### Détail par requête"),
            mo.ui.table(detail_v3, page_size=15),
            mo.download(
                data=detail_v3.to_csv(index=False).encode("utf-8"),
                filename="evaluation_v3_detail.csv",
                label="Télécharger le détail (CSV)",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    activer_v1 = mo.ui.switch(
        label="Évaluer aussi la v1 sémantique (nécessite sentence-transformers, "
              "~2-5 min d'encodage au premier lancement)"
    )
    activer_v1
    return (activer_v1,)


@app.cell
def _(activer_v1, afficher_metriques, evaluer, index_denom, mo):
    # --- Moteur v1 : réimplémentation fidèle du principe de la v1 -----------
    # (embeddings des DENOMINATIONS commerciales uniquement, similarité
    #  cosinus, top-N TOUJOURS renvoyé — aucun seuil d'abstention)
    mo.stop(not activer_v1.value, mo.md("*Active l'interrupteur pour lancer l'évaluation v1.*"))

    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        mo.stop(True, mo.callout(
            "`sentence-transformers` absent de cet environnement. "
            "Installe-le (`uv add sentence-transformers`) ou évalue la v1 "
            "dans l'environnement où elle tournait.", kind="warn"))

    _modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    _libelles = [e["libelle"] for e in index_denom]
    _emb = _modele.encode(_libelles, normalize_embeddings=True, show_progress_bar=False)

    def rechercher_v1(requete: str, top_k: int = 5) -> list[str]:
        """Reproduit la v1 : top-N systématique, sans seuil → jamais d'abstention."""
        q = _modele.encode([requete], normalize_embeddings=True)
        sims = (_emb @ q.T).ravel()
        meilleurs = np.argsort(-sims)[:top_k]
        return [_libelles[i] for i in meilleurs]

    detail_v1, metriques_v1 = evaluer(rechercher_v1, "v1 sémantique")

    mo.vstack(
        [
            mo.md("## Résultats — moteur v1 (sémantique, MiniLM, top-5 systématique)"),
            afficher_metriques(metriques_v1),
            mo.md("### Détail par requête"),
            mo.ui.table(detail_v1, page_size=15),
            mo.download(
                data=detail_v1.to_csv(index=False).encode("utf-8"),
                filename="evaluation_v1_detail.csv",
                label="Télécharger le détail (CSV)",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.accordion(
        {
            "📖 Comment lire ces métriques (et les présenter dans le mémoire)": mo.md(
                """
                **Précision** — parmi les requêtes où le moteur a *donné une
                réponse*, combien étaient correctes ? Une précision basse
                signifie que le moteur affirme des choses fausses avec
                aplomb — le défaut central de la v1.

                **Rappel** — parmi les requêtes qui *avaient* une bonne
                réponse dans la BDPM, combien le moteur en a-t-il trouvé ?
                Un rappel bas signifie que le moteur rate des réponses
                existantes (seuil trop strict, faute de frappe trop forte).

                **F1** — moyenne harmonique des deux : un seul chiffre pour
                comparer les moteurs, qui punit les déséquilibres.

                **Abstention correcte** — spécifique à ce protocole : sur les
                requêtes hors périmètre (classes thérapeutiques, hors
                domaine), le bon comportement est de ne *rien* renvoyer.
                La v1, qui renvoie toujours un top-N, est structurellement
                à 0 % ici. C'est la traduction chiffrée de l'argument
                « échec honnête plutôt que réponse plausible mais fausse ».

                **Limites à mentionner** : jeu de test de taille modeste
                (~43 requêtes) construit par l'auteure — il illustre les
                comportements plutôt qu'il ne les mesure exhaustivement ;
                le verdict repose sur une correspondance de sous-chaîne
                dans les libellés, ce qui peut sous-estimer marginalement
                les deux moteurs de la même façon.
                """
            )
        }
    )
    return


if __name__ == "__main__":
    app.run()
