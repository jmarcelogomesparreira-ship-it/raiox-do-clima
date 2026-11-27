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
| Camadas do mapa | 🤖 Robô diário (Python) | Grade de 812 pontos (~110 km) com últimos 60 dias + previsão; o navegador suaviza e recorta no contorno do Brasil |
| Avisos do INMET | 🤖 Robô diário (Python) | Avisos em vigor com área, gravidade, riscos e orientações, ligados aos municípios pelo código IBGE |
| Janelas de plantio (ZARC) | 🤖 Robô mensal (Python) | Lê ~840 MB da Tábua de Risco do MAPA (safra atual, anterior e perenes/olerícolas) e resume por município, cultura, manejo e solo em `dados/zarc/` |
| El Niño / La Niña | 🤖 Robô diário (Python) | ONI, Niño 3.4 semanal e situação oficial da NOAA/CPC em `dados/enso.json` |
| Histórico desde 1940 | 🌐 O navegador da própria pessoa | Baixa a reanálise ERA5 só quando a aba Histórico é aberta e calcula tudo ali mesmo (normal 1991–2020, recordes, tendência) |

Assim o site mostra "todos os dados" de qualquer ponto do país sem guardar terabytes, e cada visitante usa o próprio limite da API.

## Etapas

- [x] **Etapa 1**: mapa do Brasil com zoom por estado e município, busca, "usar minha localização", clima de agora, ouvir em voz alta e link para compartilhar
- [x] **Etapa 2**: previsão de 16 dias (gráficos de temperatura e chuva, lista dia a dia) e hora a hora (temperatura, chance de chuva, vento e umidade), com aviso de "tendência" a partir do 8º dia
- [x] **Etapa 3**: histórico desde 1940: chuva dos últimos 30/90 dias contra a média, dias seguidos sem chuva, ano escolhido × normal 1991–2020, listras do clima, tendência de temperatura, chuva de cada ano, recordes e tabela do clima mês a mês
- [x] **Etapa 4**: camadas coloridas no mapa do Brasil (chuva 7 e 30 dias, previsão 7 dias, temperatura máxima, umidade mínima, dias sem chuva, risco de fogo) + avisos oficiais do INMET no mapa e no painel do município
- [x] **Etapa 5**: janela de pulverização hora a hora (aba 🌱 Campo): semáforo de 7 dias × 24 horas com vento na barra, chuva, temperatura, umidade e Delta T, resposta direta "pode aplicar hoje?" e próxima janela boa
- [x] **Etapa 6**: plantio e colheita (aba 🌱 Campo): janelas oficiais do ZARC para 92 culturas em todos os municípios zoneados, por manejo (sequeiro/irrigado) e tipo de solo, com "pode plantar agora?", próxima janela e colheita estimada; guia de 15 hortaliças por região com checagem do clima previsto
- [x] **Etapa 7**: El Niño / La Niña (situação oficial da NOAA, intensidade, gráfico do ONI e o que costuma significar em cada região, com dica para o campo) + 🔤 Modo fácil: letras grandes, perguntas e respostas diretas (vai chover? pode passar veneno? o que plantar?) e "Ouvir tudo"
- [ ] **Etapa 8**: revisão geral e vídeo

## Estrutura

```
index.html                       → o site (Leaflet + JavaScript puro)
src/etapa1_mapas.py              → baixa as malhas e a lista de municípios do IBGE
.github/workflows/baixar-mapas.yml → robô que roda o script e salva em dados/
src/etapa4_camadas.py            → grade de pontos e camadas do mapa (todo dia)
src/etapa4_avisos.py             → avisos oficiais do INMET (todo dia)
src/etapa6_zarc.py               → janelas de plantio do ZARC (todo mês)
src/etapa7_enso.py               → El Niño / La Niña pela NOAA (todo dia)
dados/
  municipios.json                → 5.570 municípios com ponto central (busca e localização)
  mapas/brasil-estados.json      → contorno dos estados
  mapas/municipios-XX.json       → contorno dos municípios de cada estado
  camadas.json                   → valores da grade para as camadas coloridas
  avisos.json                    → avisos do INMET em vigor
  zarc/culturas.json             → lista de culturas zoneadas
  zarc/zarc-XX.json              → janelas de plantio por município de cada estado
```

## Fontes de dados

- **IBGE**: malhas territoriais e lista de municípios (API de serviços de dados)
- **MAPA / Embrapa**: Zoneamento Agrícola de Risco Climático (Tábua de risco, dados abertos) e recomendações da Embrapa Hortaliças
- **NOAA / CPC**: índice ONI, Niño 3.4 e situação oficial do El Niño / La Niña
- **INMET**: avisos meteorológicos oficiais (API pública de avisos)
- **Open-Meteo**: clima atual, previsão e histórico (licença CC BY 4.0, uso não comercial)
- Mapas de fundo: © OpenStreetMap, © CARTO, Esri, OpenTopoMap

> O "risco de fogo" é um índice simplificado do próprio projeto (dias sem chuva, umidade, calor e vento), não o índice oficial do INPE.

> As dicas agrícolas são orientação geral. A decisão de plantio e de aplicação de defensivos deve seguir a bula do produto e a recomendação de um agrônomo.

---

Feito por **Marcelo José Gomes Parreira** · Iturama/MG · [LinkedIn](https://www.linkedin.com/in/marcelo-jos%C3%A9-gomes-parreira-101b352ab)
