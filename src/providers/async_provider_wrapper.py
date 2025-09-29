#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Асинхронный wrapper для LLM провайдеров
Фаза 5: Архитектурная оптимизация
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .base_provider import BaseProvider, ProviderConfig, ProviderStats
from .openrouter import OpenRouterProvider
from .groq import GroqProvider
from .replicate import ReplicateProvider
from ..core.cache_manager import MultiLevelCache


@dataclass
class AsyncProviderStats(ProviderStats):
    """📊 Расширенная статистика для асинхронного провайдера с учетом кеширования"""
    concurrent_requests: int = 0
    max_concurrent_requests: int = 0
    queue_wait_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0


class AsyncProviderWrapper:
    """🚀 Асинхронный wrapper для LLM провайдеров с кешированием"""

    def __init__(self, provider: BaseProvider, max_concurrent: int = 5, enable_cache: bool = True):
        self.provider = provider
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.async_stats = AsyncProviderStats()
        self.enable_cache = enable_cache
        self.cache = MultiLevelCache() if enable_cache else None
        
        # Копируем базовую статистику
        self.async_stats.requests_count = provider.stats.requests_count
        self.async_stats.success_count = provider.stats.success_count
        self.async_stats.error_count = provider.stats.error_count
        self.async_stats.total_tokens = provider.stats.total_tokens
        self.async_stats.avg_response_time = provider.stats.avg_response_time
        self.async_stats.last_request_time = provider.stats.last_request_time

    def _generate_cache_key(self, prompt: str, **kwargs) -> str:
        """Генерация ключа кеша для запроса"""
        import hashlib
        import json
        
        cache_data = {
            'prompt': prompt,
            'kwargs': {k: v for k, v in kwargs.items() if k not in ['stream', 'callback']}
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    async def make_request_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Асинхронный запрос к LLM с кешированием

        Args:
            prompt: Текст запроса
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ LLM
        """
        queue_start = time.time()
        
        # Проверка кеша
        cache_key = None
        if self.enable_cache and self.cache:
            cache_key = self._generate_cache_key(prompt, **kwargs)
            cached_response = self.cache.get_llm_response(
                cache_key, 
                self.provider.config.name
            )
            
            if cached_response:
                self.async_stats.cache_hits += 1
                self.async_stats.requests_count += 1
                
                # Обновляем статистику базового провайдера для кеш-попаданий
                self.provider.stats.requests_count += 1
                self.provider.stats.success_count += 1
                
                # Обновление коэффициента попаданий в кеш
                if self.async_stats.requests_count > 0:
                    self.async_stats.cache_hit_rate = self.async_stats.cache_hits / self.async_stats.requests_count
                
                return {
                    **cached_response,
                    'from_cache': True,
                    'provider': self.provider.config.name
                }
        
        async with self.semaphore:
            queue_wait = time.time() - queue_start
            self.async_stats.queue_wait_time = (
                (self.async_stats.queue_wait_time * self.async_stats.requests_count + queue_wait)
                / (self.async_stats.requests_count + 1)
            )
            
            self.async_stats.concurrent_requests += 1
            if self.async_stats.concurrent_requests > self.async_stats.max_concurrent_requests:
                self.async_stats.max_concurrent_requests = self.async_stats.concurrent_requests

            try:
                # Выполняем асинхронный запрос напрямую
                # Формируем request_data для провайдеров
                request_data = {
                    'messages': [{'role': 'user', 'content': prompt}],
                    **kwargs
                }
                result = await self.provider.make_request(request_data, **kwargs)
                
                # Сохранение в кеш
                if self.enable_cache and self.cache and cache_key:
                    self.cache.set_llm_response(cache_key, self.provider.config.name, result)
                
                # Обновляем асинхронную статистику
                self.async_stats.requests_count += 1
                self.async_stats.success_count += 1
                self.async_stats.cache_misses += 1
                
                # Обновление коэффициента попаданий в кеш
                if self.async_stats.requests_count > 0:
                    self.async_stats.cache_hit_rate = self.async_stats.cache_hits / self.async_stats.requests_count
                
                result['from_cache'] = False
                return result
                
            except Exception as e:
                self.async_stats.requests_count += 1
                self.async_stats.error_count += 1
                raise e
            finally:
                self.async_stats.concurrent_requests -= 1

    async def make_batch_requests_async(self, prompts: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        🚀 Пакетная асинхронная обработка запросов

        Args:
            prompts: Список текстов для обработки
            **kwargs: Дополнительные параметры

        Returns:
            list: Список ответов LLM
        """
        tasks = [
            self.make_request_async(prompt, **kwargs)
            for prompt in prompts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка исключений
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'error': str(result),
                    'prompt_index': i,
                    'provider': self.provider.config.name
                })
            else:
                processed_results.append(result)
        
        return processed_results

    def is_available(self) -> bool:
        """✅ Проверить доступность провайдера"""
        return self.provider.is_available()

    def get_stats(self) -> Dict[str, Any]:
        """📊 Получить расширенную статистику"""
        base_stats = self.provider.get_stats()
        
        async_stats = {
            'concurrent_requests': self.async_stats.concurrent_requests,
            'max_concurrent_requests': self.async_stats.max_concurrent_requests,
            'avg_queue_wait_time': self.async_stats.queue_wait_time,
            'semaphore_limit': self.max_concurrent,
            'cache_hits': self.async_stats.cache_hits,
            'cache_misses': self.async_stats.cache_misses,
            'cache_hit_rate': round(self.async_stats.cache_hit_rate * 100, 2)
        }
        
        base_stats['async_stats'] = async_stats
        return base_stats

    def reset_stats(self):
        """🔄 Сбросить статистику"""
        self.provider.reset_stats()
        self.async_stats = AsyncProviderStats()

    async def close(self):
        """🔄 Закрыть wrapper и освободить ресурсы"""
        self.executor.shutdown(wait=True)


