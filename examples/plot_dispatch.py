"""
Visualisation du dispatch NEBCO — scénario "Pointe hivernale".

Génère trois figures :
  - dispatch_peak.png      : dispatch empilé par client
  - cost_vs_rebound.png    : arbitrage coût / rebond (scatter)
  - profile_client.png     : profil d'effacement d'un client (chauffe-eau)

Lancer depuis la racine :
    python -m examples.plot_dispatch
"""

import matplotlib.pyplot as plt
import numpy as np

from examples.run_example_peak import build_peak_consigne, build_peak_portfolio
from src import build_model, solve

COLORS = ["#E07B39", "#C0392B", "#2980B9", "#27AE60", "#8E44AD", "#7F8C8D"]
STYLE = "seaborn-v0_8-whitegrid"


def _solve():
    portfolio = build_peak_portfolio()
    consigne = build_peak_consigne()
    prob, variables = build_model(portfolio, consigne)
    solution = solve(prob, variables)
    return portfolio, consigne, solution


def _energy_stats(portfolio, consigne, solution):
    N, T, dt = portfolio.N, consigne.T, consigne.delta_t
    clients, x_val = portfolio.clients, solution.x
    e_eff = [sum(x_val[c][t] * dt for t in range(T)) for c in range(N)]
    e_reb = [sum(clients[c].taux_rebond[t] * x_val[c][t] * dt for t in range(T)) for c in range(N)]
    r_moy = [e_reb[c] / e_eff[c] if e_eff[c] > 1e-6 else 0.0 for c in range(N)]
    return e_eff, e_reb, r_moy


