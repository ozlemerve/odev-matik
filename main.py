import streamlit as st
from openai import OpenAI
import base64
import random
import urllib.parse

# --- AYARLAR ---
st.set_page_config(
    page_title="ÖdevMatik", 
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- MODERN CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        height: 60px;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        background-color: white;
        color: #31333F;
        font-weight: 800;
        font-size: 20px !important;
        transition: all 0.2s ease;
        box-
