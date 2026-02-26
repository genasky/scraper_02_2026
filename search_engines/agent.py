#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
AI Agent - модуль для автоматического выполнения задач
"""

import asyncio
import json
import logging
import re
import httpx
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from search_engines.ai_expander import OllamaManager, AIQueryExpander

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStep:
    step_id: int
    description: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class Task:
    task_id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    plan: List[TaskStep] = field(default_factory=list)
    current_step: int = 0
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    

class TaskAgent:
    """
    AI агент для автоматического выполнения задач:
    1. Получает задачу от пользователя
    2. Составляет план выполнения
    3. Выполняет план шаг за шагом
    """
    
    DEFAULT_OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.1:8b"
    
    AVAILABLE_ACTIONS = [
        "search",           # Выполнить поиск
        "scrape_contacts", # Собрать контакты с URLs
        "expand_query",    # Расширить запрос через AI
        "aggregate",       # Объединить результаты
        "export",          # Экспортировать результаты
    ]
    
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL):
        self.ollama_url = ollama_url.rstrip('/')
        self.model = model
        self.expander = AIQueryExpander(ollama_url=ollama_url, model=model)
        self.ollama_manager = OllamaManager()
        self._task_counter = 0
    
    def _generate_task_id(self) -> str:
        self._task_counter += 1
        import time
        return f"task_{int(time.time())}_{self._task_counter}"
    
    def check_connection(self) -> Dict[str, Any]:
        """Проверяет подключение к Ollama"""
        return self.expander.check_connection()
    
    def _build_planning_prompt(self, task_description: str) -> str:
        """Строит промпт для планирования задачи"""
        available_actions = "\n".join([f"- {a}: {self._get_action_description(a)}" 
                                       for a in self.AVAILABLE_ACTIONS])
        
        return f"""Ты - AI агент для автоматизации задач веб-поиска и сбора данных.

Доступные действия:
{available_actions}

Задача: "{task_description}"

Составь план выполнения этой задачи. План должен быть реалистичным и учитывать:
1. Какие действия необходимы
2. В каком порядке их выполнять
3. Какие параметры нужны для каждого действия

Формат ответа (строгий JSON):
{{
    "task_type": "Тип задачи (search, scrape_contacts, expand_query, aggregate, mixed)",
    "steps": [
        {{
            "step_id": 1,
            "action": "действие",
            "description": "описание шага",
            "params": {{"param1": "value1"}}
        }}
    ],
    "estimated_steps": количество шагов
}}

