"""Demonstração de funções geradoras. Execute: streamlit run app.py."""
import itertools
import math
import sys
import time

import altair as alt
import pandas as pd
import streamlit as st

TETO = 5_000_000
CORES = alt.Scale(domain=["Força bruta", "FGO", "FGE", "Verificação extra"],
                  range=["#f59e0b", "#8b5cf6", "#14b8a6", "#3b82f6"])


def numero(n):
    return f"{n:,}".replace(",", ".")


def memoria(n):
    unidade = "GB" if n >= 1024**3 else "MB"
    divisor = 1024**3 if unidade == "GB" else 1024**2
    return f"{n / divisor:,.2f} {unidade}".replace(",", "_").replace(".", ",").replace("_", ".")


def medir(funcao, *args):
    inicio = time.perf_counter_ns()
    resultado = funcao(*args)
    return resultado, time.perf_counter_ns() - inicio


def produto(a, b, exponencial):
    """FGO: Σ a[k]b[n-k]; FGE: Σ C(n,k)a[k]b[n-k], sem frações."""
    return [sum((math.comb(n, k) if exponencial else 1) * a[k] * b[n-k]
                for k in range(n + 1)) for n in range(len(a))]


def senhas_modelo(n, k, p, exponencial):
    """[x^N]∏ séries; na FGE guardamos diretamente n! vezes o coeficiente."""
    a = [1] + [0] * n
    for simbolo in range(k):
        b = [int(simbolo >= p or grau % 2 == 0) for grau in range(n + 1)]
        a = produto(a, b, exponencial)
    return a


def senhas_fechada(n, k, p):
    """Filtro de paridade: 2^(-P) Σ_j C(P,j)(K-2j)^N; divisão inteira exata."""
    soma = sum(math.comb(p, j) * (k - 2*j)**n for j in range(p + 1))
    return soma // (2**p)


def senhas_bruta(n, k, p):
    """Enumera K^N palavras e verifica paridade em O(N) por palavra."""
    validas = 0
    for palavra in itertools.product(range(k), repeat=n):
        paridade = 0
        for simbolo in palavra:
            if simbolo < p:
                paridade ^= 1 << simbolo
        validas += paridade == 0
    return validas


def pacotes_fgo(n, tamanhos):
    """A(x)=∏ 1/(1-x^s): cada atualização acrescenta um pacote de tamanho s."""
    a = [1] + [0] * n
    for s in tamanhos:
        for i in range(s, n + 1):
            a[i] += a[i-s]
    return a


def pacotes_fge(n, tamanhos):
    """exp(Σ x^s/s!): a(n)=Σ C(n-1,s-1)a(n-s), bloco do menor ID."""
    a = [1] + [0] * n
    for i in range(1, n + 1):
        a[i] = sum(math.comb(i-1, s-1) * a[i-s] for s in tamanhos if s <= i)
    return a


class TetoAtingido(Exception):
    pass


def pacotes_bruta(n, tamanhos, distintos, teto=TETO):
    """Enumera partições inteiras ou de conjunto, sem memoização nem lista global."""
    chamadas = 0

    def visitar():
        nonlocal chamadas
        if chamadas >= teto:
            raise TetoAtingido
        chamadas += 1

    def identicos(resto, minimo):
        # Partições de N: tamanhos não decrescentes evitam contar permutações.
        visitar()
        if resto == 0:
            return 1
        return sum(identicos(resto-s, i) for i, s in enumerate(tamanhos)
                   if i >= minimo and s <= resto)

    def rotulados(ids):
        # O bloco do menor ID determina uma única decomposição de cada partição.
        visitar()
        if not ids:
            return 1
        total = 0
        for s in tamanhos:
            if s <= len(ids):
                for outros in itertools.combinations(ids[1:], s-1):
                    bloco = set(outros)
                    total += rotulados(tuple(i for i in ids[1:] if i not in bloco))
        return total

    inicio = time.perf_counter_ns()
    try:
        valor = rotulados(tuple(range(n))) if distintos else identicos(n, 0)
        motivo = ""
    except TetoAtingido:
        valor, motivo = None, f"Busca abortada no teto de {numero(teto)} chamadas."
    return dict(valor=valor, ns=time.perf_counter_ns()-inicio,
                itens=chamadas, motivo=motivo)


