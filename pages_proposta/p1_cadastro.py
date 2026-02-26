"""
Tela 1: Cadastro do Prospect
Complete form for registering prospect information.
Includes: dados pessoais, perfil investidor, objetivos, restricoes,
          estrutura familiar, estrutura patrimonial, fee, pipeline.
With real-time validation (CPF/CNPJ, email, phone) and completeness scoring.
"""
import streamlit as st
import json
import pandas as pd
from datetime import date

from shared.brand import TAG, render_card, render_status_badge, fmt_brl
from shared.validators import (
    validate_cpf_cnpj,
    validate_email,
    validate_phone,
    validate_prospect_completeness,
)
from database.models import (
    create_prospect,
    update_prospect,
    get_prospect,
    list_prospects,
)

PERFIS = ["Conservador", "Moderado", "Arrojado", "Agressivo"]
HORIZONTES = [
    "Curto Prazo (< 1 ano)",
    "Médio Prazo (1-3 anos)",
    "Longo Prazo (3-5 anos)",
    "Muito Longo Prazo (> 5 anos)",
]
OBJETIVOS_OPTIONS = [
    "Preservação de capital",
    "Geração de renda",
    "Crescimento patrimonial",
    "Liquidez",
    "Proteção cambial",
    "Planejamento sucessório",
    "Diversificação",
]
RESTRICOES_OPTIONS = [
    "Não vender renda fixa existente",
    "Sem criptoativos",
    "Apenas fundos ESG",
    "Sem renda variável",
    "Sem fundos no exterior",
    "Sem fundos de crédito privado",
    "Manter ativos de previdência",
]
PIPELINE_STATUS = [
    "Lead",
    "Qualificado",
    "Proposta Enviada",
    "Negociação",
    "Cliente",
    "Perdido",
]

RELACOES_FAMILIARES = [
    "Cônjuge", "Filho(a)", "Neto(a)", "Pai/Mãe",
    "Irmão(ã)", "Sobrinho(a)", "Outro",
]
REGIMES_CASAMENTO = [
    "Comunhão parcial de bens",
    "Comunhão universal de bens",
    "Separação total de bens",
    "Participação final nos aquestos",
    "N/A",
]
TIPOS_ESTRUTURA = [
    "Pessoa Física",
    "Pessoa Jurídica",
    "Holding Familiar",
    "Offshore",
    "Estrutura Mista",
]
JURISDICOES_OFFSHORE = [
    "BVI (Ilhas Virgens Britânicas)",
    "Bahamas",
    "Cayman Islands",
    "Delaware (EUA)",
    "Luxemburgo",
    "Outro",
]
TIPOS_OFFSHORE = ["PIC", "Trust", "LLC", "Foundation", "Outro"]
SERVICOS_DISPONIVEIS = [
    "Gestão de investimentos",
    "Planejamento sucessório",
    "Consolidação patrimonial",
    "Gestão imobiliária",
    "Investimentos alternativos",
    "Produtos estruturados",
]


