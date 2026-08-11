"""
Graphe d'interopérabilité des codes pharmaceutiques français
===================================================================
Trois vues interactives sur le même graphe, sélectionnables via des
boutons dans la figure HTML générée :

  - Vue A : graphe synthétique des types de codes (étoile centrée sur CIS)
  - Vue B : hiérarchie ATC dépliée (vue analytique, niveaux 1 à 5)
  - Vue C : vue combinée — étoile synthétique + hiérarchie ATC affichées
            simultanément, côte à côte, avec légende de couverture commune

Usage :
    python graph_codes_medicaments_v3.py
    python graph_codes_medicaments_v3.py --json
    python graph_codes_medicaments_v3.py --layout spring

Dépendances :
    pip install networkx plotly
    # ou avec uv : uv add networkx plotly

Sources : BDPM (ANSM), Open Medic (CNAM), SNDS — Bezin et al. (2017)
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# 1. DONNÉES — modifier ici pour mettre à jour le graphe
# ==============================================================================

NODES: list[dict] = [
    # ── Identifiant spécialité (pivot) ────────────────────────────────────────
    {
        "id": "CIS",
        "label": "CIS",
        "description": "Code Identifiant de Spécialité",
        "source": "BDPM · ANSM",
        "group": "identifiant",
        "coverage_self": 1.0,
        "count": 15848,
        "notes": "Clé primaire de la BDPM. Pivot central du graphe. 1 CIS = 1 spécialité pharmaceutique.",
    },
    # ── Identifiants présentation (boîte) ────────────────────────────────────
    {
        "id": "CIP7",
        "label": "CIP7",
        "description": "Code Identifiant de Présentation (7 chiffres)",
        "source": "BDPM · ANSM",
        "group": "presentation",
        "coverage_self": 0.477,
        "count": None,
        "notes": "Ancien format court. Dérivé du CIP13 par suppression du préfixe 34009 et du chiffre de contrôle.",
    },
    {
        "id": "CIP13",
        "label": "CIP13",
        "description": "Code Identifiant de Présentation (13 chiffres)",
        "source": "BDPM · ANSM / Open Medic · CNAM",
        "group": "presentation",
        "coverage_self": 0.477,
        "count": None,
        "notes": "Format actuel (GS1). Code-barres boîte. Recouvrement OpenMedic → BDPM mesuré à 95,7 %.",
    },
    # ── Identifiants hospitaliers (UCD) ──────────────────────────────────────
    {
        "id": "UCD7",
        "label": "UCD7",
        "description": "Unité Commune de Dispensation (7 chiffres)",
        "source": "BDPM · ANSM (référentiel hospitalier)",
        "group": "presentation",
        "coverage_self": None,
        "count": None,
        "notes": "Identifie l'unité de dispensation hospitalière, hors périmètre OpenMedic (ville).",
    },
    {
        "id": "UCD13",
        "label": "UCD13",
        "description": "Unité Commune de Dispensation (13 chiffres)",
        "source": "BDPM · ANSM (référentiel hospitalier)",
        "group": "presentation",
        "coverage_self": None,
        "count": None,
        "notes": "Format long du code UCD, analogue au CIP13 pour le circuit hospitalier.",
    },
    # ── Classification substance ──────────────────────────────────────────────
    {
        "id": "DCI",
        "label": "DCI",
        "description": "Dénomination Commune Internationale",
        "source": "BDPM · ANSM",
        "group": "classification",
        "coverage_self": 0.9999,
        "count": None,
        "notes": "Nom de la substance active. Couverture CIS → DCI quasi totale (99,99 %). 40,6 % des CIS sont multi-substances.",
    },
    # ── Hiérarchie ATC (5 niveaux) ────────────────────────────────────────────
    {
        "id": "ATC1",
        "label": "ATC niv. 1",
        "description": "Groupe anatomique principal",
        "source": "OMS / Open Medic · CNAM",
        "group": "atc",
        "coverage_self": None,
        "count": 14,
        "notes": "Niveau le plus agrégé de la classification ATC (ex. A — voies digestives et métabolisme).",
    },
    {
        "id": "ATC2",
        "label": "ATC niv. 2",
        "description": "Sous-groupe thérapeutique",
        "source": "OMS / Open Medic · CNAM",
        "group": "atc",
        "coverage_self": None,
        "count": None,
        "notes": "Regroupement par grande indication thérapeutique.",
    },
    {
        "id": "ATC3",
        "label": "ATC niv. 3",
        "description": "Sous-groupe pharmacologique",
        "source": "OMS / Open Medic · CNAM",
        "group": "atc",
        "coverage_self": None,
        "count": None,
        "notes": "Regroupement par mécanisme d'action pharmacologique.",
    },
    {
        "id": "ATC4",
        "label": "ATC niv. 4",
        "description": "Sous-groupe chimique",
        "source": "OMS / Open Medic · CNAM",
        "group": "atc",
        "coverage_self": None,
        "count": None,
        "notes": "Regroupement par famille chimique.",
    },
    {
        "id": "ATC5",
        "label": "ATC niv. 5",
        "description": "Substance chimique",
        "source": "OMS / Open Medic · CNAM",
        "group": "atc",
        "coverage_self": None,
        "count": None,
        "notes": "Niveau le plus fin de la classification ATC, proche de la DCI mais non strictement équivalent.",
    },
]

# Relations (arêtes) : (source, cible, qualité, label)
# qualité ∈ {"confirme", "estime", "indirect", "gap"}
EDGES: list[dict] = [
    {"source": "CIS", "target": "CIP7", "quality": "confirme",
     "label": "1 → n (47,7 % couverts)"},
    {"source": "CIS", "target": "CIP13", "quality": "confirme",
     "label": "1 → n (47,7 % couverts)"},
    {"source": "CIP7", "target": "CIP13", "quality": "confirme",
     "label": "dérivation directe"},
    {"source": "CIS", "target": "UCD7", "quality": "estime",
     "label": "périmètre hospitalier"},
    {"source": "UCD7", "target": "UCD13", "quality": "confirme",
     "label": "dérivation directe"},
    {"source": "CIS", "target": "DCI", "quality": "confirme",
     "label": "99,99 % couverts"},
    {"source": "DCI", "target": "ATC5", "quality": "estime",
     "label": "correspondance substance"},
    {"source": "ATC5", "target": "ATC4", "quality": "confirme",
     "label": "hiérarchie ATC"},
    {"source": "ATC4", "target": "ATC3", "quality": "confirme",
     "label": "hiérarchie ATC"},
    {"source": "ATC3", "target": "ATC2", "quality": "confirme",
     "label": "hiérarchie ATC"},
    {"source": "ATC2", "target": "ATC1", "quality": "confirme",
     "label": "hiérarchie ATC"},
    {"source": "CIP13", "target": "ATC5", "quality": "indirect",
     "label": "via Open Medic (95,7 %)"},
]

QUALITY_STYLE = {
    "confirme": {"color": "#2E7D32", "dash": "solid", "width": 2.5,
                 "legend": "Confirmé (mesuré empiriquement)"},
    "estime":   {"color": "#F9A825", "dash": "dash", "width": 2,
                 "legend": "Estimé (déduction logique du modèle de données)"},
    "indirect": {"color": "#1565C0", "dash": "dot", "width": 2,
                 "legend": "Indirect (chaînage via un tiers référentiel)"},
    "gap":      {"color": "#C62828", "dash": "dashdot", "width": 1.5,
                 "legend": "Lacune documentée (non chaînable en open data)"},
}

GROUP_COLOR = {
    "identifiant": "#1F4E79",
    "presentation": "#4A90B8",
    "classification": "#7CB342",
    "atc": "#8E44AD",
}

# ==============================================================================
# 2. CONSTRUCTION DU GRAPHE
# ==============================================================================

def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    for n in NODES:
        G.add_node(n["id"], **n)
    for e in EDGES:
        G.add_edge(e["source"], e["target"], quality=e["quality"], label=e["label"])
    return G


# ==============================================================================
# 3. LAYOUTS
# ==============================================================================

def layout_star(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Vue A : étoile synthétique centrée sur CIS, anneaux par groupe."""
    pos = {"CIS": (0.0, 0.0)}
    ring_groups = [
        (["CIP7", "CIP13"], 1.0, -40, 40),
        (["UCD7", "UCD13"], 1.0, 140, 220),
        (["DCI"], 1.0, 90, 90),
        (["ATC5", "ATC4", "ATC3", "ATC2", "ATC1"], 2.0, 250, 350),
    ]
    for ids, radius, angle_start, angle_end in ring_groups:
        n = len(ids)
        for i, node_id in enumerate(ids):
            angle = math.radians(
                angle_start if n == 1 else angle_start + (angle_end - angle_start) * i / (n - 1)
            )
            pos[node_id] = (radius * math.cos(angle), radius * math.sin(angle))
    return pos


