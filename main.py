import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime
from PIL import Image
from anthropic import Anthropic
import io
import re
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO, BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import numpy as np

# =============================================================================
# CONFIGURAÇÃO INICIAL
# =============================================================================
st.set_page_config(layout="wide", page_title="Gerador de Diagnóstico Estratégico")

# Inicialização do estado da sessão
chaves_sessao = [
    'relatorio_gerado',
    'dados_carregados',
    'nome_prospect',
    'concorrentes',
    'kw_principais',
    'dados_brutos',         # dict de categoria -> DataFrame bruto
    'documento_analise',
    'slides_gerados',
    'insights_seo',
    'insights_social',
    'insights_trafego',
    'insights_midia_paga',
    'insights_buzz',
    'insights_aio',
    'recomendacoes',
    'dados_extras_interpretados',
    'contexto_adicional',
    'documento_cliente'
]

for chave in chaves_sessao:
    if chave not in st.session_state:
        if chave == 'relatorio_gerado':
            st.session_state[chave] = False
        elif chave == 'dados_carregados':
            st.session_state[chave] = False
        elif chave in ['concorrentes', 'kw_principais']:
            st.session_state[chave] = []
        elif chave == 'dados_brutos':
            st.session_state[chave] = {}
        else:
            st.session_state[chave] = ""

st.title("Gerador de Diagnóstico Estratégico")
st.markdown("Transforme dados brutos em inteligencia de mercado. Cada canal e analisado por um especialista virtual dedicado.")
st.markdown("---")

# =============================================================================
# INICIALIZAÇÃO DOS MODELOS DE IA
# =============================================================================
gemini_api_key = os.getenv("GEM_API_KEY")
if not gemini_api_key and hasattr(st, 'secrets') and 'GEM_API_KEY' in st.secrets:
    gemini_api_key = st.secrets["GEM_API_KEY"]

if not gemini_api_key:
    st.error("Chave da API Gemini não encontrada. Configure GEM_API_KEY.")
    st.stop()
genai.configure(api_key=gemini_api_key)
modelo_gemini = genai.GenerativeModel("gemini-2.5-pro")

anthropic_api_key = None
if hasattr(st, 'secrets') and 'ANTH_KEY' in st.secrets:
    anthropic_api_key = st.secrets["ANTH_KEY"]
elif os.getenv("ANTH_KEY"):
    anthropic_api_key = os.getenv("ANTH_KEY")

cliente_anthropic = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None

SISTEMA_BASE = """Voce e um consultor senior de inteligencia de mercado com 30 anos de experiencia em marketing digital
estrategico, atuando em uma agencia de marketing de alta performance (Macfor). Seu papel e transformar dados brutos
em inteligencia estrategica de nivel McKinsey/Bain que impressione clientes C-level e gere decisoes de negocio.

Voce domina os principais frameworks estrategicos e deve aplica-los quando relevante:
- PORTER'S FIVE FORCES para analise competitiva digital
- PESTEL adaptado ao ambiente digital (tecnologia, regulacao de dados, comportamento do consumidor)
- RACE Framework (Reach, Act, Convert, Engage) para funil digital
- PIE Framework (Potential, Importance, Ease) para priorizacao de otimizacoes
- ICE Score (Impact, Confidence, Ease) para ranking de oportunidades
- Modelo See-Think-Do-Care do Google para mapeamento de intencao
- Flywheel Model (HubSpot) para ecossistema de crescimento
- Jobs-To-Be-Done para analise de intencao de busca
- AARRR (Pirate Metrics) para diagnostico de funil

REFERENCIAS DE MERCADO QUE VOCE CONHECE PROFUNDAMENTE:
- Benchmarks SEMrush, Ahrefs, Moz, SimilarWeb para metricas de SEO e trafego
- Dados do Hootsuite/We Are Social Digital Report para benchmarks de social media
- Google Search Quality Rater Guidelines e E-E-A-T
- Core Web Vitals e Page Experience signals
- Estudos da Backlinko, Search Engine Journal, HubSpot Research para benchmarks de CTR por posicao
- CTR medio por posicao no Google: #1=31.7%, #2=24.7%, #3=18.7%, #4=13.6%, #5=9.5% (Backlinko 2024)
- Engagement rate benchmarks: Facebook 0.06-0.15%, Instagram 1.0-3.0%, LinkedIn 2.0-4.0%, TikTok 3.0-9.0%
- Custo medio por lead por industria (HubSpot Research)
- Conversion rate benchmarks por industria (Unbounce, WordStream)
- Domain Authority: 0-20 baixo, 21-40 em desenvolvimento, 41-60 intermediario, 61-80 forte, 80+ dominante

DIRETRIZES FUNDAMENTAIS:
- NUNCA apresente dados brutos sem contexto ou interpretacao. Cada numero = "so what?" + impacto no negocio
- Sempre conecte dados a implicacoes financeiras: receita, market share, custo de aquisicao, LTV
- CONTEXTUALIZE cada metrica contra benchmarks do setor e dos concorrentes
- Identifique padroes, tendencias, anomalias e CORRELACOES entre metricas
- Priorize insights acionaveis sobre descricoes estatisticas
- CALCULE gaps quantificados: "O prospect perde X visitas/mes (R$Y em traffic cost equivalent)"
- Use analise de cenarios: melhor caso / caso base / pior caso quando relevante
- Identifique QUICK WINS (alto impacto, baixo esforco) vs PROJETOS ESTRATEGICOS (alto impacto, alto esforco)
- Adote tom consultivo e confiante, como senior partner apresentando para o board
- Quando dados forem limitados, use conhecimento de mercado para contextualizar -- mas SINALIZE claramente
  o que e dado real vs benchmark de referencia
- NUNCA use emojis
- Portugues brasileiro profissional
- Quantifique impacto de CADA recomendacao (ex: "potencial de +X% em trafego qualificado = ~Y leads adicionais/mes")
- Aplique o conceito de "Insight Pyramid": Dado > Informacao > Insight > Recomendacao > Impacto projetado
"""

ESPECIALISTAS = {
    'seo': """PERFIL: Head de SEO com 30 anos de experiencia, certificacoes Google, ex-diretor de SEO de agencias tier-1.
Trabalhou com enterprise SEO para marcas Fortune 500.

DOMINIOS DE EXPERTISE:
- SEO Tecnico: Core Web Vitals (LCP<2.5s, FID<100ms, CLS<0.1), crawl budget, indexacao, JS rendering, hreflang
- Content Strategy: Topic clusters, content hubs, E-E-A-T optimization, semantic SEO, entity-based optimization
- Link Building: Digital PR, broken link building, skyscraper technique, analise de perfil de backlinks (toxic score, DR distribution)
- Analise Competitiva: Share of voice organico, keyword gap analysis, content gap, SERP feature ownership
- Algoritmos Google: Helpful Content Update, Link Spam Update, Core Updates, Page Experience, BERT/MUM para intencao

FRAMEWORKS QUE APLICA:
- Modelo de valor de keyword: Volume x CTR da posicao x Taxa de conversao do setor x Ticket medio = Valor/mes
- SEO ROI: (Trafego incremental x Conv. Rate x Ticket medio) - Investimento em SEO
- Keyword Difficulty vs Business Value Matrix para priorizacao
- Technical SEO Audit Framework (Google Lighthouse + crawl analysis + log file analysis)
- Content Decay Analysis: identificar conteudo que esta perdendo rankings e precisa de refresh

BENCHMARKS DE REFERENCIA:
- CTR por posicao Google (Backlinko 2024): #1=31.7%, #2=24.7%, #3=18.7%
- DA medio por industria: SaaS 40-60, E-commerce 30-50, Finance 50-70
- Organic traffic share saudavel: >40% do trafego total
- Backlink growth rate saudavel: 5-15% ao mes para sites em crescimento""",

    'social': """PERFIL: Head de Social Media & Content Strategy com 30 anos de experiencia em grandes marcas B2B e B2C.
Ex-VP de Social Media de holding multinacional. Palestrante em SXSW, Web Summit e RD Summit.

DOMINIOS DE EXPERTISE:
- Metricas que importam: Engagement Rate, Share of Voice, Sentiment Score, Brand Mention Velocity, Audience Growth Rate
- Content Intelligence: analise de performance por formato, tema, horario, tom; content scoring; creative testing
- Community Management: Net Promoter Score social, response rate, response time, community health score
- Influencer Marketing: CPE (custo por engajamento), EMV (earned media value), authenticity score
- Social Commerce: conversion rate por plataforma, shoppable content performance, social proof metrics
- Algoritmos de cada plataforma: EdgeRank (FB), Instagram Algorithm signals, LinkedIn SSI, TikTok FYP

FRAMEWORKS QUE APLICA:
- Social Media Maturity Model: nivel 1 (presenca) > 2 (engajamento) > 3 (comunidade) > 4 (advocacy) > 5 (revenue)
- Content Performance Matrix: alcance x engajamento para classificar posts em Stars, Cash Cows, Question Marks, Dogs
- Share of Voice = Mencoes da marca / Total de mencoes do setor x 100
- Engagement Rate Real = (Curtidas + Comentarios + Compartilhamentos + Saves) / Alcance x 100
- Brand Health Index: awareness + consideration + preference + advocacy

BENCHMARKS 2024-2025:
- Facebook: ER medio 0.06-0.15%, alcance organico 2-5% da base, video watch time >3s = bom
- Instagram: ER medio 1.0-3.0%, Reels alcance 2-3x feed, Stories completion rate >70% = bom
- TikTok: ER medio 3.0-9.0%, watch time >50% = viral potential, comment rate >1% = alto engajamento
- LinkedIn: ER medio 2.0-4.0%, SSI >70 = excelente, document posts tem 3x mais alcance
- Frequencia ideal: FB 1-2/dia, IG 3-7/semana, TT 1-3/dia, LI 2-5/semana""",

    'trafego': """PERFIL: Head de Growth & Analytics com 30 anos de experiencia em atribuicao multicanal, CRO e growth hacking.
Ex-VP de Growth de scale-up unicornio. Certificado Google Analytics, Adobe Analytics.

DOMINIOS DE EXPERTISE:
- Atribuicao Multicanal: last-click, first-click, linear, time-decay, position-based, data-driven attribution
- Analise de Funil: TOFU/MOFU/BOFU conversion rates, drop-off analysis, funnel velocity
- CRO (Conversion Rate Optimization): A/B testing, heatmaps, session recordings, form analytics
- Comportamento do Usuario: bounce rate, time on page, pages per session, scroll depth, micro-conversions
- Growth Loops: viral loops, content loops, paid loops, sales loops - identificar qual motor funciona

FRAMEWORKS QUE APLICA:
- AARRR (Pirate Metrics): Acquisition > Activation > Retention > Revenue > Referral
- North Star Metric Framework: identificar a metrica que melhor correlaciona com valor entregue ao cliente
- Growth Accounting: new users + resurrected users - churned users = net growth
- Channel-Market Fit: avaliar se os canais de aquisicao sao adequados para o ICP
- Traffic Quality Score: (conversion rate x avg session duration x pages/session) / bounce rate

BENCHMARKS DE REFERENCIA:
- Mix saudavel de trafego: organico >30%, direto 15-25%, social 5-15%, referral 5-10%, pago <30%
- Bounce rate por industria: B2B 25-55%, E-commerce 20-45%, Content 40-65%, Landing pages 60-90%
- Conversion rate medio: B2B 2-5%, E-commerce 1-4%, SaaS free trial 3-8%
- Dependencia de canal unico >50% = risco estrategico critico""",

    'midia_paga': """PERFIL: Head de Performance Media com 30 anos de experiencia, gestao de budgets de 8 digitos/mes.
Ex-diretor de midia de agencia top-5 do Brasil. Certificado Google Ads, Meta Blueprint, LinkedIn Marketing.

DOMINIOS DE EXPERTISE:
- Google Ads: Search, Display, Shopping, Performance Max, YouTube Ads, bidding strategies (tROAS, tCPA)
- Meta Ads: estrutura de campanha CBO/ABO, Advantage+, Catalog Sales, Lead Ads, Conversions API
- LinkedIn Ads: Sponsored Content, Message Ads, Conversation Ads, ABM targeting
- Programatica: DSPs, DMPs, header bidding, viewability, brand safety, fraud detection
- Analise de Investimento: ROAS, CAC, LTV/CAC ratio, incrementality testing, media mix modeling

FRAMEWORKS QUE APLICA:
- Media Mix Optimization: alocacao otima de budget por canal baseada em diminishing returns
- Full-Funnel Media: awareness (CPM) > consideration (CPC/CPV) > conversion (CPA) > retention (CPLC)
- Incrementality Framework: quanto da conversao e REALMENTE incremental vs canibaliza organico
- Budget Allocation: Rule of 70/20/10 (proven/testing/experimental)
- Competitive Share of Voice vs Share of Market correlation (Les Binet & Peter Field)

BENCHMARKS 2024-2025:
- Google Ads CPC medio Brasil: Search R$1.50-4.00, Display R$0.30-0.80
- Meta Ads CPM medio Brasil: R$15-40, CPC R$0.50-2.00
- LinkedIn Ads CPC medio: R$8-25, CPM R$80-200
- ROAS minimo saudavel: 3:1 para e-commerce, 5:1 para high-ticket
- LTV/CAC ratio ideal: >3:1, abaixo de 1:1 = insustentavel""",

    'buzz': """PERFIL: Head de Content Intelligence & Digital PR com 30 anos de experiencia em analise de tendencias,
comportamento do consumidor digital e estrategias de conteudo data-driven. Ex-director de content strategy
de publisher digital top-3 do Brasil. Palestrante em Content Marketing World.

DOMINIOS DE EXPERTISE:
- Search Intent Analysis: informational, navigational, commercial investigation, transactional (modelo Semrush)
- Trend Detection: Google Trends, social listening, emerging topics, cultural moments, micro-trends
- Content Gap Analysis: oportunidades de conteudo de alto valor nao exploradas pelo mercado
- Digital PR: newsjacking, data-driven storytelling, expert commentary, original research
- Consumer Journey Mapping: touchpoints, micro-moments (Google), Jobs-To-Be-Done
- Analise de SERP Features: featured snippets, PAA (People Also Ask), knowledge panels, video carousels

FRAMEWORKS QUE APLICA:
- Content-Market Fit: conteudo certo x audiencia certa x momento certo x formato certo
- Search Demand Curve: head terms (alto volume, alta competicao) > mid-tail > long-tail (baixo volume, alta conversao)
- Content Scoring Model: relevancia x autoridade x freshness x engagement x conversao
- Topic Authority Framework: cluster model para construir autoridade tematica progressiva
- PESO Model (Paid, Earned, Shared, Owned) para estrategia de distribuicao de conteudo

REFERENCIAS DE ANALISE:
- Consumidor brasileiro: 84% pesquisa online antes de comprar (Google/Offerwise)
- Zero-click searches: ~65% das buscas no Google nao geram clique (SparkToro/Datos)
- PAA aparece em ~40% das buscas informacionais - oportunidade de captura
- Videos representam 82% do trafego de internet (Cisco) - priorizacao de video content""",

    'aio': """PERFIL: Especialista lider em AI Search Optimization e GEO (Generative Engine Optimization) com experiencia
pioneira desde o lancamento do ChatGPT em 2022. Pesquisador ativo em como LLMs processam e citam informacoes.
Consultor de marcas Fortune 500 em estrategia de presenca em AI Search.

DOMINIOS DE EXPERTISE:
- AI Overview (Google SGE): como o Google seleciona fontes para AI-generated summaries
- LLM Citation Patterns: como ChatGPT, Gemini, Perplexity e Claude citam e recomendam marcas/produtos
- GEO (Generative Engine Optimization): otimizacao de conteudo para ser citado por IAs generativas
- Knowledge Graph Optimization: entidades, atributos, relacoes que alimentam respostas de IA
- Structured Data Strategy: schema markup que facilita compreensao por LLMs
- Brand Mention Monitoring em respostas de IA: sentiment, accuracy, frequency, prominence

FRAMEWORKS QUE APLICA:
- GEO Readiness Score: authority + structured data + E-E-A-T signals + brand mentions + content quality
- AI Visibility Funnel: indexacao > compreensao > citacao > recomendacao > preferencia
- LLMO (Large Language Model Optimization): otimizar para ser a resposta, nao apenas um resultado
- Source Authority Model: como LLMs avaliam credibilidade (domain authority, expert authorship, citations, freshness)

DADOS E TENDENCIAS:
- AI Overview aparece em ~15-30% das buscas no Google (variavel por categoria)
- Impacto no CTR organico: -20 a -40% para queries informacionais com AI Overview
- Perplexity: 100M+ queries/mes, tendencia de crescimento exponencial
- 40% dos consumidores Gen-Z preferem buscar no TikTok/ChatGPT vs Google (Adobe Survey)
- Fatores de citacao em LLMs: autoridade do dominio (35%), qualidade do conteudo (30%), mencoes externas (20%), dados estruturados (15%)
- Conteudo com schema markup tem 2-3x mais chances de ser citado em AI Overview""",

    'estrategico': """PERFIL: CMO fracionario / Diretor de Estrategia Digital com 30 anos de experiencia e visao 360.
Ex-CMO de empresas listadas na B3. Conselheiro de boards. MBA por Wharton, especializado em digital transformation.

DOMINIOS DE EXPERTISE:
- Estrategia Digital Integrada: alinhamento de canais, budget allocation, go-to-market digital
- Business Intelligence: traducao de metricas de marketing em KPIs de negocio (receita, margem, market share)
- Digital Maturity Assessment: avaliacao de maturidade digital vs mercado e melhores praticas
- Stakeholder Communication: traduzir complexidade tecnica em narrativa executiva impactante
- Scenario Planning: modelagem de cenarios otimista/base/pessimista com impacto financeiro

FRAMEWORKS QUE APLICA:
- Balanced Scorecard Digital: financeiro, cliente, processos internos, aprendizado e crescimento
- Matriz Esforco x Impacto para priorizacao (quadrantes: Quick Wins, Projetos Estrategicos, Fill-ins, Thankless Tasks)
- OKR Framework para estruturar objetivos e key results mensuráveis
- MECE (Mutually Exclusive, Collectively Exhaustive) para estruturacao de diagnostico
- McKinsey 3 Horizons para balancear curto, medio e longo prazo
- Digital Maturity Model: nivel 1 (basico) > 2 (gerenciado) > 3 (definido) > 4 (quantificado) > 5 (otimizado)

ESTILO DE ENTREGA:
- Abre com "the headline" - a descoberta mais impactante
- Cada insight segue: dado > implicacao > recomendacao > impacto projetado
- Fecha com roadmap priorizado e business case simplificado
- Linguagem de boardroom: confiante, baseada em evidencias, orientada a decisao"""
}

