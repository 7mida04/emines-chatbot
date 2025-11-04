from dotenv import load_dotenv
import os

# Fix OpenMP conflict
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from openai import OpenAI
from pypdf import PdfReader
from typing import Generator
import streamlit as st
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from audio_recorder_streamlit import audio_recorder
import tempfile
import json
from datetime import datetime
from collections import Counter

# Chargement des variables d'environnement
load_dotenv()

# Fichier de log pour les analytics
ANALYTICS_FILE = "analytics.json"

def load_analytics():
    """Charge les données analytics depuis le fichier JSON"""
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"visitors": 0, "interactions": []}
    return {"visitors": 0, "interactions": []}

def save_analytics(data):
    """Sauvegarde les données analytics dans le fichier JSON"""
    with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_interaction(question: str, response: str, input_type: str):
    """Log une interaction utilisateur"""
    analytics = load_analytics()
    
    interaction = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "response": response[:200],  # Limiter la taille
        "input_type": input_type,  # "text" ou "voice"
    }
    
    analytics["interactions"].append(interaction)
    save_analytics(analytics)

def increment_visitor():
    """Incrémente le compteur de visiteurs"""
    analytics = load_analytics()
    analytics["visitors"] += 1
    save_analytics(analytics)

def get_analytics_summary():
    """Retourne un résumé des analytics"""
    analytics = load_analytics()
    
    total_visitors = analytics["visitors"]
    total_questions = len(analytics["interactions"])
    
    # Questions les plus fréquentes (top 5)
    questions = [i["question"] for i in analytics["interactions"]]
    question_counts = Counter(questions)
    top_questions = question_counts.most_common(5)
    
    # Type d'entrée (texte vs vocal)
    input_types = [i["input_type"] for i in analytics["interactions"]]
    input_counts = Counter(input_types)
    
    return {
        "total_visitors": total_visitors,
        "total_questions": total_questions,
        "top_questions": top_questions,
        "input_counts": dict(input_counts),
        "recent_interactions": analytics["interactions"][-10:]  # 10 dernières
    }

class TranscriptionCorrector:
    """Corrige les transcriptions vocales avec GPT-4o-mini d'OpenAI"""
    def __init__(self):
        # Utilisation d'OpenAI pour une meilleure obéissance aux instructions
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def correct_transcription(self, transcription: str) -> str:
        """Corrige automatiquement les erreurs courantes dans la transcription"""
        correction_prompt = [
            {
                "role": "system",
                "content": """Tu es un correcteur orthographique automatique. Tu corriges UNIQUEMENT l'orthographe, tu ne réponds JAMAIS aux questions.

**Ta seule mission** : Corriger les fautes d'orthographe dans les noms propres et termes techniques d'EMINES.

**Corrections autorisées** :
- "émine", "hémine", "émines" → "EMINES"
- "um6p", "um 6p" → "UM6P"  
- "ben guérir" → "Ben Guerir"
- "management industrielle" → "Management Industriel"
- "cycle ingénieur" → "Cycle Ingénieur"

**INTERDICTIONS ABSOLUES** :
❌ NE réponds JAMAIS à la question posée
❌ NE fournis JAMAIS d'information
❌ NE reformule PAS la phrase
❌ NE change que les mots mal orthographiés
❌ NE modifie PAS la structure de la phrase

**Exemples corrects** :

Entrée: "Combien coûte hémine ?"
Sortie: "Combien coûte EMINES ?"

Entrée: "Où se trouve émine exactement ?"
Sortie: "Où se trouve EMINES exactement ?"

Entrée: "Quel est le programme de première année à l'émine ?"
Sortie: "Quel est le programme de première année à l'EMINES ?"

Entrée: "Comment postuler à um 6p ?"
Sortie: "Comment postuler à UM6P ?"

Retourne UNIQUEMENT le texte avec corrections orthographiques, rien d'autre."""
            },
            {"role": "user", "content": transcription}
        ]

        try:
            # Utilisation de GPT-4o-mini (meilleur rapport qualité/prix/obéissance)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=correction_prompt,
                temperature=0.1,
                max_tokens=150
            )
            corrected = response.choices[0].message.content.strip()
            
            # Nettoyer les préfixes indésirables (au cas où le modèle désobéit)
            unwanted_prefixes = [
                "Voici la transcription corrigée :",
                "Voici la correction :",
                "La transcription corrigée est :",
                "Transcription corrigée :",
                "Correction :",
                "Voici :",
                "Le programme",
                "La première année",
            ]
            
            for prefix in unwanted_prefixes:
                if corrected.lower().startswith(prefix.lower()):
                    corrected = corrected[len(prefix):].strip()
                    break
            
            # Vérification de sécurité : si la réponse est beaucoup plus longue,
            # c'est probablement que le modèle a répondu à la question au lieu de corriger
            if len(corrected) > len(transcription) * 2:
                # Le modèle a probablement répondu à la question, on retourne l'original
                return transcription
            
            return corrected
        except Exception as e:
            st.error(f"Erreur lors de la correction : {e}")
            return transcription  # Retourne l'original en cas d'erreur


