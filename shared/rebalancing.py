"""
Rebalancing engine: adherence analysis and smart plan generation.
"""
from datetime import datetime, timedelta

import pandas as pd

from shared.fund_utils import find_col, match_fund_liquidation
from shared.date_utils import add_business_days, compute_settle_date, compute_latest_request_date
from shared.portfolio_utils import apply_movement, build_cash_flow_timeline


def build_adherence_analysis(ativos_df, model_df, all_movements, caixa_initial, pl_total):
    """Compare portfolio (after movements) with model. Returns (df, info)."""
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    positions = {}
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        name = str(row.get("ATIVO", ""))
        fin = float(row.get("FINANCEIRO", 0))
        positions[code] = {"name": name, "financeiro": fin, "code": code}

    caixa = caixa_initial
    for mov in all_movements:
        fund_code = str(mov.get("fund_code", ""))
        caixa = apply_movement(mov["operation"], mov["value"], fund_code, positions, caixa)

    total_after = sum(p["financeiro"] for p in positions.values()) + caixa

    rows = []
    model_codes = set()

    for _, model_row in model_df.iterrows():
        m_code = str(model_row["Código"]).strip()
        m_name = str(model_row["Ativo"]).strip()
        m_pct_alvo = float(model_row["% Alvo"])
        model_codes.add(m_code)

        matched_pos = None
        if m_code in positions:
            matched_pos = positions[m_code]
        else:
            for code, pos in positions.items():
                if m_name.upper()[:15] in pos["name"].upper() or pos["name"].upper()[:15] in m_name.upper():
                    matched_pos = pos
                    model_codes.add(code)
                    break

        fin_atual = matched_pos["financeiro"] if matched_pos else 0
        pct_atual = (fin_atual / total_after * 100) if total_after > 0 else 0
        gap_pct = m_pct_alvo - pct_atual
        gap_rs = gap_pct / 100 * total_after

        if abs(gap_pct) < 0.1:
            acao = "OK"
        elif gap_pct > 0:
            acao = f"Aplicar R$ {abs(gap_rs):,.0f}"
        else:
            acao = f"Resgatar R$ {abs(gap_rs):,.0f}"

        rows.append({
            "Ativo": m_name[:45],
            "Código": m_code,
            "Financeiro Projetado": fin_atual,
            "% Atual (Pós-Mov.)": round(pct_atual, 2),
            "% Alvo (Modelo)": round(m_pct_alvo, 2),
            "Gap (p.p.)": round(gap_pct, 2),
            "Gap (R$)": round(gap_rs, 2),
            "Ação Sugerida": acao,
        })

    for code, pos in positions.items():
        if code not in model_codes and pos["financeiro"] > 100:
            pct_atual = (pos["financeiro"] / total_after * 100) if total_after > 0 else 0
            if pct_atual > 0.05:
                rows.append({
                    "Ativo": pos["name"][:45],
                    "Código": code,
                    "Financeiro Projetado": pos["financeiro"],
                    "% Atual (Pós-Mov.)": round(pct_atual, 2),
                    "% Alvo (Modelo)": 0.0,
                    "Gap (p.p.)": round(-pct_atual, 2),
                    "Gap (R$)": round(-pos["financeiro"], 2),
                    "Ação Sugerida": f"Resgatar R$ {pos['financeiro']:,.0f} (fora do modelo)",
                })

    caixa_pct = (caixa / total_after * 100) if total_after > 0 else 0
    caixa_target = 100 - model_df["% Alvo"].sum()
    caixa_gap = caixa_target - caixa_pct
    rows.append({
        "Ativo": "CAIXA",
        "Código": "CAIXA",
        "Financeiro Projetado": caixa,
        "% Atual (Pós-Mov.)": round(caixa_pct, 2),
        "% Alvo (Modelo)": round(max(0, caixa_target), 2),
        "Gap (p.p.)": round(caixa_gap, 2),
        "Gap (R$)": round(caixa_gap / 100 * total_after, 2),
        "Ação Sugerida": "Residual" if abs(caixa_gap) < 1 else ("Excesso" if caixa_gap < -1 else "Déficit"),
    })

    df = pd.DataFrame(rows)
    info = {
        "pl_projetado": total_after,
        "caixa_projetado": caixa,
        "total_aplicar": sum(r["Gap (R$)"] for r in rows if r["Gap (R$)"] > 0 and r["Código"] != "CAIXA"),
        "total_resgatar": sum(abs(r["Gap (R$)"]) for r in rows if r["Gap (R$)"] < 0 and r["Código"] != "CAIXA"),
    }
    return df, info


