# Kikiramènedescroissants ? — contexte pour Claude Code

Application de bureau Windows (Python 3 + Tkinter) de gestion des événements
d'équipe (anniversaires, naissances, départs, etc.). Dossier de déploiement :
`croissants/`, avec un sous-dossier `Images/`. L'utilisateur (Vincent) écrit et
attend les réponses **en français** ; sorties prêtes à copier-coller, sans
méta-commentaire.

## Architecture

| Fichier | Rôle |
|---|---|
| `main.py` | Point d'entrée : nettoyage des événements expirés, fenêtre principale, popup du jour 300 ms après le démarrage |
| `data_manager.py` | Toute la logique et le stockage JSON (événements, fenêtres, dates bloquées, jours fériés, médias) |
| `ui_principale.py` | Fenêtre principale : calendrier `tkcalendar`, 9 prochains événements, menu ⋮, contrôle quotidien à 1h00 |
| `ui_saisie.py` | Formulaire d'ajout / modification (date jour+mois+année, alertes week-end / férié / date bloquée) |
| `ui_popup.py` | Popup des événements du jour (image/GIF affichée en entier, le texte rétrécit en priorité ; fermeture automatique le lendemain ; pas de vidéo) |
| `ui_dates_bloquees.py` | Gestion des dates bloquées (menu ⋮) |
| `systray.py` | Icône de la zone de notification (pystray, thread séparé, actions transmises à Tk par une file lue avec `after()`) |
| `ui_helpers.py`, `theme.py` | Boutons, géométrie des fenêtres, couleurs partagées |
| `build_exe.bat`, `BUILD.md`, `requirements*.txt` | Compilation PyInstaller `--onefile --windowed --hidden-import babel.numbers --hidden-import pystray._win32` |

Les fenêtres sont inspirées de maquettes Stitch.

## Règles métier à respecter

- Les **Anniversaires** se répètent par **jour/mois** (année informative). Les autres catégories sont ponctuelles et datées par leur année (`date_reelle`) ; sans année (anciennes données), elles sont traitées comme récurrentes à l'affichage.
- Jour trop grand pour le mois (29/02 non bissextile, 31/04...) ramené au dernier jour du mois (`_date_du_jour_mois`) ; le formulaire limite les jours au mois choisi.
- Liste « 9 prochains événements » : inclut les événements passés depuis ≤ 3 jours (gris), celui du jour en gras.
- Seuls les **Anniversaires** sont conservés ; les autres catégories sont supprimées de `evenements.json` 30 jours après leur date réelle (sans année : occurrence la plus proche). Le formulaire propose de décaler à la prochaine occurrence une date ponctuelle déjà expirée.
- Week-ends et jours fériés français (Pâques par Gauss) grisés dans le calendrier.
- Contrôle de changement de jour à 1h00 (`after()` récursif) qui déclenche le popup.
- La croix masque la fenêtre (icône dans la zone de notification) ; « Quitter » (menu ⋮ ou clic droit sur l'icône) ferme réellement. Sans pystray, la croix ferme. Le popup est `transient` de la fenêtre principale : la réafficher avant de l'ouvrir.
- **Dates bloquées** : stockées avec année dans `dates_bloquees.json` ; le formulaire teste la date réelle (ponctuel) ou la **prochaine occurrence** (anniversaire) ; en modification, une date inchangée reste autorisée même si elle est bloquée.
- Position et taille des fenêtres mémorisées dans `parametres_fenetres.json`.
- Données écrites à côté de l'exe (`sys.executable` si `sys.frozen`), jamais dans le dossier temporaire PyInstaller.

## Sécurité déjà traitée

Chemins `media` limités à `Images/`, images bornées (25 M pixels, 100 frames GIF, 1000 px), validation des JSON au chargement, écriture atomique avec `.bak` / `.corrompu`, longueurs de texte limitées (100 / 60 / 2000), dépendances figées.
Restent : liens symboliques dans `Images/` (`chemin_image_categorie`), taille des fichiers copiés, purge des `.bak`, exe non signé.

## Points d'attention

- Tkinter n'était pas disponible dans l'environnement cloud : seuls `py_compile` et des tests de logique isolés ont été faits. **Le rendu visuel n'a jamais été vérifié par exécution** ; à tester sous Windows.
- Compilation à faire directement sous Windows.
