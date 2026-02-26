# Relatório do Sistema de Propostas - TAG Investimentos

**Data:** 24/02/2026
**Versão:** 1.0

---

## 1. Visão Geral

Foi desenvolvido um sistema completo de geração de propostas para clientes prospects da TAG Investimentos. O sistema automatiza o fluxo que hoje é manual (comercial envia informações para a gestão, que monta a proposta) em uma plataforma integrada com inteligência artificial.

### Fluxo do Sistema

```
Comercial cadastra prospect → Upload da carteira atual → IA analisa e diagnostica
→ IA gera proposta personalizada → Gestão revisa e ajusta → Proposta HTML para o cliente
```

---

## 2. Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| **Python 3.10** | Linguagem principal |
| **Streamlit** | Interface web (frontend + backend) |
| **SQLite** | Banco de dados local |
| **Anthropic Claude API** | Inteligência artificial (diagnóstico + recomendação) |
| **Plotly** | Gráficos interativos |
| **Pandas** | Manipulação de dados |
| **python-dotenv** | Gerenciamento de variáveis de ambiente |

---

## 3. Arquitetura de Arquivos

```
Simulador de realocação/
│
├── proposta_app.py                  ← ENTRY POINT (streamlit run proposta_app.py)
├── app.py                           ← Simulador existente (inalterado)
├── .env                             ← API Key da Anthropic
├── requirements.txt                 ← Dependências
│
├── shared/                          ← Módulos compartilhados (1.486 linhas)
│   ├── brand.py                     ← Identidade visual TAG (cores, CSS, componentes)
│   ├── date_utils.py                ← Cálculos de dias úteis/corridos
│   ├── fund_utils.py                ← Match de fundos, base de liquidação
│   ├── portfolio_utils.py           ← Parser de carteiras, cash flow, evolução
│   └── rebalancing.py               ← Motor de realocação inteligente (5 fases)
│
├── database/                        ← Banco de dados (465 linhas)
│   ├── db.py                        ← Schema SQLite (prospects, propostas, interações)
│   ├── models.py                    ← CRUD completo + estatísticas do pipeline
│   └── propostas.db                 ← Banco SQLite (auto-criado)
│
├── ai/                              ← Integração com IA (375 linhas)
│   ├── client.py                    ← Wrapper da API Claude (com fallback)
│   ├── diagnostico.py               ← Diagnóstico da carteira com IA
│   └── recomendacao.py              ← Recomendação personalizada com restrições
│
├── proposal_gen/                    ← Geração de propostas (438 linhas)
│   ├── charts.py                    ← Gráficos Plotly (donuts, barras, cenários)
│   └── html_generator.py            ← Gerador HTML premium (dark theme TAG)
│
├── pages_proposta/                  ← Telas do sistema (1.362 linhas)
│   ├── p1_cadastro.py               ← Tela 1: Cadastro do Prospect
│   ├── p2_carteira_atual.py         ← Tela 2: Carteira Atual + Diagnóstico
│   ├── p3_proposta_ia.py            ← Tela 3: Proposta com IA
│   ├── p4_visualizar.py             ← Tela 4: Preview + Export
│   └── p5_pipeline.py               ← Tela 5: Pipeline/CRM
│
├── modelos_carteira/                ← Carteiras modelo por perfil (Excel)
├── propostas_html/                  ← Propostas geradas (HTML)
├── uploads/                         ← Arquivos enviados
└── Dados de liquid.xlsx             ← Base de 2.430 fundos (existente)
```

**Total:** 4.246 linhas de código Python em 20 arquivos

---

## 4. Funcionalidades por Tela

### Tela 1: Cadastro de Prospect (p1_cadastro.py)

**O que faz:** Cadastro completo de prospects com todas as informações necessárias para gerar uma proposta.

**Campos disponíveis:**
- Dados pessoais: nome, CPF/CNPJ, email, telefone, tipo (PF/PJ)
- Perfil: conservador, moderado, arrojado, agressivo
- Patrimônio total e investível
- Horizonte de investimento
- Objetivos: preservação, renda, crescimento, liquidez, proteção cambial, sucessório
- Retirada mensal
- Restrições predefinidas: não vender RF, sem cripto, só ESG, sem RV, sem exterior, sem crédito privado, manter previdência
- Restrições em texto livre
- Status do pipeline (Lead → Cliente)
- Responsável comercial
- Observações gerais

**Recursos:**
- Criar novo ou editar prospect existente
- Excluir prospect
- Resumo visual com métricas

---

### Tela 2: Carteira Atual (p2_carteira_atual.py)

**O que faz:** Importa a carteira atual do prospect e gera diagnóstico automático.

**Funcionalidades:**
- Upload de Excel (formato Posição Projetada) com detecção automática de colunas
- Preenchimento manual (tabela editável)
- Diagnóstico automático:
  - Concentração por ativo (HHI - Herfindahl-Hirschman Index)
  - Concentração Top 3
  - Perfil de liquidez (D+0-1, D+2-5, D+6-30, D+30+)
  - Alocação por estratégia/categoria
- Gráficos: donut de alocação + barras de liquidez
- Dados salvos automaticamente no banco

---

### Tela 3: Proposta com IA (p3_proposta_ia.py)

**O que faz:** A IA analisa o perfil do prospect, sua carteira atual e restrições, e gera uma proposta personalizada.

