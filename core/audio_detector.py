"""
Scrapy Local Audio Detector & Neural Speech-to-Text Engine.
Procesa audio directamente en la GPU (NVIDIA GTX 1660 SUPER) con CUDA float16 usando faster-whisper.
100% Local, Offline, sin costos de tokens y con precisión fonética extrema para español.
"""

import os
import sys
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Asegurar que las bibliotecas CUDA v12 de Ollama/NVIDIA estén cargadas globalmente
import ctypes

cuda_v12_path = "/home/jack/.local/lib/ollama/cuda_v12"
if os.path.exists(cuda_v12_path):
    current_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if cuda_v12_path not in current_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{cuda_v12_path}:{current_ld}"
    
    # Pre-cargar con RTLD_GLOBAL para que ctranslate2 y PyAV tengan acceso inmediato
    for lib_name in ["libcublasLt.so.12", "libcublas.so.12", "libcudart.so.12"]:
        p = os.path.join(cuda_v12_path, lib_name)
        if os.path.exists(p):
            try:
                ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
            except Exception:
                pass

logger = logging.getLogger("ScrapyAudioDetector")

class LocalAudioDetector:
    """Motor singleton de reconocimiento de audio local basado en faster-whisper."""
    
    _instance: Optional['LocalAudioDetector'] = None
    _model = None
    _device: str = "cpu"
    _compute_type: str = "int8"

    # Vocabulario de contexto para guiar a Whisper y evitar cualquier adivinanza
    INITIAL_PROMPT = (
        "Jack, Scrapy, LibreWolf, YouTube, Google Chrome, 6ix9ine, GOOBA, reproduce, busca, "
        "cierra, cierra la ventana, cierra la pestaña, cierra todas las pestañas, terminal, "
        "Linux Mint, volumen, canciones, música, archivos, memoria, procesador, tarjeta gráfica."
    )

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._initialize_model()

    @classmethod
    def get_instance(cls, model_size: str = "base") -> 'LocalAudioDetector':
        if cls._instance is None:
            cls._instance = LocalAudioDetector(model_size=model_size)
        return cls._instance

    def _initialize_model(self):
        try:
            import ctranslate2
            from faster_whisper import WhisperModel

            cuda_available = ctranslate2.get_cuda_device_count() > 0
            if cuda_available:
                self._device = "cuda"
                self._compute_type = "float16"
                logger.info("⚡ Scrapy Audio Detector: Aceleración CUDA activada (GPU GTX 1660 SUPER, float16).")
            else:
                self._device = "cpu"
                self._compute_type = "int8"
                logger.info("ℹ️ Scrapy Audio Detector: Ejecutando en CPU con cuantización int8.")

            t0 = time.time()
            self._model = WhisperModel(
                self.model_size,
                device=self._device,
                compute_type=self._compute_type,
                download_root="/home/jack/.cache/huggingface/hub"
            )
            logger.info(f"✅ Modelo Whisper '{self.model_size}' cargado exitosamente en {time.time()-t0:.2f}s.")
        except Exception as e:
            logger.warning(f"⚠️ Error al inicializar Whisper en {self._device}: {e}. Intentando fallback en CPU...")
            try:
                from faster_whisper import WhisperModel
                self._device = "cpu"
                self._compute_type = "int8"
                self._model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("✅ Fallback a Whisper 'base' en CPU exitoso.")
            except Exception as e2:
                logger.error(f"❌ Error crítico cargando Whisper: {e2}")
                self._model = None

    def transcribe_bytes(self, audio_bytes: bytes, file_suffix: str = ".webm") -> Dict[str, Any]:
        """
        Transcribe un flujo de bytes de audio directamente a texto en español.
        Usa Silero VAD para filtrar silencios y ruidos no vocales.
        """
        if not audio_bytes or len(audio_bytes) < 800:
            return {"status": "empty", "text": "", "duration": 0.0}

        if self._model is None:
            self._initialize_model()
            if self._model is None:
                return {"status": "error", "message": "Modelo Whisper no disponible", "text": ""}

        with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as tf:
            tf.write(audio_bytes)
            temp_path = tf.name

        try:
            t0 = time.time()
            segments, info = self._model.transcribe(
                temp_path,
                language="es",
                initial_prompt=self.INITIAL_PROMPT,
                vad_filter=False,
                beam_size=1,
                best_of=1,
                temperature=0.0
            )

            texts = []
            for seg in segments:
                t = seg.text.strip()
                if t:
                    texts.append(t)

            final_text = " ".join(texts).strip()
            elapsed = time.time() - t0

            logger.info(f"🎤 [AudioDetector] Transcripción en {elapsed:.2f}s: «{final_text}» (duración: {info.duration:.2f}s)")

            return {
                "status": "success",
                "text": final_text,
                "language": info.language,
                "duration": round(info.duration, 2),
                "elapsed": round(elapsed, 2),
                "device": self._device
            }
        except Exception as e:
            logger.error(f"❌ Error en transcripción de audio: {e}")
            return {"status": "error", "message": str(e), "text": ""}
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

# Instancia global exportada
audio_detector = LocalAudioDetector.get_instance()