def generate_smart_rebalancing_plan(
    adherence_df, liquid_df, all_movements, caixa_initial,
    ativos_df, cash_fund_codes, today=None
):
    """Generate a rebalancing plan that guarantees cash never goes negative."""
    if today is None:
        today = pd.Timestamp(datetime.today().date())
    else:
        today = pd.Timestamp(today)

    warnings = []

    def _add_plan_entry(plan_rows, plan_movs, fund, op, amount, req_date, settle_date, motivo, source):
        d_str = (
            f"D+{fund['d_conv']}+{fund['d_liq']} ({fund['contagem']})"
            if op == "Resgate"
            else f"D+{fund['d_conv_aplic']}"
        )
        plan_rows.append({
            "Prioridade": 0,
            "Ativo": fund["name"],
            "Código": fund["code"],
            "Operação": op,
            "Valor (R$)": round(amount, 2),
            "D+": d_str,
            "Data Solicitação": req_date.strftime("%d/%m/%Y"),
            "Data Liquidação": settle_date.strftime("%d/%m/%Y"),
            "Motivo": motivo,
            "De % Atual": fund["pct_atual"],
            "Para % Alvo": fund["pct_alvo"],
        })
        plan_movs.append({
            "fund_name": fund["name"],
            "fund_code": fund["code"],
            "operation": op,
            "value": round(amount, 2),
            "request_date": req_date,
            "liquidation_date": settle_date,
            "description": f"Plano: {op} {fund['name'][:30]} ({motivo[:30]})",
            "source": source,
        })

    plan_rows = []
    plan_movements = []

    # FASE 0: Catálogo de Fundos
    catalog = {}
    for _, row in adherence_df.iterrows():
        code = str(row["Código"])
        if code == "CAIXA":
            continue
        name = row["Ativo"]
        gap_rs = row["Gap (R$)"]
        financeiro = row.get("Financeiro Projetado", 0)
        liq_info = match_fund_liquidation(name, code, liquid_df)
        if liq_info is not None:
            d_conv = int(liq_info["Conversão Resgate"])
            d_liq = int(liq_info["Liquid. Resgate"])
            contagem = str(liq_info.get("Contagem Resgate", "Úteis"))
            if contagem not in ["Úteis", "Corridos"]:
                contagem = "Úteis"
            d_conv_aplic = int(liq_info["Conversão Aplic."])
        else:
            d_conv, d_liq, contagem = 0, 0, "Úteis"
            d_conv_aplic = 0

        catalog[code] = {
            "code": code, "name": name, "gap_rs": gap_rs,
            "financeiro": financeiro, "available_fin": max(0, financeiro),
            "d_conv": d_conv, "d_liq": d_liq, "contagem": contagem,
            "d_conv_aplic": d_conv_aplic, "d_total": d_conv + d_liq,
            "is_overweight": gap_rs < -100, "is_underweight": gap_rs > 100,
            "is_cash": code in cash_fund_codes,
            "max_model_resgate": abs(gap_rs) if gap_rs < -100 else 0,
            "pct_atual": row["% Atual (Pós-Mov.)"],
            "pct_alvo": row["% Alvo (Modelo)"],
            "already_redeemed": 0.0,
            "already_applied": 0.0,
        }

    # FASE 1: Cash event map from existing movements
    cash_events = {}
    effective_cash = caixa_initial
    if ativos_df is not None and not ativos_df.empty:
        cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")
        if cod_col:
            for _, row in ativos_df.iterrows():
                code = str(row[cod_col])
                if code in cash_fund_codes:
                    effective_cash += float(row.get("FINANCEIRO", 0))

    passivo_dates = {}
    if all_movements:
        for m in all_movements:
            liq_date = pd.Timestamp(m["liquidation_date"]) if pd.notna(m.get("liquidation_date")) else None
            if liq_date is None or liq_date < today:
                continue
            op = m["operation"]
            val = m["value"]
            fund_code = str(m.get("fund_code", ""))
            is_cash_fund = fund_code in cash_fund_codes

            impact = 0.0
            if op == "Resgate Passivo":
                impact = -val
                passivo_dates.setdefault(liq_date, 0.0)
                passivo_dates[liq_date] += val
            elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
                impact = 0.0 if is_cash_fund else +val
            elif "Aplicação" in op:
                impact = 0.0 if is_cash_fund else -val
            elif op == "Débito/Passivo":
                impact = -val
            elif op == "Crédito (Provisão)":
                impact = +val

            if impact != 0:
                cash_events.setdefault(liq_date, 0.0)
                cash_events[liq_date] += impact

    # FASE 2: Cover passive redemptions
    passivos_sorted = sorted(passivo_dates.items(), key=lambda x: x[0])

    def cash_at_date(target_date):
        running = effective_cash
        for d in sorted(cash_events.keys()):
            if d <= target_date:
                running += cash_events[d]
        return running

    for passivo_date, passivo_value in passivos_sorted:
        cash_before = cash_at_date(passivo_date)
        if cash_before >= 0:
            continue

        deficit = abs(cash_before)
        candidates = []
        for code, fund in catalog.items():
            if fund["is_cash"]:
                continue
            remaining = fund["available_fin"] - fund["already_redeemed"]
            if remaining < 100:
                continue
            req_date = compute_latest_request_date(
                passivo_date, fund["d_conv"], fund["d_liq"], fund["contagem"]
            )
            if req_date < today:
                continue
            settle = compute_settle_date(req_date, fund["d_conv"], fund["d_liq"], fund["contagem"])
            candidates.append({
                "code": code, "fund": fund, "request_date": req_date,
                "settle_date": settle, "remaining": remaining,
                "is_overweight": fund["is_overweight"],
                "model_resgate": max(0, fund["max_model_resgate"] - fund["already_redeemed"]),
            })

        candidates.sort(key=lambda c: (0 if c["is_overweight"] else 1, c["fund"]["d_total"]))

        still_needed = deficit
        for cand in candidates:
            if still_needed <= 0:
                break
            fund = cand["fund"]
            actual_remaining = fund["available_fin"] - fund["already_redeemed"]
            if cand["is_overweight"] and cand["model_resgate"] > 0:
                amount = min(still_needed, cand["model_resgate"], actual_remaining)
            else:
                amount = min(still_needed, actual_remaining)
            if amount < 100:
                continue

            _add_plan_entry(
                plan_rows, plan_movements, fund, "Resgate", amount,
                cand["request_date"], cand["settle_date"],
                f"Cobertura passivo {passivo_date.strftime('%d/%m')}",
                "plano_cobertura_passivo",
            )
            fund["already_redeemed"] += amount
            cash_events.setdefault(cand["settle_date"], 0.0)
            cash_events[cand["settle_date"]] += amount
            still_needed -= amount

        if still_needed > 100:
            warnings.append({
                "level": "error",
                "message": (
                    f"Impossivel cobrir passivo de R$ {passivo_value:,.0f} em "
                    f"{passivo_date.strftime('%d/%m/%Y')}: deficit de R$ {still_needed:,.0f}."
                ),
            })

    # FASE 3: Rebalancing resgates (overweight)
    for code, fund in catalog.items():
        if not fund["is_overweight"]:
            continue
        remaining_gap = fund["max_model_resgate"] - fund["already_redeemed"]
        if remaining_gap < 100:
            continue

        req_date = today
        settle_date = compute_settle_date(req_date, fund["d_conv"], fund["d_liq"], fund["contagem"])
        _add_plan_entry(
            plan_rows, plan_movements, fund, "Resgate", remaining_gap,
            req_date, settle_date, "Rebalanceamento (acima do modelo)",
            "plano_rebalanceamento",
        )
        fund["already_redeemed"] += remaining_gap
        if not fund["is_cash"]:
            cash_events.setdefault(settle_date, 0.0)
            cash_events[settle_date] += remaining_gap

    # FASE 4: Applications with day-by-day cash check
    all_event_dates = sorted(cash_events.keys())
    if not all_event_dates:
        last_event = today + timedelta(days=5)
    else:
        last_event = max(all_event_dates) + timedelta(days=5)

    daily_cash = {}
    running = effective_cash
    current = today
    while current <= last_event:
        if current.weekday() < 5:
            running += cash_events.get(current, 0)
            daily_cash[current] = running
        current += timedelta(days=1)

    underweight_funds = [
        (code, fund) for code, fund in catalog.items() if fund["is_underweight"]
    ]
    underweight_funds.sort(key=lambda x: (0 if x[1]["is_cash"] else 1, -x[1]["gap_rs"]))

    sorted_days = sorted(daily_cash.keys())

    plan_outflows = {}

    for code, fund in underweight_funds:
        gap = fund["gap_rs"] - fund["already_applied"]
        if gap < 100:
            continue

        if fund["is_cash"]:
            best_date = today
            settle_date = add_business_days(best_date, fund["d_conv_aplic"], "Úteis")
            _add_plan_entry(
                plan_rows, plan_movements, fund, "Aplicação", gap,
                best_date, settle_date, "Rebalanceamento (abaixo do modelo)",
                "plano_rebalanceamento",
            )
            fund["already_applied"] += gap
            continue

        best_date = None
        for d in sorted_days:
            if d < today:
                continue
            planned_out = sum(v for dd, v in plan_outflows.items() if dd <= d)
            available = daily_cash[d] - planned_out
            future_ok = True
            for fd in sorted_days:
                if fd >= d:
                    future_planned = sum(v for dd, v in plan_outflows.items() if dd <= fd)
                    if daily_cash[fd] - future_planned - gap < -1:
                        future_ok = False
                        break
            if available >= gap and future_ok:
                best_date = d
                break

        if best_date is None:
            for d in sorted_days:
                if d < today:
                    continue
                planned_out = sum(v for dd, v in plan_outflows.items() if dd <= d)
                available = daily_cash[d] - planned_out
                min_fut = float("inf")
                for fd in sorted_days:
                    if fd >= d:
                        future_planned = sum(v for dd, v in plan_outflows.items() if dd <= fd)
                        min_fut = min(min_fut, daily_cash[fd] - future_planned)
                max_amount = min(gap, available, min_fut)
                if max_amount >= 100:
                    gap = max_amount
                    best_date = d
                    break

        if best_date is None or gap < 100:
            continue

        settle_date = add_business_days(best_date, fund["d_conv_aplic"], "Úteis")
        _add_plan_entry(
            plan_rows, plan_movements, fund, "Aplicação", gap,
            best_date, settle_date, "Rebalanceamento (abaixo do modelo)",
            "plano_rebalanceamento",
        )
        fund["already_applied"] += gap
        plan_outflows.setdefault(best_date, 0.0)
        plan_outflows[best_date] += gap

    # FASE 5: Final validation
    if plan_movements and ativos_df is not None and not ativos_df.empty:
        combined = (all_movements or []) + plan_movements
        df_check, _ = build_cash_flow_timeline(
            caixa_initial, ativos_df, combined, cash_fund_codes
        )
        if not df_check.empty:
            neg_days = df_check[df_check["Negativo"]]
            if not neg_days.empty:
                for _, neg_row in neg_days.iterrows():
                    warnings.append({
                        "level": "error",
                        "message": (
                            f"Caixa negativo em {neg_row['Data'].strftime('%d/%m/%Y')}: "
                            f"R$ {neg_row['Saldo (R$)']:,.0f}"
                        ),
                    })

    plan_df = pd.DataFrame(plan_rows)
    if not plan_df.empty:
        motivo_order = plan_df["Motivo"].apply(
            lambda m: 0 if "passivo" in m.lower() else (1 if "acima" in m.lower() else 2)
        )
        plan_df["_sort"] = motivo_order * 10 + plan_df["Operação"].map(
            {"Resgate": 0, "Aplicação": 5}
        ).fillna(3)
        plan_df = plan_df.sort_values(
            ["_sort", "Data Liquidação", "Valor (R$)"], ascending=[True, True, False]
        )
        plan_df["Prioridade"] = range(1, len(plan_df) + 1)
        plan_df = plan_df.drop(columns=["_sort"])

    return plan_df, plan_movements, warnings
