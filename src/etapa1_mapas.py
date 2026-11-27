"""
Raio-X do Clima — Etapa 1: mapas do Brasil
-----------------------------------------
Baixa do IBGE:
  1. a malha dos estados (para o mapa do Brasil)
  2. a malha dos municípios de cada estado (carregada quando a pessoa dá zoom no estado)
  3. a lista de municípios, com um ponto central de cada um (para a busca e o "minha localização")

Roda no GitHub Actions (o PC da usina não precisa ter Python).
Saída: pasta dados/
"""

import json
import time
from pathlib import Path

import requests
from shapely.geometry import shape

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
PASTA_MAPAS = PASTA_DADOS / "mapas"
PASTA_MAPAS.mkdir(parents=True, exist_ok=True)

API_MALHAS = "https://servicodados.ibge.gov.br/api/v3/malhas"
API_LOCAL = "https://servicodados.ibge.gov.br/api/v1/localidades"
GEOJSON = "application/vnd.geo+json"

REGIOES = {"N": "Norte", "NE": "Nordeste", "SE": "Sudeste", "S": "Sul", "CO": "Centro-Oeste"}


def baixar(url, params=None, tentativas=4):
    """Baixa um JSON com algumas tentativas (a API do IBGE às vezes engasga)."""
    for n in range(1, tentativas + 1):
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as erro:  # noqa: BLE001
            print(f"   tentativa {n} falhou: {erro}")
            time.sleep(5 * n)
    raise RuntimeError(f"Não consegui baixar {url}")


def arredondar(coords, casas=4):
    """Corta casas decimais das coordenadas — 4 casas ≈ 11 metros, e o arquivo fica bem menor."""
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], casas), round(coords[1], casas)]
    return [arredondar(c, casas) for c in coords]


def enxugar(geojson):
    for f in geojson["features"]:
        f["geometry"]["coordinates"] = arredondar(f["geometry"]["coordinates"])
    return geojson


def salvar(obj, caminho):
    caminho.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"   salvo {caminho.relative_to(RAIZ)} ({caminho.stat().st_size / 1024:.0f} KB)")


def sigla_uf(m):
    """A API mudou com os municípios novos: alguns vêm sem microrregião. Tenta os dois caminhos."""
    try:
        return m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
    except (TypeError, KeyError):
        return m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]


def main():
    print("1) Estados do IBGE")
    estados = baixar(f"{API_LOCAL}/estados")
    info_uf = {
        str(e["id"]): {"id": e["id"], "uf": e["sigla"], "nome": e["nome"], "regiao": e["regiao"]["nome"]}
        for e in estados
    }

    print("2) Malha do Brasil dividida por estados")
    br = baixar(f"{API_MALHAS}/paises/BR", {"formato": GEOJSON, "qualidade": "minima", "intrarregiao": "UF"})
    for f in br["features"]:
        cod = str(f["properties"]["codarea"])
        f["properties"].update(info_uf[cod])
    salvar(enxugar(br), PASTA_MAPAS / "brasil-estados.json")

    print("3) Lista de municípios")
    municipios = baixar(f"{API_LOCAL}/municipios")
    nome_mun = {str(m["id"]): (m["nome"], sigla_uf(m)) for m in municipios}

    print("4) Malha dos municípios de cada estado + ponto central")
    lista = []
    for cod_uf, uf in sorted(info_uf.items(), key=lambda x: x[1]["uf"]):
        sigla = uf["uf"]
        print(f" - {sigla}")
        malha = baixar(
            f"{API_MALHAS}/estados/{cod_uf}",
            {"formato": GEOJSON, "qualidade": "intermediaria", "intrarregiao": "municipio"},
        )
        for f in malha["features"]:
            cod = str(f["properties"]["codarea"])
            nome, _ = nome_mun.get(cod, (cod, sigla))
            ponto = shape(f["geometry"]).representative_point()  # sempre cai dentro do município
            f["properties"] = {"id": int(cod), "nome": nome, "uf": sigla}
            lista.append([int(cod), nome, sigla, round(ponto.y, 4), round(ponto.x, 4)])
        salvar(enxugar(malha), PASTA_MAPAS / f"municipios-{sigla}.json")
        time.sleep(1)

    print("5) Arquivo da busca")
    lista.sort(key=lambda x: (x[2], x[1]))
    salvar(
        {
            "colunas": ["id", "nome", "uf", "lat", "lon"],
            "estados": sorted(info_uf.values(), key=lambda e: e["uf"]),
            "municipios": lista,
            "atualizado": time.strftime("%Y-%m-%d"),
        },
        PASTA_DADOS / "municipios.json",
    )
    print(f"Pronto: {len(lista)} municípios em {len(info_uf)} estados.")


if __name__ == "__main__":
    main()