class InteractiveClarifier:
    def __init__(self):
        # Utilisation d'OpenAI GPT-4o-mini pour une meilleure clarification
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []

    def clarify_question(self, user_query: str, chat_history: list = None, detected_language: str = "french") -> str:
        """Clarifie la question utilisateur en utilisant l'historique de conversation
        
        Args:
            user_query: La question de l'utilisateur
            chat_history: L'historique de conversation
            detected_language: La langue détectée (french, english, darija)
        
        Returns:
            Question clarifiée en français + instruction de langue si nécessaire
        """
        
        # Construire le contexte depuis l'historique de conversation
        context_text = "Aucune conversation précédente"
        if chat_history and len(chat_history) > 0:
            # Prendre les 2 dernières interactions pour le contexte
            recent_history = chat_history[-2:]
            context_parts = []
            for interaction in recent_history:
                context_parts.append(f"Q: {interaction['user']}")
            context_text = "\n".join(context_parts)
        
        clarification_prompt = [
            {
                "role": "system",
                "content": f"""Tu es un assistant qui clarifie les questions pour EMINES - School of Industrial Management (UM6P).

**Ta mission** : Reformuler les questions en FRANÇAIS (pour chercher dans la base de données française).

**À propos d'EMINES** :
- École : EMINES (School of Industrial Management)
- Université : UM6P (Université Mohammed VI Polytechnique)
- Localisation : Ben Guerir, Maroc
- Programmes : Cycle Préparatoire (2 ans) + Cycle Ingénieur (3 ans) en Management Industriel

**Règles de clarification** :

1. **Traduire en FRANÇAIS** si la question est en darija ou anglais :
   - "kifach npostuler?" → "Comment postuler à EMINES ?"
   - "how to apply?" → "Comment postuler à EMINES ?"
   - "wach kayna bourse?" → "Y a-t-il des bourses à EMINES ?"

2. **Si la question est vague ou incomplète**, la clarifier :
   - "et pour les frais?" → "Quels sont les frais de scolarité à EMINES ?"
   - "la bourse?" → "Y a-t-il des bourses d'études disponibles à EMINES ?"

3. **Ne JAMAIS répondre à la question**, seulement la clarifier/traduire.

**Historique de conversation récent :**
{context_text}

**Exemples de clarification :**

Question: "kifach ndfE3 l EMINES?"
Clarification: "Comment postuler à EMINES ?"

Question: "wach kayna bourse?"
Clarification: "Y a-t-il des bourses à EMINES ?"

Question: "how much does it cost?"
Clarification: "Quels sont les frais de scolarité à EMINES ?"

Question: "et pour les frais?"
Clarification: "Quels sont les frais de scolarité à EMINES ?"

Retourne UNIQUEMENT la question clarifiée EN FRANÇAIS, rien d'autre."""
            },
            {"role": "user", "content": user_query}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=clarification_prompt,
                temperature=0.2,
                max_tokens=150
            )
            clarified = response.choices[0].message.content.strip()
            
            # Ajouter l'instruction de langue si ce n'est pas du français
            if detected_language == "darija":
                clarified = f"{clarified} [RÉPONDS EN DARIJA MAROCAIN]"
            elif detected_language == "english":
                clarified = f"{clarified} [RESPOND IN ENGLISH]"
            
            # Enregistrer dans l'historique
            self.conversation_history.append({
                "original": user_query,
                "clarified": clarified,
                "language": detected_language
            })
            
            return clarified
        except Exception as e:
            print(f"Erreur clarification: {e}")
            return user_query

