# Kikiramènedescroissants ?

Application de bureau (Python + Tkinter) pour suivre les anniversaires,
naissances, départs en retraite, etc. d'une équipe.

Place l'ensemble de ces fichiers dans un dossier nommé `croissants`
(le sous-dossier `Images` doit rester à côté de `main.py`).

## Lancer l'application

Tkinter est inclus avec Python sous Windows, mais deux bibliothèques sont
nécessaires pour profiter de toutes les fonctionnalités (calendrier, images,
GIF animés) :

```
pip install -r requirements.txt
```

- **tkcalendar** : **obligatoire**, utilisé pour le calendrier mensuel de
  la fenêtre principale (avec traduction française automatique via Babel,
  installé comme dépendance de tkcalendar).
- **Pillow** : nécessaire pour afficher des images (JPG, BMP, PNG avec
  transparence...) et pour l'animation des GIF. Sans Pillow, les images
  ne s'affichent pas (l'application bascule sur un emoji).

Puis lance l'application :

```
python main.py
```

## Fonctionnement

- **Fenêtre principale** :
  - **En-tête** avec le titre et un bouton "⋮" ouvrant un menu (contient
    "🔔 Tester le popup").
  - **Calendrier mensuel** navigable (◀ ▶ pour changer de mois). Les jours
    contenant un événement sont colorés selon la catégorie (survole un jour
    coloré pour voir une infobulle avec le nom et la catégorie). Les
    week-ends et jours fériés français (sans événement) apparaissent en
    **fond gris**. Le jour sélectionné (aujourd'hui par défaut) est mis en
    évidence.
  - **Liste "LES 9 PROCHAINS ÉVÉNEMENTS"** : cartes des 9 événements les
    plus proches chronologiquement, quel que soit l'horizon (indépendante du
    mois affiché par le calendrier). Chaque carte affiche le nom, la date,
    le badge de catégorie, et le message. Cliquer sur une carte la sélectionne (bordure violette) ;
    double-cliquer l'ouvre directement en modification.
  - **Barre du bas** avec 3 icônes : **Saisie** (ajouter un événement),
    **Supprimer** et **Modifier** (agissent sur la carte sélectionnée).
  - Un événement passé depuis **plus de 3 jours** disparaît de la liste.
  - L'événement du **jour même** s'affiche **en gras** dans sa carte.
  - Un événement passé depuis **moins de 3 jours** s'affiche **en gris moyen**.
