"""
main.py
Point d'entrée de l'application.
Lance la fenêtre principale, puis affiche le popup des événements
du jour si nécessaire (au démarrage).
"""

from ui_principale import FenetrePrincipale
from ui_popup import afficher_popup_du_jour
from data_manager import evenements_du_jour, nettoyer_evenements_expires


def main():
    # Supprime définitivement les événements non récurrents (tout sauf
    # Anniversaire) expirés depuis plus de 30 jours, avant toute autre chose.
    nettoyer_evenements_expires()

    app = FenetrePrincipale()

    # Vérifie les événements du jour et affiche le popup si besoin,
    # juste après l'ouverture de la fenêtre principale.
    evenements_aujourdhui = evenements_du_jour()
    app.after(300, lambda: afficher_popup_du_jour(app, evenements_aujourdhui))

    app.mainloop()


if __name__ == "__main__":
    main()
