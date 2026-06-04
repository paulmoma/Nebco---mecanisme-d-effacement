"""
Relaxation LP du dispatch NEBCO — extraction des coûts marginaux internes.

Résout une version LP du MILP en fixant les activations binaires δ à leur valeur optimale δ*. Le problème devenant un LP pur, les multiplicateurs de Lagrange (variables duales) des contraintes sont accessibles. Ces coefficients s'interprètent comme la variation du coût optimal si on relâche ces contraintes d'une unité supplémentaire.

Pour notre problème, les multiplicateurs extraits :

- C1 (livraison, par pas) : coût marginal interne d'un MWh de consigne [€/MWh].
- C2 (plafond OE, par pas) : valeur marginale d'un MW de capacité supplémentaire.
- C3 (bilan rebond, horizon) : coût marginal d'un MWh de rebond admis.

Cette analyse est locale et conditionnelle à δ* : c'est une analyse de sensibilité au voisinage de la solution optimale, pas une analyse globale.
"""

from dataclasses import dataclass
from typing import List

from pulp import LpMinimize, LpProblem, LpVariable, LpStatus, LpStatusOptimal, PULP_CBC_CMD, lpSum, value

from .data import Consigne, Portfolio

def build_modelLP(
    portfolio: Portfolio,
    consigne: Consigne,
    delta: List[List[int]],
) -> LpProblem:
    """Construit le problème de relaxation LP, obtenu à partir de la solution du MILP de dispatch interne NEBCO.

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
    """
    portfolio.check_against(consigne)

    N, T = portfolio.N, consigne.T
    dt = consigne.delta_t

    prob = LpProblem("NEBCO_Niveau2_LP", LpMinimize)

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


    # ── Fonction objectif ────────────────────────────────────────────────
    prob += (
        lpSum(
            portfolio.clients[c].cout_variable * x[c][t] * dt
            for c in range(N)
            for t in range(T)
        ),
        "Cout_variable_dispatch", 
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
            lpSum(x[c][t] for c in range(N)) <= consigne.P_max_agr,
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

    return prob

@dataclass
class DualSolution:
    """Multiplicateurs duaux de la relaxation LP.

    Attributes
    ----------
    status : str
        Statut PuLP du LP relâché.
    is_optimal : bool
        True ssi le LP a convergé.
    pi_c1 : list of float
        Coût marginal interne par pas [€/MWh]. Multiplicateur de C1.
    pi_c2 : list of float
        Valeur marginale du plafond OE par pas [€/MW]. Multiplicateur de C2.
    pi_c3 : float
        Coût marginal du rebond sur l'horizon. Multiplicateur de C3.
    """
    status: str
    is_optimal: bool
    pi_c1: List[float]
    pi_c2: List[float]
    pi_c3: float


def solveLP(
    prob: LpProblem,
    portfolio: Portfolio,
    consigne: Consigne,
    verbose: bool = False,
) -> DualSolution:
    """Résout le LP relâché avec CBC et extrait les multiplicateurs de Lagrange.

    Parameters
    ----------
    prob : LpProblem
        Le problème construit par build_modelLP.
    portfolio : Portfolio
        Le portefeuille de clients (pour N et les noms des contraintes).
    consigne : Consigne
        La consigne RTE (pour T).
    verbose : bool
        Si True, affiche la sortie du solveur CBC.

    Returns
    -------
    DualSolution
        Les multiplicateurs pi des contraintes principales, ou un objet marqué non-optimal si le LP ne converge pas.
    """
    prob.solve(PULP_CBC_CMD(msg=1 if verbose else 0))

    status_str = LpStatus[prob.status]
    is_optimal = prob.status == LpStatusOptimal

    if not is_optimal:
        return DualSolution(
            status=status_str,
            is_optimal=False,
            pi_c1=[],
            pi_c2=[],
            pi_c3=float("nan"),
        )

    T = consigne.T

    def _pi(constraint_name: str) -> float:
        """Récupère le multiplicateur d'une contrainte, 0.0 si None (presolve)."""
        v = prob.constraints[constraint_name].pi
        return float(v) if v is not None else 0.0

    pi_c1 = [_pi(f"C1_Livraison_t{t}") for t in range(T)]
    pi_c2 = [_pi(f"C2_Plafond_EDE_t{t}") for t in range(T)]
    pi_c3 = _pi("C3_Bilan_EDE_NEBCO")

    return DualSolution(
        status=status_str,
        is_optimal=True,
        pi_c1=pi_c1,
        pi_c2=pi_c2,
        pi_c3=pi_c3,
    )

