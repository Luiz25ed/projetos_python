"""Módulo de configuração global da aplicação, estilização e constantes."""

import streamlit as st
from pathlib import Path

# Caminhos de Arquivos
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "validade_inteligente.db"

# Configurações de UI/UX
APP_TITLE = "Gestão Inteligente de Validade"
APP_ICON = "📉"

CATEGORIAS_KEYWORDS = {
    "Café": ["CAFE "],
    "Iogurte": ["IOG "],
    "Pão/Padaria": ["PAO ", "PANCO", "WICKBOLD", "PULLMAN", "BISNAGU"],
    "Biscoito": ["BISC "],
    "Refrigerante": ["REFR "],
    "Leite Fermentado": ["LEITE FERMENTADO", "YAKULT"],
    "Frios/Embutidos": ["MORTADELA", "PRESUNTO", "LINGUICA", "SALAME", "APRESUNTADO"],
    "Ovos": ["OVOS ", "OVO "],
}

CORES_CATEGORIA = {
    "Café": "#E3A23D",
    "Iogurte": "#4FA98C",
    "Carnes/Aves": "#C24A3F",
    "Frios/Embutidos": "#B589C9",
    "Leite Fermentado": "#7C9CC4",
    "Refrigerante": "#5FB8D9",
    "Biscoito": "#D9A5C0",
    "Pão/Padaria": "#C9A26B",
    "Ovos": "#D9C25F",
    "Outros": "#7D8590",
}

def init_page_config() -> None:
    """Inicializa as configurações de página do Streamlit."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )