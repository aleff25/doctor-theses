# SLR Search Workflow — URLs prontos por base de dados

**Tese:** Architecture-Aware Software Metrics and AI-Supported Quality Assessment in Java-Based Distributed Systems
**Candidato:** Aleff Rodrigues Mendes de Oliveira  ·  **Orientadores:** José Pereira dos Reis, Vítor Bastos  ·  **Iscte-IUL**
**String de busca:** V3 (final, language-agnostic) — Seção 3.2.1 do draft da SLR
**Janela temporal:** 2014-01-01 → 2026-05-01
**Objetivo:** importar os resultados de cada base num folder Mendeley dedicado, para track per-database em todas as 4 fases

---

## Estado atual da sua biblioteca Mendeley (export.xml de 24/05/2026)

| Database | untagged | phase1_exc | phase1_inc | star | TOTAL | % screened |
|---|---:|---:|---:|---:|---:|---:|
| ACM | 9 | 132 | 30 | 0 | 171 | 94.7 % |
| IEEE | 0 | 10 | 4 | 0 | 14 | 100 % |
| Springer | 87 | 19 | 6 | 0 | 112 | 22.3 % |
| ScienceDirect | 1 | 1 | 0 | 0 | 2 | 50 % |
| Wiley | 8 | 4 | 2 | 0 | 14 | 42.9 % |
| MDPI | 15 | 5 | 5 | 0 | 25 | 40 % |
| Outras / sem DOI padrão | 57 | 29 | 12 | 0 | 98 | 41.8 % |
| **TOTAL** | **177** | **200** | **59** | **0** | **436** | **59.4 %** |

**O que isso te diz:** ACM e IEEE estão essencialmente triadas. Springer tem 87 ainda sem tag — o gargalo está aí. O bucket "Outras" tem 57 sem triagem — vale checar quais bases as geraram (provável Scopus/WoS importados, ou arXiv).

---

## URLs de busca pré-preenchidos

> **Como usar:** clique no link → confira que a query foi carregada → ajuste os filtros de data e tipo de documento → exporte BibTeX ou RIS → importe na pasta do Mendeley correspondente.

### 1. ACM Digital Library

**Link direto (pré-enche a busca):**
```
https://dl.acm.org/action/doSearch?AllField=%28metric%2A%20OR%20%22software%20metric%2A%22%20OR%20%22runtime%20metric%2A%22%20OR%20%22quality%20metric%2A%22%20OR%20measurement%29%20AND%20%28microservice%2A%20OR%20%22distributed%20system%2A%22%20OR%20%22cloud%20native%22%20OR%20Kubernetes%29%20AND%20%28observability%20OR%20telemetry%20OR%20monitoring%20OR%20log%2A%20OR%20trace%2A%20OR%20%22distributed%20tracing%22%29%20AND%20%28%22machine%20learning%22%20OR%20%22artificial%20intelligence%22%20OR%20AI%20OR%20%22metric%20generation%22%20OR%20%22automatic%20metric%2A%22%20OR%20%22learned%20metric%2A%22%29%20AND%20%28architectur%2A%20OR%20%22software%20architecture%22%20OR%20%22architecture%20evaluation%22%20OR%20%22architectural%20metric%2A%22%20OR%20%22architectural%20analysis%22%20OR%20%22architectural%20pattern%2A%22%20OR%20%22reference%20architecture%22%20OR%20%22architecture%20decision%2A%22%20OR%20%22architecture%20description%22%29%20NOT%20%28IoT%20OR%20%22internet%20of%20things%22%20OR%20sensor%2A%20OR%20%22wireless%20sensor%22%20OR%20WSN%20OR%20%22smart%20home%22%20OR%20%22smart%20city%22%20OR%20%22cyber-physical%22%20OR%20%22edge%20computing%22%20OR%20%22fog%20computing%22%29%20NOT%20%28medicine%20OR%20medical%20OR%20patient%20OR%20biology%29&AfterYear=2014&BeforeYear=2026
```

