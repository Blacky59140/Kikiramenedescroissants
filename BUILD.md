# Compiler l'application en .exe autonome (PyInstaller)

Cette compilation doit se faire **directement sur Windows** (PyInstaller ne
fait pas de compilation croisée : un .exe compilé sur Linux/Mac ne fonctionne
pas sous Windows, et inversement).

## Étape 1 — Installer les dépendances complètes

Depuis le dossier du projet (celui qui contient `main.py`) :

```
pip install -r requirements-build.txt
```

Les versions des dépendances sont figées dans `requirements.txt` (application)
et `requirements-build.txt` (application + PyInstaller), pour qu'une mise à jour
imprévue d'un paquet ne se retrouve pas dans l'exe. Pour les mettre à jour
volontairement, modifie les numéros de version puis retest l'application.

## Étape 2 — Lancer la compilation

Double-clique sur `build_exe.bat`, ou lance manuellement :

```
pyinstaller --noconfirm --onefile --windowed --name "Kikiramenedescroissants" --hidden-import babel.numbers --hidden-import pystray._win32 main.py
```

**Détail des options :**
- `--onefile` : un seul fichier .exe portable (plus simple à distribuer).
  Alternative : `--onedir` (un dossier avec plusieurs fichiers) — démarrage
  un peu plus rapide, mais moins pratique à déplacer.
- `--windowed` : pas de fenêtre console noire derrière l'application. À
  retirer temporairement si tu veux voir les messages de diagnostic dans la
  console (utile pour déboguer un problème d'image qui ne s'affiche pas,
  comme documenté dans `Images/LISEZMOI.md`).
- `--hidden-import babel.numbers` : **nécessaire**, sinon tkcalendar peut
  planter au lancement (Babel est utilisé en interne pour la traduction du
  calendrier, mais PyInstaller ne le détecte pas toujours automatiquement).
- `--hidden-import pystray._win32` : **nécessaire** pour l'icône de la zone de
  notification (pystray choisit son module Windows au lancement, ce que
  PyInstaller ne voit pas). Sans lui, l'icône n'apparaît pas et la croix
  ferme l'application.

## Étape 3 — Récupérer l'exécutable

Il se trouve dans `dist\Kikiramenedescroissants.exe`.

> Le nom de fichier est une version simplifiée du nom de l'application
> ("Kikiramènedescroissants ?"), sans le "?" ni l'accent — les noms de
> fichiers Windows n'acceptent pas le caractère "?". L'application affiche
> bien son vrai nom complet dans sa barre de titre et son en-tête une fois
> lancée ; seul le nom du fichier .exe est simplifié.

**Avant de le distribuer ou de le lancer pour la première fois :**
- Copie ton dossier `Images\` (s'il contient déjà des médias) à côté de
  `Kikiramenedescroissants.exe`.
- `evenements.json` sera créé automatiquement à côté de l'exe au premier
  lancement — pas besoin de le copier toi-même.

## Pourquoi c'était important de corriger le code avant de compiler

Avant cette mise à jour, `data_manager.py` calculait l'emplacement de
`evenements.json` et `Images/` à partir de l'emplacement du **script**
Python. Une fois compilé avec `--onefile`, PyInstaller extrait le programme
dans un dossier temporaire différent à **chaque lancement** — tes données
auraient donc été stockées dans ce dossier temporaire et **effacées à
chaque fermeture de l'application**. Le code utilise maintenant
`sys.executable` quand l'app est compilée, pour que les données restent
toujours à côté du vrai fichier `.exe`, de façon durable.

## Dépannage

- **"ModuleNotFoundError" au lancement de l'exe** : la bibliothèque
  manquante n'était probablement pas installée au moment de la compilation.
  Réinstalle-la (`pip install ...`) et recompile.
- **Le calendrier plante ou affiche les mois en anglais** : vérifie que
  `--hidden-import babel.numbers` est bien présent dans la commande.
- **L'exe est plus volumineux que prévu (30-50 Mo)** : c'est normal,
  PyInstaller embarque l'interpréteur Python complet, Tkinter (Tcl/Tk) et
  Pillow — ça reste largement raisonnable pour ce type d'application
  (l'app ne gère plus la vidéo, donc pas de dépendance lourde type OpenCV).
- **Antivirus qui bloque l'exe** : les exécutables PyInstaller `--onefile`
  sont parfois signalés à tort par certains antivirus (faux positif
  fréquent avec cet outil). Vérifier sur virustotal.com si besoin, ou
  utiliser `--onedir` qui déclenche moins souvent ce genre d'alerte.
