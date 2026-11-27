"""
Raio-X do Clima — Etapa 4: avisos meteorológicos oficiais do INMET
------------------------------------------------------------------
Lê os avisos em vigor (hoje e próximos dias) na API pública do INMET
e guarda em dados/avisos.json:
  tipo do aviso, gravidade, cor oficial, início e fim, riscos,
  orientações, área (polígono) e códigos IBGE dos municípios atingidos.
"""

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "avisos.json"
URL = "https://apiprevmet3.inmet.gov.br/avisos/ativos"
CAB = {"User-Agent": "raiox-do-clima (github.com/jmarcelogomesparreira-ship-it/raiox-do-clima)"}


def lista(valor):
    """O INMET às vezes manda lista de verdade, às vezes uma lista escrita como texto."""
    if isinstance(valor, list):
        itens = valor
    elif isinstance(valor, str) and valor.strip().startswith("["):
        try:
            itens = ast.literal_eval(valor)
        except (ValueError, SyntaxError):
            itens = [valor.strip("[]'\" ")]
    elif valor:
        itens = [str(valor)]
    else:
        itens = []
    return [" ".join(str(i).split()) for i in itens if str(i).strip()]


def arredondar(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 3), round(c[1], 3)]
    return [arredondar(x) for x in c]


def main():
    r = requests.get(URL, headers=CAB, timeout=60)
    r.raise_for_status()
    bruto = r.json()
    avisos = []
    for grupo in ("hoje", "futuro"):
        for a in bruto.get(grupo, []) or []:
            if a.get("encerrado"):
                continue
            try:
                poligono = json.loads(a["poligono"]) if isinstance(a.get("poligono"), str) else a.get("poligono")
                poligono["coordinates"] = arredondar(poligono["coordinates"])
            except Exception:  # noqa: BLE001
                poligono = None
            avisos.append({
                "id": a.get("id"),
                "quando": grupo,
                "evento": a.get("descricao", "Aviso"),
                "severidade": a.get("severidade", ""),
                "nivel": {"Perigo Potencial": 1, "Perigo": 2, "Grande Perigo": 3}.get(a.get("severidade"), 1),
                "cor": a.get("aviso_cor") or "#FFFE00",
                "inicio": a.get("inicio"),
                "fim": a.get("fim"),
                "estados": a.get("estados", ""),
                "riscos": lista(a.get("riscos")),
                "instrucoes": lista(a.get("instrucoes")),
                "geocodes": [int(g) for g in str(a.get("geocodes", "")).split(",") if g.strip().isdigit()],
                "poligono": poligono,
            })
    avisos.sort(key=lambda x: (-x["nivel"], x["inicio"] or ""))
    agora = datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M")
    SAIDA.write_text(json.dumps({"atualizado": agora, "fonte": "INMET", "avisos": avisos},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Pronto: {len(avisos)} avisos em vigor")


if __name__ == "__main__":
    main()
