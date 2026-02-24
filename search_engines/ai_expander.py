#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
AI Query Expander - модуль для расширения поисковых запросов через Ollama
"""

import httpx
import json
import logging
import os
import shutil
import subprocess
import time
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class OllamaManager:
    """Управление запуском и остановкой Ollama"""
    
    DEFAULT_URL = "http://localhost:11434"
    CHECK_INTERVAL = 2  # секунд между проверками
    DEFAULT_START_TIMEOUT = 30
    
    def __init__(self):
        self.ollama_path: Optional[str] = None
        self.started_pid: Optional[int] = None
        self._find_ollama()
    
    def _find_ollama(self) -> Optional[str]:
        """Ищет путь к ollama"""
        # 1. Проверить PATH
        path = shutil.which('ollama')
        if path:
            self.ollama_path = path
            return path
        
        # 2. macOS стандартные пути
        macos_paths = [
            os.path.expanduser('~/ollama'),
            '/usr/local/bin/ollama',
            '/opt/homebrew/bin/ollama',
        ]
        
        for p in macos_paths:
            if os.path.exists(p):
                self.ollama_path = p
                return p
        
        return None
    
    def is_running(self, url: str = DEFAULT_URL) -> bool:
        """Проверяет запущена ли Ollama"""
        try:
            with httpx.Client(timeout=2) as client:
                response = client.get(f"{url}/api/tags")
                return response.status_code == 200
        except:
            return False
    
    def start(self, wait_seconds: int = DEFAULT_START_TIMEOUT) -> Dict[str, Any]:
        """Запускает Ollama и ждёт готовности"""
        if self.is_running():
            return {"success": True, "already_running": True, "time_taken": 0}
        
        if not self.ollama_path:
            self._find_ollama()
            if not self.ollama_path:
                return {"success": False, "error": "Ollama not found. Install from https://ollama.com"}
        
        try:
            # Запускаем в фоне
            process = subprocess.Popen(
                [self.ollama_path, 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            self.started_pid = process.pid
            
            # Ждём готовности
            elapsed = 0
            while elapsed < wait_seconds:
                if self.is_running():
                    return {"success": True, "already_running": False, "time_taken": elapsed, "pid": self.started_pid}
                time.sleep(self.CHECK_INTERVAL)
                elapsed += self.CHECK_INTERVAL
            
            return {"success": False, "error": f"Ollama did not start within {wait_seconds} seconds"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop(self) -> Dict[str, Any]:
        """Останавливает запущенный процесс (если мы его запустили)"""
        if not self.started_pid:
            return {"success": False, "error": "No PID recorded"}
        
        try:
            os.kill(self.started_pid, 15)  # SIGTERM
            time.sleep(1)
            
            # Проверим процесс
            try:
                os.kill(self.started_pid, 0)
                # Процесс ещё жив - kill -9
                os.kill(self.started_pid, 9)
            except OSError:
                pass  # Процесс уже мёртв
            
            self.started_pid = None
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает полный статус"""
        running = self.is_running()
        return {
            "path": self.ollama_path,
            "running": running,
            "can_auto_start": self.ollama_path is not None,
            "is_self_started": self.started_pid is not None and running
        }


