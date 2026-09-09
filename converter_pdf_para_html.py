import sys
from pathlib import Path
from xml.sax.saxutils import escape

try:
    import fitz
except ImportError as e:
    print(f"ERRO: {e}. Execute: pip install Pillow PyMuPDF")
    try:
        input("Pressione Enter para sair...")
    except EOFError:
        pass
    sys.exit(1)
except Exception as e:
    print(f"ERRO: {e}")
    try:
        input("Pressione Enter para sair...")
    except EOFError:
        pass
    sys.exit(1)

RAIZ = str(Path.home() / "Desktop" / "ORDENS")
A4L = 595.28
A4A = 841.89
USAR_A4 = True


def pause():
    try:
        input("Pressione Enter para sair...")
    except EOFError:
        pass


def nome_fonte_css(font):
    f = font.replace("-", " ").replace("_", " ").replace(",Bold", "").replace("Bold", "").replace("bold", "").strip()
    mapa = {
        "CourierNew": "Courier New",
        "Courier": "Courier New",
        "ArialMT": "Arial",
        "Arial BoldMT": "Arial",
        "TimesNewRomanPS": "Times New Roman",
        "TimesNewRoman": "Times New Roman",
    }
    for k, v in mapa.items():
        if f.lower().startswith(k.lower().replace(" ", "")):
            return v
    return f if f else "monospace"


def rgba(c):
    if not c or not isinstance(c, (list, tuple)) or len(c) < 3:
        return None
    r = int(min(c[0], 1) * 255)
    g = int(min(c[1], 1) * 255)
    b = int(min(c[2], 1) * 255)
    a = c[3] if len(c) > 3 else 1.0
    if a < 1:
        return f"rgba({r},{g},{b},{round(a,3)})"
    return f"rgb({r},{g},{b})"


def cor_css(c):
    return rgba(c) or "rgb(0,0,0)"


