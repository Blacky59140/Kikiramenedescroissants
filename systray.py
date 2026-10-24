"""
systray.py
Icône dans la zone de notification de Windows (à côté de l'horloge), via
pystray : fermer la fenêtre principale la masque au lieu de quitter, et
l'application reste active en arrière-plan (contrôle quotidien de 1h00 et
popup du jour). Clic gauche sur l'icône : réafficher la fenêtre ; clic
droit : menu Ouvrir / Tester le popup / Quitter.
Sans pystray (ou sans Pillow), l'application se ferme normalement.
"""

import queue

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    SYSTRAY_DISPONIBLE = True
except ImportError:
    SYSTRAY_DISPONIBLE = False

from theme import COULEUR_ACCENT_TITRE

TAILLE_ICONE = 64
DELAI_SCRUTATION_MS = 200  # fréquence à laquelle Tkinter traite les clics reçus de l'icône


def _image_icone():
    """Emoji croissant en couleur (police Segoe UI Emoji) ; à défaut, un rond ambré."""
    image = Image.new("RGBA", (TAILLE_ICONE, TAILLE_ICONE), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(image)
    try:
        police = ImageFont.truetype("seguiemj.ttf", 52)
        dessin.text((TAILLE_ICONE // 2, TAILLE_ICONE // 2 + 2), "🥐", font=police, anchor="mm", embedded_color=True)
    except (OSError, ValueError):
        dessin.ellipse((4, 4, TAILLE_ICONE - 4, TAILLE_ICONE - 4), fill=COULEUR_ACCENT_TITRE)
    return image


class IconeSystray:
    """
    Icône de la zone de notification. pystray tourne dans son propre thread :
    ses clics ne touchent jamais Tkinter directement (non thread-safe), ils
    sont déposés dans une file que la fenêtre principale lit via after().
    """

    def __init__(self, fenetre, afficher, tester_popup, quitter):
        self._fenetre = fenetre
        self._actions = {"afficher": afficher, "tester": tester_popup, "quitter": quitter}
        self._file = queue.Queue()
        self._notification_faite = False

        menu = pystray.Menu(
            pystray.MenuItem("Ouvrir", lambda: self._file.put("afficher"), default=True),
            pystray.MenuItem("Tester le popup", lambda: self._file.put("tester")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", lambda: self._file.put("quitter")),
        )
        self._icone = pystray.Icon("kikiramenedescroissants", _image_icone(), "Kikiramènedescroissants ?", menu)
        self._icone.run_detached()
        self._fenetre.after(DELAI_SCRUTATION_MS, self._traiter_actions)

    def _traiter_actions(self):
        try:
            while True:
                action = self._file.get_nowait()
                self._actions[action]()
                if action == "quitter":
                    return  # fenêtre détruite : plus rien à planifier
        except queue.Empty:
            pass
        self._fenetre.after(DELAI_SCRUTATION_MS, self._traiter_actions)

    def signaler_mise_en_arriere_plan(self):
        """Bulle Windows affichée la première fois que la fenêtre est masquée."""
        if self._notification_faite:
            return
        self._notification_faite = True
        try:
            self._icone.notify(
                "L'application reste active ici. Clic droit sur l'icône pour la quitter.",
                "Kikiramènedescroissants ?",
            )
        except NotImplementedError:
            pass

    def arreter(self):
        self._icone.stop()
