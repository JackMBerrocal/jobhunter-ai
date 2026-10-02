#!/usr/bin/env python3
"""
Generador Maestro y Diseñador Oficial de Logos e Íconos para Scrapy AI
- Extrae la mascota 3D pura (Comp 0: 67,280 px) sin ningún residuo.
- Diseña el Ícono de Aplicación Maestro Oficial (Squircle moderno de 512x512 con borde de cristal cian y fondo premium).
- Diseña el Ícono Transparente Oficial.
- Diseña el Banner/Logo horizontal oficial con tipografía moderna.
- Genera la suite completa de resoluciones (512, 256, 128, 96, 64, 48, 32, 24, 16, .ico).
- Despliega en ~/.local/share/icons/hicolor/ y en web_ui/static/.
"""

import os
import math
from collections import deque
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import numpy as np

STATIC_DIR = "/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/web_ui/static"
TRANSPARENT_SRC = os.path.join(STATIC_DIR, "scrapy_transparent.png")

def extract_pure_scrapy():
    """Aísla a Scrapy usando análisis de componentes conectados para eliminar cualquier artefacto."""
    src = Image.open(TRANSPARENT_SRC).convert("RGBA")
    arr = np.array(src)
    
    # Máscara de alpha significativa
    alpha_mask = arr[:, :, 3] > 15
    h, w = alpha_mask.shape
    visited = np.zeros_like(alpha_mask, dtype=bool)
    
    # Encontrar componentes
    components = []
    for y in range(h):
        for x in range(w):
            if alpha_mask[y, x] and not visited[y, x]:
                comp = []
                q = deque([(y, x)])
                visited[y, x] = True
                while q:
                    cy, cx = q.popleft()
                    comp.append((cy, cx))
                    for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and alpha_mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            q.append((ny, nx))
                components.append(comp)
    
    # Ordenar por tamaño de píxeles: el mayor es Scrapy (67,000+ px)
    components.sort(key=len, reverse=True)
    scrapy_pixels = components[0]
    
    pure_arr = np.zeros_like(arr)
    ys = [p[0] for p in scrapy_pixels]
    xs = [p[1] for p in scrapy_pixels]
    
    for y, x in scrapy_pixels:
        pure_arr[y, x] = arr[y, x]
        
    min_y, max_y = min(ys), max(ys)
    min_x, max_x = min(xs), max(xs)
    
    # Recorte exacto
    cropped = pure_arr[min_y:max_y+1, min_x:max_x+1]
    scrapy_img = Image.fromarray(cropped, "RGBA")
    
    out_path = os.path.join(STATIC_DIR, "scrapy_mascot_isolated.png")
    scrapy_img.save(out_path, "PNG")
    print(f"✨ Mascota 100% pura y limpia aislada: {scrapy_img.size} ({len(scrapy_pixels)} px)")
    return scrapy_img

