import streamlit as st
import re
import pandas as pd
import pytesseract
from PIL import Image
import io

# 1. CONFIGURAÇÃO DA PÁGINA E INTERFACE VISUAL
st.set_page_config(page_title="Bot de Levantamento de Tachas", layout="wide", page_icon="🛣️")

st.title("🛣️ Bot de Levantamento de Tachas")
st.markdown("Cole o texto do WhatsApp ou anexe imagens (prints) para extrair os dados.")

# Interface de Entrada
col1, col2 = st.columns([2, 1])

with col1:
    texto_bruto_input = st.text_area("WhatsApp (Cole o texto aqui):", height=250)

with col2:
    imagens_anexadas = st.file_uploader("Anexar Imagens (OCR)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# 2. FUNÇÃO DE LIMPEZA
def extrair_apenas_numeros(valor):
    """Extrai apenas os dígitos de uma string. Se não houver números, retorna 0."""
    if not valor: return 0
    num = re.sub(r'\D', '', str(valor))
    return int(num) if num else 0

# 3. LÓGICA DE PROCESSAMENTO PRINCIPAL
if st.button("Gerar Tabela", type="primary", use_container_width=True):
    texto_final = texto_bruto_input

    # Processamento de Imagens (OCR)
    if imagens_anexadas:
        with st.spinner("⏳ A ler imagens com OCR... Aguarde."):
            for img_file in imagens_anexadas:
                try:
                    # Streamlit UploadedFile já funciona como BytesIO
                    img = Image.open(img_file)
                    texto_final += "\n" + pytesseract.image_to_string(img, lang='por')
                except Exception as e:
                    st.error(f"❌ Erro ao ler imagem: {e}")

    if not texto_final.strip():
        st.warning("⚠️ Erro: A caixa de texto está vazia e nenhuma imagem foi anexada.")
        st.stop()

    # Divisão por blocos (Evento)
    blocos = re.split(r'(?i)\*?Eventos?\s*[:\-]?.*?Ausência[^\n]*', texto_final)

    resultados = []

    for bloco in blocos:
        if not bloco.strip() or len(bloco) < 20: continue

        # --- DADOS BÁSICOS ---
        data_v, rodovia_v, via_v, sentido_v = "--", "--", "--", "--"
        km_ini, km_fim, qth_v = "--", "--", "--"
        bd, eixo, be, faixa_ad = 0, 0, 0, 0

        # Data
        m_data = re.search(r'Data\s*[:\-]?\s*\*?\s*(\d{2}[/.]\d{2}(?:[/.]\d{2,4})?)', bloco, re.IGNORECASE)
        if m_data:
            d = m_data.group(1).replace('.', '/')
            data_v = d if len(d) > 5 else f"{d}/2026"

        # Rodovia
        m_rod = re.search(r'Rodovia\s*[:\-]?\s*([A-Z]{2})\s*[-]?\s*(\d{3})', bloco, re.IGNORECASE)
        if m_rod:
            rodovia_v = f"{m_rod.group(1).upper()}-{m_rod.group(2)}"

        # Via (Dupla/Simples) + Regras BR-364/365
        m_via = re.search(r'(dupla|simples|duplicada)', bloco, re.IGNORECASE)
        if m_via:
            v_tipo = m_via.group(1).lower()
            via_v = "Pista dupla" if v_tipo in ['dupla', 'duplicada'] else "Pista simples"
        elif rodovia_v in ["BR-364", "BR-365"]:
            via_v = "Pista simples"

        # Sentido
        m_sen = re.search(r'Sentido\s*[:\-]?\s*\*?([A-Za-z]+)', bloco, re.IGNORECASE)
        if m_sen:
            s = m_sen.group(1).capitalize()
            sentido_v = "Leste" if s == "Lima" else "Oeste" if s == "Oscar" else s

        # --- LOCALIZAÇÃO (KM VS QTH) ---
        m_qth = re.search(r'Qth\s*[:\-.]?\s*([0-9\s\+/]+)', bloco, re.IGNORECASE)
        m_km_range = re.search(r'Km\s*(\d+)(?:\s*\+\s*\d+)?\s*(?:ao|/|-)\s*(\d+)', bloco, re.IGNORECASE)
        m_km_single = re.search(r'Km\s*(\d+)', bloco, re.IGNORECASE)

        if m_qth:
            qth_v = m_qth.group(1).strip()
        elif m_km_range:
            km_ini = f"{m_km_range.group(1)},000"
            km_fim = f"{m_km_range.group(2)},000"
        elif m_km_single:
            k = m_km_single.group(1)
            km_ini = f"{k},000"
            km_fim = f"{int(k) + 1},000"

        # --- TACHAS (APENAS NÚMEROS) ---
        m_bd = re.search(r'(?:Bordo\s*direito|Bord[oa].*?vermelh[ao]|BD)[^\d:]*[:\-]?\s*(\d+)', bloco, re.IGNORECASE)
        m_ex = re.search(r'(?:Eixo.*?central|Eixo.*?amarel[ao]|Eixo)[^\d:]*[:\-]?\s*(\d+)', bloco, re.IGNORECASE)
        m_be = re.search(r'(?:Bordo\s*esquerdo|Bord[oa].*?branc[oa]|BE)[^\d:]*[:\-]?\s*(\d+)', bloco, re.IGNORECASE)
        m_ad = re.search(r'(?:adicional|faixa)[^\d:]*[:\-]?\s*(\d+)', bloco, re.IGNORECASE)

        bd = extrair_apenas_numeros(m_bd.group(1)) if m_bd else 0
        eixo = extrair_apenas_numeros(m_ex.group(1)) if m_ex else 0
        be = extrair_apenas_numeros(m_be.group(1)) if m_be else 0
        faixa_ad = extrair_apenas_numeros(m_ad.group(1)) if m_ad else ""

        if rodovia_v != "--":
            resultados.append({
                'DATA': data_v, 'RODOVIA': rodovia_v, 
                'KM INICIAL': km_ini, 'KM FINAL': km_fim, 'QTH': qth_v,
                'VIA': via_v, 'SENTIDO': sentido_v,
                'BD (VERMELHO)': bd, 'EIXO (AMARELO)': eixo, 'BB (BRANCO)': be,
                'FAIXA AD': faixa_ad
            })

    if resultados:
        st.success(f"✅ Tabela Gerada com Sucesso: {len(resultados)} linhas identificadas.")
        
        df = pd.DataFrame(resultados)
        
        # Mostra a tabela na interface
        st.dataframe(df, use_container_width=True)
        
        # Prepara o botão de Download para Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Levantamento')
        buffer.seek(0)
        
        st.download_button(
            label="💾 Baixar Planilha Excel",
            data=buffer,
            file_name="Levantamento_Tachas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.error("❌ Nenhum dado identificado. Verifique o padrão das mensagens coladas.")
