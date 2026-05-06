# NEBCO Dispatch — Optimisation interne d'un opérateur d'effacement

Prototype MILP de dispatch interne pour un **Opérateur d'Effacement** (OE, aussi appelé agrégateur) opérant sous le cadre **NEBCO** (Notification d'Échanges de Blocs de Consommation, délibération CRE n°2025-199, en vigueur depuis le 01/09/2025).

## Contexte et vocabulaire NEBCO

Lorsqu'un OE reçoit de RTE un programme d'effacement retenu suite à ses offres sur le mécanisme NEBCO, il doit ventiler ce volume entre les clients de son portefeuille. Ce projet modélise ce **problème de dispatch interne** comme un programme linéaire mixte en nombres entiers (MILP).

La hiérarchie NEBCO des acteurs et périmètres est la suivante (art. 5.F) :

```
Opérateur d'Effacement (OE)              ← personne morale agréée par RTE
  └── Périmètre d'Effacement (PE)        ← un seul PE par OE, non transférable
        ├── EDE 1  (Télérelevée ou Profilée)
        │     ├── Site de Soutirage 1.1
        │     └── Site de Soutirage 1.2
        ├── EDE 2  (Télérelevée ou Profilée)
        │     └── ...
```

L'**Entité d'Effacement (EDE)** est le périmètre contractuel regroupant des sites d'une même typologie. **Le bilan énergétique NEBCO est contrôlé à la maille EDE**, pas au niveau PE ni au niveau site.

L'objectif du dispatch est de minimiser le coût interne de l'OE — compensation versée aux clients + coûts fixes d'activation — sous contraintes physiques (gisement disponible, seuils minimaux) et réglementaires (plafond OE, bilan énergétique NEBCO à la maille EDE).

## Positionnement dans la chaîne décisionnelle

```
Niveau 0  │ Caractérisation portefeuille (baseline, gisement)   ── hors scope
Niveau 1  │ Offre sur le marché NEBCO                           ── hors scope
Niveau 2  │ Dispatch interne post-notification RTE              ── CE PROJET
Niveau 3  │ Pilotage temps réel des équipements                 ── hors scope
```

**Boucle de rétroaction** : le réalisé mesuré au Niveau 3 alimente en retour le Niveau 0 (mise à jour des baselines, de la fiabilité des clients, du gisement effectif), qui conditionne les offres du Niveau 1 du jour suivant.
Un dispatch de mauvaise qualité dégrade l'indicateur de fiabilité de l'OE, ce qui resserre à son tour le plafond réglementaire (art. 5.E.1.3.2.2) — la boucle a donc un effet disciplinant direct sur l'horizon court.

## Formulation

**Variables**
- $x[c,t]$ ∈ ℝ₊ : puissance effacée par le client c au pas t [MW]
- $δ[c,t]$ ∈ {0,1} : activation du client c au pas t

**Objectif** : min Σ ( C_act[c]·x[c,t]·Δt + f[c,t]·δ[c,t] )

