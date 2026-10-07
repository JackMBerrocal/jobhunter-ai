import asyncio
import sys
from adapters.browser_manager import BrowserManager

async def run_login_session():
    print("=" * 65)
    print(" 🚀 INICIADOR DE SESIÓN PERSISTENTE - JOBHUNTER AI")
    print("=" * 65)
    print("Este script abrirá una ventana de Chromium en tu equipo con tu")
    print("perfil local guardado en: data/browser_profile")
    print()
    print("INSTRUCCIONES:")
    print(" 1. Inicia sesión con tus cuentas en las plataformas:")
    print("    - ⚡ Freelancer.com: https://www.freelancer.com/login")
    print("    - 💼 LinkedIn: https://www.linkedin.com/login")
    print("    - 🏢 Computrabajo: https://pe.computrabajo.com/candidate/login")
    print("    - 🌐 Bumeran: https://www.bumeran.com.pe/postulantes")
    print("    - 🇵🇪 Laborum: https://www.laborum.pe")
    print("    - 🚀 Torre.co: https://torre.ai")
    print("    - 💻 Get on Board: https://www.getonbrd.com/webpros/login")
    print("    - 🔎 Indeed: https://pe.indeed.com")
    print("    - 📧 Gmail / Google SSO: https://mail.google.com/")
    print(" 2. Marca la casilla 'Recordarme' o 'Mantener sesión iniciada'.")
    print(" 3. Resuelve cualquier verificación en 2 pasos o Captcha manualmente.")
    print(" 4. Una vez que hayas ingresado a todas tus cuentas, regresa aquí")
    print("    y presiona ENTER para guardar y cerrar.")
    print("=" * 65)
    
    portals = [
        ("Freelancer.com", "https://www.freelancer.com/login"),
        ("LinkedIn", "https://www.linkedin.com/login"),
        ("Computrabajo", "https://pe.computrabajo.com/candidate/login"),
        ("Bumeran", "https://www.bumeran.com.pe/postulantes"),
        ("Laborum Perú", "https://www.laborum.pe"),
        ("Torre.co", "https://torre.ai"),
        ("Get on Board", "https://www.getonbrd.com/webpros/login"),
        ("Indeed Perú", "https://pe.indeed.com"),
        ("Gmail", "https://mail.google.com/")
    ]

    # Modo visible (headless=False) para que el usuario interactúe
    bm = BrowserManager(user_data_dir="data/browser_profile", headless=False)
    
    try:
        context = await bm.initialize()
        for i, (name, url) in enumerate(portals):
            if i == 0:
                p = await bm.new_page_with_stealth()
            else:
                p = await context.new_page()
            print(f"[{i+1}/{len(portals)}] Abriendo {name}...")
            try:
                await p.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception as pe:
                print(f"  Advertencia cargando {name}: {pe}")
            await asyncio.sleep(0.5)

        print("\n🟢 El navegador está listo y abierto con las 8 pestañas.")
        print("➡️  Cuando termines de iniciar sesión en tus cuentas, presiona ENTER en esta consola...")
        
        # Esperar input del usuario en consola
        await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        
        print("\n✅ Guardando cookies y sesiones persistentes...")
    except Exception as e:
        print(f"\n❌ Error al abrir el navegador: {e}")
    finally:
        await bm.close()
        print("🔒 Navegador cerrado. ¡Tus sesiones han quedado guardadas de forma segura!")

if __name__ == "__main__":
    asyncio.run(run_login_session())