- **Popup automatique** : à chaque lancement de l'application, si un ou
  plusieurs événements tombent le jour même, une fenêtre s'ouvre
  automatiquement. **L'application reste aussi à l'écoute pendant qu'elle
  tourne** : chaque jour à 1h00 du matin, elle vérifie si on est passé au
  jour suivant (ex. si elle reste ouverte toute la nuit) et déclenche le
  popup automatiquement le cas échéant, sans besoin de relancer l'application.
  Un anniversaire du 29 février apparaît le 28 février les années non
  bissextiles (dans le popup comme dans le calendrier).
  Avec :
  - une **photo/GIF en bandeau** (recadrée pour remplir tout l'espace,
    sans déformation) avec un **badge de catégorie** superposé en haut à
    gauche ;
  - une carte avec le **nom** et la **date** (jour + mois) ;
  - une carte **message** avec bordure colorée selon la catégorie et une
    icône de citation ;
  - un bouton **"✕ FERMER"** pleine largeur en bas.
  - **Le texte et la photo s'adaptent en continu** à la taille de la fenêtre
    (redimensionne la fenêtre pour voir l'effet).
  - Le média peut être une **image fixe** ou un **GIF animé** (lu en boucle).
  - S'il y a plusieurs événements le même jour, des boutons
    "◀ Précédent" / "Suivant ▶" apparaissent au-dessus du bouton Fermer.
- **"🔔 Tester le popup"** (menu "⋮" en haut à droite) : sélectionner une
  carte puis l'utiliser prévisualise son popup exactement comme il
  apparaîtrait le jour J (utile pour vérifier le rendu d'une image/GIF
  ou d'un message avant la date réelle). Sans sélection, il teste avec les
  événements réels du jour.
- **Saisie de la date** : la liste des jours s'adapte au mois choisi (pas de
  31 avril ; 29 jours en février). Pour un événement ponctuel (toute
  catégorie autre qu'Anniversaire), l'**année compte** : le 29 février est
  refusé une année non bissextile, et une date passée depuis plus de 30 jours
  déclenche une question proposant de l'enregistrer à sa prochaine occurrence
  (sinon l'événement serait aussitôt supprimé). Pour un anniversaire,
  l'année reste informative (année de naissance).
- **Alerte week-end/jour férié** : dans le formulaire de saisie, si la date
  choisie (date réelle pour un événement ponctuel, prochaine occurrence pour
  un anniversaire) tombe un samedi, un dimanche ou un jour férié français,
  un message d'avertissement s'affiche sous les champs de date.
- **Média du popup** : deux façons de l'associer :
  1. **Par catégorie** : dépose un fichier dans `Images/` nommé d'après la
     catégorie (ex. `anniversaire.gif`) — voir `Images/LISEZMOI.md`. Il
     s'applique à tous les événements de cette catégorie qui n'ont pas de
     média personnalisé.
  2. **Par événement** (personnalisé) : dans le formulaire de saisie, choisis
     un fichier via "Parcourir..." (il est automatiquement copié dans
     `Images/`), ou sélectionne-en un déjà présent dans la liste déroulante.
     Un média personnalisé est prioritaire sur celui de la catégorie.

  Sans média trouvé, un emoji par défaut est utilisé.

## Stockage des données

Les événements sont enregistrés dans `evenements.json`, créé automatiquement
au premier lancement, dans le même dossier que l'application. Chaque
événement stocke un jour, un mois et une année. Les **anniversaires** se
répètent chaque année sans avoir à les ressaisir (leur année est purement
informative). Les **autres catégories** sont des événements ponctuels datés
par leur année : ils n'apparaissent (liste, calendrier, popup) qu'à leur
date réelle. Un ancien événement ponctuel enregistré sans année est traité
comme récurrent pour l'affichage.

> **Conservation des données** : seule la catégorie **Anniversaire** est
> conservée indéfiniment d'année en année. Toutes les autres catégories
> (Naissance, Mariage, Promotion, etc.) sont considérées comme des
> événements ponctuels : elles sont **supprimées définitivement** de
> `evenements.json` 30 jours après leur date réelle (jour/mois/année ; sans
> année, l'occurrence la plus proche d'aujourd'hui est retenue). Un
> événement saisi pour l'année suivante est donc bien conservé jusqu'à sa date. Ce nettoyage se fait
> automatiquement au démarrage de l'application et à chaque rafraîchissement
> de la fenêtre principale (`data_manager.nettoyer_evenements_expires`).

> **Mémorisation des fenêtres** : la taille et la position de la fenêtre
> principale, du formulaire de saisie et du popup sont sauvegardées dans
> `parametres_fenetres.json` à chaque fermeture, et restaurées à la
> prochaine ouverture. Si une position enregistrée tombe hors de l'écran
> actuel (ex. moniteur externe débranché depuis), elle est ignorée par
> sécurité et la fenêtre s'ouvre à un emplacement par défaut.

> **Note** : la fenêtre principale utilise `evenements_du_mois` pour le
> calendrier et `evenements_a_venir` pour la liste des 9 prochains
> événements. `data_manager.py` conserve aussi `evenements_pour_affichage`,
> `evenement_visible_et_date` (masquage après 3 jours / réapparition à 15
> jours) et `evenements_prochains_jours` (fenêtre de 30 jours), qui ne sont
> plus utilisées et ne tiennent pas compte de l'année des événements
> ponctuels.

## Robustesse et sécurité des données

- **Écriture atomique** : chaque fichier JSON est écrit dans un fichier
  temporaire puis substitué. Une copie `.bak` de la version précédente est
  conservée à côté (`evenements.json.bak`, etc.).
- **Fichier corrompu** : s'il est illisible ou du mauvais type, il est renommé
  en `.corrompu` (jamais écrasé) et la copie `.bak` est utilisée à la place.
- **Validation au chargement** : les événements dont le jour, le mois ou l'id
  sont invalides sont ignorés ; les champs texte sont forcés au bon type. Les
  positions de fenêtre et les dates bloquées invalides sont ignorées.
- **Médias** : le champ `media` d'un événement ne peut désigner qu'un fichier
  situé directement dans `Images/` (chemins absolus, sous-dossiers et `..`
  refusés). Les images de plus de 25 millions de pixels sont refusées, les GIF
  sont limités à 100 frames et chaque image est réduite à 1000 px de côté en
  mémoire.
- **Longueurs maximales** : nom 100 caractères, catégorie 60, message 2 000.
  Le formulaire refuse un texte plus long ; au chargement, les textes
  trop longs d'un JSON modifié sont tronqués.
- Installe l'application dans un dossier dont l'écriture est réservée aux
  personnes autorisées à modifier les événements.

## Dates bloquées

Menu **⋮ > 🚫 Dates bloquées…** : permet d'interdire la création d'événements
à certaines dates (fermeture, congés collectifs, etc.). Dans la zone de
saisie, on peut entrer en une fois plusieurs dates et/ou périodes, séparées
par une virgule, un point-virgule ou un retour à la ligne :

```
24/12/2026, 31/12/2026
03/08/2027 au 21/08/2027
du 01/11/2026 au 02/11/2026
```

- Formats de date acceptés : `JJ/MM/AAAA`, `JJ/MM/AA`, `JJ/MM` (= prochaine occurrence).
- Période : `date1 au date2` ou `date1 - date2` (bornes incluses).
- Les blocages se retirent depuis la même fenêtre (sélection de lignes, multiple possible).
- Dans le calendrier, les jours bloqués sont en rouge clair.
- Dans le formulaire de saisie, un message d'alerte s'affiche, et l'enregistrement
  est refusé, si la date choisie est bloquée (date réelle pour un événement
  ponctuel, **prochaine occurrence** pour un anniversaire).
- Les événements déjà existants ne sont pas modifiés ni supprimés. Un
  événement déjà placé sur une date bloquée reste modifiable (nom, message,
  média...) tant que sa date ne change pas ; seul un déplacement vers une
  date bloquée est refusé.
- Stockage : `dates_bloquees.json`, à côté de l'application.

## Fichiers du projet

| Fichier             | Rôle                                                    |
|----------------------|----------------------------------------------------------|
| `main.py`            | Point d'entrée : lance la fenêtre principale + le popup |
| `data_manager.py`    | Stockage JSON + logique des dates récurrentes            |
| `ui_principale.py`   | Fenêtre principale (liste des événements)                |
| `theme.py`           | Constantes de couleurs partagées (thème visuel)          |
| `ui_helpers.py`      | Composants d'interface réutilisés (bouton pleine largeur)|
| `ui_saisie.py`       | Formulaire de saisie d'un nouvel événement                |
| `ui_dates_bloquees.py` | Fenêtre de gestion des dates bloquées                  |
| `ui_popup.py`        | Fenêtre popup des événements du jour (grand format, images)|
| `requirements.txt`   | Dépendances figées (`requirements-build.txt` : + PyInstaller)|
| `build_exe.bat`      | Script Windows pour compiler l'app en .exe (voir `BUILD.md`)|
| `BUILD.md`           | Guide de compilation en exécutable autonome (PyInstaller)  |

## Compiler en exécutable Windows autonome

Voir **`BUILD.md`** pour compiler l'application en `.exe` autonome avec
PyInstaller (aucune installation de Python nécessaire sur les postes de
destination). Le script `build_exe.bat` automatise la commande.

## Pistes d'évolution possibles

- Lancement automatique au démarrage de Windows (raccourci dans le
  dossier "Démarrage" de Windows, ou tâche planifiée)
- Export de la liste en PDF ou Excel
- Icône dans la barre des tâches (systray) pour rester actif en arrière-plan
