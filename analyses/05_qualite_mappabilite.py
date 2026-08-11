"""
Analyses de qualité et de mappabilité — BDPM × OpenMedic

Script complémentaire, autonome, à exécuter séparément du croisement
multi-années. Il produit trois analyses qui portent non plus sur le NOMBRE
de codes qui se relient, mais sur la QUALITÉ de ce lien et sur sa
transposabilité vers les standards internationaux (RxNorm / ATC) :

  1. Concordance / conservation de l'information : sur les CIP13 communs,
     part des appariements qui conservent une DCI exploitable (vs codes
     retrouvés mais informativement creux).
  2. Mappabilité par la substance : typologie mono / bi / multi-substance
     des spécialités ; la part mono-substance borne le mapping 1-1 « facile »
     vers RxNorm.
  3. Poids des multi-substances parmi les codes réellement remboursés et
     chaînés, comparé à leur poids dans l'ensemble de la BDPM.

Aucune donnée supplémentaire n'est requise : le script réutilise les fichiers
BDPM (dont CIS_COMPO) et le millésime OpenMedic déjà présents.

Dépendances : uv add pandas
Lancement    : uv run analyses_qualite_mappabilite.py
"""

import glob
import json
import os
import re
import unicodedata
from datetime import datetime

import pandas as pd

# ============================================================================
# CHEMINS — [À ADAPTER si besoin, identiques au script de croisement]
# ============================================================================
DOSSIER_OPENMEDIC = "data"
FICHIER_CIS_CIP = "data/CIS_CIP_bdpm.txt"
FICHIER_CIS_COMPO = "data/CIS_COMPO_bdpm.txt"
DOSSIER_SORTIE = "."
MOTIF_OPENMEDIC = "OPEN_MEDIC_*.CSV"

# Millésime OpenMedic sur lequel portent les analyses 1 et 3.
ANNEE_REFERENCE = 2024

COLONNES_CIS_CIP = [
    "CIS", "CIP7", "LIBELLE_PRESENTATION", "STATUT_ADMIN",
    "ETAT_COMMERCIALISATION_CIP", "DATE_DECLARATION_COMM", "CIP13",
    "AGREMENT_COLLECTIVITES", "TAUX_REMBOURSEMENT", "PRIX_EURO",
    "PRIX_INDICATION", "INDICATIONS_REMBOURSEMENT", "SOURCE_INDICATIONS",
]
COLONNES_CIS_COMPO = [
    "CIS", "ELEMENT_PHARMA", "CODE_SUBSTANCE", "DCI", "DOSAGE",
    "REF_DOSAGE", "NATURE_COMPOSANT", "NUM_LIAISON",
]


# ============================================================================
# OUTILS (repris à l'identique du script de croisement, pour l'autonomie)
# ============================================================================
def normaliser(texte) -> str:
    if not isinstance(texte, str):
        return ""
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return " ".join(texte.lower().split())


def normaliser_code(valeur) -> str:
    if valeur is None:
        return ""
    s = str(valeur).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return "".join(c for c in s if c.isdigit())


