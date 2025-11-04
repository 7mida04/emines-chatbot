# Vercel serverless function wrapper
import sys
import os

# Ajouter le dossier parent au path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app

# Export pour Vercel
handler = app
