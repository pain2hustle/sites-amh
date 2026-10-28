"""Glossy 3D bubble letters rendered from the font outline as a height field (no mesh tearing).
Usage: python tools/bubble-letters.py "<text>" <out.webp> <width_px> [font.ttf]"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

text, out, width = sys.argv[1], sys.argv[2], int(sys.argv[3])
font = sys.argv[4] if len(sys.argv) > 4 else str(__import__('pathlib').Path(__file__).resolve().parent/'fonts/Fredoka-Bold.ttf')
SS = 1                                   # supersample for crisp edges
size = 260 * SS
f = ImageFont.truetype(font, size)
pad = 60 * SS
l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f)
W, H = r - l + pad * 2, b - t + pad * 2
mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=f, fill=255)
m = np.asarray(mask, dtype=np.float32) / 255.0
inside = m > 0.5

# pillow height: rounded profile from distance to the edge
d = ndimage.distance_transform_edt(inside).astype(np.float32)
R = 30.0 * SS                            # how far in the dome rises
h = np.sqrt(np.clip(1 - (1 - np.clip(d / R, 0, 1)) ** 2, 0, 1)) * R
h = ndimage.gaussian_filter(h, 1.2 * SS)
gy, gx = np.gradient(h)
n = np.dstack([-gx, -gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)

# base colour: candy pink top -> hot pink -> violet bottom
ys = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
c_top, c_mid, c_bot = np.array([1.0, 0.55, 0.86]), np.array([1.0, 0.16, 0.62]), np.array([0.58, 0.12, 0.92])
k = np.clip((ys - 0.18) / 0.62, 0, 1)[..., None]
base = np.where(k < 0.5, c_top + (c_mid - c_top) * (k / 0.5), c_mid + (c_bot - c_mid) * ((k - 0.5) / 0.5))

def light(v):
    v = np.array(v, dtype=np.float32); return v / np.linalg.norm(v)
L1, L2 = light([-0.45, -0.65, 0.62]), light([0.7, 0.35, 0.6])
diff = np.clip((n * L1).sum(2), 0, 1) * 0.75 + np.clip((n * L2).sum(2), 0, 1) * 0.25
amb = 0.42
V = np.array([0, 0, 1.0])
def spec(Lv, power, amt):
    Hh = (Lv + V); Hh /= np.linalg.norm(Hh)
    return np.clip((n * Hh).sum(2), 0, 1) ** power * amt
sp = spec(L1, 90, 1.25) + spec(L2, 45, 0.4)
rim = (1 - n[..., 2]) ** 2.2                     # sides darken toward deep plum
plum = np.array([0.24, 0.03, 0.32])
col = base * (amb + diff)[..., None]
col = col * (1 - rim[..., None] * 0.75) + plum * rim[..., None] * 0.75
col = col + sp[..., None]
col = np.clip(col, 0, 1)

# thick dark outline all around + soft drop shadow
ring = ndimage.binary_dilation(inside, iterations=9 * SS)
out_rgb = np.zeros((H, W, 3), np.float32); out_a = np.zeros((H, W), np.float32)
sh = ndimage.gaussian_filter(ndimage.shift(ring.astype(np.float32), (7 * SS, 3 * SS)), 6 * SS) * 0.55
out_a = sh
out_rgb[:] = np.array([0.05, 0.0, 0.08])
outline_col = np.array([0.16, 0.02, 0.22])
out_rgb[ring] = outline_col; out_a[ring] = 1
out_rgb[inside] = col[inside]; out_a[inside] = 1
img = Image.fromarray(np.dstack([out_rgb * 255, out_a * 255]).astype(np.uint8), 'RGBA')
bb = img.getbbox(); img = img.crop(bb)
img = img.resize((width, int(img.height * width / img.width)), Image.LANCZOS)
img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=50, threshold=1))
img.save(out, quality=94, method=6)
print(out, img.size)
