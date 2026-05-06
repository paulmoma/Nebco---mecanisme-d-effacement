"""
Résolution du MILP et extraction de la solution sous forme exploitable.
"""

from dataclasses import dataclass
from typing import List

from pulp import LpProblem, LpStatus, LpStatusOptimal, PULP_CBC_CMD, value

from .data import Consigne, Portfolio
from .model import ModelVariables


@dataclass
class Solution:
    """Solution numérique du problème de dispatch.

    Attributes
    ----------
    status : str
        Statut PuLP ("Optimal", "Infeasible", ...).
    is_optimal : bool
        True ssi le solveur a trouvé l'optimum.
    cost_total : float
        Valeur de la fonction objectif [€].
    x : list of list of float
        Puissance effacée [MW], x[c][t].
    delta : list of list of int
        Activations binaires, delta[c][t] ∈ {0, 1}.
    """

    status: str
    is_optimal: bool
    cost_total: float
    x: List[List[float]]
    delta: List[List[int]]


def solve(
    prob: LpProblem,
    variables: ModelVariables,
    verbose: bool = False,
) -> Solution:
    """Résout le MILP avec CBC et extrait la solution.

    Parameters
    ----------
    prob : LpProblem
        Le problème construit par build_model.
    variables : ModelVariables
        Les variables retournées par build_model.
    verbose : bool
        Si True, affiche la sortie du solveur CBC.

    Returns
    -------
    Solution
        Les valeurs numériques de l'optimum, ou un objet marqué non-optimal.
    """
    prob.solve(PULP_CBC_CMD(msg=1 if verbose else 0))

    status_str = LpStatus[prob.status]
    is_optimal = prob.status == LpStatusOptimal

    if not is_optimal:
        return Solution(
            status=status_str,
            is_optimal=False,
            cost_total=float("nan"),
            x=[],
            delta=[],
        )

    N = len(variables.x)
    T = len(variables.x[0]) if N > 0 else 0

    def _val(var) -> float:
        """Récupère la valeur d'une variable, 0.0 si None (presolve CBC)."""
        v = value(var)
        return float(v) if v is not None else 0.0

    x_val = [[_val(variables.x[c][t]) for t in range(T)] for c in range(N)]
    delta_val = [
        [int(round(_val(variables.delta[c][t]))) for t in range(T)]
        for c in range(N)
    ]

    return Solution(
        status=status_str,
        is_optimal=True,
        cost_total=float(value(prob.objective)),
        x=x_val,
        delta=delta_val,
    )


def check_constraints(
    solution: Solution,
    portfolio: Portfolio,
    consigne: Consigne,
    tol: float = 1e-4,
) -> dict:
    """Vérification a posteriori des contraintes principales.

    Retourne un dict récapitulatif utile pour le reporting et les tests.
    """
    N, T, dt = portfolio.N, consigne.T, consigne.delta_t

    # C1 — livraison par pas
    c1_ecarts = [
        sum(solution.x[c][t] * dt for c in range(N)) - consigne.e_retenu[t]
        for t in range(T)
    ]
    c1_ok = all(abs(e) < tol for e in c1_ecarts)

    # C2 — plafond par pas
    c2_puissances = [sum(solution.x[c][t] for c in range(N)) for t in range(T)]
    c2_ok = all(p <= consigne.P_max_agr + tol for p in c2_puissances)

    # C3 — bilan EDE
    total_eff = sum(
        solution.x[c][t] * dt for c in range(N) for t in range(T)
    )
    total_reb = sum(
        portfolio.clients[c].taux_rebond[t] * solution.x[c][t] * dt
        for c in range(N)
        for t in range(T)
    )
    c3_ok = total_reb <= total_eff + tol

    return {
        "C1": {"ok": c1_ok, "ecarts": c1_ecarts},
        "C2": {"ok": c2_ok, "puissances": c2_puissances},
        "C3": {
            "ok": c3_ok,
            "total_effacement": total_eff,
            "total_rebond": total_reb,
            "ratio": total_reb / total_eff if total_eff > tol else 0.0,
        },
    }
