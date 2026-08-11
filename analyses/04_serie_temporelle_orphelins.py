"""
Analyse croisée BDPM × OpenMedic (2014–2025)

Produit deux résultats, dans un seul passage :
  1. Série temporelle du recouvrement OpenMedic → BDPM, année par année.
  2. Caractérisation des CIP13 « orphelins » (présents dans OpenMedic,
     absents de la BDPM) pour l'année de référence.

Principes de robustesse (tirés de l'incident documenté en 5.4) :
  - La colonne CIP13 est repérée par son NOM, jamais par sa position :
    l'en-tête d'OpenMedic change entre 2014 et 2025 (ajout de libellés,
    casse variable). Lire par position produirait un décalage silencieux.
  - Le séparateur est détecté sur la première ligne de chaque fichier.
  - Aucun résultat n'est produit si une colonne clé est introuvable :
    le script s'arrête avec un message explicite plutôt que de deviner.
  - Chaque année imprime le nom de colonne retenu et l'effectif lu,
    pour repérer d'un coup d'œil une année qui déraille.

Dépendances : uv add pandas
Lancement    : uv run analyse_croisee_bdpm_openmedic.py
"""

import csv
import glob
import json
import os
import re
import unicodedata
from datetime import datetime

import pandas as pd

# ============================================================================
# CHEMINS — [À ADAPTER une seule fois]
# ============================================================================
DOSSIER_OPENMEDIC = "data"  # dossier des fichiers Open Medic (OPEN_MEDIC_AAAA.CSV)
FICHIER_CIS_CIP = "data/CIS_CIP_bdpm.txt"
FICHIER_CIS = "data/CIS_bdpm.txt"
DOSSIER_SORTIE = "."

# Motif des fichiers OpenMedic : capture l'année (ex. OPEN_MEDIC_2019.csv)
MOTIF_OPENMEDIC = "OPEN_MEDIC_*.CSV"

# Année de référence pour l'analyse des orphelins : idéalement la plus proche
# du millésime de la BDPM téléchargée (mars 2026 → 2024 ou 2025).
ANNEE_ORPHELINS = 2025

# Schéma BDPM attendu (13 colonnes réelles, cf. 5.4)
COLONNES_CIS_CIP = [
    "CIS", "CIP7", "LIBELLE_PRESENTATION", "STATUT_ADMIN",
    "ETAT_COMMERCIALISATION_CIP", "DATE_DECLARATION_COMM", "CIP13",
    "AGREMENT_COLLECTIVITES", "TAUX_REMBOURSEMENT", "PRIX_EURO",
    "PRIX_INDICATION", "INDICATIONS_REMBOURSEMENT", "SOURCE_INDICATIONS",
]
COLONNES_CIS = [
    "CIS", "DENOMINATION", "FORME_PHARMA", "VOIES_ADMIN", "STATUT_AMM",
    "TYPE_PROCEDURE_AMM", "ETAT_COMMERCIALISATION", "DATE_AMM", "STATUT_BDM",
    "NUM_AUTORISATION_EUROPEENNE", "TITULAIRES", "SURVEILLANCE_RENFORCEE",
]


# ============================================================================
# OUTILS
# ============================================================================
def normaliser_code(valeur) -> str:
    """Nettoie un code : espaces, suffixe '.0' des tableurs, non-chiffres."""
    if valeur is None:
        return ""
    s = str(valeur).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return "".join(c for c in s if c.isdigit())


