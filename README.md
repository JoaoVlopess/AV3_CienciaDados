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
│   ├── resumo_preparacao.json            # totais, versões de software e data da execução
│   └── splits/                           # partições treino/validação/teste (listas de caminhos)
│       ├── particoes.csv  treino.csv  validacao.csv  teste.csv
│       └── resumo_particoes.json
├── notebooks/
│   └── 01_analise_exploratoria.ipynb     # Etapa 2: EDA (executado, com saídas e interpretações)
├── resultados/
│   ├── figuras/eda/                      # figuras da EDA (PNG, 150 dpi)
│   └── tabelas/eda/                      # tabelas da EDA (CSV)
├── scripts/
│   ├── preparar_dados.py          # Etapa 1: preparação inicial, completa e reproduzível
│   └── definir_particoes.py       # partições estratificadas e agrupadas por duplicata
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

---

# Partições treino / validação / teste

O documento da EDA exige que a análise visual use apenas a partição de treino. Por isso, as partições foram definidas antes da EDA, com `scripts/definir_particoes.py`:

```bash
python -I scripts/definir_particoes.py --projeto .   # padrão: --treino 0.70 --validacao 0.15 --teste 0.15 --semente 42
```

- **Estratificada:** 490 / 105 / 105 imagens por classe (4.900 / 1.050 / 1.050 no total).
- **Agrupada por duplicata:** os 6 pares exatos de `airport` e a quase-duplicata de `mountain` ficam sempre inteiros na mesma partição, o que evita vazamento de dados entre as partições.
- **Sem cópia de arquivos:** as partições são listas de caminhos que apontam para `dados/raw/`. A verificação confirmou 0 sobreposições, 0 grupos divididos e 0 arquivos inexistentes.

As proporções e a semente podem ser alteradas por parâmetro. Se forem alteradas, a EDA deve ser executada novamente.

# Etapa 2: Análise Exploratória de Dados

Requisitos adicionais: `numpy`, `pandas`, `matplotlib`, `jupyter` (ou `nbclient` + `ipykernel`).
O notebook `notebooks/01_analise_exploratoria.ipynb` contém o código, as figuras e as interpretações. Para reproduzir, basta executá-lo do início ao fim (cerca de 2 minutos). Ele regenera tudo em `resultados/`.

**Regra de acesso aos dados:** o inventário, as contagens, os formatos e as duplicatas consideram as 7.000 imagens. Já os painéis, histogramas, descritores e a comparação de resolução usam **somente o treino**. Das partições de validação e teste, verificam-se apenas a contagem, a integridade e a sobreposição.

| Seção | Figura principal | Resultado em uma linha |
|---|---|---|
| Distribuição das classes | `distribuicao_classes.png` | 700 imagens por classe (10% cada), equilíbrio perfeito; a preparação não alterou nada |
| Características técnicas | `tamanho_arquivos.png` | 100% JPEG, 256×256, RGB com 3 canais; `dense_residential` tem os arquivos mais complexos e `desert` os mais simples |
| Exemplos das classes | `exemplos_classes.png` | 5 imagens de treino por classe (semente 42) e descrição dos padrões de cada classe |
| Ambiguidades | `ambiguidades_visuais.png`, `distancia_classes.png` | 4 pares sugeridos, com semelhanças restritas a subconjuntos de imagens; pelos descritores de cor e textura, o par mais próximo é airport × storage_tank |
| Resoluções | `comparacao_resolucoes.png`, `perda_detalhe_resolucao.png` | em 128×128 a composição se mantém, mas barcos, aeronaves, telhados e copas se perdem |
| Complementares | `intensidade_pixels.png`, `histogramas_rgb.png`, `variacao_intraclasse.png`, `casos_extremos.png` | desert é claro e quente, forest é escuro e homogêneo; há grande variação de iluminação dentro das classes |

Observação de qualidade: algumas imagens trazem marcas de atribuição do provedor de imagens (por exemplo, o texto "GEBCO" no canto de `desert_204`). Essas marcas foram mantidas, porque fazem parte do dataset original.

## Critérios de conclusão da EDA

- [x] A distribuição das dez classes foi analisada.
- [x] O gráfico de frequência das classes foi gerado.
- [x] As propriedades técnicas dos arquivos foram consolidadas.
- [x] O inventário e as inconsistências da preparação inicial foram considerados.
- [x] Os exemplos visuais das dez classes foram apresentados.
- [x] As características principais de cada categoria foram descritas.
- [x] As possíveis ambiguidades visuais foram investigadas.
- [x] Os painéis comparativos entre categorias foram produzidos.
- [x] A mesma imagem foi apresentada em 128 × 128 e 256 × 256 pixels.
- [x] As diferenças visuais entre resoluções foram discutidas.
- [x] As visualizações de conteúdo usaram exclusivamente imagens de treino.
- [x] As figuras e os resultados foram salvos.
- [x] O notebook de análise está organizado e é reproduzível.
