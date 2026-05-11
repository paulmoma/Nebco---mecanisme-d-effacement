---
title: "Note technique — Choix de modélisation du dispatch NEBCO"
author: "Paul Molaro-Maqua"
date: "11/05/2026"
---

# Note technique — Choix de modélisation du dispatch NEBCO

Cette note rappelle succinctement le cadre réglementaire du mécanisme NEBCO et développe les choix de modélisation. Elle apporte également les justifications qui n'ont pas leur place dans le README ; elle le complète sans le dupliquer.

## Sommaire
1. [Cadre réglementaire du NEBCO et décomposition du problème](#1-cadre-réglementaire-du-nebco-et-décomposition-du-problème)
2. [Périmètre modélisé : un OE, une EDE, sans distinction de profilage](#2-périmètre-modélisé--un-oe-une-ede-sans-distinction-de-profilage)
3. [Modélisation et fonction objectif : équivalence sous livraison stricte](#3-modélisation-et-fonction-objectif--équivalence-sous-livraison-stricte)
4. [Choix de la classe de modèle : LP vs MILP](#4-choix-de-la-classe-de-modèle--lp-vs-milp)
5. [Modélisation du rebond : taux scalaire vs matrice impulsionnelle](#5-modélisation-du-rebond--taux-scalaire-vs-matrice-impulsionnelle)
6. [Bilan énergétique C3 : horizon local vs période glissante NEBCO](#6-bilan-énergétique-c3--horizon-local-vs-période-glissante-nebco)
7. [Baseline et gisement, données supposées connues](#7-baseline-et-gisement-données-supposées-connues)
8. [Synthèse des perspectives](#8-synthèse-des-perspectives)

___

## 1. Cadre réglementaire du NEBCO et décomposition du problème

Le mécanisme NEBCO (Notification d'Échanges de Blocs de Consommation) permet à des Opérateurs d'Effacement (OE) agréés par RTE de valoriser des effacements de consommation sur les marchés de l'énergie — la veille pour le lendemain et en infrajournalier. Il succède au mécanisme NEBEF en vigueur depuis 2014 et s'en distingue principalement par la possibilité de valoriser également les modulations à la hausse dans le cadre de décalages de consommation (reports ou anticipations de consommation).

Concrètement, le fonctionnement est le suivant : l'Opérateur d'Effacement (OE) contractualise des clients capables de réduire ponctuellement leur consommation (industriels, gestionnaires de chauffe-eau, opérateurs de recharge de VE, etc.). Il construit des offres d'effacement qu'il soumet sur les marchés de l'énergie ou sur le mécanisme d'ajustement de RTE — la réduction de soutirage étant traitée, du point de vue du réseau, comme équivalente à une injection de puissance. Lorsqu'une offre est retenue, RTE notifie à l'OE un programme d'effacement — un profil de puissance à livrer sur un horizon donné. Ce volume est valorisé sur les marchés de l'énergie (bourse EPEX Spot ou gré-à-gré). L'OE doit alors activer ses clients pour délivrer ce volume, tout en respectant les contraintes du cadre NEBCO (bilan énergétique, plafond de capacité, versement aux fournisseurs des sites effacés). Le contrôle du volume effectivement réalisé est assuré a posteriori par RTE sur la base de courbes de référence.

### Décomposition en niveaux de décision

L'activité d'un OE se décompose en niveaux emboîtés :

```
Niveau 0  │ Caractérisation portefeuille (baseline, gisement)   ── hors scope
Niveau 1  │ Offre sur le marché NEBCO                           ── hors scope
Niveau 2  │ Dispatch interne post-notification RTE              ── CE PROJET
Niveau 3  │ Pilotage temps réel des équipements                 ── hors scope
```

Chaque niveau prend en entrée les sorties du précédent. La chaîne boucle : le réalisé mesuré au Niveau 3 alimente le Niveau 0 (mise à jour des baselines et du gisement), qui conditionne les offres du Niveau 1. Un dispatch qui ne permet pas de livrer le volume retenu dégrade l'indicateur de fiabilité de l'OE [NEBCO, art. 5.E.1.3.2.2]. 

C'est le problème de **dispatch interne**, le niveau 2 — ventiler le programme retenu entre les clients du portefeuille — qui est l'objet du présent projet.

Dans le problème réel, les niveaux 1 et 2 sont couplés : le coût interne du dispatch conditionne le prix auquel l'OE peut soumettre ses offres — un OE qui sous-estime ses coûts s'expose à des dispatches déficitaires, un OE qui les surestime n'est pas retenu. Le modèle v1 rompt ce couplage par hypothèse : le programme retenu $E_t^{retenu}$ est fixé et doit être livré intégralement (caractérisé par la contrainte C1 en égalité, voir ci-dessous). Le Niveau 2 se réduit alors à un problème de minimisation de coût, indépendant des paramètres de marché — les conditions de cette simplification sont détaillées en section 3.

___

## 2. Périmètre modélisé : un OE, une EDE, sans distinction de profilage

La hiérarchie NEBCO organise les acteurs ainsi :

```
Opérateur d'Effacement (OE)              ← personne morale agréée par RTE
  └── Périmètre d'Effacement (PE)        ← un seul PE par OE, non transférable
        ├── EDE 1  (Télérelevée ou Profilée)
        │     ├── Site de Soutirage 1.1
        │     └── Site de Soutirage 1.2
        ├── EDE 2  (Télérelevée ou Profilée)
        │     └── ...
```

Le prototype v1 considère **un OE gérant un PE contenant une seule EDE**, laquelle regroupe les N clients du portefeuille. C'est une simplification de modélisation, pas une position réglementaire.

**La typologie de l'EDE (Télérelevée ou Profilée) n'est pas distinguée.** Cette distinction est pourtant importante dans NEBCO : elle conditionne la méthode de contrôle du réalisé (mesure directe des courbes de charge pour les sites télérelevés, méthode des panels pour les sites profilés), et donc la façon dont la baseline (courbe de consommation de référence) et le rebond sont reconstruits. En ignorant cette distinction, le modèle traite tous les clients comme s'ils étaient télérelevés avec mesure directe.

La distinction Télérelevée/Profilée a des conséquences qui dépassent le Niveau 2 et touchent directement le Niveau 1 (offre sur le marché). En effet, le **barème de versement fournisseur** est **différencié par typologie d'EDE** : un barème pour les sites télérelevés et un pour les sites profilés, avec des formules propres à chaque catégorie. La typologie d'EDE est fortement corrélée avec la puissance souscrite (les sites de puissance > 36 kVA sont en pratique télérelevés)— ce qui distingue formellement les deux catégories est la modalité de mesure, pas le seuil tarifaire. Les barèmes sont publiés par RTE et approuvés par la CRE [CRE-2025-275].

En conséquence, lorsque l'OE construit son offre au Niveau 1, il doit anticiper le versement fournisseur en fonction de la composition de ses EDE — une EDE Profilée résidentielle n'a pas le même barème qu'une EDE Télérelevée industrielle. Cette différenciation n'a aucun impact sur le Niveau 2 (le versement est constant par rapport aux variables de dispatch, cf. section 3), mais elle conditionne la marge nette que l'OE peut espérer, et donc le prix auquel il peut soumettre ses offres d'effacement.

Conséquences pour la modélisation réelle :

- **Multi-EDE** : un OE peut avoir plusieurs EDE (une par typologie, ou par zone géographique pour le télérelevé). Chacune a son propre bilan énergétique à vérifier. L'extension naturelle serait de répliquer une contrainte de bilan énergétique C3 par EDE et de partitionner la consigne RTE entre EDE — ce qui revient à résoudre N sous-problèmes de dispatch couplés par le plafond OE global (C2).
- **Périodes de bilan différentes** : les périodes de contrôle du bilan C3 sont typiquement différentes pour Télérelevé et Profilé (voir section 6). Un modèle multi-EDE devrait respecter des périodes distinctes par EDE.

Cette limite ouvre la voie à une extension multi-EDE et à un bilan sur période glissante, identifiés dans la section 8.

___
## 3. Modélisation et fonction objectif : équivalence sous livraison stricte
Cette section présente d'abord la expression du problème retenue, la minimisation des coûts internes. On justifie ensuite ce choix d'objectif en montrant qu'il est équivalent à la maximisation du profit complet de l'OE sous l'hypothèse de livraison stricte (3.2), avant d'en délimiter le domaine de validité (3.3).
### 3.1 Synthèse de la modélisation

L'objectif est de minimiser le coût total de dispatch.

$$
\min_{x,\delta} \sum_{c,t} \left( C_c^{act} \cdot x_{c,t} \cdot \Delta t + f_{c,t} \cdot \delta_{c,t} \right)
$$


| Symbole | Description | Unité | Variable de décision |
|---------|-------------|-------| ---------------------|
| $x_{c,t}$ | Puissance effacée par le client c au pas t | MW | Oui |
| $\delta_{c,t}$| Activation du client c au pas t | {0, 1} | Oui |
| $C_c^{act}$ | Coût variable d'activation du client c | €/MWh | Non |
| $f_{c,t}$ | Coût fixe d'activation | € | Non |
| $\Delta t$ | Durée d'un pas de temps | h | Non |


La formulation de ce modèle utilise les contraintes suivantes, dont les choix seront discutés dans la suite de ce document :

| # | Contrainte | Formulation |
|---|-----------|-------------|
| C1 | Livraison de la consigne RTE | $\sum_c x_{c,t} \cdot \Delta t = E_t^{retenu}$ par pas |
| C2 | Plafond de puissance de l'OE | $\sum_c x_{c,t} \leq P^{max}_{OE}$ par pas |
| C3 | Bilan énergétique EDE | $\sum_{c,t} r_{c,t} \cdot x_{c,t} \cdot \Delta t \leq \sum_{c,t} x_{c,t} \cdot \Delta t$ |
| C4 | Plafond d'effacement par client $c$ & couplage effacement / activation | $x_{c,t} \leq ub_{c,t} \cdot \delta_{c,t}$ |
| C5 | Seuil minimal d'activation du client $c$| $x_{c,t} \geq e_{min,c,t} \cdot \delta_{c,t}$ |

Avec les variables suivantes :

| Symbole | Description | Unité |
|---|-----------|-------------|
| $E_t^{retenu}$ | Énergie de la consigne RTE au pas $t$ | MWh |
| $P_{OE}^{max}$ | Plafond de puissance de l'OE | MW |
| $p_{c,t}^{max}$ | Puissance maximale effaçable par le consommateur $c$ au pas $t$ | MW |
| $ub_{c,t}$ | Borne supérieure de l'effacement du consommateur $c$ au pas $t$ | MW |
| $r_{c,t}$ | Taux de rebond du consommateur $c$ au pas $t$ (cf. section 5) | sans dim. |

Toutes les variables continues sont positives ($x_{c,t} \geq 0$), ce qui est implicitement garanti par C5 ($x_{c,t} \geq e_{min,c,t} \cdot \delta_{c,t}$ avec $e_{min} \geq 0$ et $\delta \in \{0,1\}$) mais doit être déclaré explicitement au solveur.

La borne supérieure $ub_{c,t} = \min(p^{max}_{c,t},\; conso^{ref}_{c,t})$ intègre à la fois la puissance maximale ($p^{max}_{c,t}$) que le client $c$ consent à effacer et la contrainte de baseline (on ne peut pas effacer plus qu'on ne consomme). Elle intervient dans C4 et dans la borne de la variable $x_{c,t}$.

En pratique, C2 est rarement active si on contraint la livraison stricte de la consigne RTE : RTE ne devrait pas notifier un programme retenu excédant le plafond de l'OE. Néanmoins la contrainte est conservée comme garde-fou de cohérence et deviendrait structurante si l'on relâchait C1 en inégalité (sur-livraison possible mais pénalisée).


### 3.2 Du profit complet à la minimisation de coût

L'objectif retenu en 3.1 — minimiser le coût interne de dispatch — peut paraître simpliste, puisque l'OE cherche en réalité à maximiser son profit. On montre ici que sous l'hypothèse de livraison stricte (C1 en égalité), les deux problèmes sont mathématiquement équivalents.

Sur l'horizon d'un programme d'effacement retenu, le profit $\pi$ de l'OE s'écrit :

$$
\pi = \underbrace{\sum_t \lambda_t \cdot E_t^{retenu}}_{\text{vente de l'effacement}}
\;-\; \underbrace{\sum_t B \cdot E_t^{eff}}_{\text{compensation fournisseurs}}
\;-\; \underbrace{\sum_{c,t} \left( C_c^{act} \cdot x_{c,t} \cdot \Delta t + f_{c,t} \cdot \delta_{c,t} \right)}_{\text{coût dispatch interne}}- \underbrace{\sum_t \mu_t \cdot (E_t^{eff}-E_t^{retenu})}_{\text{pénalités}}
$$

avec $E_t^{eff}=\Delta t \cdot \sum_c x_{c,t}$ l'énergie totale effacée par l'OE sur le pas de temps $t$. Les quatre termes sont, dans l'ordre : la **vente de l'effacement** sur les marchés au prix spot $\lambda_t$ pour le volume $E_t^{retenu}$ retenu par RTE ; la **compensation versée aux fournisseurs** des sites effacés au barème forfaitaire $B$ fixé par la CRE (€/MWh), proportionnelle au volume effacé ; le **coût interne du dispatch**, pilotable par l'OE via les décisions $x_{c,t}$ et $\delta_{c,t}$ ; les **pénalités** sur les écarts de livraison (mécanisme de déséquilibre du marché de l'électricité, non imposé directement par NEBCO mais réel économiquement).

Sous C1 en égalité, $E_t^{eff} = E_t^{retenu}$ pour tout $t$. Trois des quatre termes deviennent alors **constants vis-à-vis des variables de décision** :

- $\lambda_t$ et $E_t^{retenu}$ sont des entrées figées par le Niveau 1 — la vente de l'effacement est un revenu fixe.
- Le versement fournisseur $B \cdot E_t^{retenu} \cdot \Delta t$ ne dépend que du volume global par pas, pas de la répartition $x_{c,t}$ entre clients : deux dispatches livrant le même $E_t^{retenu}$ paient strictement le même versement.
- Le terme de pénalité $\mu_t \cdot (E_t^{eff} - E_t^{retenu})$ s'annule trivialement.

Ces trois termes disparaissent par différentiation dans le problème d'optimisation :

$$
\arg\max_{x,\delta} \pi \;=\; \arg\min_{x,\delta} \sum_{c,t} \left( C_c^{act} \cdot x_{c,t} \cdot \Delta t + f_{c,t} \cdot \delta_{c,t} \right)
$$

Minimiser le coût de dispatch interne revient donc à maximiser le profit complet, sans perte d'optimalité. L'objectif obtenu est en outre directement interprétable comme le coût que l'OE doit débourser pour honorer sa consigne, et n'introduit aucune dépendance aux paramètres de marché ($\lambda_t$, $B$) dans le code du Niveau 2.

### 3.3 Conditions et portée

L'équivalence démontrée en 3.2 tient strictement sous deux conditions :

1. **C1 est une égalité.** Si on relâche C1 en inégalité (extension envisagée : sous-livraison autorisée avec pénalité), alors le volume livré $\sum_c x_{c,t} \cdot \Delta t$ devient une variable de décision. Le revenu NEBCO et le versement fournisseur en dépendent et doivent réapparaître explicitement dans l'objectif, conjointement avec un slack pénalisé sur la sous-livraison :

$$
\max \sum_t (\lambda_t - B) \cdot L_t \cdot \Delta t \;-\; \text{coût interne} \;-\; P \cdot s_t
$$

où $L_t = \sum_c x_{c,t}$ est le volume livré et $s_t = E_t^{retenu} - L_t$ le slack pénalisé au taux $P$.

2. **Le plan d'effacement retenu $E_t^{retenu}$ est fixé.** Si on co-optimisait Niveau 1 et Niveau 2 (offre et dispatch simultanés), revenu et versement redeviendraient variables.

S'y ajoute une hypothèse de périmètre, propre au modèle v1 plutôt que condition mathématique : le barème $B$ est uniforme sur toute l'EDE. C'est automatiquement vrai ici puisqu'on ne considère qu'une seule EDE (cf. section 2). Une extension multi-EDE devrait sommer correctement les versements en différenciant $B$ par typologie Télérelevée/Profilée — l'équivalence reste valable à l'intérieur de chaque EDE, mais l'objectif global devient une somme pondérée des coûts internes par EDE.

___

## 4. Choix de la classe de modèle : LP vs MILP

### 4.1 Programmation linéaire (LP)

Un **programme linéaire** (Linear Program, **LP**) minimise (ou maximise) une fonction objectif linéaire sur un ensemble admissible défini par un nombre fini de contraintes linéaires, avec des variables réelles. Le problème est de la forme :

$$
\min c^\top x \qquad \text{s.c.} \qquad A x \leq b, \quad x \in \mathbb{R}^n
$$

Le domaine admissible est un **polyèdre convexe**. Cette structure géométrique entraîne plusieurs propriétés fortes :

- Tout optimum local est global ; l'objectif étant linéaire et le domaine convexe, l'optimum (s'il existe et est fini) est atteint en un sommet du polyèdre.
- La **théorie de la dualité** s'applique pleinement : dualité forte, conditions de Karush-Kuhn-Tucker (KKT), interprétation économique des multiplicateurs de Lagrange comme **prix fictifs** (*shadow prices*) des contraintes.
- Les solveurs (simplexe, points intérieurs) sont matures et résolvent de façon fiable des instances de très grande taille.

L'analyse duale est souvent aussi précieuse que la solution primale : elle indique le coût marginal de chaque contrainte, ce qui ouvre la porte à la tarification interne, à l'analyse de sensibilité et à l'interprétation économique des résultats.

### 4.2 Programmation linéaire mixte en nombres entiers (MILP)

Un **programme linéaire mixte en nombres entiers** (Mixed Integer Linear Program, **MILP**) étend le LP en autorisant un sous-ensemble des variables à ne prendre que des valeurs entières, souvent restreintes à $\{0, 1\}$ (variables binaires) :

$$
\min c^\top x + d^\top y \qquad \text{s.c.} \qquad A x + B y \leq b, \quad x \in \mathbb{R}^n, y \in \mathbb{Z}^p
$$

Le qualificatif *mixte* désigne précisément la coexistence des variables continues et entières. Cette extension change la nature du problème :

- Le domaine admissible n'est plus convexe — c'est un ensemble discret de points dans un polyèdre — et les propriétés de la section 4.1 ne sont plus valables : il peut exister des optimums locaux non globaux, et la dualité forte ne tient plus en général.
- La résolution repose sur des algorithmes de type *branch-and-bound* ou *branch-and-cut*, qui énumèrent intelligemment les combinaisons de valeurs entières en s'appuyant sur des **relaxations LP** (on remplace $y \in \{0,1\}^p$ par $y \in [0,1]^p$) pour calculer des bornes et élaguer l'arbre de recherche.
- Le problème est NP-difficile dans le cas général, mais les solveurs modernes — comme CBC (COIN-OR Branch and Cut), embarqué par défaut avec PuLP — résolvent efficacement en pratique des instances structurées de taille industrielle.

En contrepartie de la flexibilité de modélisation, on perd l'analyse duale propre du LP.

### 4.3 Application au dispatch NEBCO

Plusieurs aspects du problème de dispatch sont **intrinsèquement discrets** et ne peuvent pas être représentés fidèlement dans un LP pur :

- **Coût fixe d'activation** (sollicitation télécom, usure, désagrément client) : charge déclenchée dès lors qu'on active le client, indépendante du volume effacé. Cela se modélise avec une variable binaire $\delta_{c,t}$ : $\delta_{c,t} = 1$ si le client est activé au pas $t$, $\delta_{c,t} = 0$ sinon. C'est cette variable qui distingue le cas « client non sollicité » ($x = 0$, $\delta = 0$) du cas « client sollicité à un certain niveau » ($x > 0$, $\delta = 1$).
- **Seuil minimal d'effacement si activé** : un industriel ne peut pas répondre à un ordre de 50 kW alors qu'il a un process à 500 kW. La contrainte disjonctive « $x = 0$ ou $x \geq e_{min}$ » se formule naturellement avec $x \geq e_{min} \cdot \delta$ couplée à $x \leq ub \cdot \delta$.
- **Contraintes inter-temporelles** (extension envisagée) : durée minimale d'effacement, temps de repos entre activations, nombre maximal de sollicitations par client — toutes entières par nature.

Tenter de modéliser ces aspects en LP pur revient à les relâcher : lisser les coûts fixes sur le volume, ignorer les seuils. On produit alors des dispatches physiquement irréalistes — un industriel activé à 10 % de son seuil minimal, par exemple — et des coûts sous-estimés.

Le choix du MILP est donc un arbitrage : on perd la dualité forte (les binaires cassent la convexité), mais on conserve une formulation fidèle au problème physique et contractuel. Le temps de calcul reste négligeable pour des portefeuilles de taille raisonnable : le prototype à 4 clients × 6 pas se résout en une fraction de seconde avec CBC.

### 4.4 Récupération partielle de l'analyse duale

Une approche permet de récupérer une partie du contenu informatif des duaux : résoudre le MILP complet pour trouver le plan d'activation optimal $\delta^*$, puis **résoudre la relaxation LP en fixant $\delta = \delta^*$**. Les multiplicateurs obtenus sont alors interprétables **conditionnellement** à ce plan d'activation : ils répondent à la question « quelle serait la valeur marginale d'un MWh de consigne supplémentaire, *sans changer quels clients sont activés* ? ». C'est une analyse de sensibilité locale, pas globale, mais utile pour la tarification interne et la communication aux clients.

Le multiplicateur le plus parlant est celui de C1 : il donne le coût marginal interne d'un MWh de consigne supplémentaire, c'est-à-dire le prix d'achat marginal au sein du portefeuille. Ce dual ferme la boucle avec la fonction de profit de la section 3.2 : c'est précisément le seuil en dessous duquel l'OE ne peut pas vendre rentablement un MWh supplémentaire au Niveau 1, et au-dessus duquel chaque MWh vendu rapporte. Cette extension pourrait être implémentée dans une version ultérieure.

___

## 5. Modélisation du rebond : taux scalaire vs matrice impulsionnelle

### 5.1 Définition du rebond NEBCO

Le rebond (ou *report de consommation*) désigne la consommation augmentée qui suit un effacement : un ballon d'eau chaude refroidi pendant un effacement consomme davantage ensuite pour se réchauffer ; un VE débranché pendant la pointe se rechargera plus tard. NEBCO reconnaît explicitement ce phénomène (art. L.271-1 du Code de l'énergie) et impose un bilan : l'énergie totale reportée (hausse) ne doit pas excéder l'énergie effacée (baisse), à la maille EDE.

### 5.2 Position actuelle : taux scalaire par pas (v1)

Le modèle v1 représente le rebond par un coefficient $r_{c,t} \in [0, +\infty[$ :

$$
rebond_{c,t} = r_{c,t} \cdot x_{c,t} \cdot \Delta t
$$

Ce coefficient capture l'**ampleur** du rebond mais pas son **timing**. Le rebond est supposé hors horizon d'optimisation — c'est-à-dire qu'il se produit après la fenêtre considérée par le modèle. C'est cohérent avec le fait qu'on utilise $r_{c,t}$ uniquement dans C3 (bilan global), jamais dans C1 (livraison par pas).

Cette modélisation autorise $r > 1$ pour certains clients (chauffe-eau avec réchauffage moins efficace après coupure profonde, PAC avec grand écart thermique) pourvu que le bilan global à la maille EDE reste conforme.

**Limite principale** : en pratique, le rebond d'un effacement à 18h tombe à 19h-20h, donc *dans* l'horizon d'optimisation usuel. Ignorer ce timing fausse C1 sur les pas suivants : un effacement nominal de 1 MW à 18h peut être partiellement annulé par le rebond d'un effacement précédent.

### 5.3 Modélisation plus fidèle : matrice de réponse impulsionnelle

La modélisation fidèle remplace le scalaire par une **matrice de réponse impulsionnelle** $R_c[\tau]$ : pour le client $c$, un effacement unitaire au pas $t$ génère un rebond $R_c[\tau]$ au pas $t + \tau$.

Le bilan de consommation au pas $t$ devient :

$$
conso^{réalisée}_{c,t} = conso^{ref}_{c,t} - x_{c,t}  + \sum_{\tau \geq 1} R_c[\tau] \cdot x_{c, t-\tau}
$$

Ce qui change :

- **C1 deviendrait dynamique** : la livraison nette à $t$ dépend des décisions aux pas antérieurs $t-\tau$ via le rebond. Le problème reste linéaire (en $x$) mais devient couplé inter-temporellement.
- **C3 pourrait se simplifier** : si $\sum_\tau R_c[\tau] = r_c$ (intégrale du rebond = taux global), le bilan C3 s'obtient comme limite du cas scalaire ; mais la répartition temporelle est explicite.
- **Besoin d'identifier $R_c$** : c'est un problème inverse de **déconvolution** — on cherche la réponse impulsionnelle à partir de couples (effacement notifié, écart à la baseline mesuré). En pratique, l'identification est mal posée et nécessite une régularisation (Tikhonov, lissage, contraintes de positivité ou de monotonie). Pour les équipements simples, un modèle physique (décharge thermique exponentielle d'un ballon d'eau chaude, par exemple) fournit une forme paramétrique qui réduit considérablement le nombre de paramètres à identifier.

La matrice $R_c[\tau]$ peut s'étendre aux valeurs $\tau < 0$ pour modéliser les anticipations de consommation (hausse avant l'effacement), reconnues par NEBCO au même titre que les reports.

Cette extension serait le changement de modélisation le plus important, et celui qui rapprocherait le plus le modèle des contraintes opérationnelles réelles.

___

## 6. Bilan énergétique C3 : horizon local vs période glissante NEBCO

La contrainte C3 du modèle v1 :

$$
\sum_{c,t} r_{c,t} \cdot x_{c,t} \cdot \Delta t \;\leq\; \sum_{c,t} x_{c,t} \cdot \Delta t
$$

est appliquée sur l'horizon d'optimisation court (6 pas demi-horaires = 3 heures dans l'exemple de référence).

NEBCO impose trois niveaux de contrôle de l'équilibre énergétique [CRE-2025-199]:

- **Validité des programmes déclarés** : les programmes soumis par l'OE doivent être équilibrés (hausse ≤ baisse) sur **7 jours** pour les EDE Télérelevées et **2 jours** pour les EDE Profilées. Un programme déséquilibré est rejeté par RTE.
- **Bilan annuel réalisé** : RTE vérifie a posteriori, à la maille EDE, que les volumes réalisés de modulations à la hausse ne dépassent pas ceux à la baisse, sur l'année calendaire. Un bilan annuel non conforme entraîne la suspension de l'accord de participation (3 à 6 mois).
- **Suivi mensuel** : RTE calcule des bilans et ratios mensuels à titre de surveillance. En cas de non-conformité persistante, une limitation des volumes valorisables pourra être activée.

Le modèle v1 applique C3 sur l'horizon d'optimisation court (3 heures), ce qui est **significativement plus restrictif** que ces trois niveaux de contrôle. Une solution faisable au sens v1 est nécessairement faisable au sens NEBCO — le modèle sous-optimise peut-être, mais ne viole jamais la règle.


___

## 7. Baseline et gisement, données supposées connues

Deux entrées majeures du modèle sont supposées connues, alors qu'elles sont l'objet de sous-problèmes non triviaux :

### 7.1 Baseline (Courbe de Référence NEBCO)

$conso^{ref}_{c,t}$ est la consommation qu'aurait eu le client en l'absence d'effacement. Elle sert à deux choses dans le modèle :
- Borne supérieure de l'effacement (on ne peut pas effacer plus qu'on ne consomme).
- Référence pour le contrôle du réalisé par RTE *a posteriori*.

La construction de la baseline est un problème statistique non trivial, dont les méthodes admises sont définies dans les fiches techniques transverses des Dispositions Générales des Règles de Marché de RTE [RM-0] :

- Pour les sites Télérelevés, quatre méthodes sont éligibles selon les caractéristiques du site : *rectangle à double référence corrigée*, *rectangle algébrique site à site*, *par prévision de consommation*, *par historique de consommation* [RM-0, NEBCO §5.E].
- Pour les sites Profilés, la **méthode des panels** introduite avec NEBCO [CRE-2025-199 §2.2] reconstruit la courbe de référence d'une EDE à partir d'un *panel miroir* de sites représentatifs hors activation. La courbe est une moyenne pondérée des courbes de charge du panel, avec une pondération qui minimise l'écart à la consommation observée sur une période de référence hors plages d'effacement [Enedis-CR, RTE-NEBCO-RA].

Le modèle v1 prend $conso_{ref}$ comme entrée. Un projet réel devrait soit intégrer un module de construction de baseline, soit coupler le dispatch à un service externe qui la fournit.

### 7.2 Gisement effaçable

$p^{max}_{c,t}$ est la puissance effaçable maximale, qui varie dans le temps selon :
- L'état physique de l'équipement (SOC d'un VE, niveau thermique d'un ballon, phase d'un process industriel).
- Les contraintes de confort ou de process du client.
- La disponibilité de la connexion télécom.

Le modèle v1 prend $p^{max}$ comme entrée déterministe. Extensions pertinentes :
- **Modèles physiques** par type d'équipement : équation thermique pour un ballon, modèle de recharge pour un VE, couplage avec le planning de production pour un industriel.
- **Incertitude stochastique** : $p^{max}$ connu seulement en distribution, résolution par *sample average approximation* (SAA) sur un ensemble de scénarios.

## 8. Synthèse des perspectives

Les choix documentés ici reflètent un arbitrage entre représentation fidèle du mécanisme NEBCO et facilité de mise en œuvre avec un MILP. Plusieurs directions d'amélioration se dégagent des limites discutées dans ce document :

- **Relâcher C1 en inégalité** : autoriser la sous-livraison moyennant une pénalité. L'objectif devrait alors réintégrer le revenu NEBCO et le versement fournisseur pour permettre l'arbitrage économique (cf. section 3.3).
- **Contraintes inter-temporelles** : durée minimale d'effacement, temps de repos entre activations, nombre maximal de sollicitations par client. Ces contraintes sont déterminantes pour les process industriels.
- **Rebond intra-horizon** : remplacer le taux scalaire par une matrice de réponse impulsionnelle $R_c[\tau]$, qui rendrait C1 dynamique et couplée inter-temporellement (cf. section 5.3).
- **Multi-EDE** : répliquer C3 par EDE et gérer des périodes de bilan distinctes selon la typologie Télérelevée/Profilée (cf. section 6).
- **Incertitude sur le gisement** : le $p^{max}_{c,t}$ réel n'est connu qu'en distribution — une approche stochastique (SAA sur scénarios) permettrait de robustifier le dispatch.
- **Tarification interne et analyse de sensibilité** : implémentation systématique de la relaxation LP à $\delta^*$ pour exposer les prix fictifs des contraintes (cf. section 4.4), notamment le dual de C1 qui donne le coût marginal interne d'un MWh livré et permet de remonter au Niveau 1 pour tarifer les offres.


___

## Références

- Code de l'énergie, Livre II Titre VII, *L'effacement de consommation d'électricité* — articles [L.271-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031067893) (définition de l'effacement, prise en compte du report de consommation), [L.271-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000051560254) (agrément technique de l'opérateur d'effacement, modalités de valorisation) et [L.271-3](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043214830) (régime de versement vers les fournisseurs des sites effacés).
- Code de l'énergie, partie réglementaire — articles [R.271-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033056210) (définition technique de l'effacement, modalités de prise en compte des reports) et [R.271-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033056218) (définition de l'opérateur d'effacement et objet de l'agrément technique).
- LOI n° 2015-992 du 17 août 2015 relative à la transition énergétique pour la croissance verte, art. 168 — création du régime de versement.
- LOI n° 2025-391 du 30 avril 2025, art. 17 — dernière modification de L.271-2 et L.271-3 (substitution du terme « opérateur d'effacement » par « agrégateur d'effacement » dans certaines dispositions).
- **[CRE-2025-199]** CRE, *Délibération n°2025-199 portant approbation des règles NEBCO*, juillet 2025 — section 2.2 sur l'introduction de la méthode des panels pour les EDE Profilées ([CRE](https://www.cre.fr/fileadmin/Documents/Deliberations/2025/250723_2025-199_NEBCO.pdf)).
- **[NEBCO]** RTE, *Règles de Marché — Chapitre 5 : NEBCO*, version en vigueur au 01/09/2025, en particulier art. 5.F (gestion du Périmètre d'Effacement) ([services-rte.fr](https://services-rte.fr/files/live/sites/services-rte/files/Regles%20NEBCO%201.0.pdf)).
- **[RM-0]** RTE, *Règles de Marché — Chapitre 0 : Dispositions Générales*, version V2 en vigueur au 01/01/2026 (intégrant les délibérations CRE 2025-266 et 2025-275) — fiches techniques transverses, section *« Méthodes pour l'établissement de la Courbe de Référence »* (rectangle à double référence corrigée, rectangle algébrique site à site, par prévision, par historique, méthode des panels) ([annonce RTE](https://www.services-rte.com/fr/toutes-les-actualites/nouvelles-versions-des-regles--1.html)).
- **[RTE-NEBCO-RA]** RTE, *Rapport d'accompagnement à la consultation — Règles NEBCO 1.0*, 2025 — argumentaire et modalités d'introduction de la méthode des panels dans NEBCO ([services-rte.fr](https://services-rte.fr/files/live/sites/services-rte/files/Rapport%20d'accompagnement%20NEBCO%201.0.pdf)).
- **[Enedis-CR]** Enedis, *Contrôle du Réalisé — Description des méthodes*, document support technique — description du mécanisme statistique du panel miroir (moyenne pondérée des sites du panel minimisant l'écart à la consommation hors activation) ([enedis.fr](https://www.enedis.fr/media/3147/download)).
- **[CRE-2025-275]** CRE, *Délibération n°2025-275 du 17 décembre 2025 portant approbation des dispositions générales des règles de marché de RTE* — barèmes forfaitaires de versement fournisseur pour les sites télérelevés et profilés en modèle régulé ([Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053097596), [RTE — page des barèmes](https://www.services-rte.com/fr/decouvrez-nos-offres-de-services/baremes-versement-nebef.html)).
- J.C. Gilbert, *Optimisation Différentiable — Théorie et Algorithmes*, cours OPT-201/OPT-202, ENSTA Paris 2016-2017. [Page du cours](https://who.rocq.inria.fr/Jean-Charles.Gilbert/ensta/cours2a/optim.html)