class AIQueryExpander:
    """Класс для расширения поисковых запросов через локальную Ollama"""
    
    DEFAULT_OLLAMA_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 120
    
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL, model: str = "llama3.1:8b"):
        self.ollama_url = ollama_url.rstrip('/')
        self.model = model
        self.available_models: List[str] = []
        self.ollama_manager = OllamaManager()
        self._was_auto_started = False
        self._auto_stop_enabled = True
    
    def check_connection(self) -> Dict[str, Any]:
        """Проверяет подключение к Ollama и возвращает статус"""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get('name', '') for m in data.get('models', [])]
                    self.available_models = models
                    
                    manager_status = self.ollama_manager.get_status()
                    
                    return {
                        "connected": True,
                        "models": models,
                        "default_model": self.model if self.model in models else (models[0] if models else None),
                        "can_auto_start": manager_status.get("can_auto_start", False),
                        "is_self_started": manager_status.get("is_self_started", False),
                        "ollama_path": manager_status.get("path")
                    }
                return {"connected": False, "error": f"Status: {response.status_code}"}
        except httpx.ConnectError:
            return {"connected": False, "error": "Cannot connect to Ollama"}
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def ensure_ollama(self, auto_start: bool = True) -> Dict[str, Any]:
        """Гарантирует что Ollama запущена"""
        if self.ollama_manager.is_running():
            return {"running": True, "auto_started": False, "already_running": True}
        
        if not auto_start:
            return {"running": False, "auto_started": False, "error": "Ollama not running"}
        
        # Автозапуск
        result = self.ollama_manager.start()
        self._was_auto_started = result.get("success", False)
        
        return {
            "running": result.get("success", False),
            "auto_started": self._was_auto_started,
            "time_taken": result.get("time_taken", 0),
            "error": result.get("error")
        }
    
    def stop_if_needed(self) -> Dict[str, Any]:
        """Останавливает Ollama если мы её запустили и автостоп включён"""
        if self._was_auto_started and self._auto_stop_enabled:
            result = self.ollama_manager.stop()
            self._was_auto_started = False
            return result
        return {"success": True, "skipped": True}
    
    def set_auto_stop(self, enabled: bool):
        """Включить/выключить автоостановку"""
        self._auto_stop_enabled = enabled
    
    def list_models(self) -> List[str]:
        """Возвращает список доступных моделей"""
        status = self.check_connection()
        return status.get("models", [])
    
    def _build_prompt(self, query: str, mode: str) -> str:
        """Строит промпт для Ollama в зависимости от режима"""
        
        if mode == "similar":
            return f"""Ты - помощник для генерации поисковых запросов.
Сгенерируй 5 альтернативных поисковых запросов, которые имеют тот же смысл, что и исходный запрос.

Исходный запрос: "{query}"

Верни ТОЛЬКО список запросов, по одному в строке, без нумерации и дополнительного текста."""
        
        elif mode == "expanded":
            return f"""Ты - помощник для генерации поисковых запросов.
Расширь исходный запрос, добавив связанные термины и синонимы, чтобы получить более полные результаты поиска.

Исходный запрос: "{query}"

Сгенерируй 5 расширенных вариантов запроса, по одному в строке, без нумерации и дополнительного текста."""
        
        else:  # "both"
            return f"""Ты - помощник для генерации поисковых запросов.
Для исходного запроса сгенерируй:
1. 3 альтернативных запроса (похожих по смыслу)
2. 2 расширенных запроса (с добавлением связанных терминов)

Исходный запрос: "{query}"

Формат ответа (каждый запрос с новой строки, без нумерации):
---ALTERNATIVE---
---EXPANDED---"""
    
    def _parse_response(self, response: str, mode: str) -> List[str]:
        """Парсит ответ от Ollama и извлекает варианты запросов"""
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        variants = []
        
        if mode == "both":
            for line in lines:
                if line and not line.startswith('---'):
                    variants.append(line)
            
            if not variants:
                variants = lines
        else:
            variants = [line for line in lines if line and not line.startswith('---')]
        
        return variants[:10]
    
    def expand_query(self, query: str, mode: str = "both", auto_start: bool = True) -> Dict[str, Any]:
        """Расширяет один запрос и возвращает варианты"""
        if not query or not query.strip():
            return {"success": False, "error": "Empty query"}
        
        # Проверка/запуск Ollama
        ollama_status = self.ensure_ollama(auto_start=auto_start)
        
        if not ollama_status.get("running"):
            return {
                "success": False, 
                "error": ollama_status.get("error", "Cannot start Ollama"),
                "ollama_auto_start_attempted": True,
                "ollama_auto_start_success": False
            }
        
        prompt = self._build_prompt(query.strip(), mode)
        
        try:
            with httpx.Client(timeout=self.DEFAULT_TIMEOUT) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 300
                    }
                }
                
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    raw_response = data.get("response", "").strip()
                    variants = self._parse_response(raw_response, mode)
                    
                    return {
                        "success": True,
                        "original": query,
                        "variants": variants,
                        "mode": mode,
                        "model": self.model,
                        "ollama_auto_started": ollama_status.get("auto_started", False),
                        "ollama_start_time": ollama_status.get("time_taken", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ollama error: {response.status_code}"
                    }
                    
        except httpx.ConnectError:
            return {"success": False, "error": "Cannot connect to Ollama. Make sure Ollama is running."}
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timeout. Try a smaller model or check Ollama."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def expand_queries(self, queries: List[str], mode: str = "both", auto_start: bool = True) -> Dict[str, Any]:
        """Расширяет список запросов"""
        all_variants = []
        errors = []
        ollama_auto_started = False
        
        for query in queries:
            result = self.expand_query(query, mode, auto_start)
            if result.get("success"):
                all_variants.extend(result.get("variants", []))
                if result.get("ollama_auto_started"):
                    ollama_auto_started = True
            else:
                errors.append(f"{query}: {result.get('error')}")
        
        return {
            "success": True if all_variants else False,
            "original_queries": queries,
            "all_variants": list(dict.fromkeys(all_variants)),
            "errors": errors,
            "ollama_auto_started": ollama_auto_started
        }


expander = AIQueryExpander()
