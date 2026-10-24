"""
theme.py
Constantes de couleurs partagées entre les fenêtres de l'application, pour
un rendu visuel cohérent (inspiré d'une maquette réalisée sur Google Stitch).
Séparé dans son propre module pour éviter un import circulaire entre
ui_principale.py et ui_saisie.py (qui s'importent mutuellement).
"""

COULEUR_FOND = "#F4F5FA"
COULEUR_BORDURE = "#E4E4EE"
COULEUR_TEXTE_PRINCIPAL = "#1E1E2E"
COULEUR_TEXTE_SECONDAIRE = "#8A8A99"
COULEUR_ACCENT_SELECTION = "#6C63FF"
COULEUR_ACCENT_TITRE = "#C99A1E"  # ambre/doré du titre, façon maquette
COULEUR_PLACEHOLDER = "#A6A6B0"
COULEUR_ALERTE = "#B45309"

COULEUR_BOUTON_PRINCIPAL_BG = "#1E1E2E"
COULEUR_BOUTON_PRINCIPAL_FG = "white"
COULEUR_BOUTON_SECONDAIRE_BG = "white"
COULEUR_BOUTON_SECONDAIRE_FG = "#1E1E2E"