def create_master_badge_icon(scrapy_img, size=512):
    """Crea el Ícono Maestro Oficial con squircle estético de alta gama."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    # Dimensiones del Squircle
    margin = int(size * 0.05) # 25px
    radius = int(size * 0.22) # ~112px
    inner_box = [(margin, margin), (size - margin, size - margin)]
    
    # 1. Máscara Squircle
    mask = Image.new("L", (size, size), 0)
    d_mask = ImageDraw.Draw(mask)
    d_mask.rounded_rectangle(inner_box, radius=radius, fill=255)
    
    # 2. Fondo Gradiente Obsidian Tech + Nebula Glow
    cx, cy = size / 2.0, size / 2.0
    bg_arr = np.zeros((size, size, 4), dtype=np.uint8)
    
    y_coords, x_coords = np.ogrid[:size, :size]
    dists = np.sqrt((x_coords - cx)**2 + (y_coords - (cy - 10))**2) / (size * 0.65)
    dists = np.clip(dists, 0.0, 1.0)
    
    # Color central: Azul cian profundo (#0b2246), Color exterior: Dark Obsidian (#030712)
    c_center = np.array([11, 34, 70, 255])
    c_edge = np.array([3, 7, 18, 255])
    
    for c in range(3):
        bg_arr[:, :, c] = (c_center[c] * (1.0 - dists) + c_edge[c] * dists).astype(np.uint8)
    bg_arr[:, :, 3] = 255
    bg_img = Image.fromarray(bg_arr, "RGBA")
    
    # Nebula glow cian suave centrado en la cabeza de Scrapy
    nebula = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d_neb = ImageDraw.Draw(nebula)
    d_neb.ellipse(
        [(cx - 140, cy - 140), (cx + 140, cy + 140)],
        fill=(0, 220, 255, 60)
    )
    nebula = nebula.filter(ImageFilter.GaussianBlur(radius=55))
    bg_img = Image.alpha_composite(bg_img, nebula)
    
    # Aplicar máscara al fondo
    bg_masked = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_masked.paste(bg_img, (0, 0), mask=mask)
    
    # 3. Borde de Cristal Neón Cian / Sapphire
    border_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d_border = ImageDraw.Draw(border_layer)
    border_w = max(2, int(size * 0.016)) # 8px
    d_border.rounded_rectangle(inner_box, radius=radius, outline=(0, 240, 255, 230), width=border_w)
    
    # Glow sutil exterior del borde
    border_glow = border_layer.filter(ImageFilter.GaussianBlur(radius=3))
    
    # 4. Escalar y Posicionar a Scrapy
    # Tamaño armónico con suficiente aire en los márgenes
    target_h = int(size * 0.78)
    aspect = scrapy_img.width / scrapy_img.height
    target_w = int(target_h * aspect)
    
    scrapy_scaled = scrapy_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Centrado óptico horizontal y vertical
    pos_x = (size - target_w) // 2
    pos_y = int(size * 0.11)
    
    # Sombra proyectada detrás de Scrapy
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s_mask = scrapy_scaled.split()[3]
    s_black = Image.new("RGBA", scrapy_scaled.size, (0, 0, 0, 180))
    shadow.paste(s_black, (pos_x, pos_y + 12), mask=s_mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    
    # Combinar todas las capas
    composed = Image.alpha_composite(bg_masked, border_glow)
    composed = Image.alpha_composite(composed, border_layer)
    composed = Image.alpha_composite(composed, shadow)
    composed.paste(scrapy_scaled, (pos_x, pos_y), mask=scrapy_scaled.split()[3])
    
    return composed

def create_transparent_icon(scrapy_img, size=512):
    """Crea ícono con fondo 100% transparente para muelles o barras translúcidas."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    target_h = int(size * 0.90)
    aspect = scrapy_img.width / scrapy_img.height
    target_w = int(target_h * aspect)
    
    scaled = scrapy_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    pos_x = (size - target_w) // 2
    pos_y = (size - target_h) // 2
    
    # Aura suave cian exterior
    aura = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    a_mask = scaled.split()[3]
    a_color = Image.new("RGBA", scaled.size, (0, 210, 255, 90))
    aura.paste(a_color, (pos_x, pos_y), mask=a_mask)
    aura = aura.filter(ImageFilter.GaussianBlur(radius=12))
    
    canvas = Image.alpha_composite(canvas, aura)
    canvas.paste(scaled, (pos_x, pos_y), mask=scaled.split()[3])
    return canvas

def create_official_banner_logo(scrapy_img):
    """Crea el logo banner horizontal oficial de Scrapy AI (1200x400) para headers y documentación."""
    w, h = 1200, 400
    banner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    
    # Fondo con gradiente y esquinas redondeadas
    mask = Image.new("L", (w, h), 0)
    d_m = ImageDraw.Draw(mask)
    d_m.rounded_rectangle([(10, 10), (w - 10, h - 10)], radius=36, fill=255)
    
    bg = Image.new("RGBA", (w, h), (4, 9, 20, 255))
    # Ambient glow en la izquierda detrás de la mascota
    d_bg = ImageDraw.Draw(bg)
    d_bg.ellipse([(-100, -100), (500, 500)], fill=(0, 210, 255, 45))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    
    banner_base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    banner_base.paste(bg, (0, 0), mask=mask)
    
    # Borde de cristal
    d_b = ImageDraw.Draw(banner_base)
    d_b.rounded_rectangle([(10, 10), (w - 10, h - 10)], radius=36, outline=(0, 240, 255, 200), width=4)
    
    # Mascota en la izquierda
    char_h = 320
    aspect = scrapy_img.width / scrapy_img.height
    char_w = int(char_h * aspect)
    m_scaled = scrapy_img.resize((char_w, char_h), Image.Resampling.LANCZOS)
    
    banner_base.paste(m_scaled, (70, 40), mask=m_scaled.split()[3])
    
    # Texto tipográfico "SCRAPY AI"
    draw = ImageDraw.Draw(banner_base)
    # Intentar cargar fuente bonita del sistema o usar default
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        
    text_x = 70 + char_w + 50
    # SCRAPY (Blanco brillante)
    draw.text((text_x, 100), "SCRAPY", fill=(255, 255, 255, 255), font=font_title)
    # AI (Cian neón con glow)
    draw.text((text_x + 395, 100), "AI", fill=(0, 240, 255, 255), font=font_title)
    
    # Subtítulo
    draw.text((text_x + 5, 205), "Tu Asistente Virtual Inteligente de Escritorio", fill=(148, 163, 184, 255), font=font_sub)
    
    # Badges modernos
    badges = ["⚡ Control Total X11", "🎙️ Voz Natural Neuronal", "🧠 IA Multi-Modelo"]
    bx = text_x + 5
    for b in badges:
        bw = len(b) * 11 + 24
        draw.rounded_rectangle([(bx, 265), (bx + bw, 302)], radius=12, fill=(15, 23, 42, 220), outline=(56, 189, 248, 140), width=1)
        draw.text((bx + 12, 272), b, fill=(224, 242, 254, 255), font=font_badge)
        bx += bw + 15
        
    out_banner = os.path.join(STATIC_DIR, "scrapy_official_banner.png")
    banner_base.save(out_banner, "PNG")
    print(f"🎨 Banner Oficial guardado en: {out_banner}")

