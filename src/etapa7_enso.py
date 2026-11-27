"""
Raio-X do Clima — Etapa 7: El Niño / La Niña
--------------------------------------------
Busca na NOAA (Centro de Previsão do Clima dos EUA, a referência mundial):
  • ONI — índice oficial que define El Niño e La Niña (média de 3 meses
    da anomalia de temperatura do mar na região Niño 3.4)
  • anomalia semanal mais recente do Niño 3.4
  • situação do "ENSO Alert System" e as chances previstas
Saída: dados/enso.json
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "enso.json"
CAB = {"User-Agent": "raiox-do-clima (github.com/jmarcelogomesparreira-ship-it/raiox-do-clima)"}
ONI = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SEMANAL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
DISCUSSAO = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml"

TRI_PT = {"DJF": "Dez–Fev", "JFM": "Jan–Mar", "FMA": "Fev–Abr", "MAM": "Mar–Mai", "AMJ": "Abr–Jun", "MJJ": "Mai–Jul",
          "JJA": "Jun–Ago", "JAS": "Jul–Set", "ASO": "Ago–Out", "SON": "Set–Nov", "OND": "Out–Dez", "NDJ": "Nov–Jan"}
STATUS_PT = {
    "el niño advisory": ("elnino", "El Niño em andamento"),
    "la niña advisory": ("lanina", "La Niña em andamento"),
    "final el niño advisory": ("neutro", "El Niño terminando"),
    "final la niña advisory": ("neutro", "La Niña terminando"),
    "el niño watch": ("neutro", "Vigilância de El Niño (pode se formar nos próximos meses)"),
    "la niña watch": ("neutro", "Vigilância de La Niña (pode se formar nos próximos meses)"),
    "not active": ("neutro", "Neutro: sem El Niño nem La Niña"),
}


def baixar(url):
    r = requests.get(url, headers=CAB, timeout=60)
    r.raise_for_status()
    return r.text


def main():
    saida = {"fonte": "NOAA / CPC"}

    # 1) ONI (trimestres móveis)
    oni = []
    for linha in baixar(ONI).splitlines()[1:]:
        p = linha.split()
        if len(p) == 4 and p[0] in TRI_PT:
            oni.append({"tri": p[0], "rot": TRI_PT[p[0]], "ano": int(p[1]), "v": float(p[3])})
    saida["oni"] = [x for x in oni if x["ano"] >= datetime.now().year - 16]
    saida["oni_ultimo"] = oni[-1]

    # 2) Niño 3.4 semanal (colunas: data, Niño1+2, Niño3, Niño3.4, Niño4 — cada uma "temp anomalia")
    try:
        linhas = [l for l in baixar(SEMANAL).splitlines() if re.match(r"\s*\d{2}[A-Z]{3}\d{4}", l)]
        ult = linhas[-1]
        data = ult.split()[0]
        pares = re.findall(r"(\d{1,2}\.\d)\s*(-?\d\.\d)", ult[len(ult) - len(ult.lstrip()) + len(data):])
        saida["nino34_semana"] = {"data": data, "anomalia": float(pares[2][1])}
    except Exception as erro:  # noqa: BLE001
        print("semanal falhou:", erro)

    # 3) situação oficial e chances
    try:
        html = baixar(DISCUSSAO)
        texto = re.sub(r"<[^>]+>", " ", html)
        texto = re.sub(r"\s+", " ", texto)
        m = re.search(r"ENSO Alert System Status:\s*([^.:]+?)(?:\s{0,3}(?:Synopsis|$))", texto)
        status = (m.group(1).strip() if m else "").strip()
        chave = status.lower().replace("nina", "niña").replace("nino", "niño")
        fase, rotulo = next((v for k, v in STATUS_PT.items() if chave.startswith(k)), ("neutro", status or "—"))
        saida["status_en"] = status
        saida["fase"], saida["rotulo"] = fase, rotulo
        s = re.search(r"Synopsis:\s*(.+?\.)(?:\s|$)", texto)
        if s:
            sinopse = s.group(1).strip()
            saida["sinopse_en"] = sinopse
            chances = re.findall(r"(\d{1,3})%\s*chance", sinopse)
            if chances:
                saida["chance"] = int(chances[0])
        d = re.search(r"issued by\s+CLIMATE PREDICTION CENTER.*?(\d{1,2} [A-Z][a-z]+ \d{4})", texto, re.I)
        if d:
            saida["discussao_data"] = d.group(1)
    except Exception as erro:  # noqa: BLE001
        print("discussão falhou:", erro)

    if "fase" not in saida:  # sem a discussão, decide pelo ONI (limiar oficial de ±0,5 °C)
        v = oni[-1]["v"]
        saida["fase"] = "elnino" if v >= 0.5 else "lanina" if v <= -0.5 else "neutro"
        saida["rotulo"] = {"elnino": "Condições de El Niño", "lanina": "Condições de La Niña", "neutro": "Neutro"}[saida["fase"]]

    saida["atualizado"] = datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M")
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({k: v for k, v in saida.items() if k != "oni"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
