"""Segurança do Guia de Emergências.

Content-Security-Policy: cada página tem a CSP e os hashes dos scripts
embutidos estão atualizados. Se editar um <script> dentro de um .html, corra
`python3 ferramentas/atualizar_csp.py` (explicação no próprio ficheiro).

Uso:  python3 tests/test_seguranca.py      (também corre com pytest)
"""
import os
import sys
import traceback
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))

import atualizar_csp  # noqa: E402


def test_csp_presente_e_atualizada():
    problemas = atualizar_csp.verificar(RAIZ)
    assert not problemas, "\n".join(problemas) + "\nCorra: python3 ferramentas/atualizar_csp.py"


def test_pagina_de_privacidade_ligada_em_todas_as_paginas():
    assert os.path.exists(os.path.join(RAIZ, "privacidade.html"))
    for nome in ("index.html", "anatomia.html"):
        with open(os.path.join(RAIZ, nome), encoding="utf-8") as f:
            assert 'href="privacidade.html"' in f.read(), nome


if __name__ == "__main__":
    passaram, falharam, ignorados = 0, 0, 0
    for nome in sorted(n for n in dir(sys.modules[__name__]) if n.startswith("test_")):
        try:
            globals()[nome]()
        except unittest.SkipTest as e:
            ignorados += 1
            print(f"  IGNORADO  {nome}: {e}")
        except Exception:
            falharam += 1
            print(f"  FALHOU    {nome}\n" + traceback.format_exc())
        else:
            passaram += 1
            print(f"  ok        {nome}")
    print(f"\n{passaram} passaram, {falharam} falharam, {ignorados} ignorados")
    sys.exit(1 if falharam else 0)
