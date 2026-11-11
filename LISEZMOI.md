# Canal Curieux

Mon YouTube éducatif sans algorithme : un site installable sur le téléphone, avec lecteur intégré,
et un robot qui met le catalogue à jour chaque semaine, sans IA.

## Ce que contient ce dossier

| Élément | Rôle |
|---|---|
| `index.html`, `sw.js`, `manifest.webmanifest`, `icons/` | Le site (catalogue, mélange maison, parcours, chaînes, lecteur) |
| `config.js` | Adresse et clé publique de la base de synchro (à remplir une fois) |
| `data/catalogue.json`, `data/chaines.json` | Le catalogue et les chaînes, réécrits par le robot |
| `data/journal.json`, `data/series.json` | Compte rendu des mises à jour, playlists des séries |
| `robot/maj.py` | Le robot de mise à jour |
| `robot/regles.py` | Tous les réglages : seuils, mots exclus, sous-thèmes, lignes « Pourquoi » |
| `.github/workflows/site.yml` | Lance le robot (nuit de dimanche à lundi) et publie le site |
| `supabase.sql` | Création de la base de synchro (à coller une fois dans Supabase) |

## Mise en route (une seule fois)

1. **GitHub** : créer un dépôt public `canal-curieux`, y déposer tout ce dossier.
   Dans Settings > Pages, choisir Source : « GitHub Actions ».
2. **Clé YouTube** : sur console.cloud.google.com, créer un projet, activer « YouTube Data API v3 »,
   créer une clé API. Dans le dépôt : Settings > Secrets and variables > Actions > secret `YT_API_KEY`.
3. **Synchro** : sur supabase.com, créer un projet, ouvrir SQL Editor, coller `supabase.sql`
   après y avoir mis un code de synchro personnel. Reporter l'adresse et la clé publique du projet
   dans `config.js`, et créer les secrets `SUPABASE_URL`, `SUPABASE_KEY`, `SYNC_CODE`.
4. **Premier passage** : onglet Actions > « Canal Curieux » > Run workflow.
5. **Téléphone** : ouvrir l'adresse du site, Partager > « Sur l'écran d'accueil », puis saisir le code
   de synchro dans les réglages du site (bouton en haut à droite).

## Ce que fait le robot à chaque passage

1. Lit tes décisions prises sur le site (chaînes ajoutées, gardées, exclues, liens collés, 👍/👎).
2. Vérifie les vidéos existantes : durée, date, vidéo supprimée, lecture intégrée autorisée.
3. Ajoute les nouveautés des chaînes suivies (3 par chaîne et 40 par passage au maximum),
   sans Shorts, sans directs, sans extraits de moins de 3 minutes.
4. Complète les séries à partir des playlists officielles des créateurs.
5. Propose au plus 2 chaînes « découvertes » : celles que citent tes chaînes et les vidéos que tu as
   aimées. Elles restent « à valider » et ne dépassent pas 5 % du catalogue.
6. Compte les discussions Hacker News des vidéos anglaises.

Le compte rendu de chaque passage est visible dans les réglages du site et dans l'onglet Actions de GitHub.
Coût en quota YouTube : quelques centaines d'unités par passage, pour 10 000 gratuites par jour.

## Régler le robot

Tout est dans `robot/regles.py` : durée minimale, nombre d'ajouts, part des découvertes, mots exclus,
médias écartés, mots-clés des sous-thèmes, phrase « Pourquoi » de chaque chaîne.
