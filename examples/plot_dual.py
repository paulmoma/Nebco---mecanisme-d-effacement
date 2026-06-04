"""
Visualisation des résultats de la relaxation LP — coûts marginaux internes.
"""

import matplotlib.pyplot as plt
import numpy as np

from src.data import Consigne, Portfolio
from src.duality import DualSolution


def plot_marginal_costs(
    dual: DualSolution,
    consigne: Consigne,
    portfolio: Portfolio,
) -> None:
    """Bar chart des coûts marginaux internes pi_c1 par pas de temps."""

    T = consigne.T
    labels = consigne.labels_temps if consigne.labels_temps else [f"t={t}" for t in range(T)]
    x = np.arange(T)

    fig, ax = plt.subplots(figsize=(10, 5))

    bars = ax.bar(x, dual.pi_c1, color="#1A2B3D", alpha=0.85, label=r"$\pi_{C1}$ [€/MWh]")

    couleurs = ["#E89B3C", "#C0392B", "#2980B9", "#27AE60", "#8E44AD", "#7F8C8D"]
    for i, client in enumerate(portfolio.clients):
        ax.axhline(
            client.cout_variable,
            linestyle="--",
            linewidth=0.8,
            color=couleurs[i % len(couleurs)],
            label=f"{client.label} ({client.cout_variable} €/MWh)",
        )

    ax.text(
        0.98, 0.05,
        f"$\\pi_{{C3}}$ = {dual.pi_c3:.2f} €/MWh\n(coût implicite du rebond)",
        transform=ax.transAxes,
        ha="right", va="bottom",
        fontsize=9, color="#C0392B",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#C0392B", alpha=0.8),
    )

    for bar, val in zip(bars, dual.pi_c1):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            f"{val:.2f}",
            ha="center", va="bottom", fontsize=8, color="#1A2B3D",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Pas de temps")
    ax.set_ylabel("Coût marginal [€/MWh]")
    ax.set_title(r"Coût marginal interne $\pi_{C1}$ — relaxation LP à $\delta^*$ fixé")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, max(dual.pi_c1) * 1.25)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig("docs/figures/marginal_costs.png", dpi=150, bbox_inches="tight")
    print("Figure sauvegardée : docs/figures/marginal_costs.png")