**Se a URL longa falhar, abra Advanced Search e cole:**
```
[All: "metric*"] OR [All: "software metric*"] OR [All: "runtime metric*"] OR [All: "quality metric*"] OR [All: "code metric*"] OR [All: "architecture metric*"] OR [All: measurement]
AND [[All: "microservice*"] OR [All: "distributed system*"] OR [All: "cloud native"] OR [All: kubernetes]]
AND [[All: observability] OR [All: telemetry] OR [All: monitoring] OR [All: "log*"] OR [All: "trace*"] OR [All: "distributed tracing"]]
AND [[All: "machine learning"] OR [All: "artificial intelligence"] OR [All: "AI"] OR [All: "metric generation"] OR [All: "automatic metric*"] OR [All: "learned metric*"]]
AND [[All: "architectur*"] OR [All: "software architecture"] OR [All: "architecture evaluation"] OR [All: "architectural metric*"] OR [All: "architectural analysis"] OR [All: "architectural pattern*"] OR [All: "reference architecture"] OR [All: "architecture decision*"] OR [All: "architecture description"]]
NOT [[All: IoT] OR [All: "internet of things"] OR [All: "sensor*"] OR [All: "wireless sensor"] OR [All: WSN] OR [All: "smart home"] OR [All: "smart city"] OR [All: "cyber-physical"] OR [All: "edge computing"] OR [All: "fog computing"]]
NOT [[All: medicine] OR [All: medical] OR [All: patient] OR [All: biology]]
```

**Filtros para refinar (sidebar):** Publication Date `2014–2026`; Article Type `Research Article + Short Paper + Demo + Tutorial`.

**Exportar:** "Export Citations" → BibTeX.

---

### 2. IEEE Xplore

**Link direto (pré-enche a busca):**
```
https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText=%28metric%2A%20OR%20%22software%20metric%2A%22%20OR%20%22runtime%20metric%2A%22%20OR%20%22quality%20metric%2A%22%20OR%20measurement%29%20AND%20%28microservice%2A%20OR%20%22distributed%20system%2A%22%20OR%20%22cloud%20native%22%20OR%20Kubernetes%29%20AND%20%28observability%20OR%20telemetry%20OR%20monitoring%20OR%20log%2A%20OR%20trace%2A%20OR%20%22distributed%20tracing%22%29%20AND%20%28%22machine%20learning%22%20OR%20%22artificial%20intelligence%22%20OR%20AI%20OR%20%22metric%20generation%22%20OR%20%22automatic%20metric%2A%22%20OR%20%22learned%20metric%2A%22%29%20AND%20%28architectur%2A%20OR%20%22software%20architecture%22%20OR%20%22architecture%20evaluation%22%20OR%20%22architectural%20metric%2A%22%20OR%20%22architectural%20analysis%22%20OR%20%22architectural%20pattern%2A%22%20OR%20%22reference%20architecture%22%20OR%20%22architecture%20decision%2A%22%20OR%20%22architecture%20description%22%29%20NOT%20%28IoT%20OR%20%22internet%20of%20things%22%20OR%20sensor%2A%20OR%20%22wireless%20sensor%22%20OR%20WSN%20OR%20%22smart%20home%22%20OR%20%22smart%20city%22%20OR%20%22cyber-physical%22%20OR%20%22edge%20computing%22%20OR%20%22fog%20computing%22%29%20NOT%20%28medicine%20OR%20medical%20OR%20patient%20OR%20biology%29&ranges=2014_2026_Year
```

**Se a URL longa falhar — Command Search com field codes (cole isso):**
```
("Abstract":"metric*" OR "Abstract":"software metric*" OR "Abstract":"runtime metric*" OR "Abstract":"quality metric*" OR "Abstract":"code metric*" OR "Abstract":"architecture metric*" OR "Abstract":measurement)
AND ("Abstract":"microservice*" OR "Abstract":"distributed system*" OR "Abstract":"cloud native" OR "Abstract":Kubernetes)
AND ("Abstract":observability OR "Abstract":telemetry OR "Abstract":monitoring OR "Abstract":"log*" OR "Abstract":"trace*" OR "Abstract":"distributed tracing")
AND ("Abstract":"machine learning" OR "Abstract":"artificial intelligence" OR "Abstract":AI OR "Abstract":"metric generation" OR "Abstract":"automatic metric*" OR "Abstract":"learned metric*")
AND ("Abstract":"architectur*" OR "Abstract":"software architecture" OR "Abstract":"architecture evaluation" OR "Abstract":"architectural metric*" OR "Abstract":"architectural analysis" OR "Abstract":"architectural pattern*" OR "Abstract":"reference architecture" OR "Abstract":"architecture decision*" OR "Abstract":"architecture description")
NOT ("Abstract":IoT OR "Abstract":"internet of things" OR "Abstract":"sensor*" OR "Abstract":"wireless sensor" OR "Abstract":WSN OR "Abstract":"smart home" OR "Abstract":"smart city" OR "Abstract":"cyber-physical" OR "Abstract":"edge computing" OR "Abstract":"fog computing")
NOT ("Abstract":medicine OR "Abstract":medical OR "Abstract":patient OR "Abstract":biology)
```