def gerar_texto(prompt, sistema=SISTEMA_BASE, especialista=None):
    """Gera texto usando Anthropic Claude ou, como fallback, Gemini."""
    sistema_final = sistema
    if especialista and especialista in ESPECIALISTAS:
        sistema_final = f"{SISTEMA_BASE}\n\nPERFIL DO ESPECIALISTA:\n{ESPECIALISTAS[especialista]}"

    # Injeta contexto adicional do usuario se disponivel
    ctx = st.session_state.get('contexto_adicional', '')
    if ctx:
        sistema_final += f"\n\nCONTEXTO ADICIONAL FORNECIDO PELO ANALISTA DA AGENCIA (use para enriquecer e direcionar sua analise):\n{ctx}"

    if cliente_anthropic:
        try:
            response = cliente_anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8096,
                system=sistema_final,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception:
            return gerar_texto_gemini(prompt, sistema_final)
    else:
        return gerar_texto_gemini(prompt, sistema_final)

def gerar_texto_gemini(prompt, sistema):
    """Fallback para gerar texto usando Gemini."""
    try:
        response = modelo_gemini.generate_content(f"{sistema}\n\n{prompt}")
        return response.text
    except Exception as e:
        return f"Erro ao gerar texto com Gemini: {str(e)}"

# =============================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# =============================================================================
def safe_float(val):
    try:
        return float(str(val).replace(',', '.').replace('R$', '').replace(' ', ''))
    except (ValueError, TypeError):
        return 0.0

def safe_int(val):
    try:
        return int(float(str(val).replace(',', '.').replace('.', '')))
    except (ValueError, TypeError):
        return 0

def carregar_csv(uploaded_file, separadores=[',', ';', '\t']):
    """Carrega um CSV para um DataFrame, tentando diferentes separadores e encodings."""
    if uploaded_file is not None:
        encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        for enc in encodings:
            for sep in separadores:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep=sep, encoding=enc, on_bad_lines='skip')
                    if df.shape[1] > 1:
                        # Limpa nomes de colunas
                        df.columns = [str(c).strip() for c in df.columns]
                        return df
                except:
                    continue

        # Ultima tentativa: ler como coluna unica e tentar auto-detect
        try:
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8', errors='replace')
            df = pd.read_csv(StringIO(content), sep=None, engine='python', on_bad_lines='skip')
            if not df.empty:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except:
            pass
    return None

def carregar_e_combinar_csvs(arquivos):
    """Carrega multiplos CSVs e combina em um unico DataFrame."""
    if not arquivos:
        return None
    dfs = []
    for arq in arquivos:
        df = carregar_csv(arq)
        if df is not None and not df.empty:
            dfs.append(df)
    if not dfs:
        return None
    if len(dfs) == 1:
        return dfs[0]
    # Tenta concatenar; se colunas diferentes, concatena com outer join
    try:
        return pd.concat(dfs, ignore_index=True, sort=False)
    except Exception:
        return dfs[0]

def df_para_contexto(df, max_linhas=50):
    """Converte DataFrame em texto rico para enviar à IA, maximizando dados reais."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return ""
    if isinstance(df, dict):
        if not df:
            return ""
        try:
            df = pd.DataFrame(df)
        except Exception:
            return str(df)

    info = []
    info.append(f"Dimensoes: {df.shape[0]} linhas x {df.shape[1]} colunas")
    info.append(f"Colunas: {list(df.columns)}")

    # Estatísticas numéricas
    numericas = df.select_dtypes(include=['number'])
    if not numericas.empty:
        info.append(f"\nEstatisticas numericas:\n{numericas.describe().to_string()}")

    # Dados completos (até max_linhas)
    n = min(len(df), max_linhas)
    info.append(f"\nDados ({n} de {len(df)} linhas):\n{df.head(n).to_string()}")

    # Se tem mais linhas, mostra as últimas também para ver tendências
    if len(df) > max_linhas:
        info.append(f"\nUltimas 10 linhas:\n{df.tail(10).to_string()}")

    return "\n".join(info)


def interpretar_csv_com_ia(df, contexto_tipo):
    """Usa IA para interpretar a estrutura de um CSV arbitrário e extrair dados relevantes."""
    if df is None or df.empty:
        return ""

    prompt = f"""Analise a estrutura deste CSV e extraia os dados mais relevantes para uma análise de {contexto_tipo}.

{df_para_contexto(df, 30)}

INSTRUÇÕES:
1. Identifique o que cada coluna representa, mesmo que os nomes estejam abreviados ou em outro idioma
2. Extraia um resumo estruturado dos dados mais relevantes para análise de {contexto_tipo}
3. Identifique quais linhas/colunas representam o prospect vs concorrentes (se aplicável)
4. Destaque valores notáveis, outliers, tendências visíveis e comparativos entre players
5. Se houver dados temporais, identifique a direção das tendências (crescimento/queda)
6. Apresente os dados já interpretados, NÃO como tabela bruta mas como observações estruturadas

