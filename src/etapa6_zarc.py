"""
Raio-X do Clima — Etapa 6: janelas de plantio do ZARC (MAPA)
------------------------------------------------------------
Versão de inspeção: baixa a lista de arquivos da "Tábua de risco" no
portal de dados abertos do MAPA, baixa as safras mais recentes e salva
um resumo do formato em dados/debug/ para montarmos o processamento.
"""

import csv
import io
import json
from collections import Counter
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DEBUG = RAIZ / "dados" / "debug"
DEBUG.mkdir(parents=True, exist_ok=True)
PACOTE = "https://dados.agricultura.gov.br/api/3/action/package_show?id=6d3d141c-885e-41a4-ab7f-dc8ff323b96f"
CAB = {"User-Agent": "raiox-do-clima (github.com/jmarcelogomesparreira-ship-it/raiox-do-clima)"}


def main():
    pac = requests.get(PACOTE, headers=CAB, timeout=60).json()["result"]
    recursos = [{"nome": r.get("name"), "url": r.get("url"), "formato": r.get("format"), "tamanho": r.get("size")} for r in pac["resources"]]
    (DEBUG / "zarc_recursos.json").write_text(json.dumps(recursos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(recursos, ensure_ascii=False, indent=1))
    csvs = [r for r in recursos if (r["formato"] or "").lower() == "csv" or (r["url"] or "").endswith(".csv")]
    for r in csvs[-2:]:
        print("Baixando", r["nome"])
        resp = requests.get(r["url"], headers=CAB, timeout=600)
        resp.raise_for_status()
        bruto = resp.content
        texto = None
        for cod in ("utf-8-sig", "latin-1"):
            try:
                texto = bruto.decode(cod)
                break
            except UnicodeDecodeError:
                pass
        linhas = texto.splitlines()
        nome = (r["nome"] or "safra").replace("/", "-").replace(" ", "_")
        print(f"   {len(bruto)/1e6:.1f} MB, {len(linhas)} linhas")
        sep = ";" if linhas[0].count(";") > linhas[0].count(",") else ","
        leitor = csv.DictReader(io.StringIO(texto), delimiter=sep)
        cols = leitor.fieldnames
        contagens = {c: Counter() for c in cols}
        amostra_itu = []
        n = 0
        for row in leitor:
            n += 1
            for c in cols:
                if len(contagens[c]) < 400 or row[c] in contagens[c]:
                    contagens[c][row[c]] += 1
            if "3134400" in json.dumps(row, ensure_ascii=False) and len(amostra_itu) < 60:
                amostra_itu.append(row)
        resumo = {
            "arquivo": r["nome"], "mb": round(len(bruto) / 1e6, 1), "linhas": n, "separador": sep, "colunas": cols,
            "valores": {c: contagens[c].most_common(60) for c in cols},
            "primeiras": linhas[:15], "iturama": amostra_itu,
        }
        (DEBUG / f"zarc_resumo_{nome}.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