def executar(modulo, n, k=2, p=0, tamanhos=(), distintos=False, limite=2_000_000,
             teto=TETO, permitir_bruta=True):
    """Aplica os modelos matemáticos e as travas antes de enumerar a referência."""
    if modulo == "senhas":
        fgo = medir(senhas_modelo, n, k, p, False)
        fge = medir(senhas_modelo, n, k, p, True)
        fechada = medir(senhas_fechada, n, k, p)
        itens = k**n
        if permitir_bruta and itens <= limite:
            valor, ns = medir(senhas_bruta, n, k, p)
            bruta = dict(valor=valor, ns=ns, itens=itens, motivo="")
        else:
            bruta = dict(valor=None, ns=None, itens=itens,
                         motivo=f"Força bruta bloqueada: {numero(itens)} sequências; limite {numero(limite)}.")
    else:
        fgo, fge = medir(pacotes_fgo, n, tamanhos), medir(pacotes_fge, n, tamanhos)
        fechada = None
        if permitir_bruta and (not distintos or n <= 11):
            bruta = pacotes_bruta(n, tamanhos, distintos, teto)
        else:
            bruta = dict(valor=None, ns=None, itens=0,
                         motivo="Força bruta bloqueada: bytes distintos exigem N ≤ 11 ou o orçamento do benchmark acabou.")
    return dict(fgo=fgo, fge=fge, fechada=fechada, bruta=bruta)


def barras(titulo, linhas, eixo, log=False):
    """Converte valores apenas para desenho; os resultados exatos ficam no tooltip."""
    st.markdown(f"#### {titulo}")
    base = alt.Chart(pd.DataFrame(linhas)).encode(
        y=alt.Y("Método:N", title=None, sort=None),
        x=alt.X("Valor:Q", title=eixo, scale=alt.Scale(type="symlog" if log else "linear")),
        color=alt.Color("Método:N", scale=CORES, legend=None),
        tooltip=["Método:N", alt.Tooltip("Exato:N", title="Valor")])
    st.altair_chart(base.mark_bar(cornerRadiusEnd=6, size=32).properties(height=170), width="stretch")


def graficos(r, cfg):
    """Compara contagens e tempos medidos e mostra a evolução dos coeficientes."""
    n, b = cfg["n"], r["bruta"]
    contagens, tempos = [], []
    for modelo in ("fgo", "fge"):
        vetor, ns = r[modelo]
        contagens.append({"Método": modelo.upper(), "Valor": vetor[n], "Exato": numero(vetor[n])})
        tempos.append({"Método": modelo.upper(), "Valor": ns/1_000, "Exato": f"{ns/1_000:,.3f} µs"})
    if b["valor"] is not None:
        contagens.insert(0, {"Método": "Força bruta", "Valor": b["valor"], "Exato": numero(b["valor"])})
        tempos.insert(0, {"Método": "Força bruta", "Valor": b["ns"]/1_000, "Exato": f"{b['ns']/1_000:,.3f} µs"})
    # Normalização só visual: evita perda de inteiros grandes ao enviar dados ao navegador.
    maior = max(x["Valor"] for x in contagens) or 1
    for linha in contagens:
        linha["Valor"] = 100 * (linha["Valor"] / maior)
    esquerda, direita = st.columns(2)
    with esquerda:
        barras("Quantas soluções cada método contou?", contagens, "% da maior contagem")
        st.caption("Barras iguais indicam a mesma contagem. Passe o mouse para ver o inteiro exato.")
    with direita:
        barras("Quanto tempo levou?", tempos, "Tempo em µs · escala simétrica log", True)
        st.caption("Quanto menor a barra, mais rápido. Só aparecem buscas concluídas; tempos não são estimativas.")
    st.markdown("#### O que acontece quando o problema cresce?")
    linhas = [{"N": i, "Método": nome.upper(), "Soluções": float(r[nome][0][i]),
               "Exato": numero(r[nome][0][i])} for nome in ("fgo", "fge") for i in range(1, n+1)]
    curva = alt.Chart(pd.DataFrame(linhas)).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("N:Q", title="Tamanho do problema (N)", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("Soluções:Q", title="Soluções · escala simétrica log", scale=alt.Scale(type="symlog")),
        color=alt.Color("Método:N", scale=CORES), tooltip=["N:Q", "Método:N", "Exato:N"])
    st.altair_chart(curva.properties(height=260).interactive(), width="stretch")
    st.caption("Contagens calculadas para todos os tamanhos até N, sem enumerar. A escala permite comparar ordens de grandeza e inclui zero; valores desenhados são aproximados, tooltips são exatos.")
    if cfg["modulo"] == "senhas":
        vetor = r["fge"][0]
        tamanho = sys.getsizeof(vetor) + sum(sys.getsizeof(x) for x in vetor)
        barras("E se guardássemos todas as senhas?", [
            {"Método": "Força bruta", "Valor": float(cfg["k"]**n*(49+n)), "Exato": memoria(cfg["k"]**n*(49+n)) + " (estimativa de materialização)"},
            {"Método": "FGE", "Valor": tamanho, "Exato": f"{numero(tamanho)} bytes (vetor)"},
        ], "Bytes · escala simétrica log", True)
        st.caption("Comparação hipotética: a força bruta deste app usa gerador e não ocupa a RAM da barra laranja. Estimativa por sequência: 49 bytes mais seu tamanho; não inclui a lista. A barra verde mede apenas o vetor Python.")