Formate a saída como um briefing analítico organizado por temas."""

    return gerar_texto(prompt, especialista=None)

# =============================================================================
# FUNÇÕES DE PROCESSAMENTO DE DADOS ESPECÍFICOS
# =============================================================================
def processar_dados_prospect_concorrentes(df):
    """Extrai nomes do prospect e concorrentes do CSV de cadastro."""
    prospect = ""
    concorrentes = []
    
    # Procura por linhas com "Prospect" ou "Nome"
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        if 'Prospect' in row_str and not prospect:
            # Tenta extrair o nome do prospect
            for val in row.values:
                if pd.notna(val) and 'Prospect' not in str(val) and len(str(val)) > 3:
                    prospect = str(val).strip()
                    break
        elif 'Concorrente' in row_str:
            for val in row.values:
                if pd.notna(val) and 'Concorrente' not in str(val) and len(str(val)) > 3 and 'Observações' not in str(val):
                    concorrentes.append(str(val).strip())
                    break
    
    # Se não encontrou, usa valores padrão
    if not prospect:
        prospect = "Prospect"
    if not concorrentes:
        concorrentes = ["Concorrente 1", "Concorrente 2", "Concorrente 3", "Concorrente 4"]
    
    return prospect, concorrentes[:4]  # Limita a 4 concorrentes

def processar_kw_principais(df):
    """Extrai as principais palavras-chave."""
    kws = []
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        if 'KW' in row_str or 'Keyword' in row_str:
            for val in row.values:
                if pd.notna(val) and 'KW' not in str(val) and 'Keyword' not in str(val) and len(str(val)) > 2:
                    kws.append(str(val).strip())
                    if len(kws) >= 10:
                        break
    return kws[:10]

def processar_seo_historico(df):
    """Processa dados históricos de SEO (rank, tráfego, keywords)."""
    # Identifica a estrutura: linhas com anos/meses, domínios, ranks, etc.
    dados = []
    
    # Procura por colunas que parecem datas (YYYY|MM)
    colunas_data = []
    for col in df.columns:
        if isinstance(col, str) and ('|' in col or re.match(r'\d{4}', col)):
            colunas_data.append(col)
    
    if colunas_data:
        # Encontra linhas com domínios
        for idx, row in df.iterrows():
            dominio = None
            for val in row.values[:2]:  # Primeiras colunas podem ter o domínio
                if pd.notna(val) and isinstance(val, str) and ('www.' in val or '.com' in val):
                    dominio = val
                    break
            
            if dominio:
                dados_row = {'dominio': dominio}
                for col in colunas_data:
                    if col in df.columns and idx < len(df):
                        dados_row[col] = row[col]
                dados.append(dados_row)
    
    return pd.DataFrame(dados) if dados else df

def processar_kw_ranking(df):
    """Processa dados de ranking de palavras-chave."""
    # Estrutura típica: Domain, Keyword, Position, Search volume, etc.
    colunas_esperadas = ['Domain', 'Keyword', 'Position', 'Search volume', 'URL']
    df_result = pd.DataFrame()
    
    for col in colunas_esperadas:
        for df_col in df.columns:
            if col.lower() in str(df_col).lower():
                df_result[col] = df[df_col]
                break
    
    return df_result if not df_result.empty else df

def processar_analise_kw(df):
    """Processa análise de palavras-chave com volumes e CPC."""
    # Procura por colunas: Keyword, Search volume, CPC, Competition
    colunas_mapeadas = {}
    mapeamento = {
        'keyword': 'Keyword',
        'search volume': 'Search volume',
        'cpc': 'CPC',
        'competition': 'Competition',
        'number of results': 'Number of results'
    }
    
    for termo, nome in mapeamento.items():
        for col in df.columns:
            if termo.lower() in str(col).lower():
                colunas_mapeadas[nome] = col
                break
    
    if colunas_mapeadas:
        df_result = df[list(colunas_mapeadas.values())].copy()
        df_result.columns = list(colunas_mapeadas.keys())
        return df_result
    
    return df

def processar_social_facebook(df):
    """Processa dados de engajamento do Facebook."""
    dados = {}
    
    # Procura por linhas com o nome do prospect
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        if 'Prospect' in row_str or 'plumatex' in row_str.lower():
            # Extrai métricas
            for j, val in enumerate(row.values):
                if pd.notna(val) and isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '').replace(',', '').isdigit()):
                    if 'likes' in str(row.index[j]).lower() or 'followers' in str(row.index[j]).lower():
                        dados['likes'] = safe_int(val)
                    elif 'engagement' in str(row.index[j]).lower():
                        dados['engagement'] = safe_float(val)
                    elif 'posts' in str(row.index[j]).lower():
                        dados['posts'] = safe_int(val)
    
    return dados

def processar_social_instagram(df):
    """Processa dados do Instagram."""
    dados = {}
    
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        if 'Prospect' in row_str or 'plumatex' in row_str.lower():
            for j, val in enumerate(row.values):
                if pd.notna(val):
                    if 'followers' in str(row.index[j]).lower():
                        dados['followers'] = safe_int(val)
                    elif 'engagement' in str(row.index[j]).lower():
                        dados['engagement'] = safe_float(val)
    
    return dados

def processar_autoridade(df):
    """Processa dados de autoridade de domínio."""
    dados = {}
    
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        if 'plumatex' in row_str.lower() or (idx == 0 and 'Authority' in str(row.values)):
            for j, val in enumerate(row.values):
                if pd.notna(val) and isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '').isdigit()):
                    col_name = str(row.index[j]) if j < len(row.index) else f"col{j}"
                    if 'authority' in col_name.lower() or 'score' in col_name.lower():
                        dados['authority_score'] = safe_int(val)
                    elif 'domains' in col_name.lower():
                        dados['domains'] = safe_int(val)
                    elif 'follow' in col_name.lower():
                        dados['follow_links'] = safe_int(val)
    
    return dados

# =============================================================================
# FUNCOES DE GERACAO DE INSIGHTS COM IA
# =============================================================================

REGRAS_ANALISE = """
=== REGRAS INEGOCIAVEIS DE ANALISE ===

1. USE EXCLUSIVAMENTE OS DADOS REAIS FORNECIDOS. Cada numero nos CSVs e real e foi extraido de ferramentas
   profissionais (SEMrush, Ahrefs, SimilarWeb, etc). Cite valores exatos. Nao arredonde sem necessidade.

2. NUNCA INVENTE DADOS. Se uma metrica nao esta nos CSVs, diga "dado nao disponivel nos dados fornecidos"
   e siga para o proximo ponto. NAO ESTIME, NAO PROJETE, NAO CRIE benchmarks fictícios.

3. CRUZAMENTO OBRIGATORIO. Compare metricas entre players nos MESMOS periodos.
   Calcule diferencas percentuais, gaps absolutos, taxas de variacao.

4. ZERO GENERALIDADES. Nao escreva "o trafego e baixo". Escreva:
   "O trafego organico de [prospect] (X visitas/mes) representa Y% do lider [concorrente] (Z visitas/mes),
   um gap de W visitas qualificadas perdidas mensalmente."

5. CADA OBSERVACAO = DADO REAL + "E DAI?" (impacto no negocio) + ACAO RECOMENDADA.
   Incorpore os insights naturalmente na analise, nao como secao separada.

6. TENDENCIAS TEMPORAIS: Se houver dados de multiplos periodos, calcule e destaque:
   - Taxas de crescimento/queda mes a mes ou ano a ano
   - Pontos de inflexao (mudancas bruscas) e possiveis causas
   - Aceleracao ou desaceleracao de tendencias

7. QUANDO DADOS FOREM LIMITADOS para determinada metrica, aprofunde-se MAIS nos dados que ESTAO disponiveis.
   Nunca compense falta de dados com generalizacoes.
"""

def gerar_insights_seo(dados_brutos_texto, kw_principais, prospect, concorrentes):
    """Gera analise de SEO com dados reais."""

    conc_str = ', '.join(concorrentes) if concorrentes else 'identificar nos dados'
    kw_str = ', '.join(kw_principais) if kw_principais else 'extrair dos dados'

    prompt = f"""{REGRAS_ANALISE}

PROSPECT: {prospect}
CONCORRENTES: {conc_str}
PALAVRAS-CHAVE DO SEGMENTO: {kw_str}

DADOS REAIS EXTRAIDOS DOS CSVs:
{dados_brutos_texto}

Produza uma analise estrategica de SEO de nivel senior consultant. Use os frameworks e benchmarks abaixo
para contextualizar CADA dado encontrado nos CSVs.

## 1. SCORECARD COMPETITIVO DE SEO
Monte uma tabela comparativa com VALORES REAIS de cada player encontrado nos dados:
| Metrica | {prospect} | Concorrente 1 | ... | Lider | Gap vs Lider |
Metricas: Organic Traffic, Traffic Cost, Organic Keywords, Authority Score, Backlinks, Referring Domains.
Para CADA metrica, calcule:
- Gap absoluto e percentual vs lider do mercado
- Traffic Cost Equivalent: valor monetario do trafego organico (trafego x CPC medio do setor)
- Share of Voice organico: % das keywords do setor onde cada player aparece no top 10

## 2. INTELIGENCIA DE KEYWORDS (ANALISE PROFUNDA)
Analise CADA keyword real dos dados aplicando o modelo See-Think-Do-Care:
- SEE (awareness): keywords informacionais de topo de funil - volume alto, CPC baixo
- THINK (consideration): keywords de comparacao, "melhor", "vs" - volume medio, CPC medio
- DO (conversion): keywords transacionais, "comprar", "preco", "onde" - volume baixo, CPC alto
- CARE (retention): keywords de suporte, "como usar", "assistencia"

