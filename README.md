# Amenah

**Amenah** (ةنيمأ — « digne de confiance ») est une plateforme web indépendante et non commerciale qui fournit une information claire et sourcée sur les marques profitant de l'occupation, propose des alternatives éthiques, et référence des organismes de don pour la Palestine. Inspiré du mouvement **BDS** (Boycott, Désinvestissement, Sanctions).

## Fonctionnalités

- **Liste de produits à boycotter** avec catégories et sources vérifiées
- **Alternatives éthiques** pour remplacer les marques boycottées
- **Scanner de code-barres** (caméra ou saisie manuelle)
- **Chatbot d'assistance** multilingue (FR/EN) couvrant l'histoire de la Palestine
- **Actualités Gaza** en temps réel (flux BBC + Al Jazeera)
- **Organismes de don** vérifiés par l'équipe
- **Back-office d'administration** sécurisé pour la modération
- **Formulaire de feedback** avec envoi par e-mail

## Technologies

- **Backend** : Python 3 + Flask
- **Base de données** : SQLite (par défaut) ou MySQL
- **Frontend** : HTML5, CSS3, JavaScript vanilla
- **Sécurité** : PBKDF2-SHA256, protection anti-bruteforce, sessions HttpOnly

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/<ton-username>/amenah.git
cd amenah

# Créer un environnement virtuel (recommandé)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux / macOS

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python app.py
```

Le site sera accessible sur [http://127.0.0.1:8080](http://127.0.0.1:8080).

Au premier démarrage, un compte administrateur est créé automatiquement. Les identifiants s'affichent dans la console.

## Configuration (optionnelle)

Créer un fichier `.env` à la racine avec :

```env
AMENAH_ADMIN_USER=admin
AMENAH_ADMIN_PASSWORD=ton_mot_de_passe_fort
AMENAH_SECRET_KEY=une_cle_secrete_aleatoire

# Pour MySQL (optionnel)
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=amenah

# Pour les e-mails de feedback (optionnel)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=ton.email@gmail.com
SMTP_PASSWORD=ton_mot_de_passe_applicatif
FEEDBACK_EMAIL_TO=destinataire@exemple.com
```

## Structure du projet

```
amenah/
├── app.py                  # Application Flask principale
├── manage_users.py         # Gestion des comptes admin en CLI
├── requirements.txt        # Dépendances Python
├── sql/
│   ├── schema.sql          # Schéma SQLite
│   └── schema_mysql.sql    # Schéma MySQL
├── static/                 # CSS, JS, images
├── templates/              # Templates Jinja2 (index.html, admin.html, login.html)
├── scripts/                # Utilitaires
└── tools/                  # Outils de développement
```

## Routes principales

| Route | Rôle |
|---|---|
| `/` | Page d'accueil publique |
| `/admin` | Tableau de bord d'administration (protégé) |
| `/admin/login` | Page de connexion |
| `/api/produits` | Liste des produits boycottés |
| `/api/produit-alternatives` | Liste des alternatives |
| `/api/donation-agencies` | Liste des organismes de don |
| `/api/gaza-news` | Flux d'actualités |
| `/api/chat` | Chatbot |

## Licence

Projet académique réalisé dans le cadre d'un projet de fin d'études.
