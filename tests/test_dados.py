"""Testes dos dados do Guia de Emergências.

Uso:  python3 tests/test_dados.py      (também corre com pytest)

- O emergencias_medicas.json e a cópia embutida no index.html têm de ser iguais.
- Os valores pediátricos da ficha "Abordagem e Avaliação da Vítima Pediátrica"
  têm de bater com os limites do Simulador de Triagem (parametros_vitais.json,
  bloco limites_alerta_inem). O simulador é procurado na variável de ambiente
  SIMULADOR_TRIAGEM_DIR, em ../simulador-triagem ou numa pasta ao lado com o
  parametros_vitais.json; se não existir, o teste é ignorado.
"""
import glob
import json
import os
import re
import sys
import traceback
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHA_ID = "abordagem_avaliacao_pediatrica"


def carregar_json():
    with open(os.path.join(RAIZ, "emergencias_medicas.json"), encoding="utf-8") as f:
        return json.load(f)


def carregar_embutido():
    with open(os.path.join(RAIZ, "index.html"), encoding="utf-8") as f:
        html = f.read()
    blocos = re.findall(r'<script type="application/json" id="data-source"[^>]*>(.*?)</script>', html, re.S)
    assert len(blocos) == 1, "bloco data-source não encontrado (ou repetido) no index.html"
    return json.loads(blocos[0])


def ficha_pediatrica(dados):
    for categoria in dados["categorias"]:
        for condicao in categoria["condicoes"]:
            if condicao["id"] == FICHA_ID:
                return condicao
    raise AssertionError(f"ficha {FICHA_ID} não encontrada")


def limites_do_simulador():
    candidatos = [os.environ.get("SIMULADOR_TRIAGEM_DIR"), os.path.join(RAIZ, "..", "simulador-triagem")]
    candidatos += sorted(os.path.dirname(p) for p in glob.glob(os.path.join(RAIZ, "..", "*", "parametros_vitais.json")))
    for pasta in candidatos:
        if not pasta:
            continue
        caminho = os.path.join(pasta, "parametros_vitais.json")
        if os.path.isfile(caminho):
            with open(caminho, encoding="utf-8") as f:
                dados = json.load(f)
            if "limites_alerta_inem" in dados:
                return dados["limites_alerta_inem"]
    return None


# ---------------------------------------------------------------------------

def test_json_e_copia_embutida_iguais():
    assert carregar_json() == carregar_embutido(), (
        "o emergencias_medicas.json e o bloco data-source do index.html são diferentes"
    )


def test_ficha_pediatrica_sem_tabela_antiga_nem_campos_duplicados():
    ficha = ficha_pediatrica(carregar_json())
    antigos = {"parametros_referencia_por_idade", "calculo_peso", "frequencia_cardiaca_referencia",
               "frequencia_respiratoria_referencia", "pressao_arterial_sistolica_limite_inferior_aceitavel",
               "pressao_arterial_minima_aceitavel"}
    assert not antigos & set(ficha), f"campos antigos ainda na ficha: {sorted(antigos & set(ficha))}"
    tabela = ficha["parametros_referencia_por_grupo_etario"]
    for linha in tabela.values():
        assert not any("PAD" in k or "diast" in k.lower() for k in linha), "a PAD não deve aparecer na tabela"
    assert "INEM" in ficha["fonte_parametros_pediatricos"]


def _numeros(texto):
    return [int(n) for n in re.findall(r"\d+", texto)]


def _pas(base, por_ano, maior_que=False):
    return (f"{base} + {por_ano} × idade" if por_ano else ("> " if maior_que else "") + str(base)) + " mmHg"


def test_valores_pediatricos_iguais_ao_simulador():
    limites = limites_do_simulador()
    if limites is None:
        raise unittest.SkipTest("Simulador de Triagem não encontrado ao lado deste projeto: teste ignorado "
                                "(defina SIMULADOR_TRIAGEM_DIR para o correr)")
    tabela = ficha_pediatrica(carregar_json())["parametros_referencia_por_grupo_etario"]
    grupos = limites["grupos"]
    assert list(tabela) == [g["grupo"] for g in grupos], "os grupos etários da ficha não batem com o simulador"
    pesos = limites["peso_estimado"]
    for g in grupos:
        linha = tabela[g["grupo"]]
        assert _numeros(linha["FC"]) == [g["fc_min"], g["fc_max"]], (g["grupo"], "FC")
        assert _numeros(linha["FR"]) == [g["fr_min"], g["fr_max"]], (g["grupo"], "FR")
        assert linha["PAS normal"] == _pas(g["pas_normal_base"], g["pas_normal_por_ano"], g.get("pas_normal_maior_que", False)), (g["grupo"], "PAS normal")
        assert linha["PAS mínima aceitável"] == _pas(g["pas_min_base"], g["pas_min_por_ano"]), (g["grupo"], "PAS mínima")
        assert linha["Hipoglicemia"] == f"< {g['glicemia_min']} mg/dL", (g["grupo"], "hipoglicemia")
        regra = [r for r in pesos["regras"] if r["idade_min_meses"] <= g["idade_min_meses"] and g["idade_max_meses"] <= r["idade_max_meses"]]
        assert linha["Peso estimado"] == (regra[0]["formula"] if regra else pesos["recem_nascido"]), (g["grupo"], "peso")


# ---------------------------------------------------------------------------

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
