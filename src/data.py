"""
Structures de données pour le problème de dispatch NEBCO.

Les dataclasses encapsulent les paramètres du portefeuille et de la consigne
RTE, et vérifient la cohérence dimensionnelle à la construction.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Client:
    """Paramètres d'un client du portefeuille de l'agrégateur.

    Attributes
    ----------
    label : str
        Identifiant lisible du client (ex: "Résidentiel chauffage").
    conso_ref : list of float
        Courbe de Référence NEBCO [MW] — consommation estimée sans effacement.
        Longueur = T (nombre de pas de temps).
    pmax : list of float
        Puissance effaçable maximale [MW]. pmax[t] = 0 → client indisponible.
    e_min : list of float
        Seuil minimal d'effacement si activé [MW]. En dessous de ce seuil,
        l'activation n'a pas de sens physique/contractuel.
    cout_variable : float
        Coût de compensation client [€/MWh], supposé stationnaire en v1.
    cout_fixe : list of float
        Coût fixe d'activation par pas [€]. Couvre télécom, usure, crédit
        de sollicitation.
    taux_rebond : list of float
        Ratio énergie_rebond / énergie_effacée par pas [adim]. ∈ [0, +∞[.
        r > 1 admis par client ; le bilan global est contraint à la maille EDE.
    """

    label: str
    conso_ref: List[float]
    pmax: List[float]
    e_min: List[float]
    cout_variable: float
    cout_fixe: List[float]
    taux_rebond: List[float]

    def __post_init__(self) -> None:
        n = len(self.conso_ref)
        for name, vec in [
            ("pmax", self.pmax),
            ("e_min", self.e_min),
            ("cout_fixe", self.cout_fixe),
            ("taux_rebond", self.taux_rebond),
        ]:
            if len(vec) != n:
                raise ValueError(
                    f"Client '{self.label}' : longueur de {name} "
                    f"({len(vec)}) != conso_ref ({n})"
                )

    def ub(self, t: int) -> float:
        """Borne supérieure effective [MW] : min(pmax, baseline)."""
        return min(self.pmax[t], self.conso_ref[t])


@dataclass(frozen=True)
class Consigne:
    """Programme d'effacement retenu par RTE (output du Niveau 1).

    Attributes
    ----------
    e_retenu : list of float
        Énergie à livrer par pas [MWh]. Longueur = T.
    delta_t : float
        Durée d'un pas [h]. Pas demi-horaire NEBCO → 0.5.
    e_max_agr : float
        Plafond réglementaire NEBCO (art. 5.E.1.3.2.2) [MW].
    labels_temps : list of str
        Étiquettes lisibles pour l'affichage (ex: "18h00").
    """

    e_retenu: List[float]
    delta_t: float = 0.5
    P_max_agr: float = 6.0
    labels_temps: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.labels_temps and len(self.labels_temps) != len(self.e_retenu):
            raise ValueError(
                f"labels_temps ({len(self.labels_temps)}) != "
                f"e_retenu ({len(self.e_retenu)})"
            )

    @property
    def T(self) -> int:
        """Nombre de pas de temps de l'horizon."""
        return len(self.e_retenu)


@dataclass(frozen=True)
class Portfolio:
    """Portefeuille de clients de l'agrégateur."""

    clients: List[Client]

    @property
    def N(self) -> int:
        """Nombre de clients dans le portefeuille."""
        return len(self.clients)

    def check_against(self, consigne: Consigne) -> None:
        """Vérifie la cohérence dimensionnelle portefeuille / consigne."""
        for c in self.clients:
            if len(c.conso_ref) != consigne.T:
                raise ValueError(
                    f"Client '{c.label}' : horizon ({len(c.conso_ref)}) "
                    f"!= consigne ({consigne.T})"
                )
