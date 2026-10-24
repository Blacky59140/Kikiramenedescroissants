"""
ui_popup.py
Fenêtre popup présentant un événement du jour : photo/GIF en bandeau avec
badge de catégorie superposé, carte d'info (nom + date), carte message
(bordure colorée + guillemet), navigation Précédent/Suivant si plusieurs
événements le même jour, et bouton Fermer. Style inspiré d'une maquette
réalisée sur Google Stitch.
"""

import tkinter as tk
from tkinter import ttk

from data_manager import (
    message_par_defaut,
    chemin_media_pour_popup,
    emoji_categorie,
    couleur_categorie,
)
from theme import (
    COULEUR_FOND,
    COULEUR_BORDURE,
    COULEUR_TEXTE_PRINCIPAL,
    COULEUR_TEXTE_SECONDAIRE,
    COULEUR_BOUTON_PRINCIPAL_BG,
    COULEUR_BOUTON_PRINCIPAL_FG,
)
from ui_helpers import bouton_pleine_largeur, appliquer_geometrie_sauvegardee, sauvegarder_geometrie_actuelle

try:
    from PIL import Image, ImageTk
    PIL_DISPONIBLE = True
    try:
        FILTRE_REDIMENSIONNEMENT = Image.Resampling.LANCZOS
    except AttributeError:
        FILTRE_REDIMENSIONNEMENT = Image.LANCZOS
except ImportError:
    PIL_DISPONIBLE = False

# Limites de sécurité sur les médias (protection contre les images piégées)
MAX_PIXELS_MEDIA = 25_000_000   # taille maximale d'une image source (largeur x hauteur)
MAX_FRAMES_GIF = 100            # nombre maximal de frames lues dans un GIF
DIMENSION_MAX_MEDIA = 1000      # côté maximal (px) conservé en mémoire pour chaque image/frame

LARGEUR_POPUP_DEFAUT = 420
HAUTEUR_POPUP_DEFAUT = 760
TAILLE_MIN_POPUP = (340, 560)

PROPORTION_HAUTEUR_PHOTO = 0.40  # part de la fenêtre occupée par la photo
HAUTEUR_MIN_PHOTO = 160

DELAI_DEBOUNCE_REDIMENSIONNEMENT_MS = 120
DELAI_MIN_FRAME_MS = 20

CITATION_ICONE = "„"  # guillemet typographique ouvrant, façon maquette


def _extension(chemin):
    return chemin.rsplit(".", 1)[-1].lower() if "." in chemin else ""


def _eclaircir_couleur(couleur_hex, quantite=0.85):
    couleur_hex = couleur_hex.lstrip("#")
    r, g, b = int(couleur_hex[0:2], 16), int(couleur_hex[2:4], 16), int(couleur_hex[4:6], 16)
    r = int(r + (255 - r) * quantite)
    g = int(g + (255 - g) * quantite)
    b = int(b + (255 - b) * quantite)
    return f"#{r:02x}{g:02x}{b:02x}"


def _redimensionner_cover(image_pil, largeur_cible, hauteur_cible):
    """Redimensionne puis recadre une image pour qu'elle remplisse exactement
    (largeur_cible x hauteur_cible) sans déformation, façon CSS `object-fit: cover`."""
    largeur_cible = max(1, largeur_cible)
    hauteur_cible = max(1, hauteur_cible)
    ratio_cible = largeur_cible / hauteur_cible
    ratio_image = image_pil.width / image_pil.height

    if ratio_image > ratio_cible:
        nouvelle_hauteur = hauteur_cible
        nouvelle_largeur = max(1, int(hauteur_cible * ratio_image))
    else:
        nouvelle_largeur = largeur_cible
        nouvelle_hauteur = max(1, int(largeur_cible / ratio_image))

    image_redim = image_pil.resize((nouvelle_largeur, nouvelle_hauteur), FILTRE_REDIMENSIONNEMENT)
    gauche = (nouvelle_largeur - largeur_cible) // 2
    haut = (nouvelle_hauteur - hauteur_cible) // 2
    return image_redim.crop((gauche, haut, gauche + largeur_cible, haut + hauteur_cible))


