"""
Fenêtre de gestion des dates bloquées : sur ces dates, il est impossible
de créer ou de déplacer un événement.
"""

import tkinter as tk
from tkinter import messagebox

from data_manager import (
    analyser_saisie_dates_bloquees,
    ajouter_dates_bloquees,
    charger_dates_bloquees,
    supprimer_date_bloquee,
)
from ui_helpers import bouton_pleine_largeur, appliquer_geometrie_sauvegardee, sauvegarder_geometrie_actuelle
from theme import (
    COULEUR_FOND,
    COULEUR_BORDURE,
    COULEUR_TEXTE_PRINCIPAL,
    COULEUR_TEXTE_SECONDAIRE,
    COULEUR_ACCENT_TITRE,
    COULEUR_ALERTE,
    COULEUR_BOUTON_PRINCIPAL_BG,
    COULEUR_BOUTON_PRINCIPAL_FG,
    COULEUR_BOUTON_SECONDAIRE_BG,
    COULEUR_BOUTON_SECONDAIRE_FG,
)


def _format_fr(iso):
    annee, mois, jour = iso.split("-")
    return f"{jour}/{mois}/{annee}"


def _libelle_blocage(b):
    if b["debut"] == b["fin"]:
        return _format_fr(b["debut"])
    return f"du {_format_fr(b['debut'])} au {_format_fr(b['fin'])}"


def ouvrir_fenetre_dates_bloquees(parent, callback_rafraichir):
    fenetre = tk.Toplevel(parent)
    fenetre.title("Dates bloquées")
    appliquer_geometrie_sauvegardee(fenetre, "dates_bloquees", 460, 640)
    fenetre.configure(bg=COULEUR_FOND)
    fenetre.transient(parent)
    fenetre.grab_set()

    def fermer():
        sauvegarder_geometrie_actuelle(fenetre, "dates_bloquees")
        fenetre.destroy()

    fenetre.protocol("WM_DELETE_WINDOW", fermer)

    # --- En-tête ---
    entete = tk.Frame(fenetre, bg="white", height=50)
    entete.pack(fill="x", side="top")
    entete.pack_propagate(False)
    fleche = tk.Label(entete, text="←", font=("Segoe UI", 16, "bold"), bg="white",
                      fg=COULEUR_TEXTE_PRINCIPAL, cursor="hand2")
    fleche.pack(side="left", padx=15)
    fleche.bind("<Button-1>", lambda e: fermer())
    tk.Label(entete, text="Dates bloquées", font=("Segoe UI", 12, "bold"),
             bg="white", fg=COULEUR_ACCENT_TITRE).pack(side="left")
    tk.Frame(fenetre, bg=COULEUR_BORDURE, height=1).pack(fill="x", side="top")

    corps = tk.Frame(fenetre, bg="white", padx=20, pady=15,
                     highlightbackground=COULEUR_BORDURE, highlightthickness=1)
    corps.pack(fill="both", expand=True, padx=15, pady=15)

    tk.Label(corps, text="Ajouter des dates ou des périodes", font=("Segoe UI", 9, "bold"),
             bg="white", fg=COULEUR_TEXTE_PRINCIPAL, anchor="w").pack(fill="x")

    zone = tk.Text(corps, height=4, font=("Segoe UI", 10), wrap="word", relief="solid", bd=1)
    zone.pack(fill="x", pady=(4, 4))

    tk.Label(
        corps,
        text=("Sépare les éléments par une virgule, un point-virgule ou un retour à la ligne.\n"
              "Date seule : 25/12/2026   ·   Période : 01/08/2026 au 15/08/2026\n"
              "Exemple : 24/12/2026, 31/12/2026, 03/08/2026 au 21/08/2026"),
        font=("Segoe UI", 8), bg="white", fg=COULEUR_TEXTE_SECONDAIRE, justify="left",
        anchor="w", wraplength=400,
    ).pack(fill="x", pady=(0, 6))

    label_erreur = tk.Label(corps, font=("Segoe UI", 8, "bold"), bg="white", fg=COULEUR_ALERTE,
                            wraplength=400, justify="left", anchor="w")
    label_erreur.pack(fill="x")

    tk.Label(corps, text="Dates bloquées actuellement", font=("Segoe UI", 9, "bold"),
             bg="white", fg=COULEUR_TEXTE_PRINCIPAL, anchor="w").pack(fill="x", pady=(10, 4))

    cadre_liste = tk.Frame(corps, bg="white")
    cadre_liste.pack(fill="both", expand=True)
    scroll = tk.Scrollbar(cadre_liste)
    scroll.pack(side="right", fill="y")
    liste = tk.Listbox(cadre_liste, font=("Segoe UI", 10), selectmode="extended",
                       yscrollcommand=scroll.set, activestyle="none", relief="solid", bd=1)
    liste.pack(side="left", fill="both", expand=True)
    scroll.config(command=liste.yview)

    ids = []

    def remplir_liste():
        liste.delete(0, "end")
        ids.clear()
        for b in charger_dates_bloquees():
            liste.insert("end", _libelle_blocage(b))
            ids.append(b["id"])

    def ajouter():
        periodes, erreurs = analyser_saisie_dates_bloquees(zone.get("1.0", "end"))
        if erreurs:
            label_erreur.configure(text="⚠ " + "\n⚠ ".join(erreurs))
            if not periodes:
                return
        else:
            label_erreur.configure(text="")
        if not periodes:
            label_erreur.configure(text="⚠ Aucune date saisie.")
            return
        ajouter_dates_bloquees(periodes)
        zone.delete("1.0", "end")  # les éléments valides sont enregistrés ; les erreurs restent signalées
        remplir_liste()
        callback_rafraichir()

    def supprimer_selection():
        selection = liste.curselection()
        if not selection:
            messagebox.showinfo("Dates bloquées", "Sélectionne d'abord une ou plusieurs lignes à débloquer.",
                                parent=fenetre)
            return
        for i in selection:
            supprimer_date_bloquee(ids[i])
        remplir_liste()
        callback_rafraichir()

    remplir_liste()

    bouton_pleine_largeur(fenetre, "🚫  Bloquer ces dates", ajouter,
                          COULEUR_BOUTON_PRINCIPAL_BG, COULEUR_BOUTON_PRINCIPAL_FG)
    bouton_pleine_largeur(fenetre, "🗑  Débloquer la sélection", supprimer_selection,
                          COULEUR_BOUTON_SECONDAIRE_BG, COULEUR_BOUTON_SECONDAIRE_FG, avec_bordure=True)
    bouton_pleine_largeur(fenetre, "✕  Fermer", fermer,
                          COULEUR_BOUTON_SECONDAIRE_BG, COULEUR_BOUTON_SECONDAIRE_FG, avec_bordure=True)