def pdf_para_html(caminho_pdf, caminho_html):
    doc = fitz.open(caminho_pdf)
    paginas = []

    for num_pag in range(len(doc)):
        try:
            pag = doc[num_pag]
            pw, ph = pag.rect.width, pag.rect.height

            if USAR_A4:
                escala = min(A4L / pw, A4A / ph)
                sx = sy = escala
                cw, ch = A4L, A4A
                offx = (A4L - pw * escala) / 2
                offy = (A4A - ph * escala) / 2
            else:
                sx = sy = 1.0
                cw, ch = pw, ph
                offx = offy = 0

            textos = []
            rects_pdf = []  # retangulos em coordenadas originais do PDF para detectar centralizacao

            # coleta retangulos dos desenhos (para detectar textos centralizados)
            try:
                for d in pag.get_drawings():
                    for item in d.get("items", []):
                        if item[0] == "re":
                            r = item[1]
                            rects_pdf.append({
                                "x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1,
                                "w": r.width, "h": r.height,
                            })
            except Exception:
                pass

            dict_pag = pag.get_text("dict")
            if dict_pag and "blocks" in dict_pag:
                for bloco in dict_pag["blocks"]:
                    if bloco.get("type") != 0:
                        continue
                    for linha in bloco.get("lines", []):
                        for span in linha.get("spans", []):
                            t_raw = span.get("text", "")
                            if not t_raw or not t_raw.strip():
                                continue
                            font = span.get("font", "")
                            size = span.get("size", 0)
                            if "arial" in font.lower() and size >= 15 and ("<" in t_raw or ">" in t_raw or "n" in t_raw.lower()):
                                continue
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            txt_centro = (bbox[0] + bbox[2]) / 2
                            centralizado = False
                            larg_rect = 0
                            txt_larg = bbox[2] - bbox[0]
                            melhor_r = None
                            melhor_area = float("inf")
                            for r in rects_pdf:
                                if not (bbox[2] > r["x0"] and bbox[0] < r["x1"]):
                                    continue
                                if not (bbox[3] > r["y0"] and bbox[1] < r["y1"]):
                                    continue
                                area = r["w"] * r["h"]
                                if area < melhor_area:
                                    melhor_area = area
                                    melhor_r = r
                            if melhor_r is not None:
                                if txt_larg / max(melhor_r["w"], 1) >= 0.15:
                                    rcx = (melhor_r["x0"] + melhor_r["x1"]) / 2
                                    if abs(txt_centro - rcx) / max(melhor_r["w"], 1) < 0.06:
                                        if bbox[0] >= melhor_r["x0"] - 5 and bbox[2] <= melhor_r["x1"] + 5:
                                            centralizado = True
                                            larg_rect = melhor_r["w"]
                            item_texto = {
                                "x": round(bbox[0] * sx + offx, 2),
                                "y": round(bbox[1] * sy + offy, 2),
                                "texto": escape(t_raw),
                                "fonte": nome_fonte_css(font),
                                "tam": round(size * sy, 1),
                                "cor": rgba(span.get("color")) or "#000000",
                                "negrito": "Bold" in font or "bold" in font,
                            }
                            if centralizado:
                                item_texto["centralizado"] = True
                                item_texto["larg_rect"] = round(larg_rect * sx, 2)
                            textos.append(item_texto)

            # Desenhos -> divs com borda (editaveis) + SVG para curvas
            divs_linhas = []
            svg_caminhos = []
            try:
                desenhos = pag.get_drawings()
            except Exception:
                desenhos = []

            for d in desenhos:
                try:
                    cor = d.get("color", (0, 0, 0))
                    cor_fill = d.get("fill")
                    largura = max(d.get("width", 1) * escala, 0.5)
                    op_s = d.get("stroke_opacity", 1)
                    tipo = d.get("type", "s")
                    fechar = d.get("closePath", False)

                    tem_curva = any(item[0] == "c" for item in d.get("items", []))

                    if tem_curva:
                        # curvas -> SVG
                        cmds = []
                        primeiro = True
                        fechado = False
                        for item in d.get("items", []):
                            try:
                                if item[0] == "l":
                                    p1, p2 = item[1], item[2]
                                    x1, y1 = round(p1.x * sx + offx, 2), round(p1.y * sy + offy, 2)
                                    x2, y2 = round(p2.x * sx + offx, 2), round(p2.y * sy + offy, 2)
                                    if primeiro:
                                        cmds.append(f"M{x1} {y1}")
                                        primeiro = False
                                    cmds.append(f"L{x2} {y2}")
                                elif item[0] == "c":
                                    p1, p2, p3, p4 = item[1:5]
                                    if primeiro:
                                        cmds.append(f"M{round(p1.x*sx+offx,2)} {round(p1.y*sy+offy,2)}")
                                        primeiro = False
                                    cmds.append(
                                        f"C{round(p2.x*sx+offx,2)} {round(p2.y*sy+offy,2)} "
                                        f"{round(p3.x*sx+offx,2)} {round(p3.y*sy+offy,2)} "
                                        f"{round(p4.x*sx+offx,2)} {round(p4.y*sy+offy,2)}"
                                    )
                                elif item[0] == "re":
                                    r = item[1]
                                    x = round(r.x0 * sx + offx, 2)
                                    y = round(r.y0 * sy + offy, 2)
                                    w = round(r.width * sx, 2)
                                    h = round(r.height * sy, 2)
                                    cmds.append(f"M{x} {y}h{w}v{h}h{-w}Z")
                                    fechado = True
                                    primeiro = False
                                elif item[0] == "qu":
                                    q = item[1]
                                    cmds.append(
                                        f"M{round(q.ul.x*sx+offx,2)} {round(q.ul.y*sy+offy,2)}"
                                        f"L{round(q.ur.x*sx+offx,2)} {round(q.ur.y*sy+offy,2)}"
                                        f"L{round(q.lr.x*sx+offx,2)} {round(q.lr.y*sy+offy,2)}"
                                        f"L{round(q.ll.x*sx+offx,2)} {round(q.ll.y*sy+offy,2)}Z"
                                    )
                                    fechado = True
                                    primeiro = False
                            except Exception:
                                continue
                        if fechar and not fechado:
                            cmds.append("Z")
                        if cmds:
                            d_str = " ".join(cmd for cmd in cmds)
                            atts = f'fill="none" stroke="{cor_css(cor)}" stroke-width="{largura:.2f}"'
                            svg_caminhos.append(f'<path d="{escape(d_str)}" {atts}/>')
                    else:
                        # sem curvas -> divs HTML
                        for item in d.get("items", []):
                            try:
                                c_str = cor_css(cor)
                                if item[0] == "re":
                                    r = item[1]
                                    x = round(r.x0 * sx + offx, 2)
                                    y = round(r.y0 * sy + offy, 2)
                                    w = round(r.width * sx, 2)
                                    h = round(r.height * sy, 2)
                                    if tipo in ("f", "fs") and cor_fill:
                                        fc = rgba(cor_fill)
                                        fill = f" background:{fc};" if fc else ""
                                    else:
                                        fill = ""
                                    divs_linhas.append(
                                        f'<div class="ln" style="left:{x}pt;top:{y}pt;width:{w}pt;height:{h}pt;'
                                        f'border:{largura:.1f}pt solid {c_str};{fill}"></div>'
                                    )
                                elif item[0] == "l":
                                    p1, p2 = item[1], item[2]
                                    x1, y1 = round(p1.x * sx + offx, 2), round(p1.y * sy + offy, 2)
                                    x2, y2 = round(p2.x * sx + offx, 2), round(p2.y * sy + offy, 2)
                                    if abs(x2 - x1) >= abs(y2 - y1):
                                        xm, xM = min(x1, x2), max(x1, x2)
                                        ym = y1
                                        w = xM - xm
                                        if w > 0:
                                            divs_linhas.append(
                                                f'<div class="ln" style="left:{xm}pt;top:{ym}pt;width:{w}pt;'
                                                f'height:{largura:.1f}pt;background:{c_str};"></div>'
                                            )
                                    else:
                                        ym, yM = min(y1, y2), max(y1, y2)
                                        xm = x1
                                        h = yM - ym
                                        if h > 0:
                                            divs_linhas.append(
                                                f'<div class="ln" style="left:{xm}pt;top:{ym}pt;'
                                                f'width:{largura:.1f}pt;height:{h}pt;background:{c_str};"></div>'
                                            )
                                elif item[0] == "qu":
                                    q = item[1]
                                    pts = [
                                        (q.ul.x * sx + offx, q.ul.y * sy + offy),
                                        (q.ur.x * sx + offx, q.ur.y * sy + offy),
                                        (q.lr.x * sx + offx, q.lr.y * sy + offy),
                                        (q.ll.x * sx + offx, q.ll.y * sy + offy),
                                    ]
                                    xs = [p[0] for p in pts]
                                    ys = [p[1] for p in pts]
                                    x = round(min(xs), 2)
                                    y = round(min(ys), 2)
                                    w = round(max(xs) - min(xs), 2)
                                    h = round(max(ys) - min(ys), 2)
                                    divs_linhas.append(
                                        f'<div class="ln" style="left:{x}pt;top:{y}pt;width:{w}pt;height:{h}pt;'
                                        f'border:{largura:.1f}pt solid {c_str};"></div>'
                                    )
                            except Exception:
                                continue
                except Exception:
                    continue

            conteudo_svg = "".join(svg_caminhos)
            html_svg = f'<svg id="curvas" viewBox="0 0 {cw} {ch}" xmlns="http://www.w3.org/2000/svg">{conteudo_svg}</svg>' if svg_caminhos else ""

            paginas.append({"textos": textos, "divs": divs_linhas, "svg": html_svg, "w": cw, "h": ch})
        except Exception as e:
            print(f"    ERRO na pagina {num_pag+1}: {e}", file=sys.stderr)
            continue

    doc.close()

    partes = [
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "<title>Documento</title>",
        "<style>",
        "  @page { size: A4 portrait; margin: 0; }",
        "  * { margin: 0; padding: 0; box-sizing: border-box; }",
        "  html, body { height: 100%; }",
        "  body { background: #e0e0e0; padding: 20pt 0; }",
        "  .pagina {",
        f"    width: {A4L}pt; min-height: {A4A}pt;",
        "    position: relative; background: white;",
        "    margin: 0 auto;",
        "    box-shadow: 0 2pt 10pt rgba(0,0,0,0.2);",
        "    overflow: hidden;",
        "    border: 0.3cm solid #ccc;",
        "  }",
        "  .txt { position: absolute; white-space: pre; cursor: text; }",
        "  .txt:focus { outline: 2pt dashed #f80; background: rgba(255,200,0,0.2); }",
        "  .ln { position: absolute; pointer-events: none; }",
        "  #curvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }",
        "  @media print {",
        "    html, body { height: auto; }",
        "    body { background: none; padding: 0; }",
        f"    .pagina {{ box-shadow: none; margin: 0 auto; border: none; height: {A4A}pt; page-break-after: always; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}",
        "  }",
        "</style>",
        "</head>",
        "<body>",
    ]

    for pag in paginas:
        partes.append('<div class="pagina">')
        for d in pag["divs"]:
            partes.append(f"  {d}")
        if pag["svg"]:
            partes.append(f"  {pag['svg']}")
        for t in pag["textos"]:
            estilo = (
                f'left:{t["x"]}pt; top:{t["y"]}pt; '
                f'font-size:{t["tam"]}pt; color:{t["cor"]}; '
                f'font-family:"{t["fonte"]}",monospace,sans-serif;'
            )
            if t["negrito"]:
                estilo += " font-weight:bold;"
            if t.get("centralizado"):
                estilo += f" width:{t['larg_rect']}pt; text-align:center;"
            partes.append(f'  <div class="txt" contenteditable="true" style="{estilo}">{t["texto"]}</div>')
        partes.append("</div>")

    partes.append("</body>")
    partes.append("</html>")

    with open(caminho_html, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))

    return len(paginas)


