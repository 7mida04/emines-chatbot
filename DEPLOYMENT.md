# 🎓 EMINES Chatbot - Assistant Virtuel UM6P

Chatbot intelligent pour les Journées Portes Ouvertes d'EMINES avec support multilingue (Français, English, Darija) et fonctionnalité vocale.

## 🚀 Déploiement sur Render.com (GRATUIT)

### Étape 1 : Préparer le code
1. Créez un compte GitHub (si vous n'en avez pas)
2. Créez un nouveau repository
3. Uploadez tous les fichiers de ce dossier

### Étape 2 : Déployer sur Render
1. Allez sur [render.com](https://render.com) et créez un compte
2. Cliquez sur "New +" → "Web Service"
3. Connectez votre repository GitHub
4. Configuration :
   - **Name** : `emines-chatbot`
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app`

### Étape 3 : Variables d'environnement
Dans Render, allez dans "Environment" et ajoutez :

```
OPENAI_API_KEY=votre_clé_openai
FIREWORKS_API_KEY=votre_clé_fireworks
```

### Étape 4 : Déployer
Cliquez sur "Create Web Service" et attendez 5-10 minutes.

Votre chatbot sera accessible sur : `https://emines-chatbot.onrender.com`

---

## 🌐 Autres options gratuites

### Option 2 : PythonAnywhere
- Limite : 512 MB RAM
- Idéal pour petits projets
- [pythonanywhere.com](https://www.pythonanywhere.com)

### Option 3 : Railway.app
- $5 de crédit gratuit/mois
- Très simple à utiliser
- [railway.app](https://railway.app)

### Option 4 : Fly.io
- Plan gratuit généreux
- Bon pour Flask
- [fly.io](https://fly.io)

---

## ⚙️ Configuration locale

1. Installez les dépendances :
```bash
pip install -r requirements.txt
```

2. Créez un fichier `.env` :
```
OPENAI_API_KEY=your_key_here
FIREWORKS_API_KEY=your_key_here
```

3. Lancez l'application :
```bash
python app.py
```

4. Ouvrez : `http://localhost:5000`

---

## 📋 Fonctionnalités

- ✅ Chat multilingue (FR/EN/Darija)
- ✅ Transcription vocale avec Whisper
- ✅ Correction automatique (EMINES, UM6P, etc.)
- ✅ Streaming des réponses
- ✅ Interface moderne avec palette EMINES
- ✅ RAG avec base de connaissances PDF

---

## 🎨 Technologies

- **Backend** : Flask + Python
- **AI** : OpenAI GPT-4o-mini, Whisper, DeepSeek-v3p1
- **Frontend** : HTML/CSS/JavaScript
- **Vector DB** : FAISS
- **Embeddings** : text-embedding-3-large

---

## 📝 Notes importantes

- Le plan gratuit de Render redémarre après 15 min d'inactivité (cold start)
- Première requête peut prendre 30-60 secondes
- Pour un usage intensif, envisagez un plan payant

---

## 📧 Contact

Pour toute question : **EMINES - UM6P**
