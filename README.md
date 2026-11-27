# 🌦️ Raio-X do Clima

**O clima de qualquer município do Brasil, num mapa interativo.**
Chuva, temperatura, umidade, vento e sol, com histórico desde 1940, previsão, alertas e dicas para quem planta, do grande produtor ao pequeno produtor de horta.

🔗 **Acesse:** https://jmarcelogomesparreira-ship-it.github.io/raiox-do-clima

Faz parte da série de projetos de dados públicos, ao lado do [Raio-X da Cana](https://github.com/jmarcelogomesparreira-ship-it/raiox-da-cana).

---

## Como funciona

O projeto usa um **modelo híbrido**, porque baixar o Brasil inteiro desde 1940 não caberia em repositório nenhum:

| Parte | Quem faz | O quê |
|---|---|---|
| Mapas e lista de municípios | 🤖 Robô no GitHub Actions (Python) | Baixa as malhas do IBGE e guarda em `dados/` |
| Clima do local escolhido | 🌐 O navegador da própria pessoa | Busca na hora, direto da API Open-Meteo, sempre atualizado |

Assim o site mostra "todos os dados" de qualquer ponto do país sem guardar terabytes, e cada visitante usa o próprio limite da API.

## Etapas

- [x] **Etapa 1**: mapa do Brasil com zoom por estado e município, busca, "usar minha localização", clima de agora, ouvir em voz alta e link para compartilhar
- [ ] **Etapa 2**: previsão de 16 dias, hora a hora
- [ ] **Etapa 3**: histórico desde 1940 e comparação com a média
- [ ] **Etapa 4**: camadas coloridas no mapa + avisos oficiais do INMET
- [ ] **Etapa 5**: janela de pulverização hora a hora
- [ ] **Etapa 6**: janelas de plantio (ZARC/MAPA + guia de hortaliças Embrapa) e colheita estimada
- [ ] **Etapa 7**: El Niño / La Niña + modo simples com voz
- [ ] **Etapa 8**: revisão geral e vídeo

## Estrutura

```
index.html                       → o site (Leaflet + JavaScript puro)
src/etapa1_mapas.py              → baixa as malhas e a lista de municípios do IBGE
.github/workflows/baixar-mapas.yml → robô que roda o script e salva em dados/
dados/
  municipios.json                → 5.570 municípios com ponto central (busca e localização)
  mapas/brasil-estados.json      → contorno dos estados
  mapas/municipios-XX.json       → contorno dos municípios de cada estado
```

## Fontes de dados

- **IBGE**: malhas territoriais e lista de municípios (API de serviços de dados)
- **Open-Meteo**: clima atual, previsão e histórico (licença CC BY 4.0, uso não comercial)
- Mapas de fundo: © OpenStreetMap, © CARTO, Esri, OpenTopoMap

> As dicas agrícolas são orientação geral. A decisão de plantio e de aplicação de defensivos deve seguir a bula do produto e a recomendação de um agrônomo.

---

Feito por **Marcelo José Gomes Parreira** · Iturama/MG · [LinkedIn](https://www.linkedin.com/in/marcelo-jos%C3%A9-gomes-parreira-101b352ab)
