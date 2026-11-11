"""
engine.py — Adaptateur vers le moteur d'expressions régulières.

L'API n'appelle QUE build_matcher(pattern), qui renvoie une fonction
    mot -> True / False   (le mot entier vérifie-t-il la RegEx ?)

Version actuelle : module 're' de Python, en attendant le branchement
de l'automate du Projet 1 (RegEx -> arbre syntaxique -> NFA -> DFA ->
minimisation, méthode Aho-Ullman).

TODO : remplacer le corps de build_matcher par l'automate du Projet 1.
       Le reste de l'API n'a pas à changer.
"""
import re


def build_matcher(pattern: str):
    """Compile la RegEx une seule fois, renvoie une fonction de test.
    Lève ValueError si la RegEx est invalide."""
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        raise ValueError(str(e)) from e
    return lambda word: compiled.fullmatch(word) is not None