@st.cache_resource
def load_vector_store():
    """Charge les PDFs et crée le vector store"""
    if not os.path.exists("docs"):
        os.makedirs("docs")
        return None
    
    pdf_files = [f for f in os.listdir("docs") if f.endswith(".pdf")]
    if not pdf_files:
        return None

    sections = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join("docs", pdf_file)
        school_name = os.path.splitext(pdf_file)[0].upper()
        
        pdf_reader = PdfReader(pdf_path)
        text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
        
        sections.append(f"[FORMATION: {school_name}]\n{text}")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    return FAISS.from_texts(
        texts=sections,
        embedding=embeddings
    )

class PDFChatbot:
    def __init__(self, temperature: float = 0.2):
        self.temperature = temperature
        self.clarifier = InteractiveClarifier()
        self.corrector = TranscriptionCorrector()  # Nouveau correcteur
        self.client = OpenAI(
            api_key=os.getenv("FIREWORKS_API_KEY"),
            base_url="https://api.fireworks.ai/inference/v1"
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.vector_store = load_vector_store()
        self.chat_history = []
        self.last_limitations = None

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcrit l'audio en texte en utilisant Whisper d'OpenAI"""
        try:
            # Créer un fichier temporaire pour l'audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # Transcription avec Whisper (détection automatique de la langue)
            with open(tmp_file_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=None,  # Détection automatique (fr, en, ar)
                    response_format="text"
                )
            
            # Supprimer le fichier temporaire
            os.unlink(tmp_file_path)
            
            return transcript
        except Exception as e:
            return f"Erreur de transcription : {str(e)}"
    
    def correct_and_transcribe(self, audio_bytes: bytes) -> tuple[str, str]:
        """Transcrit l'audio et corrige automatiquement les erreurs courantes
        
        Returns:
            tuple: (transcription_brute, transcription_corrigée)
        """
        # Étape 1 : Transcription brute avec Whisper
        raw_transcription = self.transcribe_audio(audio_bytes)
        
        if raw_transcription.startswith("Erreur"):
            return raw_transcription, raw_transcription
        
        # Étape 2 : Correction automatique avec le petit modèle
        corrected_transcription = self.corrector.correct_transcription(raw_transcription)
        print("raw_transcription:", raw_transcription)
        print("corrected_transcription:", corrected_transcription)
        return raw_transcription, corrected_transcription

    def detect_language(self, text: str) -> str:
        """Détecte la langue du texte en utilisant GPT-4o-mini"""
        try:
            detection_prompt = [
                {
                    "role": "system",
                    "content": """Tu es un détecteur de langue expert. Analyse le texte et identifie la langue principale.

**Langues possibles :**
- french (Français standard)
- english (Anglais)
- darija (Arabe dialectal marocain / Darija)

**Règles :**
1. Si le texte contient du Darija (même mélangé avec du français), retourne "darija"
2. Si le texte est en anglais pur, retourne "english"
3. Si le texte est en français standard (sans Darija), retourne "french"

**Exemples :**

Texte: "kifach npostuler l EMINES?"
Langue: darija

Texte: "wach kayna bourse f EMINES?"
Langue: darija

Texte: "chno homa les programmes?"
Langue: darija

Texte: "Quels sont les programmes d'EMINES ?"
Langue: french

Texte: "how to apply to EMINES?"
Langue: english

Texte: "fine kayna EMINES?"
Langue: darija

Texte: "et pour les frais?"
Langue: french

Réponds UNIQUEMENT par un seul mot : "french", "english" ou "darija"."""
                },
                {"role": "user", "content": f"Texte: {text}\nLangue:"}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=detection_prompt,
                temperature=0.0,
                max_tokens=10
            )
            
            detected = response.choices[0].message.content.strip().lower()
            
            # Vérifier que la réponse est valide
            if detected in ["french", "english", "darija"]:
                return detected
            else:
                # Fallback : français par défaut
                return "french"
                
        except Exception as e:
            print(f"Erreur détection langue: {e}")
            return "french"  # Fallback en cas d'erreur

    def generate_response(self, user_query: str) -> Generator[str, None, None]:
        """Génère une réponse avec streaming"""
        if self.last_limitations != st.session_state.limitations:
            self.chat_history.clear()
            self.last_limitations = st.session_state.limitations

        # Détecter la langue de l'utilisateur
        detected_language = self.detect_language(user_query)
        print("original_query:", user_query)
        print("detected_language:", detected_language)
        
        # Passer l'historique ET la langue détectée au clarifier
        clarified_query = self.clarifier.clarify_question(user_query, self.chat_history, detected_language)
        print("clarified_query:", clarified_query)
        
        if not self.vector_store:
            yield "⚠️ Créez un dossier 'docs/' avec des PDFs des formations"
            return

        relevant_docs = self.vector_store.similarity_search(clarified_query, k=3)
        context = "\n".join([doc.page_content for doc in relevant_docs])

        messages = [
            {
            "role": "system",
            "content": f"""
            **Répondre toujours dans la même langue que l'utilisateur**
            
            **Rôle** : Assistant spécialisé exclusivement pour EMINES - School of Industrial Management (UM6P).
            Tu es l'assistant virtuel d'EMINES et tu ne dois répondre qu'aux questions concernant cette école.

            **À propos d'EMINES** :
            - Nom complet : EMINES - School of Industrial Management
            - Université : UM6P (Université Mohammed VI Polytechnique)
            - Date de création : 2013
            - Localisation : Ben Guerir, Maroc
            - Mission : Former des ingénieurs managers capables d'innover et de diriger dans un environnement industriel moderne
            
            **Programmes EMINES** :
            1. **Cycle Préparatoire Intégré en Management Industriel** (2 ans)
               - Durée : 2 ans (Bac à Bac+2)
               - Date limite de candidature : 1 juin 2025
               - Débouchés : Accès au Cycle Ingénieur
            
            2. **Cycle Ingénieur en Management Industriel** (3 ans)
               - Durée : 3 ans (Bac+2 à Bac+5)
               - Date limite de candidature : 15 mai 2025
               - Diplôme : Diplôme d'Ingénieur d'État en Management Industriel
            
            **Contacts EMINES** :
            📧 Email : contact@emines-ingenieur.org
            🌐 Site web : emines-ingenieur.org
            📍 Adresse : UM6P - Ben Guerir, Maroc
            
            **Directives STRICTES** :
            
            0. **LIMITATION STRICTE**: 
            {st.session_state.limitations}

            1. **Spécialisation EMINES Uniquement** :
            - Tu ne réponds QU'AUX questions concernant EMINES
            - Si on te pose une question sur une autre école de l'UM6P (CC, GTI, SAP+D, ABS, etc.), réponds :
              "Je suis spécialisé uniquement pour EMINES - School of Industrial Management. Pour des informations sur [nom de l'école], veuillez consulter le site officiel : 🌐 https://um6p.ma/fr"
            
            2. **Utilisation du Contexte** :
            - Utilise UNIQUEMENT les informations du contexte fourni (PDFs EMINES et UM6P)
            - Si l'information n'est pas dans le contexte, réponds :
              "Je ne trouve pas cette information précise. Pour plus de détails sur EMINES, veuillez contacter :
              📧 contact@emines-ingenieur.org
              🌐 emines-ingenieur.org"
            
            3. **LANGUE DE RÉPONSE - RÈGLE ABSOLUE** :
            
            ⚠️ CRITIQUE : Vérifie si la question contient une instruction de langue :
            - Si tu vois "[RÉPONDS EN DARIJA MAROCAIN]" → Réponds UNIQUEMENT en DARIJA
            - Si tu vois "[RESPOND IN ENGLISH]" → Réponds UNIQUEMENT en ANGLAIS
            - Sinon, réponds en FRANÇAIS
            
            **La question en français est juste pour chercher dans la base de données. L'instruction entre crochets indique la langue de réponse !**
            
            **Exemples de réponse en DARIJA :**
            - "EMINES kayna f Ben Guerir, f UM6P"
            - "Les programmes dyali homa Cycle Préparatoire (2 ans) w Cycle Ingénieur (3 ans)"
            - "Wakha tktb l contact@emines-ingenieur.org"
            - "Ta9dim l candidature khass tkoun 9bel 1 juin 2025"
            - "Bach tpostuler, khassek tmchi l site dyal EMINES w t3mer le formulaire"
            
            **Exemples de réponse en ANGLAIS :**
            - "EMINES is located in Ben Guerir, at UM6P"
            - "Our programs are the Preparatory Cycle (2 years) and Engineering Cycle (3 years)"
            - "You can contact us at contact@emines-ingenieur.org"
            
            NE JAMAIS traduire ou mélanger les langues !
            
            4. **Format des Réponses** :
            - Sois clair, précis et professionnel
            - Structure tes réponses avec des puces ou numéros si nécessaire
            - Toujours inclure les contacts EMINES quand pertinent
            - Reste concis mais complet
            
            5. **Interdictions** :
            - Ne JAMAIS inventer d'informations
            - Ne JAMAIS donner d'informations sur d'autres écoles de l'UM6P
            - Ne JAMAIS mélanger les informations d'EMINES avec d'autres écoles
            - Ne pas répondre à des questions générales non liées à EMINES

            **Contexte actuel (Documents EMINES et UM6P)** :
            {context}"""
                        }
        ]

        for msg in self.chat_history:
            messages.append({"role": "user", "content": msg["user"]})
            messages.append({"role": "assistant", "content": msg["assistant"]})

        messages.append({"role": "user", "content": clarified_query})

        try:
            model_name = "accounts/fireworks/models/deepseek-v3p1"
            
            stream = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=float(self.temperature),  # Use the temperature parameter
                max_tokens=2000,
                stream=True
            )

            full_response = []
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_response.append(text_chunk)
                    yield text_chunk

            self.chat_history.append({
                "user": user_query,
                "assistant": "".join(full_response)
            })
            
            # Logger l'interaction pour analytics
            log_interaction(
                question=user_query,
                response="".join(full_response),
                input_type=st.session_state.get('last_input_type', 'text')
            )

        except Exception as e:
            yield f"Erreur : {str(e)}"

    def update_temperature(self, new_temperature: float):
        """Met à jour la température pour les futures réponses"""
        self.temperature = new_temperature

def main():
    st.set_page_config(
        page_title="EMINES Chatbot", 
        page_icon="�",
        layout="wide"
    )
    
    # Initialisation des limitations
    if 'limitations' not in st.session_state:
        st.session_state.limitations = """- Tu ne peux répondre qu'aux questions concernant EMINES (School of Industrial Management).
            - Si on te pose une question sur une autre école de l'UM6P, réponds : "Je suis spécialisé uniquement pour EMINES - School of Industrial Management. Pour des informations sur d'autres écoles, veuillez consulter : 🌐 https://um6p.ma/fr"
            - Pour TOUTE question non liée à EMINES ou l'UM6P, réponds : "Je suis un assistant spécialisé uniquement pour EMINES - School of Industrial Management. Je ne peux pas répondre à cette question."
            - Ne jamais répondre à des questions générales, culturelles ou personnelles (musique, célébrités, actualités, politique, etc.)"""

    with st.sidebar:
        st.markdown("### 🏭 EMINES Assistant")
        st.markdown("**School of Industrial Management**")
        st.markdown("---")
        
        st.header("⚙️ Configuration")
        temperature = st.slider(
            "Créativité des réponses",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.1,
            help="0 = Précis, 1 = Créatif"
        )
        
        st.markdown("---")
        limitations = st.text_area(
            "Règles de restriction",
            value=st.session_state.limitations,
            height=250,
            help="Personnalisez les limitations du chatbot"
        )
        
        if limitations != st.session_state.limitations:
            st.session_state.limitations = limitations
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📞 Contact EMINES")
        st.markdown("📧 contact@emines-ingenieur.org")
        st.markdown("🌐 [emines-ingenieur.org](https://emines-ingenieur.org)")
        st.markdown("📍 UM6P - Ben Guerir, Maroc")
        
        # Analytics Dashboard
        st.markdown("---")
        st.markdown("### 📊 Statistiques")
        
        analytics = get_analytics_summary()
        
        # Métriques principales
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("👥 Visiteurs", analytics["total_visitors"])
        with col_b:
            st.metric("💬 Questions", analytics["total_questions"])
        
        # Type d'entrée
        if analytics["input_counts"]:
            st.markdown("**Type d'entrée:**")
            for input_type, count in analytics["input_counts"].items():
                type_label = {
                    'text': '⌨️ Texte',
                    'voice': '🎤 Vocal',
                    'suggested': '💡 Suggérée'
                }.get(input_type, input_type)
                st.text(f"{type_label}: {count}")
        
        # Top questions
        if analytics["top_questions"]:
            with st.expander("🔥 Top 5 Questions"):
                for i, (question, count) in enumerate(analytics["top_questions"], 1):
                    st.text(f"{i}. {question[:40]}... ({count}x)")
        
        # Reset button (admin)
        if st.button("🔄 Réinitialiser Stats", use_container_width=True):
            save_analytics({"visitors": 0, "interactions": []})
            st.success("Statistiques réinitialisées!")
            st.rerun()

    st.markdown("""
    <style>
    .streaming {background: #f1f3f4; padding: 15px; border-radius: 8px; margin: 10px 0;}
    @keyframes blink {50% {opacity: 0;}}
    .blink-cursor::after {content: "▌"; animation: blink 1s step-end infinite;}
    </style>
    """, unsafe_allow_html=True)

    st.title("🏭 Assistant EMINES")
    st.markdown("**School of Industrial Management** - UM6P")
    st.caption("💬 Posez vos questions par texte ou vocal (Français, Anglais, Darija)")
    
    # Info box
    col1, col2 = st.columns([3, 1])
    with col1:
        with st.expander("ℹ️ À propos d'EMINES"):
            st.markdown("""
            **EMINES - School of Industrial Management** est une école d'ingénieurs de l'UM6P fondée en 2013.
            
            **Programmes offerts :**
            - 🎓 Cycle Préparatoire Intégré en Management Industriel (2 ans)
            - 🎓 Cycle Ingénieur en Management Industriel (3 ans)
            
            **Localisation :** Ben Guerir, Maroc
            
            **Contact :**
            - 📧 contact@emines-ingenieur.org
            - 🌐 emines-ingenieur.org
            """)
    
    with col2:
        with st.expander("🎤 Mode Vocal"):
            st.markdown("""
            **Langues supportées :**
            - 🇫🇷 Français
            - 🇬🇧 Anglais
            - 🇲🇦 Darija
            
            Cliquez sur le micro pour enregistrer votre question !
            """)

    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = PDFChatbot()
        st.session_state.current_temperature = 0.2
    
    if 'last_audio' not in st.session_state:
        st.session_state.last_audio = None
    
    if 'transcribed_text' not in st.session_state:
        st.session_state.transcribed_text = ""
    
    if 'show_transcription' not in st.session_state:
        st.session_state.show_transcription = False
    
    if 'pending_message' not in st.session_state:
        st.session_state.pending_message = None
    
    if 'visitor_counted' not in st.session_state:
        increment_visitor()
        st.session_state.visitor_counted = True
    
    if 'last_input_type' not in st.session_state:
        st.session_state.last_input_type = 'text'

    if st.session_state.current_temperature != temperature:
        st.session_state.chatbot.update_temperature(temperature)
        st.session_state.current_temperature = temperature

    if not st.session_state.chatbot.vector_store:
        st.warning("⚠️ Aucun document trouvé. Veuillez ajouter les PDFs d'EMINES dans le dossier 'docs/' et actualiser la page.")
        st.info("📁 Documents requis : EMINES.pdf et/ou UM6P.pdf")

    # Section pour l'entrée utilisateur
    st.markdown("### 💭 Posez votre question")
    
    # Créer une colonne pour le bouton audio
    col_audio, col_spacer = st.columns([1, 5])
    
    with col_audio:
        st.markdown("**🎤 Vocal**")
        audio_bytes = audio_recorder(
            text="",
            recording_color="#e74c3c",
            neutral_color="#3498db",
            icon_name="microphone",
            icon_size="2x",
        )
    
    # Traiter l'audio si disponible
    if audio_bytes and audio_bytes != st.session_state.last_audio:
        st.session_state.last_audio = audio_bytes
        st.session_state.last_input_type = 'voice'
        
        with st.spinner("🎧 Transcription en cours..."):
            raw_transcription, corrected_transcription = st.session_state.chatbot.correct_and_transcribe(audio_bytes)
            
            if not raw_transcription.startswith("Erreur"):
                # Afficher les deux versions pour information
                if raw_transcription != corrected_transcription:
                    st.success(f"✨ **Correction automatique appliquée**\n\n"
                              f"🔸 Original: _{raw_transcription}_\n\n"
                              f"🔹 Corrigé: **{corrected_transcription}**")
                else:
                    st.success("✅ Transcription réussie (aucune correction nécessaire)")
                
                # Utiliser la version corrigée pour l'édition
                st.session_state.transcribed_text = corrected_transcription
                st.session_state.show_transcription = True
                st.rerun()
            else:
                st.error(raw_transcription)
    
    # Afficher le champ de texte éditable avec la transcription
    user_input = None
    
    if st.session_state.show_transcription and st.session_state.transcribed_text:
        st.info("✅ Transcription réussie ! Vous pouvez modifier le texte ci-dessous avant de l'envoyer.")
        
        # Zone de texte éditable avec la transcription
        edited_text = st.text_area(
            "📝 Modifiez votre question si nécessaire :",
            value=st.session_state.transcribed_text,
            height=100,
            key="edit_transcription"
        )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            if st.button("✔️ Envoyer", type="primary", use_container_width=True):
                st.session_state.pending_message = edited_text
                st.session_state.show_transcription = False
                st.session_state.transcribed_text = ""
                st.rerun()
        
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.show_transcription = False
                st.session_state.transcribed_text = ""
                st.rerun()
    else:
        # Zone de saisie texte normale
        st.markdown("**⌨️ Ou tapez votre question :**")
        user_input = st.chat_input("Tapez votre question ici...")
        if user_input:
            st.session_state.last_input_type = 'text'
    
    # Questions suggérées (Quick Replies)
    if not st.session_state.show_transcription:
        st.markdown("---")
        st.markdown("### 🔎 Questions fréquentes")
        st.caption("Cliquez sur une question pour l'envoyer rapidement")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📚 Programmes", use_container_width=True, key="btn_prog"):
                st.session_state.pending_message = "Quels sont les programmes offerts par EMINES ?"
                st.session_state.last_input_type = 'suggested'
                st.rerun()
            
            if st.button("📅 Dates limites", use_container_width=True, key="btn_dates"):
                st.session_state.pending_message = "Quelles sont les dates limites de candidature ?"
                st.session_state.last_input_type = 'suggested'
                st.rerun()
        
        with col2:
            if st.button("📝 Admission", use_container_width=True, key="btn_adm"):
                st.session_state.pending_message = "Comment postuler à EMINES ?"
                st.session_state.last_input_type = 'suggested'
                st.rerun()
            
            if st.button("💰 Frais", use_container_width=True, key="btn_frais"):
                st.session_state.pending_message = "Quels sont les frais de scolarité ?"
                st.session_state.last_input_type = 'suggested'
                st.rerun()
        
        with col3:
            if st.button("📍 Localisation", use_container_width=True, key="btn_loc"):
                st.session_state.pending_message = "Où se trouve EMINES ?"
                st.session_state.last_input_type = 'suggested'
                st.rerun()
            
            if st.button("📞 Contact", use_container_width=True, key="btn_contact"):
                st.session_state.pending_message = "Comment contacter EMINES ?"
                st.session_state.last_input_type = 'suggested'
                st.rerun()
    
    # Récupérer le message en attente si disponible
    if st.session_state.pending_message:
        user_input = st.session_state.pending_message
        st.session_state.pending_message = None
    
    for msg in st.session_state.chatbot.chat_history:
        with st.chat_message("user"):
            st.write(msg["user"])
        with st.chat_message("assistant"):
            st.write(msg["assistant"])

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            response = st.empty()
            full_response = ""
            
            for chunk in st.session_state.chatbot.generate_response(user_input):
                full_response += chunk
                response.markdown(f'<div class="streaming blink-cursor">{full_response}</div>', unsafe_allow_html=True)
            
            response.markdown(f'<div class="streaming">{full_response}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
