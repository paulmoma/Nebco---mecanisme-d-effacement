"""
NEBCO Dispatch — optimisation interne d'un agrégateur d'effacement.

Modules exposés :
    data      — dataclasses Client, Consigne, Portfolio
    model     — build_model : construction du MILP
    solver    — solve, check_constraints
    reporting — affichage formaté des résultats
"""

from .data import Client, Consigne, Portfolio
from .model import ModelVariables, build_model
from .reporting import print_full_report
from .solver import Solution, check_constraints, solve

__all__ = [
    "Client",
    "Consigne",
    "Portfolio",
    "ModelVariables",
    "build_model",
    "Solution",
    "solve",
    "check_constraints",
    "print_full_report",
]
