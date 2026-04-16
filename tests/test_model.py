"""
Tests basiques du modèle MILP.

Lancer :
    pytest tests/
ou
    python -m unittest tests.test_model
"""

import unittest

from examples.run_example import build_example_consigne, build_example_portfolio
from src import Client, Consigne, Portfolio, build_model, check_constraints, solve


class TestDataValidation(unittest.TestCase):
    """Vérification des contrôles de cohérence dans les dataclasses."""

    def test_client_rejects_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            Client(
                label="Bad",
                conso_ref=[1.0, 1.0, 1.0],
                pmax=[1.0, 1.0],  # longueur différente
                e_min=[0.1, 0.1, 0.1],
                cout_variable=10.0,
                cout_fixe=[1.0, 1.0, 1.0],
                taux_rebond=[0.5, 0.5, 0.5],
            )

    def test_portfolio_rejects_inconsistent_horizon(self):
        client = Client(
            label="A",
            conso_ref=[1.0, 1.0],
            pmax=[1.0, 1.0],
            e_min=[0.1, 0.1],
            cout_variable=10.0,
            cout_fixe=[1.0, 1.0],
            taux_rebond=[0.5, 0.5],
        )
        consigne = Consigne(e_retenu=[0.5, 0.5, 0.5])  # horizon 3
        with self.assertRaises(ValueError):
            Portfolio(clients=[client]).check_against(consigne)


class TestExampleScenario(unittest.TestCase):
    """Tests d'intégration sur le scénario de référence."""

    @classmethod
    def setUpClass(cls):
        cls.portfolio = build_example_portfolio()
        cls.consigne = build_example_consigne()
        prob, variables = build_model(cls.portfolio, cls.consigne)
        cls.solution = solve(prob, variables)

    def test_solver_finds_optimum(self):
        self.assertTrue(self.solution.is_optimal)

    def test_c1_delivery_exact(self):
        checks = check_constraints(self.solution, self.portfolio, self.consigne)
        self.assertTrue(checks["C1"]["ok"])

    def test_c2_plafond_respected(self):
        checks = check_constraints(self.solution, self.portfolio, self.consigne)
        self.assertTrue(checks["C2"]["ok"])

    def test_c3_ede_balance(self):
        checks = check_constraints(self.solution, self.portfolio, self.consigne)
        self.assertTrue(checks["C3"]["ok"])

    def test_variables_respect_bounds(self):
        """x[c][t] ∈ [0, ub] et δ ∈ {0,1}."""
        for c, client in enumerate(self.portfolio.clients):
            for t in range(self.consigne.T):
                self.assertGreaterEqual(self.solution.x[c][t], -1e-6)
                self.assertLessEqual(self.solution.x[c][t], client.ub(t) + 1e-6)
                self.assertIn(self.solution.delta[c][t], (0, 1))

    def test_activation_coupling(self):
        """δ = 0 ⟹ x ≈ 0."""
        for c in range(self.portfolio.N):
            for t in range(self.consigne.T):
                if self.solution.delta[c][t] == 0:
                    self.assertLess(self.solution.x[c][t], 1e-6)


if __name__ == "__main__":
    unittest.main()
