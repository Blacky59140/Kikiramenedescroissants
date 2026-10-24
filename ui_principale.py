"""
ui_principale.py
Fenêtre principale : en-tête, calendrier mensuel (tkcalendar) avec marqueurs
colorés par catégorie, liste des événements du mois affiché sous forme de
cartes, et barre d'icônes en bas (Saisie / Supprimer / Modifier).
Inspirée d'une maquette réalisée sur Google Stitch.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import calendar
from datetime import date, datetime, time, timedelta

from tkcalendar import Calendar

from data_manager import (
    evenements_du_mois,
    evenements_a_venir,
    supprimer_evenement,
    obtenir_evenement,
    evenements_du_jour,
    couleur_categorie,
    couleurs_badge_categorie,
    normaliser_nom_categorie,
    est_weekend,
    est_jour_ferie,
    nettoyer_evenements_expires,
    jours_bloques_du_mois,
)
from ui_dates_bloquees import ouvrir_fenetre_dates_bloquees
from ui_saisie import ouvrir_fenetre_saisie
from ui_popup import afficher_popup_du_jour
from ui_helpers import appliquer_geometrie_sauvegardee, sauvegarder_geometrie_actuelle
from theme import (
    COULEUR_FOND,
    COULEUR_BORDURE,
    COULEUR_TEXTE_PRINCIPAL,
    COULEUR_TEXTE_SECONDAIRE,
    COULEUR_ACCENT_SELECTION,
)

MOIS_ABREGES = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]

HEURE_VERIFICATION_QUOTIDIENNE = time(1, 0)  # 1h00 du matin : heure à laquelle on revérifie le jour et les événements


class FenetrePrincipale(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kikiramènedescroissants ?")
        appliquer_geometrie_sauvegardee(self, "principale", 430, 780)
        self.minsize(380, 600)
        self.configure(bg=COULEUR_FOND)
        self.protocol("WM_DELETE_WINDOW", self._fermer_application)

        self.carte_selectionnee_id = None
        self.cartes_widgets = {}
        self._tags_calendrier_configures = set()
        self._dernier_jour_verifie = date.today()

        self._construire_entete()
        self._construire_calendrier()
        self._construire_liste_evenements()
        self._construire_barre_basse()

        self.rafraichir_affichage()

        # Revérifie chaque jour à 1h00 du matin si on est passé au jour
        # suivant, pour déclencher le popup sans avoir à relancer l'appli.
        self.after(self._delai_jusqua_1h_du_matin(), self._verifier_changement_de_jour)

    def _fermer_application(self):
        """Mémorise la taille/position de la fenêtre avant de fermer l'application."""
        sauvegarder_geometrie_actuelle(self, "principale")
        self.destroy()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _construire_entete(self):
        entete = tk.Frame(self, bg="white", height=56)
        entete.pack(fill="x", side="top")
        entete.pack_propagate(False)

        frame_titre = tk.Frame(entete, bg="white")
        frame_titre.pack(side="left", padx=15)
        tk.Label(frame_titre, text="👥", font=("Segoe UI Emoji", 15), bg="white").pack(side="left", padx=(0, 8))
        tk.Label(
            frame_titre, text="Kikiramènedescroissants ?", font=("Segoe UI", 11, "bold"),
            bg="white", fg=COULEUR_TEXTE_PRINCIPAL,
        ).pack(side="left")

        bouton_menu = tk.Label(
            entete, text="⋮", font=("Segoe UI", 18, "bold"), bg="white",
            fg=COULEUR_TEXTE_PRINCIPAL, cursor="hand2",
        )
        bouton_menu.pack(side="right", padx=15)
        bouton_menu.bind("<Button-1>", self._ouvrir_menu_options)

        tk.Frame(self, bg=COULEUR_BORDURE, height=1).pack(fill="x", side="top")

    def _ouvrir_menu_options(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="🚫 Dates bloquées…", command=self._ouvrir_dates_bloquees)
        menu.add_separator()
        menu.add_command(label="🔔 Tester le popup", command=self.tester_popup)
        menu.tk_popup(event.x_root, event.y_root)

    def _ouvrir_dates_bloquees(self):
        ouvrir_fenetre_dates_bloquees(self, self.rafraichir_affichage)

    def _construire_calendrier(self):
        conteneur = tk.Frame(self, bg=COULEUR_FOND, padx=15, pady=15)
        conteneur.pack(fill="x", side="top")

        aujourdhui = date.today()
        self.calendrier = Calendar(
            conteneur,
            selectmode="day",
            locale="fr_FR",
            year=aujourdhui.year, month=aujourdhui.month, day=aujourdhui.day,
            showweeknumbers=False,
            background="white", foreground=COULEUR_TEXTE_PRINCIPAL,
            headersbackground="white", headersforeground=COULEUR_TEXTE_SECONDAIRE,
            normalbackground="white", normalforeground=COULEUR_TEXTE_PRINCIPAL,
            weekendbackground="white", weekendforeground=COULEUR_TEXTE_PRINCIPAL,
            othermonthbackground=COULEUR_FOND, othermonthforeground="#C2C2CE",
            othermonthwebackground=COULEUR_FOND, othermonthweforeground="#C2C2CE",
            selectbackground=COULEUR_TEXTE_PRINCIPAL, selectforeground="white",
            bordercolor=COULEUR_BORDURE,
            font=("Segoe UI", 10),
        )
        self.calendrier.pack(fill="x")
        self.calendrier.bind("<<CalendarMonthChanged>>", lambda e: self.rafraichir_affichage())

    def _construire_liste_evenements(self):
        tk.Label(
            self, text="LES 9 PROCHAINS ÉVÉNEMENTS", font=("Segoe UI", 9, "bold"),
            bg=COULEUR_FOND, fg=COULEUR_TEXTE_SECONDAIRE,
        ).pack(anchor="w", padx=20, pady=(0, 5))

        zone_scroll = tk.Frame(self, bg=COULEUR_FOND)
        zone_scroll.pack(fill="both", expand=True, padx=15)

        self.canvas_liste = tk.Canvas(zone_scroll, bg=COULEUR_FOND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(zone_scroll, orient="vertical", command=self.canvas_liste.yview)
        self.frame_cartes = tk.Frame(self.canvas_liste, bg=COULEUR_FOND)

        self.frame_cartes.bind(
            "<Configure>", lambda e: self.canvas_liste.configure(scrollregion=self.canvas_liste.bbox("all"))
        )
        id_fenetre_canvas = self.canvas_liste.create_window((0, 0), window=self.frame_cartes, anchor="nw")
        self.canvas_liste.bind(
            "<Configure>", lambda e: self.canvas_liste.itemconfig(id_fenetre_canvas, width=e.width)
        )
        self.canvas_liste.configure(yscrollcommand=scrollbar.set)

        self.canvas_liste.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _construire_barre_basse(self):
        barre = tk.Frame(self, bg="white", height=68)
        barre.pack(fill="x", side="bottom")
        barre.pack_propagate(False)
        tk.Frame(self, bg=COULEUR_BORDURE, height=1).pack(fill="x", side="bottom")

        def creer_bouton(parent, emoji, texte, commande):
            conteneur = tk.Frame(parent, bg="white", cursor="hand2")
            tk.Label(conteneur, text=emoji, font=("Segoe UI Emoji", 16), bg="white").pack()
            tk.Label(conteneur, text=texte, font=("Segoe UI", 8), bg="white", fg="#5A5A6A").pack()
            for widget in (conteneur, *conteneur.winfo_children()):
                widget.bind("<Button-1>", lambda e: commande())
            return conteneur

        creer_bouton(barre, "📅", "Saisie", self.ouvrir_saisie).pack(side="left", expand=True, fill="both")
        creer_bouton(barre, "🗑", "Supprimer", self.supprimer_selection).pack(side="left", expand=True, fill="both")
        creer_bouton(barre, "✏", "Modifier", self.modifier_selection).pack(side="left", expand=True, fill="both")

    # ------------------------------------------------------------------
    # Rafraîchissement (calendrier + liste), déclenché à l'ouverture, après
    # ajout/modification/suppression, et à chaque changement de mois affiché
    # ------------------------------------------------------------------
    def rafraichir_affichage(self):
        nettoyer_evenements_expires()
        mois, annee = self.calendrier.get_displayed_month()
        self._mettre_a_jour_marqueurs_calendrier(mois, annee)
        self._mettre_a_jour_liste_cartes()

    def _delai_jusqua_1h_du_matin(self):
        """Calcule le délai (en millisecondes) jusqu'à la prochaine occurrence de 1h00 du matin."""
        maintenant = datetime.now()
        prochaine_echeance = datetime.combine(maintenant.date(), HEURE_VERIFICATION_QUOTIDIENNE)
        if maintenant >= prochaine_echeance:
            prochaine_echeance += timedelta(days=1)
        return int((prochaine_echeance - maintenant).total_seconds() * 1000)

    def _verifier_changement_de_jour(self):
        """
        Appelée chaque jour à 1h00 du matin tant que l'application reste
        ouverte. Si la date a changé depuis la dernière vérification (ex :
        passage de minuit pendant que l'app tourne), rafraîchit l'affichage
        et déclenche le popup du jour si un événement tombe aujourd'hui —
        sans que l'utilisateur ait besoin de relancer l'application.
        """
        aujourdhui = date.today()

        if aujourdhui != self._dernier_jour_verifie:
            self._dernier_jour_verifie = aujourdhui
            self.rafraichir_affichage()

            evenements_jour = evenements_du_jour(aujourdhui)
            if evenements_jour:
                afficher_popup_du_jour(self, evenements_jour)

        # Replanifie pour la prochaine occurrence de 1h00 du matin (recalculé
        # à chaque fois, pour rester robuste si l'ordinateur a été en veille).
        self.after(self._delai_jusqua_1h_du_matin(), self._verifier_changement_de_jour)

    def _mettre_a_jour_marqueurs_calendrier(self, mois, annee):
        self.calendrier.calevent_remove("all")
        evenements = evenements_du_mois(mois, annee)

        jours_avec_evenement = set()
        for e in evenements:
            jours_avec_evenement.add(e["date_affichage"])
            tag = f"cat_{normaliser_nom_categorie(e['categorie'])}"
            if tag not in self._tags_calendrier_configures:
                self.calendrier.tag_config(tag, background=couleur_categorie(e["categorie"]), foreground="white")
                self._tags_calendrier_configures.add(tag)
            self.calendrier.calevent_create(e["date_affichage"], f"{e['nom']} — {e['categorie']}", tag)

        # Fond gris pour les week-ends et jours fériés qui n'ont pas déjà un événement
        if "jour_non_ouvre" not in self._tags_calendrier_configures:
            self.calendrier.tag_config("jour_non_ouvre", background="#DADADF", foreground=COULEUR_TEXTE_SECONDAIRE)
            self._tags_calendrier_configures.add("jour_non_ouvre")

        if "jour_bloque" not in self._tags_calendrier_configures:
            self.calendrier.tag_config("jour_bloque", background="#FECACA", foreground="#991B1B")
            self._tags_calendrier_configures.add("jour_bloque")
        jours_bloques = jours_bloques_du_mois(mois, annee)

        nb_jours_du_mois = calendar.monthrange(annee, mois)[1]
        for jour in range(1, nb_jours_du_mois + 1):
            jour_date = date(annee, mois, jour)
            if jour_date in jours_avec_evenement:
                continue
            if jour_date in jours_bloques:
                self.calendrier.calevent_create(jour_date, "Date bloquée", "jour_bloque")
                continue
            if est_weekend(jour_date) or est_jour_ferie(jour_date):
                self.calendrier.calevent_create(jour_date, "Jour non ouvré", "jour_non_ouvre")

    def _mettre_a_jour_liste_cartes(self):
        for widget in self.frame_cartes.winfo_children():
            widget.destroy()
        self.cartes_widgets = {}
        self.carte_selectionnee_id = None

        aujourdhui = date.today()
        evenements = evenements_a_venir(9, aujourdhui)

        if not evenements:
            tk.Label(
                self.frame_cartes, text="Aucun événement à venir.", bg=COULEUR_FOND,
                fg=COULEUR_TEXTE_SECONDAIRE, font=("Segoe UI", 10, "italic"),
            ).pack(pady=20)
            return

        for e in evenements:
            self._creer_carte(e, aujourdhui)

    def _creer_carte(self, evenement, aujourdhui):
        couleur = couleur_categorie(evenement["categorie"])
        ecart = (evenement["date_affichage"] - aujourdhui).days

        outer = tk.Frame(self.frame_cartes, bg="white", highlightbackground=COULEUR_BORDURE, highlightthickness=1)
        outer.pack(fill="x", pady=6)

        barre_couleur = tk.Frame(outer, bg=couleur, width=5)
        barre_couleur.pack(side="left", fill="y")

        contenu = tk.Frame(outer, bg="white", padx=12, pady=10)
        contenu.pack(side="left", fill="both", expand=True)

        ligne_haut = tk.Frame(contenu, bg="white")
        ligne_haut.pack(fill="x")

        police_nom = ("Segoe UI", 11, "bold") if ecart == 0 else ("Segoe UI", 11)
        couleur_texte_nom = "#808080" if -3 <= ecart < 0 else COULEUR_TEXTE_PRINCIPAL

        label_nom = tk.Label(
            ligne_haut, text=evenement["nom"], font=police_nom, bg="white",
            fg=couleur_texte_nom, anchor="w",
        )
        label_nom.pack(side="left", fill="x", expand=True)

        frame_droite = tk.Frame(ligne_haut, bg="white")
        frame_droite.pack(side="right")

        bg_badge, fg_badge = couleurs_badge_categorie(evenement["categorie"])
        badge = tk.Label(
            frame_droite, text=evenement["categorie"].upper(), font=("Segoe UI", 7, "bold"),
            bg=bg_badge, fg=fg_badge, padx=8, pady=2,
        )
        badge.pack(anchor="e")

        d = evenement["date_affichage"]
        label_date = tk.Label(
            frame_droite, text=f"{d.day} {MOIS_ABREGES[d.month - 1]}", font=("Segoe UI", 8),
            bg="white", fg=COULEUR_TEXTE_SECONDAIRE,
        )
        label_date.pack(anchor="e", pady=(2, 0))

        widgets_a_lier = [outer, barre_couleur, contenu, ligne_haut, label_nom, badge, frame_droite, label_date]

        message = (evenement.get("message") or "").strip()
        if message:
            label_message = tk.Label(
                contenu, text=f"« {message} »", font=("Segoe UI", 9, "italic"), bg="white",
                fg="#5A5A6A", justify="left", anchor="w", wraplength=260,
            )
            label_message.pack(fill="x", pady=(4, 0))
            widgets_a_lier.append(label_message)

        for widget in widgets_a_lier:
            widget.bind("<Button-1>", lambda ev, id_=evenement["id"], frame=outer: self._selectionner_carte(id_, frame))
            widget.bind("<Double-1>", lambda ev, id_=evenement["id"]: self._modifier_directement(id_))

        self.cartes_widgets[evenement["id"]] = outer

    def _selectionner_carte(self, id_evenement, frame):
        if self.carte_selectionnee_id and self.carte_selectionnee_id in self.cartes_widgets:
            self.cartes_widgets[self.carte_selectionnee_id].configure(
                highlightbackground=COULEUR_BORDURE, highlightthickness=1
            )
        self.carte_selectionnee_id = id_evenement
        frame.configure(highlightbackground=COULEUR_ACCENT_SELECTION, highlightthickness=2)

    def _modifier_directement(self, id_evenement):
        self.carte_selectionnee_id = id_evenement
        self.modifier_selection()

    # ------------------------------------------------------------------
    # Actions (Saisie / Modifier / Supprimer / Tester le popup)
    # ------------------------------------------------------------------
    def ouvrir_saisie(self):
        ouvrir_fenetre_saisie(self, self.rafraichir_affichage)

    def modifier_selection(self):
        if not self.carte_selectionnee_id:
            messagebox.showinfo("Aucune sélection", "Sélectionnez un événement dans la liste avant de le modifier.")
            return

        evenement = obtenir_evenement(self.carte_selectionnee_id)
        if evenement is None:
            messagebox.showerror("Erreur", "Cet événement n'existe plus.")
            self.rafraichir_affichage()
            return

        ouvrir_fenetre_saisie(self, self.rafraichir_affichage, evenement_existant=evenement)

    def supprimer_selection(self):
        if not self.carte_selectionnee_id:
            messagebox.showinfo("Aucune sélection", "Sélectionnez un événement dans la liste avant de le supprimer.")
            return

        evenement = obtenir_evenement(self.carte_selectionnee_id)
        if evenement is None:
            messagebox.showerror("Erreur", "Cet événement n'existe plus.")
            self.rafraichir_affichage()
            return

        if messagebox.askyesno("Confirmation", f"Supprimer l'événement de {evenement['nom']} ?"):
            supprimer_evenement(self.carte_selectionnee_id)
            self.rafraichir_affichage()

    def tester_popup(self):
        """
        Prévisualise le popup :
        - si une carte est sélectionnée, teste ce popup précis
        - sinon, teste avec les événements réels du jour (s'il y en a)
        """
        if self.carte_selectionnee_id:
            evenement = obtenir_evenement(self.carte_selectionnee_id)
            if evenement is None:
                messagebox.showerror("Erreur", "Cet événement n'existe plus.")
                self.rafraichir_affichage()
                return
            afficher_popup_du_jour(self, [evenement])
            return

        evenements_jour = evenements_du_jour()
        if not evenements_jour:
            messagebox.showinfo(
                "Aucun événement aujourd'hui",
                "Aucun événement ne tombe aujourd'hui.\n"
                "Sélectionnez un événement dans la liste pour tester son affichage.",
            )
            return

        afficher_popup_du_jour(self, evenements_jour)
