"""
Exploration BDPM × OpenMedic - Étape 4 : Analyse croisée et taux de recouvrement

IMPORTANT : Télécharger d'abord OpenMedic 2024 depuis :
https://www.assurance-maladie.ameli.fr/etudes-et-donnees/open-medic-base-complete-depenses-medicaments
Fichier : Open_Medic_2024.csv (année 2024 uniquement)

"""

import pandas as pd
import numpy as np
import json
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = 'data/'

# Fichiers sources
FICHIER_OPENMEDIC = 'OPEN_MEDIC_2024.csv'  # À télécharger
FICHIER_CIS_CIP = 'CIS_CIP_bdpm.txt'
FICHIER_CIS = 'CIS_bdpm.txt'

print("="*80)
print("ANALYSE CROISÉE BDPM × OPENMEDIC - ÉTAPE 4")
print("="*80)
print(f"\n📅 Date d'analyse : {datetime.now().strftime('%Y-%m-%d')}")
print(f"🎯 Objectif : Mesurer l'interopérabilité CIP13 entre BDPM et OpenMedic\n")

# ============================================================================
# 1. CHARGEMENT DES DONNÉES
# ============================================================================

print("1️⃣  CHARGEMENT DES DONNÉES")
print("─"*80 + "\n")

# Charger la BDPM (CIS-CIP)
print("⬇️  Chargement BDPM (CIS_CIP_bdpm.txt)...")
try:
    cis_cip_df = pd.read_csv(
        DATA_DIR + FICHIER_CIS_CIP,
        sep='\t',
        encoding='utf-8',
        names=['CIS', 'CIP7', 'LIBELLE_PRESENTATION', 'STATUT_ADMIN', 
               'ETAT_COMMERCIALISATION', 'DATE_DECLARATION_COMMERCIALISATION',
               'CIP13', 'AGREMENT_COLLECTIVITES', 'TAUX_REMBOURSEMENT',
               'PRIX_EURO', 'PRIX_INDICATION'],
        dtype=str
    )
    print(f"   ✅ {len(cis_cip_df):,} lignes chargées\n")
except FileNotFoundError:
    print("   ❌ Fichier CIS_CIP_bdpm.txt introuvable !")
    exit(1)

# Charger OpenMedic 2024
print(f"⬇️  Chargement OpenMedic ({FICHIER_OPENMEDIC})...")
try:
    # OpenMedic est en CSV avec séparateur point-virgule
    openmedic_df = pd.read_csv(
        DATA_DIR + FICHIER_OPENMEDIC,
        sep=';',
        encoding='iso-8859-1',
        dtype=str,
        low_memory=False
    )
    print(f"   ✅ {len(openmedic_df):,} lignes chargées")
    print(f"   ✅ {len(openmedic_df.columns)} colonnes détectées\n")
    
    # Afficher les premières colonnes pour vérifier la structure
    print(f"   Colonnes détectées : {list(openmedic_df.columns[:10])}\n")
    
except FileNotFoundError:
    print(f"   ❌ ERREUR : Fichier {FICHIER_OPENMEDIC} introuvable !")
    print(f"\n   📥 INSTRUCTIONS DE TÉLÉCHARGEMENT :")
    print(f"   1. Aller sur : https://www.assurance-maladie.ameli.fr/etudes-et-donnees/open-medic-base-complete-depenses-medicaments")
    print(f"   2. Télécharger 'Open Medic : base complète 2024'")
    print(f"   3. Extraire le fichier CSV")
    print(f"   4. Renommer en '{FICHIER_OPENMEDIC}' (ou modifier FICHIER_OPENMEDIC dans ce script)")
    print(f"   5. Placer dans {DATA_DIR}\n")
    exit(1)

# ============================================================================
# 2. PRÉPARATION DES DONNÉES
# ============================================================================

print("\n2️⃣  PRÉPARATION DES DONNÉES")
print("─"*80 + "\n")

# Nettoyer les CIP13 de la BDPM
print("🧹 Nettoyage des CIP13 BDPM...")
cis_cip_clean = cis_cip_df[cis_cip_df['CIP13'].notna()].copy()
cis_cip_clean['CIP13'] = cis_cip_clean['CIP13'].str.strip()

