# Note technique — Choix de modélisation du dispatch NEBCO

Cette note développe les choix de modélisation du prototype et les
justifications qui n'ont pas leur place dans le README. Elle complète le
README sans le dupliquer : le README donne le contexte, la formulation et
les limites ; cette note explique **pourquoi** ces choix.

## Sommaire

1. [Périmètre modélisé : un OE, une EDE, sans distinction de profilage](#1-périmètre-modélisé)
2. [Fonction objectif : pourquoi ignorer revenu NEBCO et versement fournisseur](#2-fonction-objectif)
3. [Pourquoi MILP plutôt que LP](#3-pourquoi-milp-plutôt-que-lp)
4. [Modélisation du rebond : Position A vs matrice impulsionnelle](#4-modélisation-du-rebond)
5. [Bilan énergétique C3 : horizon local vs période glissante NEBCO](#5-bilan-énergétique-c3)
6. [Hypothèses exogènes : baseline et gisement](#6-hypothèses-exogènes)

---

## 1. Périmètre modélisé

La hiérarchie NEBCO (art. 5.F) organise les acteurs ainsi :

```
Opérateur d'Effacement (OE)              ← personne morale agréée par RTE
  └── Périmètre d'Effacement (PE)        ← un seul PE par OE, non transférable
        ├── EDE 1  (Télérelevée ou Profilée)
        │     ├── Site de Soutirage 1.1
        │     └── Site de Soutirage 1.2
        ├── EDE 2  (Télérelevée ou Profilée)
        │     └── ...
```

Le prototype v1 considère **un OE gérant un PE contenant une seule EDE**,
laquelle regroupe les N clients du portefeuille. C'est une simplification de
modélisation, pas une position réglementaire.

**La typologie de l'EDE (Télérelevée ou Profilée) n'est pas distinguée.**
Cette distinction est pourtant importante dans NEBCO : elle conditionne la
méthode de contrôle du réalisé (mesure directe des courbes de charge pour
les sites télérelevés, méthode des panels pour les sites profilés), et donc
la façon dont la baseline et le rebond sont reconstruits. En ignorant cette
distinction, le modèle traite tous les clients comme s'ils étaient
télérelevés avec mesure directe.

Conséquences pour la modélisation réelle :

- **Multi-EDE** : un OE peut avoir plusieurs EDE (une par typologie, ou par
  zone géographique pour le télérelevé). Chacune a son propre bilan
  énergétique à vérifier. L'extension naturelle est de répliquer C3 par EDE
  et de partitionner la consigne RTE entre EDE — ce qui revient à résoudre
  N sous-problèmes de dispatch couplés par le plafond OE global (C2).
- **Périodes de bilan différentes** : les périodes de contrôle du bilan C3
  sont typiquement différentes pour Télérelevé et Profilé (voir section 5).
  Un modèle multi-EDE devrait respecter des périodes distinctes par EDE.

Cette limite justifie l'extension v2.1 (multi-EDE) et v2.2 (bilan sur
période glissante) de la roadmap.

---

## 2. Fonction objectif

### 2.1 Profit complet de l'OE

Sur l'horizon d'un programme d'effacement retenu, le profit π de l'OE
s'écrit :

$$
\pi = \underbrace{\sum_t \lambda_t \cdot E_t^{retenu} \cdot \Delta t}_{\text{revenu NEBCO}}
\;-\; \underbrace{\sum_t B \cdot E_t^{retenu} \cdot \Delta t}_{\text{versement fournisseur}}
\;-\; \underbrace{\sum_{c,t} \left( C_c^{act} \cdot x_{c,t} \cdot \Delta t + f_{c,t} \cdot \delta_{c,t} \right)}_{\text{coût dispatch interne}}
$$

Les trois termes sont :

- **Revenu NEBCO** — l'OE a vendu le volume `E_t^{retenu}` sur les marchés
  de l'énergie au prix spot `λ_t`. Ce terme est fixé dès la clôture du
  Niveau 1 (offre retenue par RTE).
- **Versement fournisseur** — au titre de l'article L.271-3 du Code de
  l'énergie, l'OE reverse aux fournisseurs des sites effacés une
  compensation au barème `B` fixé par la CRE (€/MWh), proportionnelle au
  volume effacé.
- **Coût dispatch interne** — compensations versées aux clients et coûts
  fixes d'activation, pilotables par l'OE via ses décisions `x_{c,t}` et
  `δ_{c,t}`.

### 2.2 Équivalence sous C1 en égalité

La contrainte C1 impose la livraison exacte :

$$
\sum_c x_{c,t} \cdot \Delta t = E_t^{retenu} \qquad \forall t
$$

Sous cette contrainte, les deux premiers termes de π sont **entièrement
déterminés** :

- `λ_t` et `E_t^{retenu}` sont des entrées figées par le Niveau 1 — aucune
  variable de décision du Niveau 2 ne les affecte.
- `B` est un barème forfaitaire connu à l'avance. Le versement total
  `B · E_t^{retenu} · Δt` ne dépend que du volume global par pas, pas de la
  répartition `x_{c,t}` entre clients. Deux dispatches internes différents
  livrant le même `E_t^{retenu}` paient exactement le même versement
  fournisseur.

Ces deux termes sont donc **constants vis-à-vis de `x_{c,t}` et `δ_{c,t}`**.
Ils disparaissent par différentiation dans le problème d'optimisation :

$$
\arg\max_{x,\delta} \pi \;=\; \arg\min_{x,\delta} \sum_{c,t} \left( C_c^{act} \cdot x_{c,t} \cdot \Delta t + f_{c,t} \cdot \delta_{c,t} \right)
$$

Minimiser le coût dispatch interne est **mathématiquement équivalent** à
maximiser le profit complet, conditionnellement à la contrainte de
livraison. Le problème se simplifie sans perte d'optimalité.

### 2.3 Conditions de validité

L'équivalence tient strictement sous trois conditions :

1. **C1 est une égalité.** Si on relâche C1 en inégalité (v1.1 de la
   roadmap, sous-livraison autorisée avec pénalité), alors le volume livré
   `Σ_c x_{c,t} · Δt` devient une variable de décision. Le revenu NEBCO et
   le versement fournisseur dépendent de cette variable et doivent
   réapparaître explicitement dans l'objectif, avec la pénalité de
   sous-livraison :

   $$
   \max \sum_t (\lambda_t - B) \cdot L_t \cdot \Delta t \;-\; \text{coût interne} \;-\; P \cdot s_t
   $$

   où `L_t = Σ_c x_{c,t}` est le volume livré et `s_t = E_t^{retenu} - L_t`
   le slack de sous-livraison pénalisé au taux `P`.

2. **Le barème `B` est indépendant du client.** Si `B` variait selon le
   profil du site effacé (barèmes différenciés résidentiel/industriel), il
   entrerait dans l'arbitrage interne entre clients et devrait figurer dans
   `C_c^{act}` effectif.

3. **Le plan d'effacement retenu `E_t^{retenu}` est fixé.** Si on
   co-optimisait Niveau 1 et Niveau 2 (offre + dispatch simultanés), les
   trois termes seraient à nouveau variables.

### 2.4 Bénéfices pratiques

Ignorer proprement les deux premiers termes permet :

- Une **fonction objectif plus simple** à lire et à déboguer.
- Une **interprétation plus claire** des résultats : le coût optimal est
  directement le coût cash à débourser par l'OE pour honorer sa consigne.
- **Aucune dépendance** aux paramètres `λ_t` et `B` dans le code du
  Niveau 2 — qui relèvent du Niveau 1 et du cadre réglementaire.

Cette propriété sera perdue dès la v1.1 : la modélisation devra alors
inclure les revenus et la pénalité pour permettre l'arbitrage entre livrer
complètement et accepter une sous-livraison pénalisée.

---

## 3. Pourquoi MILP plutôt que LP

Un programme linéaire pur (LP) offrirait un avantage analytique puissant :
la dualité forte garantit l'existence de multiplicateurs de Lagrange
interprétables comme **prix fictifs** des contraintes. On lirait directement
la valeur marginale d'une unité supplémentaire de consigne (dual de C1), le
coût économique du plafond réglementaire (dual de C2), ou la valeur d'une
détente du bilan énergétique (dual de C3). C'est très utile pour
l'analyse *post hoc* et la tarification interne entre OE et clients.

Mais plusieurs aspects du problème sont structurellement non-convexes :

- **Coût fixe d'activation** (télécom, usure, sollicitation client) : charge
  déclenchée dès lors qu'on active le client, indépendante du volume. Ça se
  modélise avec une variable binaire `δ`, pas avec du continu. Sans binaire,
  on ne peut pas distinguer "je n'active pas" de "j'active à volume nul".
- **Seuil minimal d'effacement si activé** : un industriel ne peut pas
  répondre à un ordre de 50 kW alors qu'il a un process à 500 kW. La
  contrainte "x = 0 ou x ≥ e_min" est disjonctive, elle se formule
  naturellement avec `x ≥ e_min · δ`.
- **Contraintes inter-temporelles** (v1.2) : durée minimale d'effacement,
  temps de repos entre activations, nombre max d'activations — toutes
  entières par nature.

Tenter de modéliser ces aspects en LP pur revient à les relâcher (coûts
fixes répartis au prorata, seuils ignorés) et à produire des dispatches
physiquement irréalistes — un industriel activé à 10% de son seuil, par
exemple.

MILP perd la dualité forte (les binaires cassent la convexité), mais garde
la formulation fidèle au problème physique et contractuel. Le coût
computationnel est maîtrisé pour des portefeuilles de taille raisonnable :
le prototype à 4 clients × 6 pas se résout en une fraction de seconde avec
CBC.

### Compromis pratique : relaxation LP à δ fixés

Une approche qui récupère une partie de l'analyse duale : résoudre le MILP
complet pour trouver le plan d'activation optimal `δ*`, puis **résoudre la
relaxation LP en fixant `δ = δ*`**. Les duaux obtenus sont interprétables
**conditionnellement** à ce plan d'activation — ils répondent à la question
"quelle serait la valeur marginale d'un MWh de consigne supplémentaire,
*sans changer quels clients sont activés* ?" C'est une analyse de
sensibilité locale, pas globale, mais elle est utile pour la tarification
et la communication aux clients. Cette extension est prévue en v1.3.

---

## 4. Modélisation du rebond

### 4.1 Définition du rebond NEBCO

Le rebond (ou *report de consommation*) désigne la consommation augmentée
qui suit un effacement : un ballon d'eau chaude refroidi pendant un
effacement consomme davantage ensuite pour se réchauffer ; un VE débranché
pendant la pointe se rechargera plus tard. NEBCO reconnaît explicitement ce
phénomène (art. L.271-1 du Code de l'énergie) et impose un bilan :
l'énergie totale reportée (hausse) ne doit pas excéder l'énergie effacée
(baisse), à la maille EDE.

### 4.2 Position A : taux scalaire par pas (v1)

Le modèle v1 représente le rebond par un coefficient `r[c,t] ∈ [0, +∞[` :

$$
\text{rebond}_{c,t} = r_{c,t} \cdot x_{c,t} \cdot \Delta t
$$

Ce coefficient capture l'**ampleur** du rebond mais pas son **timing**. Le
rebond est supposé hors horizon d'optimisation — c'est-à-dire qu'il se
produit après la fenêtre considérée par le modèle. C'est cohérent avec le
fait qu'on utilise `r[c,t]` uniquement dans C3 (bilan global), jamais dans
C1 (livraison par pas).

Cette modélisation autorise `r > 1` pour certains clients (chauffe-eau avec
réchauffage moins efficace après coupure profonde, PAC avec grand écart
thermique) pourvu que le bilan global à la maille EDE reste conforme.

**Limite principale** : en pratique, le rebond d'un effacement à 18h tombe
à 19h-20h, donc *dans* l'horizon d'optimisation usuel. Ignorer ce timing
fausse C1 sur les pas suivants : un effacement nominal de 1 MW à 18h peut
être partiellement annulé par le rebond d'un effacement précédent.

### 4.3 Position B : matrice de réponse impulsionnelle (v2.0)

La modélisation fidèle remplace le scalaire par une **matrice de réponse
impulsionnelle** `R_c[τ]` : pour le client c, un effacement unitaire au pas
`t` génère un rebond `R_c[τ]` au pas `t + τ`.

Le bilan de consommation au pas t devient :

$$
\text{conso\_réalisée}_{c,t} = \text{conso\_ref}_{c,t} \;-\; x_{c,t} \;+\; \sum_{\tau \geq 1} R_c[\tau] \cdot x_{c, t-\tau}
$$

Ce qui change :

- **C1 devient dynamique** : la livraison nette à `t` dépend des décisions
  aux pas antérieurs `t-τ` via le rebond. Le problème reste linéaire (en
  `x`) mais devient couplé inter-temporellement.
- **C3 peut se simplifier** : si `Σ_τ R_c[τ] = r_c` (intégrale du rebond =
  taux global), le bilan C3 s'obtient comme limite du cas scalaire ; mais
  la réparation temporelle est explicite.
- **Besoin d'identifier R_c** : mesure empirique à partir de données
  d'effacement passées, ou modèle physique pour les équipements simples
  (ballon d'eau chaude modélisé par une décharge exponentielle).

Cette extension est le changement structurel le plus important entre v1 et
v2, et celui qui rapproche le plus le modèle des contraintes opérationnelles
réelles.

---

## 5. Bilan énergétique C3

La contrainte C3 du modèle v1 :

$$
\sum_{c,t} r_{c,t} \cdot x_{c,t} \cdot \Delta t \;\leq\; \sum_{c,t} x_{c,t} \cdot \Delta t
$$

est appliquée sur l'horizon d'optimisation court (6 pas demi-horaires = 3
heures dans l'exemple de référence).

Le bilan énergétique NEBCO officiel est en réalité contrôlé sur une
**période glissante plus longue** : typiquement quelques jours pour une EDE
Télérelevée et un peu moins pour une EDE Profilée (ordres de grandeur à
confirmer selon la version des règles applicables — les règles détaillent
des fréquences de calcul mensuelles et des périodes de validité des
programmes déclarés).

Conséquences du décalage :

- **v1 est plus restrictive que la règle réelle** : un rebond pourrait en
  pratique être reporté au-delà de l'horizon local de dispatch sans violer
  NEBCO, du moment qu'il est compensé dans la période glissante. Le modèle
  v1 interdit cette flexibilité.
- **Direction conservative** : cette restriction va dans le sens de la
  sûreté — une solution faisable au sens v1 est nécessairement faisable au
  sens NEBCO. L'OE sous-optimise peut-être, mais ne viole jamais la règle.
- **Extension v2.2** : coupler le dispatch à un suivi du bilan sur la
  période glissante complète, avec un état hérité des jours précédents. Ça
  devient un problème d'optimisation avec contrainte d'inventaire énergétique.

---

## 6. Hypothèses exogènes

Deux entrées majeures du modèle sont supposées connues, alors qu'elles sont
l'objet de sous-problèmes non triviaux :

### 6.1 Baseline (Courbe de Référence NEBCO)

`conso_ref[c,t]` est la consommation qu'aurait eu le client en l'absence
d'effacement. Elle sert à deux choses dans le modèle :
- Borne supérieure de l'effacement (on ne peut pas effacer plus qu'on ne
  consomme).
- Référence pour le contrôle du réalisé par RTE *a posteriori*.

La construction de la baseline est un problème statistique non trivial :
- Pour les sites Télérelevés, NEBCO propose plusieurs méthodes (rectangle
  à double référence corrigée, par prévision, par historique).
- Pour les sites Profilés, la méthode des panels introduite avec NEBCO
  compare la consommation des sites pilotés à un panel de sites
  représentatifs.

Le modèle v1 prend `conso_ref` comme entrée. Un projet réel devrait soit
intégrer un module de construction de baseline, soit coupler le dispatch à
un service externe qui la fournit.

### 6.2 Gisement effaçable

`pmax[c,t]` est la puissance effaçable maximale, qui varie dans le temps
selon :
- L'état physique de l'équipement (SOC d'un VE, niveau thermique d'un
  ballon, phase d'un process industriel).
- Les contraintes de confort ou de process du client.
- La disponibilité de la connexion télécom.

Le modèle v1 prend `pmax` comme entrée déterministe. Extensions pertinentes :
- **Modèles physiques** par type d'équipement (v2.x) : équation thermique
  pour un ballon, modèle de recharge pour un VE, couplage avec le planning
  de production pour un industriel.
- **Incertitude stochastique** (v2.3) : `pmax` connu seulement en
  distribution, résolution par *sample average approximation* (SAA) sur un
  ensemble de scénarios.

---

## Références

- Code de l'énergie, Livre II Titre VII, *L'effacement de consommation
  d'électricité* — articles [L.271-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031067893)
  (définition de l'effacement, prise en compte du report de consommation),
  [L.271-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000051560254)
  (agrément technique de l'opérateur d'effacement, modalités de valorisation)
  et [L.271-3](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043214830)
  (régime de versement vers les fournisseurs des sites effacés).
- Code de l'énergie, partie réglementaire — articles [R.271-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033056210)
  (définition technique de l'effacement, modalités de prise en compte des
  reports) et [R.271-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033056218)
  (définition de l'opérateur d'effacement et objet de l'agrément technique).
- LOI n° 2015-992 du 17 août 2015 relative à la transition énergétique pour
  la croissance verte, art. 168 — création du régime de versement.
- LOI n° 2025-391 du 30 avril 2025, art. 17 — dernière modification de L.271-2
  et L.271-3 (substitution du terme « opérateur d'effacement » par
  « agrégateur d'effacement » dans certaines dispositions).
- CRE, *Délibération n°2025-199 portant approbation des règles NEBCO*,
  juillet 2025.
- RTE, *Règles de Marché — Chapitre 5 : NEBCO*, version en vigueur au
  01/09/2025, en particulier art. 5.F (gestion du Périmètre d'Effacement).
- CRE, barème du versement applicable aux effacements.
