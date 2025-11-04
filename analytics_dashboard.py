"""
Dashboard Analytics Détaillé pour EMINES Chatbot
Accès: streamlit run analytics_dashboard.py
"""

import streamlit as st
import json
import os
from datetime import datetime
from collections import Counter
import pandas as pd

ANALYTICS_FILE = "analytics.json"

def load_analytics():
    """Charge les données analytics"""
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"visitors": 0, "interactions": []}
    return {"visitors": 0, "interactions": []}

st.set_page_config(
    page_title="Analytics EMINES Chatbot",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard Analytics - EMINES Chatbot")
st.markdown("**Journées Portes Ouvertes - Statistiques en temps réel**")

# Charger les données
analytics = load_analytics()

# === MÉTRIQUES PRINCIPALES ===
st.markdown("## 📈 Vue d'ensemble")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="👥 Visiteurs Total",
        value=analytics["visitors"],
        delta=None
    )

with col2:
    total_questions = len(analytics["interactions"])
    st.metric(
        label="💬 Questions Posées",
        value=total_questions,
        delta=None
    )

with col3:
    avg_per_visitor = round(total_questions / analytics["visitors"], 1) if analytics["visitors"] > 0 else 0
    st.metric(
        label="📊 Questions / Visiteur",
        value=avg_per_visitor,
        delta=None
    )

with col4:
    # Dernière activité
    if analytics["interactions"]:
        last_time = datetime.fromisoformat(analytics["interactions"][-1]["timestamp"])
        time_diff = datetime.now() - last_time
        minutes_ago = int(time_diff.total_seconds() / 60)
        st.metric(
            label="🕐 Dernière activité",
            value=f"Il y a {minutes_ago}min",
            delta=None
        )
    else:
        st.metric(label="🕐 Dernière activité", value="Aucune", delta=None)

st.markdown("---")

# === TYPE D'ENTRÉE ===
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("## 📊 Répartition par Type d'Entrée")
    
    if analytics["interactions"]:
        input_types = [i["input_type"] for i in analytics["interactions"]]
        input_counts = Counter(input_types)
        
        # Créer un DataFrame
        df_types = pd.DataFrame({
            'Type': [
                {'text': '⌨️ Texte', 'voice': '🎤 Vocal', 'suggested': '💡 Suggérée'}.get(k, k)
                for k in input_counts.keys()
            ],
            'Nombre': list(input_counts.values())
        })
        
        # Afficher comme tableau
        st.dataframe(df_types, use_container_width=True, hide_index=True)
        
        # Graphique en barres
        st.bar_chart(df_types.set_index('Type'))
    else:
        st.info("Aucune donnée disponible")

with col_right:
    st.markdown("## 🎯 Statistiques")
    
    if analytics["interactions"]:
        text_count = sum(1 for i in analytics["interactions"] if i["input_type"] == "text")
        voice_count = sum(1 for i in analytics["interactions"] if i["input_type"] == "voice")
        suggested_count = sum(1 for i in analytics["interactions"] if i["input_type"] == "suggested")
        
        total = len(analytics["interactions"])
        
        st.metric("⌨️ Texte", f"{text_count} ({round(text_count/total*100)}%)")
        st.metric("🎤 Vocal", f"{voice_count} ({round(voice_count/total*100)}%)")
        st.metric("💡 Suggérée", f"{suggested_count} ({round(suggested_count/total*100)}%)")

st.markdown("---")

# === TOP QUESTIONS ===
st.markdown("## 🔥 Top 10 Questions les Plus Posées")

if analytics["interactions"]:
    questions = [i["question"] for i in analytics["interactions"]]
    question_counts = Counter(questions)
    top_questions = question_counts.most_common(10)
    
    # Créer un DataFrame
    df_questions = pd.DataFrame({
        'Rang': range(1, len(top_questions) + 1),
        'Question': [q for q, _ in top_questions],
        'Fréquence': [c for _, c in top_questions]
    })
    
    st.dataframe(df_questions, use_container_width=True, hide_index=True)
else:
    st.info("Aucune question posée pour le moment")

st.markdown("---")

# === HISTORIQUE RÉCENT ===
st.markdown("## 📜 Dernières Interactions (10 plus récentes)")

if analytics["interactions"]:
    recent = analytics["interactions"][-10:][::-1]  # 10 dernières, inversées
    
    for i, interaction in enumerate(recent, 1):
        with st.expander(f"#{i} - {interaction['timestamp'][:19]} - {interaction['input_type'].upper()}"):
            st.markdown(f"**❓ Question:**")
            st.text(interaction['question'])
            st.markdown(f"**💬 Réponse:**")
            st.text(interaction['response'])
else:
    st.info("Aucune interaction enregistrée")

st.markdown("---")

# === EXPORT & ACTIONS ===
st.markdown("## 🛠️ Actions")

col_act1, col_act2, col_act3 = st.columns(3)

with col_act1:
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()

with col_act2:
    if st.button("📥 Exporter JSON", use_container_width=True):
        st.download_button(
            label="Télécharger analytics.json",
            data=json.dumps(analytics, indent=2, ensure_ascii=False),
            file_name=f"analytics_emines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

with col_act3:
    if st.button("⚠️ Réinitialiser Tout", use_container_width=True):
        if st.checkbox("Confirmer la réinitialisation"):
            with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"visitors": 0, "interactions": []}, f)
            st.success("✅ Statistiques réinitialisées!")
            st.rerun()

# === FOOTER ===
st.markdown("---")
st.caption("📊 Dashboard Analytics EMINES - Mise à jour automatique disponible")
st.caption("💡 Astuce: Cliquez sur 'Actualiser' pour voir les dernières données")
