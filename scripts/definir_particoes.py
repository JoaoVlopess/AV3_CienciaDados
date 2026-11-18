"""
Definição das partições treino / validação / teste — NWPU-RESISC45 (10 classes).

- Estratificada por classe (mesma proporção em cada classe).
- Semente fixa (reprodutível).
- Agrupada: arquivos registrados como duplicatas exatas (dados/duplicatas_exatas.csv) ou
  quase-duplicatas confirmadas (dados/candidatas_quase_duplicatas.csv) são sempre colocados
  na MESMA partição, evitando que a mesma cena apareça em treino e em validação/teste.
- Nenhum arquivo é copiado, movido ou excluído: as partições são listas de caminhos em dados/splits/.

Uso (a partir da raiz do projeto):
    python -I scripts/definir_particoes.py --projeto . [--treino 0.70 --validacao 0.15 --teste 0.15 --semente 42]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

CLASSES = ["airport", "beach", "circular_farmland", "dense_residential", "desert",
           "forest", "harbor", "mountain", "river", "storage_tank"]
PARTICOES = ["treino", "validacao", "teste"]


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projeto", required=True, type=Path)
    ap.add_argument("--treino", type=float, default=0.70)
    ap.add_argument("--validacao", type=float, default=0.15)
    ap.add_argument("--teste", type=float, default=0.15)
    ap.add_argument("--semente", type=int, default=42)
    args = ap.parse_args()
    proporcoes = {"treino": args.treino, "validacao": args.validacao, "teste": args.teste}
    if abs(sum(proporcoes.values()) - 1) > 1e-9:
        raise SystemExit("As proporções devem somar 1.")

    raiz = args.projeto.resolve()
    dados = raiz / "dados"
    inventario = [r for r in ler_csv(dados / "inventario_arquivos.csv") if r["valido"] == "True"]

    # ---- grupos que não podem ser separados (union-find simples)
    pai: dict[str, str] = {r["arquivo"]: r["arquivo"] for r in inventario}

    def raiz_de(x: str) -> str:
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    def unir(a: str, b: str) -> None:
        if a in pai and b in pai:
            pai[raiz_de(a)] = raiz_de(b)

    por_grupo_dup: dict[str, list[str]] = defaultdict(list)
    for r in ler_csv(dados / "duplicatas_exatas.csv"):
        por_grupo_dup[r["grupo"]].append(r["arquivo"])
    for membros in por_grupo_dup.values():
        for m in membros[1:]:
            unir(membros[0], m)
    for r in ler_csv(dados / "candidatas_quase_duplicatas.csv"):
        if r["avaliacao"].startswith("quase_duplicata"):
            unir(r["arquivo_a"], r["arquivo_b"])

    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in inventario:
        grupos[raiz_de(r["arquivo"])].append(r)

    # ---- atribuição estratificada por classe
    rng = random.Random(args.semente)
    atribuicao: dict[str, str] = {}
    grupo_id: dict[str, int] = {}
    for classe in CLASSES:
        gs = sorted((g for g in grupos.values() if g[0]["classe"] == classe), key=lambda g: g[0]["arquivo"])
        if any(len({m["classe"] for m in g}) > 1 for g in gs):
            raise SystemExit("Grupo de duplicatas entre classes: tratar antes de particionar.")
        rng.shuffle(gs)
        total = sum(len(g) for g in gs)
        alvo = {"validacao": round(total * proporcoes["validacao"]), "teste": round(total * proporcoes["teste"])}
        alvo["treino"] = total - alvo["validacao"] - alvo["teste"]
        cont = Counter()
        for g in gs:
            cabe = [p for p in PARTICOES if cont[p] + len(g) <= alvo[p]]
            destino = cabe[0] if cabe else max(PARTICOES, key=lambda p: alvo[p] - cont[p])
            for m in g:
                atribuicao[m["arquivo"]] = destino
                grupo_id[m["arquivo"]] = len(g)
            cont[destino] += len(g)

    # ---- saída
    saida = dados / "splits"
    saida.mkdir(exist_ok=True)
    linhas = sorted(({"arquivo": r["arquivo"], "classe": r["classe"], "particao": atribuicao[r["arquivo"]],
                      "tamanho_grupo": grupo_id[r["arquivo"]]} for r in inventario),
                    key=lambda r: (PARTICOES.index(r["particao"]), CLASSES.index(r["classe"]), r["arquivo"]))
    campos = ["arquivo", "classe", "particao", "tamanho_grupo"]
    with (saida / "particoes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    for p in PARTICOES:
        with (saida / f"{p}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["arquivo", "classe"])
            w.writeheader()
            w.writerows({"arquivo": r["arquivo"], "classe": r["classe"]} for r in linhas if r["particao"] == p)

    # ---- verificações
    conj = {p: {r["arquivo"] for r in linhas if r["particao"] == p} for p in PARTICOES}
    sobreposicao = {f"{a}&{b}": len(conj[a] & conj[b]) for i, a in enumerate(PARTICOES) for b in PARTICOES[i + 1:]}
    grupos_divididos = sum(1 for g in grupos.values() if len({atribuicao[m["arquivo"]] for m in g}) > 1)
    inexistentes = [r["arquivo"] for r in linhas if not (raiz / r["arquivo"]).is_file()]
    contagem = {c: {p: sum(1 for r in linhas if r["classe"] == c and r["particao"] == p) for p in PARTICOES}
                for c in CLASSES}
    resumo = {
        "semente": args.semente,
        "proporcoes": proporcoes,
        "total": len(linhas),
        "por_particao": {p: len(conj[p]) for p in PARTICOES},
        "por_classe": contagem,
        "sobreposicao_entre_particoes": sobreposicao,
        "grupos_de_duplicatas": sum(1 for g in grupos.values() if len(g) > 1),
        "grupos_divididos_entre_particoes": grupos_divididos,
        "arquivos_inexistentes": len(inexistentes),
    }
    (saida / "resumo_particoes.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: resumo[k] for k in ("total", "por_particao", "sobreposicao_entre_particoes",
                                             "grupos_de_duplicatas", "grupos_divididos_entre_particoes",
                                             "arquivos_inexistentes")}, ensure_ascii=False))
    if any(sobreposicao.values()) or grupos_divididos or inexistentes:
        raise SystemExit("Falha na verificação das partições.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
