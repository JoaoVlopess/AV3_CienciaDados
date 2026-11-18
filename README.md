# Classificação de Cenas Aéreas com Redes Neurais

**Dataset:** NWPU-RESISC45 · **Disciplina:** Ciência de Dados — Unidade III
**Etapa documentada:** preparação inicial dos dados brutos (seleção, organização e validação)

---

## 1. Estrutura do projeto

```text
AV3_CienciaDados/
├── NWPU-RESISC45/NWPU-RESISC45/   # dataset original (45 classes): preservado, nunca alterado
├── dados/
│   ├── raw/                       # cópia de trabalho: somente as 10 classes selecionadas
│   │   ├── airport/  beach/  circular_farmland/  dense_residential/  desert/
│   │   └── forest/   harbor/  mountain/  river/  storage_tank/
│   ├── relatorio_preparacao.csv          # relatório consolidado por classe
│   ├── registro_ocorrencias.csv          # cada inconsistência encontrada, com caminho e ação
│   ├── duplicatas_exatas.csv             # grupos de arquivos idênticos (SHA-256)
│   ├── candidatas_quase_duplicatas.csv   # pares visualmente semelhantes (dHash) e avaliação
│   ├── inventario_arquivos.csv           # um registro por imagem (hash, formato, dimensões, canais…)
│   ├── estrutura_original.csv            # conferência das 45 pastas originais
│   └── resumo_preparacao.json            # totais, versões de software e data da execução
├── scripts/
│   └── preparar_dados.py          # procedimento completo e reproduzível
└── README.md
```

A classe de cada imagem é identificada pelo nome da pasta em que ela está. Os nomes originais das pastas e dos arquivos foram mantidos.

## 2. Como reproduzir

Requisitos: Python 3.10 ou superior e Pillow (`pip install pillow`). Os resultados abaixo foram obtidos com Python 3.13.7 e Pillow 12.1.0.

1. Baixe o NWPU-RESISC45 e extraia-o de modo que as 45 pastas fiquem em `NWPU-RESISC45/NWPU-RESISC45/`.
2. Na raiz do projeto, execute:

   ```bash
   python -I scripts/preparar_dados.py --origem NWPU-RESISC45/NWPU-RESISC45 --projeto .
   ```

O script pode ser executado novamente sem risco. Ele nunca sobrescreve arquivos que já estão em `dados/raw/`, nunca exclui imagens e nunca altera o dataset original. A cada execução, a integridade da cópia de trabalho é conferida de novo e todos os relatórios são regenerados.

## 3. Procedimento executado

| # | Etapa | O que o script faz |
|---|---|---|
| 1 | Conferência do original | Lista as pastas, verifica se são 45, conta as imagens de cada uma (esperado: 700) e confere se os arquivos seguem o padrão `<classe>_NNN.jpg`. |
| 2 | Seleção | Copia (`shutil.copy2`) somente as 10 pastas permitidas para `dados/raw/`. As outras 35 classes nunca são copiadas, por isso nada precisa ser apagado e o original fica intacto. |
| 3 | Validação da seleção | Confere se `dados/raw/` tem exatamente 10 pastas, com os nomes exigidos, sem pastas extras e sem classes faltando. |
| 4 | Integridade | Para cada imagem: verifica se o arquivo está vazio, se `PIL.Image.verify()` aceita a estrutura e se a decodificação completa (`load()`) funciona. Confere também se o formato é JPEG, se o tamanho é 256 × 256, se o modo é RGB com 3 canais e se o SHA-256 da cópia é igual ao do arquivo original. Arquivos que não são imagens seriam ignorados na contagem e registrados. |
| 5 | Duplicatas | (a) **Exatas:** compara o SHA-256 de todas as 7.000 imagens, dentro de cada classe e entre classes. (b) **Quase-duplicatas:** compara todos os pares pelo dHash de 64 bits (distância de Hamming ≤ 4). Cada par candidato é então avaliado pela diferença absoluta média por pixel: ≤ 2,0 indica a mesma cena recodificada; acima disso, falso positivo. |
| 6 | Relatórios | Gera os arquivos CSV e JSON listados na seção 1. |

## 4. Resultados

### 4.1. Dataset original

- 45 pastas presentes, todas com 700 imagens `.jpg` e com a nomenclatura esperada (31.500 imagens).
- Nenhum arquivo fora das pastas de classe.

### 4.2. Seleção (`dados/raw/`)

- Exatamente 10 pastas, com os nomes exigidos.
- Nenhuma classe obrigatória ausente e nenhuma pasta adicional.

### 4.3. Relatório de preparação (`dados/relatorio_preparacao.csv`)