Para cada keyword calcule o VALOR ECONOMICO:
  Valor/mes = Volume x CTR da posicao atual (Backlinko: #1=31.7%, #2=24.7%, #3=18.7%, #5=9.5%, #10=3.1%)
              x Taxa de conversao media do setor x Ticket medio estimado

Identifique:
- Keyword Gaps criticos: termos de alto valor transacional onde {prospect} NAO aparece no top 20
- Quick Wins: keywords nas posicoes 11-20 que podem subir ao top 10 com otimizacao on-page
- Keywords Canibalizadas: multiplas URLs competindo pela mesma keyword
- Oportunidades Long-tail: clusters de keywords de cauda longa com intencao de compra clara

## 3. ANALISE DE AUTORIDADE E LINK PROFILE
Usando os dados de Authority Score, backlinks e referring domains:
- Classifique cada player: 0-20 (iniciante), 21-40 (em desenvolvimento), 41-60 (intermediario), 61-80 (forte), 80+ (dominante)
- Ratio backlinks/referring domains: alto ratio = poucos sites com muitos links (risco), baixo = perfil diversificado (saudavel)
- Velocidade de aquisicao de links: crescimento mes a mes dos referring domains
- Estimativa de investimento necessario em link building para fechar o gap (baseado no custo medio de R$500-2000 por link de qualidade)

## 4. EVOLUCAO TEMPORAL E TENDENCIAS
Se houver dados de multiplos periodos:
- CAGR (Compound Annual Growth Rate) de trafego organico para cada player
- Pontos de inflexao e correlacao com Google Core Updates conhecidos (Nov 2024, Mar 2024, Oct 2023, etc.)
- Analise de momentum: quem esta acelerando vs desacelerando
- Projecao de cenarios: otimista (best practices implementadas) / base (status quo) / pessimista (concorrentes aceleram)

## 5. OPORTUNIDADES DE SERP FEATURES
Com base nas keywords:
- Featured Snippets: quais keywords tem snippet e quem domina
- People Also Ask: perguntas relacionadas que podem gerar trafego incremental
- Local Pack: se relevante para o segmento
- Video Carousel: oportunidades de video SEO

## 6. CONCLUSAO ESTRATEGICA (FORMATO EXECUTIVO)
**Headline**: A descoberta mais impactante em uma frase (com numeros)
**Diagnostico**: Nivel de maturidade SEO de {prospect} (escala 1-5) com justificativa baseada nos dados
**Top 3 Gaps Criticos**: Cada um com valor economico estimado do que esta sendo perdido
**Roadmap**:
- Quick Wins (0-30 dias): acoes de otimizacao on-page, technical fixes -- resultado esperado: +X% trafego
- Projetos Taticos (1-3 meses): content gaps, link building inicial -- resultado esperado: +Y% keywords top 10
- Estrategia de Longo Prazo (3-12 meses): topic authority, digital PR -- resultado esperado: +Z% share of voice
**Business Case**: Investimento estimado vs retorno projetado em trafego, leads e receita"""

    return gerar_texto(prompt, especialista='seo')


def gerar_insights_social(dados_brutos_texto, prospect, concorrentes):
    """Gera analise de Social Media com dados reais."""

    conc_str = ', '.join(concorrentes) if concorrentes else 'identificar nos dados'

    prompt = f"""{REGRAS_ANALISE}

PROSPECT: {prospect}
CONCORRENTES: {conc_str}

DADOS REAIS EXTRAIDOS DOS CSVs:
{dados_brutos_texto}

Produza uma analise estrategica de Social Media de nivel VP/Head. Use os frameworks e benchmarks abaixo.

## 1. SCORECARD DE SOCIAL MEDIA
Monte tabela comparativa por plataforma (Facebook, Instagram, TikTok, LinkedIn, WhatsApp) com VALORES REAIS:
| Metrica | {prospect} | Concorrentes | Benchmark Setor | Avaliacao |
Metricas por plataforma:
- Followers/Base, Engagement Rate, Posts no periodo, Engajamento por post, Crescimento de base
- Para cada metrica, classifique: Abaixo do benchmark / Na media / Acima do benchmark

BENCHMARKS DE REFERENCIA (use para contextualizar):
- Facebook: ER medio 0.06-0.15%, alcance organico 2-5% da base
- Instagram: ER medio 1.0-3.0%, Reels 2-3x alcance do feed
- TikTok: ER medio 3.0-9.0%, completion rate >50% = bom
- LinkedIn: ER medio 2.0-4.0%, document posts 3x mais alcance
- Engagement Rate = (Curtidas + Comentarios + Compartilhamentos + Saves) / Alcance x 100

## 2. SOCIAL MEDIA MATURITY ASSESSMENT
Classifique {prospect} no Social Media Maturity Model:
- Nivel 1 (Presenca): perfis criados, publicacoes esporadicas
- Nivel 2 (Engajamento): frequencia consistente, conteudo planejado
- Nivel 3 (Comunidade): interacao ativa, UGC, community management
- Nivel 4 (Advocacy): embaixadores da marca, social proof, viralizacao organica
- Nivel 5 (Revenue): social commerce ativo, atribuicao clara social > venda

## 3. CONTENT PERFORMANCE MATRIX
Classifique os tipos de conteudo (se dados disponiveis) na matriz BCG adaptada:
- STARS: alto alcance + alto engajamento (escalar investimento)
- CASH COWS: engajamento consistente, alcance moderado (manter frequencia)
- QUESTION MARKS: alto alcance, baixo engajamento (testar variacoes)
- DOGS: baixo alcance e engajamento (descontinuar ou pivotar)

Analise por formato: video vs imagem vs carrossel vs stories vs reels vs texto puro
Analise por tema: quais territorios de conteudo performam melhor e por que

## 4. SHARE OF VOICE SOCIAL
Calcule o Share of Voice estimado:
- SOV = Engajamento total de {prospect} / Engajamento total de todos os players analisados x 100
- Correlacao SOV vs Share of Market (Les Binet & Peter Field): marcas com SOV > SOM tendem a crescer
- Excess Share of Voice (ESOV) = SOV - SOM: se positivo, indica potencial de crescimento

## 5. ANALISE COMPETITIVA PROFUNDA
Para CADA concorrente vs {prospect}:
- Estrategia de conteudo aparente: pilares tematicos, tom, frequencia, formatos
- Pontos fortes a observar e aprender
- Vulnerabilidades explorveis: gaps de conteudo, baixo engajamento em areas especificas
- Estimativa de investimento: baseado na frequencia e qualidade, estimativa do tamanho da equipe/budget

## 6. CONCLUSAO ESTRATEGICA
**Headline**: Descoberta principal (com numeros)
**Diagnostico de Maturidade**: nivel atual e nivel alvo em 12 meses
**Brand Health Score Social**: avaliacao de 0-100 baseada nos dados
**Top 3 Gaps**: com impacto estimado em brand awareness e pipeline
**Roadmap Social Media**:
- Imediato (0-30 dias): otimizacoes de perfil, ajuste de frequencia, formatos prioritarios
- Curto Prazo (1-3 meses): nova estrategia de conteudo, testes de formato, community building
- Medio Prazo (3-6 meses): influencer strategy, social commerce, UGC programs
**Metricas de Sucesso**: KPIs mensuraveis para cada fase"""

    return gerar_texto(prompt, especialista='social')


def gerar_insights_trafego(dados_brutos_texto, prospect, concorrentes):
    """Gera analise de fontes de trafego com dados reais."""

    conc_str = ', '.join(concorrentes) if concorrentes else 'identificar nos dados'

    prompt = f"""{REGRAS_ANALISE}

PROSPECT: {prospect}
CONCORRENTES: {conc_str}

DADOS REAIS EXTRAIDOS DOS CSVs:
{dados_brutos_texto}

Produza uma analise estrategica de Fontes de Trafego usando o RACE Framework e Pirate Metrics.

## 1. DIAGNOSTICO DO ECOSSISTEMA DE AQUISICAO
Para CADA player encontrado nos dados, identifique:
- Distribuicao por canal: organico, pago, direto, social, referral, email, display
- Channel Dependency Index: % do trafego que vem do canal dominante
  (>50% de um canal = RISCO CRITICO, 30-50% = risco moderado, <30% = saudavel)
- Motor principal de crescimento: qual canal mais contribui para trafego qualificado

BENCHMARKS DE MIX SAUDAVEL:
- Organico: >30% (indica maturidade SEO e brand equity)
- Direto: 15-25% (indica forca de marca)
- Social: 5-15% (indica engajamento de comunidade)
- Referral: 5-10% (indica autoridade e parcerias)
- Pago: <30% (proporcao maior indica dependencia de investimento)

## 2. ANALISE DE EFICIENCIA POR CANAL (RACE Framework)
Para cada fonte de trafego, avalie no framework RACE:
- REACH: volume de trafego gerado por canal
- ACT: engajamento (paginas/sessao, duracao, bounce rate por fonte)
- CONVERT: taxa de conversao por fonte (se dados disponiveis)
- ENGAGE: retorno/recorrencia por fonte

Calcule o Traffic Cost Equivalent:
- Trafego organico x CPC medio do setor = valor do ativo SEO
- Trafego social x custo equivalente de ads sociais = valor do social organico
- Trafego direto = proxy de brand equity digital (valuation de marca)

## 3. ANALISE DE VULNERABILIDADE
Aplique stress test ao mix de aquisicao:
- "E se o Google penalizar o site?" -- quanto trafego seria perdido? (cenario -50% organico)
- "E se cortar budget de ads?" -- quanto trafego cai? (cenario -100% pago)
- "E se algoritmo social mudar?" -- impacto no trafego social?
Para cada cenario, calcule: perda de trafego > perda estimada de leads > impacto em receita

## 4. TENDENCIAS TEMPORAIS E MOMENTUM
Se houver dados de multiplos periodos:
- CAGR por canal: qual esta crescendo mais rapido
- Sazonalidade: picos e vales recorrentes
- Correlacao entre canais: investimento em ads aumenta trafego direto? (halo effect)
- Ponto de inflexao: mudancas bruscas e possiveis causas

## 5. CONCLUSAO ESTRATEGICA
**Headline**: Vulnerabilidade ou oportunidade principal (com numeros)
**Health Score do Ecossistema**: nota 0-100 baseada em diversificacao, crescimento e qualidade
**Top 3 Riscos**: com probabilidade e impacto estimado
**Roadmap de Diversificacao**:
- Curto Prazo: rebalancear mix com quick wins por canal
- Medio Prazo: desenvolver canais subdimensionados
- Longo Prazo: construir moats (vantagens competitivas sustentaveis) em canais proprios"""

    return gerar_texto(prompt, especialista='trafego')


def gerar_insights_midia_paga(dados_brutos_texto, prospect, concorrentes):
    """Gera analise de midia paga com dados reais."""

    conc_str = ', '.join(concorrentes) if concorrentes else 'identificar nos dados'

    prompt = f"""{REGRAS_ANALISE}

PROSPECT: {prospect}
CONCORRENTES: {conc_str}

DADOS REAIS EXTRAIDOS DOS CSVs:
{dados_brutos_texto}

Produza uma analise estrategica de Midia Paga de nivel Head de Performance. Use frameworks de eficiencia
e benchmarks do mercado brasileiro.

## 1. SCORECARD DE INVESTIMENTO COMPETITIVO
Monte tabela comparativa com VALORES REAIS de cada player:
| Metrica | {prospect} | Concorrentes | Benchmark | Avaliacao |
Metricas: Paid Traffic, Paid Cost, CPC medio, % trafego pago vs total, Keywords compradas

Para cada player calcule:
- Custo por visita paga = Paid Cost / Paid Traffic
- Eficiencia relativa: quem extrai mais trafego por real investido
- Share of Spend estimado: % do investimento total do setor

BENCHMARKS DE REFERENCIA (mercado Brasil):
- Google Ads CPC medio: Search R$1.50-4.00, Display R$0.30-0.80, Shopping R$0.50-1.50
- Meta Ads: CPM R$15-40, CPC R$0.50-2.00, CPL variavel por industria
- LinkedIn Ads: CPC R$8-25 (B2B premium)
- ROAS minimo saudavel: 3:1 e-commerce, 5:1 high-ticket, 2:1 awareness

## 2. ANALISE DE EFICIENCIA (FRAMEWORK FULL-FUNNEL)
Avalie o investimento em cada etapa do funil:
- TOFU (Awareness): CPM, Reach, Video Views -- investimento em construcao de demanda
- MOFU (Consideration): CPC, CTR, Engagement -- investimento em educacao e consideracao
- BOFU (Conversion): CPA, ROAS, Conv. Rate -- investimento em captura de demanda
Se dados forem limitados, analise o que os dados de PPC revelam sobre a estrategia de cada player.

## 3. ANALISE DE DESPERDICIO E OPORTUNIDADE
- Sobreposicao pago-organico: keywords onde ja rankeia top 3 organicamente mas paga ads = DESPERDICIO
  Calcule: CPC dessas keywords x clicks estimados = valor desperdicado/mes
- Oportunidades de arbitragem: keywords baratas (CPC baixo) com alta intencao transacional
- Competitive gap: keywords que concorrentes compram e {prospect} nao (e vice-versa)
- Budget allocation: proporcao search vs display vs social ads -- esta otimizado?

## 4. ESTIMATIVA DE ROI E CENARIOS
Modele 3 cenarios de investimento:
- Conservador: otimizar budget atual com melhor alocacao -- impacto estimado
- Moderado: +30% budget com foco nas oportunidades identificadas -- impacto estimado
- Agressivo: dobrar investimento com full-funnel strategy -- impacto estimado
Para cada: investimento > trafego esperado > leads estimados > receita projetada (usando conv. rates do setor)

## 5. CONCLUSAO ESTRATEGICA
**Headline**: Principal achado sobre eficiencia/ineficiencia de investimento
**Efficiency Score**: nota 0-100 baseada em CPC, ROAS, mix de canais
**Top 3 Oportunidades**: com ROI projetado para cada uma
**Roadmap de Otimizacao**:
- Imediato: eliminar desperdicios, pausar keywords ineficientes
- Curto Prazo: redistribuir budget para canais/keywords de melhor performance
- Medio Prazo: expandir para novas plataformas e formatos com budget incremental"""

    return gerar_texto(prompt, especialista='midia_paga')


def gerar_insights_buzz(prospect, kw_principais=None):
    """Gera analise de buzz marketing e comportamento de busca."""

    kws = ', '.join(kw_principais) if kw_principais else 'nao fornecidas -- inferir do segmento do prospect'

    prompt = f"""{REGRAS_ANALISE}

PROSPECT: {prospect}
PALAVRAS-CHAVE DO SEGMENTO: {kws}

NOTA ESPECIAL: Para Content Intelligence, combine dados dos CSVs (se houver) com seu profundo
conhecimento do mercado digital brasileiro. Cada afirmacao deve ser HIPER-ESPECIFICA ao segmento
de {prospect}. Nada generico. Use o framework Content-Market Fit e Search Demand Curve.

Produza uma analise de Content Intelligence de nivel director.

## 1. MAPA DE INTENCAO DE BUSCA DO CONSUMIDOR
Usando o modelo See-Think-Do-Care e Jobs-To-Be-Done, mapeie o comportamento de busca:

**Jornada de Busca do Consumidor no segmento de {prospect}:**
- DESCOBERTA: queries informacionais de topo de funil (volume estimado, tendencia)
  Liste 10+ queries reais que consumidores fazem, agrupadas por tema
- CONSIDERACAO: queries comparativas, "melhor", "review", "vale a pena" (volume, tendencia)
  Liste 8+ queries de comparacao especificas do segmento
- DECISAO: queries transacionais, "comprar", "preco", "onde encontrar" (volume, CPC estimado)
  Liste 5+ queries de conversao de alto valor
- POS-COMPRA: "como usar", "assistencia", "troca" -- oportunidades de retencao

Para cada grupo: volume estimado de buscas mensais, tendencia (crescendo/estavel/caindo),
e o que revela sobre dores e necessidades nao atendidas.

## 2. ANALISE DE DEMANDA E SAZONALIDADE
Especifico para o segmento de {prospect}:
- Picos de demanda: quais meses/periodos tem mais buscas e por que
- Eventos gatilho: datas comerciais, estacoes, eventos setoriais que impulsionam demanda
- Micro-tendencias emergentes: temas em ascensao que ainda nao saturaram
- Macro-tendencias: mudancas estruturais no comportamento do consumidor do segmento

## 3. TERRITORIOS DE CONTEUDO (CONTENT-MARKET FIT)
Aplique a Search Demand Curve para identificar oportunidades:
- HEAD TERMS (alto volume, alta competicao): quais {prospect} PRECISA disputar para credibilidade
- MID-TAIL (volume medio, competicao moderada): oportunidades realistas de rankear em 3-6 meses
- LONG-TAIL (baixo volume, alta conversao): nichos de conteudo com compradores qualificados

Para cada territorio, avalie:
- Dificuldade de competicao (quem ja domina e qual a autoridade deles)
- Content gap: alta demanda + baixa qualidade de conteudo existente = OPORTUNIDADE
- Formato ideal: artigo longo, video, ferramenta, calculadora, comparativo, guia

## 4. ANALISE DE SENTIMENTO E REPUTACAO DIGITAL
Baseado no conhecimento do segmento:
- Onde consumidores falam sobre marcas do segmento (Reclame Aqui, Google Reviews, Reddit, TikTok, forums)
- Temas de insatisfacao recorrentes no setor (oportunidade de se diferenciar)
- Nivel de confianca digital do setor: o consumidor confia em comprar online?
- User-generated content: o que consumidores postam sobre o segmento espontaneamente

## 5. ESTRATEGIA DE CONTEUDO PESO (Paid, Earned, Shared, Owned)
Recomende mix de distribuicao para {prospect}:
- OWNED: blog, site, newsletter -- pilares de conteudo proprietario
- EARNED: digital PR, mencoes espontaneas, backlinks editoriais -- como conquistar
- SHARED: social media, UGC, parcerias de conteudo -- como amplificar
- PAID: content amplification, native ads, sponsored content -- como acelerar

## 6. CONCLUSAO ESTRATEGICA
**Headline**: A maior oportunidade de conteudo para {prospect} (especifica, com estimativa de volume)
**Content Maturity Score**: avaliacao 0-100 da maturidade de conteudo atual
**Top 5 Territorios Prioritarios**: rankeados por potencial de trafego x dificuldade x valor de negocio
**Calendario Editorial Estrategico**: temas prioritarios por trimestre, alinhados a sazonalidade
**Metricas de Sucesso**: KPIs por territorio (trafego, rankings, leads, engagement)"""

    return gerar_texto(prompt, especialista='buzz')


def gerar_insights_aio(dados_brutos_texto, prospect, kw_principais=None):
    """Gera analise de AI Search / GEO."""

    kws = ', '.join(kw_principais) if kw_principais else 'inferir do segmento do prospect'

    prompt = f"""{REGRAS_ANALISE}

PROSPECT: {prospect}
PALAVRAS-CHAVE DO SEGMENTO: {kws}

DADOS REAIS EXTRAIDOS DOS CSVs (metricas de authority, keywords, trafego relevantes para GEO):
{dados_brutos_texto}

Produza uma analise PIONEIRA de AI Search Optimization (GEO) -- este e um diferencial competitivo
da Macfor que pouquissimas agencias oferecem. A analise deve ser visionaria e pratica ao mesmo tempo.

## 1. AI SEARCH READINESS SCORE
Avalie a preparacao de {prospect} para o novo paradigma de busca por IA.
Calcule um score de 0-100 baseado em:
- Authority Score / Domain Rating (peso 35%): autoridade e confiabilidade percebida por LLMs
  Referencia: DA <30 = muito baixo para citacao, 30-50 = possivel, 50-70 = provavel, 70+ = alta probabilidade
- Qualidade de Conteudo E-E-A-T (peso 30%): expertise, experiencia, autoridade, confianca
  Analise: o conteudo do prospect demonstra autoria especialista, fontes primarias, dados originais?
- Dados Estruturados (peso 20%): schema markup, FAQs estruturadas, knowledge graph signals
- Mencoes Externas e Citacoes (peso 15%): backlinks de fontes autoritativas, mencoes em midia, reviews

## 2. IMPACTO DO AI OVERVIEW NAS KEYWORDS DO SETOR
Classifique as keywords dos dados em niveis de risco de AI Overview:
- ALTO RISCO (provavel AI Overview): queries informacionais, "como", "o que e", "melhor X para Y"
  Impacto estimado no CTR: -25 a -40% vs busca tradicional
- MEDIO RISCO (possivel AI Overview): queries comparativas, "X vs Y", reviews
  Impacto estimado no CTR: -10 a -25%
- BAIXO RISCO (improvavel AI Overview): queries transacionais diretas, navegacionais, locais
  Impacto minimo no CTR

Para keywords de alto risco, calcule:
- Trafego atual nessas keywords x reducao estimada de CTR = PERDA PROJETADA de trafego
- Quem esta posicionado para SER CITADO no AI Overview (authority + conteudo + entidade no knowledge graph)

## 3. ANALISE DE PRESENCA EM LLMs
Avalie como {prospect} provavelmente aparece (ou nao) em respostas de:
- ChatGPT/GPT-4: prioriza fontes com alta autoridade, conteudo abrangente, reviews verificados
- Google Gemini/AI Overview: prioriza fontes que ja rankeiam bem + dados estruturados + E-E-A-T
- Perplexity: prioriza conteudo recente, bem citado, com dados originais
- Claude: prioriza conteudo factual, bem estruturado, de fontes respeitadas

Fatores que determinam citacao em LLMs (pesquisa de GEO):
- Autoridade do dominio: 35% do peso
- Qualidade e profundidade do conteudo: 30%
- Mencoes externas e citacoes: 20%
- Dados estruturados e markup: 15%

## 4. ESTRATEGIA GEO (GENERATIVE ENGINE OPTIMIZATION)
Acoes concretas priorizadas por impacto:

**Otimizacao de Conteudo para LLMs:**
- Estrutura de conteudo: perguntas claras como headers, respostas diretas no primeiro paragrafo
- Dados proprietarios: pesquisas originais, benchmarks unicos, estudos de caso -- LLMs preferem dados exclusivos
- Autoria especialista: bylines de especialistas reais, credenciais visiveis, links para perfis
- Atualizacao continua: conteudo com data de atualizacao recente tem prioridade

**Schema Markup Prioritario:**
- FAQ Schema em todas as paginas de conteudo informacional
- HowTo Schema para tutoriais e guias
- Product Schema com reviews agregados
- Organization Schema com founding date, awards, credentials
- Article Schema com author, datePublished, dateModified

**Estrategia de Entidade e Knowledge Graph:**
- Criar/otimizar Google Knowledge Panel da marca
- Wikipedia/Wikidata presence (se elegivel)
- Consistencia de NAP (Name, Address, Phone) em todas as plataformas
- Citacoes em fontes autoritativas do setor

## 5. CENARIOS FUTUROS (2025-2027)
Modelagem de impacto da evolucao do AI Search no setor de {prospect}:
- Cenario 1 (conservador): AI Overview em 20% das buscas do setor, CTR organico cai 10-15%
- Cenario 2 (moderado): AI Overview em 40% das buscas, CTR cai 20-30%, novos canais de IA emergem
- Cenario 3 (agressivo): 60%+ das buscas mediadas por IA, modelo de trafego muda fundamentalmente
Para cada cenario: impacto em trafego, leads e receita de {prospect}

## 6. CONCLUSAO ESTRATEGICA
**Headline**: Nivel de preparacao de {prospect} para o futuro da busca
**AI Readiness Score**: X/100 com breakdown por fator
**Risco Quantificado**: % do trafego atual vulneravel a AI Overview
**Roadmap GEO**:
- Imediato (0-30 dias): schema markup, otimizacao de headers FAQ, autoria especialista
- Curto Prazo (1-3 meses): conteudo data-driven, pesquisas originais, link building autoritativo
- Medio Prazo (3-6 meses): knowledge graph optimization, presenca em plataformas de IA
- Longo Prazo (6-12 meses): AI-first content strategy, ferramentas interativas, dados proprietarios"""

    return gerar_texto(prompt, especialista='aio')


def gerar_recomendacoes_estrategicas(insights_seo, insights_social, insights_trafego, insights_midia, insights_buzz, insights_aio, prospect):
    """Consolida recomendacoes em plano estrategico."""

    # Monta material disponivel (so inclui o que tem conteudo)
    material = ""
    if insights_seo:
        material += f"\n--- SEO (Head de SEO, 30 anos exp.) ---\n{insights_seo[:4000]}\n"
    if insights_social:
        material += f"\n--- SOCIAL MEDIA (Head de Social, 30 anos exp.) ---\n{insights_social[:4000]}\n"
    if insights_trafego:
        material += f"\n--- FONTES DE TRAFEGO (Head de Growth, 30 anos exp.) ---\n{insights_trafego[:3000]}\n"
    if insights_midia:
        material += f"\n--- MIDIA PAGA (Head de Performance, 30 anos exp.) ---\n{insights_midia[:3000]}\n"
    if insights_buzz:
        material += f"\n--- CONTENT INTELLIGENCE (Head de Content, 30 anos exp.) ---\n{insights_buzz[:3000]}\n"
    if insights_aio:
        material += f"\n--- AI SEARCH / GEO (Especialista GEO, pioneiro) ---\n{insights_aio[:3000]}\n"

    prompt = f"""Voce e o CMO/Diretor de Estrategia responsavel por consolidar as analises de TODOS os especialistas
abaixo em um plano estrategico integrado de nivel board-level. Use frameworks McKinsey e Bain para estruturar.

{REGRAS_ANALISE}

ANALISES DOS ESPECIALISTAS:
{material}

Produza um PLANO ESTRATEGICO INTEGRADO usando os frameworks abaixo:

## 1. EXECUTIVE SUMMARY (estilo McKinsey: Situation-Complication-Resolution)
**Situacao**: Contexto de mercado e posicao atual de {prospect} (2-3 frases com numeros)
**Complicacao**: O que esta em risco e por que agir agora e urgente (2-3 frases com impacto financeiro)
**Resolucao**: A tese estrategica central -- o que propomos e o resultado esperado (2-3 frases)

## 2. DIGITAL MATURITY ASSESSMENT
Avalie {prospect} no Digital Maturity Model (escala 1-5):
| Dimensao | Nivel Atual | Nivel Alvo (12m) | Gap |
- SEO & Conteudo: [1-5]
- Social Media: [1-5]
- Performance Media: [1-5]
- Analytics & Data: [1-5]
- AI Readiness: [1-5]
- Integracao de Canais: [1-5]
**Score Geral**: X/5 -- Classificacao: Iniciante / Em Desenvolvimento / Intermediario / Avancado / Lider

## 3. HIGHLIGHTS EXECUTIVOS
Para CADA canal analisado, extraia os 3-5 insights mais impactantes.
Formato: dado concreto + "isso significa que..." + impacto estimado em R$ ou %.
Ordene por impacto financeiro (maior primeiro).

## 4. DIAGNOSTICO INTEGRADO (ANALISE CRUZADA)
A "grande narrativa" que emerge do cruzamento de TODOS os dados:
- Sinergias entre canais: onde investimento em um canal potencializa outro
- Dependencias perigosas: riscos de concentracao em canal/estrategia unica
- Correlacoes descobertas: padroes que so aparecem cruzando dados de multiplos canais
- Posicao competitiva: onde {prospect} ganha e onde perde vs mercado (mapa de calor verbal)
- Biggest Threat: qual concorrente representa maior ameaca e em quais frentes
- Biggest Opportunity: a oportunidade de maior impacto com menor competicao

## 5. MATRIZ ESTRATEGICA (ESFORCO x IMPACTO)
Classifique TODAS as recomendacoes em 4 quadrantes:

**QUICK WINS (Alto Impacto, Baixo Esforco) -- 0 a 30 dias:**
Para cada: acao especifica + KPI + meta + impacto estimado
Estas sao as prioridades #1 -- resultados rapidos que geram momentum.

**PROJETOS ESTRATEGICOS (Alto Impacto, Alto Esforco) -- 1 a 6 meses:**
Para cada: acao + recursos necessarios + KPI + meta + ROI projetado
O core do plano -- onde a maior parte do investimento deve ir.

**OTIMIZACOES INCREMENTAIS (Baixo Impacto, Baixo Esforco) -- ongoing:**
Melhorias continuas que compoem resultado ao longo do tempo.

**APOSTAS DE LONGO PRAZO (Alto Impacto, Alto Esforco) -- 6 a 12 meses:**
Iniciativas transformacionais que redefinem a presenca digital.

## 6. ROADMAP COM OKRs (12 MESES)
Estruture em OKRs por trimestre:

**Q1 -- Fundacao e Quick Wins:**
- Objective: [objetivo claro]
- KR1: [metrica mensuravel]
- KR2: [metrica mensuravel]
- KR3: [metrica mensuravel]
- Investimento estimado: R$X

**Q2 -- Escala e Otimizacao:**
[mesmo formato]

**Q3 -- Diferenciacao:**
[mesmo formato]

**Q4 -- Lideranca:**
[mesmo formato]

## 7. BUSINESS CASE SIMPLIFICADO
| Item | Valor |
- Investimento total estimado (12 meses): R$X
- Retorno projetado em trafego incremental: +X%
- Retorno projetado em leads/oportunidades: +X/mes
- Retorno projetado em receita: R$X
- ROI estimado: X:1
- Payback period: X meses

## 8. RECOMENDACOES FINAIS (TOP 7)
As 7 acoes de MAIOR impacto no negocio, em ordem de prioridade.
Para cada:
1. **O que fazer** (acao concreta e especifica)
2. **Por que** (dado que sustenta + impacto se nao agir)
3. **Como** (primeiros passos praticos)
4. **Resultado esperado** (KPI + meta + prazo)
5. **Investimento estimado** vs **Retorno projetado**"""

    return gerar_texto(prompt, especialista='estrategico')

# =============================================================================
# FUNCOES DE GERACAO DE SLIDES (DINAMICO)
# =============================================================================
def gerar_slides_completos(prospect, insights_seo, insights_social, insights_trafego, insights_midia, insights_buzz, insights_aio, recomendacoes, kw_principais, concorrentes):
    """Gera slides dinamicamente via IA com base nos insights disponíveis."""

    # Monta o inventario de insights disponiveis
    secoes_disponiveis = []
    conteudo_para_slides = ""

    if insights_seo and insights_seo.strip():
        secoes_disponiveis.append("SEO")
        conteudo_para_slides += f"\n\n=== ANALISE DE SEO (pelo Head de SEO) ===\n{insights_seo}"

    if insights_social and insights_social.strip():
        secoes_disponiveis.append("SOCIAL MEDIA")
        conteudo_para_slides += f"\n\n=== ANALISE DE SOCIAL MEDIA (pelo Head de Social Media) ===\n{insights_social}"

    if insights_trafego and insights_trafego.strip():
        secoes_disponiveis.append("FONTES DE TRAFEGO")
        conteudo_para_slides += f"\n\n=== ANALISE DE FONTES DE TRAFEGO (pelo Head de Growth) ===\n{insights_trafego}"

    if insights_midia and insights_midia.strip():
        secoes_disponiveis.append("MIDIA PAGA")
        conteudo_para_slides += f"\n\n=== ANALISE DE MIDIA PAGA (pelo Head de Performance Media) ===\n{insights_midia}"

    if insights_buzz and insights_buzz.strip():
        secoes_disponiveis.append("BUZZ MARKETING")
        conteudo_para_slides += f"\n\n=== ANALISE DE BUZZ MARKETING (pelo Head de Content Intelligence) ===\n{insights_buzz}"

    if insights_aio and insights_aio.strip():
        secoes_disponiveis.append("AIO - AI SEARCH")
        conteudo_para_slides += f"\n\n=== ANALISE DE AIO (pelo Especialista em GEO) ===\n{insights_aio}"

    if recomendacoes and recomendacoes.strip():
        conteudo_para_slides += f"\n\n=== RECOMENDACOES ESTRATEGICAS CONSOLIDADAS (pelo CMO) ===\n{recomendacoes}"

    info_contexto = f"""PROSPECT: {prospect}
CONCORRENTES: {', '.join(concorrentes)}
PALAVRAS-CHAVE: {', '.join(kw_principais)}
SECOES COM DADOS DISPONIVEIS: {', '.join(secoes_disponiveis)}"""

    prompt = f"""Voce e um diretor criativo de apresentacoes estrategicas. Sua missao e transformar as analises abaixo
em uma apresentacao de slides de diagnostico estrategico para o cliente {prospect}.

{info_contexto}

{conteudo_para_slides}

DIRETRIZES PARA A APRESENTACAO:

1. ESTRUTURA ADAPTATIVA: Crie APENAS os slides necessarios para comunicar os insights com impacto.
   Nao ha numero fixo -- pode ser 20, 40 ou 60 slides dependendo da profundidade dos dados.
   Cada slide deve ter um proposito claro. Se nao tem conteudo relevante, nao crie o slide.

2. NARRATIVA ESTRATEGICA: A apresentacao deve contar uma historia:
   - Abertura: contexto e escopo do diagnostico
   - Sumario executivo: highlights que capturam atencao imediata
   - Analises por canal: APENAS para canais com dados disponiveis ({', '.join(secoes_disponiveis)})
   - Para cada canal: scorecard > analise detalhada > insights > conclusao (problema/implicacao/solucao)
   - Visao integrada: como os canais se conectam
   - Recomendacoes priorizadas: roadmap estrategico
   - Encerramento

3. REGRAS DE CONTEUDO POR SLIDE:
   - Titulo claro e direto (maximo 10 palavras)
   - Conteudo conciso: bullet points, nao paragrafos
   - Maximo 5-7 bullets por slide. Se precisar de mais, divida em 2 slides
   - Cada insight deve ter o formato: dado/observacao + implicacao para o negocio
   - NUNCA apresente dados brutos sem interpretacao
   - Inclua indicacoes de [GRAFICO: descricao] onde fizer sentido visual

4. FORMATO DE SAIDA (siga rigorosamente):
   Cada slide deve seguir este formato exato:

   ==SLIDE==
   TITULO: [titulo do slide]
   CONTEUDO:
   [conteudo do slide, com bullets usando "-" e sub-bullets usando "  -"]
   ==FIM_SLIDE==

5. NAO INCLUA slides institucionais da Macfor (quem somos, cases, time, metodologia).
   Esses serao adicionados separadamente. Foque 100% no diagnostico e inteligencia de mercado.

Crie a apresentacao agora. Lembre-se: qualidade e profundidade dos insights importam mais que quantidade de slides."""

    resultado_ia = gerar_texto(prompt, especialista='estrategico')
    return parse_slides_ia(resultado_ia)


def parse_slides_ia(texto_ia):
    """Converte a saida da IA em lista estruturada de slides."""
    slides = []
    if not texto_ia:
        return slides

    # Divide pelos marcadores de slide
    partes = re.split(r'==\s*SLIDE\s*==', texto_ia)

    num_slide = 0
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue

        # Remove marcador de fim
        parte = re.sub(r'==\s*FIM_SLIDE\s*==', '', parte).strip()
        if not parte:
            continue

        num_slide += 1

        # Extrai titulo
        titulo = ""
        conteudo_linhas = []
        linhas = parte.split('\n')
        modo_conteudo = False

        for linha in linhas:
            linha_strip = linha.strip()
            if linha_strip.upper().startswith('TITULO:'):
                titulo = linha_strip[7:].strip()
            elif linha_strip.upper().startswith('CONTEUDO:') or linha_strip.upper().startswith('CONTEUDO :'):
                modo_conteudo = True
            elif modo_conteudo and linha_strip:
                conteudo_linhas.append(linha_strip)
            elif not titulo and not modo_conteudo and linha_strip:
                # Fallback: primeira linha nao vazia e titulo
                titulo = linha_strip
                modo_conteudo = True

        # Monta o slide
        separador = f"{'=' * 50} SLIDE {num_slide} {'=' * 50}"
        slides.append((separador,))
        if titulo:
            slides.append((titulo,))
        for linha in conteudo_linhas:
            slides.append((linha,))
        slides.append(("",))

    return slides

def gerar_documento_interno(prospect, insights_seo, insights_social, insights_trafego, insights_midia, insights_buzz, insights_aio, recomendacoes, dados_extras=""):
    """Gera documento INTERNO da agencia com todas as analises detalhadas e notas tecnicas."""

    secao_extras = ""
    if dados_extras:
        secao_extras = f"\n---\n\n## DADOS COMPLEMENTARES\n\n{dados_extras}\n"

    # Monta lista de secoes com conteudo disponivel
    secoes = []
    if insights_seo:
        secoes.append(f"## SEO\n\n{insights_seo}")
    if insights_social:
        secoes.append(f"## SOCIAL MEDIA\n\n{insights_social}")
    if insights_trafego:
        secoes.append(f"## FONTES DE TRAFEGO\n\n{insights_trafego}")
    if insights_midia:
        secoes.append(f"## MIDIA PAGA\n\n{insights_midia}")
    if insights_buzz:
        secoes.append(f"## BUZZ MARKETING / CONTENT INTELLIGENCE\n\n{insights_buzz}")
    if insights_aio:
        secoes.append(f"## AI SEARCH (GEO)\n\n{insights_aio}")

    corpo_analises = "\n\n---\n\n".join(secoes)

    documento = f"""# DOCUMENTO INTERNO -- DIAGNOSTICO {prospect.upper()}
**Data:** {datetime.now().strftime('%d/%m/%Y')}
**Uso:** INTERNO AGENCIA -- Nao compartilhar com cliente
**Elaborado por:** Equipe de Inteligencia de Mercado -- Macfor

---

{corpo_analises}
{secao_extras}
---

## RECOMENDACOES ESTRATEGICAS CONSOLIDADAS

{recomendacoes}

---

*Documento interno. Contem analises tecnicas detalhadas, notas metodologicas e dados brutos interpretados.
Para o cliente, usar o Documento de Apresentacao.*
"""
    return documento


def gerar_documento_cliente(prospect, insights_seo, insights_social, insights_trafego, insights_midia, insights_buzz, insights_aio, recomendacoes):
    """Gera documento de APRESENTACAO para o cliente via IA -- linguagem executiva, sem jargoes tecnicos."""

    # Coleta todo o material de analise
    material = ""
    if insights_seo:
        material += f"\n--- SEO ---\n{insights_seo}\n"
    if insights_social:
        material += f"\n--- SOCIAL MEDIA ---\n{insights_social}\n"
    if insights_trafego:
        material += f"\n--- TRAFEGO ---\n{insights_trafego}\n"
    if insights_midia:
        material += f"\n--- MIDIA PAGA ---\n{insights_midia}\n"
    if insights_buzz:
        material += f"\n--- BUZZ ---\n{insights_buzz}\n"
    if insights_aio:
        material += f"\n--- AI SEARCH ---\n{insights_aio}\n"
    if recomendacoes:
        material += f"\n--- RECOMENDACOES ---\n{recomendacoes}\n"

    prompt = f"""Voce e um diretor de estrategia digital apresentando um diagnostico para o CEO/CMO de {prospect}.

MATERIAL DAS ANALISES INTERNAS (use como base, mas REESCREVA em linguagem executiva):
{material}

Gere um DOCUMENTO DE APRESENTACAO para o cliente seguindo estas regras:

1. LINGUAGEM EXECUTIVA: O cliente e C-level, nao e tecnico. Traduza jargoes em impacto de negocio.
   Em vez de "Domain Authority de 35", diga "a credibilidade digital da marca esta 40% abaixo dos concorrentes".

2. FOCO EM NEGOCIO: Cada descoberta deve responder "quanto isso custa?" ou "quanto podemos ganhar?"

3. NARRATIVA FLUIDA: Nao use formato de "secao de insights" separada. Os insights devem estar
   incorporados naturalmente ao longo da analise, como um consultor explicando em uma reuniao.

4. ESTRUTURA DO DOCUMENTO:
   - Sumario executivo (1 pagina): as 5 descobertas mais impactantes
   - Panorama competitivo: onde {prospect} esta vs concorrentes (numeros reais, visualizacoes sugeridas)
   - Analise por canal: APENAS os canais com dados reais, cada um com descobertas + implicacoes + oportunidades
   - Visao integrada: como tudo se conecta
   - Plano de acao recomendado: priorizado por impacto e timeline
   - Proximo passo: o que propomos fazer

5. TOM: Consultivo, confiante, baseado em evidencias. Nao use "acreditamos" ou "sugerimos" --
   use "os dados mostram" e "recomendamos".

6. EXTENSAO: Seja completo mas conciso. Cada paragrafo deve ter proposito.

Formate em Markdown com titulos claros."""

    return gerar_texto(prompt, especialista='estrategico')

# =============================================================================
# GERACAO DE DOCX FORMATADO
# =============================================================================
COR_PRIMARIA = RGBColor(0x1A, 0x1A, 0x2E)
COR_SECUNDARIA = RGBColor(0x00, 0x7B, 0xFF)
COR_ACCENT = RGBColor(0xFF, 0x6B, 0x00)

def _setup_styles(doc):
    """Configura estilos do documento."""
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15

    for i, (size, color) in enumerate([(24, COR_PRIMARIA), (18, COR_SECUNDARIA), (14, COR_PRIMARIA)], 1):
        h = doc.styles[f'Heading {i}']
        h.font.name = 'Calibri'
        h.font.size = Pt(size)
        h.font.color.rgb = color
        h.font.bold = True
        h.paragraph_format.space_before = Pt(18 if i == 1 else 12)
        h.paragraph_format.space_after = Pt(8)

def _add_capa(doc, prospect, tipo='cliente'):
    """Adiciona capa ao documento."""
    for _ in range(6):
        doc.add_paragraph('')
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run('DIAGNOSTICO ESTRATEGICO DIGITAL')
    run.font.size = Pt(28)
    run.font.color.rgb = COR_PRIMARIA
    run.font.bold = True
    run.font.name = 'Calibri'

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(prospect.upper())
    run.font.size = Pt(20)
    run.font.color.rgb = COR_SECUNDARIA
    run.font.name = 'Calibri'

    doc.add_paragraph('')
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label = 'Documento Interno - Agencia' if tipo == 'interno' else 'Apresentacao Executiva'
    run = info.add_run(f'{label}\n{datetime.now().strftime("%d/%m/%Y")}')
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    run.font.name = 'Calibri'

    doc.add_paragraph('')
    marca = doc.add_paragraph()
    marca.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = marca.add_run('Macfor - Marketing Intelligence')
    run.font.size = Pt(14)
    run.font.color.rgb = COR_ACCENT
    run.font.bold = True
    run.font.name = 'Calibri'

    doc.add_page_break()

def _colorir_celula(cell, cor_hex):
    """Aplica cor de fundo a uma celula."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{cor_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def _add_tabela_df(doc, df, titulo=None, max_linhas=20):
    """Adiciona DataFrame como tabela formatada."""
    if df is None or df.empty:
        return
    if titulo:
        doc.add_heading(titulo, level=3)
    df_show = df.head(max_linhas)
    table = doc.add_table(rows=1, cols=len(df_show.columns))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header
    for j, col in enumerate(df_show.columns):
        cell = table.rows[0].cells[j]
        cell.text = str(col)
        _colorir_celula(cell, '1A1A2E')
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.name = 'Calibri'

    # Rows with zebra striping
    for i, (_, row) in enumerate(df_show.iterrows()):
        row_cells = table.add_row().cells
        for j, val in enumerate(row):
            row_cells[j].text = str(val) if pd.notna(val) else ''
            for p in row_cells[j].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
                    r.font.name = 'Calibri'
            if i % 2 == 0:
                _colorir_celula(row_cells[j], 'F0F4FF')

    doc.add_paragraph('')

def _gerar_grafico_barras(df, col_label, col_valor, titulo, cor='#007BFF'):
    """Gera grafico de barras horizontais e retorna como BytesIO."""
    try:
        dados = df[[col_label, col_valor]].dropna().head(15)
        if dados.empty:
            return None
        dados[col_valor] = pd.to_numeric(dados[col_valor], errors='coerce')
        dados = dados.dropna().sort_values(col_valor, ascending=True)
        if dados.empty:
            return None
        fig, ax = plt.subplots(figsize=(8, max(3, len(dados) * 0.4)))
        ax.barh(dados[col_label].astype(str), dados[col_valor], color=cor, edgecolor='white')
        ax.set_title(titulo, fontsize=12, fontweight='bold', color='#1A1A2E')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=9)
        plt.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None