class AsyncProviderManager:
    """🎯 Менеджер асинхронных провайдеров"""

    def __init__(self, providers: List[BaseProvider] = None, max_concurrent_per_provider: int = 5):
        providers = providers or []
        self.async_providers = [
            AsyncProviderWrapper(provider, max_concurrent_per_provider)
            for provider in providers
        ]
        self.providers = {}  # Словарь для хранения провайдеров по именам
        self.round_robin_index = 0
        self.max_concurrent_per_provider = max_concurrent_per_provider
    
    def add_provider(self, name: str, provider: BaseProvider):
        """➕ Добавить провайдер в менеджер"""
        wrapper = AsyncProviderWrapper(provider, self.max_concurrent_per_provider)
        self.async_providers.append(wrapper)
        self.providers[name] = wrapper
        print(f"   ✅ Провайдер {name} добавлен в AsyncProviderManager")

    async def make_request_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос с автоматическим выбором провайдера

        Args:
            prompt: Текст запроса
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ LLM
        """
        available_providers = [p for p in self.async_providers if p.is_available()]
        
        if not available_providers:
            raise RuntimeError("❌ Нет доступных провайдеров")

        # Сортировка по приоритету
        available_providers.sort(key=lambda p: p.provider.config.priority)
        
        # Попытка запроса к лучшему провайдеру
        for provider in available_providers:
            try:
                return await provider.make_request_async(prompt, **kwargs)
            except Exception as e:
                print(f"⚠️ Ошибка провайдера {provider.provider.config.name}: {e}")
                continue
        
        raise RuntimeError("❌ Все провайдеры недоступны")

    async def make_batch_requests_async(self, prompts: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        🚀 Пакетная обработка с распределением по провайдерам

        Args:
            prompts: Список текстов для обработки
            **kwargs: Дополнительные параметры

        Returns:
            list: Список ответов LLM
        """
        available_providers = [p for p in self.async_providers if p.is_available()]
        
        if not available_providers:
            raise RuntimeError("❌ Нет доступных провайдеров")

        # Распределение промптов по провайдерам (round-robin)
        provider_prompts = {i: [] for i in range(len(available_providers))}
        prompt_mapping = {}  # Для восстановления порядка
        
        for i, prompt in enumerate(prompts):
            provider_idx = i % len(available_providers)
            provider_prompts[provider_idx].append(prompt)
            prompt_mapping[prompt] = i

        # Параллельная обработка по провайдерам
        tasks = []
        for provider_idx, provider_prompt_list in provider_prompts.items():
            if provider_prompt_list:
                provider = available_providers[provider_idx]
                task = provider.make_batch_requests_async(provider_prompt_list, **kwargs)
                tasks.append((provider_idx, task))

        # Сбор результатов
        results = [None] * len(prompts)
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (provider_idx, _), provider_results in zip(tasks, completed_tasks):
            if isinstance(provider_results, Exception):
                continue
                
            provider_prompt_list = provider_prompts[provider_idx]
            for prompt, result in zip(provider_prompt_list, provider_results):
                original_index = prompt_mapping[prompt]
                results[original_index] = result

        return results

    def get_stats(self) -> Dict[str, Any]:
        """📊 Получить агрегированную статистику всех провайдеров"""
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        cache_hits = 0
        cache_misses = 0
        total_response_time = 0.0
        active_providers = 0
        
        for provider in self.async_providers:
            stats = provider.get_stats()
            
            # Получаем статистику кеширования из async_stats
            if 'async_stats' in stats:
                async_stats = stats['async_stats']
                cache_hits += async_stats.get('cache_hits', 0)
                cache_misses += async_stats.get('cache_misses', 0)
            
            # Получаем основную статистику
            requests = stats.get('requests_count', 0)
            
            # Добавляем кеш-попадания к общему количеству запросов
            async_stats = stats.get('async_stats', {})
            cache_hits_for_provider = async_stats.get('cache_hits', 0)
            total_provider_requests = requests + cache_hits_for_provider
            
            if total_provider_requests > 0:
                active_providers += 1
                total_requests += total_provider_requests
                success_count = stats.get('success_count', 0)
                error_count = stats.get('error_count', 0)
                # Кеш-попадания считаются успешными
                successful_requests += success_count + cache_hits_for_provider
                failed_requests += error_count
                total_response_time += stats.get('avg_response_time', 0.0)
        
        # Вычисляем средние значения
        avg_response_time = total_response_time / max(1, active_providers) if active_providers > 0 else 0.0
        cache_hit_rate = (cache_hits / max(1, cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0.0
        overall_success_rate = (successful_requests / max(1, total_requests) * 100) if total_requests > 0 else 0.0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': round(overall_success_rate, 2),
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': round(cache_hit_rate, 2),
            'average_response_time': round(avg_response_time, 3),
            'active_providers': active_providers,
            'total_providers': len(self.async_providers)
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """📊 Получить статистику всех провайдеров"""
        return {
            provider.provider.config.name: provider.get_stats()
            for provider in self.async_providers
        }

    async def close_all(self):
        """🔄 Закрыть все wrapper'ы"""
        await asyncio.gather(*[provider.close() for provider in self.async_providers])