**Filtros:** Year `2014-2026`; Content Type `Conferences + Journals + Early Access + Magazines`.

**Exportar:** selecione todos os resultados (até 100 por página) → "Export" → "Citations" → BibTeX.

---

### 3. SpringerLink

> **Atenção:** Springer não suporta aninhamento booleano profundo via URL. Recomendo executar em **DUAS passes** e combinar offline (depois o Mendeley deduplica via DOI automaticamente).

**Run A — métricas+microservices+AI+arquitetura:**
```
https://link.springer.com/search?query=%28metric+OR+metrics+OR+measurement+OR+%22software+metric%22+OR+%22runtime+metric%22+OR+%22quality+metric%22+OR+%22code+metric%22+OR+%22architecture+metric%22%29+AND+%28microservice+OR+microservices+OR+%22distributed+system%22+OR+%22distributed+systems%22+OR+%22cloud+native%22+OR+Kubernetes%29+AND+%28%22machine+learning%22+OR+%22artificial+intelligence%22+OR+AI+OR+%22metric+generation%22+OR+%22automatic+metric%22+OR+%22learned+metric%22%29+AND+%28architecture+OR+architectures+OR+architectural+OR+%22software+architecture%22%29&date-facet-mode=between&facet-start-year=2014&facet-end-year=2026
```

**Run B — observabilidade+microservices+arquitetura:**
```
https://link.springer.com/search?query=%28observability+OR+telemetry+OR+monitoring+OR+log+OR+logs+OR+trace+OR+traces+OR+%22distributed+tracing%22%29+AND+%28microservice+OR+microservices+OR+%22distributed+system%22+OR+%22distributed+systems%22+OR+%22cloud+native%22+OR+Kubernetes%29+AND+%28architecture+OR+architectural+OR+%22software+architecture%22%29&date-facet-mode=between&facet-start-year=2014&facet-end-year=2026
```

**Filtros (em ambas):** Discipline `Computer Science`; Content Type `Article + Conference Paper + Chapter`; Language `English`.

**Pós-filtro offline:** descartar entries cujo título/abstract bata com `IoT|sensor|WSN|smart home|smart city|cyber-physical|edge computing|fog computing|medicine|medical|patient|biology`.

**Exportar:** botão "Download" em cada página → CSV → converter via Mendeley.

---

### 4. ScienceDirect (Elsevier)

> **Atenção:** ScienceDirect tem limite de 8 conectores booleanos por query. Mesma estratégia de duas passes.

**Run A:**
```
https://www.sciencedirect.com/search?qs=%28metric+OR+measurement+OR+%22software+metric%22+OR+%22quality+metric%22+OR+%22architecture+metric%22%29+AND+%28microservice+OR+microservices+OR+%22cloud+native%22+OR+Kubernetes+OR+%22distributed+system%22%29+AND+%28%22machine+learning%22+OR+%22artificial+intelligence%22%29+AND+%28architecture+OR+architectural%29&date=2014-2026&articleTypes=FLA%2CCH%2CCON%2CREV
```

**Run B:**
```
https://www.sciencedirect.com/search?qs=%28observability+OR+telemetry+OR+monitoring+OR+log+OR+trace+OR+%22distributed+tracing%22%29+AND+%28microservice+OR+%22cloud+native%22+OR+Kubernetes%29+AND+%28%22machine+learning%22+OR+%22artificial+intelligence%22%29+AND+%28architecture+OR+architectural%29&date=2014-2026&articleTypes=FLA%2CCH%2CCON%2CREV
```

**Filtros:** Years `2014-2026`; Article type `Research articles + Conference abstracts + Review articles + Book chapters`.

**Exportar:** "Export citations" → BibTeX (até 200 por export).

---