# Enlever les CIP13 vides après strip
cis_cip_clean = cis_cip_clean[cis_cip_clean['CIP13'] != '']

nb_cip13_bdpm = cis_cip_clean['CIP13'].nunique()
print(f"   • CIP13 uniques dans BDPM : {nb_cip13_bdpm:,}\n")

# Identifier la colonne CIP13 dans OpenMedic
# Les noms de colonnes possibles : 'L_CIP13', 'CIP13', 'cip13', etc.
cip_column_openmedic = None
for col in openmedic_df.columns:
    if 'cip' in col.lower() and '13' in col.lower():
        cip_column_openmedic = col
        break

if cip_column_openmedic is None:
    # Essayer sans le "13"
    for col in openmedic_df.columns:
        if col.lower() == 'cip' or col.lower() == 'l_cip':
            cip_column_openmedic = col
            break

if cip_column_openmedic is None:
    print("   ⚠️  ATTENTION : Colonne CIP13 non trouvée automatiquement dans OpenMedic")
    print(f"   Colonnes disponibles : {list(openmedic_df.columns)}")
    print("\n   Veuillez identifier manuellement la colonne CIP et modifier le script.\n")
    exit(1)

print(f"🔍 Colonne CIP identifiée dans OpenMedic : '{cip_column_openmedic}'")

# Nettoyer les CIP13 d'OpenMedic
openmedic_df[cip_column_openmedic] = openmedic_df[cip_column_openmedic].astype(str).str.strip()
openmedic_clean = openmedic_df[openmedic_df[cip_column_openmedic].notna()].copy()
openmedic_clean = openmedic_clean[openmedic_clean[cip_column_openmedic] != '']
openmedic_clean = openmedic_clean[openmedic_clean[cip_column_openmedic] != 'nan']

nb_cip13_openmedic = openmedic_clean[cip_column_openmedic].nunique()
print(f"   • CIP13 uniques dans OpenMedic 2024 : {nb_cip13_openmedic:,}\n")

# ============================================================================
# 3. ANALYSE DE RECOUVREMENT
# ============================================================================

print("\n3️⃣  ANALYSE DE RECOUVREMENT BDPM ↔ OPENMEDIC")
print("─"*80 + "\n")

# Ensembles de CIP13
set_bdpm = set(cis_cip_clean['CIP13'].unique())
set_openmedic = set(openmedic_clean[cip_column_openmedic].unique())

# Intersection et différences
intersection = set_bdpm & set_openmedic
cip_only_bdpm = set_bdpm - set_openmedic
cip_only_openmedic = set_openmedic - set_bdpm

print("📊 Statistiques de recouvrement :\n")

print(f"   • CIP13 dans BDPM uniquement : {len(cip_only_bdpm):,} ({len(cip_only_bdpm)/len(set_bdpm)*100:.1f}%)")
print(f"   • CIP13 dans OpenMedic uniquement : {len(cip_only_openmedic):,} ({len(cip_only_openmedic)/len(set_openmedic)*100:.1f}%)")
print(f"   • CIP13 en commun (intersection) : {len(intersection):,}\n")

# Taux de recouvrement
taux_bdpm_vers_openmedic = len(intersection) / len(set_bdpm) * 100 if len(set_bdpm) > 0 else 0
taux_openmedic_vers_bdpm = len(intersection) / len(set_openmedic) * 100 if len(set_openmedic) > 0 else 0

print("📈 Taux de recouvrement (correspondance) :\n")
print(f"   • BDPM → OpenMedic : {taux_bdpm_vers_openmedic:.2f}%")
print(f"     ({len(intersection):,} CIP13 de la BDPM retrouvés dans OpenMedic)")
print(f"\n   • OpenMedic → BDPM : {taux_openmedic_vers_bdpm:.2f}%")
print(f"     ({len(intersection):,} CIP13 d'OpenMedic retrouvés dans la BDPM)\n")

# ============================================================================
# 4. ANALYSE DES CIP13 ABSENTS DE LA BDPM
# ============================================================================

