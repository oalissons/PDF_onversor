# Kit de Conversão e Processamento de PDFs

Conjunto de ferramentas para o fluxo de impressão/documentação de **ordens de serviço**:

- **JPG/JPEG → PDF** — A4 paisagem, recorte automático do fundo, alta qualidade
- **PDF → HTML editável** — texto clicável/editável, mantendo fonte, cor e posição
- **Mesclagem de PDFs** — agrupa arquivos por nome e junta em um único PDF, com backup de segurança

Desenvolvido e testado no Windows com **Python 3** + **PowerShell 5.1**.

---

## Ferramentas

| Ferramenta | O que faz |
|---|---|
| `converter_jpg_para_pdf` | Varre um diretório, converte todos os `*.jpg`/`*.jpeg` para PDF A4 paisagem (margem branca, fundo removido). Para cada pasta criada uma pasta-espelho com `" PDF"` no nome. Arquivos da raiz vão para `"0 - Raiz PDF"`. |
| `converter_pdf_para_html` | Converte PDFs em HTML autocontido com texto **editável** (`contenteditable`), preservando fontes, tamanhos, cores, negrito, linhas traçadas e curvas (SVG). Escala tudo para A4 retrato. |
| `mesclar_pdfs` | Agrupa PDFs por padrão de nome (ex.: `pedido - 1.pdf`, `pedido - 2.pdf`), junta em `pedido.pdf`, verifica o resultado e faz backup dos originais em `_backup/` antes de apagar. |
| `instalar_dependencias` | Instala Python 3 (via `winget` ou `python.org`), Pillow e PyMuPDF automaticamente. |
| `teste_conversao` | Teste rápido: converte 1 JPG em PDF A4 paisagem salvo no Desktop. |

## Requisitos

- Windows 10/11
- PowerShell 5.1 (embutido no Windows)
- Python 3.x
- Pacotes pip: **Pillow** e **PyMuPDF**

## Instalação

**Opção A — automática (recomendado):**

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar_dependencias.ps1
```

**Opção B — manual:**

```powershell
pip install -r requirements.txt
```

> Os scripts `.ps1` já detectam dependências faltando e chamam o instalador automaticamente.

## Uso

### 1. JPG → PDF

```powershell
powershell -ExecutionPolicy Bypass -File .\converter_jpg_para_pdf.ps1 -rootDir "C:\caminho\com\jpegs"
```

```bat
python converter_jpg_para_pdf.py "C:\caminho\com\jpegs"
```

Cria, para cada subpasta, uma pasta-espelho `"<nome> PDF"`. Arquivos já convertidos são ignorados (re-executar só converte o que falta).

### 2. PDF → HTML

```powershell
powershell -ExecutionPolicy Bypass -File .\converter_pdf_para_html.ps1 -diretorio "C:\caminho\com\pdfs"
```

```bat
python converter_pdf_para_html.py "C:\caminho\com\pdfs" --force
```

> `--force` (ou `-f`) re-converte arquivos que já possuem HTML.

Faz um `.html` para cada PDF (mesmo nome, pasta `<nome> HTML`). Abra no navegador; textos ficam editáveis e a página pode ser impressa em A4.

### 3. Mesclar PDFs

```powershell
powershell -ExecutionPolicy Bypass -File .\mesclar_pdfs.ps1 -diretorio "C:\caminho\com\pdfs"
```

- `arquivo - 1.pdf` + `arquivo - 2.pdf` → `arquivo.pdf`
- Antes de apagar os originais, salva backup em `_backup/`
- Só apaga os originais após validar o PDF mesclado (restaura sozinho se algo falhar)

## Diretório padrão

Quando nenhum caminho é passado, os scripts usam por padrão a pasta **`ORDENS`** no Desktop do usuário:

```
%USERPROFILE%\Desktop\ORDENS
```

Para usar outra pasta, basta passar o argumento `-rootDir` / `-diretorio` (veja os exemplos acima) ou editar a variável `RAIZ` no começo de cada script `.py`.

## Estrutura do projeto

```
.
├── converter_jpg_para_pdf.py      # Núcleo em Python do conversor JPG -> PDF
├── converter_jpg_para_pdf.ps1     # Wrapper PowerShell (auto-instala dependências)
├── converter_pdf_para_html.py     # Núcleo em Python do conversor PDF -> HTML
├── converter_pdf_para_html.ps1    # Wrapper PowerShell
├── converter_pdf_para_html.bat    # Atalho .bat para o conversor PDF -> HTML
├── mesclar_pdfs.ps1               # Mesclagem em lote com backup de segurança
├── instalar_dependencias.ps1      # Instala Python + Pillow + PyMuPDF
├── teste_conversao.py             # Teste rápido 1 JPG -> PDF
├── requirements.txt               # Dependências pip
├── LICENSE                        # GPL-3.0
└── README.md
```

## Licença

Distribuído sob a [GNU GPL v3.0](LICENSE) — uso livre e modificação, desde que
derivações também sejam licenciadas sob GPL.