### 5. Scopus

> Cobertura ampla (indexa boa parte de ACM/IEEE/Springer/Elsevier/Wiley/MDPI). Use para complementar buscas diretas e para WoS, e para a desduplicação cross-database. Você precisa de login institucional pelo Iscte.

**Link direto (pode pedir refresh — a URL pré-enche o campo de busca):**
```
https://www.scopus.com/results/results.uri?src=s&s=TITLE-ABS-KEY+%28+%28+metric%2A+OR+%22software+metric%2A%22+OR+%22runtime+metric%2A%22+OR+%22quality+metric%2A%22+OR+%22code+metric%2A%22+OR+%22architecture+metric%2A%22+OR+measurement+%29+AND+%28+microservice%2A+OR+%22distributed+system%2A%22+OR+%22cloud+native%22+OR+kubernetes+%29+AND+%28+observability+OR+telemetry+OR+monitoring+OR+log%2A+OR+trace%2A+OR+%22distributed+tracing%22+%29+AND+%28+%22machine+learning%22+OR+%22artificial+intelligence%22+OR+AI+OR+%22metric+generation%22+OR+%22automatic+metric%2A%22+OR+%22learned+metric%2A%22+%29+AND+%28+architectur%2A+OR+%22software+architecture%22+OR+%22architecture+evaluation%22+OR+%22architectural+metric%2A%22+OR+%22architectural+analysis%22+OR+%22architectural+pattern%2A%22+OR+%22reference+architecture%22+OR+%22architecture+decision%2A%22+OR+%22architecture+description%22+%29+AND+NOT+%28+iot+OR+%22internet+of+things%22+OR+sensor%2A+OR+%22wireless+sensor%22+OR+wsn+OR+%22smart+home%22+OR+%22smart+city%22+OR+%22cyber-physical%22+OR+%22edge+computing%22+OR+%22fog+computing%22+%29+AND+NOT+%28+medicine+OR+medical+OR+patient+OR+biology+%29+%29+AND+PUBYEAR+%3E+2013+AND+PUBYEAR+%3C+2027
```

**Se a URL longa falhar — Advanced Search, cole isso:**
```
TITLE-ABS-KEY (
  ( metric*  OR  "software metric*"  OR  "runtime metric*"  OR  "quality metric*"
    OR  "code metric*"  OR  "architecture metric*"  OR  measurement )
  AND  ( microservice*  OR  "distributed system*"  OR  "cloud native"  OR  kubernetes )
  AND  ( observability  OR  telemetry  OR  monitoring  OR  log*  OR  trace*
         OR  "distributed tracing" )
  AND  ( "machine learning"  OR  "artificial intelligence"  OR  AI
         OR  "metric generation"  OR  "automatic metric*"  OR  "learned metric*" )
  AND  ( architectur*  OR  "software architecture"  OR  "architecture evaluation"
         OR  "architectural metric*"  OR  "architectural analysis"
         OR  "architectural pattern*"  OR  "reference architecture"
         OR  "architecture decision*"  OR  "architecture description" )
  AND NOT ( iot  OR  "internet of things"  OR  sensor*  OR  "wireless sensor"
            OR  wsn  OR  "smart home"  OR  "smart city"  OR  "cyber-physical"
            OR  "edge computing"  OR  "fog computing" )
  AND NOT ( medicine  OR  medical  OR  patient  OR  biology )
)
AND  PUBYEAR  >  2013  AND  PUBYEAR  <  2027
AND  ( LIMIT-TO ( DOCTYPE , "ar" ) OR LIMIT-TO ( DOCTYPE , "cp" )
       OR LIMIT-TO ( DOCTYPE , "ch" ) )
AND  ( LIMIT-TO ( LANGUAGE , "English" ) )
AND  ( LIMIT-TO ( SUBJAREA , "COMP" ) OR LIMIT-TO ( SUBJAREA , "ENGI" ) )
```

**Exportar:** "Export" → BibTeX → "Citation information" + "Abstract & keywords" (importante para a triagem da Fase 2).

---

### 6. ISI Web of Science

> WoS não aceita queries longas via URL. Use Advanced Search → Web of Science Core Collection.

**Acesso:** <https://www.webofscience.com/wos/woscc/basic-search>

