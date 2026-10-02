#!/usr/bin/env bash
# ==============================================================================
# Inicia la ventana interactiva de Chromium para iniciar sesión en Freelancer.com
# Una vez iniciada sesión, el perfil queda guardado permanentemente en data/browser_profile
# ==============================================================================
cd "$(dirname "$0")/.."
./venv/bin/python -m core.browser_bidder login