def _gerar_grafico_linhas(df, col_x, colunas_y, titulo):
    """Gera grafico de linhas e retorna como BytesIO."""
    try:
        fig, ax = plt.subplots(figsize=(9, 5))
        cores = ['#007BFF', '#FF6B00', '#1A1A2E', '#28a745', '#dc3545', '#6f42c1']
        for i, col in enumerate(colunas_y):
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors='coerce')
                ax.plot(df[col_x].astype(str), vals, marker='o', label=col,
                        color=cores[i % len(cores)], linewidth=2)
        ax.set_title(titulo, fontsize=12, fontweight='bold', color='#1A1A2E')
        ax.legend(fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.xticks(rotation=45, ha='right', fontsize=8)
        plt.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None

def _detectar_e_gerar_graficos(doc, dados_brutos):
    """Detecta dados graficaveis e gera charts automaticamente."""
    for nome, df in dados_brutos.items():
        if df is None or df.empty or len(df) < 2:
            continue
        numericas = df.select_dtypes(include=['number']).columns.tolist()
        texto_cols = df.select_dtypes(include=['object']).columns.tolist()
        if not numericas:
            continue

        # Tenta grafico de barras: col texto + col numerica
        if texto_cols and numericas:
            label_col = texto_cols[0]
            for val_col in numericas[:2]:
                buf = _gerar_grafico_barras(df, label_col, val_col,
                                            f'{nome}: {val_col}')
                if buf:
                    doc.add_picture(buf, width=Inches(5.5))
                    last = doc.paragraphs[-1]
                    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    doc.add_paragraph('')

        # Tenta grafico de linhas se parece temporal
        if texto_cols:
            date_col = None
            for c in texto_cols:
                sample = df[c].astype(str).iloc[0]
                if re.match(r'\d{4}', sample) or '|' in sample or '/' in sample:
                    date_col = c
                    break
            if date_col and len(numericas) >= 1:
                buf = _gerar_grafico_linhas(df, date_col, numericas[:4],
                                            f'{nome}: Evolucao temporal')
                if buf:
                    doc.add_picture(buf, width=Inches(5.5))
                    last = doc.paragraphs[-1]
                    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    doc.add_paragraph('')

def _add_runs_formatados(paragraph, texto):
    """Adiciona texto com **bold** e *italic* como runs."""
    partes = re.split(r'(\*\*.*?\*\*|\*.*?\*)', texto)
    for parte in partes:
        if parte.startswith('**') and parte.endswith('**'):
            run = paragraph.add_run(parte[2:-2])
            run.bold = True
        elif parte.startswith('*') and parte.endswith('*'):
            run = paragraph.add_run(parte[1:-1])
            run.italic = True
        else:
            paragraph.add_run(parte)

def _markdown_para_docx(doc, texto_md):
    """Converte markdown basico em elementos DOCX."""
    if not texto_md:
        return
    linhas = texto_md.split('\n')
    for linha in linhas:
        stripped = linha.strip()
        if not stripped:
            continue
        if stripped.startswith('### '):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith('## '):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith('# '):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith('---'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(12)
            run = p.add_run('_' * 60)
            run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
            run.font.size = Pt(8)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            p = doc.add_paragraph(style='List Bullet')
            _add_runs_formatados(p, stripped[2:])
        elif re.match(r'^\d+[\.\)] ', stripped):
            p = doc.add_paragraph(style='List Number')
            texto = re.sub(r'^\d+[\.\)] ', '', stripped)
            _add_runs_formatados(p, texto)
        elif stripped.startswith('  - ') or stripped.startswith('  * '):
            p = doc.add_paragraph(style='List Bullet 2')
            _add_runs_formatados(p, stripped.strip()[2:])
        else:
            p = doc.add_paragraph()
            _add_runs_formatados(p, stripped)

def gerar_docx(prospect, texto_markdown, dados_brutos, tipo='cliente'):
    """Gera documento DOCX formatado completo."""
    doc = Document()

    # Configura margens
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    _setup_styles(doc)
    _add_capa(doc, prospect, tipo)

    # Conteudo principal via markdown
    _markdown_para_docx(doc, texto_markdown)

    # Graficos automaticos
    if dados_brutos:
        doc.add_page_break()
        doc.add_heading('Anexo: Visualizacoes de Dados', level=1)
        _detectar_e_gerar_graficos(doc, dados_brutos)

    # Tabelas de dados
    if dados_brutos:
        doc.add_page_break()
        doc.add_heading('Anexo: Dados Tabulados', level=1)
        for nome, df in dados_brutos.items():
            if df is not None and not df.empty:
                _add_tabela_df(doc, df, titulo=nome.replace('_', ' ').title(), max_linhas=15)

    # Rodape
    doc.add_paragraph('')
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('Macfor - Marketing Intelligence | Diagnostico Estrategico Digital')
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    run.font.name = 'Calibri'

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================
st.sidebar.header("Configuração")

# Informacoes basicas
st.sidebar.subheader("Informacoes do Cliente")
input_prospect = st.sidebar.text_input("Nome do Prospect/Cliente", placeholder="Ex: Empresa XYZ", key="input_prospect")
input_concorrentes = st.sidebar.text_input("Concorrentes (separados por virgula)", placeholder="Ex: Concorrente A, Concorrente B", key="input_concorrentes")
input_kw = st.sidebar.text_input("Palavras-chave principais (separadas por virgula)", placeholder="Ex: colchao, colchao ortopedico, cama box", key="input_kw")

st.sidebar.markdown("---")

# Upload dos CSVs
st.sidebar.subheader("Upload de Arquivos")
st.sidebar.caption("Cada campo aceita multiplos arquivos. Nenhum campo e obrigatorio -- carregue apenas o que tiver.")
arquivos_seo = st.sidebar.file_uploader("SEO (historico, rank, trafego organico)", type=['csv'], accept_multiple_files=True, key="seo")
arquivos_keywords = st.sidebar.file_uploader("Keywords (ranking, volume, analise)", type=['csv'], accept_multiple_files=True, key="kw")
arquivos_facebook = st.sidebar.file_uploader("Facebook", type=['csv'], accept_multiple_files=True, key="fb")
arquivos_instagram = st.sidebar.file_uploader("Instagram", type=['csv'], accept_multiple_files=True, key="ig")
arquivos_tiktok = st.sidebar.file_uploader("TikTok", type=['csv'], accept_multiple_files=True, key="tt")
arquivos_linkedin = st.sidebar.file_uploader("LinkedIn", type=['csv'], accept_multiple_files=True, key="li")
arquivos_whatsapp = st.sidebar.file_uploader("WhatsApp", type=['csv'], accept_multiple_files=True, key="wa")
arquivos_concorrencia = st.sidebar.file_uploader("Concorrencia (benchmarks, comparativos)", type=['csv'], accept_multiple_files=True, key="conc")
arquivos_autoridade = st.sidebar.file_uploader("Autoridade / Dominio (backlinks, DA)", type=['csv'], accept_multiple_files=True, key="auth")

st.sidebar.markdown("---")
st.sidebar.subheader("Dados Adicionais")
st.sidebar.caption("Qualquer CSV extra -- a IA interpretara automaticamente.")
arquivos_extras = st.sidebar.file_uploader("Adicionais", type=['csv'], accept_multiple_files=True, key="extras")

st.sidebar.markdown("---")
st.sidebar.subheader("Contexto Adicional")
contexto_usuario = st.sidebar.text_area(
    "Informacoes extras para a analise",
    placeholder="Ex: O cliente atua no segmento B2B de colchoes premium, faturamento anual de R$50M, objetivo principal e aumentar market share no digital frente ao concorrente X que lancou e-commerce recentemente...",
    height=150,
    key="contexto_usuario"
)

# Botão para processar
if st.sidebar.button("Processar Dados e Gerar Diagnóstico"):
    # Salvar contexto adicional no session_state para uso nos prompts
    st.session_state.contexto_adicional = contexto_usuario.strip() if contexto_usuario else ""

    with st.spinner("Carregando e processando dados..."):
        dados_brutos = {}

        # Carregar todos os CSVs e armazenar brutos
        mapa_uploads = {
            'seo': arquivos_seo,
            'keywords': arquivos_keywords,
            'facebook': arquivos_facebook,
            'instagram': arquivos_instagram,
            'tiktok': arquivos_tiktok,
            'linkedin': arquivos_linkedin,
            'whatsapp': arquivos_whatsapp,
            'concorrencia': arquivos_concorrencia,
            'autoridade': arquivos_autoridade,
        }
        for chave, arquivos in mapa_uploads.items():
            if arquivos:
                df = carregar_e_combinar_csvs(arquivos)
                if df is not None and not df.empty:
                    dados_brutos[chave] = df

        # Prospect e concorrentes: prioriza input manual, fallback para CSV
        prospect_manual = input_prospect.strip() if input_prospect else ""
        conc_manual = [c.strip() for c in input_concorrentes.split(',') if c.strip()] if input_concorrentes else []
        kw_manual = [k.strip() for k in input_kw.split(',') if k.strip()] if input_kw else []

        if prospect_manual:
            st.session_state.nome_prospect = prospect_manual
        elif 'concorrencia' in dados_brutos:
            prospect, _ = processar_dados_prospect_concorrentes(dados_brutos['concorrencia'])
            st.session_state.nome_prospect = prospect
        else:
            st.session_state.nome_prospect = "Prospect"

        if conc_manual:
            st.session_state.concorrentes = conc_manual
        elif 'concorrencia' in dados_brutos:
            _, concorrentes = processar_dados_prospect_concorrentes(dados_brutos['concorrencia'])
            st.session_state.concorrentes = concorrentes
        else:
            st.session_state.concorrentes = []

        if kw_manual:
            st.session_state.kw_principais = kw_manual
        elif 'concorrencia' in dados_brutos:
            kws = processar_kw_principais(dados_brutos['concorrencia'])
            st.session_state.kw_principais = kws if kws else []
        else:
            st.session_state.kw_principais = []

        # CSVs extras
        if arquivos_extras:
            for i, arq in enumerate(arquivos_extras):
                df_extra = carregar_csv(arq)
                if df_extra is not None and not df_extra.empty:
                    nome = arq.name.replace('.csv', '').replace('.CSV', '')
                    dados_brutos[f'extra_{nome}'] = df_extra

        st.session_state.dados_brutos = dados_brutos
        st.session_state.dados_carregados = True
        st.success(f"Dados carregados: {len(dados_brutos)} conjuntos de dados ({', '.join(dados_brutos.keys())})")
    
    with st.spinner("Gerando insights com IA -- isso pode levar alguns minutos..."):
        prospect = st.session_state.nome_prospect
        concorrentes = st.session_state.concorrentes
        kw_principais = st.session_state.kw_principais
        db = st.session_state.dados_brutos

        # Monta contexto de dados brutos por area
        dados_seo = ""
        for k in ['seo', 'keywords', 'autoridade', 'concorrencia']:
            if k in db:
                dados_seo += f"\n--- CSV: {k} ---\n{df_para_contexto(db[k])}\n"

        dados_social = ""
        for k in ['facebook', 'instagram', 'tiktok', 'linkedin', 'whatsapp']:
            if k in db:
                dados_social += f"\n--- CSV: {k} ---\n{df_para_contexto(db[k])}\n"

        dados_todos = ""
        for k, v in db.items():
            dados_todos += f"\n--- CSV: {k} ---\n{df_para_contexto(v, 25)}\n"

        dados_extras = ""
        for k in db:
            if k.startswith('extra_'):
                dados_extras += f"\n--- {k} ---\n{df_para_contexto(db[k])}\n"

        # SEO -- gera se houver dados de SEO/keywords/autoridade OU contexto do usuario
        if dados_seo or st.session_state.contexto_adicional:
            st.info("Analisando SEO...")
            st.session_state.insights_seo = gerar_insights_seo(
                dados_seo or "(Nenhum CSV de SEO fornecido. Use o contexto adicional e dados disponiveis.)",
                kw_principais, prospect, concorrentes
            )

        # Social Media -- gera se houver dados sociais
        if dados_social:
            st.info("Analisando Social Media...")
            st.session_state.insights_social = gerar_insights_social(
                dados_social, prospect, concorrentes
            )

        # Tráfego -- gera se houver qualquer dado
        if dados_todos:
            st.info("Analisando Fontes de Trafego...")
            st.session_state.insights_trafego = gerar_insights_trafego(
                dados_todos, prospect, concorrentes
            )

        # Mídia Paga -- gera se houver qualquer dado
        if dados_todos:
            st.info("Analisando Midia Paga...")
            st.session_state.insights_midia_paga = gerar_insights_midia_paga(
                dados_todos, prospect, concorrentes
            )

        # Buzz -- sempre gera (usa conhecimento de mercado + contexto)
        st.info("Analisando Buzz Marketing...")
        st.session_state.insights_buzz = gerar_insights_buzz(
            prospect, kw_principais
        )

        # AIO -- gera se houver dados de SEO ou keywords
        if dados_seo or kw_principais:
            st.info("Analisando AI Search / AIO...")
            st.session_state.insights_aio = gerar_insights_aio(
                dados_seo or "(Sem dados de SEO. Analise com base nas keywords e contexto.)",
                prospect, kw_principais
            )

        # Recomendações consolidadas -- sempre gera com o que tiver
        st.info("Consolidando recomendacoes estrategicas...")
        st.session_state.recomendacoes = gerar_recomendacoes_estrategicas(
            st.session_state.insights_seo or "",
            st.session_state.insights_social or "",
            st.session_state.insights_trafego or "",
            st.session_state.insights_midia_paga or "",
            st.session_state.insights_buzz or "",
            st.session_state.insights_aio or "",
            prospect
        )

        # Gerar slides
        st.info("Gerando apresentacao de slides...")
        st.session_state.slides_gerados = gerar_slides_completos(
            prospect,
            st.session_state.insights_seo or "",
            st.session_state.insights_social or "",
            st.session_state.insights_trafego or "",
            st.session_state.insights_midia_paga or "",
            st.session_state.insights_buzz or "",
            st.session_state.insights_aio or "",
            st.session_state.recomendacoes or "",
            kw_principais,
            concorrentes
        )

        # Gerar documento INTERNO (agencia)
        st.info("Gerando documento interno...")
        st.session_state.documento_analise = gerar_documento_interno(
            prospect,
            st.session_state.insights_seo or "",
            st.session_state.insights_social or "",
            st.session_state.insights_trafego or "",
            st.session_state.insights_midia_paga or "",
            st.session_state.insights_buzz or "",
            st.session_state.insights_aio or "",
            st.session_state.recomendacoes or "",
            dados_extras
        )

        # Gerar documento do CLIENTE (apresentacao executiva)
        st.info("Gerando documento de apresentacao para o cliente...")
        st.session_state.documento_cliente = gerar_documento_cliente(
            prospect,
            st.session_state.insights_seo or "",
            st.session_state.insights_social or "",
            st.session_state.insights_trafego or "",
            st.session_state.insights_midia_paga or "",
            st.session_state.insights_buzz or "",
            st.session_state.insights_aio or "",
            st.session_state.recomendacoes or ""
        )

        st.session_state.relatorio_gerado = True
        st.success("Diagnostico gerado com sucesso!")

# =============================================================================
# EXIBIÇÃO DOS RESULTADOS
# =============================================================================
if st.session_state.relatorio_gerado:
    st.markdown("---")
    
    nome_safe = st.session_state.nome_prospect.lower().replace(' ', '_')
    data_str = datetime.now().strftime('%Y%m%d')

    tab_cliente, tab_interno, tab_slides, tab_dados = st.tabs([
        "Apresentacao Cliente",
        "Documento Interno",
        "Slides",
        "Dados Brutos"
    ])

    with tab_cliente:
        st.header(f"Diagnostico Estrategico -- {st.session_state.nome_prospect}")
        st.caption("Documento para apresentar ao cliente. Linguagem executiva, foco em negocio.")
        st.markdown(st.session_state.documento_cliente)
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="Baixar Markdown",
                data=st.session_state.documento_cliente,
                file_name=f"cliente_{nome_safe}_{data_str}.md",
                mime="text/markdown",
                key="dl_cliente_md"
            )
        with col_dl2:
            docx_cliente = gerar_docx(
                st.session_state.nome_prospect,
                st.session_state.documento_cliente,
                st.session_state.dados_brutos,
                tipo='cliente'
            )
            st.download_button(
                label="Baixar DOCX Formatado",
                data=docx_cliente,
                file_name=f"cliente_{nome_safe}_{data_str}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_cliente_docx"
            )

    with tab_interno:
        st.header(f"Documento Interno -- {st.session_state.nome_prospect}")
        st.caption("USO INTERNO DA AGENCIA. Analises detalhadas, dados brutos, notas tecnicas.")
        st.markdown(st.session_state.documento_analise)
        col_dl3, col_dl4 = st.columns(2)
        with col_dl3:
            st.download_button(
                label="Baixar Markdown",
                data=st.session_state.documento_analise,
                file_name=f"interno_{nome_safe}_{data_str}.md",
                mime="text/markdown",
                key="dl_interno_md"
            )
        with col_dl4:
            docx_interno = gerar_docx(
                st.session_state.nome_prospect,
                st.session_state.documento_analise,
                st.session_state.dados_brutos,
                tipo='interno'
            )
            st.download_button(
                label="Baixar DOCX Formatado",
                data=docx_interno,
                file_name=f"interno_{nome_safe}_{data_str}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_interno_docx"
            )
    
    with tab_slides:
        st.header("Slides do Diagnostico")

        slides_list = st.session_state.slides_gerados
        if slides_list:
            # Conta slides reais (pelos separadores)
            total_slides = sum(1 for s in slides_list if s and s[0] and 'SLIDE' in s[0] and '===' in s[0])
            st.markdown(f"**{total_slides} slides gerados** com base nos dados disponiveis.")
            st.markdown("---")

            # Renderiza cada slide como card
            slide_atual = None
            conteudo_slide = []
            for elemento in slides_list:
                linha = elemento[0] if isinstance(elemento, tuple) and elemento else str(elemento)
                if 'SLIDE' in linha and '===' in linha:
                    # Renderiza slide anterior
                    if slide_atual is not None:
                        with st.expander(slide_atual, expanded=False):
                            st.markdown('\n'.join(conteudo_slide))
                    slide_atual = linha.strip('= ').strip()
                    conteudo_slide = []
                elif linha.strip():
                    conteudo_slide.append(linha)

            # Renderiza ultimo slide
            if slide_atual is not None and conteudo_slide:
                with st.expander(slide_atual, expanded=False):
                    st.markdown('\n'.join(conteudo_slide))

        # Texto para download
        texto_slides = ""
        for elemento in slides_list:
            if isinstance(elemento, tuple):
                texto_slides += "\n".join(elemento) + "\n"
            else:
                texto_slides += str(elemento) + "\n"

        st.download_button(
            label="Baixar Slides (TXT)",
            data=texto_slides,
            file_name=f"slides_{st.session_state.nome_prospect.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
    
    with tab_dados:
        st.header("Dados Processados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Prospect e Concorrentes")
            st.write(f"**Prospect:** {st.session_state.nome_prospect}")
            st.write("**Concorrentes:**")
            for i, conc in enumerate(st.session_state.concorrentes, 1):
                st.write(f"{i}. {conc}")
            
            st.subheader("Palavras-chave Principais")
            for i, kw in enumerate(st.session_state.kw_principais, 1):
                st.write(f"{i}. {kw}")
        
        with col2:
            st.subheader("Conjuntos de Dados Carregados")
            for nome, df in st.session_state.dados_brutos.items():
                st.write(f"**{nome}**: {df.shape[0]} linhas x {df.shape[1]} colunas")

        # Mostra amostra de cada dataset
        for nome, df in st.session_state.dados_brutos.items():
            with st.expander(f"Dados: {nome} ({df.shape[0]}x{df.shape[1]})"):
                st.dataframe(df.head(15))

else:
    # Tela inicial
    st.info("👈 Carregue os arquivos CSV na barra lateral para gerar o diagnóstico.")
    
    st.markdown("""
    ## Instrucoes

    1. **Carregue os arquivos CSV** na barra lateral (nao e necessario preencher todos os campos)
    2. **Preencha o contexto adicional** com informacoes sobre o cliente e objetivos
    3. **Clique em "Processar Dados e Gerar Diagnostico"**
    4. **Baixe os resultados** em Markdown ou DOCX formatado

    ### Campos de Upload

    | Campo | O que carregar |
    |-------|---------------|
    | **SEO** | Historico SEO, trafego organico, rank tracking (SEMrush, Ahrefs) |
    | **Keywords** | Ranking de keywords, volumes, CPC, analise de oportunidades |
    | **Facebook** | Metricas de pagina, engajamento, posts |
    | **Instagram** | Followers, engagement rate, posts, stories |
    | **TikTok** | Views, engajamento, seguidores, videos |
    | **LinkedIn** | Company page, followers, posts, engajamento |
    | **WhatsApp** | Metricas de atendimento, conversao, volume |
    | **Concorrencia** | Benchmarks, dados comparativos entre players |
    | **Autoridade/Dominio** | Domain Authority, backlinks, dominios referenciadores |
    | **Adicionais** | Qualquer CSV extra (CRM, GA, vendas, NPS, etc.) |

    ### Saidas Geradas

    - **Apresentacao Cliente**: documento executivo (DOCX formatado com graficos e tabelas)
    - **Documento Interno**: analise tecnica detalhada para uso da agencia
    - **Slides**: apresentacao dinamica gerada com base nos dados
    - **Dados Brutos**: visualizacao dos datasets carregados
    """)

# Rodapé
st.markdown("---")
st.markdown("**Gerador de Diagnóstico Estratégico** | Desenvolvido para Macfor")
