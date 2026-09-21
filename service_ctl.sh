#!/bin/bash
# ==============================================================================
# 🚀 JobHunter AI - Gestor de Servicio Systemd de Arranque Automático
# ==============================================================================

SERVICE_NAME="jobhunter.service"

show_help() {
    echo "Uso: ./service_ctl.sh {status|start|stop|restart|logs|enable|disable}"
    echo ""
    echo "Comandos disponibles:"
    echo "  status   - Muestra si el agente está corriendo o detenido"
    echo "  start    - Inicia el agente en segundo plano"
    echo "  stop     - Detiene el agente"
    echo "  restart  - Reinicia el agente"
    echo "  logs     - Muestra los logs en tiempo real (Ctrl + C para salir)"
    echo "  enable   - Activa el auto-arranque al encender la PC"
    echo "  disable  - Desactiva el auto-arranque al encender la PC"
}

case "$1" in
    status)
        systemctl --user status "$SERVICE_NAME"
        ;;
    start)
        systemctl --user daemon-reload
        systemctl --user start "$SERVICE_NAME"
        echo "🟢 JobHunter AI iniciado en http://localhost:8000"
        ;;
    stop)
        systemctl --user stop "$SERVICE_NAME"
        echo "🛑 JobHunter AI detenido"
        ;;
    restart)
        systemctl --user daemon-reload
        systemctl --user restart "$SERVICE_NAME"
        echo "🔄 JobHunter AI reiniciado en http://localhost:8000"
        ;;
    logs)
        journalctl --user -u "$SERVICE_NAME" -f -n 50
        ;;
    enable)
        systemctl --user daemon-reload
        systemctl --user enable "$SERVICE_NAME"
        loginctl enable-linger "$USER" 2>/dev/null || true
        echo "✅ Auto-arranque ACTIVADO: JobHunter AI iniciará solo cada vez que enciendas la PC."
        ;;
    disable)
        systemctl --user disable "$SERVICE_NAME"
        echo "❌ Auto-arranque DESACTIVADO."
        ;;
    *)
        show_help
        exit 1
        ;;
esac
