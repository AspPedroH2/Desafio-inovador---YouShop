"""YouShop Controladoria AI — Plataforma de Governança, Normalização e Dashboards Setoriais."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.banco_dados_youshop import CONSULTAS_PRONTAS, GerenciadorBaseCentral
from src.conciliacao_financeira import conciliar_operacoes, normalizar_planilhas
from src.gerador_planilhas_teste import gerar_planilhas_teste
from src.inteligencia_artificial import (
    APELIDOS_TABELAS,
    auditar_divergencias,
    gerar_relatorio_normalizacao,
    ler_e_mapear_planilhas,
)
from src.protecao_dados_lgpd import preparar_pacote_seguro

st.set_page_config(
    page_title="Central de governança de dados - YouShop",
    layout="wide",
    initial_sidebar_state="expanded",
)

ESTILO_YOUSHO = """
<style>
    /* Fundo azul escuro com barra verde no topo */
    .stApp {
        background-color: #0B1F3A;
        color: #FFFFFF;
        border-top: 8px solid #A3E635;
    }
    header[data-testid="stHeader"] {
        background-color: #0B1F3A;
        border-top: 6px solid #A3E635;
    }

    /* Barra lateral azul com borda verde lateral */
    section[data-testid="stSidebar"] {
        background-color: #07162B;
        border-right: 6px solid #A3E635;
        color: #FFFFFF;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #0B1F3A !important;
        color: #FFFFFF !important;
        border: 1px solid #1E3A5F !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #0B1F3A !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 2px solid #A3E635 !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] .stButton > button * {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #13315C !important;
        border-color: #A3E635 !important;
        color: #FFFFFF !important;
    }

    /* Cabeçalho azul escuro com letras brancas e barra verde */
    .ys-cabecalho {
        background-color: #07162B;
        color: #FFFFFF;
        padding: 1.1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid #1E3A5F;
        border-top: 6px solid #A3E635;
        border-left: 6px solid #A3E635;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22);
    }
    .ys-cabecalho h1 {
        margin: 0;
        font-size: 1.65rem;
        color: #FFFFFF;
    }
    .ys-cabecalho p {
        margin: 0.25rem 0 0 0;
        color: #CBD5E1;
        font-size: 0.94rem;
    }

    /* Abas no fundo azul com destaque verde padrão YouShop */
    div[data-baseweb="tab-list"],
    div[data-testid="stTabs"] [role="tablist"] {
        gap: 0.45rem;
    }
    button[data-baseweb="tab"],
    div[data-testid="stTabs"] button[role="tab"] {
        background-color: transparent !important;
        color: #CBD5E1 !important;
        padding: 0.55rem 0.9rem !important;
        border: none !important;
    }
    button[data-baseweb="tab"] *,
    div[data-testid="stTabs"] button[role="tab"] * {
        color: #CBD5E1 !important;
    }
    button[data-baseweb="tab"]:hover *,
    div[data-testid="stTabs"] button[role="tab"]:hover * {
        color: #A3E635 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #A3E635 !important;
        font-weight: 700 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] *,
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
        color: #A3E635 !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #A3E635 !important;
    }

    /* Rótulos dos widgets na área principal (fundo azul) */
    .main label, .main [data-testid="stWidgetLabel"] p {
        color: #FFFFFF !important;
        font-weight: 600;
    }

    /* Quadros no tom azul escuro (#07162B) com letras brancas */
    .ys-quadro,
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #07162B !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1px solid #1E3A5F !important;
        border-left: 5px solid #A3E635 !important;
        padding: 0.95rem 1.15rem !important;
        margin-bottom: 0.85rem;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.22);
    }
    .ys-quadro *,
    div[data-testid="stVerticalBlockBorderWrapper"] h1,
    div[data-testid="stVerticalBlockBorderWrapper"] h2,
    div[data-testid="stVerticalBlockBorderWrapper"] h3,
    div[data-testid="stVerticalBlockBorderWrapper"] h4,
    div[data-testid="stVerticalBlockBorderWrapper"] h5,
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] span,
    div[data-testid="stVerticalBlockBorderWrapper"] label,
    div[data-testid="stVerticalBlockBorderWrapper"] li {
        color: #FFFFFF !important;
    }

    /* Cards de Métricas no tom azul escuro com letras brancas e barra verde */
    div[data-testid="stMetric"] {
        background-color: #07162B !important;
        border: 1px solid #1E3A5F;
        border-top: 4px solid #A3E635;
        border-left: 4px solid #A3E635;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.20);
    }
    div[data-testid="stMetric"] * {
        color: #FFFFFF !important;
    }

    /* Caixa de texto direta do Relatório de Alterações */
    .ys-relatorio-caixa {
        background-color: #07162B;
        color: #FFFFFF;
        border: 1px solid #1E3A5F;
        border-left: 6px solid #A3E635;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        line-height: 1.7;
        font-size: 0.94rem;
    }
    .ys-relatorio-caixa ul {
        margin: 0.4rem 0 0 0;
        padding-left: 1.2rem;
    }
    .ys-relatorio-caixa li {
        color: #F8FAFC;
        margin-bottom: 0.35rem;
    }

    /* Cards de auditoria e resumo no tom azul escuro com texto branco */
    .ys-auditoria {
        background-color: #07162B;
        color: #FFFFFF;
        border: 1px solid #1E3A5F;
        border-left: 6px solid #A3E635;
        border-radius: 8px;
        padding: 0.85rem 1.05rem;
        margin-bottom: 0.65rem;
    }
    .ys-auditoria * { color: #FFFFFF !important; }
    .ys-grav-alta { border-left-color: #DC2626 !important; }
    .ys-grav-media { border-left-color: #D97706 !important; }
    .ys-grav-baixa { border-left-color: #38BDF8 !important; }

    .ys-resumo {
        background-color: #07162B;
        color: #FFFFFF;
        border: 1px solid #1E3A5F;
        border-top: 4px solid #A3E635;
        border-left: 6px solid #A3E635;
        border-radius: 10px;
        padding: 1.1rem 1.35rem;
        line-height: 1.65;
        margin-bottom: 0.9rem;
    }
    .ys-resumo * { color: #FFFFFF !important; }

    /* Expanders, caixas de seleção e editores no tom azul escuro com letras brancas */
    div[data-testid="stExpander"],
    div[data-testid="stExpander"] details {
        background-color: #07162B !important;
        border: 1px solid #1E3A5F !important;
        border-radius: 8px !important;
        border-left: 5px solid #A3E635 !important;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #07162B !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stExpander"] summary:hover {
        background-color: #10284A !important;
    }
    div[data-testid="stExpander"] summary svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stExpander"] * {
        color: #FFFFFF !important;
    }
    div[data-testid="stExpander"] code,
    div[data-testid="stVerticalBlockBorderWrapper"] code,
    .ys-quadro code,
    .ys-relatorio-caixa code {
        background-color: #132C4E !important;
        color: #A3E635 !important;
        padding: 0.12rem 0.38rem !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
    }
    .main div[data-baseweb="select"] > div,
    .main textarea {
        background-color: #07162B !important;
        color: #FFFFFF !important;
        border: 1px solid #1E3A5F !important;
        border-radius: 8px !important;
    }
    .main div[data-baseweb="select"] span {
        color: #FFFFFF !important;
    }

    /* Botões na área principal e caixas de sucesso: fundo azul, borda verde, fonte branca */
    .main .stButton > button[kind="primary"],
    .main .stDownloadButton > button {
        background-color: #0B1F3A !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 2px solid #A3E635 !important;
        border-radius: 8px !important;
    }
    .main .stButton > button[kind="primary"] *,
    .main .stDownloadButton > button * {
        color: #FFFFFF !important;
    }
    .main .stButton > button[kind="primary"]:hover,
    .main .stDownloadButton > button:hover {
        background-color: #13315C !important;
        border-color: #A3E635 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]),
    div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) > div,
    div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) [role="alert"] {
        background-color: #0B1F3A !important;
        border: 2px solid #A3E635 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) * {
        color: #FFFFFF !important;
    }
</style>
"""
st.markdown(ESTILO_YOUSHO, unsafe_allow_html=True)

CORES_SETORES = {
    "Financeiro": "#38BDF8",
    "Controladoria": "#3B82F6",
    "Diretoria": "#A3E635",
}


def _reais(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _aplicar_tema_grafico(fig: Any) -> Any:
    fig.update_layout(
        paper_bgcolor="#07162B",
        plot_bgcolor="#07162B",
        font=dict(color="#FFFFFF"),
        title_font=dict(color="#FFFFFF", size=15),
        legend=dict(font=dict(color="#FFFFFF")),
        margin=dict(t=48, b=36, l=36, r=24),
    )
    fig.update_xaxes(title_font=dict(color="#FFFFFF"), tickfont=dict(color="#E2E8F0"), gridcolor="#1E3A5F")
    fig.update_yaxes(title_font=dict(color="#FFFFFF"), tickfont=dict(color="#E2E8F0"), gridcolor="#1E3A5F")
    return fig


def _calcular_indicadores(df_fato: pd.DataFrame, df_div: pd.DataFrame) -> dict[str, Any]:
    vol_conc = float(df_fato["valor_bruto"].sum()) if not df_fato.empty else 0.0
    vol_div = (
        float(df_div[df_div["status_checkout"] == "Aprovada"]["valor_bruto"].sum())
        if not df_div.empty
        else 0.0
    )
    volume_aprovado = round(vol_conc + vol_div, 2)
    receita_ys = round(float(df_fato["taxa_youshop"].sum()), 2) if not df_fato.empty else 0.0
    repasse_prod = round(float(df_fato["repasse_produtor"].sum()), 2) if not df_fato.empty else 0.0
    comissao_creat = round(float(df_fato["comissao_creator"].sum()), 2) if not df_fato.empty else 0.0

    impacto_estornos = 0.0
    if not df_div.empty:
        filtro_est = df_div["tipo_divergencia"].str.contains("Contestação|Estorno", case=False, na=False)
        impacto_estornos = round(float(df_div.loc[filtro_est, "impacto_financeiro"].sum()), 2)

    impacto_div = round(float(df_div["impacto_financeiro"].sum()), 2) if not df_div.empty else 0.0
    total_aprovadas = len(df_fato) + (len(df_div[df_div["status_checkout"] == "Aprovada"]) if not df_div.empty else 0)
    taxa_acerto = round((len(df_fato) / total_aprovadas) * 100, 2) if total_aprovadas > 0 else 100.0

    return {
        "volume_vendas_aprovadas": volume_aprovado,
        "receita_youshop": receita_ys,
        "repasse_produtores": repasse_prod,
        "comissoes_creators": comissao_creat,
        "impacto_estornos": impacto_estornos,
        "impacto_divergencias": impacto_div,
        "taxa_conciliacao_pct": taxa_acerto,
        "qtd_conciliadas": int(len(df_fato)),
        "qtd_divergencias": int(len(df_div)),
    }


def _processar_entrada(
    arquivos: Any,
    modo_envio: str,
    banco: GerenciadorBaseCentral,
    chave_api: str,
    gravar_automatico: bool = True,
) -> None:
    amostras, tabelas_brutas = preparar_pacote_seguro(arquivos)
    leitura_ia = ler_e_mapear_planilhas(amostras, chave_api=chave_api)

    st.session_state["amostras_protegidas"] = amostras
    st.session_state["tabelas_brutas"] = tabelas_brutas
    st.session_state["leitura_ia"] = leitura_ia
    st.session_state["modo_envio_atual"] = modo_envio

    if gravar_automatico:
        _normalizar_e_gravar(banco, modo_envio, chave_api)


def _normalizar_e_gravar(banco: GerenciadorBaseCentral, modo_envio: str, chave_api: str) -> None:
    tabelas_brutas = st.session_state.get("tabelas_brutas", {})
    leitura_ia = st.session_state.get("leitura_ia", {})
    if not tabelas_brutas or not leitura_ia:
        return

    tabelas_norm, resumo_arqs, alteracoes = normalizar_planilhas(tabelas_brutas, leitura_ia)
    relatorio_norm = gerar_relatorio_normalizacao(alteracoes, chave_api=chave_api)
    resultado = conciliar_operacoes(tabelas_norm)
    banco.gravar_conferencia(
        resultado_conciliacao=resultado,
        resumo_arquivos=resumo_arqs,
        modo_envio=modo_envio,
    )

    indicadores = _calcular_indicadores(resultado["df_fato_conciliado"], resultado["df_divergencias"])
    auditoria = auditar_divergencias(resultado["df_divergencias"], indicadores, chave_api=chave_api)

    st.session_state["tabelas_normalizadas"] = tabelas_norm
    st.session_state["relatorio_normalizacao"] = relatorio_norm
    st.session_state["auditoria_ia"] = auditoria
    st.session_state["situacao_gravacao"] = {"gravado": True, "indicadores": indicadores}


banco_central = GerenciadorBaseCentral()

st.markdown(
    """
    <div class="ys-cabecalho">
        <h1>🟢 Central de governança de dados - YouShop</h1>
        <p>Carga, limpeza e transformação de dados via IA para o financeiro e controladoria</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 🟢 Carga de Dados")
    chave_digitada = st.text_input(
        "Chave API Gemini (Opcional)",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help="Com chave informada, a IA Gemini executa leitura, relatório de alterações e auditoria.",
    )
    chave_ativa = chave_digitada.strip()

    if st.button("🟢 Simular Carga Automática (Integração Sistemas)", width="stretch"):
        with st.spinner("Normalizando planilhas, protegendo LGPD e alimentando painéis..."):
            caminhos = gerar_planilhas_teste()
            _processar_entrada(
                arquivos=caminhos,
                modo_envio="Carga Automática",
                banco=banco_central,
                chave_api=chave_ativa,
                gravar_automatico=True,
            )
        st.success("Carga concluída!")

    st.markdown("---")
    arquivos_enviados = st.file_uploader(
        "📤 Envio Manual (.xlsx / .csv)",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
    )
    if arquivos_enviados and st.button("🔍 Ler e Normalizar Planilhas", width="stretch"):
        with st.spinner("Lendo, normalizando e gravando na Base Central..."):
            _processar_entrada(
                arquivos=arquivos_enviados,
                modo_envio="Envio Manual",
                banco=banco_central,
                chave_api=chave_ativa,
                gravar_automatico=True,
            )
        st.success("Planilhas normalizadas e gravadas!")

    st.markdown("---")
    df_fato_banco = banco_central.carregar_tabela("fato_conciliacao_vendas")
    df_div_banco = banco_central.carregar_tabela("fato_divergencias")
    meses_disp = set()
    if not df_fato_banco.empty and "data_competencia" in df_fato_banco.columns:
        meses_disp.update(df_fato_banco["data_competencia"].dropna().astype(str).tolist())
    if not df_div_banco.empty and "data_competencia" in df_div_banco.columns:
        meses_disp.update(df_div_banco["data_competencia"].dropna().astype(str).tolist())
    opcoes_mes = ["Todos os Meses"] + sorted(m for m in meses_disp if m)
    competencia_global = st.selectbox("📅 Mês de Competência", opcoes_mes, index=0)

    st.caption(f"🧠 Motor: **{'Gemini 2.5 Flash' if chave_ativa else 'Regras Locais (Sem Chave)'}**")

    st.markdown("---")
    if st.button("🗑️ Zerar Base e Cache", width="stretch"):
        banco_central.limpar_base_dados()
        st.session_state.clear()
        st.rerun()


aba1, aba2, aba3, aba4 = st.tabs(
    [
        "1️⃣ Dados Normalizados & Relatório IA",
        "2️⃣ Histórico por Setor",
        "3️⃣ Base Central",
        "4️⃣ Dashboards por Setor",
    ]
)

# ==============================================================================
# ABA 1: TABELAS NORMALIZADAS + RELATÓRIO DIRETO DA IA (SEM CONFIABILIDADE)
# ==============================================================================
with aba1:
    amostras = st.session_state.get("amostras_protegidas", [])
    leitura_ia = st.session_state.get("leitura_ia", {})
    relatorio_norm = st.session_state.get("relatorio_normalizacao", {})
    tabelas_norm = st.session_state.get("tabelas_normalizadas", {})
    sit_gravacao = st.session_state.get("situacao_gravacao", {})

    if not tabelas_norm:
        st.markdown(
            '<div class="ys-quadro"><strong>Nenhuma carga normalizada na sessão atual.</strong><br>'
            'Clique em <strong>"🟢 Simular Carga Automática (Integração Sistemas)"</strong> na barra lateral ou envie suas planilhas.</div>',
            unsafe_allow_html=True,
        )
    else:
        mapa_apelido_para_chave = {
            APELIDOS_TABELAS[k]: k for k in tabelas_norm.keys() if k in APELIDOS_TABELAS
        }
        opcoes_tabelas = ["Todas as Tabelas"] + list(mapa_apelido_para_chave.keys())
        filtro_tabela = st.selectbox("Filtrar por Tabela Normalizada:", opcoes_tabelas)

        # 1. PRIMEIRO: Tabelas Já Normalizadas
        with st.container(border=True):
            st.markdown("### 📊 Tabelas Já Normalizadas")
            if filtro_tabela == "Todas as Tabelas":
                for apelido, chave_interna in mapa_apelido_para_chave.items():
                    df_t = tabelas_norm[chave_interna]
                    st.markdown(f"**{apelido}** ({len(df_t)} linhas)")
                    st.dataframe(df_t.head(8).astype(str), width="stretch", hide_index=True)
            else:
                chave_sel = mapa_apelido_para_chave[filtro_tabela]
                df_t = tabelas_norm[chave_sel]
                st.markdown(f"**{filtro_tabela}** ({len(df_t)} linhas)")
                st.dataframe(df_t.astype(str), width="stretch", hide_index=True)

        # 2. EM SEGUIDA: Caixa de Texto com Frases Bem Diretas do Relatório
        if relatorio_norm:
            frases_lista = relatorio_norm.get("frases", [])
            if filtro_tabela != "Todas as Tabelas":
                frases_filtradas = [f for f in frases_lista if f.get("tabela_destino") == filtro_tabela]
            else:
                frases_filtradas = frases_lista

            with st.container(border=True):
                st.markdown(f"### 📝 Relatório das Alterações ({relatorio_norm.get('modo_motor', 'IA')})")
                if frases_filtradas:
                    itens_html = "".join(f"<li>{item['frase']}</li>" for item in frases_filtradas)
                    st.markdown(
                        f'<div class="ys-relatorio-caixa"><ul>{itens_html}</ul></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.write("Nenhuma alteração registrada para a tabela selecionada.")

        # 3. Revisão apenas se houver coluna desconhecida fora do padrão + LGPD recolhido
        for idx_arq, arq in enumerate(leitura_ia.get("arquivos", [])):
            pontos = arq.get("pontos_incerteza", [])
            if pontos:
                with st.expander(f"⚠️ Colunas fora do padrão em {arq['arquivo']}", expanded=True):
                    for ponto in pontos:
                        st.write(f"- **{ponto['coluna']}**: {ponto['motivo_incerteza']} ({ponto['solucao_proposta']})")

        if amostras:
            with st.expander("🔒 Prova de Proteção LGPD (Colunas Sensíveis Ocultadas)", expanded=False):
                for amostra in amostras:
                    cols_prot = amostra.get("colunas_protegidas", [])
                    st.markdown(
                        f"**{amostra['arquivo']}** ({amostra['total_linhas']} linhas) — Ocultadas: "
                        f"`{', '.join(cols_prot) if cols_prot else 'Nenhuma'}`"
                    )
                    st.dataframe(pd.DataFrame(amostra["amostra_protegida"]).astype(str), width="stretch", hide_index=True)

        if sit_gravacao.get("gravado"):
            ind = sit_gravacao.get("indicadores", {})
            st.markdown(
                f'<div class="ys-quadro">✅ <strong>Gravado na Base Central:</strong> '
                f'{ind.get("qtd_conciliadas", 0)} vendas conferidas e {ind.get("qtd_divergencias", 0)} divergências isoladas.</div>',
                unsafe_allow_html=True,
            )

# ==============================================================================
# ABA 2: DASHBOARD DE QUANTIDADE DE CARGAS POR SETOR (FINANCEIRO, CONTROLADORIA E DIRETORIA)
# ==============================================================================
with aba2:
    df_hist = banco_central.buscar_historico_conferencias()
    if df_hist.empty:
        st.markdown(
            '<div class="ys-quadro">Nenhuma carga registrada ainda. Execute uma carga pelo menu lateral.</div>',
            unsafe_allow_html=True,
        )
    else:
        qtd_fin = int((df_hist["setor_origem"] == "Financeiro").sum())
        qtd_ctrl = int((df_hist["setor_origem"] == "Controladoria").sum())
        qtd_dir = int((df_hist["setor_origem"] == "Diretoria").sum())
        total_cargas = len(df_hist)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Cargas", total_cargas)
        m2.metric("Cargas — Financeiro", qtd_fin)
        m3.metric("Cargas — Controladoria", qtd_ctrl)
        m4.metric("Cargas — Diretoria", qtd_dir)

        df_por_setor = (
            df_hist.groupby("setor_origem", as_index=False)
            .agg(cargas=("id_log", "count"), linhas_processadas=("total_registros", "sum"))
        )
        df_por_setor["ordem"] = df_por_setor["setor_origem"].map({"Financeiro": 1, "Controladoria": 2, "Diretoria": 3})
        df_por_setor = df_por_setor.sort_values("ordem")

        df_hist["data_exec"] = df_hist["data_hora_execucao"].str.slice(0, 10)
        df_por_data = (
            df_hist.groupby(["data_exec", "setor_origem"], as_index=False)
            .agg(cargas=("id_log", "count"))
            .sort_values("data_exec")
        )

        g_h1, g_h2 = st.columns(2)
        with g_h1:
            with st.container(border=True):
                fig_setor = px.bar(
                    df_por_setor,
                    x="setor_origem",
                    y="cargas",
                    text="cargas",
                    title="Quantidade de Cargas por Setor",
                    labels={"setor_origem": "Setor", "cargas": "Quantidade de Cargas"},
                    color="setor_origem",
                    color_discrete_map=CORES_SETORES,
                )
                fig_setor.update_traces(textposition="outside")
                fig_setor.update_layout(showlegend=False)
                st.plotly_chart(_aplicar_tema_grafico(fig_setor), width="stretch")

        with g_h2:
            with st.container(border=True):
                fig_data = px.bar(
                    df_por_data,
                    x="data_exec",
                    y="cargas",
                    color="setor_origem",
                    barmode="group",
                    text="cargas",
                    title="Cargas por Data e Setor",
                    labels={"data_exec": "Data da Carga", "cargas": "Quantidade de Cargas", "setor_origem": "Setor"},
                    color_discrete_map=CORES_SETORES,
                )
                fig_data.update_traces(textposition="outside")
                st.plotly_chart(_aplicar_tema_grafico(fig_data), width="stretch")

# ==============================================================================
# ABA 3: BASE CENTRAL — FONTE DE DADOS PARA ALIMENTAR OS PAINÉIS DA DIRETORIA
# ==============================================================================
with aba3:
    st.markdown(
        '<div class="ys-quadro">'
        '<h3 style="margin:0 0 0.25rem 0;">🗄️ Fonte de dados para alimentar os painéis da Diretoria</h3>'
        '<p style="margin:0;">Base central padronizada da YouShop disponível para consultas prontas ou livres.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    catalogo = banco_central.listar_tabelas_base()
    if not catalogo or sum(t["linhas"] for t in catalogo) == 0:
        st.markdown(
            '<div class="ys-quadro">Base Central vazia. Execute uma carga pelo menu lateral.</div>',
            unsafe_allow_html=True,
        )
    else:
        with st.expander("🗂️ Tabelas Disponíveis na Base Central", expanded=False):
            for t in catalogo:
                st.markdown(f"- **{t['nome_amigavel']}** (`{t['tabela']}` — {t['linhas']} linhas)")

        with st.container(border=True):
            pergunta = st.selectbox("Consulta Pronta:", list(CONSULTAS_PRONTAS.keys()))
            sql_txt = st.text_area("Consulta SQL (somente leitura):", value=CONSULTAS_PRONTAS[pergunta], height=145)
            if st.button("▶ Executar Consulta", type="primary"):
                try:
                    st.session_state["res_sql"] = banco_central.executar_consulta_leitura(sql_txt)
                except Exception as exc:
                    st.error(f"Erro na consulta: {exc}")

            df_sql = st.session_state.get("res_sql")
            if df_sql is None:
                try:
                    df_sql = banco_central.executar_consulta_leitura(CONSULTAS_PRONTAS[pergunta])
                except Exception:
                    df_sql = pd.DataFrame()
            if not df_sql.empty:
                st.dataframe(df_sql, width="stretch", hide_index=True)
                st.download_button(
                    "📥 Baixar Resultado",
                    data=df_sql.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
                    file_name="youshop_consulta.csv",
                    mime="text/csv",
                )

# ==============================================================================
# ABA 4: DASHBOARDS COM FILTRO SUSPENSO POR SETOR (DIRETORIA, FINANCEIRO, CONTROLADORIA)
# ==============================================================================
with aba4:
    df_fato_v = banco_central.carregar_tabela("fato_conciliacao_vendas")
    df_div_v = banco_central.carregar_tabela("fato_divergencias")
    df_resumo_v = banco_central.carregar_tabela("fato_resumo_vendas")

    if competencia_global != "Todos os Meses":
        if not df_fato_v.empty:
            df_fato_v = df_fato_v[df_fato_v["data_competencia"] == competencia_global]
        if not df_div_v.empty:
            df_div_v = df_div_v[df_div_v["data_competencia"] == competencia_global]
        if not df_resumo_v.empty:
            df_resumo_v = df_resumo_v[df_resumo_v["data_competencia"] == competencia_global]

    if df_fato_v.empty and df_div_v.empty:
        st.markdown(
            '<div class="ys-quadro">Nenhum dado disponível. Execute uma carga pelo menu lateral.</div>',
            unsafe_allow_html=True,
        )
    else:
        setor_dashboard = st.selectbox(
            "Filtrar Dashboard por Setor:",
            ["Diretoria", "Financeiro", "Controladoria"],
        )

        # ----------------------------------------------------------------------
        # VISÃO DIRETORIA (RESUMO EXECUTIVO VIA DASHBOARD)
        # ----------------------------------------------------------------------
        if setor_dashboard == "Diretoria":
            ind_exec = _calcular_indicadores(df_fato_v, df_div_v)
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Vendas Aprovadas", _reais(ind_exec["volume_vendas_aprovadas"]))
            k2.metric("Receita YouShop", _reais(ind_exec["receita_youshop"]))
            k3.metric("Repasse Produtores", _reais(ind_exec["repasse_produtores"]))
            k4.metric("Comissão Creators", _reais(ind_exec["comissoes_creators"]))
            k5.metric("Estornos / Contestações", _reais(ind_exec["impacto_estornos"]))

            d_g1, d_g2 = st.columns(2)
            with d_g1:
                with st.container(border=True):
                    df_comp = pd.DataFrame([
                        {"Destino": "Repasse Produtores", "Valor": ind_exec["repasse_produtores"]},
                        {"Destino": "Comissão Creators", "Valor": ind_exec["comissoes_creators"]},
                        {"Destino": "Receita YouShop", "Valor": ind_exec["receita_youshop"]},
                    ])
                    fig_comp = px.pie(
                        df_comp,
                        names="Destino",
                        values="Valor",
                        hole=0.48,
                        title="Composição Executiva do Faturamento",
                        color_discrete_sequence=["#38BDF8", "#3B82F6", "#A3E635"],
                    )
                    st.plotly_chart(_aplicar_tema_grafico(fig_comp), width="stretch")

            with d_g2:
                with st.container(border=True):
                    if not df_fato_v.empty:
                        df_marca_dir = (
                            df_fato_v.groupby("marca_produtor", as_index=False)[["valor_bruto", "taxa_youshop"]]
                            .sum()
                            .rename(columns={"valor_bruto": "Faturamento (R$)", "taxa_youshop": "Receita YouShop (R$)"})
                        )
                        fig_m_dir = px.bar(
                            df_marca_dir,
                            x="marca_produtor",
                            y=["Faturamento (R$)", "Receita YouShop (R$)"],
                            barmode="group",
                            title="Faturamento e Receita YouShop por Marca",
                            labels={"marca_produtor": "Marca", "value": "Valor (R$)", "variable": "Indicador"},
                            color_discrete_sequence=["#38BDF8", "#A3E635"],
                        )
                        st.plotly_chart(_aplicar_tema_grafico(fig_m_dir), width="stretch")

            d_g3, d_g4 = st.columns(2)
            with d_g3:
                with st.container(border=True):
                    df_hist_dir = banco_central.carregar_tabela("fato_conciliacao_vendas")
                    if not df_hist_dir.empty:
                        df_mes_dir = (
                            df_hist_dir.groupby("data_competencia", as_index=False)[["valor_bruto", "taxa_youshop"]]
                            .sum()
                            .sort_values("data_competencia")
                            .rename(columns={"valor_bruto": "Vendas Aprovadas", "taxa_youshop": "Receita YouShop"})
                        )
                        fig_l_dir = px.line(
                            df_mes_dir,
                            x="data_competencia",
                            y=["Vendas Aprovadas", "Receita YouShop"],
                            markers=True,
                            title="Evolução Mensal: Vendas vs. Receita YouShop",
                            labels={"data_competencia": "Mês", "value": "Valor (R$)", "variable": "Série"},
                            color_discrete_sequence=["#38BDF8", "#A3E635"],
                        )
                        st.plotly_chart(_aplicar_tema_grafico(fig_l_dir), width="stretch")

            with d_g4:
                with st.container(border=True):
                    if not df_div_v.empty:
                        df_risco_dir = (
                            df_div_v.groupby("tipo_divergencia", as_index=False)["impacto_financeiro"]
                            .sum()
                            .sort_values("impacto_financeiro", ascending=True)
                        )
                        fig_r_dir = px.bar(
                            df_risco_dir,
                            x="impacto_financeiro",
                            y="tipo_divergencia",
                            orientation="h",
                            text="impacto_financeiro",
                            title="Impacto Financeiro das Divergências por Tipo",
                            labels={"impacto_financeiro": "Impacto (R$)", "tipo_divergencia": "Tipo"},
                            color_discrete_sequence=["#F87171"],
                        )
                        fig_r_dir.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
                        st.plotly_chart(_aplicar_tema_grafico(fig_r_dir), width="stretch")

            auditoria = st.session_state.get("auditoria_ia")
            if auditoria is None or competencia_global != "Todos os Meses":
                auditoria = auditar_divergencias(df_div_v, ind_exec, chave_api=chave_ativa)

            resumo_html = auditoria.get("briefing_diretoria", "").replace("\n\n", "<br><br>")
            st.markdown(
                f'<div class="ys-resumo"><strong>📋 Resumo Executivo da IA ({auditoria.get("modo_motor", "IA")})</strong><br><br>{resumo_html}</div>',
                unsafe_allow_html=True,
            )

            if not df_div_v.empty:
                for diag in auditoria.get("diagnosticos", []):
                    grav = str(diag.get("severidade", "Média")).lower()
                    cls_g = "ys-grav-alta" if "alta" in grav else ("ys-grav-baixa" if "baixa" in grav else "ys-grav-media")
                    st.markdown(
                        f'<div class="ys-auditoria {cls_g}">'
                        f'<strong>{diag.get("id_transacao")} — {diag.get("tipo_divergencia")}</strong> '
                        f'| <em>Gravidade: {diag.get("severidade")}</em> | <em>Responsável: {diag.get("setor_responsavel")}</em>'
                        f'<br><strong>Causa:</strong> {diag.get("causa_raiz")}'
                        f'<br><strong>Ação:</strong> {diag.get("acao_recomendada")}</div>',
                        unsafe_allow_html=True,
                    )

        # ----------------------------------------------------------------------
        # VISÃO FINANCEIRO (COMISSÕES, GRÁFICOS E COMPARAÇÕES)
        # ----------------------------------------------------------------------
        elif setor_dashboard == "Financeiro":
            df_saques_v = banco_central.carregar_tabela("fato_saques")
            if competencia_global != "Todos os Meses" and not df_saques_v.empty:
                df_saques_v = df_saques_v[df_saques_v["data_competencia"] == competencia_global]

            total_comissionamento = float(df_fato_v["comissao_creator"].sum()) if not df_fato_v.empty else 0.0
            total_repasse_prod = float(df_fato_v["repasse_produtor"].sum()) if not df_fato_v.empty else 0.0
            creators_apurados = int(df_fato_v["id_creator"].nunique()) if not df_fato_v.empty else 0
            qtd_liquidados = int((df_fato_v["status_banco"] == "Liquidado").sum()) if not df_fato_v.empty else 0
            qtd_agendados = int((df_fato_v["status_banco"] == "Agendado").sum()) if not df_fato_v.empty else 0
            total_saques = float(df_saques_v["valor_solicitado"].sum()) if not df_saques_v.empty else 0.0

            f1, f2, f3, f4, f5 = st.columns(5)
            f1.metric("Comissionamento Total", _reais(total_comissionamento))
            f2.metric("Creators Apurados", creators_apurados)
            f3.metric("Repasse a Produtores", _reais(total_repasse_prod))
            f4.metric("Pagamentos (Liq. / Ag.)", f"{qtd_liquidados} / {qtd_agendados}")
            f5.metric("Solicitações de Saque", _reais(total_saques), f"{len(df_saques_v)} pedido(s)")

            df_fato_hist = banco_central.carregar_tabela("fato_conciliacao_vendas")
            g_fin1, g_fin2 = st.columns(2)
            with g_fin1:
                with st.container(border=True):
                    if not df_fato_hist.empty:
                        df_evol = (
                            df_fato_hist.groupby("data_competencia", as_index=False)["comissao_creator"]
                            .sum()
                            .sort_values("data_competencia")
                        )
                        fig_evol = px.line(
                            df_evol,
                            x="data_competencia",
                            y="comissao_creator",
                            markers=True,
                            title="Evolução Mensal da Comissão dos Creators",
                            labels={"data_competencia": "Mês", "comissao_creator": "Comissões (R$)"},
                            color_discrete_sequence=["#38BDF8"],
                        )
                        fig_evol.update_traces(
                            line=dict(width=3),
                            marker=dict(size=10, color="#A3E635", line=dict(width=2, color="#FFFFFF")),
                        )
                        st.plotly_chart(_aplicar_tema_grafico(fig_evol), width="stretch")

            with g_fin2:
                with st.container(border=True):
                    if not df_fato_v.empty:
                        df_tier = (
                            df_fato_v.groupby("tier_creator", as_index=False)["comissao_creator"]
                            .sum()
                            .sort_values("comissao_creator", ascending=False)
                        )
                        fig_tier = px.bar(
                            df_tier,
                            x="tier_creator",
                            y="comissao_creator",
                            text="comissao_creator",
                            title="Comparação de Comissões por Nível de Creator",
                            labels={"tier_creator": "Nível", "comissao_creator": "Comissão (R$)"},
                            color="tier_creator",
                            color_discrete_sequence=["#38BDF8", "#3B82F6", "#A3E635"],
                        )
                        fig_tier.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
                        fig_tier.update_layout(showlegend=False)
                        st.plotly_chart(_aplicar_tema_grafico(fig_tier), width="stretch")

            g_fin3, g_fin4 = st.columns(2)
            with g_fin3:
                with st.container(border=True):
                    if not df_fato_v.empty:
                        df_comp_m = (
                            df_fato_v.groupby("marca_produtor", as_index=False)[["comissao_creator", "repasse_produtor"]]
                            .sum()
                            .rename(columns={"comissao_creator": "Comissão Creators", "repasse_produtor": "Repasse Produtores"})
                        )
                        fig_comp_m = px.bar(
                            df_comp_m,
                            x="marca_produtor",
                            y=["Comissão Creators", "Repasse Produtores"],
                            barmode="group",
                            title="Comparativo por Marca: Comissões vs. Repasse Produtor",
                            labels={"marca_produtor": "Marca", "value": "Valor (R$)", "variable": "Pagamento"},
                            color_discrete_sequence=["#A3E635", "#38BDF8"],
                        )
                        st.plotly_chart(_aplicar_tema_grafico(fig_comp_m), width="stretch")

            with g_fin4:
                with st.container(border=True):
                    if not df_fato_v.empty:
                        df_top_creat = (
                            df_fato_v.groupby(["handle_social", "tier_creator"], as_index=False)["comissao_creator"]
                            .sum()
                            .sort_values("comissao_creator", ascending=True)
                            .tail(8)
                        )
                        fig_top = px.bar(
                            df_top_creat,
                            x="comissao_creator",
                            y="handle_social",
                            orientation="h",
                            text="comissao_creator",
                            title="Top Creators por Comissionamento no Período",
                            labels={"handle_social": "Creator", "comissao_creator": "Comissão (R$)"},
                            color_discrete_sequence=["#38BDF8"],
                        )
                        fig_top.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
                        st.plotly_chart(_aplicar_tema_grafico(fig_top), width="stretch")

            if not df_saques_v.empty:
                with st.container(border=True):
                    st.markdown("#### 💸 Conciliação de Solicitações de Saque (Saldo vs. Solicitado)")
                    df_saq_exib = df_saques_v[
                        [
                            "id_saque", "data_solicitacao", "handle_social",
                            "saldo_disponivel", "valor_solicitado", "status_banco", "situacao_saque",
                        ]
                    ].rename(
                        columns={
                            "id_saque": "Código Saque",
                            "data_solicitacao": "Data",
                            "handle_social": "Creator",
                            "saldo_disponivel": "Saldo Disponível (R$)",
                            "valor_solicitado": "Valor Solicitado (R$)",
                            "status_banco": "Banco",
                            "situacao_saque": "Situação",
                        }
                    )
                    st.dataframe(df_saq_exib, width="stretch", hide_index=True)

            if not df_div_v.empty:
                div_fin = df_div_v[
                    df_div_v["tipo_divergencia"].str.contains("Comissão|Repasse|Centavos|Pós-Pagamento|Saque", case=False, na=False)
                ]
                if not div_fin.empty:
                    with st.container(border=True):
                        st.warning(
                            f"🚨 **Acionamento Automático da IA — Financeiro:** "
                            f"**{len(div_fin)}** lançamento(s) com divergência financeira "
                            f"(impacto de **{_reais(float(div_fin['impacto_financeiro'].sum()))}**) isolados para ação."
                        )
                        st.dataframe(
                            div_fin[
                                ["id_transacao", "tipo_divergencia", "valor_esperado", "valor_pago", "impacto_financeiro", "detalhe_tecnico"]
                            ].rename(
                                columns={
                                    "id_transacao": "Código Venda",
                                    "tipo_divergencia": "Tipo de Erro",
                                    "valor_esperado": "Esperado (R$)",
                                    "valor_pago": "Pago (R$)",
                                    "impacto_financeiro": "Impacto (R$)",
                                    "detalhe_tecnico": "Detalhe",
                                }
                            ),
                            width="stretch",
                            hide_index=True,
                        )

        # ----------------------------------------------------------------------
        # VISÃO CONTROLADORIA (INDICADORES DE DESEMPENHO + AUDITORIA)
        # ----------------------------------------------------------------------
        else:
            base_ctrl = df_resumo_v if not df_resumo_v.empty else pd.concat([df_fato_v, df_div_v], ignore_index=True)
            clientes_atendidos = int(base_ctrl["id_cliente_anonimo"].nunique()) if "id_cliente_anonimo" in base_ctrl.columns else int(len(base_ctrl))
            skus_vendidos = int(base_ctrl["cod_produto"].nunique()) if not base_ctrl.empty else 0
            venda_total_bruta = float(base_ctrl["valor_bruto"].sum()) if not base_ctrl.empty else 0.0
            qtd_pedidos = int(len(base_ctrl))
            qtd_aprov = int((base_ctrl["status_checkout"] == "Aprovada").sum()) if "status_checkout" in base_ctrl.columns else qtd_pedidos
            taxa_aprov = round((qtd_aprov / qtd_pedidos) * 100, 1) if qtd_pedidos > 0 else 0.0
            ticket_medio = round(venda_total_bruta / qtd_pedidos, 2) if qtd_pedidos > 0 else 0.0

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Clientes Atendidos", clientes_atendidos)
            c2.metric("SKUs Vendidos", skus_vendidos)
            c3.metric("Venda Total (Pedidos)", _reais(venda_total_bruta))
            c4.metric("Taxa de Aprovação", f"{taxa_aprov:.1f}%")
            c5.metric("Ticket Médio", _reais(ticket_medio))

            if not base_ctrl.empty:
                g_c1, g_c2 = st.columns(2)
                with g_c1:
                    with st.container(border=True):
                        df_status = (
                            base_ctrl.groupby("status_checkout", as_index=False)
                            .agg(pedidos=("id_transacao", "count"), valor=("valor_bruto", "sum"))
                        )
                        fig_st = px.bar(
                            df_status,
                            x="status_checkout",
                            y="valor",
                            text="pedidos",
                            title="Desempenho por Situação do Pedido",
                            labels={"status_checkout": "Situação", "valor": "Valor Total (R$)"},
                            color="status_checkout",
                            color_discrete_sequence=["#38BDF8", "#A3E635", "#94A3B8"],
                        )
                        fig_st.update_traces(texttemplate="%{text} pedidos", textposition="outside")
                        fig_st.update_layout(showlegend=False)
                        st.plotly_chart(_aplicar_tema_grafico(fig_st), width="stretch")

                with g_c2:
                    with st.container(border=True):
                        df_marca_c = (
                            base_ctrl.groupby("marca_produtor", as_index=False)
                            .agg(skus=("cod_produto", "nunique"), pedidos=("id_transacao", "count"), valor=("valor_bruto", "sum"))
                            .sort_values("valor", ascending=False)
                        )
                        fig_mc = px.bar(
                            df_marca_c,
                            x="marca_produtor",
                            y="valor",
                            text="skus",
                            title="Desempenho de Vendas e SKUs por Marca",
                            labels={"marca_produtor": "Marca", "valor": "Venda Total (R$)"},
                            color_discrete_sequence=["#38BDF8"],
                        )
                        fig_mc.update_traces(texttemplate="%{text} SKUs", textposition="outside")
                        st.plotly_chart(_aplicar_tema_grafico(fig_mc), width="stretch")

                g_c3, g_c4 = st.columns(2)
                with g_c3:
                    with st.container(border=True):
                        df_ctrl_hist = banco_central.carregar_tabela("fato_resumo_vendas")
                        if not df_ctrl_hist.empty:
                            df_mes_c = (
                                df_ctrl_hist.groupby("data_competencia", as_index=False)
                                .agg(pedidos=("id_transacao", "count"), clientes=("id_cliente_anonimo", "nunique"))
                                .sort_values("data_competencia")
                            )
                            fig_ev_c = px.line(
                                df_mes_c,
                                x="data_competencia",
                                y=["pedidos", "clientes"],
                                markers=True,
                                title="Evolução Mensal: Pedidos e Clientes Atendidos",
                                labels={"data_competencia": "Mês", "value": "Quantidade", "variable": "Indicador"},
                                color_discrete_sequence=["#38BDF8", "#A3E635"],
                            )
                            st.plotly_chart(_aplicar_tema_grafico(fig_ev_c), width="stretch")

                with g_c4:
                    with st.container(border=True):
                        if "tipo_produto" in base_ctrl.columns:
                            df_tp = base_ctrl.groupby("tipo_produto", as_index=False)["valor_bruto"].sum()
                            fig_tp = px.pie(
                                df_tp,
                                names="tipo_produto",
                                values="valor_bruto",
                                hole=0.48,
                                title="Participação por Tipo de Produto",
                                color_discrete_sequence=["#38BDF8", "#A3E635"],
                            )
                            st.plotly_chart(_aplicar_tema_grafico(fig_tp), width="stretch")

            df_prod_cat = banco_central.carregar_tabela("dim_produtos")
            itens_bloq = (
                df_prod_cat[df_prod_cat["status_produto"] == "Bloqueado"]
                if not df_prod_cat.empty and "status_produto" in df_prod_cat.columns
                else pd.DataFrame()
            )
            vendas_bloq = (
                df_div_v[df_div_v["tipo_divergencia"] == "Venda de Produto Bloqueado"]
                if not df_div_v.empty
                else pd.DataFrame()
            )

            with st.container(border=True):
                if not itens_bloq.empty or not vendas_bloq.empty:
                    cods_bloq = ", ".join(itens_bloq["cod_produto"].astype(str).tolist()) if not itens_bloq.empty else "-"
                    st.error(
                        f"🚨 **Acionamento Automático da IA — Item Bloqueado Separado:** "
                        f"**{len(itens_bloq)}** produto(s) bloqueado(s) no catálogo (`{cods_bloq}`) e "
                        f"**{len(vendas_bloq)}** venda(s) aprovada(s) indevidamente sobre item bloqueado foram isoladas na planilha de auditoria abaixo."
                    )

                st.markdown("#### 📋 Planilha de Auditoria (Vendas Isoladas pela IA)")
                if not df_div_v.empty:
                    df_aud_planilha = df_div_v[
                        [
                            "id_transacao", "data_pedido", "cod_produto", "nome_produto",
                            "marca_produtor", "status_produto", "id_creator", "valor_bruto",
                            "tipo_divergencia", "valor_esperado", "valor_pago",
                            "impacto_financeiro", "detalhe_tecnico",
                        ]
                    ].rename(
                        columns={
                            "id_transacao": "Código Venda",
                            "data_pedido": "Data",
                            "cod_produto": "SKU",
                            "nome_produto": "Produto",
                            "marca_produtor": "Marca",
                            "status_produto": "Situação Produto",
                            "id_creator": "Creator",
                            "valor_bruto": "Valor Venda (R$)",
                            "tipo_divergencia": "Tipo de Divergência",
                            "valor_esperado": "Esperado (R$)",
                            "valor_pago": "Pago (R$)",
                            "impacto_financeiro": "Impacto (R$)",
                            "detalhe_tecnico": "Motivo / Detalhe",
                        }
                    )
                    st.dataframe(df_aud_planilha, width="stretch", hide_index=True)
                    st.download_button(
                        "📥 Baixar Planilha de Auditoria",
                        data=df_aud_planilha.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
                        file_name="youshop_planilha_auditoria.csv",
                        mime="text/csv",
                    )
                else:
                    st.success("Nenhuma divergência encontrada para a planilha de auditoria neste período.")
