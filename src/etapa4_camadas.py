"""
Raio-X do Clima — Etapa 4: camadas coloridas do mapa do Brasil
--------------------------------------------------------------
Monta uma grade de pontos (1 grau ≈ 110 km) cobrindo o Brasil e busca na
Open-Meteo, para cada ponto, os últimos 60 dias e a previsão de 8 dias.
Com isso calcula as camadas que o mapa pinta:

  chuva7     chuva dos últimos 7 dias (mm)
  chuva30    chuva dos últimos 30 dias (mm)
  prev7      chuva prevista para os próximos 7 dias (mm)
  tmax       temperatura máxima prevista para hoje (°C)
  urmin      umidade mínima prevista para hoje (%)
  semchuva   dias seguidos sem chuva (≥ 1 mm) até ontem
  fogo       risco de fogo simplificado (0 a 4: baixo → crítico)

Roda 1 vez por dia no GitHub Actions. Saída: dados/camadas.json
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from shapely.geometry import Point, shape
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

PASSO = 1.0
LAT0, LAT1 = -34.0, 6.0     # bordas da grade (sul → norte)
LON0, LON1 = -74.0, -34.0   # (oeste → leste)
LOTE = 50                   # pontos por pedido à API
DIAS_PASSADOS = 60
DIA_CHUVA = 1.0

API = "https://api.open-meteo.com/v1/forecast"
VARS = ["precipitation_sum", "temperature_2m_max", "relative_humidity_2m_min", "wind_speed_10m_max"]


def contorno_brasil():
    br = json.loads((DADOS / "mapas" / "brasil-estados.json").read_text(encoding="utf-8"))
    return unary_union([shape(f["geometry"]) for f in br["features"]]).buffer(0.6)


def montar_grade(brasil):
    nlat = int(round((LAT1 - LAT0) / PASSO))
    nlon = int(round((LON1 - LON0) / PASSO))
    pontos = []
    for i in range(nlat):
        lat = LAT0 + (i + 0.5) * PASSO
        for j in range(nlon):
            lon = LON0 + (j + 0.5) * PASSO
            if brasil.contains(Point(lon, lat)):
                pontos.append((i, j, round(lat, 3), round(lon, 3)))
    return nlat, nlon, pontos


def pedir(lote, variaveis):
    params = {
        "latitude": ",".join(str(p[2]) for p in lote),
        "longitude": ",".join(str(p[3]) for p in lote),
        "daily": ",".join(variaveis),
        "past_days": DIAS_PASSADOS,
        "forecast_days": 8,
        "timezone": "America/Sao_Paulo",
    }
    for tentativa in range(1, 7):
        r = requests.get(API, params=params, timeout=180)
        if r.status_code == 429:
            espera = 65 * tentativa
            print(f"   limite da API, esperando {espera}s…")
            time.sleep(espera)
            continue
        if r.status_code == 400:
            raise ValueError(r.text[:300])
        r.raise_for_status()
        dados = r.json()
        return dados if isinstance(dados, list) else [dados]
    raise RuntimeError("API não respondeu depois de várias tentativas")


def classe(valor, limites):
    """Devolve quantos limites o valor já passou (0, 1, 2…)."""
    return sum(valor >= x for x in limites)


def risco_fogo(dias_secos, ur_min, t_max, vento, chuva_hoje):
    if None in (ur_min, t_max):
        return None
    pts = classe(dias_secos, [3, 8, 16, 31])                      # 0–4
    pts += 4 - classe(ur_min, [20, 30, 40, 60])                     # 0–4 (quanto mais seco, mais pontos)
    pts += classe(t_max, [25, 30, 33, 36])                          # 0–4
    pts += classe(vento or 0, [10, 20, 30])                         # 0–3
    if (chuva_hoje or 0) >= 5:
        pts -= 4
    return min(4, max(0, classe(pts, [4, 7, 10, 13])))              # 0 baixo … 4 crítico


def main():
    brasil = contorno_brasil()
    nlat, nlon, pontos = montar_grade(brasil)
    print(f"Grade: {nlat}×{nlon}, {len(pontos)} pontos dentro do Brasil")

    campos = {k: [None] * (nlat * nlon) for k in ["chuva7", "chuva30", "prev7", "tmax", "urmin", "semchuva", "fogo"]}
    variaveis = list(VARS)
    hoje = DIAS_PASSADOS  # índice do dia de hoje na resposta

    for n in range(0, len(pontos), LOTE):
        lote = pontos[n:n + LOTE]
        try:
            respostas = pedir(lote, variaveis)
        except ValueError as erro:
            print(f"   pedido recusado ({erro}); tentando sem umidade mínima")
            variaveis = [v for v in variaveis if v != "relative_humidity_2m_min"]
            respostas = pedir(lote, variaveis)
        for (i, j, _, _), resp in zip(lote, respostas):
            d = resp["daily"]
            chuva = [c if c is not None else 0 for c in d["precipitation_sum"]]
            tmax = d["temperature_2m_max"]
            urmin = d.get("relative_humidity_2m_min") or [None] * len(chuva)
            vento = d["wind_speed_10m_max"]
            secos = 0
            for c in reversed(chuva[:hoje]):
                if c >= DIA_CHUVA:
                    break
                secos += 1
            k = i * nlon + j
            campos["chuva7"][k] = round(sum(chuva[hoje - 7:hoje]), 1)
            campos["chuva30"][k] = round(sum(chuva[hoje - 30:hoje]), 1)
            campos["prev7"][k] = round(sum(chuva[hoje:hoje + 7]), 1)
            campos["tmax"][k] = tmax[hoje]
            campos["urmin"][k] = urmin[hoje]
            campos["semchuva"][k] = secos
            campos["fogo"][k] = risco_fogo(secos, urmin[hoje], tmax[hoje], vento[hoje], chuva[hoje])
        print(f"   {min(n + LOTE, len(pontos))}/{len(pontos)} pontos")
        time.sleep(8)

    if "relative_humidity_2m_min" not in variaveis:
        campos.pop("urmin")
        campos.pop("fogo")

    agora = datetime.now(timezone(timedelta(hours=-3)))
    saida = {
        "atualizado": agora.strftime("%Y-%m-%d %H:%M"),
        "lat0": LAT0, "lon0": LON0, "passo": PASSO, "nlat": nlat, "nlon": nlon,
        "campos": campos,
    }
    (DADOS / "camadas.json").write_text(json.dumps(saida, separators=(",", ":")), encoding="utf-8")
    print("Pronto: dados/camadas.json")


if __name__ == "__main__":
    main()
