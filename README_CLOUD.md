# ☁️ Guía de Ejecución en la Nube 24/7 (Sin Dejar Tu PC Encendida)

Esta guía te permite tener a **JobHunter AI** postulando, buscando ofertas y monitoreando correos las 24 horas del día, los 365 días del año, **incluso cuando tu PC personal esté completamente apagada**.

---

## 🌟 Opción 1: Oracle Cloud Free Tier (100% Gratuito Para Siempre) - RECOMENDADA

Oracle Cloud ofrece **máquinas virtuales gratuitas de por vida** (Always Free) con 24 GB de RAM y procesadores Ampere/ARM o AMD x86.

### Pasos rápidos:
1. Crea tu cuenta gratuita en [oracle.com/cloud/free](https://www.oracle.com/cloud/free/).
2. Crea una instancia de computación (Ubuntu 22.04 o 24.04).
3. Conéctate por SSH a tu servidor e instala Docker:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose
   ```
4. Sube tu paquete generado desde el panel de JobHunter (`jobhunter_cloud_bundle.tar.gz`) con `scp`:
   ```bash
   scp data/jobhunter_cloud_bundle.tar.gz ubuntu@<TU_IP_ORACLE>:~/
   ```
5. En tu servidor Oracle, descomprime e inicia:
   ```bash
   tar -xzf jobhunter_cloud_bundle.tar.gz
   sudo docker-compose up -d --build
   ```
6. **¡Listo!** El agente correrá de forma perpetua. Puedes apagar tu PC.

---

## 🚀 Opción 2: Railway o Render (Despliegue en 1 Clic con Docker)

1. En [railway.app](https://railway.app) o [render.com](https://render.com), crea un nuevo servicio desde **Docker Image** o subiendo este repositorio.
2. Agrega una variable de entorno:
   - `HEADLESS=true`
   - `PORT=8000`
3. El servicio se levantará y te dará una URL pública tipo `https://tu-jobhunter.up.railway.app` accesible desde tu teléfono móvil.

---

## 🖥️ Opción 3: Cualquier Servidor VPS (DigitalOcean / Hetzner / Hostinger)

Si tienes un VPS básico ($3 a $4 USD/mes):
```bash
# 1. Clonar o subir el paquete
tar -xzf jobhunter_cloud_bundle.tar.gz

# 2. Iniciar en segundo plano
docker-compose up -d --build

# 3. Ver logs en vivo
docker logs -f jobhunter-ai-cloud
```

---

## 🔄 ¿Cómo se sincronizan mis sesiones de Upwork, Workana y LinkedIn?
El paquete generado por el botón **"📦 Generar Paquete de Despliegue en la Nube"** en tu panel incluye el archivo `data/storage_state.json` con todas tus cookies autenticadas. El contenedor Docker arranca con tus sesiones ya activas.