def plot_dispatch(output_path: str = "dispatch_peak.png") -> None:
    """Dispatch empilé par client avec consigne RTE."""
    portfolio, consigne, solution = _solve()

    N, T, dt = portfolio.N, consigne.T, consigne.delta_t
    labels, clients, x_val = consigne.labels_temps, portfolio.clients, solution.x
    e_eff, _, _ = _energy_stats(portfolio, consigne, solution)

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
        x_pos = np.arange(T)
        bar_w = 0.6

        bottom = np.zeros(T)
        for c in range(N):
            vals = np.array([x_val[c][t] for t in range(T)])
            if vals.max() < 1e-6:
                continue
            ax.bar(x_pos, vals, bottom=bottom, width=bar_w,
                   color=COLORS[c], label=clients[c].label, alpha=0.88, zorder=3)
            bottom += vals

        consigne_mw = np.array([e / dt for e in consigne.e_retenu])
        ax.step(x_pos, consigne_mw, where="mid",
                color="black", linewidth=2.2, linestyle="--", label="Consigne RTE", zorder=5)
        ax.hlines(consigne_mw[0],  -bar_w / 2, 0,             colors="black", linewidth=2.2, linestyle="--", zorder=5)
        ax.hlines(consigne_mw[-1], T - 1, T - 1 + bar_w / 2, colors="black", linewidth=2.2, linestyle="--", zorder=5)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=9)
        ax.set_ylabel("Puissance effacée [MW]", fontsize=10)
        ax.set_xlabel("Pas de temps", fontsize=10)
        ax.set_title("Dispatch NEBCO — pointe hivernale", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
        ax.set_xlim(-0.6, T - 0.4)
        ax.set_ylim(bottom=0)

        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Figure sauvegardée : {output_path}")
        plt.close()


def plot_cost_vs_rebound(output_path: str = "cost_vs_rebound.png") -> None:
    """Scatter coût variable vs taux de rebond moyen. Taille des bulles = énergie effacée."""
    portfolio, consigne, solution = _solve()

    N = portfolio.N
    clients = portfolio.clients
    e_eff, e_reb, r_moy = _energy_stats(portfolio, consigne, solution)
    total_eff = sum(e_eff)
    total_reb = sum(e_reb)

    # Échelle des bulles : on cale sur e_eff max → surface 600 pt²
    e_max = max(e for e in e_eff if e > 1e-6)
    S_MAX = 600.0

    label_offsets = {
        "Chauffe-eau":           ( 0.03,  3.5,  "left"),
        "Résidentiel chauffage": (-0.06,  3.5,  "right"),
        "VE flotte entreprise":  ( 0.03,  3.0,  "left"),
        "Chambre froide":        ( 0.03,  0.0,  "left"),
        "Industriel process":    ( 0.03,  0.0,  "left"),
        "Datacenter":            ( 0.03,  0.0,  "left"),
    }

    XLIM, YLIM = (0.0, 1.50), (0, 50)

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)

        # Zone r > 1
        ax.axvspan(1.0, XLIM[1], alpha=0.07, color="red", zorder=0)
        ax.axvline(1.0, color="red", linewidth=1.2, linestyle="--", alpha=0.6, zorder=2)
        ax.text(1.02, YLIM[1] * 0.96, "r > 1\n(C3 en danger)", fontsize=9,
                color="firebrick", va="top")

        for c in range(N):
            lbl = clients[c].label
            dx, dy, ha = label_offsets.get(lbl, (0.02, 0.0, "left"))
            if e_eff[c] < 1e-6:
                r_d = float(np.mean(clients[c].taux_rebond))
                ax.scatter(r_d, clients[c].cout_variable, s=55,
                           color="lightgray", edgecolors="gray", linewidth=0.8,
                           zorder=3, alpha=0.7)
                ax.scatter(r_d, clients[c].cout_variable, s=55,
                           color="gray", linewidth=1.4,
                           marker="x", zorder=4, alpha=0.9)
                ax.text(r_d + dx, clients[c].cout_variable + dy,
                        lbl, fontsize=9, color="gray", va="center", ha=ha)
            else:
                s = S_MAX * (e_eff[c] / e_max)
                ax.scatter(r_moy[c], clients[c].cout_variable,
                           s=s, color=COLORS[c],
                           edgecolors="white", linewidth=1.2, zorder=4, alpha=0.9)
                ax.text(r_moy[c] + dx, clients[c].cout_variable + dy,
                        lbl, fontsize=9, color="black", va="center", ha=ha)

        # Annotation chambre froide
        cf = next(c for c in range(N) if "Chambre" in clients[c].label)
        ax.annotate(
            "Activée malgré le coût\npour compenser le rebond\n(C3 saturée à 1.000)",
            xy=(r_moy[cf], clients[cf].cout_variable),
            xytext=(0.12, 35), fontsize=9, color=COLORS[cf],
            arrowprops=dict(arrowstyle="->", color=COLORS[cf], lw=1.3),
        )

        # Encart bilan C3
        ratio = total_reb / total_eff if total_eff > 0 else 0.0
        statut = "CONFORME" if ratio <= 1.0 else "NON CONFORME"
        col_c3 = "#27AE60" if ratio <= 1.0 else "#C0392B"
        ax.text(0.03, 0.97,
                f"C3 (bilan énergétique EDE) :\n"
                f"rebond = effacement = {total_eff:.1f} MWh\n"
                f"r = {ratio:.3f}  →  {statut}",
                transform=ax.transAxes, fontsize=9, ha="left", va="top",
                color=col_c3, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                          edgecolor=col_c3, alpha=0.9))

        # Légende d'échelle des bulles
        ref_sizes = [1.0, 4.0, 8.0]
        legend_handles = [
            plt.scatter([], [], s=S_MAX * (v / e_max), color="silver",
                        edgecolors="gray", linewidth=0.8, alpha=0.9,
                        label=f"{v:.0f} MWh")
            for v in ref_sizes
        ]
        leg = ax.legend(handles=legend_handles, title="Énergie effacée",
                        loc="lower right", fontsize=8.5, title_fontsize=8.5,
                        framealpha=0.9, labelspacing=1.2)
        ax.add_artist(leg)

        ax.set_xlabel("Taux de rebond moyen (r) [adim.]", fontsize=11)
        ax.set_ylabel("Coût variable [€/MWh]", fontsize=11)
        ax.set_title("Arbitrage coût / rebond — pointe hivernale", fontsize=12, fontweight="bold")
        ax.set_xlim(XLIM)
        ax.set_ylim(YLIM)

        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Figure sauvegardée : {output_path}")
        plt.close()


