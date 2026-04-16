"""
Formulation MILP du dispatch interne NEBCO (Niveau 2).

La fonction build_model construit le programme PuLP à partir d'un Portfolio
et d'une Consigne, et retourne le problème ainsi qu'un dictionnaire des
variables pour permettre l'inspection post-résolution.

Formulation
-----------
Variables :
    x[c,t] ∈ [0, ub[c,t]]  : puissance effacée [MW]
    δ[c,t] ∈ {0, 1}         : activation du client c au pas t

Objectif : min Σ ( C_act[c] · x[c,t] · Δt + f[c,t] · δ[c,t] )

Contraintes :
    C1 — Livraison exacte de la consigne RTE par pas [égalité, v1]
    C2 — Plafond réglementaire EDE par pas
    C3 — Bilan énergétique NEBCO : Σ rebond ≤ Σ effacement (maille EDE)
    C4 — Couplage activation/effacement : x ≤ ub · δ
    C5 — Seuil minimal si activé : x ≥ e_min · δ
"""

from dataclasses import dataclass
from typing import Dict, List

from pulp import LpBinary, LpMinimize, LpProblem, LpVariable, lpSum

from .data import Consigne, Portfolio


@dataclass
class ModelVariables:
    """Conteneur des variables de décision pour inspection post-résolution.

    Indexation : x[c][t], delta[c][t] avec c ∈ [0, N[, t ∈ [0, T[.
    """

    x: List[List[LpVariable]]
    delta: List[List[LpVariable]]


def build_model(
    portfolio: Portfolio,
    consigne: Consigne,
) -> tuple[LpProblem, ModelVariables]:
    """Construit le problème MILP de dispatch interne NEBCO.

    Parameters
    ----------
    portfolio : Portfolio
        Portefeuille de clients de l'agrégateur.
    consigne : Consigne
        Programme d'effacement retenu par RTE.

    Returns
    -------
    prob : LpProblem
        Le problème PuLP, non résolu.
    variables : ModelVariables
        Les variables de décision, pour inspection après solve().
    """
    portfolio.check_against(consigne)

    N, T = portfolio.N, consigne.T
    dt = consigne.delta_t

    prob = LpProblem("NEBCO_Niveau2_MILP", LpMinimize)

    # ── Variables de décision ────────────────────────────────────────────
    x = [
        [
            LpVariable(
                f"x_c{c}_t{t}",
                lowBound=0,
                upBound=portfolio.clients[c].ub(t),
            )
            for t in range(T)
        ]
        for c in range(N)
    ]
    delta = [
        [LpVariable(f"delta_c{c}_t{t}", cat=LpBinary) for t in range(T)]
        for c in range(N)
    ]

    # ── Fonction objectif ────────────────────────────────────────────────
    prob += (
        lpSum(
            portfolio.clients[c].cout_variable * x[c][t] * dt
            + portfolio.clients[c].cout_fixe[t] * delta[c][t]
            for c in range(N)
            for t in range(T)
        ),
        "Cout_total_dispatch",
    )

    # ── Contraintes par pas de temps ─────────────────────────────────────
    for t in range(T):
        # C1 — Livraison exacte de la consigne [MWh]
        prob += (
            lpSum(x[c][t] * dt for c in range(N)) == consigne.e_retenu[t],
            f"C1_Livraison_t{t}",
        )

        # C2 — Plafond réglementaire EDE [MW]
        prob += (
            lpSum(x[c][t] for c in range(N)) <= consigne.e_max_agr,
            f"C2_Plafond_EDE_t{t}",
        )

        for c in range(N):
            client = portfolio.clients[c]

            # C4 — Couplage activation/effacement (big-M = ub naturel)
            prob += (
                x[c][t] <= client.ub(t) * delta[c][t],
                f"C4_BorneSupActivation_c{c}_t{t}",
            )

            # C5 — Seuil minimal si activé
            prob += (
                x[c][t] >= client.e_min[t] * delta[c][t],
                f"C5_SeuilMinActivation_c{c}_t{t}",
            )

    # ── C3 — Bilan énergétique NEBCO sur l'horizon ───────────────────────
    prob += (
        lpSum(
            portfolio.clients[c].taux_rebond[t] * x[c][t] * dt
            for c in range(N)
            for t in range(T)
        )
        <= lpSum(x[c][t] * dt for c in range(N) for t in range(T)),
        "C3_Bilan_EDE_NEBCO",
    )

    return prob, ModelVariables(x=x, delta=delta)
