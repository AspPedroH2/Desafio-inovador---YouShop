# Central de Governança de Dados – YouShop

Plataforma interna de governança, normalização inteligente de dados (LGPD + IA), conciliação financeira e dashboards executivos para **Financeiro**, **Controladoria** e **Diretoria**.

## Arquitetura do Fluxo
1. **Proteção LGPD Local**: oculta irreversivelmente CPF, CNPJ, e-mail e nome civil antes de qualquer análise com IA.
2. **Leitura e Relatório com IA (`Gemini 2.5 Flash`)**: interpreta planilhas heterogêneas e gera frases diretas detalhando cada coluna transformada (`dProdutos`, `dCreators`, `fVendas`, `fRepasses`, `fEstornos`), com fallback determinístico automático offline caso nenhuma chave seja informada.
3. **Motor Determinístico + Base Central (SQLite)**: calcula Take Rate, comissões, repasses, saldo de saques e isola divergências em modelagem Dimensão/Fato.
4. **4 Abas Integradas**:
   - **Dados Normalizados & Relatório IA**
   - **Histórico por Setor** (`Financeiro`, `Controladoria`, `Diretoria`)
   - **Base Central** (fonte de dados para alimentar os painéis da Diretoria + consultas SQL prontas)
   - **Dashboards por Setor** (Diretoria, Financeiro com conciliação de saques, Controladoria com Planilha de Auditoria)

## Execução Local
```bash
pip install -r requirements.txt
streamlit run painel_youshop.py
```

## Publicação no Streamlit Community Cloud
- **Main file path**: `painel_youshop.py`
- *(Opcional)* Em **Settings → Secrets**, adicione `GEMINI_API_KEY = "sua-chave"` para ativar o `Gemini 2.5 Flash` por padrão.