**Cole em Advanced Search (no campo "Edit advanced search" → "Add to query preview"):**
```
TS = ( ( metric*  OR  "software metric*"  OR  "runtime metric*"
        OR  "quality metric*"  OR  "code metric*"  OR  "architecture metric*"
        OR  measurement )
      AND ( microservice*  OR  "distributed system*"  OR  "cloud native"
            OR  Kubernetes )
      AND ( observability  OR  telemetry  OR  monitoring  OR  log*
            OR  trace*  OR  "distributed tracing" )
      AND ( "machine learning"  OR  "artificial intelligence"  OR  AI
            OR  "metric generation"  OR  "automatic metric*"
            OR  "learned metric*" )
      AND ( architectur*  OR  "software architecture"  OR  "architecture evaluation"
            OR  "architectural metric*"  OR  "architectural analysis"
            OR  "architectural pattern*"  OR  "reference architecture"
            OR  "architecture decision*"  OR  "architecture description" )
      NOT  ( IoT  OR  "internet of things"  OR  sensor*  OR  "wireless sensor"
             OR  WSN  OR  "smart home"  OR  "smart city"  OR  "cyber-physical"
             OR  "edge computing"  OR  "fog computing" )
      NOT  ( medicine  OR  medical  OR  patient  OR  biology ) )
```

**Filtros (na lateral, após executar):**
- Timespan `2014-01-01 → 2026-05-01`
- Document Types `Article + Proceedings Paper + Book Chapter + Review Article`
- Index `SCI-EXPANDED + ESCI + CPCI-S + BKCI-S`

**Exportar:** "Export" → "BibTeX" → "Records from 1 to 500" (em batches se >500 hits).

---

## Workflow no Mendeley (passo a passo)

1. **Crie 6 folders** no Mendeley com os nomes:
   - `SLR/ACM`
   - `SLR/IEEE Xplore`
   - `SLR/Springer Link`
   - `SLR/ScienceDirect`
   - `SLR/Scopus`
   - `SLR/Web of Science`

2. **Para cada folder, na ordem acima:**
   - Clique no URL pré-preenchido (ou cole a query no Advanced Search da base)
   - Confira que a query carregou corretamente (a barra de busca deve mostrar a string completa)
   - Aplique os filtros listados (data + tipo de documento + idioma)
   - Exporte tudo em BibTeX ou RIS
   - No Mendeley, com o folder selecionado, use **File → Import** apontando para o arquivo exportado — as entradas vão direto para o folder ativo

3. **Anote no tracker** (`SLR_Search_Tracker.xlsx`) o número de "Raw hits (Phase 1)" que cada base retornou. Esse é o número que vai para a Tabela 3 da Seção 3.2.4 do `.docx` da SLR.

4. **Triagem (Fase 2):** abra cada folder no Mendeley, leia título + abstract de cada entry, e aplique a tag `phase1_exc` ou `phase1_inc`. A `% screened` no tracker te mostra o progresso por base.

5. **Fase 3 (full intro/methods/conclusion):** ainda no folder, dos `phase1_inc`, mantenha a tag ou re-tag para `phase1_exc` se a leitura completa revelar que o estudo não atende IC3.1–IC3.4.

6. **Fase 4 (Dybå QA):** rode a planilha Dybå (Q1–Q11, ver §3.2.8 do docx) sobre os sobreviventes da Fase 3. Marque com `star` os que passam ≥ 6/11 E são fortemente alinhados às RQs.

7. **Atualize o tracker periodicamente.** O `% retained` calcula sozinho a taxa de sobrevivência por base.

---

## Para o seu PRISMA flow no docx

Depois que rodar as 6 buscas e preencher o tracker, a Tabela 3 (Seção 3.2.4) ficará completa. A Figura 2 (PRISMA-style flow) reflete o pipeline 438 → ~95 → 52 → 40; cada um desses números agora poderá ser quebrado por base de dados na própria Tabela 3 e ilustrado num Sankey diagram se você quiser (posso gerar quando os números estiverem fechados).

**Observação importante sobre o seu estado atual:** As 162 entradas com DOIs não-padrão na sua biblioteca atual provavelmente vieram de buscas no Scopus ou WoS que indexam papers cujos DOIs primários não batem com os prefixos clássicos. Quando você refizer as buscas com este workflow, esses entries vão se atribuir corretamente à base de origem (Scopus ou WoS).
