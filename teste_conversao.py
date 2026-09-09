"""Teste: 1 JPEG -> A4 paisagem, margem 1cm, maxima qualidade."""

import sys
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image
    import fitz
except ImportError as e:
    print(f"ERRO: {e}. Execute: pip install Pillow PyMuPDF")
    input("Pressione Enter para sair...")
    sys.exit(1)

if len(sys.argv) > 1:
    ARQUIVO = sys.argv[1]
else:
    ARQUIVO = "exemplo.jpg"

A4L_PT = (841.89, 595.28)
MARGEM = 8.5


def auto_crop(img, threshold=40, step=3):
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


origem = Path(ARQUIVO)
if not origem.is_file():
    print(f"ERRO: Arquivo nao encontrado: {origem}")
    print(f"Uso: python {sys.argv[0]} [caminho_do_arquivo]")
    input("Pressione Enter para sair...")
    sys.exit(1)

destino = Path.home() / "Desktop" / f"{origem.stem}_test.pdf"

if destino.exists():
    print(f"Arquivo ja existe: {destino.name}")
    input("Pressione Enter para sair...")
    sys.exit(0)

print(f"Convertendo: {origem.name}")
print(f"Salvando em: {destino.name}")

try:
    img = Image.open(origem).convert("RGB")
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
    doc.save(str(destino), garbage=4, deflate=True)
    doc.close()
    buf.close()

    print(f"OK! Salvo em: {destino.name}")
except Exception as e:
    print(f"ERRO: {e}")
    input("Pressione Enter para sair...")
    sys.exit(1)
