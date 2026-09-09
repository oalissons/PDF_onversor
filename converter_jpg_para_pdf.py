"""Converte todos os JPEGs de uma pasta da rede para PDF.

Para cada subpasta, cria uma pasta-espelho com sufixo " PDF", remove fundo
uniforme e gera A4 paisagem com margem branca de 0,3cm para impressao.

Arquivos no nivel raiz vao para "0 - Raiz PDF".

Requer: pip install Pillow PyMuPDF
"""

import os
import sys
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
    import fitz
except ImportError as e:
    print(f"ERRO: {e}. Execute: pip install Pillow PyMuPDF")
    input("Pressione Enter para sair...")
    sys.exit(1)

RAIZ = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Desktop" / "ORDENS")
EXTENSOES = {".jpg", ".jpeg"}
A4L_PT = (841.89, 595.28)
MARGEM = 8.5  # 0,3cm em pontos (margem de impressao)


def auto_crop(img, threshold=40, step=3):
    """Remove borda de fundo uniforme ao redor do conteudo."""
    w, h = img.size
    bg = tuple(
        (img.getpixel((0,0))[i] + img.getpixel((w-1,0))[i] +
         img.getpixel((0,h-1))[i] + img.getpixel((w-1,h-1))[i]) // 4
        for i in range(3)
    )
    def is_bg(px):
        return max(abs(px[i] - bg[i]) for i in range(3)) <= threshold

    left = next((x for x in range(w) if sum(1 for y in range(0, h, step) if not is_bg(img.getpixel((x, y)))) > h // step * 0.01), 0)
    right = next((x for x in range(w-1, -1, -1) if sum(1 for y in range(0, h, step) if not is_bg(img.getpixel((x, y)))) > h // step * 0.01), w-1)
    top = next((y for y in range(h) if sum(1 for x in range(0, w, step) if not is_bg(img.getpixel((x, y)))) > w // step * 0.01), 0)
    bottom = next((y for y in range(h-1, -1, -1) if sum(1 for x in range(0, w, step) if not is_bg(img.getpixel((x, y)))) > w // step * 0.01), h-1)
    return (left, top, right + 1, bottom + 1)


def converter_jpg_para_pdf(caminho_jpg: Path, caminho_pdf: Path) -> bool:
    """Converte JPEG -> A4 paisagem com margem branca e maxima qualidade."""
    try:
        img = Image.open(caminho_jpg).convert("RGB")
        bbox = auto_crop(img)
        img_content = img.crop(bbox)

        buf = BytesIO()
        img_content.save(buf, "PNG")
        buf.seek(0)

        doc = fitz.open()
        page = doc.new_page(width=A4L_PT[0], height=A4L_PT[1])
        page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
        img_rect = fitz.Rect(MARGEM, MARGEM, A4L_PT[0] - MARGEM, A4L_PT[1] - MARGEM)
        page.insert_image(img_rect, stream=buf.read(), keep_proportion=True)
        doc.save(str(caminho_pdf), garbage=4, deflate=True)
        doc.close()
        buf.close()
        return True
    except Exception as e:
        print(f"    FALHA: {caminho_jpg.name} - {e}")
        return False


def processar_diretorio(src_dir: Path, dest_dir: Path) -> tuple[int, int]:
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)

    convertidos = 0
    ignorados = 0

    for item in sorted(src_dir.iterdir()):
        if not item.is_file():
            continue
        ext = item.suffix.lower()
        if ext not in EXTENSOES:
            continue

        pdf_dest = dest_dir / f"{item.stem}.pdf"
        if pdf_dest.exists():
            ignorados += 1
            continue

        if converter_jpg_para_pdf(item, pdf_dest):
            convertidos += 1
            print(f"    OK: {item.name}")
        else:
            ignorados += 1

    return convertidos, ignorados


def main():
    print("=== Conversor JPEG -> PDF ===")
    print(f"Raiz: {RAIZ}")
    print()

    raiz = Path(RAIZ)
    if not raiz.is_dir():
        print(f"ERRO: Diretorio raiz nao encontrado: {RAIZ}")
        print(f"Uso: python {sys.argv[0]} [caminho_do_diretorio]")
        input("Pressione Enter para sair...")
        sys.exit(1)

    dirs = [raiz] + sorted([d for d in raiz.iterdir() if d.is_dir()])
    total_convertidos = 0
    total_ignorados = 0
    total_dirs = len(dirs)

    for i, src_dir in enumerate(dirs, 1):
        if src_dir == raiz:
            dest_dir = raiz / "0 - Raiz PDF"
        else:
            dest_dir = src_dir.parent / f"{src_dir.name} PDF"

        tem_jpeg = any(
            p.is_file() and p.suffix.lower() in EXTENSOES
            for p in src_dir.iterdir()
        )
        if not tem_jpeg:
            print(f"[{i}/{total_dirs}] NENHUM JPEG em: {src_dir}")
            continue

        print(f"[{i}/{total_dirs}] {src_dir} -> {dest_dir}")
        conv, ign = processar_diretorio(src_dir, dest_dir)
        total_convertidos += conv
        total_ignorados += ign

    print(f"\n=== RESUMO ===")
    print(f"Pastas processadas: {total_dirs}")
    print(f"Convertidos: {total_convertidos}")
    print(f"Ignorados: {total_ignorados}")
    print("Concluido!")


if __name__ == "__main__":
    main()
