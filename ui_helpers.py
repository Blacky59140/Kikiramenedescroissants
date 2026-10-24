"""
ui_helpers.py
Petits composants d'interface réutilisés entre plusieurs fenêtres
(boutons pleine largeur façon maquette Stitch, mémorisation de la taille
et de la position des fenêtres entre deux lancements de l'application).
"""

import tkinter as tk

from theme import COULEUR_BORDURE
from data_manager import obtenir_geometrie_fenetre, sauvegarder_geometrie_fenetre


def bouton_pleine_largeur(parent, texte, commande, bg, fg, avec_bordure=False):
    """Crée un bouton pleine largeur façon maquette (Frame cliquable ; pas de coins arrondis natifs en Tkinter)."""
    conteneur = tk.Frame(
        parent, bg=bg, cursor="hand2",
        highlightbackground=COULEUR_BORDURE if avec_bordure else bg,
        highlightthickness=1 if avec_bordure else 0,
    )
    conteneur.pack(fill="x", pady=(0, 10))

    label = tk.Label(conteneur, text=texte, font=("Segoe UI", 10, "bold"), bg=bg, fg=fg)
    label.pack(pady=10)

    for widget in (conteneur, label):
        widget.bind("<Button-1>", lambda e: commande())

    return conteneur


def appliquer_geometrie_sauvegardee(fenetre, nom_fenetre, largeur_defaut, hauteur_defaut):
    """
    Positionne/dimensionne `fenetre` selon ce qui a été enregistré la
    dernière fois qu'elle a été fermée (identifiée par `nom_fenetre`), ou
    utilise la taille par défaut (sans position particulière, laissée au
    système) si rien n'a encore été sauvegardé.
    Si la position enregistrée tombe hors de l'écran actuel (ex : moniteur
    externe débranché depuis), elle est ignorée par sécurité.
    """
    geometrie = obtenir_geometrie_fenetre(nom_fenetre)

    if not geometrie:
        fenetre.geometry(f"{largeur_defaut}x{hauteur_defaut}")
        return

    largeur, hauteur, x, y = geometrie

    fenetre.update_idletasks()
    largeur_ecran = fenetre.winfo_screenwidth()
    hauteur_ecran = fenetre.winfo_screenheight()

    position_valide = (
        -50 <= x < largeur_ecran - 50 and -50 <= y < hauteur_ecran - 50
    )

    if position_valide:
        fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")
    else:
        fenetre.geometry(f"{largeur}x{hauteur}")


def sauvegarder_geometrie_actuelle(fenetre, nom_fenetre):
    """Sauvegarde la taille et la position actuelles de `fenetre`. À appeler juste avant sa fermeture."""
    try:
        sauvegarder_geometrie_fenetre(
            nom_fenetre, fenetre.winfo_width(), fenetre.winfo_height(), fenetre.winfo_x(), fenetre.winfo_y()
        )
    except tk.TclError:
        pass  # la fenêtre est peut-être déjà en cours de destruction