print("\n4️⃣  ANALYSE DES CIP13 OPENMEDIC ABSENTS DE LA BDPM")
print("─"*80 + "\n")

if len(cip_only_openmedic) > 0:
    print(f"⚠️  {len(cip_only_openmedic):,} CIP13 présents dans OpenMedic 2024 mais absents de la BDPM\n")
    
    # Analyser ces CIP13 manquants dans OpenMedic
    cip_manquants = openmedic_clean[openmedic_clean[cip_column_openmedic].isin(cip_only_openmedic)]
    
    print("   Hypothèses expliquant ces absences :")
    print("   1. Médicaments radiés entre la date MAJ BDPM (02/03/2026) et l'année 2024")
    print("   2. Décalage temporel : OpenMedic 2024 inclut des CIP commercialisés en 2024,")
    print("      mais la BDPM n'est mise à jour que début 2026")
    print("   3. Erreurs de codification ou codes temporaires dans OpenMedic")
    print("   4. CIP13 d'établissements ou dispositifs non couverts par la BDPM\n")
    
    # Échantillon des CIP manquants
    print("   📋 Échantillon de CIP13 absents (10 premiers) :")
    sample_missing = list(cip_only_openmedic)[:10]
    for cip in sample_missing:
        print(f"      - {cip}")
    
    if len(cip_only_openmedic) > 10:
        print(f"      ... et {len(cip_only_openmedic) - 10:,} autres\n")
else:
    print("✅ Tous les CIP13 d'OpenMedic sont présents dans la BDPM (recouvrement 100%)\n")

# ============================================================================
# 5. ANALYSE DES CIP13 BDPM ABSENTS D'OPENMEDIC
# ============================================================================

print("\n5️⃣  ANALYSE DES CIP13 BDPM ABSENTS D'OPENMEDIC")
print("─"*80 + "\n")

if len(cip_only_bdpm) > 0:
    print(f"⚠️  {len(cip_only_bdpm):,} CIP13 présents dans la BDPM mais absents d'OpenMedic 2024\n")
    
    # Analyser ces CIP13 dans la BDPM
    cip_bdpm_non_utilises = cis_cip_clean[cis_cip_clean['CIP13'].isin(cip_only_bdpm)]
    
    # Distribution par statut de commercialisation
    if 'ETAT_COMMERCIALISATION' in cip_bdpm_non_utilises.columns:
        print("   📊 Distribution par état de commercialisation :")
        etat_dist = cip_bdpm_non_utilises['ETAT_COMMERCIALISATION'].value_counts()
        for etat, count in etat_dist.items():
            pct = count / len(cip_bdpm_non_utilises) * 100
            print(f"      - {etat}: {count:,} ({pct:.1f}%)")
        print()
    
    print("   Interprétation :")
    print("   • CIP13 non remboursés en 2024 (médicaments non commercialisés)")
    print("   • Spécialités hospitalières (UCD) non présentes dans OpenMedic (ville)")
    print("   • Médicaments d'accès précoce ou ATU non encore remboursés")
    print("   • Dispositifs médicaux codés en CIP mais hors périmètre OpenMedic\n")
else:
    print("✅ Tous les CIP13 de la BDPM sont présents dans OpenMedic (usage 100%)\n")

# ============================================================================
# 6. EXPORT DES RÉSULTATS
# ============================================================================

print("\n6️⃣  EXPORT DES RÉSULTATS")
print("─"*80 + "\n")

resultats = {
    'date_analyse': datetime.now().strftime('%Y-%m-%d'),
    'sources': {
        'bdpm': 'CIS_CIP_bdpm.txt (MAJ 02/03/2026)',
        'openmedic': f'{FICHIER_OPENMEDIC} (année 2024)'
    },
    'volumes': {
        'nb_cip13_bdpm': int(nb_cip13_bdpm),
        'nb_cip13_openmedic': int(nb_cip13_openmedic),
        'nb_intersection': int(len(intersection)),
        'nb_cip_only_bdpm': int(len(cip_only_bdpm)),
        'nb_cip_only_openmedic': int(len(cip_only_openmedic))
    },
    'taux_recouvrement': {
        'bdpm_vers_openmedic_pct': round(taux_bdpm_vers_openmedic, 2),
        'openmedic_vers_bdpm_pct': round(taux_openmedic_vers_bdpm, 2)
    },
    'interpretation': {
        'qualite_chainage': 'Bon' if taux_openmedic_vers_bdpm > 90 else 'Moyen' if taux_openmedic_vers_bdpm > 75 else 'Faible',
        'gap_identifie': len(cip_only_openmedic) > 0
    }
}