Верни ТОЛЬКО JSON без дополнительного текста."""

    def _get_action_description(self, action: str) -> str:
        """Возвращает описание действия"""
        descriptions = {
            "search": "Выполнить поисковый запрос через несколько поисковых систем",
            "scrape_contacts": "Собрать контакты (email, телефоны, соцсети) с веб-страниц",
            "expand_query": "Расширить поисковый запрос с помощью AI",
            "aggregate": "Объединить и обработать результаты из разных источников",
            "export": "Экспортировать результаты в файл (JSON/CSV)",
        }
        return descriptions.get(action, "Неизвестное действие")
    
    def _parse_plan_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Парсит ответ с планом от Ollama"""
        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```.*?\n', '', response)
                response = re.sub(r'\n```$', '', response)
            
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            return None
    
    async def create_plan(self, task_description: str) -> Dict[str, Any]:
        """Создает план выполнения задачи"""
        if not task_description or not task_description.strip():
            return {"success": False, "error": "Task description is empty"}
        
        ollama_status = self.expander.ensure_ollama(auto_start=True)
        if not ollama_status.get("running"):
            return {
                "success": False,
                "error": ollama_status.get("error", "Cannot start Ollama")
            }
        
        prompt = self._build_planning_prompt(task_description)
        
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 800
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    raw_response = data.get("response", "").strip()
                    plan_data = self._parse_plan_response(raw_response)
                    
                    if plan_data:
                        task_id = self._generate_task_id()
                        steps = []
                        for step_data in plan_data.get("steps", []):
                            step = TaskStep(
                                step_id=step_data.get("step_id", len(steps) + 1),
                                description=step_data.get("description", ""),
                                action=step_data.get("action", ""),
                                params=step_data.get("params", {})
                            )
                            steps.append(step)
                        
                        return {
                            "success": True,
                            "task_id": task_id,
                            "task_type": plan_data.get("task_type", "unknown"),
                            "plan": [
                                {
                                    "step_id": s.step_id,
                                    "description": s.description,
                                    "action": s.action,
                                    "params": s.params
                                }
                                for s in steps
                            ],
                            "estimated_steps": len(steps)
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Failed to parse plan"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Ollama error: {response.status_code}"
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_search(self, query: str, engines: List[str], pages: int = 1) -> Dict[str, Any]:
        """Выполняет поисковый запрос"""
        try:
            from search_engines.multiple_search_engines import MultipleSearchEngines
            
            search_engine = MultipleSearchEngines(
                engines=engines,
                language="ru",
                country="ru"
            )
            
            results = await search_engine.search(query, pages=pages)
            
            return {
                "success": True,
                "query": query,
                "results_count": len(results._results),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("link", ""),
                        "description": r.get("text", ""),
                        "engine": r.get("engine", "")
                    }
                    for r in results._results[:10]
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_scrape_contacts(self, urls: List[str]) -> Dict[str, Any]:
        """Собирает контакты с URLs"""
        from bs4 import BeautifulSoup
        import httpx
        
        try:
            from search_engines.config import get_parser
            from search_engines.output import parse_page_for_contacts as parse_contacts
            use_parser = True
        except ImportError:
            use_parser = False
        
        all_contacts = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            for url in urls[:10]:
                try:
                    response = await client.get(url)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    found_contacts = set()
                    
                    if use_parser:
                        parse_contacts(soup, url, found_contacts)
                    else:
                        self._basic_parse_contacts(soup, url, found_contacts)
                    
                    for contact_type, value, source in found_contacts:
                        all_contacts.append({
                            "type": contact_type,
                            "value": value,
                            "source": url
                        })
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
        
        return {
            "success": True,
            "contacts": all_contacts,
            "count": len(all_contacts)
        }
    
    def _basic_parse_contacts(self, soup, url: str, found_contacts: set):
        """Базовый парсинг контактов без внешних зависимостей"""
        import re
        
        text = soup.get_text()
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for email in re.finditer(email_pattern, text):
            found_contacts.add(('email', email.group(0).lower(), url))
        
        phone_pattern = r'\+\d{1,3}\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}'
        for phone in re.finditer(phone_pattern, text):
            found_contacts.add(('phone', phone.group(0), url))
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('mailto:'):
                found_contacts.add(('email', href.replace('mailto:', '').strip(), url))
            elif href.startswith('tel:'):
                found_contacts.add(('phone', href.replace('tel:', '').strip(), url))
    
    async def execute_expand_query(self, query: str) -> Dict[str, Any]:
        """Расширяет запрос через AI"""
        result = self.expander.expand_query(query, mode="both")
        return result
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Выполняет задачу по шагам"""
        results = {}
        errors = []
        
        for step in task.plan:
            if task.status == TaskStatus.CANCELLED:
                break
            
            task.status = TaskStatus.EXECUTING
            step.status = "executing"
            
            try:
                if step.action == "search":
                    query = step.params.get("query", "")
                    engines = step.params.get("engines", ["yahoo"])
                    pages = step.params.get("pages", 1)
                    
                    result = await self.execute_search(query, engines, pages)
                    step.result = result
                    step.status = "completed" if result.get("success") else "failed"
                    
                    if result.get("success"):
                        results[f"search_{step.step_id}"] = result
                    else:
                        errors.append(f"Search failed: {result.get('error')}")
                
                elif step.action == "scrape_contacts":
                    urls = step.params.get("urls", [])
                    result = await self.execute_scrape_contacts(urls)
                    step.result = result
                    step.status = "completed" if result.get("success") else "failed"
                    
                    if result.get("success"):
                        results[f"contacts_{step.step_id}"] = result
                    else:
                        errors.append(f"Contact scraping failed: {result.get('error')}")
                
                elif step.action == "expand_query":
                    query = step.params.get("query", "")
                    result = await self.execute_expand_query(query)
                    step.result = result
                    step.status = "completed" if result.get("success") else "failed"
                    
                    if result.get("success"):
                        results[f"expanded_{step.step_id}"] = result
                    else:
                        errors.append(f"Query expansion failed: {result.get('error')}")
                
                elif step.action == "export":
                    pass
                
                else:
                    step.status = "failed"
                    step.error = f"Unknown action: {step.action}"
                    errors.append(step.error)
                    
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Step {step.step_id} error: {e}")
        
        task.status = TaskStatus.COMPLETED if not errors else TaskStatus.FAILED
        task.results = results
        task.errors = errors
        
        return {
            "success": task.status == TaskStatus.COMPLETED,
            "task_id": task.task_id,
            "status": task.status.value,
            "completed_steps": len([s for s in task.plan if s.status == "completed"]),
            "total_steps": len(task.plan),
            "results": results,
            "errors": errors
        }
    
    async def run_task(self, task_description: str) -> Dict[str, Any]:
        """Полная обработка задачи: план + выполнение"""
        plan_result = await self.create_plan(task_description)
        
        if not plan_result.get("success"):
            return plan_result
        
        task_id = plan_result["task_id"]
        steps_data = plan_result["plan"]
        
        steps = []
        for s in steps_data:
            step = TaskStep(
                step_id=s["step_id"],
                description=s["description"],
                action=s["action"],
                params=s["params"]
            )
            steps.append(step)
        
        task = Task(
            task_id=task_id,
            description=task_description,
            status=TaskStatus.PLANNING,
            plan=steps
        )
        
        execute_result = await self.execute_task(task)
        
        return {
            **plan_result,
            "execution": execute_result
        }


agent = TaskAgent()
