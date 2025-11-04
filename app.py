from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
import os
import json
from openai import OpenAI
from pypdf import PdfReader
from typing import Generator
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import tempfile

# Fix OpenMP conflict
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Chargement des variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Classes identiques à model1.py
class TranscriptionCorrector:
    """Corrige les transcriptions vocales avec GPT-4o-mini d'OpenAI"""
    def __init__(self):
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

Retourne UNIQUEMENT le texte avec corrections orthographiques, rien d'autre."""
            },
            {"role": "user", "content": transcription}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=correction_prompt,
                temperature=0.1,
                max_tokens=150
            )
            corrected = response.choices[0].message.content.strip()
            
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
            
            if len(corrected) > len(transcription) * 2:
                return transcription
            
            return corrected
        except Exception as e:
            print(f"Erreur correction: {e}")
            return transcription


class InteractiveClarifier:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []

    def clarify_question(self, user_query: str, chat_history: list = None, detected_language: str = "french") -> str:
        """Clarifie la question utilisateur en utilisant l'historique de conversation"""
        
        context_text = "Aucune conversation précédente"
        if chat_history and len(chat_history) > 0:
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
            
            if detected_language == "darija":
                clarified = f"{clarified} [RÉPONDS EN DARIJA MAROCAIN]"
            elif detected_language == "english":
                clarified = f"{clarified} [RESPOND IN ENGLISH]"
            
            self.conversation_history.append({
                "original": user_query,
                "clarified": clarified,
                "language": detected_language
            })
            
            return clarified
        except Exception as e:
            print(f"Erreur clarification: {e}")
            return user_query


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
        self.corrector = TranscriptionCorrector()
        self.client = OpenAI(
            api_key=os.getenv("FIREWORKS_API_KEY"),
            base_url="https://api.fireworks.ai/inference/v1"
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.vector_store = load_vector_store()
        self.chat_history = []
        self.limitations = """- Tu ne peux répondre qu'aux questions concernant EMINES (School of Industrial Management).
            - Si on te pose une question sur une autre école de l'UM6P, réponds : "Je suis spécialisé uniquement pour EMINES - School of Industrial Management. Pour des informations sur d'autres écoles, veuillez consulter : 🌐 https://um6p.ma/fr"
            - Pour TOUTE question non liée à EMINES ou l'UM6P, réponds : "Je suis un assistant spécialisé uniquement pour EMINES - School of Industrial Management. Je ne peux pas répondre à cette question."
            - Ne jamais répondre à des questions générales, culturelles ou personnelles (musique, célébrités, actualités, politique, etc.)"""

    def transcribe_audio(self, audio_file) -> str:
        """Transcrit l'audio en texte en utilisant Whisper d'OpenAI"""
        try:
            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=None,
                response_format="text"
            )
            return transcript
        except Exception as e:
            return f"Erreur de transcription : {str(e)}"

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
            
            if detected in ["french", "english", "darija"]:
                return detected
            else:
                return "french"
                
        except Exception as e:
            print(f"Erreur détection langue: {e}")
            return "french"

    def generate_response(self, user_query: str) -> Generator[str, None, None]:
        """Génère une réponse avec streaming"""
        
        detected_language = self.detect_language(user_query)
        print(f"Langue détectée: {detected_language}")
        
        clarified_query = self.clarifier.clarify_question(user_query, self.chat_history, detected_language)
        print(f"Question clarifiée: {clarified_query}")
        
        if not self.vector_store:
            yield "⚠️ Aucun document trouvé dans le dossier 'docs/'"
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
{self.limitations}

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
            stream = self.client.chat.completions.create(
                model="accounts/fireworks/models/deepseek-v3p1",
                messages=messages,
                temperature=float(self.temperature),
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

        except Exception as e:
            yield f"Erreur : {str(e)}"


# Instance globale du chatbot
chatbot = PDFChatbot()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message vide'}), 400
        
        def generate():
            for chunk in chatbot.generate_response(message):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    temp_audio_path = None
    try:
        print("=== TRANSCRIPTION REQUEST ===")
        
        if 'audio' not in request.files:
            print("Erreur: Aucun fichier audio dans la requête")
            return jsonify({'error': 'Aucun fichier audio'}), 400
        
        audio_file = request.files['audio']
        print(f"Fichier reçu: {audio_file.filename}, Content-Type: {audio_file.content_type}")
        
        # Déterminer l'extension du fichier
        filename = audio_file.filename or 'recording.webm'
        extension = filename.split('.')[-1] if '.' in filename else 'webm'
        
        # Sauvegarder temporairement le fichier audio
        temp_audio_path = os.path.join(tempfile.gettempdir(), f'temp_audio_{os.getpid()}.{extension}')
        print(f"Sauvegarde temporaire: {temp_audio_path}")
        audio_file.save(temp_audio_path)
        
        # Vérifier la taille du fichier
        file_size = os.path.getsize(temp_audio_path)
        print(f"Taille du fichier: {file_size} bytes")
        
        if file_size == 0:
            print("Erreur: Fichier audio vide")
            return jsonify({'error': 'Fichier audio vide'}), 400
        
        # Transcription
        print("Début de la transcription avec Whisper...")
        with open(temp_audio_path, 'rb') as f:
            raw_transcription = chatbot.transcribe_audio(f)
        
        print(f"Transcription brute: {raw_transcription}")
        
        if raw_transcription.startswith("Erreur"):
            print(f"Erreur lors de la transcription: {raw_transcription}")
            return jsonify({'error': raw_transcription}), 500
        
        # Correction
        print("Correction de la transcription...")
        corrected_transcription = chatbot.corrector.correct_transcription(raw_transcription)
        print(f"Transcription corrigée: {corrected_transcription}")
        
        return jsonify({
            'raw': raw_transcription,
            'corrected': corrected_transcription
        })
    
    except Exception as e:
        print(f"=== ERREUR TRANSCRIPTION ===")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
    
    finally:
        # Supprimer le fichier temporaire
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
                print(f"Fichier temporaire supprimé: {temp_audio_path}")
            except Exception as e:
                print(f"Impossible de supprimer le fichier temporaire: {e}")


@app.route('/api/clear', methods=['POST'])
def clear_history():
    try:
        chatbot.chat_history = []
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