def layout_atc_hierarchy(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Vue B : hiérarchie ATC dépliée verticalement, branche identifiants à gauche."""
    pos = {}
    # Colonne hiérarchie ATC (droite, du général en haut au spécifique en bas)
    atc_order = ["ATC1", "ATC2", "ATC3", "ATC4", "ATC5"]
    for i, node_id in enumerate(atc_order):
        pos[node_id] = (2.0, -i * 1.0)

    # Colonne identifiants (gauche)
    pos["CIS"] = (-1.5, -1.5)
    pos["DCI"] = (0.3, -2.0)
    pos["CIP7"] = (-2.5, -0.5)
    pos["CIP13"] = (-2.5, -2.5)
    pos["UCD7"] = (-1.5, 0.5)
    pos["UCD13"] = (-1.5, -4.5)
    return pos


def layout_combined(G: nx.DiGraph, offset_x: float = 5.0) -> tuple[dict, dict]:
    """Vue C : positions des deux layouts, décalées côte à côte sur un même canevas."""
    pos_a = layout_star(G)
    pos_b = layout_atc_hierarchy(G)
    pos_b_shifted = {k: (x + offset_x, y) for k, (x, y) in pos_b.items()}
    return pos_a, pos_b_shifted


# ==============================================================================
# 4. CONSTRUCTION DES TRACES PLOTLY
# ==============================================================================

def make_edge_traces(G: nx.DiGraph, pos: dict, suffix: str = "") -> list[go.Scatter]:
    traces = []
    seen_quality = set()
    for u, v, data in G.edges(data=True):
        if u not in pos or v not in pos:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        style = QUALITY_STYLE[data["quality"]]
        show_legend = data["quality"] not in seen_quality
        seen_quality.add(data["quality"])
        traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(color=style["color"], width=style["width"], dash=style["dash"]),
            hoverinfo="text",
            text=f"{u} → {v}<br>{data['label']}",
            name=style["legend"],
            legendgroup=data["quality"] + suffix,
            showlegend=show_legend,
            opacity=0.85,
        ))
    return traces


def make_node_trace(G: nx.DiGraph, pos: dict) -> go.Scatter:
    xs, ys, texts, hover, colors, sizes = [], [], [], [], [], []
    for node_id, data in G.nodes(data=True):
        if node_id not in pos:
            continue
        x, y = pos[node_id]
        xs.append(x)
        ys.append(y)
        texts.append(data["label"])
        cov = f"{data['coverage_self']*100:.1f} %" if data.get("coverage_self") is not None else "n/d"
        cnt = f"{data['count']:,}".replace(",", " ") if data.get("count") is not None else "n/d"
        hover.append(
            f"<b>{data['label']}</b> ({node_id})<br>"
            f"{data['description']}<br>"
            f"Source : {data['source']}<br>"
            f"Couverture propre : {cov}<br>"
            f"Effectif connu : {cnt}<br>"
            f"<i>{data['notes']}</i>"
        )
        colors.append(GROUP_COLOR[data["group"]])
        sizes.append(46 if node_id == "CIS" else 34)

    return go.Scatter(
        x=xs, y=ys, mode="markers+text",
        text=texts, textposition="middle center",
        textfont=dict(size=11, color="white", family="Arial Black"),
        marker=dict(size=sizes, color=colors, line=dict(width=2, color="white")),
        hovertext=hover, hoverinfo="text",
        showlegend=False,
        name="noeuds",
    )


# ==============================================================================
# 5. FIGURE COMPLÈTE AVEC BOUTONS DE BASCULE (VUE A / B / C)
# ==============================================================================

def build_figure(G: nx.DiGraph) -> go.Figure:
    pos_a = layout_star(G)
    pos_b = layout_atc_hierarchy(G)
    pos_a_c, pos_b_c = layout_combined(G)

    traces_a = make_edge_traces(G, pos_a, suffix="_a") + [make_node_trace(G, pos_a)]
    traces_b = make_edge_traces(G, pos_b, suffix="_b") + [make_node_trace(G, pos_b)]

    # Vue C = union des deux jeux de positions sur un même graphe (deux sous-graphes visuels)
    pos_c = {**pos_a_c, **pos_b_c}
    # On ne peut pas avoir deux fois le même node_id en vue C -> on construit un graphe miroir
    G_c_left = G.copy()
    G_c_right = nx.relabel_nodes(G, {n: f"{n}__b" for n in G.nodes()})
    G_c_right_edges = nx.DiGraph()
    for u, v, d in G.edges(data=True):
        G_c_right_edges.add_edge(f"{u}__b", f"{v}__b", **d)
    for n, d in G.nodes(data=True):
        G_c_right_edges.add_node(f"{n}__b", **d)
    pos_c_right = {f"{n}__b": pos_b_c[n] for n in G.nodes()}

    traces_c = (
        make_edge_traces(G_c_left, pos_a_c, suffix="_c_a")
        + make_edge_traces(G_c_right_edges, pos_c_right, suffix="_c_b")
        + [make_node_trace(G_c_left, pos_a_c), make_node_trace(G_c_right_edges, pos_c_right)]
    )

    n_a, n_b, n_c = len(traces_a), len(traces_b), len(traces_c)
    all_traces = traces_a + traces_b + traces_c
    vis_a = [True] * n_a + [False] * n_b + [False] * n_c
    vis_b = [False] * n_a + [True] * n_b + [False] * n_c
    vis_c = [False] * n_a + [False] * n_b + [True] * n_c

    fig = go.Figure(data=all_traces)

    fig.update_layout(
        title=dict(
            text="Interopérabilité des codes pharmaceutiques français — vue synthétique",
            x=0.5, font=dict(size=18, color="#1F4E79"),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=90, b=80),
        height=750,
        updatemenus=[dict(
            type="buttons",
            direction="left",
            x=0.5, y=1.12, xanchor="center", yanchor="top",
            buttons=[
                dict(label="Vue A — Étoile synthétique", method="update",
                     args=[{"visible": vis_a},
                           {"title": "Vue A — Graphe synthétique des types de codes (étoile centrée CIS)"}]),
                dict(label="Vue B — Hiérarchie ATC", method="update",
                     args=[{"visible": vis_b},
                           {"title": "Vue B — Hiérarchie ATC dépliée (niveaux 1 à 5)"}]),
                dict(label="Vue C — Combinée", method="update",
                     args=[{"visible": vis_c},
                           {"title": "Vue C — Vue combinée : étoile synthétique + hiérarchie ATC"}]),
            ],
        )],
        annotations=[dict(
            text="Survolez un nœud ou une arête pour le détail. Boutons en haut pour changer de vue.",
            xref="paper", yref="paper", x=0.5, y=-0.28, showarrow=False,
            font=dict(size=11, color="#666666"),
        )],
    )
    return fig


# ==============================================================================
# 6. EXPORT JSON (reproductibilité des données du graphe)
# ==============================================================================

def export_json(path: Path) -> None:
    payload = {
        "generated_by": "graph_codes_medicaments_v3.py",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "python_version": sys.version,
        "nodes": NODES,
        "edges": EDGES,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   ✅ Données exportées : {path}")


# ==============================================================================
# 7. MAIN
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Génère le graphe d'interopérabilité des codes pharmaceutiques.")
    parser.add_argument("--json", action="store_true", help="Exporter aussi les données en JSON.")
    parser.add_argument("--output", default="graph_codes_medicaments_v3.html", help="Nom du fichier HTML de sortie.")
    args = parser.parse_args()

    print("=" * 80)
    print("GÉNÉRATION DU GRAPHE D'INTEROPÉRABILITÉ — v3 (Vues A / B / C)")
    print("=" * 80)
    print(f"Python : {sys.version.split()[0]}")
    print(f"Date   : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    G = build_graph()
    print(f"Graphe construit : {G.number_of_nodes()} nœuds, {G.number_of_edges()} arêtes\n")

    fig = build_figure(G)
    out_path = Path(args.output)
    fig.write_html(out_path, include_plotlyjs="cdn")
    print(f"✅ Graphe HTML interactif généré : {out_path.resolve()}")

    if args.json:
        export_json(Path("graph_codes_medicaments_v3.json"))

    print("\n" + "=" * 80)
    print("✅ Terminé — ouvrir le fichier HTML dans un navigateur")
    print("=" * 80)


if __name__ == "__main__":
    main()
