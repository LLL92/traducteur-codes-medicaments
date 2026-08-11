"""
Exploration de la BDPM - Étape 2 : Indicateurs de qualité et analyse des relations
"""

import pandas as pd
import numpy as np
import json

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

DATA_DIR = 'data/'

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
    }
}

# Chargement
cis_df = pd.read_csv(DATA_DIR + 'CIS_bdpm.txt', **SCHEMAS['CIS_bdpm.txt'], dtype=str)
cis_cip_df = pd.read_csv(DATA_DIR + 'CIS_CIP_bdpm.txt', **SCHEMAS['CIS_CIP_bdpm.txt'], dtype=str)
cis_compo_df = pd.read_csv(DATA_DIR + 'CIS_COMPO_bdpm.txt', **SCHEMAS['CIS_COMPO_bdpm.txt'], dtype=str)

print("="*80)
print("EXPLORATION DE LA BDPM - ÉTAPE 2 : INDICATEURS DE QUALITÉ")
print("="*80 + "\n")

# ============================================================================
# 1. ANALYSE DE COMPLÉTUDE DU RÉFÉRENTIEL PIVOT (CIS_bdpm)
# ============================================================================

print("1️⃣  ANALYSE DE COMPLÉTUDE DU RÉFÉRENTIEL PIVOT (CIS_bdpm)")
print("─"*80 + "\n")

nb_cis_total = len(cis_df)

# Indicateur 1 : Taux de renseignement par champ obligatoire
champs_obligatoires = ['CIS', 'NOM', 'FORME', 'STATUT_AMM', 'COMMERCIALISATION']
print("📋 Taux de renseignement des champs obligatoires :\n")

for champ in champs_obligatoires:
    nb_renseigne = cis_df[champ].notna().sum()
    taux = (nb_renseigne / nb_cis_total) * 100
    print(f"   • {champ:25s}: {nb_renseigne:>6,} / {nb_cis_total:>6,} ({taux:>5.1f}%)")

# Indicateur 2 : Distribution par statut (actif vs inactif)
print(f"\n📊 Distribution par statut AMM :\n")
statut_counts = cis_df['STATUT_AMM'].value_counts()
for statut, count in statut_counts.items():
    pct = (count / nb_cis_total) * 100
    print(f"   • {statut:30s}: {count:>6,} ({pct:>5.1f}%)")

# Indicateur 3 : CIS sans commercialisation
cis_actifs = cis_df[cis_df['STATUT_AMM'] == 'Autorisation active']
cis_actifs_non_comm = cis_actifs[cis_actifs['COMMERCIALISATION'] == 'Non commercialisée']

print(f"\n⚠️  CIS avec AMM active mais non commercialisés :")
print(f"   • Nombre : {len(cis_actifs_non_comm):,}")
print(f"   • Proportion : {len(cis_actifs_non_comm)/len(cis_actifs)*100:.1f}% des AMM actives")

# ============================================================================
# 2. ANALYSE DE LA RELATION CIS ↔ CIP (CARDINALITÉ)
# ============================================================================

print("\n\n2️⃣  ANALYSE DE LA RELATION CIS ↔ CIP (CARDINALITÉ)")
print("─"*80 + "\n")

# Nombre de CIS présents dans CIS_CIP
cis_dans_cip = cis_cip_df['CIS'].unique()
nb_cis_dans_cip = len(cis_dans_cip)

print(f"📈 Couverture CIS → CIP :")
print(f"   • CIS dans CIS_bdpm.txt : {nb_cis_total:,}")
print(f"   • CIS dans CIS_CIP_bdpm.txt : {nb_cis_dans_cip:,}")
print(f"   • Taux de couverture : {nb_cis_dans_cip/nb_cis_total*100:.1f}%")

# CIS sans aucun CIP
cis_sans_cip = set(cis_df['CIS']) - set(cis_dans_cip)
print(f"\n⚠️  CIS sans aucun code CIP :")
print(f"   • Nombre : {len(cis_sans_cip):,}")
print(f"   • Proportion : {len(cis_sans_cip)/nb_cis_total*100:.1f}%")

# Analyser ces CIS sans CIP
if len(cis_sans_cip) > 0:
    cis_sans_cip_df = cis_df[cis_df['CIS'].isin(cis_sans_cip)]
    print(f"\n   Caractéristiques des CIS sans CIP :")
    statut_sans_cip = cis_sans_cip_df['STATUT_AMM'].value_counts()
    for statut, count in statut_sans_cip.items():
        print(f"      - {statut}: {count:,} ({count/len(cis_sans_cip)*100:.1f}%)")

# Distribution de la cardinalité CIS → CIP
print(f"\n📊 Distribution de la cardinalité CIS → CIP :\n")

cip_par_cis = cis_cip_df.groupby('CIS').size()

print(f"   Statistiques :")
print(f"   • Moyenne : {cip_par_cis.mean():.2f} CIP par CIS")
print(f"   • Médiane : {cip_par_cis.median():.0f}")
print(f"   • Écart-type : {cip_par_cis.std():.2f}")
print(f"   • Min : {cip_par_cis.min():.0f}")
print(f"   • Max : {cip_par_cis.max():.0f}")