avec :
- $C_act[c]$ [€/MWh] — **coût variable de compensation** versé au client c proportionnellement à l'énergie effacée. Négocié bilatéralement, supposé stationnaire en v1.
- $f[c,t]$ [€] — **coût fixe d'activation** payé dès que δ[c,t]=1, indépendamment du volume effacé. Modélise les frais de télécommande, l'usure des équipements, et le "crédit de sollicitation" (risque de désengagement client en cas d'activations trop fréquentes). Différencié par (client, pas) pour permettre une modulation contextuelle.

**Contraintes**
- C1 — Livraison exacte de la consigne RTE par pas
- C2 — Plafond réglementaire OE (art. 5.E.1.3.2.2)
- C3 — Bilan énergétique NEBCO : Σ rebond ≤ Σ effacement (maille EDE)
- C4 — Couplage activation/effacement (big-M = borne naturelle)
- C5 — Seuil minimal d'effacement si activé

> Les justifications approfondies des choix de modélisation — choix MILP plutôt que LP, périmètre à une seule EDE sans distinction de profilage, absence du revenu NEBCO et du versement fournisseur dans l'objectif, Position A sur le rebond, bilan C3 sur horizon court vs période glissante, hypothèses exogènes sur baseline et gisement — seront développées dans une note technique.

## Structure du projet

```
nebco-dispatch/
├── src/
│   ├── data.py          # dataclasses Client, Consigne, Portfolio
│   ├── model.py         # build_model : construction du MILP
│   ├── solver.py        # solve + check_constraints
│   └── reporting.py     # affichage formaté
├── examples/
│   └── run_example.py   # scénario 4 clients × 6 pas demi-horaires
├── tests/
│   └── test_model.py    # tests unitaires et d'intégration
└── docs/
    └── note-technique.md   # justifications approfondies des choix de modélisation
```

## Installation et utilisation

```bash
git clone https://github.com/<user>/nebco-dispatch.git
cd nebco-dispatch
pip install -r requirements.txt

# Lancer l'exemple
python -m examples.run_example

# Lancer les tests
python -m unittest discover tests
```

Dépendances : $pulp$ (solveur CBC inclus).

Exemple d'utilisation programmatique :

```python
from src import Client, Consigne, Portfolio, build_model, solve, print_full_report

portfolio = Portfolio(clients=[...])
consigne = Consigne(e_retenu=[1.0, 1.2, 1.5], delta_t=0.5, P_max_agr=6.0)

prob, variables = build_model(portfolio, consigne)
solution = solve(prob, variables)
print_full_report(solution, portfolio, consigne)
```

## Limites de la v1

Ce prototype privilégie la lisibilité de la formulation sur la fidélité opérationnelle. Les principales limites, documentées en détail dans la note technique :

- **Un OE, un PE, une seule EDE**, sans distinction de typologie Télérelevée/Profilée.
- **C1 en égalité stricte** — la sous-livraison n'est pas autorisée, alors qu'elle est pénalisée financièrement par RTE, pas interdite.
- **Rebond hors horizon** — taux scalaire $r[c,t]$ qui capte l'ampleur mais pas le timing du rebond.
- **Contrainte C3 bilan énergétique sur l'horizon d'optimisation court** — plus restrictif que le bilan NEBCO réel contrôlé sur période glissante.
- **Pas de contraintes inter-temporelles** par client (durée minimale, temps de repos, nombre max d'activations).
- **Baseline et gisement exogènes** — supposés connus, alors qu'ils font chacun l'objet d'un sous-problème non trivial.
- **Horizon fixe**, pas de redéclaration infrajournalière ; données déterministes.


## Perspectives

Les principales directions d'amélioration sont documentées dans la note technique : relâchement de C1 en inégalité avec pénalité de sous-livraison, ajout de contraintes inter-temporelles par client, modélisation explicite du rebond intra-horizon via une matrice de réponse impulsionnelle, et extension au cas multi-EDE.

## About
Curieux et passionné par les marchés de l'électricité, je me suis rendu compte que je maîtrisais mal les mécanismes d'effacement, qui sont pourtant de formidables outils pour rendre les systèmes électriques européens plus flexibles et résilients. 

En me renseignant sur le nouveau dispositif **NEBCO**, j'ai immédiatement fait le lien avec les problèmes de recherche opérationnelle sur lesquels j'avais travaillé lors de ma formation à l'**ENSTA Paris**. J'ai donc eu envie de modéliser une partie du problème auquel sont confrontés les **Opérateurs d'Effacement**, afin de mieux comprendre le NEBCO et de **remobiliser des compétences** de modélisation et d'optimisation, qui commençaient à être bien enfouies dans mon système neuronal ! Une replongée dans les brillants et complexes cours de Jean-Charles Gilbert ([lien](https://who.rocq.inria.fr/Jean-Charles.Gilbert/ensta/cours2a/optim.html)) m'a rappelé à quel point l'univers de la recherche opérationnelle est riche et complexe. 

Loin de prétendre maîtriser aujourd'hui la RO, mon ambition est de **comprendre les modèles, de les implémenter, et d'en tirer des analyses pertinentes**. 


---
Ce travail est mené **en parallèle d’une formation "[Data Engineer & IA](https://le-campus-numerique.fr/formation-data/)"** au **Campus Numérique in the Alps (Grenoble)**. Certaines notions étudiées lors de cette formation pourront compléter ce projet, je pense notamment à l'utilisation de **Machine Learning** pour établir des base-lines de consommation.


## Utilisation des outils d'intelligence artificielle

Dans le cadre de ce projet, j'ai utilisé des outils d'IA pour :
- **Structurer et clarifier** certaines parties de la documentation (README, notes techniques).
- **Vérifier la terminologie et la cohérence de certaines hypothèses** (règles NEBCO).
- **Explorer et challenger des pistes de modélisation** (discussions sur les contraintes, simplification des hypothèses).
- Générer des **jeux de données d'exemple cohérentes**
- Aider à **implémenter le module de reporting** et à **fiabiliser le solver** (détection et correction d'un bug sur les variables éliminées en presolve CBC)

**Ce qui reste issu de mon travail** :
- L'**Analyse réglementaire**
- La **modélisation mathématique** (choix des variables, contraintes, fonction objectif).
- La **conception du code** (architecture du projet, choix techniques, structure des modules).
- Les **hypothèses simplificatrices et le cadrage du problème**.
- La **relecture critique** de toutes les propositions reçues.

*Outils utilisés* : Claude (Anthropic) pour la documentation, les discussions techniques et l'assistance au développement..


## Références

- **Cadre légal** — Code de l'énergie, articles [L.271-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031067893) à [L.271-3](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043214830) (définition de l'effacement, agrément de l'opérateur, régime de versement) et articles [R.271-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033056210) à [R.271-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033056218) (modalités techniques).
- **Règles opérationnelles** — CRE, *Délibération n°2025-199 portant approbation  des règles NEBCO*, juillet 2025.
- **Mise en œuvre** — RTE, *Règles de Marché — Chapitre 5 : NEBCO*, version en vigueur au 01/09/2025 — en particulier art. 5.F.
