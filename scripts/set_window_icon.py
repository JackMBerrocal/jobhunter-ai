#!/usr/bin/env python3
"""
Aplica el ícono oficial de Scrapy AI directamente al protocolo X11 (_NET_WM_ICON)
usando libX11.so nativo con ctypes para garantizar que aparezca en la barra de tareas
de Linux Mint (Cinnamon), Plank dock, panel inferior y conmutador Alt+Tab.
"""

import sys
import os
import subprocess
import ctypes
from ctypes import c_ulong, c_int, c_char_p, byref
from PIL import Image

ICON_PATH = "/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/web_ui/static/scrapy_app_icon.png"

# Cargar biblioteca X11 nativa
try:
    x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
    Display_p = ctypes.c_void_p
    Window = c_ulong
    Atom = c_ulong

    x11.XOpenDisplay.argtypes = [c_char_p]
    x11.XOpenDisplay.restype = Display_p
    x11.XInternAtom.argtypes = [Display_p, c_char_p, c_int]
    x11.XInternAtom.restype = Atom
    x11.XChangeProperty.argtypes = [
        Display_p, Window, Atom, Atom, c_int, c_int,
        ctypes.c_void_p, c_int
    ]
    x11.XChangeProperty.restype = c_int
    x11.XFlush.argtypes = [Display_p]
    x11.XFlush.restype = c_int
    x11.XCloseDisplay.argtypes = [Display_p]
    x11.XCloseDisplay.restype = c_int
except Exception as e:
    print(f"Error cargando libX11: {e}")
    sys.exit(1)

def apply_icon_to_window(win_id_int, icon_path=ICON_PATH):
    """Asigna _NET_WM_ICON multi-resolución (16, 24, 32, 48, 64, 128) a la ventana X11."""
    if not os.path.exists(icon_path):
        print(f"No existe el archivo de ícono: {icon_path}")
        return False
        
    display = x11.XOpenDisplay(None)
    if not display:
        print("No se pudo conectar al Display X11 (:0)")
        return False
        
    try:
        net_wm_icon = x11.XInternAtom(display, b'_NET_WM_ICON', 0)
        cardinal = x11.XInternAtom(display, b'CARDINAL', 0)
        
        raw_data = []
        for s in [16, 24, 32, 48, 64, 128]:
            im = Image.open(icon_path).convert('RGBA').resize((s, s), Image.Resampling.LANCZOS)
            raw_data.append(s)
            raw_data.append(s)
            pixels = im.load()
            for y in range(s):
                for x in range(s):
                    r, g, b, a = pixels[x, y]
                    argb = (a << 24) | (r << 16) | (g << 8) | b
                    raw_data.append(argb)
                    
        c_array = (c_ulong * len(raw_data))(*raw_data)
        # PropModeReplace = 0
        res = x11.XChangeProperty(display, win_id_int, net_wm_icon, cardinal, 32, 0, byref(c_array), len(raw_data))
        x11.XFlush(display)
        print(f"✅ Ícono oficial asignado a la ventana X11 {hex(win_id_int)}")
        return res == 1
    finally:
        x11.XCloseDisplay(display)

def tag_all_scrapy_windows(icon_path=ICON_PATH):
    """Busca y etiqueta cualquier ventana activa relacionada con Scrapy o JobHunter."""
    try:
        out = subprocess.check_output(['wmctrl', '-l'], text=True)
        tagged = 0
        for line in out.strip().splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 4:
                wid_hex, title = parts[0], parts[3]
                if any(k.lower() in title.lower() for k in ["scrapy", "jobhunter", "asistente virtual"]):
                    wid_int = int(wid_hex, 16)
                    if apply_icon_to_window(wid_int, icon_path):
                        tagged += 1
        return tagged
    except Exception as e:
        print(f"Error escaneando ventanas: {e}")
        return 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        wid = int(target, 16) if target.startswith("0x") else int(target)
        apply_icon_to_window(wid)
    else:
        count = tag_all_scrapy_windows()
        print(f"Total de ventanas etiquetadas con el ícono de Scrapy: {count}")
