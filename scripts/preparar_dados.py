"""
Preparação inicial dos dados brutos — NWPU-RESISC45 (10 classes).

Etapas:
  1. Confere a estrutura do dataset original (45 pastas, 700 imagens cada).
  2. Copia exclusivamente as 10 classes selecionadas para dados/raw/
     (o dataset original nunca é alterado; arquivos já existentes não são sobrescritos).
  3. Valida a seleção (exatamente 10 pastas, nomes corretos, sem pastas extras).
  4. Verifica cada imagem: leitura/decodificação, formato, 256x256, 3 canais RGB,
     arquivos vazios e integridade da cópia (SHA-256 idêntico ao original).
  5. Identifica duplicatas exatas (SHA-256) dentro e entre classes e lista
     candidatas a quase-duplicatas (dHash) apenas para inspeção visual.
  6. Gera relatórios em dados/.

Nenhuma imagem é excluída ou modificada automaticamente.

Uso (a partir da raiz do projeto):
    python -I scripts/preparar_dados.py --origem NWPU-RESISC45/NWPU-RESISC45 --projeto .
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import PIL
from PIL import Image, ImageChops, ImageStat

CLASSES_SELECIONADAS = [
    "airport",
    "beach",
    "circular_farmland",
    "dense_residential",
    "desert",
    "forest",
    "harbor",
    "mountain",
    "river",
    "storage_tank",
]
TOTAL_CLASSES_ORIGINAL = 45
IMAGENS_POR_CLASSE = 700
LARGURA, ALTURA = 256, 256
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
LIMIAR_DHASH = 4  # distância de Hamming máxima (de 64 bits) para candidatas a quase-duplicatas
LIMIAR_DIF_PIXEL = 2.0  # diferença média por pixel (0–255) abaixo da qual o par é considerado a mesma cena


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def dhash(img: Image.Image, tamanho: int = 8) -> int:
    """Hash perceptual por diferença (64 bits)."""
    cinza = img.convert("L").resize((tamanho + 1, tamanho), Image.Resampling.LANCZOS)
    obter = getattr(cinza, "get_flattened_data", None) or cinza.getdata  # Pillow >= 12.1 / anteriores
    px = list(obter())
    bits = 0
    for linha in range(tamanho):
        for col in range(tamanho):
            esq = px[linha * (tamanho + 1) + col]
            dir_ = px[linha * (tamanho + 1) + col + 1]
            bits = (bits << 1) | (1 if esq > dir_ else 0)
    return bits


def escrever_csv(caminho: Path, campos: list[str], linhas: list[dict]) -> None:
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origem", required=True, type=Path, help="Pasta com as 45 classes originais")
    ap.add_argument("--projeto", required=True, type=Path, help="Raiz do projeto (onde fica dados/)")
    args = ap.parse_args()

    origem: Path = args.origem.resolve()
    dados: Path = (args.projeto / "dados").resolve()
    raw: Path = dados / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    ocorrencias: list[dict] = []

    def registrar(tipo: str, classe: str, caminho: str, descricao: str, acao: str = "registrado; nenhuma alteração") -> None:
        ocorrencias.append({"tipo": tipo, "classe": classe, "caminho": caminho, "descricao": descricao, "acao": acao})

    # ------------------------------------------------------------------ 1. Estrutura original
    print(f"[1/6] Conferindo dataset original em {origem}")
    pastas_orig = sorted(p.name for p in origem.iterdir() if p.is_dir())
    arquivos_soltos = sorted(p.name for p in origem.iterdir() if p.is_file())
    estrutura_original = []
    for nome in pastas_orig:
        arqs = [a for a in (origem / nome).iterdir() if a.is_file()]
        imgs = [a for a in arqs if a.suffix.lower() in EXTENSOES_IMAGEM]
        prefixo_ok = all(a.stem.startswith(nome + "_") for a in imgs)
        estrutura_original.append({
            "classe": nome,
            "selecionada": "sim" if nome in CLASSES_SELECIONADAS else "nao",
            "arquivos": len(arqs),
            "imagens": len(imgs),
            "nomenclatura_ok": "sim" if prefixo_ok else "nao",
        })
        if len(imgs) != IMAGENS_POR_CLASSE:
            registrar("contagem_original_divergente", nome, str(origem / nome),
                      f"{len(imgs)} imagens no original (esperado {IMAGENS_POR_CLASSE})")
        if not prefixo_ok:
            registrar("nomenclatura_original_divergente", nome, str(origem / nome),
                      "há arquivos cujo nome não começa com '<classe>_'")
    if len(pastas_orig) != TOTAL_CLASSES_ORIGINAL:
        registrar("estrutura_original", "-", str(origem),
                  f"{len(pastas_orig)} pastas encontradas (esperado {TOTAL_CLASSES_ORIGINAL})")
    for a in arquivos_soltos:
        registrar("arquivo_solto_original", "-", str(origem / a), "arquivo fora das pastas de classe")
    escrever_csv(dados / "estrutura_original.csv",
                 ["classe", "selecionada", "arquivos", "imagens", "nomenclatura_ok"], estrutura_original)
    print(f"      {len(pastas_orig)} pastas, {sum(e['imagens'] for e in estrutura_original)} imagens")

    ausentes_origem = [c for c in CLASSES_SELECIONADAS if c not in pastas_orig]
    for c in ausentes_origem:
        registrar("classe_obrigatoria_ausente_origem", c, str(origem / c), "classe exigida não existe no original")

    # ------------------------------------------------------------------ 2. Cópia das 10 classes
    print("[2/6] Copiando as 10 classes selecionadas para dados/raw/")
    copiados = ja_existentes = 0
    for classe in CLASSES_SELECIONADAS:
        if classe in ausentes_origem:
            continue
        destino_cls = raw / classe
        destino_cls.mkdir(exist_ok=True)
        for src in sorted((origem / classe).iterdir()):
            if not src.is_file():
                continue
            dst = destino_cls / src.name
            if dst.exists():
                ja_existentes += 1
                continue  # nunca sobrescreve; a integridade é conferida na etapa 4
            shutil.copy2(src, dst)
            copiados += 1
    print(f"      {copiados} arquivos copiados, {ja_existentes} já existiam (não sobrescritos)")

    # ------------------------------------------------------------------ 3. Validação da seleção
    print("[3/6] Validando a seleção")
    pastas_raw = sorted(p.name for p in raw.iterdir() if p.is_dir())
    extras = [p for p in pastas_raw if p not in CLASSES_SELECIONADAS]
    faltando = [c for c in CLASSES_SELECIONADAS if c not in pastas_raw]
    for p in extras:
        registrar("pasta_adicional", p, str(raw / p), "pasta não autorizada em dados/raw/",
                  "registrado; remover manualmente após conferência")
    for c in faltando:
        registrar("classe_obrigatoria_ausente", c, str(raw / c), "classe obrigatória ausente em dados/raw/")
    for a in (p for p in raw.iterdir() if p.is_file()):
        registrar("arquivo_solto_raw", "-", str(a), "arquivo fora das pastas de classe em dados/raw/")
    validacao_selecao = {
        "pastas_em_raw": len(pastas_raw),
        "exatamente_10_pastas": len(pastas_raw) == len(CLASSES_SELECIONADAS),
        "nomes_corretos": pastas_raw == sorted(CLASSES_SELECIONADAS),
        "pastas_adicionais": extras,
        "classes_ausentes": faltando,
    }
    print(f"      {validacao_selecao}")

    # ------------------------------------------------------------------ 4. Integridade das imagens
    print("[4/6] Verificando integridade de cada imagem")
    inventario: list[dict] = []
    por_classe: dict[str, dict] = {}
    for classe in CLASSES_SELECIONADAS:
        pasta = raw / classe
        stats = {"encontradas": 0, "validas": 0, "invalidas": 0, "nao_imagem": 0}
        por_classe[classe] = stats
        if not pasta.is_dir():
            continue
        for arq in sorted(pasta.iterdir()):
            if not arq.is_file():
                continue
            rel = arq.relative_to(dados.parent).as_posix()
            if arq.suffix.lower() not in EXTENSOES_IMAGEM:
                stats["nao_imagem"] += 1
                registrar("arquivo_nao_imagem", classe, rel, f"extensão '{arq.suffix}' ignorada na contagem")
                continue
            stats["encontradas"] += 1
            reg = {"classe": classe, "arquivo": rel, "bytes": arq.stat().st_size, "sha256": "",
                   "formato": "", "largura": "", "altura": "", "modo": "", "canais": "",
                   "dhash": "", "copia_identica_original": "", "valido": False, "problemas": ""}
            problemas = []
            if reg["bytes"] == 0:
                problemas.append("arquivo vazio")
            else:
                reg["sha256"] = sha256(arq)
                orig = origem / classe / arq.name
                if orig.exists():
                    igual = sha256(orig) == reg["sha256"]
                    reg["copia_identica_original"] = "sim" if igual else "nao"
                    if not igual:
                        problemas.append("conteúdo difere do arquivo original")
                else:
                    reg["copia_identica_original"] = "sem_original"
                    problemas.append("arquivo não existe no dataset original")
                try:
                    with Image.open(arq) as im:
                        im.verify()
                    with Image.open(arq) as im:
                        im.load()  # decodificação completa
                        reg["formato"] = im.format
                        reg["largura"], reg["altura"] = im.size
                        reg["modo"] = im.mode
                        reg["canais"] = len(im.getbands())
                        reg["dhash"] = f"{dhash(im):016x}"
                    if reg["formato"] != "JPEG" and arq.suffix.lower() in {".jpg", ".jpeg"}:
                        problemas.append(f"extensão .jpg mas formato {reg['formato']}")
                    if (reg["largura"], reg["altura"]) != (LARGURA, ALTURA):
                        problemas.append(f"dimensão {reg['largura']}x{reg['altura']} (esperado {LARGURA}x{ALTURA})")
                    if reg["modo"] != "RGB" or reg["canais"] != 3:
                        problemas.append(f"modo {reg['modo']} com {reg['canais']} canais (esperado RGB, 3)")
                except Exception as e:  # noqa: BLE001
                    problemas.append(f"falha ao abrir/decodificar: {type(e).__name__}: {e}")
            reg["valido"] = not problemas
            reg["problemas"] = "; ".join(problemas)
            if problemas:
                stats["invalidas"] += 1
                registrar("imagem_invalida", classe, rel, reg["problemas"])
            else:
                stats["validas"] += 1
            inventario.append(reg)
        print(f"      {classe:18s} {stats}")

    # ------------------------------------------------------------------ 5. Duplicatas
    print("[5/6] Procurando duplicatas")
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in inventario:
        if r["sha256"]:
            grupos[r["sha256"]].append(r)
    dup_rows = []
    dup_por_classe = defaultdict(int)
    gid = 0
    for h, membros in sorted(grupos.items()):
        if len(membros) < 2:
            continue
        gid += 1
        classes = sorted({m["classe"] for m in membros})
        escopo = "mesma_classe" if len(classes) == 1 else "entre_classes"
        for m in membros:
            dup_por_classe[m["classe"]] += 1
            dup_rows.append({"grupo": gid, "sha256": h, "escopo": escopo, "classe": m["classe"],
                             "arquivo": m["arquivo"], "tamanho_grupo": len(membros)})
        registrar("duplicata_exata", ",".join(classes), " | ".join(m["arquivo"] for m in membros),
                  f"grupo {gid}: {len(membros)} arquivos idênticos ({escopo})",
                  "registrado; não excluído (decisão posterior)")
    escrever_csv(dados / "duplicatas_exatas.csv",
                 ["grupo", "sha256", "escopo", "classe", "arquivo", "tamanho_grupo"], dup_rows)
    print(f"      {gid} grupos de duplicatas exatas ({len(dup_rows)} arquivos)")

    # Quase-duplicatas (apenas candidatas para inspeção visual; não entram no relatório como duplicatas)
    itens = [(r, int(r["dhash"], 16)) for r in inventario if r["dhash"]]
    exatos = {r["arquivo"]: r["sha256"] for r, _ in itens}
    quase = []
    for i in range(len(itens)):
        ri, hi = itens[i]
        for j in range(i + 1, len(itens)):
            rj, hj = itens[j]
            d = (hi ^ hj).bit_count()
            if d <= LIMIAR_DHASH and exatos[ri["arquivo"]] != exatos[rj["arquivo"]]:
                quase.append({"arquivo_a": ri["arquivo"], "classe_a": ri["classe"],
                              "arquivo_b": rj["arquivo"], "classe_b": rj["classe"],
                              "distancia_dhash": d,
                              "escopo": "mesma_classe" if ri["classe"] == rj["classe"] else "entre_classes"})
    quase.sort(key=lambda q: (q["distancia_dhash"], q["arquivo_a"]))
    # Confirmação objetiva: diferença absoluta média por pixel (0–255) entre as duas imagens.
    for q in quase:
        with Image.open(dados.parent / q["arquivo_a"]) as a, Image.open(dados.parent / q["arquivo_b"]) as b:
            dif = ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean
        q["diferenca_media_pixel"] = round(sum(dif) / len(dif), 3)
        q["avaliacao"] = ("quase_duplicata_confirmada (mesma cena, recodificada)"
                          if q["diferenca_media_pixel"] <= LIMIAR_DIF_PIXEL
                          else "falso_positivo (cenas distintas)")
    escrever_csv(dados / "candidatas_quase_duplicatas.csv",
                 ["arquivo_a", "classe_a", "arquivo_b", "classe_b", "distancia_dhash", "escopo",
                  "diferenca_media_pixel", "avaliacao"], quase)
    print(f"      {len(quase)} pares candidatos a quase-duplicata (dHash <= {LIMIAR_DHASH})")

    # ------------------------------------------------------------------ 6. Relatórios
    print("[6/6] Gerando relatórios")
    relatorio = []
    for classe in CLASSES_SELECIONADAS:
        s = por_classe[classe]
        if classe in faltando:
            status = "AUSENTE"
        elif s["encontradas"] != IMAGENS_POR_CLASSE or s["invalidas"] > 0:
            status = "INCONSISTENTE"
        elif dup_por_classe[classe] > 0:
            status = "OK_COM_DUPLICATAS"
        else:
            status = "OK"
        relatorio.append({
            "classe": classe,
            "quantidade_esperada": IMAGENS_POR_CLASSE,
            "quantidade_encontrada": s["encontradas"],
            "diferenca": s["encontradas"] - IMAGENS_POR_CLASSE,
            "arquivos_validos": s["validas"],
            "arquivos_invalidos": s["invalidas"],
            "duplicatas_exatas": dup_por_classe[classe],
            "status": status,
        })
    tot = {k: sum(r[k] for r in relatorio) for k in
           ["quantidade_esperada", "quantidade_encontrada", "diferenca", "arquivos_validos",
            "arquivos_invalidos", "duplicatas_exatas"]}
    relatorio.append({"classe": "TOTAL", **tot,
                      "status": "OK" if all(r["status"] == "OK" for r in relatorio) else "VER_OCORRENCIAS"})
    escrever_csv(dados / "relatorio_preparacao.csv",
                 ["classe", "quantidade_esperada", "quantidade_encontrada", "diferenca", "arquivos_validos",
                  "arquivos_invalidos", "duplicatas_exatas", "status"], relatorio)

    escrever_csv(dados / "inventario_arquivos.csv",
                 ["classe", "arquivo", "bytes", "sha256", "formato", "largura", "altura", "modo", "canais",
                  "dhash", "copia_identica_original", "valido", "problemas"], inventario)

    for q in quase:
        registrar("candidata_quase_duplicata", f"{q['classe_a']},{q['classe_b']}",
                  f"{q['arquivo_a']} | {q['arquivo_b']}",
                  f"dHash a {q['distancia_dhash']} bits ({q['escopo']}); diferença média por pixel "
                  f"{q['diferenca_media_pixel']} -> {q['avaliacao']}",
                  "registrado; não excluído")
    escrever_csv(dados / "registro_ocorrencias.csv", ["tipo", "classe", "caminho", "descricao", "acao"], ocorrencias)

    resumo = {
        "executado_em": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "pillow": PIL.__version__,
        "sistema": platform.platform(),
        "origem": str(origem),
        "destino": str(raw),
        "classes_originais": len(pastas_orig),
        "imagens_originais": sum(e["imagens"] for e in estrutura_original),
        "classes_selecionadas": CLASSES_SELECIONADAS,
        "arquivos_copiados_nesta_execucao": copiados,
        "arquivos_ja_existentes": ja_existentes,
        "validacao_selecao": validacao_selecao,
        "totais": tot,
        "grupos_duplicatas_exatas": gid,
        "pares_quase_duplicatas": len(quase),
        "quase_duplicatas_confirmadas": sum(1 for q in quase if q["avaliacao"].startswith("quase_duplicata")),
        "limiar_dhash": LIMIAR_DHASH,
        "limiar_diferenca_pixel": LIMIAR_DIF_PIXEL,
        "ocorrencias_registradas": len(ocorrencias),
        "exclusoes_realizadas": 0,
    }
    (dados / "resumo_preparacao.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumo["totais"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
