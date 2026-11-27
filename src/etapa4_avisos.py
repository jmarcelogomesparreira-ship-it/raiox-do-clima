"""
Raio-X do Clima — Etapa 4: avisos meteorológicos oficiais do INMET
------------------------------------------------------------------
Lê o feed público de avisos do INMET e guarda em dados/avisos.json
os avisos em vigor (tipo, gravidade, período, área e orientações).

Primeira versão: também salva amostras brutas em dados/debug/ para
conferirmos o formato exato que o INMET devolve.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
DEBUG = DADOS / "debug"
DEBUG.mkdir(parents=True, exist_ok=True)

FONTES = {
    "rss": "https://apiprevmet3.inmet.gov.br/avisos/rss",
    "ativos": "https://apiprevmet3.inmet.gov.br/avisos/ativos",
}
CAB = {"User-Agent": "raiox-do-clima (github.com/jmarcelogomesparreira-ship-it/raiox-do-clima)"}


def baixar(url):
    r = requests.get(url, headers=CAB, timeout=60)
    print(f"   {url} → {r.status_code}, {len(r.content)} bytes, {r.headers.get('content-type')}")
    r.raise_for_status()
    return r


def main():
    for nome, url in FONTES.items():
        try:
            r = baixar(url)
            ext = "json" if "json" in (r.headers.get("content-type") or "") else "xml"
            (DEBUG / f"avisos_{nome}.{ext}").write_bytes(r.content[:400_000])
        except Exception as erro:  # noqa: BLE001
            print(f"   falhou {nome}: {erro}")

    # amostra de alguns itens do RSS (links para o aviso completo)
    rss = DEBUG / "avisos_rss.xml"
    if rss.exists():
        try:
            raiz = ET.fromstring(rss.read_bytes())
            itens = raiz.findall(".//item")
            print(f"   RSS com {len(itens)} itens")
            for k, it in enumerate(itens[:3]):
                link = (it.findtext("link") or "").strip()
                if not link:
                    continue
                try:
                    r = baixar(link)
                    (DEBUG / f"aviso_item{k}.txt").write_bytes(r.content[:200_000])
                except Exception as erro:  # noqa: BLE001
                    print(f"   item {k} falhou: {erro}")
                m = re.search(r"(\d{6,})", link)
                if m:
                    for tentativa in (f"https://apiprevmet3.inmet.gov.br/aviso/getByID/{m.group(1)}",
                                      f"https://apiprevmet3.inmet.gov.br/avisos/{m.group(1)}"):
                        try:
                            r = baixar(tentativa)
                            (DEBUG / f"aviso_item{k}_api.txt").write_bytes(r.content[:200_000])
                            break
                        except Exception:  # noqa: BLE001
                            pass
        except ET.ParseError as erro:
            print(f"   RSS ilegível: {erro}")

    agora = datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M")
    if not (DADOS / "avisos.json").exists():
        (DADOS / "avisos.json").write_text(json.dumps({"atualizado": agora, "avisos": []}), encoding="utf-8")


if __name__ == "__main__":
    main()
