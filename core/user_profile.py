import os
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

PROFILE_FILE = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/user_profile.json")


class UserProfileManager:
    """
    Gestor de Perfil, Identidad y Memoria Personal de Jack Berrocal.
    Permite a Scrapy recordar fechas especiales (cumpleaños, aniversarios),
    preferencias personales, datos familiares y objetivos compartidos.
    """

    DEFAULT_PROFILE = {
        "user_name": "Jack Berrocal",
        "nickname": "Jack",
        "role": "Ingeniero de Sistemas & Desarrollador Full-Stack",
        "location": "Lima, Perú",
        "birthday": None,  # Ej: "15 de marzo"
        "partner": {
            "role": "Diseñadora Gráfica Experta",
            "skills": ["Photoshop", "Illustrator", "Branding", "Identidad Visual", "Redes Sociales", "Piezas Publicitarias"],
            "target": "Clientes de diseño recurrente ($100 - $150 USD por pack)"
        },
        "target_monthly_income": 1500,  # USD
        "currency": "USD",
        "preferred_browser": "librewolf",
        "voice_preference": "es-MX-JorgeNeural",
        "voice_speed": "+15%",
        "personal_facts": [
            {"key": "profesion", "fact": "Ingeniero de Sistemas experto en Python, FastAPI, React, SQL y web scraping."},
            {"key": "meta", "fact": "Generar $1,500 USD netos mensuales entre Jack y su pareja trabajando en remoto."},
            {"key": "equipo", "fact": "PC Linux Mint con GPU NVIDIA GeForce GTX 1660 Super y 16GB RAM."},
            {"key": "ciudad", "fact": "Reside en Lima, Perú."}
        ]
    }

    def __init__(self):
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not PROFILE_FILE.exists():
            self._save_to_disk(self.DEFAULT_PROFILE)
            return dict(self.DEFAULT_PROFILE)

        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Fusionar con valores por defecto si falta alguna clave
                for k, v in self.DEFAULT_PROFILE.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return dict(self.DEFAULT_PROFILE)

    def _save_to_disk(self, data: Dict[str, Any]):
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_profile(self) -> Dict[str, Any]:
        return self.profile

    def update_profile(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in updates.items():
            if k in self.profile:
                self.profile[k] = v
        self._save_to_disk(self.profile)
        return self.profile

    def set_birthday(self, birthday_str: str) -> bool:
        """Guarda o actualiza la fecha de cumpleaños de Jack."""
        clean = birthday_str.strip()
        if not clean:
            return False
        self.profile["birthday"] = clean
        # Actualizar o insertar en personal_facts
        found = False
        for item in self.profile.get("personal_facts", []):
            if item.get("key") == "cumpleanos":
                item["fact"] = f"El cumpleaños de Jack es el {clean}."
                found = True
                break
        if not found:
            self.profile.setdefault("personal_facts", []).append({
                "key": "cumpleanos",
                "fact": f"El cumpleaños de Jack es el {clean}."
            })
        self._save_to_disk(self.profile)
        return True

    def get_birthday(self) -> Optional[str]:
        return self.profile.get("birthday")

    def add_personal_fact(self, key: str, fact: str) -> bool:
        """Agrega un aprendizaje personal o recuerdo a la memoria."""
        if not fact.strip():
            return False
        facts = self.profile.setdefault("personal_facts", [])
        # Actualizar si existe la misma clave
        for f in facts:
            if f.get("key") == key:
                f["fact"] = fact.strip()
                self._save_to_disk(self.profile)
                return True
        facts.append({"key": key, "fact": fact.strip()})
        self._save_to_disk(self.profile)
        return True

    def remove_fact(self, key_or_term: str) -> bool:
        """Elimina un hecho o recuerdo de la memoria."""
        term_low = key_or_term.lower().strip()
        facts = self.profile.get("personal_facts", [])
        initial_len = len(facts)
        self.profile["personal_facts"] = [
            f for f in facts
            if f.get("key", "").lower() != term_low and term_low not in f.get("fact", "").lower()
        ]
        if len(self.profile["personal_facts"]) < initial_len:
            self._save_to_disk(self.profile)
            return True
        return False

    def get_context_for_prompt(self) -> str:
        """Genera el bloque de contexto personal humano para el LLM."""
        p = self.profile
        bday_txt = p.get('birthday') if p.get('birthday') else "Aún no especificado por Jack"
        facts_txt = "\n".join([f"- {f.get('fact')}" for f in p.get("personal_facts", [])])
        return (
            f"PERFIL PERSONAL DE JACK:\n"
            f"- Nombre: {p.get('user_name', 'Jack Berrocal')}\n"
            f"- Profesión: {p.get('role')}\n"
            f"- Ciudad: {p.get('location')}\n"
            f"- Cumpleaños: {bday_txt}\n"
            f"- Pareja: {p.get('partner', {}).get('role')}\n"
            f"- Meta mensual compartida: ${p.get('target_monthly_income')} USD netos\n"
            f"- Memoria y hechos aprendidos:\n{facts_txt}"
        )


_user_profile_instance = None

def get_user_profile() -> UserProfileManager:
    global _user_profile_instance
    if _user_profile_instance is None:
        _user_profile_instance = UserProfileManager()
    return _user_profile_instance
