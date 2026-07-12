# Crous Watcher

Surveille automatiquement trouverunlogement.lescrous.fr et envoie une notification
Telegram dès qu'un nouveau logement apparaît dans les codes postaux suivants :

69002, 69003, 69004, 69005, 69006, 69007, 69008, 69100, 69500, 69200, 69120

Vérification toutes les 15 minutes, 24h/24, gratuitement, via GitHub Actions.

## Mise en place (environ 15 minutes)

### 1. Créer le bot Telegram

1. Ouvre Telegram et cherche **@BotFather**.
2. Envoie `/newbot`, choisis un nom et un identifiant (doit finir par `bot`).
3. BotFather te donne un **token** du type `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`. Garde-le, c'est `TELEGRAM_BOT_TOKEN`.
4. Envoie un premier message quelconque à ton bot (sinon il ne peut pas t'écrire).

### 2. Récupérer ton chat_id

1. Va sur `https://api.telegram.org/bot<TON_TOKEN>/getUpdates` (remplace `<TON_TOKEN>`) dans ton navigateur, juste après avoir envoyé un message au bot.
2. Cherche `"chat":{"id":XXXXXXXXX` dans la réponse. Ce nombre est ton `TELEGRAM_CHAT_ID`.

### 3. Créer le dépôt GitHub

1. Crée un compte GitHub si besoin (gratuit) : https://github.com
2. Crée un nouveau dépôt, par exemple `crous-watcher`. Public de préférence (minutes GitHub Actions illimitées ; en privé, la limite gratuite de 2000 minutes/mois suffit largement avec un intervalle de 15 minutes, mais public simplifie tout).
3. Mets-y les fichiers de ce projet (`crous_watcher.py`, `.github/workflows/watch.yml`).

### 4. Ajouter les secrets

Dans le dépôt : **Settings > Secrets and variables > Actions > New repository secret**

- `TELEGRAM_BOT_TOKEN` → le token obtenu à l'étape 1
- `TELEGRAM_CHAT_ID` → le chat_id obtenu à l'étape 2

### 5. Activer et tester

1. Onglet **Actions** du dépôt, active les workflows si demandé.
2. Lance manuellement "Crous Watcher" via **Run workflow** (bouton `workflow_dispatch`) pour vérifier que tout fonctionne.
3. Le premier lancement n'envoie **aucune notification** : il enregistre juste l'état actuel des logements existants comme référence. C'est normal.
4. À partir du deuxième lancement, seuls les **nouveaux** logements dans tes codes postaux déclenchent un message Telegram.

## Ajuster

- **Codes postaux** : modifie la liste `TARGET_POSTAL_CODES` dans `crous_watcher.py`.
- **Fréquence** : modifie la ligne `cron` dans `.github/workflows/watch.yml` (format cron standard, en UTC). Éviter de descendre sous 5 minutes pour rester correct vis-à-vis du site du Crous.
- **Année universitaire** : le script cible la campagne 2026-2027 (`tools/47`). Pour l'année en cours, remplacer `47` par `42` dans `SEARCH_URL`.

## Limites à connaître

- Le site du Crous peut changer sa structure HTML à tout moment, ce qui casserait le parsing. Si plus aucune notification n'arrive après plusieurs jours alors que tu sais qu'il y a du mouvement, vérifie les logs dans l'onglet Actions.
- GitHub peut retarder légèrement l'exécution des cron jobs en cas de forte charge sur leur infrastructure (rarement plus de quelques minutes).
- Ceci ne remplace pas une vérification manuelle régulière : garde un œil sur le site de temps en temps.