def processar_diretorio(src_dir, dest_dir, forcar=False):
    src = Path(src_dir)
    dest = Path(dest_dir)
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)

    convertidos = 0
    for item in sorted(src.iterdir()):
        if not item.is_file() or item.suffix.lower() != ".pdf":
            continue
        html_dest = dest / f"{item.stem}.html"
        if html_dest.exists() and not forcar:
            print(f"  [PULANDO] {item.name} — HTML ja existe em {html_dest.name}")
            continue
        elif html_dest.exists() and forcar:
            html_dest.unlink()
        print(f"  Convertendo: {item.name}")
        try:
            pag = pdf_para_html(str(item), str(html_dest))
            print(f"    OK: {html_dest.name} ({pag} paginas)")
            convertidos += 1
        except Exception as e:
            print(f"    ERRO: {e}")
    return convertidos


def main():
    forcar = "--force" in sys.argv or "-f" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--force", "-f")]
    diretorio = args[0] if args else RAIZ
    raiz = Path(diretorio)

    if not raiz.is_dir():
        print(f"ERRO: Diretorio nao encontrado: {diretorio}")
        print(f"Uso: python {sys.argv[0]} [caminho_do_diretorio]")
        pause()
        sys.exit(1)

    pastas = []
    if list(raiz.glob("*.pdf")):
        pastas.append(raiz)
    for d in sorted(raiz.iterdir()):
        if d.is_dir() and list(d.glob("*.pdf")):
            pastas.append(d)

    if not pastas:
        print(f"Nenhum PDF encontrado em: {raiz}")
        pause()
        sys.exit(0)

    total = 0
    for pasta in pastas:
        dest_pasta = pasta.parent / f"{pasta.name} HTML"
        print(f"\n>>> {pasta} -> {dest_pasta}")
        conv = processar_diretorio(pasta, dest_pasta, forcar)
        total += conv

    print(f"\n=== RESUMO ===")
    print(f"Total convertidos: {total}")
    print("Concluido!")
    pause()


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        pass
    except Exception as e:
        print(f"\n[ERRO NAO ESPERADO] {e}")
        import traceback
        traceback.print_exc()
        pause()
        sys.exit(1)
