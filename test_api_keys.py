"""
Script de test pour vérifier la validité des clés API
Teste FIREWORKS_API_KEY et OPENAI_API_KEY
"""

from dotenv import load_dotenv
import os
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings

# Couleurs pour le terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Affiche un en-tête coloré"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    """Affiche un message de succès"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Affiche un message d'erreur"""
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    """Affiche un message d'information"""
    print(f"{YELLOW}ℹ {text}{RESET}")

def test_fireworks_api():
    """Test de la clé API Fireworks"""
    print_header("TEST FIREWORKS API")
    
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print_error("FIREWORKS_API_KEY n'est pas définie dans le fichier .env")
        return False
    
    if api_key == "your_fireworks_api_key_here":
        print_error("FIREWORKS_API_KEY n'a pas été remplacée (valeur par défaut détectée)")
        return False
    
    print_info(f"Clé trouvée: {api_key[:10]}...{api_key[-4:]}")
    print_info("Test de connexion avec le modèle DeepSeek-v3p1...")
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.fireworks.ai/inference/v1"
        )
        
        response = client.chat.completions.create(
            
            model="accounts/fireworks/models/deepseek-v3p1",
            messages=[
                {"role": "system", "content": "Tu es un assistant utile."},
                {"role": "user", "content": "quelle est la capitale de la France?"}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print_success(f"Connexion réussie!")
        print_info(f"Réponse du modèle: {result}")
        return True
        
    except Exception as e:
        print_error(f"Échec de la connexion: {str(e)}")
        if "401" in str(e):
            print_info("→ Clé API invalide ou expirée")
        elif "403" in str(e):
            print_info("→ Accès refusé, vérifiez vos permissions")
        elif "429" in str(e):
            print_info("→ Limite de taux atteinte")
        return False

def test_openai_api():
    """Test de la clé API OpenAI"""
    print_header("TEST OPENAI API")
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print_error("OPENAI_API_KEY n'est pas définie dans le fichier .env")
        return False
    
    if api_key == "your_openai_api_key_here":
        print_error("OPENAI_API_KEY n'a pas été remplacée (valeur par défaut détectée)")
        return False
    
    print_info(f"Clé trouvée: {api_key[:10]}...{api_key[-4:]}")
    print_info("Test de création d'embeddings avec text-embedding-3-large...")
    
    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=api_key
        )
        
        # Test avec un texte simple
        test_text = "Ceci est un test d'embedding"
        result = embeddings.embed_query(test_text)
        
        print_success(f"Connexion réussie!")
        print_info(f"Dimensions du vecteur: {len(result)}")
        print_info(f"Premiers éléments: [{', '.join(map(str, result[:3]))}...]")
        return True
        
    except Exception as e:
        print_error(f"Échec de la connexion: {str(e)}")
        if "401" in str(e) or "Incorrect API key" in str(e):
            print_info("→ Clé API invalide ou incorrecte")
        elif "403" in str(e):
            print_info("→ Accès refusé, vérifiez vos permissions")
        elif "429" in str(e):
            print_info("→ Limite de taux atteinte ou quota dépassé")
        return False

def main():
    """Fonction principale"""
    print_header("VÉRIFICATION DES CLÉS API - UM6P CHATBOT")
    
    # Charger les variables d'environnement
    print_info("Chargement du fichier .env...")
    load_dotenv()
    
    # Vérifier si le fichier .env existe
    if not os.path.exists(".env"):
        print_error("Fichier .env introuvable!")
        print_info("Créez un fichier .env dans le même répertoire que ce script")
        return
    
    print_success("Fichier .env trouvé\n")
    
    # Tests
    fireworks_ok = test_fireworks_api()
    openai_ok = test_openai_api()
    
    # Résumé
    print_header("RÉSUMÉ DES TESTS")
    
    if fireworks_ok:
        print_success("Fireworks API: Fonctionnelle")
    else:
        print_error("Fireworks API: Échec")
        print_info("→ Obtenez votre clé sur: https://fireworks.ai/")
    
    if openai_ok:
        print_success("OpenAI API: Fonctionnelle")
    else:
        print_error("OpenAI API: Échec")
        print_info("→ Obtenez votre clé sur: https://platform.openai.com/api-keys")
    
    print()
    if fireworks_ok and openai_ok:
        print_success("Toutes les clés API sont fonctionnelles! ✨")
        print_info("Vous pouvez maintenant lancer le chatbot avec: streamlit run model1.py")
    else:
        print_error("Certaines clés API ne fonctionnent pas")
        print_info("Veuillez corriger les problèmes avant de lancer le chatbot")
    
    print(f"\n{BLUE}{'='*60}{RESET}\n")

if __name__ == "__main__":
    main()
