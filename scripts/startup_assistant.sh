#!/usr/bin/env bash
# ==============================================================================
# JobHunter AI - Script de Arranque Automático & Saludo de Asistente de Escritorio
# Se ejecuta al iniciar sesión en el escritorio Linux (Cinnamon / X11 / Wayland)
# ==============================================================================

# 1. Esperar brevemente a que el servidor de sonido y el entorno de escritorio carguen
sleep 2

# 2. Asegurar que el servicio de JobHunter AI esté activo
systemctl --user start jobhunter.service 2>/dev/null || true

# 3. Esperar a que el servidor web local esté listo (hasta 12 segundos)
for i in {1..12}; do
    if curl -s -f http://localhost:8000/api/system/health >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 4. ABRIR DE INMEDIATO LA PÁGINA EN EL NAVEGADOR (Centro Freelance & Pipeline)
if command -v google-chrome >/dev/null 2>&1; then
    google-chrome "http://localhost:8000" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:8000" >/dev/null 2>&1 &
elif command -v librewolf >/dev/null 2>&1; then
    librewolf "http://localhost:8000" >/dev/null 2>&1 &
fi

# 5. Notificación nativa de escritorio en Linux
if command -v notify-send >/dev/null 2>&1; then
    notify-send -u normal -a "JobHunter AI" \
        "💼 Centro Freelance & Gigs Activo" \
        "¡Hola Jack! Tu panel de monitoreo está abierto en pantalla listo para vigilar ofertas y respuestas de clientes."
fi

# 6. Saludo por voz en los altavoces del ordenador (en español)
if command -v spd-say >/dev/null 2>&1; then
    spd-say -l es "Hola Jack. JobHunter AI y tu Centro Freelance están abiertos en tu pantalla. Vamos por la meta de cinco mil dólares." 2>/dev/null || true
fi

# 7. Abrir el Gadget Flotante de Scrapy en el Escritorio
sleep 1
if [ -f "/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/scripts/launch_scrapy_gadget.sh" ]; then
    /home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/scripts/launch_scrapy_gadget.sh >/dev/null 2>&1 &
fi
