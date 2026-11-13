"""Algorithme de Knuth-Morris-Pratt (KMP) pour la recherche d'un facteur.

Un *facteur* est une expression reguliere reduite a la concatenation
(aucun operateur : on cherche une suite exacte de caracteres).
Le cours (lecture 2) montre que la recherche d'un facteur peut se faire en
O(n + m) au lieu de O(n * m), avec n la taille du texte et m celle du facteur.

Vocabulaire du cours : le tableau ``CarryOver`` est la table des reports.
Pour un facteur F de taille m, CarryOver contient m + 1 valeurs :

    F = [m, a, m, i]  ->  CarryOver = [-1, 0, -1, 1, 0]

CarryOver[i] indique, apres un echec de comparaison a la position i du
facteur, a quelle position du facteur on reprend, sans jamais reculer dans
le texte. La valeur -1 signifie : on avance d'un caractere dans le texte et
on repart du debut du facteur. C'est la version optimisee de la table,
celle du cours : on evite de retester une lettre deja connue comme fausse.
"""

from __future__ import annotations

from typing import List


def carry_over(factor: str) -> List[int]:
    """Calcule la table CarryOver (m + 1 valeurs) du facteur, en O(m)."""
    m = len(factor)
    table = [0] * (m + 1)
    table[0] = -1
    pos = 1  # position courante dans le facteur
    cnd = 0  # position du prochain candidat (longueur du bord courant)

    while pos < m:
        if factor[pos] == factor[cnd]:
            # Meme lettre qu'au candidat : un echec ici echouerait aussi
            # au candidat, on reporte donc directement son report.
            table[pos] = table[cnd]
        else:
            table[pos] = cnd
            while cnd >= 0 and factor[pos] != factor[cnd]:
                cnd = table[cnd]
        pos += 1
        cnd += 1

    table[m] = cnd
    return table


def kmp_search(text: str, factor: str) -> List[int]:
    """Retourne toutes les positions (indices dans ``text``) ou ``factor`` apparait.

    Les occurrences qui se chevauchent sont toutes retournees.
    Un facteur vide n'a pas de sens pour une recherche : on retourne [].
    Complexite : O(n + m) comparaisons.
    """
    n, m = len(text), len(factor)
    if m == 0 or m > n:
        return []

    table = carry_over(factor)
    matches: List[int] = []
    i = 0  # position dans le texte
    j = 0  # position dans le facteur

    while i < n:
        if factor[j] == text[i]:
            i += 1
            j += 1
            if j == m:
                matches.append(i - j)
                j = table[j]
        else:
            j = table[j]
            if j < 0:
                i += 1
                j = 0
    return matches


def kmp_contains(text: str, factor: str) -> bool:
    """Vrai si ``factor`` apparait au moins une fois dans ``text``."""
    return len(kmp_search_first(text, factor)) > 0


def kmp_search_first(text: str, factor: str) -> List[int]:
    """Comme ``kmp_search`` mais s'arrete a la premiere occurrence.

    Retourne [position] ou []. Utile pour tester la presence d'un mot
    dans un livre entier sans parcourir tout le texte.
    """
    n, m = len(text), len(factor)
    if m == 0 or m > n:
        return []

    table = carry_over(factor)
    i = 0
    j = 0
    while i < n:
        if factor[j] == text[i]:
            i += 1
            j += 1
            if j == m:
                return [i - j]
        else:
            j = table[j]
            if j < 0:
                i += 1
                j = 0
    return []