def normaliser_nom_colonne(nom: str) -> str:
    nom = unicodedata.normalize("NFKD", str(nom))
    nom = "".join(c for c in nom if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", nom.lower())


def detecter_separateur(chemin: str) -> str:
    with open(chemin, encoding="latin-1") as f:
        premiere = f.readline()
    candidats = {";": premiere.count(";"), "\t": premiere.count("\t"),
                 ",": premiere.count(",")}
    return max(candidats, key=candidats.get)


def trouver_colonne_cip13(colonnes):
    cibles = {normaliser_nom_colonne(c): c for c in colonnes}
    if "cip13" in cibles:
        return cibles["cip13"]
    for norm, brut in cibles.items():
        if "cip13" in norm and not norm.startswith("l"):
            return brut
    return None


def compter_colonnes(chemin: str, sep: str, n_echantillon: int = 2000) -> dict:
    counts = {}
    with open(chemin, encoding="latin-1") as f:
        for i, ligne in enumerate(f):
            if i >= n_echantillon:
                break
            n = len(ligne.rstrip("\n").split(sep))
            counts[n] = counts.get(n, 0) + 1
    return counts


def charger_bdpm(chemin: str, colonnes, sep: str = "\t") -> pd.DataFrame:
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


def lire_openmedic_annee(annee: int) -> set:
    """Retourne l'ensemble des CIP13 normalisés du millésime demandé."""
    fichiers = glob.glob(os.path.join(DOSSIER_OPENMEDIC, MOTIF_OPENMEDIC))
    chemin = next((f for f in fichiers if str(annee) in os.path.basename(f)), None)
    if chemin is None:
        raise FileNotFoundError(f"Millésime OpenMedic {annee} introuvable.")
    sep = detecter_separateur(chemin)
    entete = pd.read_csv(chemin, sep=sep, nrows=0, dtype=str,
                         engine="python", encoding="latin-1")
    col = trouver_colonne_cip13(entete.columns)
    if col is None:
        raise ValueError(f"Colonne CIP13 introuvable dans {os.path.basename(chemin)}")
    df = pd.read_csv(chemin, sep=sep, usecols=[col], dtype=str,
                     engine="python", on_bad_lines="skip", encoding="latin-1")
    codes = df[col].map(normaliser_code)
    return set(codes[codes != ""])


# ============================================================================
# RÉFÉRENCES BDPM
# ============================================================================
def charger_references():
    print("Chargement de la BDPM (CIS_CIP + CIS_COMPO)…")
    cis_cip = charger_bdpm(FICHIER_CIS_CIP, COLONNES_CIS_CIP)
    cis_cip["CIP13_norm"] = cis_cip["CIP13"].map(normaliser_code)
    cip13_bdpm = set(cis_cip.loc[cis_cip["CIP13_norm"] != "", "CIP13_norm"])

    cis_compo = charger_bdpm(FICHIER_CIS_COMPO, COLONNES_CIS_COMPO)
    print(f"    CIP13 BDPM : {len(cip13_bdpm):,} | "
          f"lignes composition : {len(cis_compo):,}")

    cip_vers_cis = dict(zip(cis_cip["CIP13_norm"], cis_cip["CIS"]))
    cis_nb_dci = (cis_compo.assign(DCI_norm=cis_compo["DCI"].map(normaliser))
                  .query("DCI_norm != ''")
                  .groupby("CIS")["DCI_norm"].nunique())
    return cip13_bdpm, cip_vers_cis, cis_nb_dci


# ============================================================================
# ANALYSE 1 — conservation de l'information (DCI) sur les codes chaînés
# ============================================================================
def analyse_1(cip13_bdpm, cip_vers_cis, cis_nb_dci) -> dict:
    print("\n[Analyse 1] Conservation de la DCI sur les appariements :")
    communs = lire_openmedic_annee(ANNEE_REFERENCE) & cip13_bdpm
    avec = sans = 0
    for cip in communs:
        cis = cip_vers_cis.get(cip)
        if cis and cis_nb_dci.get(cis, 0) > 0:
            avec += 1
        else:
            sans += 1
    total = avec + sans or 1
    r = {
        "annee": ANNEE_REFERENCE,
        "nb_communs_analyses": total,
        "apparies_avec_dci": avec,
        "apparies_sans_dci": sans,
        "taux_conservation_dci_pct": round(100 * avec / total, 2),
        "note": ("Part des CIP13 communs dont la spécialité BDPM atteinte porte au "
                 "moins une DCI exploitable. Un appariement 'sans DCI' compte dans le "
                 "taux de recouvrement (5.4) mais ne permet ni bascule vers la "
                 "substance ni vers l'international : le taux mesure la fréquence du "
                 "lien, celui-ci mesure l'information qu'il conserve."),
    }
    print(f"    Communs : {total:,} | avec DCI : {avec:,} "
          f"({r['taux_conservation_dci_pct']} %) | sans DCI : {sans:,}")
    return r


# ============================================================================
# ANALYSE 2 — typologie de mappabilité par la substance
# ============================================================================
def analyse_2(cis_nb_dci) -> dict:
    print("\n[Analyse 2] Mappabilité par la substance (mono / bi / multi) :")
    g = cis_nb_dci
    total = int(g.shape[0]) or 1
    mono = int((g == 1).sum())
    bi = int((g == 2).sum())
    multi = int((g >= 3).sum())
    r = {
        "nb_cis_avec_composition": total,
        "mono_substance": mono,
        "bi_substance": bi,
        "multi_substance_3plus": multi,
        "mono_pct": round(100 * mono / total, 1),
        "bi_pct": round(100 * bi / total, 1),
        "multi_pct": round(100 * multi / total, 1),
        "max_substances": int(g.max()),
        "note": ("La part mono-substance borne le mapping 1-1 'facile' vers RxNorm / "
                 "ATC ; bi- et multi-substances exigent un traitement d'association "
                 "que ni l'ATC ni RxNorm ne restituent trivialement."),
    }
    print(f"    CIS : {total:,} | mono : {mono:,} ({r['mono_pct']} %) | "
          f"bi : {bi:,} ({r['bi_pct']} %) | multi≥3 : {multi:,} ({r['multi_pct']} %) | "
          f"max : {r['max_substances']}")
    return r


# ============================================================================
# ANALYSE 3 — poids des multi-substances parmi les codes chaînés
# ============================================================================
def analyse_3(cip13_bdpm, cip_vers_cis, cis_nb_dci, mappabilite: dict) -> dict:
    print("\n[Analyse 3] Poids des multi-substances parmi les codes chaînés :")
    communs = lire_openmedic_annee(ANNEE_REFERENCE) & cip13_bdpm
    mono = multi = inconnu = 0
    for cip in communs:
        cis = cip_vers_cis.get(cip)
        n = int(cis_nb_dci.get(cis, 0)) if cis else 0
        if n == 0:
            inconnu += 1
        elif n == 1:
            mono += 1
        else:
            multi += 1
    base = mono + multi or 1
    part_chaines = round(100 * multi / base, 1)
    part_reference = mappabilite.get("multi_pct", 0.0)
    r = {
        "annee": ANNEE_REFERENCE,
        "nb_communs": len(communs),
        "chaines_mono_substance": mono,
        "chaines_multi_substance": multi,
        "chaines_sans_composition": inconnu,
        "part_multi_parmi_chaines_pct": part_chaines,
        "part_multi_dans_bdpm_pct": part_reference,
        "ecart_points": round(part_chaines - part_reference, 1),
        "note": ("Compare la part multi-substance parmi les codes remboursés et "
                 "chaînés à sa part dans l'ensemble de la BDPM (analyse 2). Un écart "
                 "positif signifierait que les associations pèsent davantage dans la "
                 "consommation réelle que dans le référentiel, amplifiant le problème "
                 "de mapping international."),
    }
    print(f"    Chaînés mono : {mono:,} | multi : {multi:,} ({part_chaines} %) | "
          f"sans compo : {inconnu:,}")
    print(f"    Multi parmi chaînés : {part_chaines} % vs BDPM : {part_reference} % "
          f"(écart : {r['ecart_points']} pts)")
    return r


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 70)
    print("ANALYSES DE QUALITÉ ET DE MAPPABILITÉ — BDPM × OPENMEDIC")
    print("=" * 70)

    cip13_bdpm, cip_vers_cis, cis_nb_dci = charger_references()
    a1 = analyse_1(cip13_bdpm, cip_vers_cis, cis_nb_dci)
    a2 = analyse_2(cis_nb_dci)
    a3 = analyse_3(cip13_bdpm, cip_vers_cis, cis_nb_dci, a2)

    resultats = {
        "date_analyse": datetime.now().strftime("%Y-%m-%d"),
        "statut": "RÉEL",
        "annee_reference": ANNEE_REFERENCE,
        "analyse1_conservation_dci": a1,
        "analyse2_mappabilite_dci": a2,
        "analyse3_multisubstances_chaines": a3,
    }
    sortie = os.path.join(DOSSIER_SORTIE, "analyses_qualite_mappabilite.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Résultats écrits dans : {sortie}")
    print("Colle ce JSON dans le chat : j'écris les trois sous-sections "
          "correspondantes avec les chiffres réels.")
    print("=" * 70)


if __name__ == "__main__":
    main()
