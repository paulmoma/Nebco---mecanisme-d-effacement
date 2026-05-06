"""
Exemple : dispatch NEBCO sur un portefeuille de 4 clients, 6 pas demi-horaires.

Reproduit le scénario du prototype initial (pointe de soirée 18h-20h30).
Lancer depuis la racine du projet :

    python -m examples.run_example
"""

from src import (
    Client,
    Consigne,
    Portfolio,
    build_model,
    print_full_report,
    solve,
)


def build_example_portfolio() -> Portfolio:
    """Portefeuille de 4 clients typés : résidentiel, industriel, ECS, VE."""
    clients = [
        Client(
            label="Résidentiel chauffage",
            conso_ref=[2.0, 1.8, 2.2, 2.0, 1.5, 1.2],
            pmax=[1.0, 1.0, 1.0, 1.0, 1.0, 0.8],
            e_min=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            cout_variable=15.0,
            cout_fixe=[2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
            # Inertie bâtiment : rebond modéré croissant avec la profondeur
            taux_rebond=[0.70, 0.75, 0.80, 0.85, 0.70, 0.60],
        ),
        Client(
            label="Industriel process",
            conso_ref=[3.5, 3.5, 3.0, 2.0, 1.0, 0.5],
            pmax=[2.0, 2.0, 1.5, 1.0, 0.0, 0.0],  # fin de poste à 19h30
            e_min=[0.5, 0.5, 0.5, 0.3, 0.0, 0.0],
            cout_variable=25.0,
            cout_fixe=[5.0, 5.0, 5.0, 4.0, 0.0, 0.0],
            # Process peu rattrapé (production non reprise)
            taux_rebond=[0.20, 0.20, 0.15, 0.10, 0.00, 0.00],
        ),
        Client(
            label="Chauffe-eau",
            conso_ref=[0.6, 0.6, 0.5, 0.4, 0.3, 0.4],
            pmax=[0.5, 0.5, 0.4, 0.3, 0.2, 0.3],
            e_min=[0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
            cout_variable=8.0,
            cout_fixe=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            # r > 1 en profond : réchauffage moins efficace après coupure longue
            taux_rebond=[0.95, 1.00, 1.10, 1.20, 1.15, 1.00],
        ),
        Client(
            label="VE recharge",
            conso_ref=[1.0, 1.0, 1.0, 0.8, 0.5, 0.3],
            pmax=[1.0, 1.0, 0.8, 0.5, 0.0, 0.0],  # déconnexion après 19h30
            e_min=[0.2, 0.2, 0.2, 0.1, 0.0, 0.0],
            cout_variable=12.0,
            cout_fixe=[2.5, 2.5, 2.5, 2.0, 0.0, 0.0],
            # Énergie intégralement reportée tant que le VE est branché
            taux_rebond=[1.00, 1.00, 1.00, 1.00, 0.00, 0.00],
        ),
    ]
    return Portfolio(clients=clients)


def build_example_consigne() -> Consigne:
    """Consigne RTE typique de pointe de soirée.

    Note : e_retenu décroît en fin d'horizon pour rester compatible avec le
    gisement disponible (industriel et VE indisponibles après 19h30). Dans
    la v1, C1 étant en égalité stricte, une consigne supérieure au gisement
    total rendrait le problème infaisable. C'est l'une des limites discutées
    dans le README et traitée par la v1.1.
    """
    return Consigne(
        e_retenu=[1.0, 1.2, 1.5, 1.0, 0.5, 0.4],
        delta_t=0.5,
        P_max_agr=6.0,
        labels_temps=["18h00", "18h30", "19h00", "19h30", "20h00", "20h30"],
    )


def main() -> None:
    portfolio = build_example_portfolio()
    consigne = build_example_consigne()

    prob, variables = build_model(portfolio, consigne)
    solution = solve(prob, variables)

    print_full_report(solution, portfolio, consigne)


if __name__ == "__main__":
    main()