**Fluxo:**
1. Seleciona prospect (que já tem carteira)
2. Seleciona carteira modelo base (upload, arquivo salvo, ou manual)
3. Clica "Gerar Proposta"
4. A IA:
   - Gera diagnóstico profissional da carteira atual
   - Seleciona modelo adequado ao perfil
   - Aplica restrições do cliente (ex: mantém renda fixa)
   - Gera texto de recomendação
5. Resultado editável pela gestão
6. Comparativo visual: Atual vs Proposta (donuts lado a lado)
7. Salvar rascunho, enviar para revisão, ou aprovar

**IA utilizada em 3 pontos:**
- `ai/diagnostico.py` - Análise da carteira com pontos de atenção
- `ai/recomendacao.py` - Carteira personalizada respeitando restrições
- `ai/recomendacao.py` - Texto profissional da recomendação

---

### Tela 4: Visualizar Proposta (p4_visualizar.py)

**O que faz:** Preview completo da proposta com opção de exportar.

**Seções da proposta:**
1. Capa: logo TAG, nome do prospect, perfil, data
2. Métricas: patrimônio, perfil, ativos, horizonte
3. Diagnóstico da carteira atual
4. Gráficos comparativos (Atual vs Proposta)
5. Recomendação
6. Tabela detalhada da carteira proposta
7. Sobre a TAG
8. Disclaimer legal

**Exportação:**
- Gerar HTML standalone (design premium dark theme)
- Download do arquivo HTML
- Marcar como "Enviada" (atualiza pipeline)

---

### Tela 5: Pipeline/CRM (p5_pipeline.py)

**O que faz:** Gestão visual de todos os prospects e funil de vendas.

**Componentes:**
- Métricas do funil: total, patrimônio, em prospecção, em negociação, convertidos
- Kanban visual com 5 colunas: Lead → Qualificado → Proposta Enviada → Negociação → Cliente
- Cards com nome, perfil e patrimônio
- Tabela completa com busca e filtros (status, responsável)
- Registro de interações (reunião, ligação, email, WhatsApp, proposta)
- Próximas ações pendentes

---

## 5. Banco de Dados

### Tabela: prospects
Armazena todos os prospects com dados completos (perfil, patrimônio, objetivos, restrições, carteira, status do pipeline).

### Tabela: propostas
Cada proposta gerada com versão, modelo usado, textos da IA, carteira proposta, status (Rascunho → Enviada → Aceita), link de compartilhamento.

### Tabela: interacoes
Histórico de todas as interações com cada prospect (tipo, descrição, responsável, próxima ação).

---

## 6. Integração com IA (Claude API)

**Modelo utilizado:** Claude Sonnet (claude-sonnet-4-20250514)
**Custo estimado:** R$ 0,05 a R$ 0,15 por proposta gerada

### Diagnóstico (ai/diagnostico.py)
A IA recebe: perfil do prospect + carteira completa + métricas calculadas.
Gera: texto profissional com visão geral, pontos de atenção, oportunidades e recomendação principal.

### Recomendação (ai/recomendacao.py)
A IA recebe: perfil + restrições + modelo base + carteira atual.
Gera: JSON com carteira proposta ajustada + justificativa por mudança.

### Fallback
Se a API Key não estiver configurada, o sistema funciona com diagnósticos básicos (numéricos, sem texto IA).

---

## 7. Motor de Realocação (Reutilizado)

O sistema reutiliza o motor inteligente do Simulador de Realocação existente:
- Algoritmo de 5 fases que garante caixa nunca negativo
- Base de 2.430 fundos brasileiros com dados de liquidação (D+)
- Cálculos de dias úteis/corridos
- Match de fundos por código Anbima, nome ou ticker B3
- Simulação dia-a-dia de fluxo de caixa

---

## 8. Como Usar

### Primeiro uso:
```bash
cd "G:\Drives compartilhados\Gestao_AI\Simulador de realocação"
pip install -r requirements.txt
streamlit run proposta_app.py
```

### Fluxo recomendado:
1. **Pipeline** - Ver panorama geral
2. **Cadastro** - Registrar novo prospect com dados completos
3. **Carteira Atual** - Upload do Excel ou preenchimento manual
4. **Proposta com IA** - Selecionar modelo e gerar proposta
5. **Visualizar** - Revisar, exportar HTML e enviar ao cliente

### Para colocar carteiras modelo:
Salvar arquivos Excel em `modelos_carteira/` com colunas: Código, Ativo, % Alvo

---

## 9. Segurança

- API Key armazenada em `.env` (não commitado no Git)
- Banco SQLite local (não exposto na internet)
- Propostas HTML são arquivos estáticos (sem server-side)

---

## 10. Próximos Passos Sugeridos

1. **Carteiras modelo reais** - Salvar as carteiras modelo da TAG por perfil em `modelos_carteira/`
2. **Geração de PDF** - Adicionar export em PDF com reportlab (atualmente gera HTML)
3. **Cenários de projeção** - Simulação Monte Carlo (otimista/base/pessimista)
4. **Plano de transição** - Integrar cronograma Gantt na proposta
5. **Múltiplos usuários** - Autenticação para diferentes membros do time
6. **Deploy** - Publicar em servidor interno ou Streamlit Cloud

---

*Desenvolvido para TAG Investimentos - Fevereiro 2026*
