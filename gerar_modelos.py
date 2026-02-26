"""
Script para gerar os arquivos Excel das carteiras modelo TAG por perfil.
Dados extraídos da tabela oficial GFF.
Executar uma vez: python gerar_modelos.py
"""
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "modelos_carteira")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Dados completos da tabela de carteiras modelo ──
MODELO_COMPLETO = [
    # (Classe Ativo, Subcategoria, Ativo/Fundo, RF_hoje, Cons_hoje, Mod_hoje, Agr_hoje, RF_min, RF_max, Cons_min, Cons_max, Mod_min, Mod_max, Agr_min, Agr_max)
    ("LOCAL CAIXA", "TPF", "PORTO SIMPLES", 25.0, 15.0, 15.0, 7.5, 0, 100, 0, 100, 0, 100, 0, 100),
    ("LOCAL CAIXA", "CRÉDITO D0", "BNP MATCH DI", 20.0, 5.0, 0.0, 0.0, 0, 100, 0, 100, 0, 100, 0, 100),
    ("LOCAL RENDA FIXA PÓS", "CRÉDITO HG", "LCI/LCA 95% CDI", 5.0, 0.0, 0.0, 0.0, 0, 50, 0, 50, 0, 50, 0, 50),
    ("LOCAL RENDA FIXA PÓS", "CRÉDITO FIDC", "TITAN", 10.0, 20.0, 7.5, 5.0, 0, 20, 0, 20, 0, 20, 0, 20),
    ("LOCAL RENDA FIXA PÓS", "CRÉDITO HY", "75% VIT HY E 25% TB HY", 10.0, 10.0, 7.5, 5.0, 0, 20, 0, 20, 0, 20, 0, 20),
    ("LOCAL RENDA FIXA PRÉ", "TPF", "IDKA11", 0.0, 0.0, 0.0, 0.0, 0, 20, 0, 20, 0, 30, 0, 30),
    ("LOCAL RENDA FIXA PRÉ", "CRÉDITO", "LCI CEF PRÉ 13,20% (2 anos)", 0.0, 0.0, 0.0, 0.0, 0, 20, 0, 20, 0, 30, 0, 20),
    ("LOCAL RENDA FIXA CDI+", "CRÉDITO", "CRA/CRI GENÉRICO CDI + 4%", 5.0, 10.0, 5.0, 5.0, 0, 20, 0, 20, 0, 30, 0, 30),
    ("LOCAL RENDA FIXA INFLAÇÃO", "TPF", "B5P211 (IMAB 5 ETF ITAÚ)", 15.0, 15.0, 15.0, 15.0, 0, 20, 0, 20, 0, 40, 0, 40),
    ("LOCAL RENDA FIXA INFLAÇÃO", "CRÉDITO", "DEB INFRA 10 ANOS VALE/SABESP/RAIZEN", 5.0, 5.0, 10.0, 15.0, 0, 20, 0, 20, 0, 40, 0, 40),
    ("RF FUNDOS LISTADOS ISENTOS", "CRÉDITO", "RURA11 / KNIP11 / ALZC11 / KDIF11 / AZIN11", 5.0, 5.0, 10.0, 10.0, 0, 10, 0, 20, 0, 30, 0, 30),
    ("RF CAMBIAL", "CAMBIAL", "TB HEDGE FUNDS / TAG MULTI ASSET SOL", 0.0, 2.5, 5.0, 5.0, 0, 5, 0, 10, 0, 20, 0, 30),
    ("LOCAL RENDA VARIÁVEL", "RV", "VIT AÇÕES 30%, VIT LONG BIAS 60%, SPXR11 10%", 0.0, 5.0, 10.0, 15.0, 0, 0, 0, 10, 0, 20, 0, 30),
    ("LOCAL MULTIMERCADO", "MM", "VIT MULTIMERCADO", 0.0, 5.0, 7.5, 7.5, 0, 0, 0, 10, 0, 20, 0, 30),
    ("LOCAL ALTERNATIVOS", "ALTS", "VIT SPECIAL SITS / TAG PRIVATE GROWTH 3", 0.0, 2.5, 7.5, 10.0, 0, 0, 0, 10, 0, 20, 0, 30),
    ("LOCAL ALTERNATIVOS", "CRIPTO", "BIT11 (1% e 2%)", 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 2.5, 0, 5),
    ("LOCAL HEDGES", "ALTS", "SEM NADA NO MOMENTO", 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 2.5, 0, 5, 0, 7.5),
]

PERFIS = {
    "renda_fixa": {"idx_hoje": 3, "idx_min": 7, "idx_max": 8, "label": "Renda Fixa"},
    "conservador": {"idx_hoje": 4, "idx_min": 9, "idx_max": 10, "label": "Conservador"},
    "moderado": {"idx_hoje": 5, "idx_min": 11, "idx_max": 12, "label": "Moderado"},
    "agressivo": {"idx_hoje": 6, "idx_min": 13, "idx_max": 14, "label": "Agressivo"},
}


def gerar_excel_perfil(perfil_key, info):
    """Gera Excel de um perfil com dados completos."""
    rows = []
    for m in MODELO_COMPLETO:
        pct = m[info["idx_hoje"]]
        rows.append({
            "Classe": m[0],
            "Subcategoria": m[1],
            "Ativo": m[2],
            "% Alvo": pct,
            "Min %": m[info["idx_min"]],
            "Max %": m[info["idx_max"]],
        })

    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, f"{perfil_key}.xlsx")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Sheet 1: Modelo completo (todas as linhas)
        df.to_excel(writer, sheet_name="Modelo", index=False)

        # Sheet 2: Apenas alocações ativas (% > 0)
        df_ativo = df[df["% Alvo"] > 0].reset_index(drop=True)
        df_ativo.to_excel(writer, sheet_name="Ativos", index=False)

    print(f"  OK {path} ({len(df_ativo)} ativos com alocacao)")
    return df


def gerar_master_excel():
    """Gera Excel mestre com todos os perfis."""
    rows = []
    for m in MODELO_COMPLETO:
        rows.append({
            "Classe Ativo": m[0],
            "Subcategoria": m[1],
            "Ativo": m[2],
            "Renda Fixa HOJE": m[3],
            "Conservador HOJE": m[4],
            "Moderado HOJE": m[5],
            "Agressivo HOJE": m[6],
            "RF Min": m[7], "RF Max": m[8],
            "Cons Min": m[9], "Cons Max": m[10],
            "Mod Min": m[11], "Mod Max": m[12],
            "Agr Min": m[13], "Agr Max": m[14],
        })

    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "_master_modelos.xlsx")
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"  OK Master: {path}")

    # Totais
    for perfil_label, col in [("Renda Fixa", "Renda Fixa HOJE"), ("Conservador", "Conservador HOJE"),
                               ("Moderado", "Moderado HOJE"), ("Agressivo", "Agressivo HOJE")]:
        total = df[col].sum()
        print(f"    {perfil_label}: {total:.1f}%")


if __name__ == "__main__":
    print("Gerando carteiras modelo TAG...\n")

    for key, info in PERFIS.items():
        gerar_excel_perfil(key, info)

    print()
    gerar_master_excel()
    print("\nConcluido!")
