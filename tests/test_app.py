import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from streamlit.testing.v1 import AppTest


def test_password_models_exhaustively():
    for n in range(7):
        for k in range(2, 5):
            for p in range(k + 1):
                brute = app.senhas_bruta(n, k, p)
                assert app.senhas_modelo(n, k, p, True)[n] == brute
                assert app.senhas_fechada(n, k, p) == brute
                # Independent enumeration of quantity profiles, not word positions.
                profiles = sum(sum(counts) == n and all(x % 2 == 0 for x in counts[:p])
                               for counts in itertools.product(range(n + 1), repeat=k))
                assert app.senhas_modelo(n, k, p, False)[n] == profiles


def test_packets_and_limits():
    for sizes in [(), (1,), (2,), (1, 2), (1, 2, 5)]:
        for n in range(8):
            assert app.pacotes_fgo(n, sizes)[n] == app.pacotes_bruta(n, sizes, False)['valor']
            assert app.pacotes_fge(n, sizes)[n] == app.pacotes_bruta(n, sizes, True)['valor']
    assert app.pacotes_bruta(8, (1, 2), True, teto=1)['valor'] is None
    assert app.executar('senhas', 10, 8, 3, limite=20_000)['bruta']['valor'] is None
    assert app.executar('pacotes', 12, tamanhos=(1, 2), distintos=True)['bruta']['valor'] is None
    for n in (4, 6, 8, 10, 12, 15):
        assert app.escala_calculada(n)[0] == app.escala_calculada(n)[1]


def test_guided_presentation():
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=20).run()
    assert not at.exception
    assert [x.value for x in at.metric] == ['3', '4']
    for step in range(1, 5):
        at.button[1].click().run()
        assert not at.exception
        assert at.session_state['etapa_guia'] == step
    at.selectbox(key='etapa_guia').select(2).run()
    at.radio(key='caso_senha').set_value('Com regra · 3 símbolos').run()
    assert not at.exception
    assert [x.value for x in at.metric] == ['81', '41', '9']
    at.radio(key='caso_senha').set_value('Explorar').run()
    at.slider(key='g_k').set_value(6).run()
    at.slider(key='g_p').set_value(6).run()
    at.slider(key='g_k').set_value(2).run()
    assert not at.exception
    at.selectbox(key='etapa_guia').select(3).run()
    at.toggle(key='ids_guiados').set_value(True).run()
    assert [x.value for x in at.metric] == ['3', '4']
    at.selectbox(key='etapa_guia').select(4).run()
    for n in (4, 15):
        at.select_slider(key='escala_n').set_value(n).run()
        assert not at.exception
    at.sidebar.button[0].click().run()
    assert at.session_state['etapa_guia'] == 0
    assert not at.exception


def test_full_laboratory():
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    at.sidebar.radio[0].set_value('Laboratório completo').run()
    assert not at.exception