def render_cadastro():
    st.title("Cadastro de Prospect")

    # ── Select existing or create new ──
    prospects = list_prospects()
    prospect_names = ["+ Novo Prospect"] + [
        f"{p['nome']} ({p['status']})" for p in prospects
    ]

    selected = st.selectbox(
        "Selecionar prospect",
        prospect_names,
        key="cadastro_select",
    )

    editing = selected != "+ Novo Prospect"
    if editing:
        idx = prospect_names.index(selected) - 1
        prospect = get_prospect(prospects[idx]["id"])
        prospect_id = prospect["id"]
    else:
        prospect = {}
        prospect_id = None

    # ── Completeness score badge (for existing prospects) ──
    if editing and prospect:
        _render_completeness_badge(prospect)

    # ── Initialize session state for family members ──
    _init_family_state(prospect)

    # ── TABS for organized sections ──
    tabs = st.tabs([
        "📋 Dados Pessoais",
        "💰 Perfil Investidor",
        "👨\u200d👩\u200d👧\u200d👦 Estrutura Familiar",
        "🏢 Estrutura Patrimonial",
        "💵 Fee / Proposta Comercial",
        "📊 Pipeline",
    ])

    # ── Form ──
    with st.form("prospect_form", clear_on_submit=False):

        # ── TAB 1: Dados Pessoais ──
        with tabs[0]:
            st.markdown(
                f'<div style="color:{TAG["laranja"]};font-weight:600;font-size:1.1rem;margin-bottom:16px">'
                f'{"Editando: " + prospect.get("nome", "") if editing else "Novo Prospect"}'
                f"</div>",
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                nome = st.text_input("Nome completo *", value=prospect.get("nome", ""))
            with col2:
                tipo_pessoa = st.radio(
                    "Tipo",
                    ["PF", "PJ"],
                    index=0 if prospect.get("tipo_pessoa", "PF") == "PF" else 1,
                    horizontal=True,
                )
            with col3:
                cpf_cnpj = st.text_input(
                    "CPF/CNPJ",
                    value=prospect.get("cpf_cnpj", ""),
                    help="Digite apenas números. Será validado automaticamente.",
                )

            col1, col2, col3 = st.columns(3)
            with col1:
                email = st.text_input(
                    "Email",
                    value=prospect.get("email", ""),
                )
            with col2:
                telefone = st.text_input(
                    "Telefone",
                    value=prospect.get("telefone", ""),
                    help="Formato: (XX) XXXXX-XXXX",
                )
            with col3:
                responsavel = st.text_input(
                    "Responsável comercial",
                    value=prospect.get("responsavel", ""),
                )

            # ── Real-time validations ──
            _show_field_validations(cpf_cnpj, email, telefone)

        # ── TAB 2: Perfil de Investidor ──
        with tabs[1]:
            col1, col2, col3 = st.columns(3)
            with col1:
                perfil_idx = PERFIS.index(prospect.get("perfil_investidor", "Moderado")) if prospect.get("perfil_investidor") in PERFIS else 1
                perfil = st.selectbox("Perfil *", PERFIS, index=perfil_idx)
            with col2:
                patrimonio_total = st.number_input(
                    "Patrimônio Total (R$)",
                    min_value=0.0,
                    value=float(prospect.get("patrimonio_total", 0)),
                    step=100000.0,
                    format="%.2f",
                )
            with col3:
                patrimonio_investivel = st.number_input(
                    "Patrimônio Investível (R$)",
                    min_value=0.0,
                    value=float(prospect.get("patrimonio_investivel", 0)),
                    step=100000.0,
                    format="%.2f",
                )

            # Alert if investivel > total
            if patrimonio_investivel > 0 and patrimonio_total > 0 and patrimonio_investivel > patrimonio_total:
                st.warning("⚠️ Patrimônio investível está maior que o patrimônio total. Verifique os valores.")

            col1, col2 = st.columns(2)
            with col1:
                horiz_idx = HORIZONTES.index(prospect.get("horizonte_investimento", HORIZONTES[1])) if prospect.get("horizonte_investimento") in HORIZONTES else 1
                horizonte = st.selectbox("Horizonte de investimento", HORIZONTES, index=horiz_idx)
            with col2:
                retirada = st.number_input(
                    "Retirada mensal (R$, se houver)",
                    min_value=0.0,
                    value=float(prospect.get("retirada_mensal", 0)),
                    step=5000.0,
                    format="%.2f",
                )

            # Retirada consistency check
            if retirada > 0 and patrimonio_investivel > 0:
                annual_withdrawal_pct = (retirada * 12 / patrimonio_investivel) * 100
                if annual_withdrawal_pct > 8:
                    st.warning(
                        f"⚠️ Retirada mensal equivale a **{annual_withdrawal_pct:.1f}% a.a.** "
                        f"do patrimônio investível. Taxas acima de 8% a.a. podem comprometer o capital."
                    )
                elif annual_withdrawal_pct > 4:
                    st.info(
                        f"ℹ️ Retirada mensal equivale a **{annual_withdrawal_pct:.1f}% a.a.** "
                        f"do patrimônio investível."
                    )

            st.markdown("---")

            # Objetivos
            st.markdown("**Objetivos**")
            current_objetivos = prospect.get("objetivos", []) if isinstance(prospect.get("objetivos"), list) else []
            objetivos = st.multiselect(
                "Selecione os objetivos do prospect",
                OBJETIVOS_OPTIONS,
                default=[o for o in current_objetivos if o in OBJETIVOS_OPTIONS],
            )

            st.markdown("---")

            # Restrições
            st.markdown("**Restrições**")
            current_restricoes = prospect.get("restricoes", []) if isinstance(prospect.get("restricoes"), list) else []
            restricoes = st.multiselect(
                "Restrições de investimento",
                RESTRICOES_OPTIONS,
                default=[r for r in current_restricoes if r in RESTRICOES_OPTIONS],
            )
            restricoes_texto = st.text_area(
                "Outras restrições (texto livre)",
                value=prospect.get("restricoes_texto", ""),
                placeholder="Ex: Cliente não quer exposição a VALE, quer manter FII no Itaú...",
            )

            # Profile consistency hints
            _show_profile_hints(perfil, objetivos, horizonte)

        # ── TAB 3: Estrutura Familiar ──
        with tabs[2]:
            st.markdown(
                f'<p style="color:{TAG["text_muted"]};font-size:0.9rem">'
                f"Registre os membros da família para análise de planejamento sucessório e patrimonial."
                f"</p>",
                unsafe_allow_html=True,
            )

            # Load existing data
            existing_family = prospect.get("estrutura_familiar", [])
            if not isinstance(existing_family, list):
                existing_family = []

            # Use data_editor for family members
            family_df = pd.DataFrame(
                existing_family if existing_family else [],
                columns=["nome", "relacao", "idade", "regime_casamento"],
            )
            if family_df.empty:
                family_df = pd.DataFrame(
                    [{"nome": "", "relacao": "Filho(a)", "idade": 0, "regime_casamento": "N/A"}],
                    columns=["nome", "relacao", "idade", "regime_casamento"],
                )

            family_edited = st.data_editor(
                family_df,
                column_config={
                    "nome": st.column_config.TextColumn("Nome", width="large"),
                    "relacao": st.column_config.SelectboxColumn(
                        "Relação",
                        options=RELACOES_FAMILIARES,
                        width="medium",
                    ),
                    "idade": st.column_config.NumberColumn("Idade", min_value=0, max_value=120, width="small"),
                    "regime_casamento": st.column_config.SelectboxColumn(
                        "Regime Casamento",
                        options=REGIMES_CASAMENTO,
                        width="medium",
                    ),
                },
                num_rows="dynamic",
                use_container_width=True,
                key="family_editor",
            )

            st.markdown("---")
            st.markdown("**Patrimônio para Sucessão**")
            patrimonio_sucessao = st.number_input(
                "Patrimônio estimado para sucessão (R$)",
                min_value=0.0,
                value=float(
                    prospect.get("estrutura_patrimonial", {}).get("patrimonio_sucessao", 0)
                    if isinstance(prospect.get("estrutura_patrimonial"), dict) else 0
                ),
                step=100000.0,
                format="%.2f",
                key="patrimonio_sucessao",
            )

            # Family insights
            _show_family_insights(family_edited, patrimonio_sucessao)

        # ── TAB 4: Estrutura Patrimonial ──
        with tabs[3]:
            st.markdown(
                f'<p style="color:{TAG["text_muted"]};font-size:0.9rem">'
                f"Defina a estrutura patrimonial atual do prospect (tipo de pessoa/entidade, offshore, holdings)."
                f"</p>",
                unsafe_allow_html=True,
            )

            estr_patrim = prospect.get("estrutura_patrimonial", {})
            if not isinstance(estr_patrim, dict):
                estr_patrim = {}

            col1, col2 = st.columns(2)
            with col1:
                tipo_estr_idx = 0
                tipo_estr_val = estr_patrim.get("tipo", "Pessoa Física")
                if tipo_estr_val in TIPOS_ESTRUTURA:
                    tipo_estr_idx = TIPOS_ESTRUTURA.index(tipo_estr_val)
                tipo_estrutura = st.selectbox(
                    "Tipo de estrutura",
                    TIPOS_ESTRUTURA,
                    index=tipo_estr_idx,
                    key="tipo_estrutura",
                )
            with col2:
                possui_offshore = st.checkbox(
                    "Possui estrutura offshore",
                    value=estr_patrim.get("possui_offshore", False),
                    key="possui_offshore",
                )

            # Offshore details
            if possui_offshore or tipo_estrutura == "Offshore":
                st.markdown("**Detalhes Offshore**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    jur_idx = 0
                    jur_val = estr_patrim.get("jurisdicao", JURISDICOES_OFFSHORE[0])
                    if jur_val in JURISDICOES_OFFSHORE:
                        jur_idx = JURISDICOES_OFFSHORE.index(jur_val)
                    jurisdicao = st.selectbox(
                        "Jurisdição",
                        JURISDICOES_OFFSHORE,
                        index=jur_idx,
                        key="jurisdicao",
                    )
                with col2:
                    tipo_off_idx = 0
                    tipo_off_val = estr_patrim.get("tipo_offshore", TIPOS_OFFSHORE[0])
                    if tipo_off_val in TIPOS_OFFSHORE:
                        tipo_off_idx = TIPOS_OFFSHORE.index(tipo_off_val)
                    tipo_offshore = st.selectbox(
                        "Tipo de veículo",
                        TIPOS_OFFSHORE,
                        index=tipo_off_idx,
                        key="tipo_offshore",
                    )
                with col3:
                    patrimonio_offshore = st.number_input(
                        "Patrimônio offshore (USD)",
                        min_value=0.0,
                        value=float(estr_patrim.get("patrimonio_offshore", 0)),
                        step=100000.0,
                        format="%.2f",
                        key="patrimonio_offshore",
                    )
            else:
                jurisdicao = ""
                tipo_offshore = ""
                patrimonio_offshore = 0.0

            st.markdown("---")

            # Holdings
            st.markdown("**Holdings / PICs**")
            holdings_texto = st.text_area(
                "Descreva as holdings, PICs ou estruturas societárias existentes",
                value=estr_patrim.get("holdings_texto", ""),
                placeholder="Ex: Holding ABC Ltda. detém 60% dos imóveis, PIC na BVI controla ativos internacionais...",
                key="holdings_texto",
            )

            st.markdown("---")

            # Plano sucessório
            st.markdown("**Plano Sucessório Atual**")
            plano = prospect.get("plano_sucessorio", {})
            if not isinstance(plano, dict):
                plano = {}

            col1, col2 = st.columns(2)
            with col1:
                tem_testamento = st.checkbox("Possui testamento", value=plano.get("testamento", False), key="tem_testamento")
                tem_doacao = st.checkbox("Doação em adiantamento de legítima", value=plano.get("doacao_antecipada", False), key="tem_doacao")
                tem_seguro = st.checkbox("Seguro de vida / Previdência", value=plano.get("seguro_vida", False), key="tem_seguro")
            with col2:
                tem_trust = st.checkbox("Trust / PIC", value=plano.get("trust", False), key="tem_trust")
                tem_holding = st.checkbox("Holding familiar constituída", value=plano.get("holding_familiar", False), key="tem_holding")
                tem_protocolo = st.checkbox("Protocolo familiar", value=plano.get("protocolo_familiar", False), key="tem_protocolo")

            obs_sucessorio = st.text_area(
                "Observações sobre planejamento sucessório",
                value=plano.get("observacoes", ""),
                placeholder="Ex: Herdeiros menores de idade, conflito entre sócios, regime de separação...",
                key="obs_sucessorio",
            )

        # ── TAB 5: Fee / Proposta Comercial ──
        with tabs[4]:
            st.markdown(
                f'<p style="color:{TAG["text_muted"]};font-size:0.9rem">'
                f"Configure a taxa de administração negociada e os serviços incluídos na proposta."
                f"</p>",
                unsafe_allow_html=True,
            )

            fee_data = prospect.get("fee_negociada", {})
            if not isinstance(fee_data, dict):
                fee_data = {}

            st.markdown("**Taxa de Administração**")
            col1, col2 = st.columns(2)
            with col1:
                taxa_adm_1 = st.number_input(
                    "Taxa até R$ 500 milhões (% a.a.)",
                    min_value=0.0,
                    max_value=5.0,
                    value=float(fee_data.get("taxa_ate_500m", 0.25)),
                    step=0.01,
                    format="%.2f",
                    key="taxa_adm_1",
                )
            with col2:
                taxa_adm_2 = st.number_input(
                    "Taxa acima de R$ 500 milhões (% a.a.)",
                    min_value=0.0,
                    max_value=5.0,
                    value=float(fee_data.get("taxa_acima_500m", 0.20)),
                    step=0.01,
                    format="%.2f",
                    key="taxa_adm_2",
                )

            taxa_performance = st.number_input(
                "Taxa de performance (%, se houver)",
                min_value=0.0,
                max_value=50.0,
                value=float(fee_data.get("taxa_performance", 0.0)),
                step=1.0,
                format="%.1f",
                key="taxa_performance",
            )

            # Fee revenue estimate
            if patrimonio_investivel > 0:
                fee_rate = taxa_adm_1 if patrimonio_investivel <= 500_000_000 else taxa_adm_2
                annual_fee = patrimonio_investivel * fee_rate / 100
                monthly_fee = annual_fee / 12
                st.markdown(
                    f'<div class="tag-card" style="padding:12px 16px;margin-top:8px">'
                    f'<div style="color:{TAG["laranja"]};font-weight:600;font-size:0.85rem;margin-bottom:6px">'
                    f'💰 Estimativa de Receita</div>'
                    f'<div style="display:flex;gap:24px">'
                    f'<div><span style="color:{TAG["text_muted"]};font-size:0.78rem">Anual:</span> '
                    f'<span style="color:{TAG["offwhite"]};font-weight:600">{fmt_brl(annual_fee)}</span></div>'
                    f'<div><span style="color:{TAG["text_muted"]};font-size:0.78rem">Mensal:</span> '
                    f'<span style="color:{TAG["offwhite"]};font-weight:600">{fmt_brl(monthly_fee)}</span></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            st.markdown("**Serviços Incluídos**")
            current_servicos = fee_data.get("servicos", []) if isinstance(fee_data.get("servicos"), list) else []
            servicos = st.multiselect(
                "Selecione os serviços incluídos na proposta",
                SERVICOS_DISPONIVEIS,
                default=[s for s in current_servicos if s in SERVICOS_DISPONIVEIS],
                key="servicos_incluidos",
            )

            st.markdown("---")
            st.markdown("**Condições Especiais**")
            condicoes_especiais = st.text_area(
                "Condições ou observações comerciais",
                value=fee_data.get("condicoes_especiais", ""),
                placeholder="Ex: Isenção de fee no primeiro trimestre, fee regressivo após 3 anos...",
                key="condicoes_especiais",
            )

        # ── TAB 6: Pipeline ──
        with tabs[5]:
            col1, col2 = st.columns([1, 3])
            with col1:
                status_idx = PIPELINE_STATUS.index(prospect.get("status", "Lead")) if prospect.get("status") in PIPELINE_STATUS else 0
                status = st.selectbox("Status", PIPELINE_STATUS, index=status_idx)
            with col2:
                observacoes = st.text_area(
                    "Observações gerais",
                    value=prospect.get("observacoes", ""),
                    placeholder="Contexto adicional sobre o prospect, origem do lead, etc.",
                )

        # ── Submit ──
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button(
                "Salvar Prospect" if not editing else "Atualizar Prospect",
                type="primary",
                use_container_width=True,
            )
        with col2:
            if editing:
                delete_btn = st.form_submit_button(
                    "Excluir",
                    use_container_width=True,
                )
            else:
                delete_btn = False

    # ── Handle submission ──
    if submitted:
        # Validate fields before saving
        errors = _validate_all_fields(nome, cpf_cnpj, email, telefone)
        if errors:
            for err in errors:
                st.error(err)
            return

        # Build family list from data_editor
        family_list = []
        if family_edited is not None and not family_edited.empty:
            for _, row in family_edited.iterrows():
                if row.get("nome") and str(row["nome"]).strip():
                    family_list.append({
                        "nome": str(row["nome"]).strip(),
                        "relacao": str(row.get("relacao", "Outro")),
                        "idade": int(row.get("idade", 0)),
                        "regime_casamento": str(row.get("regime_casamento", "N/A")),
                    })

        # Build estrutura_patrimonial
        estrutura_patrim = {
            "tipo": tipo_estrutura,
            "possui_offshore": possui_offshore or tipo_estrutura == "Offshore",
            "jurisdicao": jurisdicao,
            "tipo_offshore": tipo_offshore,
            "patrimonio_offshore": patrimonio_offshore,
            "holdings_texto": holdings_texto,
            "patrimonio_sucessao": patrimonio_sucessao,
        }

        # Build plano_sucessorio
        plano_suc = {
            "testamento": tem_testamento,
            "doacao_antecipada": tem_doacao,
            "seguro_vida": tem_seguro,
            "trust": tem_trust,
            "holding_familiar": tem_holding,
            "protocolo_familiar": tem_protocolo,
            "observacoes": obs_sucessorio,
        }

        # Build fee_negociada
        fee_neg = {
            "taxa_ate_500m": taxa_adm_1,
            "taxa_acima_500m": taxa_adm_2,
            "taxa_performance": taxa_performance,
            "servicos": servicos,
            "condicoes_especiais": condicoes_especiais,
        }

        # Format validated fields
        _, cpf_formatted, _, _ = validate_cpf_cnpj(cpf_cnpj)
        _, _, phone_formatted, _ = True, True, telefone.strip(), ""
        try:
            _, phone_formatted, _ = validate_phone(telefone)
        except Exception:
            phone_formatted = telefone.strip()

        data = {
            "nome": nome.strip(),
            "cpf_cnpj": cpf_formatted if cpf_formatted else cpf_cnpj.strip(),
            "email": email.strip().lower() if email else "",
            "telefone": phone_formatted if phone_formatted else telefone.strip(),
            "tipo_pessoa": tipo_pessoa,
            "perfil_investidor": perfil,
            "patrimonio_total": patrimonio_total,
            "patrimonio_investivel": patrimonio_investivel,
            "horizonte_investimento": horizonte,
            "objetivos": objetivos,
            "retirada_mensal": retirada,
            "restricoes": restricoes,
            "restricoes_texto": restricoes_texto,
            "observacoes": observacoes,
            "status": status,
            "responsavel": responsavel.strip(),
            "estrutura_familiar": family_list,
            "estrutura_patrimonial": estrutura_patrim,
            "plano_sucessorio": plano_suc,
            "fee_negociada": fee_neg,
        }

        if editing:
            update_prospect(prospect_id, data)
            st.success(f"Prospect **{nome}** atualizado com sucesso!")
        else:
            new_id = create_prospect(data)
            st.success(f"Prospect **{nome}** cadastrado com sucesso! (ID: {new_id})")
        st.rerun()

    if delete_btn and editing:
        from database.models import delete_prospect
        delete_prospect(prospect_id)
        st.success(f"Prospect excluído.")
        st.rerun()

    # ── Preview card ──
    if editing and prospect:
        st.markdown("---")
        st.subheader("Resumo do Prospect")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Patrimônio Investível", fmt_brl(prospect.get("patrimonio_investivel", 0)))
        with col2:
            st.metric("Perfil", prospect.get("perfil_investidor", "N/A"))
        with col3:
            st.metric("Status", prospect.get("status", "Lead"))
        with col4:
            st.metric("Retirada Mensal", fmt_brl(prospect.get("retirada_mensal", 0)))

        # Family summary
        family = prospect.get("estrutura_familiar", [])
        if family and isinstance(family, list) and any(m.get("nome") for m in family):
            st.markdown("**Estrutura Familiar:**")
            for m in family:
                if m.get("nome"):
                    st.markdown(f"- {m['nome']} ({m.get('relacao', '')}, {m.get('idade', '?')} anos)")

        # Fee summary
        fee = prospect.get("fee_negociada", {})
        if isinstance(fee, dict) and fee.get("taxa_ate_500m"):
            st.markdown(
                f"**Fee negociada:** {fee.get('taxa_ate_500m', 0.25):.2f}% "
                f"(até R$500M) / {fee.get('taxa_acima_500m', 0.20):.2f}% (acima)"
            )

        if prospect.get("restricoes"):
            st.markdown(
                f"**Restrições:** {', '.join(prospect['restricoes'])}"
            )
        if prospect.get("restricoes_texto"):
            st.markdown(f"**Observações de restrição:** {prospect['restricoes_texto']}")


# ═══════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════

def _validate_all_fields(nome, cpf_cnpj, email, telefone):
    """Validate all fields and return list of error messages."""
    errors = []

    # Nome obrigatório
    if not nome or not nome.strip():
        errors.append("❌ Nome é obrigatório.")

    # CPF/CNPJ
    if cpf_cnpj and cpf_cnpj.strip():
        is_valid, _, err_msg, _ = validate_cpf_cnpj(cpf_cnpj)
        if not is_valid:
            errors.append(f"❌ {err_msg}")

    # Email
    if email and email.strip():
        is_valid, err_msg = validate_email(email)
        if not is_valid:
            errors.append(f"❌ {err_msg}")

    # Telefone
    if telefone and telefone.strip():
        is_valid, _, err_msg = validate_phone(telefone)
        if not is_valid:
            errors.append(f"❌ {err_msg}")

    return errors


def _show_field_validations(cpf_cnpj, email, telefone):
    """Show real-time field validation feedback."""
    validation_msgs = []

    # CPF/CNPJ validation
    if cpf_cnpj and cpf_cnpj.strip():
        is_valid, formatted, err_msg, tipo = validate_cpf_cnpj(cpf_cnpj)
        if is_valid and formatted:
            validation_msgs.append(
                f'<span style="color:{TAG["verde"]};font-size:0.78rem">'
                f'✅ {tipo} válido: {formatted}</span>'
            )
        elif not is_valid:
            validation_msgs.append(
                f'<span style="color:{TAG["rosa"]};font-size:0.78rem">'
                f'❌ {err_msg}</span>'
            )

    # Email validation
    if email and email.strip():
        is_valid, err_msg = validate_email(email)
        if is_valid:
            validation_msgs.append(
                f'<span style="color:{TAG["verde"]};font-size:0.78rem">'
                f'✅ Email válido</span>'
            )
        else:
            validation_msgs.append(
                f'<span style="color:{TAG["rosa"]};font-size:0.78rem">'
                f'❌ {err_msg}</span>'
            )

    # Phone validation
    if telefone and telefone.strip():
        is_valid, formatted, err_msg = validate_phone(telefone)
        if is_valid and formatted:
            validation_msgs.append(
                f'<span style="color:{TAG["verde"]};font-size:0.78rem">'
                f'✅ Telefone: {formatted}</span>'
            )
        elif not is_valid:
            validation_msgs.append(
                f'<span style="color:{TAG["rosa"]};font-size:0.78rem">'
                f'❌ {err_msg}</span>'
            )

    if validation_msgs:
        st.markdown(
            f'<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:4px">'
            + "".join(validation_msgs)
            + f'</div>',
            unsafe_allow_html=True,
        )


def _show_profile_hints(perfil, objetivos, horizonte):
    """Show hints when profile/objectives don't match well."""
    hints = []

    if perfil == "Conservador":
        if "Crescimento patrimonial" in objetivos and "Preservação de capital" not in objetivos:
            hints.append(
                "Perfil Conservador com objetivo de crescimento patrimonial sem preservação de capital "
                "pode gerar expectativas desalinhadas."
            )
        if horizonte and "Muito Longo" in horizonte:
            hints.append(
                "Horizonte muito longo prazo com perfil Conservador: considere se Moderado seria mais adequado."
            )

    if perfil == "Agressivo":
        if "Preservação de capital" in objetivos and "Crescimento patrimonial" not in objetivos:
            hints.append(
                "Perfil Agressivo focado apenas em preservação: considere se perfil Moderado seria mais adequado."
            )
        if horizonte and "Curto" in horizonte:
            hints.append(
                "Perfil Agressivo com horizonte curto prazo pode gerar volatilidade excessiva."
            )

    if "Geração de renda" in objetivos and horizonte and "Curto" in horizonte:
        hints.append(
            "Geração de renda com horizonte curto prazo: foco em fundos de crédito e renda fixa."
        )

    if hints:
        st.markdown(
            f'<div style="background:{TAG["amarelo"]}15;border:1px solid {TAG["amarelo"]}30;'
            f'border-radius:8px;padding:10px 14px;margin-top:12px">'
            f'<div style="color:{TAG["amarelo"]};font-weight:600;font-size:0.82rem;margin-bottom:6px">'
            f'💡 Dicas de Consistência</div>',
            unsafe_allow_html=True,
        )
        for h in hints:
            st.markdown(
                f'<div style="color:{TAG["text_muted"]};font-size:0.78rem;margin-bottom:4px">'
                f'• {h}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


def _show_family_insights(family_df, patrimonio_sucessao):
    """Show insights about family structure."""
    if family_df is None or family_df.empty:
        return

    members = []
    for _, row in family_df.iterrows():
        if row.get("nome") and str(row["nome"]).strip():
            members.append(row)

    if not members:
        return

    insights = []

    # Count by relationship
    n_filhos = sum(1 for m in members if str(m.get("relacao", "")).startswith("Filho"))
    n_conjuge = sum(1 for m in members if str(m.get("relacao", "")) == "Cônjuge")
    n_netos = sum(1 for m in members if str(m.get("relacao", "")).startswith("Neto"))

    # Minor heirs check
    menores = [m for m in members if int(m.get("idade", 0)) < 18 and int(m.get("idade", 0)) > 0]
    if menores:
        insights.append(
            f"⚠️ {len(menores)} herdeiro(s) menor(es) de idade - considerar tutela e curadoria."
        )

    # Multiple marriages / regimes
    regimes = set(
        str(m.get("regime_casamento", "N/A"))
        for m in members
        if str(m.get("relacao", "")) == "Cônjuge"
    )
    regimes.discard("N/A")
    if regimes:
        insights.append(
            f"Regime de casamento: {', '.join(regimes)}. "
            f"Verificar comunicabilidade de bens para planejamento."
        )

    # Succession estimate
    if patrimonio_sucessao > 0 and n_filhos > 0:
        per_heir = patrimonio_sucessao / (n_filhos + (1 if n_conjuge else 0))
        insights.append(
            f"Estimativa por herdeiro (divisão igualitária): ~{fmt_brl(per_heir)}"
        )

    if insights:
        st.markdown(
            f'<div style="background:{TAG["azul"]}15;border:1px solid {TAG["azul"]}30;'
            f'border-radius:8px;padding:10px 14px;margin-top:12px">'
            f'<div style="color:{TAG["azul"]};font-weight:600;font-size:0.82rem;margin-bottom:6px">'
            f'📋 Insights Familiares</div>',
            unsafe_allow_html=True,
        )
        for insight in insights:
            st.markdown(
                f'<div style="color:{TAG["text_muted"]};font-size:0.78rem;margin-bottom:4px">'
                f'• {insight}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


def _render_completeness_badge(prospect):
    """Show a completeness score badge for existing prospects."""
    score, missing, recommendations = validate_prospect_completeness(prospect)

    if score >= 90:
        color = TAG["verde"]
        icon = "🟢"
        label = "Completo"
    elif score >= 70:
        color = TAG["azul"]
        icon = "🔵"
        label = "Bom"
    elif score >= 50:
        color = TAG["amarelo"]
        icon = "🟡"
        label = "Parcial"
    else:
        color = TAG["rosa"]
        icon = "🔴"
        label = "Incompleto"

    # Badge row
    bar_width = max(score, 3)

    st.markdown(
        f'<div style="background:{TAG["bg_card"]};border:1px solid {color}40;'
        f'border-radius:10px;padding:12px 16px;margin-bottom:16px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
        f'<div style="color:{TAG["offwhite"]};font-weight:600;font-size:0.9rem">'
        f'{icon} Cadastro {label}</div>'
        f'<div style="color:{color};font-weight:700;font-size:1.1rem">{score}%</div>'
        f'</div>'
        f'<div style="background:{TAG["bg_dark"]};border-radius:6px;height:6px;overflow:hidden">'
        f'<div style="width:{bar_width}%;height:100%;background:{color};border-radius:6px;'
        f'transition:width 0.3s"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if missing:
        st.markdown(
            f'<div style="color:{TAG["text_muted"]};font-size:0.75rem;margin-top:6px">'
            f'Campos pendentes: {", ".join(missing[:5])}'
            + (f" +{len(missing)-5} mais" if len(missing) > 5 else "")
            + f'</div>',
            unsafe_allow_html=True,
        )

    if recommendations:
        for rec in recommendations[:2]:
            st.markdown(
                f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">'
                f'💡 {rec}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)


def _init_family_state(prospect):
    """Initialize session state for family editor."""
    if "family_initialized" not in st.session_state:
        st.session_state.family_initialized = True