# Distribution par buckets
buckets = [
    (1, 1, "Exactement 1 CIP"),
    (2, 5, "2 à 5 CIP"),
    (6, 10, "6 à 10 CIP"),
    (11, 20, "11 à 20 CIP"),
    (21, 999, ">20 CIP")
]

print(f"\n   Distribution par nombre de CIP :")
for min_val, max_val, label in buckets:
    count = ((cip_par_cis >= min_val) & (cip_par_cis <= max_val)).sum()
    pct = count / len(cip_par_cis) * 100
    print(f"      - {label:20s}: {count:>5,} CIS ({pct:>5.1f}%)")

# Cas extrêmes : CIS avec le plus de CIP
print(f"\n   🔝 Top 5 des CIS avec le plus de CIP :")
top_cis = cip_par_cis.nlargest(5)
for cis, nb_cip in top_cis.items():
    cis_info = cis_df[cis_df['CIS'] == cis]
    if len(cis_info) > 0:
        nom = cis_info['NOM'].iloc[0]
        print(f"      - CIS {cis}: {nb_cip:>3} CIP — {nom[:60]}")
    else:
        print(f"      - CIS {cis}: {nb_cip:>3} CIP — (CIS non trouvé dans CIS_bdpm)")

# ============================================================================
# 3. ANALYSE DE LA RELATION CIS → DCI (COMPOSITION)
# ============================================================================

print("\n\n3️⃣  ANALYSE DE LA RELATION CIS → DCI (COMPOSITION)")
print("─"*80 + "\n")

# Nombre de CIS présents dans CIS_COMPO
cis_dans_compo = cis_compo_df['CIS'].unique()
nb_cis_dans_compo = len(cis_dans_compo)

print(f"📈 Couverture CIS → DCI :")
print(f"   • CIS dans CIS_bdpm.txt : {nb_cis_total:,}")
print(f"   • CIS dans CIS_COMPO_bdpm.txt : {nb_cis_dans_compo:,}")
print(f"   • Taux de couverture : {nb_cis_dans_compo/nb_cis_total*100:.1f}%")

# CIS sans composition
cis_sans_compo = set(cis_df['CIS']) - set(cis_dans_compo)
print(f"\n⚠️  CIS sans composition documentée :")
print(f"   • Nombre : {len(cis_sans_compo):,}")
print(f"   • Proportion : {len(cis_sans_compo)/nb_cis_total*100:.1f}%")

# Distribution mono-substance vs multi-substances
substances_par_cis = cis_compo_df.groupby('CIS')['NOM_SUBSTANCE'].nunique()

print(f"\n📊 Distribution mono-substance vs multi-substances :\n")
mono = (substances_par_cis == 1).sum()
multi = (substances_par_cis > 1).sum()
print(f"   • Mono-substance : {mono:,} CIS ({mono/len(substances_par_cis)*100:.1f}%)")
print(f"   • Multi-substances : {multi:,} CIS ({multi/len(substances_par_cis)*100:.1f}%)")

# Distribution détaillée
print(f"\n   Distribution par nombre de substances :")
for i in range(1, 11):
    count = (substances_par_cis == i).sum()
    if count > 0:
        pct = count / len(substances_par_cis) * 100
        print(f"      - {i:2d} substance(s) : {count:>5,} CIS ({pct:>5.1f}%)")

max_substances = substances_par_cis.max()
count_max = (substances_par_cis > 10).sum()
if count_max > 0:
    pct_max = count_max / len(substances_par_cis) * 100
    print(f"      - >10 substances   : {count_max:>5,} CIS ({pct_max:>5.1f}%)")

# Cas extrêmes
print(f"\n   🔝 Top 5 des CIS avec le plus de substances :")
top_compo = substances_par_cis.nlargest(5)
for cis, nb_subst in top_compo.items():
    cis_info = cis_df[cis_df['CIS'] == cis]
    if len(cis_info) > 0:
        nom = cis_info['NOM'].iloc[0]
        print(f"      - CIS {cis}: {nb_subst:>2} substances — {nom[:50]}")
    else:
        print(f"      - CIS {cis}: {nb_subst:>2} substances — (CIS non trouvé)")

# ============================================================================
# 4. ANALYSE CROISÉE : CIS SANS CIP ET SANS COMPOSITION
# ============================================================================

print("\n\n4️⃣  ANALYSE CROISÉE : LACUNES CUMULÉES")
print("─"*80 + "\n")

# CIS sans CIP ET sans composition
cis_sans_cip_ni_compo = cis_sans_cip.intersection(cis_sans_compo)

print(f"⚠️  CIS sans CIP NI composition :")
print(f"   • Nombre : {len(cis_sans_cip_ni_compo):,}")
print(f"   • Proportion : {len(cis_sans_cip_ni_compo)/nb_cis_total*100:.1f}% du total")

