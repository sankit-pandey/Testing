import fitz, os

pdf = r"C:\Projects\AI Localization\UX\UX.pdf"
out = r"C:\Projects\AI Localization\UX\_pages"
os.makedirs(out, exist_ok=True)

doc = fitz.open(pdf)
page = doc[0]
W, H = page.rect.width, page.rect.height
zoom = 2.0
tile_h = 1250  # points per tile

i = 0
y = 0.0
while y < H:
    clip = fitz.Rect(0, y, W, min(y + tile_h, H))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    path = os.path.join(out, f"tile_{i:02d}.png")
    pix.save(path)
    print(f"saved tile_{i:02d} y[{int(clip.y0)}-{int(clip.y1)}] {pix.width}x{pix.height}")
    i += 1
    y += tile_h
print("DONE", i, "tiles")