# Exporter en JSON
output_file = 'resultats/analyse_croisee_bdpm_openmedic.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(resultats, f, indent=2, ensure_ascii=False)

print(f"✅ Résultats exportés dans : {output_file}\n")

# Exporter la liste des CIP manquants
if len(cip_only_openmedic) > 0:
# LIGNE 277 - CORRECT
    cip_manquants_file = 'resultats/cip13_openmedic_absents_bdpm.txt'   
    with open(cip_manquants_file, 'w') as f:
        for cip in sorted(cip_only_openmedic):
            f.write(f"{cip}\n")
    print(f"✅ Liste des CIP13 manquants exportée : {cip_manquants_file}")

if len(cip_only_bdpm) > 0:
# LIGNE 284 - CORRECT
    cip_non_utilises_file = 'resultats/cip13_bdpm_non_utilises_openmedic.txt'    
    with open(cip_non_utilises_file, 'w') as f:
        for cip in sorted(cip_only_bdpm):
            f.write(f"{cip}\n")
    print(f"✅ Liste des CIP13 non utilisés exportée : {cip_non_utilises_file}\n")

# ============================================================================
# 7. SYNTHÈSE POUR LE MÉMOIRE
# ============================================================================

print("\n7️⃣  SYNTHÈSE POUR LE MÉMOIRE")
print("─"*80 + "\n")

print("📊 RÉSULTATS QUANTITATIFS CLÉS :\n")
print(f"   • Taux de recouvrement OpenMedic → BDPM : {taux_openmedic_vers_bdpm:.1f}%")
print(f"   • CIP13 OpenMedic absents BDPM : {len(cip_only_openmedic):,} ({len(cip_only_openmedic)/nb_cip13_openmedic*100:.1f}%)")
print(f"   • CIP13 BDPM non utilisés en 2024 : {len(cip_only_bdpm):,} ({len(cip_only_bdpm)/nb_cip13_bdpm*100:.1f}%)\n")

print("✍️  INTERPRÉTATION :\n")

if taux_openmedic_vers_bdpm >= 95:
    print("   ✅ Excellent recouvrement : la BDPM couvre quasi-intégralement les")
    print("      médicaments remboursés en ville (OpenMedic). Le chaînage BDPM ↔ OpenMedic")
    print("      via CIP13 est fiable pour l'analyse pharmaco-épidémiologique.\n")
elif taux_openmedic_vers_bdpm >= 85:
    print("   ⚠️  Bon recouvrement avec quelques gaps : la majorité des médicaments")
    print("      OpenMedic trouve une correspondance BDPM. Les écarts peuvent s'expliquer")
    print("      par des délais de mise à jour entre les deux bases.\n")
else:
    print("   ❌ Recouvrement insuffisant : des lacunes structurelles existent entre")
    print("      BDPM et OpenMedic. Analyse approfondie nécessaire des CIP manquants.\n")

print("🎯 IMPLICATIONS POUR L'INTEROPÉRABILITÉ :\n")
print("   • La relation BDPM ↔ OpenMedic via CIP13 est la clé de voûte")
print("     du chaînage entre référentiels (CIS) et données de remboursement (ATC).")
print(f"   • Taux de succès observé : {taux_openmedic_vers_bdpm:.1f}% des CIP13 OpenMedic")
print("     trouvent une correspondance dans la BDPM.")
print("   • Gap documenté : nécessité d'une stratégie de gestion des CIP13 orphelins")
print("     (codes présents dans une base mais absents de l'autre).\n")

print("="*80)
print("✅ Analyse croisée terminée")
print("="*80)
