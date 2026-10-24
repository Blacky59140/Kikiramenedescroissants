"""
data_manager.py
Gestion du stockage (JSON local) et de la logique métier :
- calcul de la prochaine occurrence d'un événement récurrent
- règle d'affichage (masqué 3 jours après la date)
- tri, ajout, suppression
"""

import calendar
import json
import os
import shutil
import sys
import unicodedata
import uuid
from datetime import date, timedelta


def _dossier_application():
    """
    Retourne le dossier où se trouve l'application :
    - une fois compilée avec PyInstaller (--onefile ou --onedir) : le dossier
      contenant l'exécutable .exe (PAS le dossier temporaire d'extraction
      sys._MEIPASS, qui est effacé à chaque fermeture — y stocker des
      données les ferait disparaître à chaque redémarrage) ;
    - en développement (script Python normal) : le dossier du script.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


FICHIER_DONNEES = os.path.join(_dossier_application(), "evenements.json")
DOSSIER_IMAGES = os.path.join(_dossier_application(), "Images")
FICHIER_PARAMETRES_FENETRES = os.path.join(_dossier_application(), "parametres_fenetres.json")
FICHIER_DATES_BLOQUEES = os.path.join(_dossier_application(), "dates_bloquees.json")

# Longueurs maximales des champs texte (protection contre les saisies démesurées)
LONGUEUR_MAX_NOM = 100
LONGUEUR_MAX_CATEGORIE = 60
LONGUEUR_MAX_MESSAGE = 2000
LONGUEUR_MAX_MEDIA = 255

JOURS_AFFICHAGE_APRES_EVENEMENT = 3  # un événement reste visible 3 jours après sa date
JOURS_CONSERVATION_EVENEMENTS_NON_RECURRENTS = 30  # au-delà, suppression définitive (sauf Anniversaire)
JOURS_REAPPARITION_AVANT_EVENEMENT = 15  # un événement masqué réapparaît 15 jours avant sa prochaine date

# .png/.gif/.ppm/.pgm sont lus nativement par Tkinter ; .jpg/.jpeg/.bmp nécessitent Pillow
EXTENSIONS_IMAGES_SUPPORTEES = [".png", ".gif", ".ppm", ".pgm", ".jpg", ".jpeg", ".bmp"]
EXTENSIONS_MEDIA_SUPPORTEES = EXTENSIONS_IMAGES_SUPPORTEES

EMOJIS_PAR_DEFAUT = {
    "anniversaire": "🎂",
    "naissance": "👶",
    "retraite": "🎉",
    "départ": "📦",
    "arrivée": "🚪",
    "nouvelle voiture": "🚗",
    "mariage": "💍",
    "promotion": "📈",
    "vacances": "🏖️",
    "oups, j'ai buggé": "🐛",
}
EMOJI_GENERIQUE = "✨"


# --- Lecture / écriture JSON sécurisées ---

def _ecrire_json_atomique(chemin, donnees):
    """
    Écrit `donnees` dans `chemin` de façon atomique : écriture dans un fichier
    temporaire puis remplacement (os.replace). Une copie .bak du dernier
    fichier valide est conservée. Un plantage pendant l'écriture ne peut donc
    plus tronquer le fichier de données.
    """
    temporaire = f"{chemin}.{os.getpid()}.tmp"
    try:
        with open(temporaire, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(chemin):
            try:
                shutil.copy2(chemin, chemin + ".bak")
            except OSError:
                pass  # la sauvegarde de secours ne doit jamais bloquer l'écriture
        os.replace(temporaire, chemin)
    finally:
        if os.path.exists(temporaire):
            try:
                os.remove(temporaire)
            except OSError:
                pass


def _lire_json_securise(chemin, type_attendu, defaut):
    """
    Lit un fichier JSON et vérifie son type de plus haut niveau (list/dict).
    Si le fichier est illisible ou du mauvais type, il est renommé en
    .corrompu (pour ne pas être écrasé) et la copie .bak est essayée. En
    dernier recours, retourne `defaut`.
    """
    for candidat in (chemin, chemin + ".bak"):
        if not os.path.exists(candidat):
            continue
        try:
            with open(candidat, "r", encoding="utf-8") as f:
                donnees = json.load(f)
            if isinstance(donnees, type_attendu):
                return donnees
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            pass
        if candidat == chemin:
            try:
                os.replace(chemin, chemin + ".corrompu")
            except OSError:
                pass
    return defaut


def _entier_borne(valeur, minimum, maximum):
    """Retourne `valeur` si c'est un entier (hors booléen) compris dans [minimum, maximum], sinon None."""
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        return None
    return valeur if minimum <= valeur <= maximum else None


