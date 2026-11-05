# FGO × FGE — Equipe 7

Simulação didática em Streamlit sobre funções geradoras exponenciais e estruturas rotuladas, com aplicações em espaço de senhas e agrupamento de dados.

## Executar

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

A aplicação abre na **Apresentação guiada**. Use **Próxima →**, **← Anterior** ou o seletor de etapas. No menu lateral, **Laboratório completo** mantém os controles, gráficos e benchmarks detalhados. **Recomeçar apresentação** restaura os exemplos do percurso.

## Roteiro sugerido — 10 minutos

| Etapa | Tempo | Demonstração e mensagem |
| --- | --- | --- |
| 1. A ideia | 2 min | AA, AB, BA, BB são quatro senhas; há três perfis de quantidades. Pergunte se AB e BA são diferentes. |
| 2. A matemática | 3 min | Defina FGO e FGE, explique a extração do coeficiente e o fator n!. Mostre que a convolução FGE distribui rótulos com binomiais. |
| 3. Senhas | 2 min | Selecione “Com regra”: K=3, N=4, P=1. Há 81 candidatas, 41 válidas e 9 perfis. Mostre as senhas e a verificação independente. |
| 4. Comunicação | 1,5 min | Ligue os IDs: dois perfis tornam-se quatro partições de dados rotulados. |
| 5. Escala e código | 1,5 min | Aumente N de 4 para 15. Compare o crescimento das candidatas com o número de parcelas das convoluções. Abra o código se houver tempo. |

As etapas 3–5 correspondem a 50% do tempo. Cada etapa tem uma sugestão de fala recolhida. O tempo real deve ser adaptado ao limite definido pelo professor.

## Avaliação da versão inicial e mudanças

A base matemática já possuía convolução inteira, filtro de paridade independente, força bruta com limites e distinção entre partições inteiras e de conjuntos. A tela, porém, mostrava vários gráficos, controles e métricas antes de apresentar um exemplo concreto. Os resultados de formulários também podiam permanecer associados a parâmetros antigos sem um aviso claro.

O percurso novo começa com objetos visíveis e números pequenos. Mostra uma etapa por vez e três aplicações práticas, mantendo os detalhes técnicos em expansores ou no laboratório. Os controles do percurso atualizam os resultados imediatamente. O laboratório avisa quando os parâmetros não correspondem à execução salva; seu exemplo inicial de pacotes foi reduzido para evitar uma busca longa ao abrir.

## Precisão matemática e limites das aplicações

- **FGO também pode contar sequências ordenadas:** `1/(1-Kx)` é a FGO de `K^n`. O produto FGO **por símbolo** usado no comparativo conta perfis de quantidades; não é a única construção possível.
- Ambas as funções podem representar a mesma sequência `a_n`. Na FGO extraímos `[x^n]A`; na FGE extraímos `n![x^n]E`.
- Para senhas com P símbolos de ocorrência par, `E(x) = cosh(x)^P exp((K-P)x)`. As posições 1,…,n são os rótulos, e os símbolos podem repetir. Zero é uma ocorrência par.
- O produto FGE guarda contagens inteiras e aplica `c_n = Σ binom(n,j) a_j b_(n-j)`. Isso evita frações e arredondamento.
- A regra de paridade é um exemplo de validação e contagem de espaço de busca; não é um mecanismo de criptografia segura. O logaritmo da contagem só representa bits de espaço de busca sob escolha uniforme.
- Comunicação: contamos blocos sem ordem, com conteúdo sem ordem interna. É um modelo simplificado de agrupamento; pacotes contíguos, ordem de envio e cabeçalhos exigem outra modelagem.
- O gráfico guiado compara candidatas com parcelas de convolução; **não mede tempo de CPU**. O laboratório possui medições únicas de tempo, sujeitas a ruído e custos fixos.
- Força bruta: `O(K^n n)`; produto FGE: `O(K n²)` operações aritméticas, `O(n)` inteiros auxiliares. Inteiros grandes não têm custo constante em bits. O filtro especializado de paridade possui `P+1` termos.
- A força bruta implementada usa geradores/recursão; não guarda todo o espaço de busca na RAM. Não se deve atribuir a ela a memória de uma lista hipotética de senhas.

## Verificação

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes comparam os modelos de senhas com enumeração independente de palavras e perfis, verificam partições e limites de execução, percorrem as cinco etapas e exercitam exemplos, mudanças de controles, reinício e laboratório. A validação por força bruta permanece limitada nos exemplos grandes.

## Referências

- Flajolet e Sedgewick, *Analytic Combinatorics*, capítulos I e II: https://ac.cs.princeton.edu/home/
- Sedgewick e Flajolet, *An Introduction to the Analysis of Algorithms*, Generating Functions: https://aofa.cs.princeton.edu/30gf/