def mostrar(r, cfg):
    n, modulo = cfg["n"], cfg["modulo"]
    adequada = "fge" if modulo == "senhas" or cfg.get("distintos") else "fgo"
    b = r["bruta"]
    st.markdown("### Compare os resultados")
    graficos(r, cfg)
    if b["valor"] is None:
        (st.error if b["ns"] is None else st.warning)(b["motivo"])
        st.warning("A verdade de referência não foi gerada; a adequação abaixo é matemática, sem validação por enumeração.")
    else:
        st.metric("Força bruta — resultado exato", numero(b["valor"]))
    for coluna, modelo in zip(st.columns(2), ("fgo", "fge")):
        vetor, ns = r[modelo]
        with coluna:
            st.metric(f"Modelo {modelo.upper()}", numero(vetor[n]))
            st.write(f"Tempo: **{ns / 1_000:,.3f} µs**")
            if b["valor"] is not None:
                if vetor[n] != b["valor"]:
                    st.error("❌ Diverge da força bruta: modelo inadequado")
                elif modelo == adequada:
                    st.success("✅ Coincide com a força bruta: modelo adequado")
                else:
                    st.warning("Coincidência numérica neste caso; o modelo continua inadequado para esta interpretação.")
            else:
                st.write("✅ Modelo adequado pela interpretação" if modelo == adequada
                         else "❌ Modelo inadequado pela interpretação")
            if modelo != adequada:
                st.caption("Este produto FGO conta vetores de contagens, sem distribuir posições. Outras FGOs podem contar sequências."
                           if modulo == "senhas" else
                           ("A FGO ignora os IDs dos bytes." if cfg.get("distintos")
                            else "A FGE distingue bytes que o problema considera idênticos."))
            tamanho = sys.getsizeof(vetor) + sum(sys.getsizeof(x) for x in vetor)
            st.caption(f"Vetor: {n+1} inteiros — {numero(tamanho)} bytes nesta execução.")
    st.write(f"FGO e FGE {'coincidem numericamente' if r['fgo'][0][n] == r['fge'][0][n] else 'divergem numericamente'} neste caso.")
    if r["fechada"]:
        valor, ns = r["fechada"]
        st.write(f"Verificação extra: **{numero(valor)}** · {ns / 1_000:,.3f} µs")
        (st.success if valor == r["fge"][0][n] else st.error)(
            "✅ A verificação extra confirma a FGE." if valor == r["fge"][0][n]
            else "❌ A verificação extra diverge da FGE.")
    if b["ns"] is not None:
        st.write(f"Força bruta: **{b['ns'] / 1_000_000:,.3f} ms**"
                 + (" (busca incompleta)" if b["valor"] is None else ""))
    if b["valor"] is not None:
        denominador = r[adequada][1]
        st.write(f"Ganho: **{b['ns'] / denominador:,.2f} vezes mais rápido** com {adequada.upper()}."
                 if denominador else "Ganho indisponível: tempo do modelo igual a zero.")
        st.caption("Medição única: ruído e custos fixos podem fazer o ganho ficar abaixo de 1 em casos pequenos.")
    st.write(f"{'Sequências a gerar' if modulo == 'senhas' else 'Chamadas recursivas realizadas'}: **{numero(b['itens'])}**")
    if modulo == "senhas":
        itens = cfg["k"]**n
        mem = memoria(itens * (49+n))
        if itens > cfg["limite"]:
            st.warning(f"Atenção: para N={n} e K={cfg['k']}, a força bruta geraria {numero(itens)} sequências (≈ {mem} de RAM se guardadas), enquanto a FGE resolve com cerca de {numero(cfg['k']*(n+1)*(n+2)//2)} operações aritméticas.")
    st.caption("A força bruta usa geradores/recursão e não guarda todos os resultados. As funções geradoras usam O(N) inteiros; o tamanho de cada inteiro cresce com a contagem.")


def benchmark(cfg):
    """Mede N=1…N atual; limita também o total de chamadas da referência."""
    linhas, saldo, parar = [], TETO, False
    progresso = st.progress(0)
    for n in range(1, cfg["n"] + 1):
        parametros = dict(cfg, n=n, teto=saldo, permitir_bruta=not parar)
        r = executar(**parametros)
        for nome in ("fgo", "fge", "fechada"):
            if r[nome] is not None:
                linhas.append(dict(N=n, Método="Verificação extra" if nome == "fechada" else nome.upper(), Tempo=max(r[nome][1], 1)/1_000))
        b = r["bruta"]
        if b["valor"] is not None:
            linhas.append(dict(N=n, Método="Força bruta", Tempo=max(b["ns"], 1)/1_000))
        if cfg["modulo"] == "pacotes":
            saldo -= b["itens"]
        parar = parar or b["valor"] is None or saldo <= 0
        progresso.progress(n / cfg["n"])
    progresso.empty()
    return linhas