| classe | esperada | encontrada | válidos | inválidos | duplicatas exatas | status |
|---|---:|---:|---:|---:|---:|---|
| airport | 700 | 700 | 700 | 0 | 12 | OK_COM_DUPLICATAS |
| beach | 700 | 700 | 700 | 0 | 0 | OK |
| circular_farmland | 700 | 700 | 700 | 0 | 0 | OK |
| dense_residential | 700 | 700 | 700 | 0 | 0 | OK |
| desert | 700 | 700 | 700 | 0 | 0 | OK |
| forest | 700 | 700 | 700 | 0 | 0 | OK |
| harbor | 700 | 700 | 700 | 0 | 0 | OK |
| mountain | 700 | 700 | 700 | 0 | 0 | OK |
| river | 700 | 700 | 700 | 0 | 0 | OK |
| storage_tank | 700 | 700 | 700 | 0 | 0 | OK |
| **TOTAL** | **7.000** | **7.000** | **7.000** | **0** | **12** | |

Na coluna `duplicatas_exatas`, conta-se o número de **arquivos** da classe que pertencem a algum grupo de arquivos idênticos. Assim, 12 arquivos correspondem a 6 pares.

### 4.4. Integridade

Todas as 7.000 imagens abrem e decodificam sem erro. Todas são JPEG, 256 × 256 e RGB com 3 canais, e nenhum arquivo está vazio. Cada cópia é byte a byte idêntica ao arquivo original (SHA-256 igual).

### 4.5. Duplicatas exatas (SHA-256)

Foram encontrados 6 pares de arquivos idênticos, todos dentro da classe `airport`. Não há duplicatas entre classes diferentes.

| grupo | arquivos |
|---:|---|
| 1 | `airport_118.jpg` = `airport_315.jpg` |
| 2 | `airport_050.jpg` = `airport_420.jpg` |
| 3 | `airport_243.jpg` = `airport_397.jpg` |
| 4 | `airport_361.jpg` = `airport_509.jpg` |
| 5 | `airport_064.jpg` = `airport_527.jpg` |
| 6 | `airport_289.jpg` = `airport_635.jpg` |

### 4.6. Quase-duplicatas (dHash + diferença por pixel)

| par | dHash | dif. média/pixel | avaliação |
|---|---:|---:|---|
| `mountain_111` × `mountain_324` | 0 | 0,034 | **Mesma cena, recodificada** (quase-duplicata confirmada) |
| `beach_106` × `desert_318` | 2 | 44,3 | Falso positivo: cenas distintas |
| `beach_106` × `beach_592` | 3 | 34,8 | Falso positivo: cenas distintas |

Os três pares também foram inspecionados visualmente, e a inspeção confirmou a avaliação automática. Os falsos positivos aparecem porque o dHash, com apenas 64 bits, não diferencia bem cenas de pouca textura e com gradiente parecido (água/areia, areia/dunas).

## 5. Ocorrências e decisões

| Tipo | Ocorrências | Ação nesta etapa |
|---|---:|---|
| Pastas obrigatórias ausentes | 0 | — |
| Pastas adicionais | 0 | — |
| Imagens corrompidas / ilegíveis / vazias | 0 | — |
| Dimensões ou canais inesperados | 0 | — |
| Duplicatas exatas | 6 pares (12 arquivos, `airport`) | Registradas, **não excluídas** |
| Quase-duplicatas confirmadas | 1 par (`mountain`) | Registrada, **não excluída** |
| Arquivos recuperados | 0 | Nenhum arquivo precisou ser recuperado |
| Exclusões | 0 | Nenhuma |

O detalhamento linha a linha está em `dados/registro_ocorrencias.csv`.

Como pede a documentação, nenhuma duplicata foi removida automaticamente: `dados/raw/` mantém as **7.000 imagens originais, 700 por classe**. A decisão sobre os 7 pares redundantes deve ser tomada e justificada antes do particionamento. Por exemplo, pode-se manter apenas um arquivo de cada par ou garantir que as duas cópias fiquem no mesmo subconjunto (treino, validação ou teste), para evitar vazamento de dados entre os conjuntos. Caso um arquivo de cada par seja removido, a classe `airport` ficaria com 694 imagens, a classe `mountain` com 699 e o total seria de 6.993.

## 6. Critérios de conclusão

- [x] O dataset NWPU-RESISC45 foi baixado e extraído.
- [x] A estrutura original foi conferida (45 pastas × 700 imagens).
- [x] As dez classes obrigatórias foram identificadas.
- [x] As 35 classes não utilizadas ficaram fora da cópia de trabalho (o original foi preservado).
- [x] `dados/raw/` contém exclusivamente as dez categorias selecionadas.
- [x] A quantidade de imagens por classe foi contabilizada.
- [x] Todas as imagens foram verificadas quanto à leitura, dimensões e canais.
- [x] Os arquivos problemáticos foram registrados (nenhum foi encontrado).
- [x] A verificação de duplicatas foi realizada (exatas e quase-duplicatas).
- [x] O relatório de preparação foi gerado.
- [x] O procedimento está documentado e pode ser reproduzido (`scripts/preparar_dados.py`).