def _texte(valeur, maximum=None):
    """Retourne `valeur` si c'est une chaîne (tronquée à `maximum` caractères), sinon ''."""
    if not isinstance(valeur, str):
        return ""
    return valeur[:maximum] if maximum else valeur


def _evenement_valide(e):
    """Retourne l'événement normalisé (types garantis), ou None s'il est inexploitable."""
    if not isinstance(e, dict):
        return None
    jour = _entier_borne(e.get("jour"), 1, 31)
    mois = _entier_borne(e.get("mois"), 1, 12)
    if jour is None or mois is None:
        return None
    jour = min(jour, jours_max_du_mois(mois))  # ex : un 31/02 d'un JSON modifié devient 29/02
    identifiant = e.get("id")
    if not isinstance(identifiant, str) or not identifiant:
        return None
    return {
        "id": identifiant,
        "nom": _texte(e.get("nom"), LONGUEUR_MAX_NOM),
        "jour": jour,
        "mois": mois,
        "annee": _entier_borne(e.get("annee"), 1, 9999),
        "categorie": _texte(e.get("categorie"), LONGUEUR_MAX_CATEGORIE),
        "message": _texte(e.get("message"), LONGUEUR_MAX_MESSAGE),
        "media": _texte(e.get("media"), LONGUEUR_MAX_MEDIA),
    }


def charger_evenements():
    """Charge les événements depuis le fichier JSON (validés, types garantis). Crée le fichier s'il n'existe pas."""
    if not os.path.exists(FICHIER_DONNEES) and not os.path.exists(FICHIER_DONNEES + ".bak"):
        sauvegarder_evenements([])
        return []
    donnees = _lire_json_securise(FICHIER_DONNEES, list, [])
    return [e for e in (_evenement_valide(x) for x in donnees) if e is not None]


def sauvegarder_evenements(evenements):
    """Écrit la liste des événements dans le fichier JSON (écriture atomique)."""
    _ecrire_json_atomique(FICHIER_DONNEES, evenements)


# --- Mémorisation de la taille/position des fenêtres entre deux lancements ---

def charger_parametres_fenetres():
    """Charge les tailles/positions de fenêtres sauvegardées. Retourne un dict vide si le fichier n'existe pas ou est corrompu."""
    return _lire_json_securise(FICHIER_PARAMETRES_FENETRES, dict, {})


def sauvegarder_geometrie_fenetre(nom_fenetre, largeur, hauteur, x, y):
    """Enregistre la taille et la position d'une fenêtre, identifiée par un nom (ex : 'principale', 'saisie', 'popup')."""
    parametres = charger_parametres_fenetres()
    parametres[nom_fenetre] = {"largeur": largeur, "hauteur": hauteur, "x": x, "y": y}
    try:
        _ecrire_json_atomique(FICHIER_PARAMETRES_FENETRES, parametres)
    except OSError:
        pass  # on ne bloque jamais la fermeture de l'application pour ça


def obtenir_geometrie_fenetre(nom_fenetre):
    """Retourne (largeur, hauteur, x, y) sauvegardés pour cette fenêtre, ou None si absent ou invalide."""
    donnees = charger_parametres_fenetres().get(nom_fenetre)
    if not isinstance(donnees, dict):
        return None
    largeur = _entier_borne(donnees.get("largeur"), 200, 10000)
    hauteur = _entier_borne(donnees.get("hauteur"), 200, 10000)
    x = _entier_borne(donnees.get("x"), -10000, 20000)
    y = _entier_borne(donnees.get("y"), -10000, 20000)
    if None in (largeur, hauteur, x, y):
        return None
    return largeur, hauteur, x, y


def ajouter_evenement(nom, jour, mois, categorie, message="", media="", annee=None):
    """Ajoute un nouvel événement et le sauvegarde. `media` est le nom de
    fichier (dans Images/) à utiliser pour ce popup, ou "" pour utiliser
    l'image par défaut de la catégorie. `annee` est purement informative
    (année d'origine de l'événement, ex : année de naissance) : elle n'est
    JAMAIS utilisée pour la récurrence ni le masquage, qui restent basés
    uniquement sur jour/mois."""
    evenements = charger_evenements()
    nouvel_evenement = {
        "id": str(uuid.uuid4()),
        "nom": nom.strip()[:LONGUEUR_MAX_NOM],
        "jour": int(jour),
        "mois": int(mois),
        "annee": int(annee) if annee else None,
        "categorie": categorie.strip()[:LONGUEUR_MAX_CATEGORIE],
        "message": message.strip()[:LONGUEUR_MAX_MESSAGE],
        "media": media.strip()[:LONGUEUR_MAX_MEDIA],
    }
    evenements.append(nouvel_evenement)
    sauvegarder_evenements(evenements)
    return nouvel_evenement


