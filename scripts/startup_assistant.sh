#!/usr/bin/env bash
# ==============================================================================
# JobHunter AI - Script de Arranque Automático & Saludo de Asistente de Escritorio
# Se ejecuta al iniciar sesión en el escritorio Linux (Cinnamon / X11 / Wayland)
# ==============================================================================

# 1. Esperar brevemente a que el servidor de sonido y el entorno de escritorio carguen
sleep 3

# 2. Asegurar que el servicio de JobHunter AI esté activo
systemctl --user start jobhunter.service 2>/dev/null || true

# 3. Notificación nativa de escritorio en Linux
if command -v notify-send >/dev/null 2>&1; then
    notify-send -u normal -a "JobHunter AI" \
        "🤖 Asistente Virtual Activo" \
        "¡Hola Jack! Tu asistente está en línea monitoreando oportunidades por hora y de diseño."
fi

# 4. Saludo por voz en los altavoces del ordenador (en español)
if command -v spd-say >/dev/null 2>&1; then
    spd-say -l es "Hola Jack, Scrapy está en línea en tu escritorio. Di Hola Scrapy cuando me necesites." 2>/dev/null || true
fi

# 5. Abrir el Gadget Flotante de Scrapy en el Escritorio
sleep 1
/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/scripts/launch_scrapy_gadget.sh >/dev/null 2>&1 &
