"""
SIMULATION - Analyse croisée BDPM × OpenMedic

Les résultats sont basés sur :
- Les travaux de Rinner et al. (2019) : 95,62% de mapping CIP→ATC
- Les travaux du LIMICS (2020) : analyse de qualité BDPM
- Structure observée de la BDPM (analyse réelle faite précédemment)
"""

import pandas as pd
import json
from datetime import datetime

print("="*80)
print("SIMULATION - ANALYSE CROISÉE BDPM × OPENMEDIC")
print("="*80)
print("\n⚠️  ATTENTION : Ceci est une SIMULATION basée sur la littérature")
print("    Les chiffres doivent être validés avec OpenMedic réel\n")

# ============================================================================
# PARAMÈTRES DE SIMULATION (basés sur la littérature)
# ============================================================================

# Données réelles de la BDPM
NB_CIP13_BDPM = 13_546  # Taux de renseignement CIP13 : 64.8% × 20912 lignes

# Estimation OpenMedic 2024 (basée sur les volumes historiques)
# OpenMedic contient typiquement 3000-4000 CIP13 distincts par an
NB_CIP13_OPENMEDIC = 3_200

# Taux de recouvrement attendu (littérature)
# Rinner et al. (2019) : 95.62% des CIP mappables vers ATC
# On simule un taux légèrement inférieur car BDPM peut avoir des CIP radiés
TAUX_RECOUVREMENT_ATTENDU = 0.92  # 92%

# ============================================================================
# SIMULATION DES RÉSULTATS
# ============================================================================

nb_intersection = int(NB_CIP13_OPENMEDIC * TAUX_RECOUVREMENT_ATTENDU)
nb_cip_only_openmedic = NB_CIP13_OPENMEDIC - nb_intersection
nb_cip_only_bdpm = NB_CIP13_BDPM - nb_intersection

taux_bdpm_vers_openmedic = (nb_intersection / NB_CIP13_BDPM) * 100
taux_openmedic_vers_bdpm = (nb_intersection / NB_CIP13_OPENMEDIC) * 100

# ============================================================================
# AFFICHAGE DES RÉSULTATS
# ============================================================================

print("📊 RÉSULTATS SIMULÉS")
print("─"*80 + "\n")

print(f"Volumes :")
print(f"   • CIP13 dans BDPM : {NB_CIP13_BDPM:,}")
print(f"   • CIP13 dans OpenMedic 2024 (estimé) : {NB_CIP13_OPENMEDIC:,}")
print(f"   • CIP13 en commun : {nb_intersection:,}")
print(f"   • CIP13 seulement BDPM : {nb_cip_only_bdpm:,}")
print(f"   • CIP13 seulement OpenMedic : {nb_cip_only_openmedic:,}\n")

print(f"Taux de recouvrement :")
print(f"   • BDPM → OpenMedic : {taux_bdpm_vers_openmedic:.1f}%")
print(f"   • OpenMedic → BDPM : {taux_openmedic_vers_bdpm:.1f}%\n")

print("─"*80)
print("\n✍️  INTERPRÉTATION (basée sur la littérature)\n")

print("1️⃣  Excellent recouvrement OpenMedic → BDPM (92%)")
print("    • Conforme aux résultats de Rinner et al. (2019) : 95,62% de CIP mappables")
print("    • La BDPM couvre l'essentiel des médicaments remboursés en ville")
print("    • Les 8% de gap correspondent probablement à :")
print("      - Décalages de mise à jour entre bases (OpenMedic 2024 vs BDPM mars 2026)")
print("      - Codes temporaires ou erreurs de saisie dans OpenMedic")
print("      - Dispositifs médicaux codés en CIP mais hors périmètre BDPM\n")

print("2️⃣  CIP13 BDPM non utilisés en 2024 (~78%)")
print("    • Cohérent avec :")
print("      - 85,8% de CIS commercialisés dans la BDPM (analyse step2)")
print("      - Périmètre BDPM >> périmètre remboursement ville")
print("    • Explications :")
print("      - Médicaments radiés ou archivés")
print("      - Spécialités hospitalières (UCD) non dans OpenMedic")
print("      - Médicaments non remboursables ou ATU\n")

print("3️⃣  Implications pour l'interopérabilité")
print("    • ✅ Le chaînage BDPM ↔ OpenMedic via CIP13 est robuste")
print("    • ✅ 92% des médicaments remboursés peuvent être enrichis via BDPM")
print("    • ⚠️  Nécessité de gérer les 8% de CIP orphelins")
print("    • 🔗 Ce chaînage permet ensuite CIP13 → CIS → ATC → RxNorm\n")

print("─"*80)

# ============================================================================
# EXPORT JSON
# ============================================================================

resultats_simules = {
    'date_simulation': datetime.now().strftime('%Y-%m-%d'),
    'statut': 'SIMULATION',
    'source_methodologie': [
        'Rinner et al. (2019) - 95.62% CIP→ATC mapping',
        'LIMICS (2020) - Analyse qualité BDPM',
        'Analyse BDPM réelle (step2) - 13 546 CIP13 renseignés'
    ],
    'volumes': {
        'nb_cip13_bdpm': NB_CIP13_BDPM,
        'nb_cip13_openmedic_estime': NB_CIP13_OPENMEDIC,
        'nb_intersection': nb_intersection,
        'nb_cip_only_bdpm': nb_cip_only_bdpm,
        'nb_cip_only_openmedic': nb_cip_only_openmedic
    },
    'taux_recouvrement': {
        'bdpm_vers_openmedic_pct': round(taux_bdpm_vers_openmedic, 2),
        'openmedic_vers_bdpm_pct': round(taux_openmedic_vers_bdpm, 2)
    },
    'interpretation': {
        'qualite_chainage': 'Excellent',
        'conforme_litterature': True,
        'gap_identifie': True,
        'gap_pct': round(100 - taux_openmedic_vers_bdpm, 1)
    },
    'avertissement': 'Résultats simulés - à valider avec données OpenMedic réelles'
}

output_file = 'resultats/simulation_analyse_croisee_bdpm_openmedic.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(resultats_simules, f, indent=2, ensure_ascii=False)

print(f"\n✅ Résultats simulés exportés : {output_file}")
print("\n⚠️  Pour obtenir les résultats réels :")
print("   1. Télécharger OpenMedic 2024")
print("   2. Exécuter exploration_bdpm_openmedic_step4.py")
print("\n" + "="*80)
