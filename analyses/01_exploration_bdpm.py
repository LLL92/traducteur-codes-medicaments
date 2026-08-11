"""
Exploration de la BDPM - Étape 1 : Analyse descriptive des fichiers
Date de collecte : 2026-03-26
Source : https://base-donnees-publique.medicaments.gouv.fr/
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Chemins des fichiers
FICHIERS = {
    'CIS_bdpm.txt': 'Spécialités (référentiel pivot)',
    'CIS_CIP_bdpm.txt': 'Présentations (correspondance CIS→CIP)',
    'CIS_COMPO_bdpm.txt': 'Compositions (correspondance CIS→DCI)',
    'CIS_CPD_bdpm.txt': 'Conditions de prescription et délivrance',
    'CIS_GENER_bdpm.txt': 'Groupes génériques'
}

DATA_DIR = 'data/'

# Métadonnées de collecte
METADATA = {
    'date_collecte': '2026-03-26',
    'source': 'https://base-donnees-publique.medicaments.gouv.fr/',
    'date_maj_bdpm': '02/03/2026',
    'version_bdpm': 'v4'
}

# ============================================================================
# 1. CHARGEMENT DES FICHIERS
# ============================================================================

print("="*80)
print("EXPLORATION DE LA BDPM - ÉTAPE 1 : ANALYSE DESCRIPTIVE")
print("="*80)
print(f"\n📅 Date de collecte : {METADATA['date_collecte']}")
print(f"📅 Date de mise à jour BDPM : {METADATA['date_maj_bdpm']}")
print(f"🔗 Source : {METADATA['source']}\n")

# Structure des fichiers selon la documentation BDPM
SCHEMAS = {
    'CIS_bdpm.txt': {
        'sep': '\t',
        'encoding': 'iso-8859-1',
        'names': ['CIS', 'NOM', 'FORME', 'VOIES_ADMIN', 'STATUT_AMM', 
                  'TYPE_PROC_AMM', 'COMMERCIALISATION', 'DATE_AMM', 
                  'STATUT_BDM', 'NUM_AUTORISATION_EU', 'TITULAIRES', 
                  'SURVEILLANCE_RENFORCEE']
    },
    'CIS_CIP_bdpm.txt': {
        'sep': '\t',
        'encoding': 'utf-8',
        'names': ['CIS', 'CIP7', 'LIBELLE_PRESENTATION', 'STATUT_ADMIN', 
                  'ETAT_COMMERCIALISATION', 'DATE_DECLARATION_COMMERCIALISATION',
                  'CIP13', 'AGREMENT_COLLECTIVITES', 'TAUX_REMBOURSEMENT',
                  'PRIX_EURO', 'PRIX_INDICATION']
    },
    'CIS_COMPO_bdpm.txt': {
        'sep': '\t',
        'encoding': 'iso-8859-1',
        'names': ['CIS', 'DESIGNATION_ELEMENT', 'CODE_SUBSTANCE', 
                  'NOM_SUBSTANCE', 'DOSAGE', 'REFERENCE_DOSAGE', 
                  'NATURE_COMPOSANT', 'NUMERO_LIAISON']
    },
    'CIS_CPD_bdpm.txt': {
        'sep': '\t',
        'encoding': 'iso-8859-1',
        'names': ['CIS', 'CONDITION']
    },
    'CIS_GENER_bdpm.txt': {
        'sep': '\t',
        'encoding': 'iso-8859-1',
        'names': ['ID_GROUPE', 'LIBELLE_GROUPE', 'CIS', 'TYPE_GENERIQUE', 
                  'NUM_ORDRE']
    }
}

# Chargement des fichiers
dataframes = {}
for fichier, description in FICHIERS.items():
    print(f"⬇️  Chargement : {fichier} ({description})")
    try:
        schema = SCHEMAS[fichier]
        df = pd.read_csv(
            DATA_DIR + fichier,
            sep=schema['sep'],
            encoding=schema['encoding'],
            names=schema['names'],
            dtype=str,  # Tout en string pour éviter les problèmes de typage
            na_values=['', 'NA', 'null'],
            keep_default_na=True
        )
        dataframes[fichier.replace('.txt', '')] = df
        print(f"   ✅ {len(df):,} lignes chargées\n")
    except Exception as e:
        print(f"   ❌ Erreur : {e}\n")

# ============================================================================
# 2. ANALYSE DESCRIPTIVE DE CHAQUE FICHIER
# ============================================================================

print("\n" + "="*80)
print("2. ANALYSE DESCRIPTIVE DES FICHIERS")
print("="*80 + "\n")

resultats = {}

for nom_fichier, df in dataframes.items():
    print(f"\n{'─'*80}")
    print(f"📄 Fichier : {nom_fichier}")
    print(f"{'─'*80}")
    
    # Statistiques de base
    nb_lignes = len(df)
    nb_colonnes = len(df.columns)
    taille_memoire = df.memory_usage(deep=True).sum() / 1024**2  # en MB
    
    print(f"\n📊 Dimensions :")
    print(f"   • Lignes : {nb_lignes:,}")
    print(f"   • Colonnes : {nb_colonnes}")
    print(f"   • Mémoire : {taille_memoire:.2f} MB")
    
    # Valeurs manquantes par colonne
    print(f"\n🔍 Valeurs manquantes :")
    missing = df.isnull().sum()
    missing_pct = (missing / nb_lignes * 100).round(2)
    missing_df = pd.DataFrame({
        'Colonne': df.columns,
        'Nb_manquants': missing.values,
        'Pct_manquants': missing_pct.values
    })
    missing_df = missing_df[missing_df['Nb_manquants'] > 0].sort_values(
        'Pct_manquants', ascending=False
    )
    
    if len(missing_df) > 0:
        for _, row in missing_df.iterrows():
            print(f"   • {row['Colonne']}: {row['Nb_manquants']:,} ({row['Pct_manquants']:.1f}%)")
    else:
        print("   ✅ Aucune valeur manquante")
    
    # Doublons
    print(f"\n🔄 Doublons :")
    nb_doublons = df.duplicated().sum()
    print(f"   • Lignes dupliquées : {nb_doublons:,} ({nb_doublons/nb_lignes*100:.2f}%)")
    
    # Analyse spécifique par fichier
    print(f"\n📈 Analyse spécifique :")
    
    if nom_fichier == 'CIS_bdpm':
        # Nombre de CIS uniques (clé primaire)
        nb_cis_unique = df['CIS'].nunique()
        print(f"   • CIS uniques : {nb_cis_unique:,}")
        print(f"   • CIS dupliqués : {nb_lignes - nb_cis_unique:,}")
        
        # Distribution par statut AMM
        print(f"\n   Statut AMM :")
        statut_counts = df['STATUT_AMM'].value_counts()
        for statut, count in statut_counts.items():
            print(f"      - {statut}: {count:,} ({count/nb_lignes*100:.1f}%)")
        
        # Distribution par commercialisation
        print(f"\n   Commercialisation :")
        comm_counts = df['COMMERCIALISATION'].value_counts()
        for comm, count in comm_counts.items():
            print(f"      - {comm}: {count:,} ({count/nb_lignes*100:.1f}%)")
    
    elif nom_fichier == 'CIS_CIP_bdpm':
        # Relation CIS → CIP (cardinalité)
        nb_cis = df['CIS'].nunique()
        nb_cip13 = df['CIP13'].nunique()
        nb_cip7 = df['CIP7'].nunique()
        
        print(f"   • CIS distincts : {nb_cis:,}")
        print(f"   • CIP13 distincts : {nb_cip13:,}")
        print(f"   • CIP7 distincts : {nb_cip7:,}")
        
        # Cardinalité moyenne CIS → CIP
        cis_counts = df.groupby('CIS').size()
        print(f"\n   Cardinalité CIS → CIP :")
        print(f"      - Moyenne : {cis_counts.mean():.2f} CIP par CIS")
        print(f"      - Médiane : {cis_counts.median():.0f}")
        print(f"      - Max : {cis_counts.max():.0f}")
        print(f"      - CIS avec 1 seul CIP : {(cis_counts == 1).sum():,} ({(cis_counts == 1).sum()/nb_cis*100:.1f}%)")
        print(f"      - CIS avec >5 CIP : {(cis_counts > 5).sum():,} ({(cis_counts > 5).sum()/nb_cis*100:.1f}%)")
    
    elif nom_fichier == 'CIS_COMPO_bdpm':
        # Relation CIS → DCI (substances actives)
        nb_cis = df['CIS'].nunique()
        nb_substances = df['NOM_SUBSTANCE'].nunique()
        
        print(f"   • CIS distincts : {nb_cis:,}")
        print(f"   • Substances uniques : {nb_substances:,}")
        
        # Médicaments mono-substance vs multi-substances
        substances_par_cis = df.groupby('CIS')['NOM_SUBSTANCE'].nunique()
        print(f"\n   Composition :")
        print(f"      - Mono-substance : {(substances_par_cis == 1).sum():,} ({(substances_par_cis == 1).sum()/nb_cis*100:.1f}%)")
        print(f"      - Multi-substances : {(substances_par_cis > 1).sum():,} ({(substances_par_cis > 1).sum()/nb_cis*100:.1f}%)")
        print(f"      - Max substances par CIS : {substances_par_cis.max():.0f}")
    
    elif nom_fichier == 'CIS_CPD_bdpm':
        # Types de conditions
        nb_cis = df['CIS'].nunique()
        conditions_par_cis = df.groupby('CIS').size()
        
        print(f"   • CIS avec conditions : {nb_cis:,}")
        print(f"   • Conditions moyennes par CIS : {conditions_par_cis.mean():.2f}")
    
    elif nom_fichier == 'CIS_GENER_bdpm':
        # Groupes génériques
        nb_groupes = df['ID_GROUPE'].nunique()
        nb_cis = df['CIS'].nunique()
        
        print(f"   • Groupes génériques : {nb_groupes:,}")
        print(f"   • CIS concernés : {nb_cis:,}")
        
        # Distribution par type
        if 'TYPE_GENERIQUE' in df.columns:
            type_counts = df['TYPE_GENERIQUE'].value_counts()
            print(f"\n   Types :")
            for type_gen, count in type_counts.items():
                print(f"      - {type_gen}: {count:,}")
    
    # Stocker les résultats
    resultats[nom_fichier] = {
        'nb_lignes': nb_lignes,
        'nb_colonnes': nb_colonnes,
        'taille_mb': taille_memoire,
        'nb_doublons': nb_doublons,
        'missing_df': missing_df
    }

# ============================================================================
# 3. SYNTHÈSE GLOBALE
# ============================================================================

print("\n\n" + "="*80)
print("3. SYNTHÈSE GLOBALE")
print("="*80 + "\n")

print("📊 Récapitulatif des fichiers téléchargés :\n")

for fichier, description in FICHIERS.items():
    nom = fichier.replace('.txt', '')
    if nom in resultats:
        res = resultats[nom]
        print(f"✅ {fichier}")
        print(f"   • Description : {description}")
        print(f"   • Lignes : {res['nb_lignes']:,}")
        print(f"   • Colonnes : {res['nb_colonnes']}")
        print(f"   • Taille : {res['taille_mb']:.2f} MB")
        print(f"   • Doublons : {res['nb_doublons']:,}\n")

print("\n🎯 Fichiers manquants identifiés :")
print("   ❌ CIS_CIS-ATC_bdpm.txt (table de correspondance CIS→ATC)")
print("      → Non disponible en téléchargement direct sur la BDPM")
print("      → À rechercher sur data.gouv.fr ou via API\n")

print("="*80)
print("✅ Analyse descriptive terminée")
print("="*80)