def build_icon_resolutions(master_icon, trans_icon):
    """Crea la suite de resoluciones completas."""
    sizes = [512, 256, 128, 96, 64, 48, 32, 24, 16]
    
    # 1. Guardar Maestro
    master_path = os.path.join(STATIC_DIR, "scrapy_app_icon.png")
    master_icon.save(master_path, "PNG")
    
    trans_path = os.path.join(STATIC_DIR, "scrapy_icon_transparent.png")
    trans_icon.save(trans_path, "PNG")
    
    # 2. Cada tamaño para la web
    for s in sizes:
        # Usamos Lanczos con un toque de nitidez para tamaños pequeños de barra de tareas
        resized = master_icon.resize((s, s), Image.Resampling.LANCZOS)
        if s <= 48:
            enhancer = ImageEnhance.Sharpness(resized)
            resized = enhancer.enhance(1.4)
        p = os.path.join(STATIC_DIR, f"scrapy_icon_{s}.png")
        resized.save(p, "PNG")
        
    # 3. Favicon ICO y PNG
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master_icon.save(os.path.join(STATIC_DIR, "favicon.ico"), format="ICO", sizes=ico_sizes)
    master_icon.resize((32, 32), Image.Resampling.LANCZOS).save(os.path.join(STATIC_DIR, "favicon.png"), "PNG")
    master_icon.resize((192, 192), Image.Resampling.LANCZOS).save(os.path.join(STATIC_DIR, "icon-192.png"), "PNG")
    master_icon.resize((512, 512), Image.Resampling.LANCZOS).save(os.path.join(STATIC_DIR, "icon-512.png"), "PNG")
    master_icon.resize((180, 180), Image.Resampling.LANCZOS).save(os.path.join(STATIC_DIR, "apple-touch-icon.png"), "PNG")
    
    # 4. Instalar en el sistema Linux Mint (hicolor theme)
    hicolor_base = os.path.expanduser("~/.local/share/icons/hicolor")
    for s in [512, 256, 128, 64, 48, 32, 24, 16]:
        target_dir = os.path.join(hicolor_base, f"{s}x{s}", "apps")
        os.makedirs(target_dir, exist_ok=True)
        master_icon.resize((s, s), Image.Resampling.LANCZOS).save(os.path.join(target_dir, "scrapy-ai.png"), "PNG")
        master_icon.resize((s, s), Image.Resampling.LANCZOS).save(os.path.join(target_dir, "scrapy.png"), "PNG")
        
    # También en pixmaps de usuario para compatibilidad máxima con gestores de ventanas X11 / Cinnamon
    pixmaps_dir = os.path.expanduser("~/.local/share/pixmaps")
    os.makedirs(pixmaps_dir, exist_ok=True)
    master_icon.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(pixmaps_dir, "scrapy-ai.png"), "PNG")
    master_icon.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(pixmaps_dir, "scrapy.png"), "PNG")

if __name__ == "__main__":
    print("🚀 Iniciando generación perfecta de íconos oficiales...")
    mascot = extract_pure_scrapy()
    master = create_master_badge_icon(mascot, 512)
    trans = create_transparent_icon(mascot, 512)
    build_icon_resolutions(master, trans)
    create_official_banner_logo(mascot)
    print("✅ ¡Generación completada con éxito!")
