"""
Script pour tester les modèles Fireworks AI disponibles
"""

from dotenv import load_dotenv
import os
from openai import OpenAI

# Couleurs pour le terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Affiche un en-tête coloré"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    """Affiche un message de succès"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Affiche un message d'erreur"""
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    """Affiche un message d'information"""
    print(f"{YELLOW}ℹ {text}{RESET}")

def test_model(client, model_name):
    """Test un modèle spécifique"""
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Tu es un assistant utile."},
                {"role": "user", "content": "Dis juste 'OK'"}
            ],
            temperature=0.1,
            max_tokens=10
        )
        result = response.choices[0].message.content
        return True, result
    except Exception as e:
        return False, str(e)

def main():
    """Fonction principale"""
    print_header("TEST DES MODÈLES FIREWORKS AI DISPONIBLES")
    
    # Charger les variables d'environnement
    load_dotenv()
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print_error("FIREWORKS_API_KEY non trouvée dans .env")
        return
    
    print_info(f"Clé API: {api_key[:10]}...{api_key[-4:]}\n")
    
    # Liste des modèles populaires à tester
    models_to_test = [
        # DeepSeek models
        "accounts/fireworks/models/deepseek-v3",
        "accounts/fireworks/models/deepseek-v3p1",
        "accounts/fireworks/models/deepseek-v2-5",
        "accounts/fireworks/models/deepseek-coder",
        
        # Llama models
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "accounts/fireworks/models/llama-v3p2-3b-instruct",
        "accounts/fireworks/models/llama-v3p1-70b-instruct",
        "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "accounts/fireworks/models/llama-v3-70b-instruct",
        
        # Mixtral models
        "accounts/fireworks/models/mixtral-8x7b-instruct",
        "accounts/fireworks/models/mixtral-8x22b-instruct",
        
        # Qwen models
        "accounts/fireworks/models/qwen2p5-72b-instruct",
        "accounts/fireworks/models/qwen-2-72b-instruct",
        
        # Autres modèles populaires
        "accounts/fireworks/models/phi-3-vision-128k-instruct",
        "accounts/fireworks/models/mythomax-l2-13b",
    ]
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.fireworks.ai/inference/v1"
    )
    
    working_models = []
    failed_models = []
    
    print_header("TESTS EN COURS...")
    
    for i, model in enumerate(models_to_test, 1):
        model_short = model.split('/')[-1]
        print(f"\n[{i}/{len(models_to_test)}] Test de: {BLUE}{model_short}{RESET}")
        
        success, result = test_model(client, model)
        
        if success:
            print_success(f"FONCTIONNE! Réponse: {result}")
            working_models.append(model)
        else:
            if "404" in result:
                print_error("Modèle non trouvé (404)")
            elif "401" in result:
                print_error("Non autorisé (401) - Problème de clé API")
            elif "403" in result:
                print_error("Accès refusé (403) - Modèle non accessible")
            else:
                print_error(f"Erreur: {result[:50]}...")
            failed_models.append(model)
    
    # Résumé
    print_header("RÉSUMÉ DES RÉSULTATS")
    
    if working_models:
        print_success(f"{len(working_models)} modèle(s) fonctionnel(s) trouvé(s):\n")
        for model in working_models:
            print(f"  {GREEN}✓{RESET} {model}")
        
        print(f"\n{YELLOW}{'='*70}{RESET}")
        print_info("MODÈLE RECOMMANDÉ POUR VOTRE CHATBOT:")
        print(f"\n  {GREEN}{working_models[0]}{RESET}\n")
        print_info("Copiez ce nom de modèle dans votre fichier model1.py")
        print(f"{YELLOW}{'='*70}{RESET}\n")
    else:
        print_error("Aucun modèle fonctionnel trouvé!")
        print_info("Vérifiez:")
        print("  1. Votre clé API Fireworks est valide")
        print("  2. Votre compte a accès aux modèles")
        print("  3. Visitez https://fireworks.ai/models pour voir les modèles disponibles")
    
    print(f"\n{BLUE}{'='*70}{RESET}\n")

if __name__ == "__main__":
    main()
