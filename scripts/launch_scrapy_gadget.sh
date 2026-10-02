#!/usr/bin/env bash
# ==============================================================================
# Lanzador del Gadget de Escritorio de Scrapy AI
# Abre una ventana compacta tipo Gadget flotante con micrófono continuo y voz
# ==============================================================================

export DISPLAY=:0

PROFILE_DIR="/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/chrome_scrapy_profile"
mkdir -p "$PROFILE_DIR"

# Asegurar que el backend esté activo
systemctl --user start jobhunter.service 2>/dev/null || true

# Cerrar cualquier instancia previa huérfana de este perfil y limpiar locks
pkill -f "chrome.*chrome_scrapy_profile" 2>/dev/null || true
rm -f "$PROFILE_DIR"/Singleton* 2>/dev/null || true
sleep 1

# Lanzar ventana de app de Chrome con setsid para persistir como proceso daemon independiente
setsid google-chrome-stable \
    --app="http://localhost:8000/scrapy_widget" \
    --class="scrapy-ai" \
    --name="scrapy-ai" \
    --window-size=400,660 \
    --window-position=1480,200 \
    --user-data-dir="$PROFILE_DIR" \
    --autoplay-policy=no-user-gesture-required \
    --use-fake-ui-for-media-stream \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    --disable-features=Translate \
    --no-first-run \
    --no-default-browser-check \
    --disable-search-engine-choice-screen \
    --test-type \
    --disable-infobars \
    --disable-fre </dev/null >/dev/null 2>&1 &

CHROME_PID=$!
disown $CHROME_PID 2>/dev/null || true

# Esperar a que la ventana se dibuje, asignarle el ícono oficial y fijarla flotante
for i in {1..8}; do
    sleep 0.8
    WID=$(wmctrl -l | grep -i "Scrapy AI" | awk '{print $1}' | head -n 1)
    if [ -n "$WID" ]; then
        # Asignar ícono oficial a nivel X11 para la barra de tareas y el conmutador
        /home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/scripts/set_window_icon.py "$WID" 2>/dev/null || true
        wmctrl -i -r "$WID" -b add,above,sticky 2>/dev/null || true
        wmctrl -i -r "$WID" -e 0,1460,180,410,670 2>/dev/null || true
        wmctrl -i -a "$WID" 2>/dev/null || true
        echo "✅ Scrapy AI Gadget fijado con éxito en ventana $WID e ícono asignado"
        break
    fi
done
