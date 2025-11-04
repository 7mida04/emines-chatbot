# 🏭 EMINES Chatbot - Assistant Intelligent

Un chatbot conversationnel intelligent spécialisé pour **EMINES - School of Industrial Management** (UM6P) avec support vocal multilingue.

## ✨ Fonctionnalités

- 🎤 **Mode Vocal** : Reconnaissance vocale en Français, Anglais et Darija
- ⌨️ **Mode Texte** : Saisie classique par clavier
- 🧠 **IA Avancée** : Utilise DeepSeek-v3p1 (Fireworks AI) et Whisper (OpenAI)
- 📚 **Base de connaissances** : Recherche vectorielle dans les documents PDF
- 🌍 **Multilingue** : Support automatique de plusieurs langues
- 💬 **Historique** : Conversations contextualisées
- ⚙️ **Personnalisable** : Température et règles ajustables

## 🚀 Installation rapide

### 1. Cloner le projet
```bash
git clone https://github.com/votre-repo/UM6PBOT.git
cd UM6PBOT
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer les clés API

Créez un fichier `.env` à la racine du projet :
```env
# Clé API Fireworks AI (pour le modèle de chat)
FIREWORKS_API_KEY=votre_cle_fireworks

# Clé API OpenAI (pour embeddings et Whisper)
OPENAI_API_KEY=votre_cle_openai
```

**Obtenir les clés :**
- Fireworks AI : https://fireworks.ai/
- OpenAI : https://platform.openai.com/api-keys

### 4. Ajouter les documents

Placez les fichiers PDF dans le dossier `docs/` :
```
docs/
  ├── Cycle de formation ingénieur en Management Industriel (EMINES).pdf
  └── UM6P.pdf
```

### 5. Lancer l'application
```bash
streamlit run model1.py
```

Ouvrez votre navigateur : `http://localhost:8501`

## 🎤 Utilisation du mode vocal

### Activation
1. Cliquez sur le bouton **microphone** 🎙️
2. Parlez votre question clairement
3. Cliquez à nouveau pour arrêter
4. La transcription apparaît automatiquement

### Langues supportées
- 🇫🇷 **Français** : "Quels sont les programmes d'EMINES ?"
- 🇬🇧 **Anglais** : "What programs does EMINES offer?"
- 🇲🇦 **Darija** : "شنو البرامج ديال EMINES؟"

### Permissions
Autorisez l'accès au microphone dans votre navigateur (une notification apparaîtra).

## 📖 Documentation

- 📘 [Guide vocal complet](GUIDE_VOCAL.md)
- 🔧 [Test des clés API](test_api_keys.py)
- 🧪 [Test des modèles Fireworks](test_fireworks_models.py)

## 🏗️ Architecture technique

### Modèles IA
- **Chat** : DeepSeek-v3p1 (Fireworks AI)
- **Embeddings** : text-embedding-3-large (OpenAI)
- **Transcription** : Whisper-1 (OpenAI)
- **Vector Store** : FAISS

### Technologies
- **Framework** : Streamlit
- **LLM** : OpenAI SDK + Fireworks AI
- **Vector DB** : LangChain + FAISS
- **Audio** : audio-recorder-streamlit

## 🔧 Configuration avancée

### Ajuster la créativité
Utilisez le slider dans la barre latérale :
- **0.0** : Réponses très précises et factuelles
- **0.5** : Équilibre entre précision et créativité
- **1.0** : Réponses plus créatives et variées

### Personnaliser les règles
Modifiez les règles de restriction dans la barre latérale pour contrôler le comportement du chatbot.

## 📊 Coûts estimés

### OpenAI
- **Embeddings** : ~$0.00013 par 1000 tokens
- **Whisper** : ~$0.006 par minute d'audio

### Fireworks AI
- **DeepSeek-v3p1** : Vérifiez les tarifs sur https://fireworks.ai/pricing

**Estimation** : ~$0.01 par conversation complète (texte + vocal)

## 🐛 Dépannage

### Erreur OpenMP
Si vous voyez une erreur `libomp140.x86_64.dll` :
✅ **Solution** : Déjà corrigée dans le code (`KMP_DUPLICATE_LIB_OK=TRUE`)

### Microphone ne fonctionne pas
✅ Vérifiez les permissions du navigateur (cliquez sur 🔒 dans la barre d'adresse)
✅ Testez sur Chrome/Edge (meilleure compatibilité)

### Clés API invalides
✅ Exécutez `python test_api_keys.py` pour vérifier vos clés
✅ Assurez-vous que le fichier `.env` est à la racine du projet

### Documents non chargés
✅ Vérifiez que le dossier `docs/` contient des fichiers PDF
✅ Rechargez la page Streamlit (F5)

## 🧪 Tests

### Tester les clés API
```bash
python test_api_keys.py
```

### Tester les modèles Fireworks
```bash
python test_fireworks_models.py
```

## 📝 Structure du projet

```
UM6PBOT/
├── model1.py                 # Application principale
├── test_api_keys.py          # Test des clés API
├── test_fireworks_models.py  # Test des modèles Fireworks
├── requirements.txt          # Dépendances Python
├── .env                      # Variables d'environnement (à créer)
├── README.md                 # Ce fichier
├── GUIDE_VOCAL.md           # Guide d'utilisation vocal
└── docs/                    # Dossier des documents PDF
    ├── EMINES.pdf
    └── UM6P.pdf
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :
1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👥 Contact

**EMINES - School of Industrial Management**
- 📧 contact@emines-ingenieur.org
- 🌐 https://emines-ingenieur.org
- 📍 UM6P - Ben Guerir, Maroc

---

**Développé avec ❤️ pour EMINES** 🏭