def plot_client_profile(c_focus: int = 0, output_path: str = "profile_client.png") -> None:
    """Profil d'effacement d'un client sur l'horizon."""
    portfolio, consigne, solution = _solve()

    T, dt = consigne.T, consigne.delta_t
    labels, clients, x_val = consigne.labels_temps, portfolio.clients, solution.x
    e_eff, e_reb, r_moy = _energy_stats(portfolio, consigne, solution)

    client = clients[c_focus]
    color  = COLORS[c_focus]
    x_pos  = np.arange(T)
    bar_w  = 0.6

    baseline   = list(client.conso_ref)
    effacement = [x_val[c_focus][t] for t in range(T)]
    pmax_eff   = [client.ub(t) for t in range(T)]
    emin_val   = list(client.e_min)

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)

        ax.bar(x_pos, baseline, width=bar_w, color="lightgray", alpha=0.6,
               label="Baseline (conso_ref)", zorder=2)
        ax.bar(x_pos, effacement, width=bar_w, color=color, alpha=0.88,
               label="Effacement x[c,t]", zorder=3)

        ax.step(x_pos, pmax_eff, where="mid",
                color="navy", linewidth=1.8, linestyle=":", zorder=5, label="pmax — borne supérieure")
        ax.step(x_pos, emin_val, where="mid",
                color="gray", linewidth=1.4, linestyle="-.", zorder=5, label="e_min — seuil d'activation")

        for val, x_start, x_end in [(pmax_eff[0], -bar_w/2, 0), (pmax_eff[-1], T-1, T-1+bar_w/2)]:
            ax.hlines(val, x_start, x_end, colors="navy", linewidth=1.8, linestyle=":", zorder=5)
        for val, x_start, x_end in [(emin_val[0], -bar_w/2, 0), (emin_val[-1], T-1, T-1+bar_w/2)]:
            ax.hlines(val, x_start, x_end, colors="gray", linewidth=1.4, linestyle="-.", zorder=5)

        ax.text(0.97, 0.97,
                f"r moyen = {r_moy[c_focus]:.2f}  (r > 1)\n"
                "Rebond > effacement sur ce client seul.\n"
                "Le bilan C3 est contrôlé à la maille EDE,\n"
                "pas au niveau individuel.",
                transform=ax.transAxes, fontsize=8.5, ha="right", va="top",
                color="firebrick", style="italic",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="firebrick", alpha=0.85))

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=9)
        ax.set_ylabel("Puissance [MW]", fontsize=10)
        ax.set_xlabel("Pas de temps", fontsize=10)
        n_act = sum(1 for t in range(T) if solution.delta[c_focus][t])
        cout_var = e_eff[c_focus] * client.cout_variable
        cout_fix = sum(client.cout_fixe[t] for t in range(T) if solution.delta[c_focus][t])
        ax.set_title(f"Profil d'effacement — {client.label}", fontsize=11, fontweight="bold")
        ax.text(0.01, 0.03,
                f"Activé {n_act}/{T} pas  |  E effacée = {e_eff[c_focus]:.2f} MWh  |  "
                f"Coût = {client.cout_variable:.0f} €/MWh × {e_eff[c_focus]:.2f} MWh = {cout_var:.0f} €  +  {cout_fix:.0f} € fixe",
                transform=ax.transAxes, fontsize=8, color="dimgray", va="bottom")
        ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
        ax.set_xlim(-0.6, T - 0.4)
        ax.set_ylim(bottom=0)

        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Figure sauvegardée : {output_path}")
        plt.close()


if __name__ == "__main__":
    plot_dispatch()
    plot_cost_vs_rebound()
    plot_client_profile(c_focus=0)
