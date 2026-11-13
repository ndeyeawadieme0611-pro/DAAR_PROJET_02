"""
engine.py — Adaptateur vers le moteur d'expressions régulières.

L'API n'appelle QUE build_matcher(pattern), qui renvoie une fonction
    mot -> True / False   (le mot entier vérifie-t-il la RegEx ?)

Moteur : automate du Projet 1
    RegEx -> arbre syntaxique -> NFA -> DFA -> DFA minimal (Moore).
Syntaxe : lettre, '.', concaténation, '|', '*', '+', parenthèses.
"""
from .parser import parse
from .nfa import arbre_vers_nfa
from .dfa import construire_dfa, accepte_dfa
from .minimize import minimiser


def build_matcher(pattern: str):
    """Compile la RegEx une seule fois, renvoie une fonction de test.
    Lève ValueError si la RegEx est invalide."""
    dfa = minimiser(construire_dfa(arbre_vers_nfa(parse(pattern))))
    return lambda word: accepte_dfa(dfa, word)