if len(cis_sans_cip_ni_compo) > 0:
    cis_problematiques = cis_df[cis_df['CIS'].isin(cis_sans_cip_ni_compo)]
    print(f"\n   Caractéristiques :")
    statut_pb = cis_problematiques['STATUT_AMM'].value_counts()
    for statut, count in statut_pb.items():
        print(f"      - {statut}: {count:,} ({count/len(cis_problematiques)*100:.1f}%)")

# ============================================================================
# 5. QUALITÉ DES CODES CIP13 vs CIP7
# ============================================================================

print("\n\n5️⃣  QUALITÉ DES CODES CIP13 vs CIP7")
print("─"*80 + "\n")

# Complétude CIP13 vs CIP7
nb_cip_total = len(cis_cip_df)
nb_cip13_renseigne = cis_cip_df['CIP13'].notna().sum()
nb_cip7_renseigne = cis_cip_df['CIP7'].notna().sum()

print(f"📊 Taux de renseignement :")
print(f"   • CIP7 : {nb_cip7_renseigne:,} / {nb_cip_total:,} ({nb_cip7_renseigne/nb_cip_total*100:.1f}%)")
print(f"   • CIP13 : {nb_cip13_renseigne:,} / {nb_cip_total:,} ({nb_cip13_renseigne/nb_cip_total*100:.1f}%)")

# Codes sans CIP13
lignes_sans_cip13 = cis_cip_df[cis_cip_df['CIP13'].isna()]
print(f"\n⚠️  Présentations sans CIP13 :")
print(f"   • Nombre : {len(lignes_sans_cip13):,}")
print(f"   • Proportion : {len(lignes_sans_cip13)/nb_cip_total*100:.1f}%")

# ============================================================================
# 6. EXPORT DES RÉSULTATS QUANTITATIFS
# ============================================================================

print("\n\n6️⃣  EXPORT DES INDICATEURS POUR LE MÉMOIRE")
print("─"*80 + "\n")

indicateurs = {
    'date_analyse': '2026-03-26',
    'referentiel_pivot': {
        'nb_cis_total': int(nb_cis_total),
        'nb_cis_actifs': int(len(cis_actifs)),
        'nb_cis_actifs_non_comm': int(len(cis_actifs_non_comm)),
        'taux_cis_actifs': round(len(cis_actifs)/nb_cis_total*100, 2)
    },
    'relation_cis_cip': {
        'nb_cis_avec_cip': int(nb_cis_dans_cip),
        'nb_cis_sans_cip': int(len(cis_sans_cip)),
        'taux_couverture': round(nb_cis_dans_cip/nb_cis_total*100, 2),
        'cardinalite_moyenne': round(cip_par_cis.mean(), 2),
        'cardinalite_mediane': int(cip_par_cis.median()),
        'cardinalite_max': int(cip_par_cis.max()),
        'nb_cis_1_cip': int((cip_par_cis == 1).sum()),
        'nb_cis_plus_5_cip': int((cip_par_cis > 5).sum())
    },
    'relation_cis_dci': {
        'nb_cis_avec_compo': int(nb_cis_dans_compo),
        'nb_cis_sans_compo': int(len(cis_sans_compo)),
        'taux_couverture': round(nb_cis_dans_compo/nb_cis_total*100, 2),
        'nb_mono_substance': int(mono),
        'nb_multi_substances': int(multi),
        'taux_multi_substances': round(multi/len(substances_par_cis)*100, 2),
        'nb_substances_max': int(max_substances)
    },
    'lacunes_croisees': {
        'nb_cis_sans_cip_ni_compo': int(len(cis_sans_cip_ni_compo)),
        'taux': round(len(cis_sans_cip_ni_compo)/nb_cis_total*100, 2)
    },
    'qualite_cip': {
        'taux_cip7': round(nb_cip7_renseigne/nb_cip_total*100, 2),
        'taux_cip13': round(nb_cip13_renseigne/nb_cip_total*100, 2),
        'nb_presentations_sans_cip13': int(len(lignes_sans_cip13))
    }
}

# Sauvegarder en JSON
with open('resultats/indicateurs_qualite_bdpm.json', 'w') as f:
    json.dump(indicateurs, f, indent=2, ensure_ascii=False)

print("✅ Indicateurs exportés dans : indicateurs_qualite_bdpm.json")

# Afficher un résumé
print(f"\n📊 RÉSUMÉ DES INDICATEURS CLÉS :\n")
print(f"   • CIS total : {indicateurs['referentiel_pivot']['nb_cis_total']:,}")
print(f"   • CIS sans CIP : {indicateurs['relation_cis_cip']['nb_cis_sans_cip']:,} ({100-indicateurs['relation_cis_cip']['taux_couverture']:.1f}%)")
print(f"   • CIS sans composition : {indicateurs['relation_cis_dci']['nb_cis_sans_compo']:,} ({100-indicateurs['relation_cis_dci']['taux_couverture']:.1f}%)")
print(f"   • Cardinalité moyenne CIS→CIP : {indicateurs['relation_cis_cip']['cardinalite_moyenne']}")
print(f"   • Taux multi-substances : {indicateurs['relation_cis_dci']['taux_multi_substances']:.1f}%")

print("\n" + "="*80)
print("✅ Analyse de qualité terminée")
print("="*80)
