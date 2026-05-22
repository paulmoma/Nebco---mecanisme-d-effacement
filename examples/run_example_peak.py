"""
Scénario "Pointe hivernale" — contrainte C3 active.

Ce scénario montre le cas où le MILP mobilise des clients plus coûteux
(chambre froide, industriel) parce que le mix bon marché seul (chauffe-eau +
résidentiel + VE) produirait un rebond total supérieur à l'effacement,
violant ainsi la contrainte C3 de bilan énergétique NEBCO.

Lancer depuis la racine :
    python -m examples.run_example_peak
"""

from src import Client, Consigne, Portfolio, build_model, print_full_report, solve


def build_peak_portfolio() -> Portfolio:
    """Portefeuille de 6 clients sur une pointe hivernale 16h-19h30."""
    return Portfolio(clients=[
        Client(
            label="Chauffe-eau",
            conso_ref=[2.5, 2.8, 3.2, 3.5, 3.5, 3.2, 2.8, 2.5],
            pmax=    [1.5, 1.8, 2.2, 2.5, 2.5, 2.2, 1.8, 1.5],
            e_min=   [0.1] * 8,
            cout_variable=6.0,
            cout_fixe=[1.5] * 8,
            # Sur-rebond : réchauffage après coupure consomme plus que prévu
            taux_rebond=[1.08, 1.10, 1.12, 1.15, 1.15, 1.12, 1.10, 1.08],
        ),
        Client(
            label="Résidentiel chauffage",
            conso_ref=[5.0, 5.5, 6.5, 7.5, 8.0, 7.5, 6.5, 5.5],
            pmax=    [2.5, 3.0, 3.5, 4.0, 4.0, 3.5, 3.0, 2.5],
            e_min=   [0.3] * 8,
            cout_variable=14.0,
            cout_fixe=[3.0] * 8,
            # Inertie thermique bâtiment : quasi-intégralité du report récupérée
            taux_rebond=[0.92, 0.94, 0.95, 0.97, 0.98, 0.97, 0.95, 0.92],
        ),
        Client(
            label="VE flotte entreprise",
            conso_ref=[2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 1.5, 0.5],
            pmax=    [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.0, 0.3],
            e_min=   [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0],
            cout_variable=16.0,
            cout_fixe=[2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 1.5, 0.5],
            # Énergie reportée tant que les VE sont branchés
            taux_rebond=[1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 0.80, 0.00],
        ),
        Client(
            label="Chambre froide",
            conso_ref=[1.5] * 8,
            pmax=    [0.8] * 8,
            e_min=   [0.15] * 8,
            cout_variable=20.0,
            cout_fixe=[2.5] * 8,
            # Inertie thermique : seulement une partie de l'énergie est récupérée
            taux_rebond=[0.40, 0.42, 0.44, 0.46, 0.48, 0.46, 0.44, 0.42],
        ),
        Client(
            label="Industriel process",
            conso_ref=[4.5, 4.5, 4.0, 4.0, 3.5, 3.5, 2.5, 1.5],
            pmax=    [2.5, 2.5, 2.0, 2.0, 1.5, 1.5, 1.0, 0.5],
            e_min=   [0.5, 0.5, 0.4, 0.4, 0.3, 0.3, 0.2, 0.1],
            cout_variable=28.0,
            cout_fixe=[8.0, 8.0, 7.0, 7.0, 6.0, 6.0, 4.0, 2.0],
            # Production non rattrapée : rebond quasi nul
            taux_rebond=[0.08, 0.08, 0.07, 0.07, 0.06, 0.06, 0.05, 0.04],
        ),
        Client(
            label="Datacenter",
            conso_ref=[3.0] * 8,
            pmax=    [0.8] * 8,
            e_min=   [0.1] * 8,
            cout_variable=40.0,
            cout_fixe=[5.0] * 8,
            # Calcul reporté en nuit : rebond infime
            taux_rebond=[0.02] * 8,
        ),
    ])


def build_peak_consigne() -> Consigne:
    """Consigne RTE pointe hivernale, rampe 16h-18h puis décrue."""
    return Consigne(
        e_retenu=[0.8, 1.2, 2.0, 3.0, 3.8, 3.5, 2.5, 1.5],
        delta_t=0.5,
        P_max_agr=9.0,
        labels_temps=["16h00", "16h30", "17h00", "17h30", "18h00", "18h30", "19h00", "19h30"],
    )


def main() -> None:
    portfolio = build_peak_portfolio()
    consigne = build_peak_consigne()
    prob, variables = build_model(portfolio, consigne)
    solution = solve(prob, variables)
    print_full_report(solution, portfolio, consigne)


if __name__ == "__main__":
    main()
