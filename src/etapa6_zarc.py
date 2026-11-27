"""
Raio-X do Clima — Etapa 6: janelas de plantio do ZARC (MAPA)
------------------------------------------------------------
Baixa a "Tábua de risco" do Zoneamento Agrícola de Risco Climático no portal
de dados abertos do Ministério da Agricultura e resume, para cada município:

  cultura → manejo (sequeiro / irrigado) → tipo de solo (arenoso / médio / argiloso)
          → 36 decêndios do ano com o risco de perda indicado (20%, 30%, 40% ou não indicado)

Regras do resumo (explicadas no site):
  • entre ciclos de cultivar, clima e níveis de manejo: fica o MENOR risco
    (existe opção de cultivar/manejo com aquele risco);
  • dentro de cada grupo de solo: fica o MAIOR risco (estimativa conservadora).

Arquivos usados: safra mais recente, a anterior (só para culturas que ainda
não saíram na mais recente) e "Perene, Olerícola e Sem Safra".
Saída: dados/zarc/zarc-UF.json (um por estado) + dados/zarc/culturas.json
"""

import csv
import io
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "zarc"
SAIDA.mkdir(parents=True, exist_ok=True)
PACOTE = "https://dados.agricultura.gov.br/api/3/action/package_show?id=6d3d141c-885e-41a4-ab7f-dc8ff323b96f"
CAB = {"User-Agent": "raiox-do-clima (github.com/jmarcelogomesparreira-ship-it/raiox-do-clima)"}

# códigos de solo do ZARC → grupo simples
#   antigos: 1 arenoso, 2 médio, 3 argiloso · novos (água disponível): AD1..AD6 = 11..16
GRUPO_SOLO = {"1": 0, "11": 0, "12": 0, "2": 1, "13": 1, "14": 1, "3": 2, "15": 2, "16": 2}
MANEJO = {"1": "S", "2": "I", "3": "I", "4": "S", "5": "I"}  # sequeiro / irrigado (variações juntas)
RISCO = {"0": 0, "20": 2, "30": 3, "40": 4}
FORA = re.compile(r"macaúba|forrageira pecuária", re.I)  # culturas muito específicas, fora do foco


def recursos():
    pac = requests.get(PACOTE, headers=CAB, timeout=60).json()["result"]["resources"]
    safras = []
    perene = None
    for r in pac:
        nome = r.get("name") or ""
        m = re.search(r"Safra (\d{4})/(\d{4})", nome)
        if m:
            safras.append((int(m.group(1)), nome, r["url"]))
        elif "Perene" in nome:
            perene = (nome, r["url"])
    safras.sort()
    return safras[-1], safras[-2], perene


def linhas_csv(url):
    """Baixa em streaming e devolve as linhas como dicionários (o arquivo tem centenas de MB)."""
    for tentativa in range(1, 4):
        try:
            with requests.get(url, headers=CAB, timeout=900, stream=True) as r:
                r.raise_for_status()
                bruto = io.BytesIO()
                for bloco in r.iter_content(1 << 20):
                    bruto.write(bloco)
            break
        except Exception as erro:  # noqa: BLE001
            print(f"   tentativa {tentativa} falhou: {erro}")
            time.sleep(20 * tentativa)
    else:
        raise RuntimeError(f"não consegui baixar {url}")
    bruto.seek(0)
    texto = io.TextIOWrapper(bruto, encoding="utf-8-sig", errors="replace", newline="")
    yield from csv.DictReader(texto, delimiter=";")


def main():
    atual, anterior, perene = recursos()
    print("Arquivos:", atual[1], "|", anterior[1], "|", perene[0])

    culturas = {}                      # código → {nome, tipo, portaria}
    # (uf, geocodigo, cultura, manejo, codigo_solo) → bytearray(36) com o MENOR risco entre ciclos/climas/manejos
    melhor = {}
    culturas_atual = set()

    def processar(url, tipo, so_novas=False):
        n = 0
        for row in linhas_csv(url):
            n += 1
            nome = row["Nome_cultura"].strip()
            if FORA.search(nome):
                continue
            cod = row["Cod_Cultura"]
            if so_novas and cod in culturas_atual:
                continue
            if tipo == "safra" and not so_novas:
                culturas_atual.add(cod)
            solo = row["Cod_Solo"]
            if solo not in GRUPO_SOLO:
                continue
            t = tipo if tipo == "safra" else row["SafraFin"].strip().lower()
            culturas.setdefault(cod, {"nome": nome, "tipo": t, "portaria": row["Portaria"]})
            chave = (row["UF"], row["geocodigo"], cod, MANEJO.get(row["Cod_Outros_Manejos"], "S"), solo)
            decs = bytearray(RISCO.get(row[f"dec{i}"], 0) for i in range(1, 37))
            atual_b = melhor.get(chave)
            if atual_b is None:
                melhor[chave] = decs
            else:
                for i in range(36):
                    a, b = atual_b[i], decs[i]
                    if b and (not a or b < a):
                        atual_b[i] = b
            if n % 500_000 == 0:
                print(f"   {n:,} linhas")
        print(f"   total {n:,} linhas")

    print("1) Safra atual"); processar(atual[2], "safra")
    print("2) Safra anterior (só culturas que ainda não saíram)"); processar(anterior[2], "safra", so_novas=True)
    print("3) Perene, olerícola e sem safra"); processar(perene[1], "perene")

    # junta os códigos de solo em 3 grupos, ficando com o MAIOR risco (conservador)
    por_uf = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))  # uf → geo → cultura → manejo → [3 grupos]
    grupos = defaultdict(lambda: [None, None, None])
    for (uf, geo, cod, man, solo), decs in melhor.items():
        g = GRUPO_SOLO[solo]
        k = (uf, geo, cod, man)
        atual_g = grupos[k][g]
        if atual_g is None:
            grupos[k][g] = bytearray(decs)
        else:
            for i in range(36):
                a, b = atual_g[i], decs[i]
                atual_g[i] = 0 if (a == 0 or b == 0) else max(a, b)
    for (uf, geo, cod, man), gs in grupos.items():
        txt = "|".join("".join(str(x) for x in g) if g else "" for g in gs)
        if txt.replace("0", "").replace("|", ""):
            por_uf[uf][geo][cod][man] = txt

    usados = set()
    for uf, muns in por_uf.items():
        for geo in muns.values():
            usados.update(geo.keys())
    lista = sorted(([c, v["nome"], v["tipo"]] for c, v in culturas.items() if c in usados), key=lambda x: x[1])
    idx = {c[0]: i for i, c in enumerate(lista)}
    for uf, muns in por_uf.items():
        saida = {geo: {str(idx[c]): v for c, v in cs.items()} for geo, cs in muns.items()}
        (SAIDA / f"zarc-{uf}.json").write_text(json.dumps(saida, separators=(",", ":")), encoding="utf-8")
        print(f"   {uf}: {len(saida)} municípios, {(SAIDA / f'zarc-{uf}.json').stat().st_size / 1e6:.1f} MB")
    (SAIDA / "culturas.json").write_text(json.dumps({
        "culturas": lista, "safra": atual[1], "anterior": anterior[1],
        "atualizado": time.strftime("%Y-%m-%d"),
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Pronto: {len(lista)} culturas")


if __name__ == "__main__":
    main()
