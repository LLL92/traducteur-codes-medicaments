import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    """Piste de recherche « intelligente » — exploratoire, non intégrée à l'outil.

    Prototype d'une couche d'assistance à la recherche : une requête en langage
    naturel (classe thérapeutique, symptôme, maladie) est traduite en termes de
    recherche, ensuite vérifiés dans la BDPM. Deux voies :
      - classe / symptôme : un LLM local (Ollama) propose des substances ;
      - maladie : la relation may_treat de MED-RT via l'API RxClass (NIH)
        fournit des substances sourcées.

    L'assistance ne produit jamais de code ni de nom de médicament : elle ne
    génère que des termes à chercher, la BDPM restant l'unique source de vérité.

    Cette piste a été écartée de l'outil final pour deux raisons : elle dépend
    de services externes (contraire à un fonctionnement hors-ligne), et la
    traduction entre codifications est une correspondance exacte qui n'appelle
    aucun modèle probabiliste. Le code est conservé à titre documentaire.

    Non exécutable seul : référence des fonctions définies dans l'outil principal.
    """
    import json
    import urllib.request
    import urllib.error
    import urllib.parse
    import marimo as mo
    import pandas as pd
    return json, mo, pd, urllib


@app.cell
def _(json, urllib):
    # =========================================================================
    #  COUCHE IA — l'IA traduit l'intention ; la BDPM reste la source de vérité
    # =========================================================================
    MODELE_OLLAMA = "mistral"          # ← change ici pour un modèle plus léger
    OLLAMA_URL = "http://localhost:11434/api/chat"
    RXCLASS = "https://rxnav.nlm.nih.gov/REST/rxclass"

    def post_json(url, payload, timeout=120):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def get_json(url, timeout=30):
        req = urllib.request.Request(url, headers={"User-Agent": "memoire-mias/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    return MODELE_OLLAMA, OLLAMA_URL, RXCLASS, get_json, post_json



@app.cell
def _(MODELE_OLLAMA, OLLAMA_URL, post_json, json, urllib):
    # --- Voie commune : le LLM comprend l'intention et route (classe vs maladie) ---
    _SYSTEME = (
        "Tu aides à retrouver des médicaments dans la base française BDPM. "
        "Tu ne donnes JAMAIS de médicament précis, ni de code, ni de conseil médical. "
        "Tu analyses la demande et réponds UNIQUEMENT par un objet JSON valide :\n"
        '{"type":"classe|maladie|nom|inconnu",'
        '"termes_fr":["..."],'
        '"terme_en":"...",'
        '"interpretation":"une phrase"}\n'
        "Règles :\n"
        "- classe/symptôme (antalgique, pour la fièvre) : mets dans termes_fr les DCI "
        "françaises courantes (ex. paracétamol, ibuprofène). terme_en vide.\n"
        "- maladie (diabète, hypertension) : mets dans terme_en le nom anglais standard "
        "de la maladie (ex. diabetes mellitus, hypertension). termes_fr vide.\n"
        "- nom (doliprane) : mets-le tel quel dans termes_fr.\n"
        "- sinon : type inconnu.\n"
        "N'invente aucun code. interpretation résume ce que tu as compris, en français."
    )

    def interpreter_intention(question: str):
        """Retourne (plan_dict, erreur_str_ou_None)."""
        payload = {
            "model": MODELE_OLLAMA,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": _SYSTEME},
                {"role": "user", "content": question},
            ],
        }
        try:
            rep = post_json(OLLAMA_URL, payload)
        except urllib.error.URLError:
            return None, "ollama_absent"
        except Exception as e:  # noqa: BLE001
            return None, f"erreur Ollama : {e}"
        try:
            return json.loads(rep["message"]["content"]), None
        except Exception:  # noqa: BLE001
            return None, "réponse du modèle illisible"

    return (interpreter_intention,)



@app.cell
def _(RXCLASS, get_json, urllib):
    # --- Voie B : maladie -> substances SOURCÉES via RxClass (may_treat, MED-RT) ---
    def maladie_vers_substances(terme_en: str, maxi: int = 25):
        """
        Retourne (nom_classe, [substances_en], erreur_ou_None).
        Source : relation may_treat de MED-RT, exposée par l'API RxClass (NIH).
        """
        q = urllib.parse.quote(terme_en)
        # 1) trouver la classe MALADIE correspondante
        try:
            d1 = get_json(
                f"{RXCLASS}/class/byName.json?className={q}&classTypes=DISEASE"
            )
        except urllib.error.URLError:
            return None, None, "reseau"
        except Exception as e:  # noqa: BLE001
            return None, None, f"erreur RxClass : {e}"
        classes = (d1.get("rxclassMinConceptList") or {}).get("rxclassMinConcept") or []
        if not classes:
            return None, [], "aucune_classe"
        classe = classes[0]
        class_id = classe.get("classId")
        class_nom = classe.get("className")
        # 2) récupérer les médicaments qui « may_treat » cette maladie
        try:
            d2 = get_json(
                f"{RXCLASS}/classMembers.json?classId={class_id}"
                "&relaSource=MEDRT&rela=may_treat"
            )
        except Exception as e:  # noqa: BLE001
            return class_nom, None, f"erreur RxClass : {e}"
        membres = (d2.get("drugMemberGroup") or {}).get("drugMember") or []
        noms = []
        for m in membres:
            nom = (m.get("minConcept") or {}).get("name")
            if nom and nom not in noms:
                noms.append(nom)
        return class_nom, noms[:maxi], None

    return (maladie_vers_substances,)



@app.cell
def _(mo):
    # --- Entrée de la recherche intelligente (form : n'appelle l'IA qu'à la soumission) ---
    requete_ia = mo.ui.text(
        placeholder="ex. antalgique · pour la fièvre · diabète · hypertension",
        full_width=True,
    ).form(submit_button_label="🤖 Rechercher avec l'IA")
    return (requete_ia,)



@app.cell
def _(
    hint,
    interpreter_intention,
    maladie_vers_substances,
    mo,
    pd,
    recherche_lexicale,
    requete_ia,
    traduire_cis,
):
    def _medicaments_pour_terme(terme: str, source: str) -> list[dict]:
        lignes = []
        for c in recherche_lexicale(terme, top_k=5):
            cis_list = c["CIS_multiples"] if c["type"] == "DCI" else [c["CIS"]]
            for cis in cis_list[:8]:
                det = traduire_cis(cis)
                cip13 = next(
                    (p["CIP13"] for p in det["presentations"] if p.get("CIP13")), ""
                )
                lignes.append({
                    "Recherché": source,
                    "Médicament (BDPM)": det["denomination"],
                    "CIS": cis,
                    "CIP13": cip13,
                })
        return lignes

    def _executer(question: str):
        plan, err = interpreter_intention(question)
        if err == "ollama_absent":
            return mo.callout(mo.md(
                "**IA locale indisponible.** Vérifiez qu'Ollama tourne et que le "
                "modèle est installé :\n\n```\nollama pull mistral\n```\n"
                "L'IA est un complément : les autres onglets fonctionnent sans elle."
            ), kind="danger")
        if err or not plan:
            return mo.callout(f"Interprétation impossible ({err}).", kind="danger")

        typ = plan.get("type", "inconnu")
        blocs = [
            mo.callout(mo.md(
                "⚠️ **Aide exploratoire, pas un avis médical.** Les résultats "
                "proviennent de votre BDPM ; l'IA ne fait que traduire votre demande."
            ), kind="warn"),
            mo.md(f"🧠 **Compris comme :** {plan.get('interpretation', '—')}"),
        ]

        lignes = []
        if typ in ("classe", "nom"):
            termes = plan.get("termes_fr") or []
            blocs.append(mo.md("🔎 **Substances recherchées :** " + ", ".join(termes)))
            for t in termes:
                lignes += _medicaments_pour_terme(t, t)

        elif typ == "maladie":
            class_nom, noms, err2 = maladie_vers_substances(
                plan.get("terme_en") or question
            )
            if err2 == "reseau":
                blocs.append(mo.callout(
                    "Source RxClass injoignable — vérifiez votre connexion internet.",
                    kind="danger"))
                return mo.vstack(blocs)
            if err2 == "aucune_classe" or not noms:
                blocs.append(mo.callout(
                    f"Aucune correspondance trouvée dans MED-RT pour « "
                    f"{plan.get('terme_en')} ». Essayez une formulation plus simple.",
                    kind="warn"))
                return mo.vstack(blocs)
            blocs.append(mo.md(
                f"📚 **Source :** relation *may_treat* de MED-RT via RxClass (NIH) — "
                f"classe « {class_nom} ». Noms issus d'un référentiel anglophone ; "
                f"le rapprochement avec la BDPM française est approximatif."
            ))
            for nom in noms:
                lignes += _medicaments_pour_terme(nom, nom)

        else:
            blocs.append(mo.callout(
                "Je n'ai pas su rattacher cette demande à un médicament. Reformulez, "
                "ou utilisez la recherche classique (onglet 🔍).", kind="info"))
            return mo.vstack(blocs)

        if not lignes:
            blocs.append(mo.callout(
                "Aucun médicament correspondant retrouvé dans votre BDPM. "
                "(Les noms proposés par la source peuvent différer des dénominations "
                "françaises — c'est une limite connue du rapprochement.)", kind="warn"))
            return mo.vstack(blocs)

        df = pd.DataFrame(lignes).drop_duplicates(subset=["CIS"]).reset_index(drop=True)
        blocs.append(mo.callout(
            f"**{len(df)}** médicament(s) retrouvé(s) dans votre BDPM.", kind="success"))
        blocs.append(mo.ui.table(df, page_size=15))
        blocs.append(mo.download(
            data=df.to_csv(index=False).encode("utf-8"),
            filename="recherche_intelligente.csv",
            label="Télécharger les résultats (CSV)"))
        return mo.vstack(blocs)

    if not requete_ia.value:
        _resultat = mo.md(
            "*Décrivez ce que vous cherchez — une classe (`antalgique`), un symptôme "
            "(`pour la fièvre`) ou une maladie (`diabète`) — puis cliquez sur le "
            "bouton. La première réponse de l'IA peut prendre quelques secondes.*"
        )
    else:
        _resultat = _executer(requete_ia.value.strip())

    vue_ia = mo.vstack([
        hint(
            "<b>Décrivez votre besoin en langage naturel.</b> Une IA locale traduit "
            "votre demande en substances, puis l'outil les vérifie dans votre BDPM. "
            "Pour une <b>maladie</b>, les correspondances viennent d'une source "
            "médicale citée (RxClass / MED-RT). Ce n'est pas un avis médical."
        ),
        requete_ia,
        _resultat,
    ])
    return (vue_ia,)




if __name__ == "__main__":
    app.run()