def normaliser_nom_colonne(nom: str) -> str:
    """Minuscules + sans accents + sans séparateurs, pour comparer les en-têtes."""
    nom = unicodedata.normalize("NFKD", str(nom))
    nom = "".join(c for c in nom if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", nom.lower())


def detecter_separateur(chemin: str) -> str:
    """Détecte ; \\t ou , sur la première ligne (comme le fait l'outil)."""
    with open(chemin, encoding="latin-1") as f:
        premiere = f.readline()
    candidats = {";": premiere.count(";"), "\t": premiere.count("\t"),
                 ",": premiere.count(",")}
    return max(candidats, key=candidats.get)


def trouver_colonne_cip13(colonnes) -> str | None:
    """
    Repère la colonne CIP13 par son NOM normalisé, jamais par sa position.
    Gère 'CIP13', 'cip13' ; ignore explicitement 'l_cip13' (libellé, 2025).
    """
    cibles = {normaliser_nom_colonne(c): c for c in colonnes}
    # priorité stricte au nom 'cip13' exact
    if "cip13" in cibles:
        return cibles["cip13"]
    # variantes éventuelles, en excluant tout ce qui commence par un libellé 'l'
    for norm, brut in cibles.items():
        if "cip13" in norm and not norm.startswith("l"):
            return brut
    return None


def compter_colonnes(chemin: str, sep: str, n_echantillon: int = 2000) -> dict:
    """Garde-fou : distribution du nombre de champs (cf. 5.4)."""
    counts: dict[int, int] = {}
    with open(chemin, encoding="latin-1") as f:
        for i, ligne in enumerate(f):
            if i >= n_echantillon:
                break
            n = len(ligne.rstrip("\n").split(sep))
            counts[n] = counts.get(n, 0) + 1
    return counts


def charger_bdpm(chemin: str, colonnes: list[str], sep: str = "\t") -> pd.DataFrame:
    """Chargement BDPM avec garde-fou colonnes (cf. 5.4)."""
    counts = compter_colonnes(chemin, sep)
    dominant = max(counts, key=counts.get)
    noms = colonnes
    if dominant != len(colonnes):
        print(f"    [AVERTISSEMENT] {len(colonnes)} colonnes attendues, "
              f"{dominant} détectées (distribution : {counts})")
        if dominant > len(colonnes):
            noms = colonnes + [f"EXTRA_{i}" for i in range(dominant - len(colonnes))]
        else:
            noms = colonnes[:dominant]
    return pd.read_csv(chemin, sep=sep, names=noms, dtype=str,
                       engine="python", on_bad_lines="skip", encoding="latin-1")


# ============================================================================
# 1. RÉFÉRENTIEL BDPM
# ============================================================================
def charger_reference_bdpm() -> tuple[set, pd.DataFrame]:
    print("Chargement de la BDPM…")
    cis_cip = charger_bdpm(FICHIER_CIS_CIP, COLONNES_CIS_CIP)
    cis_cip["CIP13_norm"] = cis_cip["CIP13"].map(normaliser_code)
    cip13_bdpm = set(cis_cip.loc[cis_cip["CIP13_norm"] != "", "CIP13_norm"])
    print(f"    CIP13 distincts renseignés dans la BDPM : {len(cip13_bdpm):,}")
    return cip13_bdpm, cis_cip


# ============================================================================
# 2. SÉRIE TEMPORELLE
# ============================================================================
def lire_cip13_openmedic(chemin: str) -> tuple[set, str, int]:
    """Retourne (ensemble CIP13 normalisés, nom colonne retenu, nb lignes)."""
    sep = detecter_separateur(chemin)
    # lecture de l'en-tête seul pour repérer la colonne
    entete = pd.read_csv(chemin, sep=sep, nrows=0, dtype=str,
                         engine="python", encoding="latin-1")
    col = trouver_colonne_cip13(entete.columns)
    if col is None:
        raise ValueError(
            f"Colonne CIP13 introuvable dans {os.path.basename(chemin)} "
            f"(colonnes : {list(entete.columns)})")
    df = pd.read_csv(chemin, sep=sep, usecols=[col], dtype=str,
                     engine="python", on_bad_lines="skip", encoding="latin-1")
    codes = df[col].map(normaliser_code)
    ensemble = set(codes[codes != ""])
    return ensemble, col, len(df)


def serie_temporelle(cip13_bdpm: set) -> list[dict]:
    print("\nSérie temporelle du recouvrement OpenMedic → BDPM :")
    fichiers = sorted(glob.glob(os.path.join(DOSSIER_OPENMEDIC, MOTIF_OPENMEDIC)))
    if not fichiers:
        raise FileNotFoundError(
            f"Aucun fichier '{MOTIF_OPENMEDIC}' dans {DOSSIER_OPENMEDIC}")

    lignes = []
    print(f"    {'année':>6} | {'col.':>7} | {'CIP13 OM':>9} | "
          f"{'communs':>8} | {'orphelins':>9} | recouvr.")
    print("    " + "-" * 66)
    for chemin in fichiers:
        m = re.search(r"(20\d{2})", os.path.basename(chemin))
        if not m:
            print(f"    [ignoré] année illisible : {os.path.basename(chemin)}")
            continue
        annee = int(m.group(1))
        cip13_om, col, n = lire_cip13_openmedic(chemin)
        communs = cip13_om & cip13_bdpm
        orphelins = cip13_om - cip13_bdpm
        taux = 100 * len(communs) / len(cip13_om) if cip13_om else 0.0
        lignes.append({
            "annee": annee,
            "colonne_cip13_retenue": col,
            "nb_cip13_openmedic": len(cip13_om),
            "nb_communs": len(communs),
            "nb_orphelins": len(orphelins),
            "taux_recouvrement_om_vers_bdpm_pct": round(taux, 2),
        })
        print(f"    {annee:>6} | {col:>7} | {len(cip13_om):>9,} | "
              f"{len(communs):>8,} | {len(orphelins):>9,} | {taux:6.2f} %")
    return lignes


# ============================================================================
# 3. CARACTÉRISATION DES ORPHELINS
# ============================================================================
def caracteriser_orphelins(cip13_bdpm: set, cis_cip: pd.DataFrame) -> dict:
    print(f"\nCaractérisation des orphelins pour l'année {ANNEE_ORPHELINS} :")
    chemin = None
    for f in glob.glob(os.path.join(DOSSIER_OPENMEDIC, MOTIF_OPENMEDIC)):
        if str(ANNEE_ORPHELINS) in os.path.basename(f):
            chemin = f
            break
    if chemin is None:
        print(f"    [ignoré] fichier {ANNEE_ORPHELINS} introuvable.")
        return {}

    cip13_om, col, _ = lire_cip13_openmedic(chemin)
    orphelins = sorted(cip13_om - cip13_bdpm)
    print(f"    Orphelins (dans OpenMedic {ANNEE_ORPHELINS}, absents BDPM) : "
          f"{len(orphelins):,}")

    # Un orphelin est par définition absent de la BDPM : la plupart n'auront
    # donc AUCUNE trace résiduelle. On mesure d'abord cette part, qui est
    # elle-même un résultat (présentations disparues avant le téléchargement).
    cis = charger_bdpm(FICHIER_CIS, COLONNES_CIS)
    cis_cip = cis_cip.merge(cis[["CIS", "DATE_AMM"]], on="CIS", how="left")

    # Trace résiduelle : un CIP13 orphelin peut exister sous une forme
    # légèrement différente ? Non — par construction il est absent. On rapporte
    # donc les indices ATC portés par OpenMedic lui-même, plus informatifs ici.
    df_om = _lire_openmedic_complet(chemin)
    df_om["CIP13_norm"] = df_om["cip13_col"].map(normaliser_code)
    orph_df = df_om[df_om["CIP13_norm"].isin(set(orphelins))].copy()

    # (a) préfixe ATC1 : quelle famille thérapeutique domine chez les orphelins ?
    repartition_atc1 = {}
    if "ATC1" in orph_df.columns:
        repartition_atc1 = (orph_df.drop_duplicates("CIP13_norm")["ATC1"]
                            .value_counts().head(10).to_dict())

    # (b) volume remboursé : les orphelins sont-ils marginaux ou significatifs ?
    volume = {}
    if "BOITES" in orph_df.columns:
        boites = pd.to_numeric(orph_df["BOITES"], errors="coerce").fillna(0)
        volume = {
            "boites_orphelins_total": int(boites.sum()),
            "boites_orphelins_median_par_ligne": float(boites.median()),
        }

    resultat = {
        "annee": ANNEE_ORPHELINS,
        "nb_orphelins": len(orphelins),
        "part_sans_trace_bdpm_pct": 100.0,  # par construction (absents BDPM)
        "repartition_par_classe_atc1_top10": repartition_atc1,
        "volume_rembourse": volume,
        "echantillon_codes": orphelins[:20],
        "note": ("Un CIP13 orphelin est par définition absent de la BDPM ; sa "
                 "caractérisation s'appuie donc sur les colonnes portées par "
                 "OpenMedic (ATC, volumes), non sur la BDPM. Les codes anciens "
                 "radiés avant le téléchargement BDPM (mars 2026) en constituent "
                 "l'explication attendue."),
    }
    print(f"    Top classes ATC1 : {repartition_atc1}")
    print(f"    Volume : {volume}")
    return resultat


def profils_anciennete_orphelins(cip13_bdpm: set) -> dict:
    """
    Pour les orphelins de l'année de référence, retrace leur présence dans
    TOUS les millésimes OpenMedic afin de distinguer :
      - les « radiés en fin de vie » : remboursés sur plusieurs années
        anciennes, encore présents en année de référence, puis disparus de
        la BDPM (profil compatible avec une radiation entre l'année de
        remboursement et le téléchargement BDPM de mars 2026) ;
      - les « isolés / récents » : présents seulement sur une ou deux années,
        sans historique long, plus compatibles avec une nouveauté mal
        référencée ou une anomalie de saisie.
    Aucune BDPM historique n'est requise : la mesure repose uniquement sur la
    présence multi-annuelle dans OpenMedic, déjà disponible.
    """
    print(f"\nProfils d'ancienneté des orphelins {ANNEE_ORPHELINS} :")
    fichiers = sorted(glob.glob(os.path.join(DOSSIER_OPENMEDIC, MOTIF_OPENMEDIC)))

    # 1) présence de chaque CIP13 dans chaque année
    presence: dict[str, set[int]] = {}
    for chemin in fichiers:
        m = re.search(r"(20\d{2})", os.path.basename(chemin))
        if not m:
            continue
        annee = int(m.group(1))
        codes, _, _ = lire_cip13_openmedic(chemin)
        for c in codes:
            presence.setdefault(c, set()).add(annee)

    # 2) orphelins de l'année de référence
    chemin_ref = next((f for f in fichiers
                       if str(ANNEE_ORPHELINS) in os.path.basename(f)), None)
    if chemin_ref is None:
        print("    [ignoré] année de référence introuvable.")
        return {}
    codes_ref, _, _ = lire_cip13_openmedic(chemin_ref)
    orphelins = sorted(codes_ref - cip13_bdpm)

    # 3) pour chaque orphelin : première/dernière année, nb d'années, durée
    lignes = []
    for c in orphelins:
        annees = sorted(presence.get(c, set()))
        if not annees:
            continue
        lignes.append({
            "cip13": c,
            "premiere_annee": annees[0],
            "derniere_annee": annees[-1],
            "nb_annees": len(annees),
            "duree": annees[-1] - annees[0] + 1,
        })

    # 4) classification en profils
    def profil(l):
        # « ancien en fin de vie » : présent sur >= 4 années et débutant avant 2020
        if l["nb_annees"] >= 4 and l["premiere_annee"] <= 2019:
            return "ancien_fin_de_vie"
        # « récent isolé » : n'apparaît qu'à partir de 2022 et sur <= 2 années
        if l["premiere_annee"] >= 2022 and l["nb_annees"] <= 2:
            return "recent_isole"
        return "intermediaire"

    from collections import Counter
    profils = Counter(profil(l) for l in lignes)
    total = len(lignes) or 1

    # distribution du nombre d'années de présence
    dist_nb_annees = dict(sorted(Counter(l["nb_annees"] for l in lignes).items()))
    # distribution de la première année d'apparition
    dist_premiere = dict(sorted(Counter(l["premiere_annee"] for l in lignes).items()))

    resultat = {
        "annee_reference": ANNEE_ORPHELINS,
        "nb_orphelins_traces": len(lignes),
        "profils": dict(profils),
        "profils_pct": {k: round(100 * v / total, 1) for k, v in profils.items()},
        "distribution_nb_annees_presence": dist_nb_annees,
        "distribution_premiere_annee": dist_premiere,
        "note": ("Un profil 'ancien_fin_de_vie' (présent sur au moins 4 millésimes, "
                 "débutant en 2019 ou avant, puis absent de la BDPM 2026) est "
                 "fortement compatible avec une radiation. Un profil 'recent_isole' "
                 "(apparu à partir de 2022, sur 1 ou 2 années) relève plutôt d'une "
                 "nouveauté mal référencée ou d'une anomalie. Cette analyse ne prouve "
                 "pas la radiation faute de BDPM historique, mais mesure la part des "
                 "orphelins dont le profil temporel y est compatible."),
    }
    print(f"    Orphelins tracés : {len(lignes)}")
    print(f"    Profils : {dict(profils)}")
    print(f"    Répartition première année : {dist_premiere}")
    return resultat


def _lire_openmedic_complet(chemin: str) -> pd.DataFrame:
    sep = detecter_separateur(chemin)
    df = pd.read_csv(chemin, sep=sep, dtype=str, engine="python",
                     on_bad_lines="skip", encoding="latin-1")
    col = trouver_colonne_cip13(df.columns)
    df = df.rename(columns={col: "cip13_col"})
    # harmonise ATC1 quelle que soit la casse
    for c in df.columns:
        if normaliser_nom_colonne(c) == "atc1":
            df = df.rename(columns={c: "ATC1"})
        if normaliser_nom_colonne(c) == "boites":
            df = df.rename(columns={c: "BOITES"})
    return df


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 70)
    print("ANALYSE CROISÉE BDPM × OPENMEDIC — RÉSULTATS RÉELS")
    print("=" * 70)

    cip13_bdpm, cis_cip = charger_reference_bdpm()
    serie = serie_temporelle(cip13_bdpm)
    orphelins = caracteriser_orphelins(cip13_bdpm, cis_cip)
    anciennete = profils_anciennete_orphelins(cip13_bdpm)

    resultats = {
        "date_analyse": datetime.now().strftime("%Y-%m-%d"),
        "statut": "RÉEL",
        "nb_cip13_bdpm_reference": len(cip13_bdpm),
        "serie_temporelle": serie,
        "orphelins": orphelins,
        "orphelins_anciennete": anciennete,
    }
    sortie = os.path.join(DOSSIER_SORTIE, "analyse_croisee_reelle.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Résultats écrits dans : {sortie}")
    print("Colle ce JSON dans le chat : je remplis §5.4, §5.5 et la nouvelle "
          "sous-section orphelins avec les chiffres réels.")
    print("=" * 70)


if __name__ == "__main__":
    main()
