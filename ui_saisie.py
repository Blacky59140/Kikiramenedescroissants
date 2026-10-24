"""
ui_saisie.py
Fenêtre de saisie d'un événement : date, nom, catégorie (libre), message
optionnel, et média personnalisé optionnel pour le popup.
Sert à la fois pour la création d'un nouvel événement et pour la
modification d'un événement existant (si `evenement_existant` est fourni).
Style inspiré d'une maquette réalisée sur Google Stitch.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

from data_manager import (
    ajouter_evenement,
    modifier_evenement,
    charger_evenements,
    lister_medias_disponibles,
    copier_media_vers_images,
    EXTENSIONS_MEDIA_SUPPORTEES,
    prochaine_occurrence,
    date_a_afficher,
    jours_max_du_mois,
    est_anniversaire,
    est_weekend,
    est_jour_ferie,
    est_date_bloquee,
    JOURS_CONSERVATION_EVENEMENTS_NON_RECURRENTS,
    LONGUEUR_MAX_NOM,
    LONGUEUR_MAX_CATEGORIE,
    LONGUEUR_MAX_MESSAGE,
)
from ui_helpers import bouton_pleine_largeur, appliquer_geometrie_sauvegardee, sauvegarder_geometrie_actuelle
from theme import (
    COULEUR_FOND,
    COULEUR_BORDURE,
    COULEUR_TEXTE_PRINCIPAL,
    COULEUR_TEXTE_SECONDAIRE,
    COULEUR_ACCENT_TITRE,
    COULEUR_PLACEHOLDER,
    COULEUR_ALERTE,
    COULEUR_BOUTON_PRINCIPAL_BG,
    COULEUR_BOUTON_PRINCIPAL_FG,
    COULEUR_BOUTON_SECONDAIRE_BG,
    COULEUR_BOUTON_SECONDAIRE_FG,
)

AUCUN_MEDIA_LABEL = "(Aucun — utiliser l'image de la catégorie)"

PLACEHOLDER_NOM = "Ex: Jean Dupont"
PLACEHOLDER_CATEGORIE = "Sélectionnez une catégorie"
PLACEHOLDER_MESSAGE = "Écrivez un message chaleureux..."


def _categories_existantes():
    """Récupère la liste des catégories déjà utilisées, pour la liste déroulante."""
    evenements = charger_evenements()
    categories = sorted({e["categorie"] for e in evenements if e["categorie"]})
    for base in [
        "Anniversaire", "Naissance", "Retraite", "Départ", "Arrivée",
        "Nouvelle voiture", "Mariage", "Promotion", "Vacances", "Oups, j'ai buggé",
    ]:
        if base not in categories:
            categories.append(base)
    return categories


def _configurer_placeholder_variable(widget, variable, placeholder):
    """Simule un texte de substitution (placeholder) sur un Entry/Combobox lié à une StringVar."""

    def au_focus(_event):
        if variable.get() == placeholder:
            variable.set("")
            widget.configure(foreground=COULEUR_TEXTE_PRINCIPAL)

    def hors_focus(_event):
        if not variable.get().strip():
            variable.set(placeholder)
            widget.configure(foreground=COULEUR_PLACEHOLDER)

    widget.bind("<FocusIn>", au_focus)
    widget.bind("<FocusOut>", hors_focus)

    if not variable.get().strip():
        variable.set(placeholder)
        widget.configure(foreground=COULEUR_PLACEHOLDER)
    else:
        widget.configure(foreground=COULEUR_TEXTE_PRINCIPAL)


def _configurer_placeholder_texte(widget_texte, placeholder):
    """Simule un texte de substitution (placeholder) sur un widget Text multi-lignes."""

    def au_focus(_event):
        if widget_texte.get("1.0", "end").strip() == placeholder:
            widget_texte.delete("1.0", "end")
            widget_texte.configure(fg=COULEUR_TEXTE_PRINCIPAL)

    def hors_focus(_event):
        if not widget_texte.get("1.0", "end").strip():
            widget_texte.insert("1.0", placeholder)
            widget_texte.configure(fg=COULEUR_PLACEHOLDER)

    widget_texte.bind("<FocusIn>", au_focus)
    widget_texte.bind("<FocusOut>", hors_focus)

    if not widget_texte.get("1.0", "end").strip():
        widget_texte.insert("1.0", placeholder)
        widget_texte.configure(fg=COULEUR_PLACEHOLDER)
    else:
        widget_texte.configure(fg=COULEUR_TEXTE_PRINCIPAL)


def ouvrir_fenetre_saisie(parent, callback_rafraichir, evenement_existant=None):
    """
    Ouvre la fenêtre de saisie.
    - `callback_rafraichir` est appelé après l'enregistrement pour rafraîchir
      la fenêtre principale.
    - `evenement_existant` (optionnel) : dict d'un événement à modifier.
      Si fourni, la fenêtre s'ouvre en mode "modification" avec les champs
      pré-remplis ; sinon elle s'ouvre en mode "création".
    """
    mode_modification = evenement_existant is not None

    fenetre = tk.Toplevel(parent)
    fenetre.title("Modifier l'événement" if mode_modification else "Nouvel événement")
    appliquer_geometrie_sauvegardee(fenetre, "saisie", 440, 780)
    fenetre.resizable(False, False)
    fenetre.configure(bg=COULEUR_FOND)
    fenetre.transient(parent)
    fenetre.grab_set()

    def fermer_fenetre_saisie():
        sauvegarder_geometrie_actuelle(fenetre, "saisie")
        fenetre.destroy()

    fenetre.protocol("WM_DELETE_WINDOW", fermer_fenetre_saisie)

    # --- En-tête (flèche retour + titre) ---
    entete = tk.Frame(fenetre, bg="white", height=50)
    entete.pack(fill="x", side="top")
    entete.pack_propagate(False)

    fleche_retour = tk.Label(
        entete, text="←", font=("Segoe UI", 16, "bold"), bg="white",
        fg=COULEUR_TEXTE_PRINCIPAL, cursor="hand2",
    )
    fleche_retour.pack(side="left", padx=15)
    fleche_retour.bind("<Button-1>", lambda e: fermer_fenetre_saisie())

    tk.Label(
        entete, text="Modifier l'événement" if mode_modification else "Nouvel événement",
        font=("Segoe UI", 12, "bold"), bg="white", fg=COULEUR_ACCENT_TITRE,
    ).pack(side="left")

    tk.Frame(fenetre, bg=COULEUR_BORDURE, height=1).pack(fill="x", side="top")

    # --- Carte contenant le formulaire ---
    fond = tk.Frame(fenetre, bg=COULEUR_FOND)
    fond.pack(fill="both", expand=True)

    carte = tk.Frame(fond, bg="white", highlightbackground=COULEUR_BORDURE, highlightthickness=1)
    carte.pack(fill="both", expand=True, padx=15, pady=15)

    conteneur = tk.Frame(carte, bg="white", padx=18, pady=18)
    conteneur.pack(fill="both", expand=True)

    def _titre_champ(texte, optionnel=False):
        ligne = tk.Frame(conteneur, bg="white")
        ligne.pack(fill="x", pady=(0, 6))
        tk.Label(
            ligne, text=texte.upper(), font=("Segoe UI", 8, "bold"), bg="white", fg=COULEUR_TEXTE_SECONDAIRE,
        ).pack(side="left")
        if optionnel:
            tk.Label(
                ligne, text="Optionnel", font=("Segoe UI", 8, "italic"), bg="white", fg=COULEUR_PLACEHOLDER,
            ).pack(side="right")

    # --- Date ---
    _titre_champ("Date de l'événement")

    frame_date = tk.Frame(conteneur, bg="white")
    frame_date.pack(fill="x", pady=(0, 15))

    mois_labels = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
    ]
    annee_courante = date.today().year
    annees = [str(a) for a in range(annee_courante - 100, annee_courante + 2)]

    if mode_modification:
        valeur_jour = str(evenement_existant["jour"])
        valeur_mois = mois_labels[evenement_existant["mois"] - 1]
        valeur_annee = str(evenement_existant["annee"]) if evenement_existant.get("annee") else str(annee_courante)
    else:
        valeur_jour = str(date.today().day)
        valeur_mois = mois_labels[date.today().month - 1]
        valeur_annee = str(annee_courante)

    var_jour = tk.StringVar(value=valeur_jour)
    var_mois = tk.StringVar(value=valeur_mois)
    var_annee = tk.StringVar(value=valeur_annee)

    def _jours_du_mois():
        """Jours proposés pour le mois choisi (29 en février : l'année n'est pas connue pour un anniversaire)."""
        mois = mois_labels.index(var_mois.get()) + 1
        return [str(i) for i in range(1, jours_max_du_mois(mois) + 1)]

    combo_jour = ttk.Combobox(
        frame_date, textvariable=var_jour, values=_jours_du_mois(), width=4, state="readonly", font=("Segoe UI", 10)
    )
    combo_jour.pack(side="left", padx=(0, 8), ipady=3)

    combo_mois = ttk.Combobox(
        frame_date, textvariable=var_mois, values=mois_labels, width=11, state="readonly", font=("Segoe UI", 10)
    )
    combo_mois.pack(side="left", padx=(0, 8), ipady=3)

    combo_annee = ttk.Combobox(
        frame_date, textvariable=var_annee, values=annees, width=6, state="readonly", font=("Segoe UI", 10)
    )
    combo_annee.pack(side="left", fill="x", expand=True, ipady=3)

    label_alerte_date = tk.Label(
        conteneur, font=("Segoe UI", 8, "bold"), bg="white", fg=COULEUR_ALERTE,
        wraplength=380, justify="left", anchor="w",
    )

    def _categorie_saisie():
        categorie = var_categorie.get().strip()
        return "" if categorie == PLACEHOLDER_CATEGORIE else categorie

    def _date_controlee(jour, mois, annee, categorie):
        """Date réelle pour un événement ponctuel, prochaine occurrence pour un anniversaire."""
        return date_a_afficher({"jour": jour, "mois": mois, "annee": annee, "categorie": categorie})

    # En modification, un événement déjà placé sur une date bloquée peut être
    # modifié tant que sa date ne change pas.
    date_initiale = (
        _date_controlee(evenement_existant["jour"], evenement_existant["mois"],
                        evenement_existant.get("annee"), evenement_existant["categorie"])
        if mode_modification else None
    )

    def verifier_alerte_date(_event=None):
        try:
            jour = int(var_jour.get())
            mois = mois_labels.index(var_mois.get()) + 1
            annee = int(var_annee.get())
        except (ValueError, IndexError):
            label_alerte_date.pack_forget()
            return

        occurrence = _date_controlee(jour, mois, annee, _categorie_saisie())

        if est_date_bloquee(occurrence):
            if occurrence == date_initiale:
                texte = (f"⚠ Le {occurrence.strftime('%d/%m/%Y')} est une date bloquée : "
                         "l'événement existant peut être modifié, mais pas déplacé sur une autre date bloquée.")
            else:
                texte = (f"⛔ Le {occurrence.strftime('%d/%m/%Y')} est une date bloquée : "
                         "aucun événement ne peut y être créé.")
            label_alerte_date.configure(text=texte)
            label_alerte_date.pack(fill="x", pady=(6, 0))
        elif est_jour_ferie(occurrence):
            label_alerte_date.configure(text=f"⚠ Attention, cette date tombe un jour férié en {occurrence.year}.")
            label_alerte_date.pack(fill="x", pady=(6, 0))
        elif est_weekend(occurrence):
            nom_jour = "samedi" if occurrence.weekday() == 5 else "dimanche"
            label_alerte_date.configure(text=f"⚠ Attention, cette date tombe un {nom_jour} en {occurrence.year}.")
            label_alerte_date.pack(fill="x", pady=(6, 0))
        else:
            label_alerte_date.pack_forget()

    def changement_de_mois(_event=None):
        """Limite la liste des jours au mois choisi (ex : pas de 31 en avril)."""
        jours = _jours_du_mois()
        combo_jour.configure(values=jours)
        if var_jour.get() not in jours:
            var_jour.set(jours[-1])
        verifier_alerte_date()

    combo_jour.bind("<<ComboboxSelected>>", verifier_alerte_date)
    combo_mois.bind("<<ComboboxSelected>>", changement_de_mois)
    combo_annee.bind("<<ComboboxSelected>>", verifier_alerte_date)

    # --- Nom ---
    _titre_champ("Nom de la personne")
    var_nom = tk.StringVar(value=evenement_existant["nom"] if mode_modification else "")
    entree_nom = ttk.Entry(conteneur, textvariable=var_nom, font=("Segoe UI", 10))
    entree_nom.pack(fill="x", pady=(0, 15), ipady=5)
    _configurer_placeholder_variable(entree_nom, var_nom, PLACEHOLDER_NOM)
    if not mode_modification:
        entree_nom.focus()

    # --- Catégorie (liste déroulante modifiable) ---
    _titre_champ("Catégorie")
    var_categorie = tk.StringVar(value=evenement_existant["categorie"] if mode_modification else "")
    combo_categorie = ttk.Combobox(
        conteneur, textvariable=var_categorie, values=_categories_existantes(), font=("Segoe UI", 10)
    )  # pas de state="readonly" -> l'utilisateur peut taper une nouvelle catégorie
    combo_categorie.pack(fill="x", pady=(0, 15), ipady=3)
    _configurer_placeholder_variable(combo_categorie, var_categorie, PLACEHOLDER_CATEGORIE)
    # La date contrôlée dépend de la catégorie (anniversaire récurrent ou événement ponctuel)
    combo_categorie.bind("<<ComboboxSelected>>", verifier_alerte_date)
    combo_categorie.bind("<FocusOut>", verifier_alerte_date, add="+")
    verifier_alerte_date()

    # --- Message optionnel ---
    _titre_champ("Message personnalisé", optionnel=True)
    texte_message = tk.Text(
        conteneur, height=4, font=("Segoe UI", 10), relief="solid", bd=1,
        highlightthickness=0, wrap="word", padx=8, pady=6,
    )
    texte_message.pack(fill="x", pady=(0, 15))
    if mode_modification and evenement_existant.get("message"):
        texte_message.insert("1.0", evenement_existant["message"])
        texte_message.configure(fg=COULEUR_TEXTE_PRINCIPAL)
    else:
        _configurer_placeholder_texte(texte_message, PLACEHOLDER_MESSAGE)

    # --- Média personnalisé du popup (optionnel) ---
    _titre_champ("Image/GIF du popup", optionnel=True)

    valeur_media_initiale = (
        evenement_existant.get("media", "") if mode_modification and evenement_existant.get("media") else ""
    )
    var_media = tk.StringVar(value=valeur_media_initiale or AUCUN_MEDIA_LABEL)

    valeurs_media = [AUCUN_MEDIA_LABEL] + lister_medias_disponibles()
    combo_media = ttk.Combobox(
        conteneur, textvariable=var_media, values=valeurs_media, state="readonly", font=("Segoe UI", 10)
    )
    combo_media.pack(fill="x", pady=(0, 8), ipady=3)

    def parcourir_media():
        types_fichiers = [
            ("Images et GIF", " ".join(f"*{ext}" for ext in EXTENSIONS_MEDIA_SUPPORTEES)),
            ("Tous les fichiers", "*.*"),
        ]
        chemin_choisi = filedialog.askopenfilename(
            title="Choisir une image ou un GIF", filetypes=types_fichiers, parent=fenetre
        )
        if not chemin_choisi:
            return

        nom_fichier = copier_media_vers_images(chemin_choisi)
        nouvelles_valeurs = [AUCUN_MEDIA_LABEL] + lister_medias_disponibles()
        combo_media.configure(values=nouvelles_valeurs)
        var_media.set(nom_fichier)

    bouton_pleine_largeur(conteneur, "Parcourir...", parcourir_media, "#EDEDF2", COULEUR_TEXTE_PRINCIPAL)

    tk.Label(
        conteneur,
        text="Sans sélection, l'image par défaut de la catégorie est utilisée.",
        font=("Segoe UI", 8), bg="white", fg=COULEUR_PLACEHOLDER, wraplength=380, justify="left",
    ).pack(anchor="w", pady=(0, 20))

    # --- Validation ---
    def valider():
        nom = var_nom.get().strip()
        if nom == PLACEHOLDER_NOM:
            nom = ""

        categorie = var_categorie.get().strip()
        if categorie == PLACEHOLDER_CATEGORIE:
            categorie = ""

        message = texte_message.get("1.0", "end").strip()
        if message == PLACEHOLDER_MESSAGE:
            message = ""

        media = var_media.get().strip()
        if media == AUCUN_MEDIA_LABEL:
            media = ""

        if not nom:
            messagebox.showwarning("Champ manquant", "Le nom de la personne est obligatoire.")
            return
        if not categorie:
            messagebox.showwarning("Champ manquant", "La catégorie est obligatoire.")
            return

        for libelle, valeur, maximum in (
            ("Le nom", nom, LONGUEUR_MAX_NOM),
            ("La catégorie", categorie, LONGUEUR_MAX_CATEGORIE),
            ("Le message", message, LONGUEUR_MAX_MESSAGE),
        ):
            if len(valeur) > maximum:
                messagebox.showwarning(
                    "Texte trop long",
                    f"{libelle} est trop long ({len(valeur)} caractères) : {maximum} caractères maximum.",
                    parent=fenetre,
                )
                return

        jour = int(var_jour.get())
        mois = mois_labels.index(var_mois.get()) + 1
        annee = int(var_annee.get())

        if not est_anniversaire({"categorie": categorie}):
            # Événement ponctuel : la date complète doit exister et ne pas être déjà expirée
            if jour > jours_max_du_mois(mois, annee):
                messagebox.showwarning(
                    "Date invalide", f"Le {jour} {var_mois.get().lower()} n'existe pas en {annee}.", parent=fenetre,
                )
                return
            date_saisie = date(annee, mois, jour)
            if (date_saisie - date.today()).days < -JOURS_CONSERVATION_EVENEMENTS_NON_RECURRENTS:
                proposition = prochaine_occurrence(jour, mois)
                if not messagebox.askyesno(
                    "Date passée",
                    f"Le {date_saisie.strftime('%d/%m/%Y')} est passé depuis plus de "
                    f"{JOURS_CONSERVATION_EVENEMENTS_NON_RECURRENTS} jours : l'événement serait supprimé "
                    "automatiquement.\n\n"
                    f"Enregistrer plutôt pour le {proposition.strftime('%d/%m/%Y')} ?",
                    parent=fenetre,
                ):
                    return
                annee = proposition.year
                var_annee.set(str(annee))

        occurrence = _date_controlee(jour, mois, annee, categorie)
        if est_date_bloquee(occurrence) and occurrence != date_initiale:
            messagebox.showwarning(
                "Date bloquée",
                f"Le {occurrence.strftime('%d/%m/%Y')} fait partie des dates bloquées.\n"
                "Choisis une autre date, ou débloque-la depuis le menu ⋮ > Dates bloquées.",
                parent=fenetre,
            )
            return

        if mode_modification:
            modifier_evenement(evenement_existant["id"], nom, jour, mois, categorie, message, media, annee)
        else:
            ajouter_evenement(nom, jour, mois, categorie, message, media, annee)

        callback_rafraichir()
        fermer_fenetre_saisie()

    bouton_pleine_largeur(
        conteneur, "💾  Enregistrer", valider, COULEUR_BOUTON_PRINCIPAL_BG, COULEUR_BOUTON_PRINCIPAL_FG
    )
    bouton_pleine_largeur(
        conteneur, "✕  Annuler", fermer_fenetre_saisie, COULEUR_BOUTON_SECONDAIRE_BG, COULEUR_BOUTON_SECONDAIRE_FG,
        avec_bordure=True,
    )
