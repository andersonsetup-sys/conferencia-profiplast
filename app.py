import streamlit as st
import re
import pandas as pd
from supabase import create_client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="PROFIPLAST | Web", layout="wide")

# Substitua com os dados que você pegou no Passo 1 (API do Supabase)
URL = "SUA_URL_AQUI"
KEY = "SUA_CHAVE_AQUI"

try:
    supabase = create_client(URL, KEY)
except:
    st.error("Configure a URL e a KEY do Supabase no código.")

# --- ESTILO PROFIPLAST ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stHeader { background-color: #004085; padding: 20px; border-radius: 10px; color: white; text-align: center; }
    .stTextInput > div > div > input { font-size: 30px !important; text-align: center; border: 2px solid #004085; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="stHeader"><h1>PROFIPLAST</h1><p>SISTEMA DE EXPEDIÇÃO WEB</p></div>', unsafe_allow_html=True)

# --- LÓGICA ZPL ---
def extrair_zpl(texto):
    pedidos = []
    blocos = re.findall(r"\^XA.*?\^XZ", texto, re.DOTALL)
    for b in blocos:
        m_id = re.search(r'\"id\":\"(\d+)\"', b)
        if m_id:
            qr_id = m_id.group(1)
            campos = re.findall(r"\^FD(.*?)\^FS", b)
            venda = "N/A"
            for i, t in enumerate(campos):
                if "Venda:" in t or "Pack ID:" in t:
                    venda = re.sub(r"\D", "", t) + (re.sub(r"\D", "", campos[i+1]) if i+1 < len(campos) else "")
                    break
            m_cli = re.search(r"\^FD([^^\r\n]+?)\s*\([^)]*\)\^FS", b)
            cliente = m_cli.group(1).strip() if m_cli else "Desconhecido"
            pedidos.append({"id": qr_id, "venda": venda, "cliente": cliente, "status": "Pendente"})
    return pedidos

# --- ABAS ---
tab1, tab2 = st.tabs(["?? GERENCIAL (PC)", "?? OPERAÇÃO (CELULAR)"])

with tab1:
    st.write("### Carregar Lote do Dia")
    zpl_raw = st.text_area("Cole o ZPL aqui", height=200)
    if st.button("?? ENVIAR PARA O CELULAR"):
        dados = extrair_zpl(zpl_raw)
        if dados:
            supabase.table("conferência").delete().neq("status", "Lixeira").execute() # Limpa anterior
            supabase.table("conferência").insert(dados).execute()
            st.success(f"{len(dados)} etiquetas enviadas para operação!")
            st.rerun()

with tab2:
    st.write("### Bipagem de Pacotes")
    scan = st.text_input("CLIQUE E BIPE", key="input_scan")
    
    if scan:
        id_lido = re.sub(r"\D", "", scan)
        res = supabase.table("conferência").select("*").eq("id", id_lido).execute()
        
        if res.data:
            p = res.data[0]
            if p['status'] == 'OK':
                st.warning(f"JÁ FOI BIPADO: {p['venda']}")
            else:
                supabase.table("conferência").update({"status": "OK"}).eq("id", id_lido).execute()
                st.success(f"VALIDADO: {p['venda']} - {p['cliente']}")
        else:
            st.error("PAGOTE NÃO ENCONTRADO NO LOTE!")

    # Painel de Progresso
    dados_atuais = supabase.table("conferência").select("*").execute()
    if dados_atuais.data:
        df = pd.DataFrame(dados_atuais.data)
        total = len(df)
        ok = len(df[df['status'] == 'OK'])
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Total no Lote", total)
        c2.metric("Conferidos", ok)
        
        st.write("#### Faltando:")
        st.dataframe(df[df['status'] == 'Pendente'][['venda', 'cliente']], use_container_width=True)
