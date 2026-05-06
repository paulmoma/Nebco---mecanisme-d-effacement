"""
Affichage formaté des résultats du dispatch NEBCO.
"""

from .data import Consigne, Portfolio
from .solver import Solution, check_constraints

SEP = "═" * 76


def print_header(solution: Solution) -> None:
    """En-tête avec statut et coût total."""
    print(SEP)
    print("  DISPATCH INTERNE NEBCO — MILP NIVEAU 2")
    print(SEP)
    print(f"  Statut     : {solution.status}")
    if not solution.is_optimal:
        print("  ⚠ Problème infaisable ou non borné — vérifier les données.")
        return
    print(f"  Coût total : {solution.cost_total:.2f} €")
    print()


def print_dispatch(
    solution: Solution,
    portfolio: Portfolio,
    consigne: Consigne,
) -> None:
    """Tableau du dispatch pas par pas, client par client."""
    if not solution.is_optimal:
        return

    N, T, dt = portfolio.N, consigne.T, consigne.delta_t
    W = 9  # largeur colonne client
    labels_t = consigne.labels_temps or [f"t={t}" for t in range(T)]

    print("DISPATCH PAR PAS [MW effacé par client]")
    print("-" * (32 + (W + 2) * N))

    header = f"  {'Heure':<8} {'Consigne':>9} {'Livré':>7} │"
    for c in range(N):
        header += f" {portfolio.clients[c].label[:W]:>{W}}"
    print(header)
    print("-" * len(header))

    for t in range(T):
        livraison = sum(solution.x[c][t] * dt for c in range(N))
        ecart = livraison - consigne.e_retenu[t]
        alert = f" ({'+' if ecart >= 0 else ''}{ecart:.3f})"

        ligne = (
            f"  {labels_t[t]:<8} {consigne.e_retenu[t]:>8.2f}  "
            f"{livraison:>6.3f} │"
        )
        for c in range(N):
            v = solution.x[c][t]
            flag = "*" if solution.delta[c][t] == 1 else " "
            ligne += f" {v:>{W-1}.3f}{flag}"
        print(ligne + alert)

    print("  (* = client activé, delta=1)")
    print()


def print_bilan(
    solution: Solution,
    portfolio: Portfolio,
    consigne: Consigne,
) -> None:
    """Bilan par client sur l'horizon : énergie, rebond, coûts."""
    if not solution.is_optimal:
        return

    N, T, dt = portfolio.N, consigne.T, consigne.delta_t

    print("BILAN PAR CLIENT SUR L'HORIZON")
    print("-" * 90)
    print(
        f"  {'Client':<24} {'Activations':>11} {'E effacée':>10} "
        f"{'r effectif':>11} {'E rebond':>10} "
        f"{'Coût var.':>10} {'Coût fixe':>10} {'Total':>8}"
    )
    print("-" * 90)

    total_eff = total_reb = total_cv = total_cf = 0.0

    for c in range(N):
        client = portfolio.clients[c]
        activations = sum(solution.delta[c][t] for t in range(T))
        e_t = [solution.x[c][t] * dt for t in range(T)]
        e_eff = sum(e_t)
        e_reb = sum(client.taux_rebond[t] * e_t[t] for t in range(T))
        r_eff = e_reb / e_eff if e_eff > 1e-6 else 0.0
        cout_var = client.cout_variable * e_eff
        cout_fixe = sum(
            client.cout_fixe[t] * solution.delta[c][t] for t in range(T)
        )
        cout_total = cout_var + cout_fixe

        total_eff += e_eff
        total_reb += e_reb
        total_cv += cout_var
        total_cf += cout_fixe

        flag = " ▶r>1" if r_eff > 1.0 + 1e-4 else ""
        print(
            f"  {client.label:<24} {activations:>9} /T  "
            f"{e_eff:>8.3f} MWh  {r_eff:>9.2f}x  "
            f"{e_reb:>8.3f} MWh  "
            f"{cout_var:>8.2f} €  {cout_fixe:>8.2f} €  "
            f"{cout_total:>6.2f} €{flag}"
        )

    r_global = total_reb / total_eff if total_eff > 1e-6 else 0.0
    print("-" * 90)
    print(
        f"  {'TOTAL EDE':<24} {'':>11}  "
        f"{total_eff:>8.3f} MWh  {r_global:>9.2f}x  "
        f"{total_reb:>8.3f} MWh  "
        f"{total_cv:>8.2f} €  {total_cf:>8.2f} €  "
        f"{total_cv+total_cf:>6.2f} €"
    )
    print()


def print_constraints_check(
    solution: Solution,
    portfolio: Portfolio,
    consigne: Consigne,
) -> None:
    """Vérification a posteriori des contraintes C1, C2, C3."""
    if not solution.is_optimal:
        return

    checks = check_constraints(solution, portfolio, consigne)
    labels_t = consigne.labels_temps or [f"t={t}" for t in range(consigne.T)]

    print("VÉRIFICATION DES CONTRAINTES")
    print("-" * 55)

    print("  C1 — Livraison RTE par pas :")
    for t in range(consigne.T):
        livraison = sum(solution.x[c][t] * consigne.delta_t for c in range(portfolio.N))
        ok = abs(livraison - consigne.e_retenu[t]) < 1e-4
        status = "✓" if ok else "✗"
        print(
            f"    t={labels_t[t]} : {livraison:.3f} / "
            f"{consigne.e_retenu[t]:.3f} MWh  {status}"
        )

    print("  C2 — Plafond agrégateur par pas :")
    for t, p in enumerate(checks["C2"]["puissances"]):
        ok = p <= consigne.P_max_agr + 1e-4
        status = "✓" if ok else "✗"
        print(
            f"    t={labels_t[t]} : {p:.3f} / {consigne.P_max_agr:.1f} MW  {status}"
        )

    c3 = checks["C3"]
    status = "✓ CONFORME" if c3["ok"] else "✗ NON CONFORME"
    print("  C3 — Bilan EDE NEBCO :")
    print(f"    Rebond total  : {c3['total_rebond']:.3f} MWh")
    print(f"    Effacement    : {c3['total_effacement']:.3f} MWh")
    print(f"    Ratio global  : {c3['ratio']:.3f}  {status}")
    print("    (r > 1 admis par client, contrôlé à la maille EDE)")
    print()


def print_roadmap() -> None:
    """Rappel des extensions prévues (cohérent avec le README)."""
    print(SEP)
    print("  EXTENSIONS FUTURES")
    print(SEP)
    print("  v1.1 → Sous-livraison : slack pénalisé dans C1")
    print("  v1.2 → Min up/down time et nombre max d'activations par client")
    print("  v1.3 → Dual de la relaxation LP : analyse économique")
    print("  v2.0 → Rebond explicite : variables y[c][t] + matrice R_c[τ]")
    print("  v2.1 → Stochastique : pmax incertain → SAA sur scénarios")
    print("  v3.0 → Rolling horizon : redéclaration intraday (NF5 NEBCO)")


def print_full_report(
    solution: Solution,
    portfolio: Portfolio,
    consigne: Consigne,
) -> None:
    """Rapport complet : header + dispatch + bilan + vérifications + roadmap."""
    print_header(solution)
    if not solution.is_optimal:
        return
    print_dispatch(solution, portfolio, consigne)
    print_bilan(solution, portfolio, consigne)
    print_constraints_check(solution, portfolio, consigne)
    print_roadmap()
