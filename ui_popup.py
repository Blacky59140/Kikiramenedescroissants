"""
ui_popup.py
Fenêtre popup présentant un événement du jour : photo/GIF affichée en entier
(format 3:4 vertical prévu), carte d'info (nom + catégorie + date), carte
message (bordure colorée + guillemet), navigation Précédent/Suivant si
plusieurs événements le même jour, et bouton Fermer. Quand la fenêtre est
trop petite, le texte est réduit en priorité, l'image ensuite. Le popup se
ferme tout seul le lendemain s'il est resté ouvert. Style inspiré d'une
maquette réalisée sur Google Stitch.
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

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

PROPORTION_HAUTEUR_PHOTO = 0.40  # part de la fenêtre occupée par l'emoji quand il n'y a pas d'image
HAUTEUR_MIN_PHOTO = 160

# Réduction du texte avant celle de l'image : le facteur appliqué aux polices
# et aux marges descend par pas jusqu'à ce minimum ; ensuite seulement
# l'image rapetisse (toujours entière, bandes de couleur sur les côtés).
FACTEUR_TEXTE_MIN = 0.6
PAS_FACTEUR_TEXTE = 0.05
MARGE_CARTES = 15

DELAI_DEBOUNCE_REDIMENSIONNEMENT_MS = 120
DELAI_MIN_FRAME_MS = 20
DELAI_VERIFICATION_LENDEMAIN_MS = 60_000  # contrôle chaque minute (robuste à la mise en veille)

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


def _redimensionner_contain(image_pil, largeur_cible, hauteur_cible):
    """Redimensionne une image pour qu'elle tienne entièrement dans
    (largeur_cible x hauteur_cible) sans déformation ni recadrage, façon CSS
    `object-fit: contain` (le Label centre l'image, le fond comble le reste)."""
    echelle = min(max(1, largeur_cible) / image_pil.width, max(1, hauteur_cible) / image_pil.height)
    taille = (max(1, int(image_pil.width * echelle)), max(1, int(image_pil.height * echelle)))
    return image_pil.resize(taille, FILTRE_REDIMENSIONNEMENT)


def _taille_police(base_reference, facteur):
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
        "apres_id_lendemain": None,
        "pil_image_statique": None,
        "gif_frames": None,
        "gif_index": 0,
        "ratio_image": None,  # hauteur / largeur du média affiché (None : emoji)
        "taille_cible": (LARGEUR_POPUP_DEFAUT, int(HAUTEUR_POPUP_DEFAUT * PROPORTION_HAUTEUR_PHOTO)),
        "taille_disposee": None,
    }

    # Widgets texte du popup et taille de police de référence (avant réduction)
    widgets = {}
    polices = []  # (widget, taille de référence, style)
    label_compteur = None

    # ------------------------------------------------------------------
    # Structure générale (empilement vertical)
    # ------------------------------------------------------------------
    zone_photo = tk.Frame(popup, bg="#EDEDF2")
    zone_photo.pack(fill="x", side="top")
    zone_photo.pack_propagate(False)

    zone_basse = tk.Frame(popup, bg=COULEUR_FOND)
    zone_basse.pack(fill="x", side="bottom")

    zone_scroll = tk.Frame(popup, bg=COULEUR_FOND)
    zone_scroll.pack(fill="both", expand=True, side="top")

    # --- Bouton Fermer (toujours visible en bas) ---
    def fermer_popup():
        arreter_media()
        for cle in ("apres_id_redim", "apres_id_lendemain"):
            if etat[cle] is not None:
                try:
                    popup.after_cancel(etat[cle])
                except (tk.TclError, ValueError):
                    pass
                etat[cle] = None
        sauvegarder_geometrie_actuelle(popup, "popup")
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", fermer_popup)

    conteneur_bas = tk.Frame(zone_basse, bg=COULEUR_FOND, padx=15, pady=10)
    conteneur_bas.pack(fill="x")

    frame_navigation = tk.Frame(conteneur_bas, bg=COULEUR_FOND)
    if len(evenements) > 1:
        frame_navigation.pack(fill="x", pady=(0, 8))

    bouton_pleine_largeur(conteneur_bas, "✕  FERMER", fermer_popup, COULEUR_BOUTON_PRINCIPAL_BG, COULEUR_BOUTON_PRINCIPAL_FG)

    # --- Fermeture automatique le lendemain, si personne ne l'a fermé avant ---
    date_ouverture = date.today()

    def verifier_lendemain():
        etat["apres_id_lendemain"] = None
        if date.today() != date_ouverture:
            fermer_popup()
            return
        etat["apres_id_lendemain"] = popup.after(DELAI_VERIFICATION_LENDEMAIN_MS, verifier_lendemain)

    etat["apres_id_lendemain"] = popup.after(DELAI_VERIFICATION_LENDEMAIN_MS, verifier_lendemain)

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
        etat["ratio_image"] = None

    # ------------------------------------------------------------------
    # Rendu image statique / GIF (image entière, sans recadrage)
    # ------------------------------------------------------------------
    def _afficher_photo(image_tk):
        popup.images_references.append(image_tk)
        if len(popup.images_references) > 5:
            popup.images_references.pop(0)
        widgets["photo"].configure(image=image_tk, text="")
        widgets["photo"].image = image_tk

    def rendre_image_statique():
        if etat["pil_image_statique"] is None or widgets.get("photo") is None:
            return
        try:
            largeur, hauteur = etat["taille_cible"]
            image_reduite = _redimensionner_contain(etat["pil_image_statique"], largeur, hauteur)
            _afficher_photo(ImageTk.PhotoImage(image_reduite))
        except Exception as erreur:
            print(f"[popup] Erreur de redimensionnement de l'image : {erreur}")

    def jouer_frame_gif(token_appel):
        if token_appel != etat["token"] or not etat["gif_frames"] or widgets.get("photo") is None:
            return
        frame_pil, duree_ms = etat["gif_frames"][etat["gif_index"]]
        try:
            largeur, hauteur = etat["taille_cible"]
            image_reduite = _redimensionner_contain(frame_pil, largeur, hauteur)
            _afficher_photo(ImageTk.PhotoImage(image_reduite))
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

    def charger_media(chemin_media):
        """Charge l'image ou le GIF (sans l'afficher) et retient son ratio. Renvoie True si réussi."""
        if not chemin_media:
            return False
        if not PIL_DISPONIBLE:
            print(
                "[popup] Pillow n'est pas installé : impossible d'afficher les images/GIF.\n"
                "[popup] Installe-le avec : pip install pillow"
            )
            return False
        if _extension(chemin_media) == "gif":
            frames = charger_gif(chemin_media)
            if frames:
                etat["gif_frames"] = frames
                etat["gif_index"] = 0
                premiere = frames[0][0]
                etat["ratio_image"] = premiere.height / premiere.width
                return True
        try:
            etat["pil_image_statique"] = _reduire(_ouvrir_image(chemin_media).convert("RGBA"))
            etat["ratio_image"] = etat["pil_image_statique"].height / etat["pil_image_statique"].width
            return True
        except Exception as erreur:
            print(f"[popup] Impossible de charger l'image '{chemin_media}' : {erreur}")
            return False

    # ------------------------------------------------------------------
    # Affichage d'un événement à l'index donné
    # ------------------------------------------------------------------
    def _label_texte(parent_widget, texte, taille, style, **options):
        label = tk.Label(parent_widget, text=texte, font=("Segoe UI", taille, style), bg="white", **options)
        polices.append((label, taille, style))
        return label

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
        widgets.clear()
        polices.clear()

        # --- Photo / GIF (image fixe ou animée), sans badge superposé ---
        widgets["photo"] = tk.Label(zone_photo, bg=_eclaircir_couleur(couleur, 0.85), bd=0)
        widgets["photo"].place(x=0, y=0, relwidth=1, relheight=1)

        media_affiche = charger_media(chemin_media_pour_popup(evenement))
        if not media_affiche:
            widgets["photo"].configure(text=emoji_categorie(evenement["categorie"]), font=("Segoe UI Emoji", 56))

        # --- Carte info : nom + date ---
        widgets["carte_info"] = carte_info = tk.Frame(zone_scroll, bg="white")
        carte_info.pack(fill="x", padx=MARGE_CARTES, pady=(MARGE_CARTES, 0))

        widgets["conteneur_info"] = conteneur_info = tk.Frame(carte_info, bg="white", padx=15, pady=MARGE_CARTES)
        conteneur_info.pack(fill="x")

        widgets["nom"] = _label_texte(
            conteneur_info, evenement["nom"], 26, "bold",
            fg=COULEUR_TEXTE_PRINCIPAL, anchor="center", justify="center", wraplength=320,
        )
        widgets["nom"].pack(fill="x")

        ligne_sous = tk.Frame(conteneur_info, bg="white")
        ligne_sous.pack(fill="x", pady=(8, 0))

        frame_date = tk.Frame(ligne_sous, bg="white")
        frame_date.pack(side="right")
        _label_texte(frame_date, str(evenement["jour"]), 18, "bold", fg=COULEUR_TEXTE_PRINCIPAL).pack()
        noms_mois = [
            "JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN",
            "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE",
        ]
        _label_texte(frame_date, noms_mois[evenement["mois"] - 1], 9, "bold", fg=COULEUR_TEXTE_SECONDAIRE).pack()

        widgets["categorie"] = _label_texte(
            ligne_sous, evenement["categorie"].upper(), 10, "bold",
            fg=COULEUR_TEXTE_SECONDAIRE, anchor="w", justify="left", wraplength=200,
        )
        widgets["categorie"].pack(side="left", fill="x", expand=True)

        tk.Frame(carte_info, bg=COULEUR_BORDURE, height=1).pack(fill="x", padx=15)

        # --- Carte message (bordure colorée) ---
        widgets["carte_message"] = carte_message = tk.Frame(
            zone_scroll, bg="white", highlightbackground=COULEUR_BORDURE, highlightthickness=1,
        )
        carte_message.pack(fill="x", padx=MARGE_CARTES, pady=MARGE_CARTES)

        barre_couleur = tk.Frame(carte_message, bg=couleur, width=4)
        barre_couleur.pack(side="left", fill="y")

        widgets["conteneur_message"] = conteneur_message = tk.Frame(carte_message, bg="white", padx=15, pady=MARGE_CARTES)
        conteneur_message.pack(side="left", fill="both", expand=True)

        ligne_titre_message = tk.Frame(conteneur_message, bg="white")
        ligne_titre_message.pack(fill="x")
        _label_texte(ligne_titre_message, CITATION_ICONE, 20, "bold", fg=couleur).pack(side="left", padx=(0, 6))
        _label_texte(ligne_titre_message, "MESSAGE", 9, "bold", fg=COULEUR_TEXTE_SECONDAIRE).pack(side="left")

        widgets["message"] = _label_texte(
            conteneur_message, f"« {message} »", 11, "italic",
            fg=COULEUR_TEXTE_PRINCIPAL, justify="left", anchor="w", wraplength=280,
        )
        widgets["message"].pack(fill="x", pady=(10, 0))

        if label_compteur is not None:
            label_compteur.configure(text=f"{i + 1} / {len(evenements)}")

        disposer()
        if etat["gif_frames"]:
            jouer_frame_gif(token_actuel)
        else:
            rendre_image_statique()

    # ------------------------------------------------------------------
    # Adaptation continue à la taille de la fenêtre
    # ------------------------------------------------------------------
    def _taille_popup():
        largeur, hauteur = popup.winfo_width(), popup.winfo_height()
        if largeur <= 1 or hauteur <= 1:  # fenêtre pas encore affichée
            return LARGEUR_POPUP_DEFAUT, HAUTEUR_POPUP_DEFAUT
        return largeur, hauteur

    def _mettre_a_jour_largeurs_texte(largeur):
        if widgets.get("message") is not None:
            widgets["message"].configure(wraplength=max(largeur - 90, 180))
        if widgets.get("nom") is not None:
            widgets["nom"].configure(wraplength=max(largeur - 60, 200))
        if widgets.get("categorie") is not None:
            widgets["categorie"].configure(wraplength=max(largeur - 160, 120))

    def _appliquer_facteur_texte(facteur):
        for label, taille, style in polices:
            label.configure(font=("Segoe UI", _taille_police(taille, facteur), style))
        marge = max(4, int(MARGE_CARTES * facteur))
        if "carte_info" in widgets:
            widgets["conteneur_info"].configure(pady=marge)
            widgets["conteneur_message"].configure(pady=marge)
            widgets["carte_info"].pack_configure(pady=(marge, 0))
            widgets["carte_message"].pack_configure(pady=marge)

    def disposer():
        """
        Répartit la hauteur entre l'image et le texte : l'image vise sa taille
        idéale (pleine largeur, proportions respectées) ; si la place manque,
        le texte est réduit d'abord (jusqu'à FACTEUR_TEXTE_MIN), puis l'image
        rapetisse en restant entière.
        """
        largeur, hauteur = _taille_popup()
        _mettre_a_jour_largeurs_texte(largeur)
        popup.update_idletasks()
        disponible = hauteur - zone_basse.winfo_reqheight()

        if etat["ratio_image"]:
            hauteur_photo_ideale = int(largeur * etat["ratio_image"])
        else:
            hauteur_photo_ideale = max(HAUTEUR_MIN_PHOTO, int(hauteur * PROPORTION_HAUTEUR_PHOTO))

        facteur = max(FACTEUR_TEXTE_MIN, min(largeur / LARGEUR_POPUP_DEFAUT, hauteur / HAUTEUR_POPUP_DEFAUT, 1.8))
        while True:
            _appliquer_facteur_texte(facteur)
            zone_scroll.update_idletasks()
            hauteur_texte = zone_scroll.winfo_reqheight()
            if hauteur_photo_ideale + hauteur_texte <= disponible or facteur <= FACTEUR_TEXTE_MIN:
                break
            facteur = max(FACTEUR_TEXTE_MIN, facteur - PAS_FACTEUR_TEXTE)

        hauteur_photo = max(HAUTEUR_MIN_PHOTO, min(hauteur_photo_ideale, disponible - hauteur_texte))
        etat["taille_cible"] = (largeur, hauteur_photo)
        etat["facteur_texte"] = facteur
        zone_photo.configure(height=hauteur_photo)

    def _redimensionner_reellement():
        etat["apres_id_redim"] = None
        disposer()
        if etat["pil_image_statique"] is not None:
            rendre_image_statique()

    def _sur_redimensionnement(event=None):
        # La liaison sur la Toplevel reçoit aussi les <Configure> des widgets
        # enfants : on ne réagit qu'à un vrai changement de taille de la fenêtre.
        if event is not None and (event.widget is not popup or (event.width, event.height) == etat["taille_disposee"]):
            return
        etat["taille_disposee"] = (event.width, event.height) if event is not None else None
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
