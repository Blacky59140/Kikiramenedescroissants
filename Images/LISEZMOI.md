# Images par catégorie

Il existe deux façons d'associer un média (image ou GIF animé) à un
popup :

1. **Par catégorie** (ce dossier) : dépose ici un fichier nommé d'après la
   catégorie. Il s'applique à tous les événements de cette catégorie qui
   n'ont pas de média personnalisé.
2. **Par événement** : dans le formulaire de saisie, choisis un fichier via
   le bouton "Parcourir..." — il est alors copié automatiquement ici, et
   n'est utilisé que pour cet événement précis (prioritaire sur le média
   de catégorie).

Ce dossier doit s'appeler `Images` (avec un I majuscule) et se trouver au
même niveau que `main.py`.

## Règle de nommage

Le fichier doit porter le nom de la catégorie, normalisé :
- minuscules
- sans accents
- espaces remplacés par des underscores `_`

(la casse du nom de fichier et de son extension n'a pas d'importance,
la recherche est insensible à la casse)

Exemples :
| Catégorie (telle que saisie) | Nom de fichier attendu     |
|-------------------------------|-----------------------------|
| Anniversaire                  | `anniversaire.png`          |
| Naissance                     | `naissance.png`             |
| Retraite                      | `retraite.png`               |
| Départ                        | `depart.png`                 |
| Arrivée                       | `arrivee.png`                 |
| Nouvelle voiture              | `nouvelle_voiture.png`        |
| Mariage                       | `mariage.png`                 |
| Promotion                     | `promotion.png`               |
| Vacances                      | `vacances.png`                |
| Départ à la retraite          | `depart_a_la_retraite.png`  |

## Formats acceptés

- `.png`, `.gif`, `.ppm`, `.pgm` : fonctionnent nativement, sans rien installer
- `.jpg`, `.jpeg`, `.bmp`, et les PNG "complexes" (avec transparence,
  profils de couleur, entrelacement...) : nécessitent la bibliothèque
  **Pillow**. Si elle n'est pas installée, ces formats peuvent échouer à
  s'afficher (l'application bascule alors sur l'emoji par défaut).

  Pour l'installer : `pip install pillow`

- **GIF animés** : lus en boucle automatiquement (nécessite Pillow).

## Si aucune image n'est trouvée (ou si elle ne peut pas être lue)

Un emoji par défaut est utilisé à la place :
🎂 Anniversaire · 👶 Naissance · 🎉 Retraite · 📦 Départ · 🚪 Arrivée ·
🚗 Nouvelle voiture · 💍 Mariage · 📈 Promotion · 🏖️ Vacances ·
✨ toute autre catégorie

Si une image censée exister ne s'affiche pas, lance l'application depuis
une invite de commandes (pas en double-cliquant) : un message d'erreur
explicite s'affichera dans la console pour indiquer pourquoi l'image n'a
pas pu être chargée.

## Taille de l'image

L'image (ou chaque frame d'un GIF) est automatiquement redimensionnée pour
s'adapter à la taille de la fenêtre popup, y compris quand tu la
redimensionnes en direct. Aucun format de taille particulier n'est requis.