def supprimer_evenement(id_evenement):
    """Supprime un événement par son id."""
    evenements = charger_evenements()
    evenements = [e for e in evenements if e["id"] != id_evenement]
    sauvegarder_evenements(evenements)


def nettoyer_evenements_expires(aujourdhui=None):
    """
    Supprime DÉFINITIVEMENT (dans evenements.json) les événements dont la
    catégorie n'est PAS "Anniversaire" et dont la date réelle (jour/mois/année)
    est passée depuis plus de JOURS_CONSERVATION_EVENEMENTS_NON_RECURRENTS jours.
    Les anniversaires sont conservés indéfiniment (ils se répètent chaque
    année) ; toutes les autres catégories sont considérées comme des
    événements ponctuels qui n'ont plus lieu d'être conservés une fois
    passés. Un événement ponctuel sans année (anciennes données) est daté
    par son occurrence la plus proche d'aujourd'hui. Retourne la liste des
    événements supprimés.
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    evenements = charger_evenements()
    conserves = []
    supprimes = []

    for e in evenements:
        if est_anniversaire(e):
            conserves.append(e)
            continue

        date_evenement = date_reelle(e) or _occurrence_la_plus_proche(e["jour"], e["mois"], aujourdhui)
        ecart = (date_evenement - aujourdhui).days

        if ecart < -JOURS_CONSERVATION_EVENEMENTS_NON_RECURRENTS:
            supprimes.append(e)
        else:
            conserves.append(e)

    if supprimes:
        sauvegarder_evenements(conserves)

    return supprimes


def obtenir_evenement(id_evenement):
    """Retourne un événement par son id, ou None s'il n'existe pas."""
    evenements = charger_evenements()
    for e in evenements:
        if e["id"] == id_evenement:
            return e
    return None


def modifier_evenement(id_evenement, nom, jour, mois, categorie, message="", media="", annee=None):
    """Met à jour un événement existant. Retourne True si trouvé et modifié, False sinon."""
    evenements = charger_evenements()
    for e in evenements:
        if e["id"] == id_evenement:
            e["nom"] = nom.strip()[:LONGUEUR_MAX_NOM]
            e["jour"] = int(jour)
            e["mois"] = int(mois)
            e["annee"] = int(annee) if annee else None
            e["categorie"] = categorie.strip()[:LONGUEUR_MAX_CATEGORIE]
            e["message"] = message.strip()[:LONGUEUR_MAX_MESSAGE]
            e["media"] = media.strip()[:LONGUEUR_MAX_MEDIA]
            sauvegarder_evenements(evenements)
            return True
    return False


def jours_max_du_mois(mois, annee=None):
    """Nombre de jours du mois. Sans année, février compte 29 jours (anniversaire d'un 29 février)."""
    return calendar.monthrange(annee or 2000, mois)[1]  # 2000 est bissextile


def _date_du_jour_mois(jour, mois, annee):
    """Construit une date ; un jour trop grand pour le mois (29 février d'une année
    non bissextile, 31/04...) est ramené au dernier jour du mois."""
    return date(annee, mois, min(jour, jours_max_du_mois(mois, annee)))


def est_anniversaire(evenement):
    """Seuls les anniversaires se répètent chaque année ; les autres catégories sont ponctuelles."""
    return evenement["categorie"].strip().lower() == "anniversaire"


def date_reelle(evenement):
    """
    Date effective d'un événement ponctuel (catégorie autre qu'Anniversaire,
    avec une année), ou None s'il se répète chaque année : anniversaire
    (l'année n'est alors qu'informative) ou ancien événement sans année.
    """
    if est_anniversaire(evenement) or not evenement.get("annee"):
        return None
    return _date_du_jour_mois(evenement["jour"], evenement["mois"], evenement["annee"])


def date_a_afficher(evenement, aujourdhui=None):
    """Date réelle d'un événement ponctuel, sinon prochaine occurrence d'un événement récurrent."""
    return date_reelle(evenement) or prochaine_occurrence(evenement["jour"], evenement["mois"], aujourdhui)


def _occurrence_la_plus_proche(jour, mois, aujourdhui):
    """Occurrence (année précédente, en cours ou suivante) la plus proche d'aujourd'hui."""
    candidates = [_date_du_jour_mois(jour, mois, aujourdhui.year + d) for d in (-1, 0, 1)]
    return min(candidates, key=lambda d: abs((d - aujourdhui).days))


def prochaine_occurrence(jour, mois, aujourdhui=None):
    """
    Calcule la prochaine date d'occurrence d'un événement récurrent (utilisée
    par exemple par le popup) :
    - si l'événement de cette année est à venir, ou passé de
      JOURS_AFFICHAGE_APRES_EVENEMENT jours ou moins -> on garde la date de cette année
    - sinon (déjà passé de plus de X jours) -> on prend la date de l'année prochaine
    Ne présage pas de la visibilité dans la liste (voir evenement_visible_et_date).
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    date_cette_annee = _date_du_jour_mois(jour, mois, aujourdhui.year)
    ecart = (date_cette_annee - aujourdhui).days

    if ecart >= -JOURS_AFFICHAGE_APRES_EVENEMENT:
        return date_cette_annee
    else:
        return _date_du_jour_mois(jour, mois, aujourdhui.year + 1)


def evenement_visible_et_date(jour, mois, aujourdhui=None):
    """
    Détermine si un événement doit être visible dans la liste "à venir", et
    avec quelle date d'affichage :
    - à venir cette année (quel que soit l'horizon), ou passé de
      JOURS_AFFICHAGE_APRES_EVENEMENT jours ou moins -> visible, date de cette année
    - passé de plus de JOURS_AFFICHAGE_APRES_EVENEMENT jours -> masqué, SAUF si on
      est entré dans la fenêtre des JOURS_REAPPARITION_AVANT_EVENEMENT jours
      précédant sa prochaine occurrence (l'année suivante), auquel cas il
      réapparaît avec cette date-là.
    Retourne un tuple (visible: bool, date_affichage: date).
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    date_cette_annee = _date_du_jour_mois(jour, mois, aujourdhui.year)
    ecart_cette_annee = (date_cette_annee - aujourdhui).days

    if ecart_cette_annee >= -JOURS_AFFICHAGE_APRES_EVENEMENT:
        return True, date_cette_annee

    date_annee_prochaine = _date_du_jour_mois(jour, mois, aujourdhui.year + 1)
    ecart_prochaine = (date_annee_prochaine - aujourdhui).days

    if ecart_prochaine <= JOURS_REAPPARITION_AVANT_EVENEMENT:
        return True, date_annee_prochaine

    return False, date_annee_prochaine


def evenements_pour_affichage(aujourdhui=None):
    """
    Retourne la liste des événements enrichis d'une date d'affichage calculée,
    triés par date la plus proche. Un événement passé depuis plus de
    JOURS_AFFICHAGE_APRES_EVENEMENT jours est masqué (absent du résultat)
    jusqu'à ce qu'on entre dans la fenêtre des JOURS_REAPPARITION_AVANT_EVENEMENT
    jours précédant sa prochaine occurrence.
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    evenements = charger_evenements()
    resultat = []
    for e in evenements:
        visible, date_affichage = evenement_visible_et_date(e["jour"], e["mois"], aujourdhui)
        if visible:
            resultat.append({**e, "date_affichage": date_affichage})

    resultat.sort(key=lambda e: e["date_affichage"])
    return resultat


def evenements_du_jour(aujourdhui=None):
    """
    Retourne les événements qui tombent aujourd'hui : date réelle pour un
    événement ponctuel, jour/mois de l'année en cours pour un événement
    récurrent (un 29 février tombe le 28 les années non bissextiles, comme
    dans le calendrier).
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    evenements = charger_evenements()
    return [
        e for e in evenements
        if (date_reelle(e) or _date_du_jour_mois(e["jour"], e["mois"], aujourdhui.year)) == aujourdhui
    ]


def message_par_defaut(categorie):
    """Génère un message par défaut selon la catégorie si l'utilisateur n'en a pas saisi."""
    categorie_lower = categorie.strip().lower()
    messages = {
        "anniversaire": "Bon anniversaire !",
        "naissance": "Félicitations pour cette naissance !",
        "retraite": "Bonne retraite !",
        "départ": "Bonne route pour la suite !",
        "arrivée": "Bienvenue dans l'équipe !",
        "nouvelle voiture": "Félicitations pour cette nouvelle voiture !",
        "mariage": "Tous nos vœux de bonheur !",
        "promotion": "Félicitations pour cette promotion !",
        "vacances": "Bonnes vacances !",
        "oups, j'ai buggé": "Ça arrive aux meilleurs ! On corrige et on repart 🐛",
    }
    return messages.get(categorie_lower, f"Bonne nouvelle : {categorie} !")


def _normaliser_nom_categorie(categorie):
    """Normalise un nom de catégorie pour en faire un nom de fichier : minuscules, sans accents, sans ponctuation, espaces -> underscores."""
    texte = unicodedata.normalize("NFKD", categorie).encode("ascii", "ignore").decode("ascii")
    texte = texte.strip().lower()
    texte = "".join(c if (c.isalnum() or c == " ") else "" for c in texte)
    texte = "_".join(texte.split())
    return texte


def chemin_image_categorie(categorie):
    """
    Cherche un média (image ou GIF) correspondant à la catégorie dans
    le dossier `Images/`. Le fichier doit s'appeler comme la catégorie
    normalisée (ex : catégorie "Anniversaire" -> fichier "anniversaire.png"
    ou "anniversaire.gif"). Recherche insensible à la casse.
    Retourne le chemin trouvé, ou None si aucun média n'existe pour cette catégorie.
    """
    if not os.path.isdir(DOSSIER_IMAGES):
        return None

    nom_normalise = _normaliser_nom_categorie(categorie)
    extensions_normalisees = {ext.lower() for ext in EXTENSIONS_MEDIA_SUPPORTEES}

    for nom_fichier in os.listdir(DOSSIER_IMAGES):
        racine, extension = os.path.splitext(nom_fichier)
        if racine.lower() == nom_normalise and extension.lower() in extensions_normalisees:
            return os.path.join(DOSSIER_IMAGES, nom_fichier)

    return None


def _chemin_sur_dans_images(nom_media):
    """
    Retourne le chemin absolu de `nom_media` s'il désigne bien un fichier
    situé directement dans Images/ (pas de chemin absolu, de sous-dossier ni
    de « .. »), sinon None. Protège contre une traversée de chemin via un
    evenements.json modifié.
    """
    nom_media = (nom_media or "").strip()
    if not nom_media or nom_media != os.path.basename(nom_media.replace("\\", "/")):
        return None
    if os.path.splitext(nom_media)[1].lower() not in {e.lower() for e in EXTENSIONS_MEDIA_SUPPORTEES}:
        return None
    dossier = os.path.realpath(DOSSIER_IMAGES)
    chemin = os.path.realpath(os.path.join(dossier, nom_media))
    if os.path.dirname(chemin) != dossier or not os.path.isfile(chemin):
        return None
    return chemin


def chemin_media_evenement(evenement):
    """
    Retourne le chemin du média personnalisé d'un événement (choisi à la
    saisie), ou None si l'événement n'en a pas, que le fichier n'existe
    plus dans Images/ ou que le nom est suspect (chemin hors de Images/).
    """
    return _chemin_sur_dans_images(evenement.get("media"))


def chemin_media_pour_popup(evenement):
    """
    Détermine le média à afficher dans le popup pour cet événement :
    priorité au média personnalisé de l'événement, sinon le média par
    défaut de sa catégorie, sinon None (l'appelant affichera un emoji).
    """
    return chemin_media_evenement(evenement) or chemin_image_categorie(evenement["categorie"])


def lister_medias_disponibles():
    """Retourne la liste triée des fichiers présents dans Images/ (pour un menu déroulant de sélection)."""
    if not os.path.isdir(DOSSIER_IMAGES):
        return []
    extensions_normalisees = {ext.lower() for ext in EXTENSIONS_MEDIA_SUPPORTEES}
    fichiers = [
        f for f in os.listdir(DOSSIER_IMAGES)
        if os.path.splitext(f)[1].lower() in extensions_normalisees
    ]
    return sorted(fichiers, key=str.lower)


def copier_media_vers_images(chemin_source):
    """
    Copie un fichier choisi par l'utilisateur (via une boîte de dialogue)
    dans le dossier Images/, en évitant d'écraser un fichier existant du
    même nom. Si le fichier source se trouve déjà dans Images/, ne fait
    rien. Retourne le nom de fichier final (relatif à Images/).
    """
    os.makedirs(DOSSIER_IMAGES, exist_ok=True)
    chemin_source = os.path.abspath(chemin_source)

    # Le fichier est déjà dans Images/ : rien à copier
    if os.path.dirname(chemin_source) == os.path.abspath(DOSSIER_IMAGES):
        return os.path.basename(chemin_source)

    nom_fichier = os.path.basename(chemin_source)
    racine, extension = os.path.splitext(nom_fichier)
    destination = os.path.join(DOSSIER_IMAGES, nom_fichier)

    compteur = 1
    while os.path.exists(destination):
        nom_fichier = f"{racine}_{compteur}{extension}"
        destination = os.path.join(DOSSIER_IMAGES, nom_fichier)
        compteur += 1

    shutil.copy2(chemin_source, destination)
    return nom_fichier


def emoji_categorie(categorie):
    """Retourne un emoji par défaut pour la catégorie, utilisé si aucune image n'est disponible."""
    return EMOJIS_PAR_DEFAUT.get(categorie.strip().lower(), EMOJI_GENERIQUE)


# --- Couleurs par catégorie (calendrier, barre latérale des cartes, badges) ---

COULEURS_CATEGORIE = {
    "anniversaire": "#F5C518",       # jaune/ambre
    "naissance": "#4A90D9",          # bleu
    "retraite": "#43A047",           # vert
    "départ": "#8D6E63",             # brun (valise/voyage)
    "arrivée": "#26A69A",            # bleu-vert (accueil)
    "nouvelle voiture": "#546E7A",   # gris-bleu acier
    "mariage": "#EC407A",            # rose
    "promotion": "#5C6BC0",          # indigo (professionnel)
    "vacances": "#FF7043",           # orange corail
    "oups, j'ai buggé": "#E53935",   # rouge (alerte, avec humour)
}
COULEUR_GENERIQUE = "#9C6ADE"  # violet, pour toute autre catégorie


def couleur_categorie(categorie):
    """Retourne une couleur vive associée à la catégorie (barre des cartes, marqueurs du calendrier)."""
    return COULEURS_CATEGORIE.get(categorie.strip().lower(), COULEUR_GENERIQUE)


def _eclaircir_couleur(couleur_hex, quantite=0.82):
    """Mélange une couleur hexadécimale avec du blanc pour obtenir une teinte pastel (0=inchangé, 1=blanc pur)."""
    couleur_hex = couleur_hex.lstrip("#")
    r, g, b = int(couleur_hex[0:2], 16), int(couleur_hex[2:4], 16), int(couleur_hex[4:6], 16)
    r = int(r + (255 - r) * quantite)
    g = int(g + (255 - g) * quantite)
    b = int(b + (255 - b) * quantite)
    return f"#{r:02x}{g:02x}{b:02x}"


def couleurs_badge_categorie(categorie):
    """Retourne (couleur_fond_pastel, couleur_texte_vive) pour le badge de catégorie affiché sur une carte."""
    couleur_vive = couleur_categorie(categorie)
    return _eclaircir_couleur(couleur_vive), couleur_vive


def normaliser_nom_categorie(categorie):
    """Version publique de la normalisation d'un nom de catégorie (utile pour nommer les tags du calendrier)."""
    return _normaliser_nom_categorie(categorie)


def evenements_a_venir(nombre=9, aujourdhui=None):
    """
    Retourne les `nombre` prochains événements les plus proches chronologiquement,
    tous mois/années confondus (sans limite de fenêtre en jours). Inclut aussi
    les événements passés depuis JOURS_AFFICHAGE_APRES_EVENEMENT jours ou moins,
    pour affichage en gris avant qu'ils ne disparaissent. Utilisé par la liste
    "prochains événements" de la fenêtre principale (remplace l'ancienne
    fenêtre glissante de 30 jours par un nombre fixe d'événements affichés).
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    evenements = charger_evenements()
    resultat = []
    for e in evenements:
        occurrence = date_a_afficher(e, aujourdhui)
        ecart = (occurrence - aujourdhui).days
        if ecart >= -JOURS_AFFICHAGE_APRES_EVENEMENT:
            resultat.append({**e, "date_affichage": occurrence})

    resultat.sort(key=lambda e: e["date_affichage"])
    return resultat[:nombre]


def evenements_prochains_jours(nombre_jours=30, aujourdhui=None):
    """
    Retourne les événements dont la prochaine occurrence tombe dans les
    `nombre_jours` prochains jours (inclus), qu'elle soit ce mois-ci ou un
    mois suivant (fenêtre glissante, sans se soucier des limites de mois
    calendaires). Inclut aussi les événements passés depuis
    JOURS_AFFICHAGE_APRES_EVENEMENT jours ou moins, pour affichage en gris
    avant qu'ils ne disparaissent.

    Non utilisée par la fenêtre principale actuelle (qui utilise désormais
    evenements_a_venir, basée sur un nombre fixe d'événements plutôt qu'une
    fenêtre en jours) ; conservée si besoin de la réutiliser ailleurs.
    """
    if aujourdhui is None:
        aujourdhui = date.today()

    evenements = charger_evenements()
    resultat = []
    for e in evenements:
        occurrence = prochaine_occurrence(e["jour"], e["mois"], aujourdhui)
        ecart = (occurrence - aujourdhui).days
        if -JOURS_AFFICHAGE_APRES_EVENEMENT <= ecart <= nombre_jours:
            resultat.append({**e, "date_affichage": occurrence})

    resultat.sort(key=lambda e: e["date_affichage"])
    return resultat


def evenements_du_mois(mois, annee):
    """
    Retourne tous les événements qui tombent dans le mois `mois` de l'année
    `annee` : les événements récurrents sont rejoués chaque année, les
    événements ponctuels n'apparaissent que dans leur année réelle.
    Contrairement à evenements_pour_affichage, ne masque rien d'autre :
    montre tout ce qui tombe dans ce mois, quelle que soit sa position dans
    le temps. Utilisé par la vue calendrier mensuelle de la fenêtre principale.
    """
    resultat = []
    for e in charger_evenements():
        d = date_reelle(e)
        if d is None and e["mois"] == mois:
            d = _date_du_jour_mois(e["jour"], mois, annee)
        if d is not None and d.year == annee and d.month == mois:
            resultat.append({**e, "date_affichage": d})
    resultat.sort(key=lambda e: e["date_affichage"])
    return resultat


# --- Jours fériés français et week-ends ---

def _dimanche_paques(annee):
    """Calcule la date du dimanche de Pâques pour une année donnée (algorithme de Gauss)."""
    a = annee % 19
    b = annee // 100
    c = annee % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = ((h + l - 7 * m + 114) % 31) + 1
    return date(annee, mois, jour)


def jours_feries(annee):
    """Retourne l'ensemble des jours fériés français (dates fixes + mobiles liées à Pâques) pour l'année donnée."""
    paques = _dimanche_paques(annee)
    return {
        date(annee, 1, 1),    # Jour de l'an
        date(annee, 5, 1),    # Fête du travail
        date(annee, 5, 8),    # Victoire 1945
        date(annee, 7, 14),   # Fête nationale
        date(annee, 8, 15),   # Assomption
        date(annee, 11, 1),   # Toussaint
        date(annee, 11, 11),  # Armistice
        date(annee, 12, 25),  # Noël
        paques + timedelta(days=1),   # Lundi de Pâques
        paques + timedelta(days=39),  # Ascension
        paques + timedelta(days=50),  # Lundi de Pentecôte
    }


def est_jour_ferie(une_date):
    """Indique si la date donnée est un jour férié français."""
    return une_date in jours_feries(une_date.year)


def est_weekend(une_date):
    """Indique si la date donnée est un samedi ou un dimanche."""
    return une_date.weekday() >= 5



# ---------------------------------------------------------------------------
# Dates bloquées (impossible de créer un événement à ces dates)
# ---------------------------------------------------------------------------

def charger_dates_bloquees():
    """Retourne la liste des blocages : [{"id", "debut", "fin"}] (dates ISO, fin >= debut), validés."""
    donnees = _lire_json_securise(FICHIER_DATES_BLOQUEES, list, [])
    resultat = []
    for b in donnees:
        if not isinstance(b, dict) or not isinstance(b.get("id"), str):
            continue
        try:
            debut = date.fromisoformat(b.get("debut"))
            fin = date.fromisoformat(b.get("fin"))
        except (TypeError, ValueError):
            continue
        if fin < debut:
            debut, fin = fin, debut
        resultat.append({"id": b["id"], "debut": debut.isoformat(), "fin": fin.isoformat()})
    return resultat


def sauvegarder_dates_bloquees(blocages):
    _ecrire_json_atomique(FICHIER_DATES_BLOQUEES, blocages)


def _lire_une_date(texte, reference=None):
    """Lit JJ/MM/AAAA, JJ/MM/AA ou JJ/MM (année = prochaine occurrence). Lève ValueError."""
    morceaux = texte.strip().replace(".", "/").replace("-", "/").split("/")
    try:
        nombres = [int(m) for m in morceaux]
    except ValueError:
        raise ValueError(f"Date illisible : « {texte.strip()} »")
    reference = reference or date.today()
    if len(nombres) == 2:
        jour, mois = nombres
        try:
            return prochaine_occurrence(jour, mois, reference)
        except (ValueError, TypeError):
            raise ValueError(f"Date invalide : « {texte.strip()} »")
    if len(nombres) == 3:
        jour, mois, annee = nombres
        if annee < 100:
            annee += 2000
        try:
            return date(annee, mois, jour)
        except ValueError:
            raise ValueError(f"Date invalide : « {texte.strip()} »")
    raise ValueError(f"Date illisible : « {texte.strip()} »")


def analyser_saisie_dates_bloquees(texte, reference=None):
    """
    Analyse une saisie libre contenant plusieurs dates et/ou périodes.
    Séparateurs entre éléments : virgule, point-virgule, retour à la ligne.
    Période : « 01/08/2026 au 15/08/2026 », « 01/08/2026 - 15/08/2026 »
              ou « du 01/08/2026 au 15/08/2026 ».
    Retourne (liste de (debut, fin), liste de messages d'erreur).
    """
    import re
    periodes, erreurs = [], []
    elements = re.split(r"[;,\n]+", texte or "")
    for element in elements:
        element = element.strip()
        if not element:
            continue
        nettoye = re.sub(r"^\s*du\s+", "", element, flags=re.IGNORECASE)
        parties = re.split(r"\s+(?:au|à|a)\s+|\s*(?:→|–|—)\s*|\s+-\s+", nettoye, flags=re.IGNORECASE)
        # Accepte aussi « 01/08/2026-15/08/2026 » (tiret collé)
        if len(parties) == 1:
            collees = re.fullmatch(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)-(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", nettoye)
            if collees:
                parties = list(collees.groups())
        try:
            if len(parties) == 1:
                d = _lire_une_date(parties[0], reference)
                periodes.append((d, d))
            elif len(parties) == 2:
                debut = _lire_une_date(parties[0], reference)
                fin = _lire_une_date(parties[1], reference)
                if fin < debut:
                    debut, fin = fin, debut
                periodes.append((debut, fin))
            else:
                raise ValueError(f"Format non reconnu : « {element} »")
        except ValueError as e:
            erreurs.append(str(e))
    return periodes, erreurs


def ajouter_dates_bloquees(periodes):
    """Ajoute des périodes [(debut, fin)] ; retourne le nombre ajouté (les doublons exacts sont ignorés)."""
    blocages = charger_dates_bloquees()
    existants = {(b["debut"], b["fin"]) for b in blocages}
    ajoutes = 0
    for debut, fin in periodes:
        cle = (debut.isoformat(), fin.isoformat())
        if cle in existants:
            continue
        blocages.append({"id": str(uuid.uuid4()), "debut": cle[0], "fin": cle[1]})
        existants.add(cle)
        ajoutes += 1
    blocages.sort(key=lambda b: b["debut"])
    sauvegarder_dates_bloquees(blocages)
    return ajoutes


def supprimer_date_bloquee(id_blocage):
    blocages = [b for b in charger_dates_bloquees() if b.get("id") != id_blocage]
    sauvegarder_dates_bloquees(blocages)


def est_date_bloquee(une_date):
    """Indique si la date donnée appartient à une période bloquée."""
    iso = une_date.isoformat()
    return any(b["debut"] <= iso <= b["fin"] for b in charger_dates_bloquees())


def jours_bloques_du_mois(mois, annee):
    """Ensemble des dates bloquées appartenant au mois donné."""
    resultat = set()
    debut_mois = date(annee, mois, 1).isoformat()
    nb = calendar_monthrange(annee, mois)
    fin_mois = date(annee, mois, nb).isoformat()
    for b in charger_dates_bloquees():
        if b["fin"] < debut_mois or b["debut"] > fin_mois:
            continue
        d = max(date.fromisoformat(b["debut"]), date(annee, mois, 1))
        fin = min(date.fromisoformat(b["fin"]), date(annee, mois, nb))
        while d <= fin:
            resultat.add(d)
            d += timedelta(days=1)
    return resultat


def calendar_monthrange(annee, mois):
    return calendar.monthrange(annee, mois)[1]
