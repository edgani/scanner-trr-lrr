from __future__ import annotations
import streamlit as st


def inject_theme() -> None:
    st.markdown("""
    <style>
    .block-container {padding-top: .18rem; padding-bottom: .28rem; max-width: 1500px;}
    h1 {margin-bottom: .12rem !important;}
    h2, h3 {letter-spacing:-0.01em; margin-top: .16rem !important; margin-bottom: .10rem !important;}
    div[data-testid="stMetric"] {background:linear-gradient(180deg,rgba(14,32,62,.95),rgba(8,20,39,.95));border:1px solid #203552;padding:4px 6px;border-radius:10px;min-height:0 !important;}
    div[data-testid="stMetric"] label {font-weight:700;}
    .stDataFrame {border:1px solid #203552;border-radius:10px;overflow:hidden;}
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"] h1),
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"] h2),
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"] h3) {margin-bottom:.04rem;}
    .stAlert {padding:.34rem .52rem;}
    div[data-testid="column"] {padding-top: 0 !important;}
    .element-container {margin-bottom: .02rem !important;}
    .stMarkdown p, .stMarkdown li {line-height: 1.08; margin-bottom: .02rem;}
    button[kind="secondary"] {padding-top:.16rem !important; padding-bottom:.16rem !important;}
    div[role="tablist"] button {padding-top:.15rem !important; padding-bottom:.15rem !important;}
    </style>
    """, unsafe_allow_html=True)
