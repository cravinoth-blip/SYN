import sys
import os

# Add the Questionnaire root to the path so Flask can find app.py, templates/, static/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app  # Vercel uses this as the WSGI handler
