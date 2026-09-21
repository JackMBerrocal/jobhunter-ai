# 🚀 JobHunter AI - Agente Autónomo de Búsqueda Laboral

Sistema inteligente local diseñado para **Ingenieros de Sistemas sin experiencia laboral previa** que buscan trabajo **100% Remoto**. El agente automatiza la búsqueda de vacantes en **LinkedIn (Easy Apply)**, **Computrabajo** y **Bumeran**, responde preguntas de filtros con IA y monitorea la bandeja de correo para detectar y responder a invitaciones de entrevistas y pruebas técnicas.

---

## 🌟 Características Principales

1. **Sesión Persistente Segura (Sin compartir contraseñas)**:
   - Utiliza Chromium con almacenamiento local (`data/browser_profile`).
   - Inicias sesión manualmente una única vez con tus cuentas personales (LinkedIn, Computrabajo, Bumeran, Gmail) resolviendo 2FA y Captchas en tu propia máquina.
   - El agente reutiliza las cookies locales de forma transparente y segura.

2. **Estrategia para Candidato sin Experiencia Formal**:
   - Destaca proyectos académicos, universitarios y de GitHub registrados en `config/candidate_profile.yaml`.
   - Motor LLM que evalúa vacantes descartando ofertas Senior y respondiendo inteligentemente preguntas de cuestionarios (años de experiencia, pretensiones, disponibilidad, inglés).

3. **Monitoreo Inteligente de Correos**:
   - Escanea mensajes de reclutadores y clasifica automáticamente:
     - 🎯 **Invitación a Entrevista**: Extrae enlaces de videollamada y redacta confirmación formal.
     - 💻 **Prueba Técnica / Desafío de Código**: Identifica plataformas (HackerRank, repositorio, etc.) y plazos.
     - 📄 **Actualizaciones de Estado y Feedback**.
   - Permite aprobar respuestas con 1 clic en el Dashboard o envío automático en modo guardián.

4. **Dashboard Web Local Interactivo**:
   - Acceso en `http://localhost:8000` con diseño dark-mode de alta estética.
   - Vista en tiempo real de vacantes descubiertas, compatibilidad (Score %), postulaciones enviadas y consola de eventos.
   - Editor integrado del perfil del candidato.

---

## 🛠️ Instalación y Puesta en Marcha

### 1. Requisitos Previos
El entorno virtual ya se encuentra configurado en `venv/` con todas las dependencias instaladas (`playwright`, `fastapi`, `uvicorn`, `sqlalchemy`, etc.).

### 2. Iniciar Sesión en tus Cuentas (Paso Único)
Abre la ventana interactiva para autenticarte en tus plataformas:
```bash
./venv/bin/python main.py --login
```
Se abrirán las pestañas de **LinkedIn**, **Computrabajo**, **Bumeran** y **Gmail**. Inicia sesión, marca "Recordar sesión" y presiona `ENTER` en la terminal para guardar el perfil.

### 3. Iniciar el Dashboard Web / Servicio Autónomo 24/7

Puedes gestionar el servicio en segundo plano con auto-arranque ante cortes de energía:

```bash
# Ver estado del agente
./service_ctl.sh status

# Ver logs en vivo en tiempo real
./service_ctl.sh logs

# Iniciar o Reiniciar
./service_ctl.sh start
./service_ctl.sh restart

# Activar / Desactivar auto-arranque en reinicios de PC
./service_ctl.sh enable
./service_ctl.sh disable
```

El Dashboard está disponible de inmediato en:
👉 **[http://localhost:8000](http://localhost:8000)**

### 4. Resiliencia Automática (Anti-Cortes de Luz)
El servicio ya está registrado en `systemd --user` con persistencia linger activada (`Linger=yes`). Si la computadora se reinicia o sufre un corte de energía, JobHunter AI se levantará automáticamente en segundo plano en cuanto vuelva la corriente sin que tengas que intervenir.

---

## ⚙️ Estructura del Proyecto

```
jobhunter-ai/
├── config/
│   └── candidate_profile.yaml    # Perfil, habilidades, proyectos y respuestas a RRHH
├── core/
│   ├── database.py               # Base de datos SQLite local (Jobs, Emails, Logs)
│   └── llm_engine.py             # Evaluador de vacantes y redactor de respuestas
├── adapters/
│   ├── browser_manager.py        # Gestor de navegador Playwright con modo stealth
│   ├── base.py                   # Interfaz base de plataformas
│   ├── linkedin.py               # Adaptador de LinkedIn (Easy Apply)
│   ├── computrabajo.py           # Adaptador de Computrabajo
│   └── bumeran.py                # Adaptador de Bumeran
├── email_agent/
│   ├── scanner.py                # Escáner de correos en Gmail / IMAP
│   └── responder.py              # Clasificador y redactor de respuestas
├── web_ui/
│   ├── app.py                    # Servidor API FastAPI
│   └── templates/
│       └── index.html            # Dashboard web moderno con glassmorphism
├── data/                         # Base de datos y perfil persistente de navegador
├── login_setup.py                # Script asistente de inicio de sesión
├── main.py                       # CLI y lanzador principal
└── requirements.txt              # Dependencias de Python
```

---

## 🛡️ Consejos de Seguridad Anti-Baneo

- **No excedas 20-25 postulaciones al día por plataforma**: El agente ya incluye retardos aleatorios entre 45 y 120 segundos para simular comportamiento humano.
- **Mantén tu perfil actualizado**: Añade nuevos repositorios o proyectos en `config/candidate_profile.yaml` o desde la pestaña "Perfil del Candidato" en el Dashboard.