def _calculer_taille_photo(popup):
    largeur = popup.winfo_width() or LARGEUR_POPUP_DEFAUT
    hauteur = popup.winfo_height() or HAUTEUR_POPUP_DEFAUT
    hauteur_photo = max(HAUTEUR_MIN_PHOTO, int(hauteur * PROPORTION_HAUTEUR_PHOTO))
    return largeur, hauteur_photo


def _calculer_taille_police(popup, base_reference):
    largeur = popup.winfo_width() or LARGEUR_POPUP_DEFAUT
    hauteur = popup.winfo_height() or HAUTEUR_POPUP_DEFAUT
    facteur = min(largeur / LARGEUR_POPUP_DEFAUT, hauteur / HAUTEUR_POPUP_DEFAUT)
    facteur = max(0.75, min(facteur, 1.8))
    return max(8, int(base_reference * facteur))


def afficher_popup_du_jour(parent, evenements):
    """Affiche la fenêtre popup pour un ou plusieurs événements du jour."""
    if not evenements:
        return

    popup = tk.Toplevel(parent)
    appliquer_geometrie_sauvegardee(popup, "popup", LARGEUR_POPUP_DEFAUT, HAUTEUR_POPUP_DEFAUT)
    popup.minsize(*TAILLE_MIN_POPUP)
    popup.resizable(True, True)
    popup.configure(bg="white")

    popup.attributes("-topmost", True)
    popup.after(100, lambda: popup.attributes("-topmost", False))

    popup.images_references = []

    etat = {
        "index": 0,
        "token": 0,
        "apres_id_anim": None,
        "apres_id_redim": None,
        "pil_image_statique": None,
        "gif_frames": None,
        "gif_index": 0,
        "taille_cible": (LARGEUR_POPUP_DEFAUT, int(HAUTEUR_POPUP_DEFAUT * PROPORTION_HAUTEUR_PHOTO)),
    }

    widgets = {"photo": None, "badge": None, "nom": None, "categorie": None, "jour": None, "mois": None, "message": None}
    label_compteur = None

    # ------------------------------------------------------------------
    # Structure générale (empilement vertical)
    # ------------------------------------------------------------------
    zone_photo = tk.Frame(popup, bg="#EDEDF2")
    zone_photo.pack(fill="x", side="top")
    zone_photo.pack_propagate(False)

    zone_scroll = tk.Frame(popup, bg=COULEUR_FOND)
    zone_scroll.pack(fill="both", expand=True, side="top")

    zone_basse = tk.Frame(popup, bg=COULEUR_FOND)
    zone_basse.pack(fill="x", side="bottom")

    # --- Bouton Fermer (toujours visible en bas) ---
    def fermer_popup():
        arreter_media()
        if etat["apres_id_redim"] is not None:
            try:
                popup.after_cancel(etat["apres_id_redim"])
            except (tk.TclError, ValueError):
                pass
        sauvegarder_geometrie_actuelle(popup, "popup")
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", fermer_popup)

    conteneur_bas = tk.Frame(zone_basse, bg=COULEUR_FOND, padx=15, pady=10)
    conteneur_bas.pack(fill="x")

    frame_navigation = tk.Frame(conteneur_bas, bg=COULEUR_FOND)
    if len(evenements) > 1:
        frame_navigation.pack(fill="x", pady=(0, 8))

    bouton_pleine_largeur(conteneur_bas, "✕  FERMER", fermer_popup, COULEUR_BOUTON_PRINCIPAL_BG, COULEUR_BOUTON_PRINCIPAL_FG)

    # ------------------------------------------------------------------
    # Nettoyage / arrêt des animations en cours
    # ------------------------------------------------------------------
    def arreter_media():
        if etat["apres_id_anim"] is not None:
            try:
                popup.after_cancel(etat["apres_id_anim"])
            except (tk.TclError, ValueError):
                pass
            etat["apres_id_anim"] = None

        etat["pil_image_statique"] = None
        etat["gif_frames"] = None
        etat["gif_index"] = 0

    # ------------------------------------------------------------------
    # Rendu image statique / GIF (recadrage "cover" plein cadre)
    # ------------------------------------------------------------------
    def _afficher_photo(image_tk):
        popup.images_references.append(image_tk)
        if len(popup.images_references) > 5:
            popup.images_references.pop(0)
        widgets["photo"].configure(image=image_tk, text="")
        widgets["photo"].image = image_tk

    def rendre_image_statique():
        if etat["pil_image_statique"] is None or widgets["photo"] is None:
            return
        try:
            largeur, hauteur = etat["taille_cible"]
            image_recadree = _redimensionner_cover(etat["pil_image_statique"], largeur, hauteur)
            _afficher_photo(ImageTk.PhotoImage(image_recadree))
        except Exception as erreur:
            print(f"[popup] Erreur de redimensionnement de l'image : {erreur}")

    def jouer_frame_gif(token_appel):
        if token_appel != etat["token"] or not etat["gif_frames"] or widgets["photo"] is None:
            return
        frame_pil, duree_ms = etat["gif_frames"][etat["gif_index"]]
        try:
            largeur, hauteur = etat["taille_cible"]
            image_recadree = _redimensionner_cover(frame_pil, largeur, hauteur)
            _afficher_photo(ImageTk.PhotoImage(image_recadree))
        except Exception as erreur:
            print(f"[popup] Erreur d'affichage du GIF : {erreur}")
            return

        etat["gif_index"] = (etat["gif_index"] + 1) % len(etat["gif_frames"])
        delai = max(DELAI_MIN_FRAME_MS, duree_ms)
        etat["apres_id_anim"] = popup.after(delai, lambda: jouer_frame_gif(token_appel))

    def _ouvrir_image(chemin):
        """Ouvre une image après avoir vérifié ses dimensions (sans la décoder)."""
        image = Image.open(chemin)
        largeur, hauteur = image.size
        if largeur * hauteur > MAX_PIXELS_MEDIA:
            image.close()
            raise ValueError(f"image trop grande ({largeur}x{hauteur} px)")
        return image

    def _reduire(image):
        """Limite la taille en mémoire : aucune image ne dépasse DIMENSION_MAX_MEDIA px de côté."""
        image.thumbnail((DIMENSION_MAX_MEDIA, DIMENSION_MAX_MEDIA))
        return image

    def charger_gif(chemin):
        try:
            from PIL import ImageSequence
            image_source = _ouvrir_image(chemin)
            frames = []
            for frame in ImageSequence.Iterator(image_source):
                if len(frames) >= MAX_FRAMES_GIF:
                    break
                duree = frame.info.get("duration", 100)
                frames.append((_reduire(frame.convert("RGBA")), duree))
            return frames if len(frames) > 1 else None
        except Exception as erreur:
            print(f"[popup] Impossible de lire le GIF '{chemin}' : {erreur}")
            return None

    # ------------------------------------------------------------------
    # Affichage d'un événement à l'index donné
    # ------------------------------------------------------------------
    def afficher_evenement(i):
        arreter_media()
        etat["index"] = i
        etat["token"] += 1
        token_actuel = etat["token"]

        evenement = evenements[i]
        couleur = couleur_categorie(evenement["categorie"])
        message = evenement.get("message") or message_par_defaut(evenement["categorie"])

        for widget in zone_photo.winfo_children():
            widget.destroy()
        for widget in zone_scroll.winfo_children():
            widget.destroy()

        etat["taille_cible"] = _calculer_taille_photo(popup)

        # --- Photo / GIF (image fixe ou animée) ---
        widgets["photo"] = tk.Label(zone_photo, bg=_eclaircir_couleur(couleur, 0.85), bd=0)
        widgets["photo"].place(x=0, y=0, relwidth=1, relheight=1)

        chemin_media = chemin_media_pour_popup(evenement)
        extension = _extension(chemin_media) if chemin_media else ""
        media_affiche = False

        if chemin_media and PIL_DISPONIBLE:
            if extension == "gif":
                frames = charger_gif(chemin_media)
                if frames:
                    etat["gif_frames"] = frames
                    etat["gif_index"] = 0
                    jouer_frame_gif(token_actuel)
                    media_affiche = True
                else:
                    try:
                        etat["pil_image_statique"] = _reduire(_ouvrir_image(chemin_media).convert("RGBA"))
                        rendre_image_statique()
                        media_affiche = True
                    except Exception as erreur:
                        print(f"[popup] Impossible de charger l'image '{chemin_media}' : {erreur}")
            else:
                try:
                    etat["pil_image_statique"] = _reduire(_ouvrir_image(chemin_media).convert("RGBA"))
                    rendre_image_statique()
                    media_affiche = True
                except Exception as erreur:
                    print(f"[popup] Impossible de charger l'image '{chemin_media}' : {erreur}")
        elif chemin_media and not PIL_DISPONIBLE:
            print(
                "[popup] Pillow n'est pas installé : impossible d'afficher les images/GIF.\n"
                "[popup] Installe-le avec : pip install pillow"
            )

        if not media_affiche:
            widgets["photo"].configure(text=emoji_categorie(evenement["categorie"]), font=("Segoe UI Emoji", 56))

        # --- Badge de catégorie superposé (coin supérieur gauche de la photo) ---
        widgets["badge"] = tk.Label(
            zone_photo, text=f"  {emoji_categorie(evenement['categorie'])}  {evenement['categorie'].upper()}  ",
            font=("Segoe UI", 9, "bold"), bg="white", fg=couleur,
        )
        widgets["badge"].place(x=15, y=15)

        # --- Carte info : nom + date ---
        carte_info = tk.Frame(zone_scroll, bg="white")
        carte_info.pack(fill="x", padx=15, pady=(15, 0))

        conteneur_info = tk.Frame(carte_info, bg="white", padx=15, pady=15)
        conteneur_info.pack(fill="x")

        widgets["nom"] = tk.Label(
            conteneur_info, text=evenement["nom"], font=("Segoe UI", _calculer_taille_police(popup, 26), "bold"),
            bg="white", fg=COULEUR_TEXTE_PRINCIPAL, anchor="center", justify="center", wraplength=320,
        )
        widgets["nom"].pack(fill="x")

        ligne_sous = tk.Frame(conteneur_info, bg="white")
        ligne_sous.pack(fill="x", pady=(8, 0))

        frame_date = tk.Frame(ligne_sous, bg="white")
        frame_date.pack(side="right")
        widgets["jour"] = tk.Label(
            frame_date, text=str(evenement["jour"]),
            font=("Segoe UI", _calculer_taille_police(popup, 18), "bold"), bg="white", fg=COULEUR_TEXTE_PRINCIPAL,
        )
        widgets["jour"].pack()
        noms_mois = [
            "JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN",
            "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE",
        ]
        widgets["mois"] = tk.Label(
            frame_date, text=noms_mois[evenement["mois"] - 1], font=("Segoe UI", _calculer_taille_police(popup, 9), "bold"),
            bg="white", fg=COULEUR_TEXTE_SECONDAIRE,
        )
        widgets["mois"].pack()

        widgets["categorie"] = tk.Label(
            ligne_sous, text=evenement["categorie"].upper(), font=("Segoe UI", _calculer_taille_police(popup, 10), "bold"),
            bg="white", fg=COULEUR_TEXTE_SECONDAIRE, anchor="w", justify="left", wraplength=200,
        )
        widgets["categorie"].pack(side="left", fill="x", expand=True)

        tk.Frame(carte_info, bg=COULEUR_BORDURE, height=1).pack(fill="x", padx=15)

        # --- Carte message (bordure colorée) ---
        carte_message = tk.Frame(zone_scroll, bg="white", highlightbackground=COULEUR_BORDURE, highlightthickness=1)
        carte_message.pack(fill="x", padx=15, pady=15)

        barre_couleur = tk.Frame(carte_message, bg=couleur, width=4)
        barre_couleur.pack(side="left", fill="y")

        conteneur_message = tk.Frame(carte_message, bg="white", padx=15, pady=15)
        conteneur_message.pack(side="left", fill="both", expand=True)

        ligne_titre_message = tk.Frame(conteneur_message, bg="white")
        ligne_titre_message.pack(fill="x")
        tk.Label(
            ligne_titre_message, text=CITATION_ICONE, font=("Segoe UI", 20, "bold"), bg="white", fg=couleur,
        ).pack(side="left", padx=(0, 6))
        tk.Label(
            ligne_titre_message, text="MESSAGE", font=("Segoe UI", 9, "bold"), bg="white", fg=COULEUR_TEXTE_SECONDAIRE,
        ).pack(side="left")

        widgets["message"] = tk.Label(
            conteneur_message, text=f"« {message} »", font=("Segoe UI", _calculer_taille_police(popup, 11), "italic"),
            bg="white", fg=COULEUR_TEXTE_PRINCIPAL, justify="left", anchor="w", wraplength=280,
        )
        widgets["message"].pack(fill="x", pady=(10, 0))

        if label_compteur is not None:
            label_compteur.configure(text=f"{i + 1} / {len(evenements)}")

        _mettre_a_jour_largeurs_texte()

    # ------------------------------------------------------------------
    # Adaptation continue à la taille de la fenêtre
    # ------------------------------------------------------------------
    def _mettre_a_jour_largeurs_texte():
        largeur_disponible = max(popup.winfo_width() - 90, 180)
        if widgets["message"] is not None:
            widgets["message"].configure(wraplength=largeur_disponible)
        if widgets["nom"] is not None:
            widgets["nom"].configure(wraplength=max(popup.winfo_width() - 60, 200))
        if widgets["categorie"] is not None:
            widgets["categorie"].configure(wraplength=max(popup.winfo_width() - 160, 120))

    def _redimensionner_reellement():
        largeur, hauteur = _calculer_taille_photo(popup)
        etat["taille_cible"] = (largeur, hauteur)
        zone_photo.configure(height=hauteur)

        if widgets["nom"] is not None:
            widgets["nom"].configure(font=("Segoe UI", _calculer_taille_police(popup, 26), "bold"))
        if widgets["categorie"] is not None:
            widgets["categorie"].configure(font=("Segoe UI", _calculer_taille_police(popup, 10), "bold"))
        if widgets["jour"] is not None:
            widgets["jour"].configure(font=("Segoe UI", _calculer_taille_police(popup, 18), "bold"))
        if widgets["mois"] is not None:
            widgets["mois"].configure(font=("Segoe UI", _calculer_taille_police(popup, 9), "bold"))
        if widgets["message"] is not None:
            widgets["message"].configure(font=("Segoe UI", _calculer_taille_police(popup, 11), "italic"))

        _mettre_a_jour_largeurs_texte()

        if etat["pil_image_statique"] is not None:
            rendre_image_statique()

    def _sur_redimensionnement(event=None):
        if etat["apres_id_redim"] is not None:
            try:
                popup.after_cancel(etat["apres_id_redim"])
            except (tk.TclError, ValueError):
                pass
        etat["apres_id_redim"] = popup.after(DELAI_DEBOUNCE_REDIMENSIONNEMENT_MS, _redimensionner_reellement)

    popup.bind("<Configure>", _sur_redimensionnement)

    def naviguer(delta):
        nouvel_index = (etat["index"] + delta) % len(evenements)
        afficher_evenement(nouvel_index)

    # --- Barre de navigation (au-dessus du bouton Fermer, si plusieurs événements) ---
    if len(evenements) > 1:
        ttk.Button(frame_navigation, text="◀ Précédent", command=lambda: naviguer(-1)).pack(side="left")
        label_compteur = tk.Label(
            frame_navigation, text=f"1 / {len(evenements)}", font=("Segoe UI", 9), bg=COULEUR_FOND, fg=COULEUR_TEXTE_SECONDAIRE
        )
        label_compteur.pack(side="left", expand=True)
        ttk.Button(frame_navigation, text="Suivant ▶", command=lambda: naviguer(1)).pack(side="right")

    zone_photo.configure(height=etat["taille_cible"][1])
    afficher_evenement(0)

    popup.title("Événement du jour" if len(evenements) == 1 else "Événements du jour")
    popup.transient(parent)
    popup.grab_set()