def painel_benchmark(cfg):
    chave = "benchmark_" + cfg["modulo"]
    st.markdown("### Corrida dos algoritmos")
    st.caption("Benchmark: medições únicas, em µs, com eixo logarítmico. Pontos da força bruta abortada/bloqueada são omitidos. Pacotes: teto total de 5 milhões de chamadas.")
    if st.button("Rodar benchmark", key=chave+"_botao"):
        st.session_state[chave] = (dict(cfg), benchmark(cfg))
    if chave in st.session_state:
        origem, linhas = st.session_state[chave]
        st.caption(f"Benchmark salvo até N={origem['n']}. Os controles atuais só são aplicados ao rodar novamente.")
        grafico = alt.Chart(pd.DataFrame(linhas)).mark_line(point=True).encode(
            x=alt.X("N:Q", title="N"),
            y=alt.Y("Tempo:Q", title="Tempo (µs) — escala log", scale=alt.Scale(type="log")),
            color=alt.Color("Método:N", scale=CORES), tooltip=["N", "Método", "Tempo"])
        st.altair_chart(grafico, width="stretch")


def autoteste():
    """Compara enumeração, extração de coeficientes e valores conhecidos."""
    casos = []
    for n, k, p, esperado, ordinario in [(2, 2, 0, 4, 3), (2, 2, 2, 2, 2), (4, 3, 0, 81, 15)]:
        valores = (senhas_bruta(n, k, p), senhas_modelo(n, k, p, True)[n],
                   senhas_fechada(n, k, p), senhas_modelo(n, k, p, False)[n])
        casos.append((f"Senhas K={k}, N={n}, P={p}", valores == (esperado, esperado, esperado, ordinario)))
    for n, s, distintos, esperado in [(5, (1, 2, 5), False, 4), (3, (1, 2), True, 4)]:
        modelo = pacotes_fge if distintos else pacotes_fgo
        outro = pacotes_fgo if distintos else pacotes_fge
        ok = modelo(n, s)[n] == pacotes_bruta(n, s, distintos)["valor"] == esperado
        casos.append((f"Pacotes N={n}, S={s}, distintos={distintos}", ok and outro(n, s)[n] != esperado))
    for nome, ok in casos:
        (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {nome}")
    return all(ok for _, ok in casos)


def laboratorio():
    st.markdown("""<style>
    .block-container {max-width: 1250px; padding-top: 2rem;}
    [data-testid="stMetric"] {background: #14b8a610; border: 1px solid #14b8a640;
        padding: 16px; border-radius: 12px;}
    </style>""", unsafe_allow_html=True)
    st.title("FGE × FGO × Força bruta")
    st.markdown("### Contar tudo ou contar com inteligência?")
    st.write("O que decide é se os elementos são **distinguíveis (rotulados)**, não apenas ‘a ordem importa’.")
    for coluna, titulo, texto in zip(st.columns(3), ["🟠 Força bruta", "🟣 FGO", "🟢 FGE"],
            ["Testa cada possibilidade.", "Neste produto, conta perfis de quantidades.", "Neste produto, distribui posições rotuladas."]):
        with coluna:
            st.markdown(f"**{titulo}**")
            st.caption(texto)
    senhas, pacotes = st.tabs(["Criptografia", "Teoria das comunicações"])
    with senhas:
        st.info("🔑 AB e BA são senhas diferentes. O produto FGE usado aqui distribui posições rotuladas; o produto FGO usado aqui conta apenas quantidades. Outras FGOs podem contar sequências. Os símbolos especiais devem aparecer um número par de vezes.")
        k = st.slider("Símbolos K", 2, 32, 4)
        p = st.slider("Símbolos especiais P (ocorrências pares; zero é par)", 0, k, min(2, k))
        with st.form("senhas_form"):
            n = st.slider("Tamanho N", 1, 15, 8)
            limite = st.number_input("Limite de sequências na força bruta", 1, 20_000_000, 2_000_000, step=100_000)
            rodar = st.form_submit_button("Calcular senhas")
        cfg = dict(modulo="senhas", n=n, k=k, p=p, limite=int(limite))
        if rodar or "resultado_senhas" not in st.session_state:
            st.session_state["resultado_senhas"] = (cfg, executar(**cfg))
        if "resultado_senhas" in st.session_state:
            origem, r = st.session_state["resultado_senhas"]
            st.caption(f"Execução salva: N={origem['n']}, K={origem['k']}, P={origem['p']}.")
            if origem != cfg:
                st.warning("Parâmetros alterados. Clique em Calcular para atualizar os resultados abaixo.")
            mostrar(r, origem)
        with st.expander("Custos dos algoritmos"):
            st.caption("Força bruta O(K^N·N); FGO/FGE O(K·N²); verificação extra O(P) termos. Custos em operações aritméticas; inteiros maiores exigem mais trabalho por operação.")
        painel_benchmark(cfg)
    with pacotes:
        st.info("📦 Os pacotes não têm ordem. Com bytes idênticos, só o tamanho dos pacotes importa: use FGO. Com IDs, trocar os bytes de pacote pode criar outra divisão: use FGE.")
        interpretacao = st.radio("Interpretação", ["Bytes idênticos", "Bytes distintos (cada byte tem um ID)"])
        st.session_state.setdefault("tamanhos", [1, 2, 5])
        for coluna, valores in zip(st.columns(2), ([1, 2, 5], [2, 4, 8])):
            if coluna.button(f"Usar {valores}"):
                st.session_state["tamanhos"] = valores
        tamanhos = tuple(sorted(st.multiselect("Tamanhos permitidos S", range(1, 11), key="tamanhos")))
        if not tamanhos:
            st.info("S vazio: não há divisão possível para N ≥ 1; ambos os modelos retornam zero.")
        with st.form("pacotes_form"):
            n = st.slider("Bytes N", 1, 100, 5)
            rodar = st.form_submit_button("Calcular pacotes")
        cfg = dict(modulo="pacotes", n=n, tamanhos=tamanhos, distintos=interpretacao.startswith("Bytes distintos"))
        if rodar or "resultado_pacotes" not in st.session_state:
            st.session_state["resultado_pacotes"] = (cfg, executar(**cfg))
        if "resultado_pacotes" in st.session_state:
            origem, r = st.session_state["resultado_pacotes"]
            st.caption(f"Execução salva: N={origem['n']}, S={origem['tamanhos']}, bytes {'distintos' if origem['distintos'] else 'idênticos'}.")
            if origem != cfg:
                st.warning("Parâmetros alterados. Clique em Calcular para atualizar os resultados abaixo.")
            mostrar(r, origem)
        with st.expander("Custos e limites dos algoritmos"):
            st.caption("Força bruta exponencial no pior caso; FGO/FGE O(N·|S|). Teto: 5 milhões de chamadas; bytes distintos exigem N ≤ 11. Busca sem materialização das partições. Custos em operações aritméticas.")
        painel_benchmark(cfg)
    with st.expander("Autotestes e exemplos para apresentação"):
        st.write("Experimente K=4, N=8, P=2; K=8, N=10, P=3 (trava); S={1,2,5}, N=30.")
        if st.button("Executar autoteste"):
            autoteste()
    st.table(pd.DataFrame([
        ["Senhas com paridade", "símbolos repetidos em posições distintas", "FGE", "reconhece cada sequência diferente"],
        ["Buffer, bytes idênticos", "indistinguíveis", "FGO", "só importa quantos pacotes de cada tamanho"],
        ["Buffer, bytes com ID", "rotulados", "FGE", "dividir um conjunto rotulado em blocos"],
    ], columns=["Problema", "Elementos", "Modelo adequado", "Por quê"]))


ETAPAS = ["1 · A ideia", "2 · A matemática", "3 · Senhas", "4 · Comunicação", "5 · Escala e código"]


def destaque(titulo, texto):
    # Conteúdo editorial fixo; valores dos controles são números limitados.
    st.markdown(f'<div class="destaque"><small>{titulo}</small><p>{texto}</p></div>', unsafe_allow_html=True)


def fichas(palavras):
    st.markdown('<div class="fichas">' + ''.join(
        f'<span class="ficha">{palavra}</span>' for palavra in palavras) + '</div>', unsafe_allow_html=True)


def fala(texto):
    with st.expander("Sugestão de fala para esta etapa"):
        st.write(texto)


def ideia():
    st.header("AB e BA: uma ou duas possibilidades?")
    st.write("Uma senha tem **2 posições** e usa os símbolos **A e B**, com repetição permitida.")
    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Olhar só as quantidades")
        fichas(["2 A", "1 A + 1 B", "2 B"])
        st.metric("Perfis de quantidades", "3")
        st.caption("AB e BA têm o mesmo perfil: um A e um B.")
    with direita:
        st.subheader("Olhar cada posição")
        fichas(["AA", "AB", "BA", "BB"])
        st.metric("Senhas diferentes", "4")
        st.caption("Posição 1 e posição 2 são rótulos distintos.")
    destaque("A PERGUNTA QUE ESCOLHE O MODELO", "O que torna duas soluções diferentes?")
    st.info("O produto FGO por símbolo conta 3 perfis. O produto FGE por símbolo conta 4 senhas, ao distribuir as posições. A diferença está na construção usada.")
    fala("Se eu trocar AB por BA, continuo com a mesma quantidade de letras, mas a senha muda. Vamos ver como a matemática representa essa diferença.")


def matematica():
    st.header("O que muda na função geradora?")
    esq, dir = st.columns(2)
    with esq:
        st.subheader("FGO · ordinária")
        st.latex(r"A(x)=\sum_{n\geq0}a_nx^n")
        st.write("O coeficiente de xⁿ já é a contagem aₙ.")
        st.latex(r"(1+x+x^2+\cdots)^2=1+2x+3x^2+\cdots")
        st.caption("Um fator para cada símbolo. No grau 2: três perfis de quantidades.")
    with dir:
        st.subheader("FGE · exponencial")
        st.latex(r"E(x)=\sum_{n\geq0}a_n\frac{x^n}{n!}")
        st.write("Multiplicamos o coeficiente de xⁿ por n! para recuperar aₙ.")
        st.latex(r"(e^x)^2=e^{2x}=1+2x+\frac{4x^2}{2!}+\cdots")
        st.caption("No grau 2: 2! × (4/2!) = quatro senhas.")
    with st.expander("Por que aparece o coeficiente binomial no código?"):
        st.latex(r"c_n=\sum_{j=0}^{n}\binom{n}{j}a_jb_{n-j}")
        st.write("Escolhemos quais j dos n rótulos vão para o primeiro fator. O código guarda aₙ diretamente, usando inteiros e sem erros de arredondamento.")
        st.latex(r"\text{Para quantidades fixas:}\quad \frac{n!}{n_1!n_2!\cdots n_K!}")
    st.warning("Evite dizer ‘ordem importa → sempre FGE’. A FGO 1/(1−Kx) também conta as Kⁿ palavras de tamanho n. A FGE facilita a composição de estruturas rotuladas e as restrições por símbolo.")
    fala("As duas funções podem representar a mesma sequência de contagens. A FGE divide os termos por n fatorial e, no produto, escolhe como distribuir os rótulos entre as partes.")


def senhas_guiadas():
    st.header("Quantas senhas passam pela regra?")
    st.write("Aplicação: contar o espaço de senhas de um sistema com uma regra de validação.")
    caso = st.radio("Escolha um exemplo", ["Visual · 2 símbolos", "Com regra · 3 símbolos", "Explorar"], horizontal=True, key="caso_senha")
    if caso == "Visual · 2 símbolos":
        n, k, p = 2, 2, 0
    elif caso == "Com regra · 3 símbolos":
        n, k, p = 4, 3, 1
    else:
        a, b, c = st.columns(3)
        k = a.slider("Quantidade de símbolos", 2, 6, 3, key="g_k")
        n = b.slider("Posições da senha", 1, 10, 4, key="g_n")
        p = c.slider("Símbolos com ocorrência par", 0, k, min(1, k), key="g_p")
    alfabeto = "ABCDEF"[:k]
    especiais = alfabeto[:p]
    st.caption(f"Alfabeto: {', '.join(alfabeto)} · {n} posições · repetição permitida")
    st.info(f"Regra: cada símbolo em {{{', '.join(especiais)}}} deve aparecer um número par de vezes. Zero também é par."
            if p else "Sem restrição: qualquer sequência deste alfabeto é válida.")
    r = executar("senhas", n, k, p, limite=20_000)
    total = k**n
    validas = r["fge"][0][n]
    a, b, c = st.columns(3)
    a.metric("Candidatas · Kⁿ", numero(total))
    b.metric("Válidas · FGE", numero(validas))
    c.metric("Perfis · produto FGO", numero(r["fgo"][0][n]))
    if total <= 256:
        palavras = [''.join(w) for w in itertools.product(alfabeto, repeat=n)]
        aceitas = [w for w in palavras if all(w.count(s) % 2 == 0 for s in especiais)]
        st.subheader("Veja as senhas válidas")
        fichas(aceitas[:12] or ["Nenhuma senha atende à regra"])
        st.caption(f"Exibindo {min(12, len(aceitas))} de {len(aceitas)} senhas válidas.")
        if len(aceitas) > 12:
            with st.expander("Ver todas as senhas válidas"):
                fichas(aceitas)
        rejeitadas = [w for w in palavras if w not in aceitas]
        if rejeitadas:
            st.caption("Exemplos rejeitados: " + ", ".join(rejeitadas[:6]) + ". Ocorre um símbolo restrito um número ímpar de vezes.")
    else:
        st.caption("A lista fica oculta nos casos grandes: o objetivo é contar sem gerar todas as senhas.")
    if r["bruta"]["valor"] is not None:
        st.success(f"Conferido: enumeração, FGE e fórmula de paridade retornam {numero(validas)}.")
    else:
        st.info("Enumeração omitida acima de 20 mil candidatas. O filtro de paridade confirma o resultado da FGE.")
    with st.expander("Ver a fórmula aplicada"):
        st.latex(r"E(x)=\cosh(x)^P e^{(K-P)x},\qquad a_n=n![x^n]E(x)")
        st.write("cosh(x) contém apenas graus pares; eˣ permite qualquer quantidade. Aqui, K é o alfabeto e P é a quantidade de símbolos restritos.")
        st.latex(r"a_n=\frac{1}{2^P}\sum_{j=0}^P\binom{P}{j}(K-2j)^n")
    destaque("CONEXÃO COM CRIPTOGRAFIA", f"A regra deixa {numero(validas)} de {numero(total)} candidatas para uma busca exaustiva.")
    st.caption("Modelo didático de espaço de busca: paridade não é criptografia segura. log₂(contagem) mede bits de espaço de busca apenas sob escolha uniforme; senhas humanas não seguem essa hipótese.")
    fala("Primeiro contamos todas as candidatas. Depois aplicamos a regra. A FGE chega à contagem sem testar cada senha. Uma restrição também reduz o espaço que um atacante precisaria explorar.")


def comunicacao_guiada():
    st.header("Os dados têm identidade?")
    st.write("Modelo de comunicação: agrupar unidades de dados em blocos de **1 ou 2**, sem ordenar os blocos nem os elementos dentro deles.")
    rotulados = st.toggle("Distinguir os IDs dos dados", value=False, key="ids_guiados")
    a, b = st.columns([1, 2])
    with a:
        st.metric("Unidades de dados", "3")
        total = pacotes_fge(3, (1, 2))[3] if rotulados else pacotes_fgo(3, (1, 2))[3]
        st.metric("Agrupamentos possíveis", str(total))
        st.success("FGE · partições de um conjunto rotulado" if rotulados else "FGO · perfis de tamanhos")
    with b:
        st.subheader("Todos os agrupamentos")
        if rotulados:
            fichas(["{A} | {B} | {C}", "{A,B} | {C}", "{A,C} | {B}", "{B,C} | {A}"])
            st.caption("A, B e C identificam unidades diferentes. Há três maneiras de escolher o par.")
        else:
            fichas(["1 + 1 + 1", "1 + 2"])
            st.caption("Sem IDs, só importa a quantidade de blocos de cada tamanho.")
    destaque("OBSERVE A MUDANÇA", "O tamanho dos blocos é o mesmo. A identidade dos dados muda a contagem: de 2 para 4.")
    with st.expander("Ver a modelagem matemática"):
        st.latex(r"G(x)=\frac{1}{(1-x)(1-x^2)}\quad\Rightarrow\quad[x^3]G(x)=2")
        st.latex(r"E(x)=\exp\left(x+\frac{x^2}{2!}\right)\quad\Rightarrow\quad3![x^3]E(x)=4")
        st.write("É um modelo simplificado de agrupamento, não uma implementação de TCP. Pacotes contíguos de um fluxo, ordem de transmissão e cabeçalhos exigem outro modelo.")
    fala("Sem identidade, temos dois perfis. Ao ligar os IDs, o par AB é diferente de AC e BC. Esse é um exemplo de FGE mesmo sem ordenar os pacotes: identidade e ordem são conceitos diferentes.")


@st.cache_data(show_spinner=False)
def escala_calculada(n):
    return senhas_modelo(n, 8, 3, True)[n], senhas_fechada(n, 8, 3)


def escala_guiada():
    st.header("Contar sem listar: por que isso importa?")
    n = st.select_slider("Posições · alfabeto com 8 símbolos, 3 com ocorrência par", options=[4, 6, 8, 10, 12, 15], value=10, key="escala_n")
    validas, confirmacao = escala_calculada(n)
    total = 8**n
    operacoes = 8 * (n+1) * (n+2) // 2
    a, b, c = st.columns(3)
    a.metric("Candidatas a testar", numero(total))
    b.metric("Termos no produto FGE", numero(operacoes))
    c.metric("Senhas válidas", numero(validas))
    st.caption("Termos são parcelas das convoluções, não instruções de CPU; a força bruta ainda percorre as posições de cada candidata.")
    dados = pd.DataFrame([{"N": i, "Quantidade": float(valor), "Trabalho": tipo, "Exato": numero(valor)}
        for i in range(1, n+1) for tipo, valor in [
            ("Candidatas · 8ⁿ", 8**i), ("Termos · produto FGE", 8*(i+1)*(i+2)//2)]])
    grafico = alt.Chart(dados).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("N:Q", axis=alt.Axis(tickMinStep=1), title="Posições da senha"),
        y=alt.Y("Quantidade:Q", scale=alt.Scale(type="log"), title="Quantidade · escala logarítmica"),
        color=alt.Color("Trabalho:N", scale=alt.Scale(range=["#f59e0b", "#14b8a6"]), legend=alt.Legend(orient="bottom")),
        tooltip=["N", "Trabalho", "Exato"])
    st.altair_chart(grafico.properties(height=240), width="stretch")
    st.success(f"FGE e filtro de paridade concordam: {numero(confirmacao)}. Nenhuma das {numero(total)} candidatas foi enumerada nesta etapa.")
    with st.expander("Ver código, complexidade e memória"):
        st.code('''# Convolução de FGE: guardamos contagens a[n], não frações.
for n in range(N + 1):
    c[n] = sum(comb(n, j) * a[j] * b[n-j]
               for j in range(n + 1))''', language="python")
        st.write("Força bruta: O(Kⁿ · n). Produto FGE: O(K · n²) operações aritméticas, O(n) inteiros auxiliares. O custo de inteiros grandes também cresce.")
        st.write("A enumeração por gerador também evita guardar todas as senhas. A vantagem demonstrada é contar sem percorrer o espaço de busca, não uma obrigação de materializar tudo na RAM.")
        st.write("O filtro de paridade usa P+1 termos e é uma alternativa especializada para esta regra. A FGE fornece uma construção que pode ser adaptada a outras restrições.")
    fala("Ao aumentar o tamanho, o número de candidatas cresce exponencialmente. O cálculo dos coeficientes cresce de forma polinomial em operações aritméticas. Estamos comparando trabalho teórico, não prometendo um tempo fixo de execução.")


def mudar_etapa(delta):
    st.session_state["etapa_guia"] = max(0, min(4, st.session_state.get("etapa_guia", 0) + delta))


def main():
    st.set_page_config(page_title="FGO × FGE · Equipe 7", page_icon="🧮", layout="wide", initial_sidebar_state="collapsed")
    st.markdown('''<style>
    .block-container {max-width:1120px; padding-top:4rem; padding-bottom:2rem;}
    [data-testid="stVerticalBlock"] {gap:.75rem;}
    [data-testid="stDivider"] {margin:.25rem 0;}
    h1 {font-size:2rem !important;} h2 {font-size:1.9rem !important;}
    [data-testid="stMetric"] {border:1px solid #14b8a650; border-radius:14px; padding:14px; background:#14b8a60a;}
    .destaque {border-left:4px solid #14b8a6; background:#14b8a612; padding:14px 20px; border-radius:8px; margin:16px 0;}
    .destaque small {font-weight:700; letter-spacing:.08em;}
    .destaque p {font-size:1.2rem; margin:6px 0;}
    .fichas {display:flex; gap:10px; flex-wrap:wrap; margin:16px 0;}
    .ficha {font:600 1.2rem monospace; border:1px solid #8b5cf680; background:#8b5cf614; border-radius:10px; padding:12px 16px;}
    @media(max-width:640px) {h1 {font-size:1.8rem !important;} .ficha {font-size:1rem; padding:9px;}}
    </style>''', unsafe_allow_html=True)
    modo = st.sidebar.radio("Como você quer usar?", ["Apresentação guiada", "Laboratório completo"], key="modo")
    st.sidebar.caption("Equipe 7 · FGE e estruturas rotuladas")
    if st.sidebar.button("Recomeçar apresentação"):
        st.session_state["etapa_guia"] = 0
        for chave in ("caso_senha", "g_k", "g_n", "g_p", "ids_guiados", "escala_n"):
            st.session_state.pop(chave, None)
        st.rerun()
    if modo == "Laboratório completo":
        laboratorio()
        return
    st.title("FGO × FGE")
    st.caption("Equipe 7 · Estruturas rotuladas · Da contagem às aplicações em computação")
    st.session_state.setdefault("etapa_guia", 0)
    etapa = st.session_state["etapa_guia"]
    st.progress((etapa + 1) / 5, text=f"Etapa {etapa+1} de 5 · {ETAPAS[etapa].split(' · ')[1]}")
    anterior, seletor, proxima = st.columns([1, 3, 1])
    anterior.button("← Anterior", disabled=etapa == 0, on_click=mudar_etapa, args=(-1,), width="stretch")
    seletor.selectbox("Ir para a etapa", range(5), format_func=lambda i: ETAPAS[i], key="etapa_guia", label_visibility="collapsed")
    proxima.button("Próxima →", disabled=etapa == 4, type="primary", on_click=mudar_etapa, args=(1,), width="stretch")
    st.divider()
    [ideia, matematica, senhas_guiadas, comunicacao_guiada, escala_guiada][etapa]()
    st.divider()
    st.caption("Sugestão para 10 min: ideia 2 min · matemática 3 min · senhas 2 min · comunicação 1,5 min · escala 1,5 min. Metade do tempo é prática.")
    with st.expander("Dúvidas da banca e referências"):
        st.markdown("**FGO não conta ordem?** Conta, sim: 1/(1−Kx) gera Kⁿ. A comparação por símbolo deste app usa outra construção.")
        st.markdown("**Por que n!?** O coeficiente na FGE é aₙ/n!; o produto distribui os rótulos por escolhas binomiais.")
        st.markdown("**Mais regras tornam uma senha mais segura?** Não necessariamente. Reduzir possibilidades pode facilitar a busca; a distribuição e o comprimento também importam.")
        st.markdown("**Pacotes sempre usam FGE?** Depende do objeto contado. Aqui são blocos sem ordem; um fluxo contíguo é outro problema.")
        st.markdown("Referências: Flajolet e Sedgewick, [Analytic Combinatorics · cap. I e II](https://ac.cs.princeton.edu/home/); Sedgewick e Flajolet, [Generating Functions](https://aofa.cs.princeton.edu/30gf/).")


if __name__ == "__main__":
    main()
