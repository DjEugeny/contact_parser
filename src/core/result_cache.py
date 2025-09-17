import redis
import json
import hashlib
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
import os


@dataclass
class CacheConfig:
    """
    ⚙️ Конфигурация системы кеширования
    """
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # TTL для разных типов данных (в секундах)
    extraction_ttl: int = 3600  # 1 час для результатов извлечения
    ocr_ttl: int = 86400  # 24 часа для OCR результатов
    prompt_ttl: int = 7200  # 2 часа для промптов
    
    # Локальное кеширование
    enable_local_cache: bool = True
    local_cache_dir: str = "cache"
    local_cache_max_size_mb: int = 100
    
    # Сжатие данных
    enable_compression: bool = True
    compression_threshold: int = 1024  # Сжимать данные больше 1KB


class ResultCache:
    """
    💾 Система кеширования результатов с Redis и локальным fallback
    
    Реализует рекомендацию 9 из отчета по архитектуре:
    - Redis кеш для результатов извлечения
    - Локальное кеширование как fallback
    - Сжатие больших данных
    - TTL для разных типов контента
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client = None
        self.local_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'redis_hits': 0,
            'local_hits': 0,
            'redis_errors': 0,
            'cache_size_mb': 0.0
        }
        
        # Инициализация Redis
        self._init_redis()
        
        # Инициализация локального кеша
        self._init_local_cache()
        
        print("💾 ResultCache инициализирован")
        print(f"   🔴 Redis: {'✅ подключен' if self.redis_client else '❌ недоступен'}")
        print(f"   📁 Локальный кеш: {'✅ включен' if self.config.enable_local_cache else '❌ отключен'}")
        print(f"   🗜️ Сжатие: {'✅ включено' if self.config.enable_compression else '❌ отключено'}")
    
    def _init_redis(self):
        """
        🔴 Инициализация Redis подключения
        """
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=False,  # Для работы с binary данными
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Проверяем подключение
            self.redis_client.ping()
            print(f"✅ Redis подключен: {self.config.redis_host}:{self.config.redis_port}")
            
        except Exception as e:
            print(f"⚠️ Redis недоступен: {e}")
            print("📁 Будет использоваться только локальное кеширование")
            self.redis_client = None
    
    def _init_local_cache(self):
        """
        📁 Инициализация локального кеша
        """
        if self.config.enable_local_cache:
            cache_dir = Path(self.config.local_cache_dir)
            cache_dir.mkdir(exist_ok=True)
            print(f"📁 Локальный кеш: {cache_dir.absolute()}")
    
    def get_extraction_result(self, content_hash: str) -> Optional[Dict]:
        """
        🔍 Получение результата извлечения из кеша
        """
        cache_key = f"extract:{content_hash}"
        
        # Сначала пробуем Redis
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    result = self._deserialize_data(cached_data)
                    if result:
                        self.cache_stats['hits'] += 1
                        self.cache_stats['redis_hits'] += 1
                        print(f"💾 Cache HIT (Redis): {content_hash[:8]}...")
                        return result
            except Exception as e:
                print(f"⚠️ Redis ошибка при чтении: {e}")
                self.cache_stats['redis_errors'] += 1
        
        # Fallback на локальный кеш
        if self.config.enable_local_cache:
            local_result = self._get_local_cache(cache_key)
            if local_result:
                self.cache_stats['hits'] += 1
                self.cache_stats['local_hits'] += 1
                print(f"💾 Cache HIT (Local): {content_hash[:8]}...")
                return local_result
        
        # Cache miss
        self.cache_stats['misses'] += 1
        print(f"💾 Cache MISS: {content_hash[:8]}...")
        return None
    
    def cache_extraction_result(self, content_hash: str, result: Dict, ttl: int = None) -> bool:
        """
        💾 Кеширование результата извлечения
        """
        cache_key = f"extract:{content_hash}"
        ttl = ttl or self.config.extraction_ttl
        
        # Добавляем метаданные кеша
        cache_data = {
            'result': result,
            'cached_at': time.time(),
            'content_hash': content_hash,
            'cache_version': '1.0'
        }
        
        success = False
        
        # Кешируем в Redis
        if self.redis_client:
            try:
                serialized_data = self._serialize_data(cache_data)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                success = True
                print(f"💾 Cached to Redis: {content_hash[:8]}... (TTL: {ttl}s)")
            except Exception as e:
                print(f"⚠️ Redis ошибка при записи: {e}")
                self.cache_stats['redis_errors'] += 1
        
        # Кешируем локально
        if self.config.enable_local_cache:
            local_success = self._set_local_cache(cache_key, cache_data, ttl)
            success = success or local_success
        
        return success
    
    def get_ocr_result(self, file_hash: str) -> Optional[str]:
        """
        🔍 Получение результата OCR из кеша
        """
        cache_key = f"ocr:{file_hash}"
        
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    result = self._deserialize_data(cached_data)
                    if result and 'ocr_text' in result:
                        self.cache_stats['hits'] += 1
                        self.cache_stats['redis_hits'] += 1
                        print(f"💾 OCR Cache HIT: {file_hash[:8]}...")
                        return result['ocr_text']
            except Exception as e:
                print(f"⚠️ Redis ошибка при чтении OCR: {e}")
                self.cache_stats['redis_errors'] += 1
        
        # Локальный кеш для OCR
        if self.config.enable_local_cache:
            local_result = self._get_local_cache(cache_key)
            if local_result and 'ocr_text' in local_result:
                self.cache_stats['hits'] += 1
                self.cache_stats['local_hits'] += 1
                print(f"💾 OCR Cache HIT (Local): {file_hash[:8]}...")
                return local_result['ocr_text']
        
        self.cache_stats['misses'] += 1
        return None
    
    def cache_ocr_result(self, file_hash: str, ocr_text: str, ttl: int = None) -> bool:
        """
        💾 Кеширование результата OCR
        """
        cache_key = f"ocr:{file_hash}"
        ttl = ttl or self.config.ocr_ttl
        
        cache_data = {
            'ocr_text': ocr_text,
            'cached_at': time.time(),
            'file_hash': file_hash,
            'cache_version': '1.0'
        }
        
        success = False
        
        # Redis кеширование
        if self.redis_client:
            try:
                serialized_data = self._serialize_data(cache_data)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                success = True
                print(f"💾 OCR Cached to Redis: {file_hash[:8]}... (TTL: {ttl}s)")
            except Exception as e:
                print(f"⚠️ Redis ошибка при записи OCR: {e}")
                self.cache_stats['redis_errors'] += 1
        
        # Локальное кеширование
        if self.config.enable_local_cache:
            local_success = self._set_local_cache(cache_key, cache_data, ttl)
            success = success or local_success
        
        return success
    
    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """
        🔍 Получение промпта из кеша
        """
        cache_key = f"prompt:{prompt_name}"
        
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    result = self._deserialize_data(cached_data)
                    if result and 'prompt_text' in result:
                        self.cache_stats['hits'] += 1
                        self.cache_stats['redis_hits'] += 1
                        return result['prompt_text']
            except Exception as e:
                print(f"⚠️ Redis ошибка при чтении промпта: {e}")
                self.cache_stats['redis_errors'] += 1
        
        # Локальный кеш для промптов
        if self.config.enable_local_cache:
            local_result = self._get_local_cache(cache_key)
            if local_result and 'prompt_text' in local_result:
                self.cache_stats['hits'] += 1
                self.cache_stats['local_hits'] += 1
                return local_result['prompt_text']
        
        self.cache_stats['misses'] += 1
        return None
    
    def cache_prompt(self, prompt_name: str, prompt_text: str, ttl: int = None) -> bool:
        """
        💾 Кеширование промпта
        """
        cache_key = f"prompt:{prompt_name}"
        ttl = ttl or self.config.prompt_ttl
        
        cache_data = {
            'prompt_text': prompt_text,
            'cached_at': time.time(),
            'prompt_name': prompt_name,
            'cache_version': '1.0'
        }
        
        success = False
        
        # Redis кеширование
        if self.redis_client:
            try:
                serialized_data = self._serialize_data(cache_data)
                self.redis_client.setex(cache_key, ttl, serialized_data)
                success = True
            except Exception as e:
                print(f"⚠️ Redis ошибка при записи промпта: {e}")
                self.cache_stats['redis_errors'] += 1
        
        # Локальное кеширование
        if self.config.enable_local_cache:
            local_success = self._set_local_cache(cache_key, cache_data, ttl)
            success = success or local_success
        
        return success
    
    def _serialize_data(self, data: Dict) -> bytes:
        """
        📦 Сериализация данных с опциональным сжатием
        """
        try:
            # Сериализуем в JSON
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            json_bytes = json_data.encode('utf-8')
            
            # Сжимаем если данные большие
            if self.config.enable_compression and len(json_bytes) > self.config.compression_threshold:
                import gzip
                compressed_data = gzip.compress(json_bytes)
                # Добавляем маркер сжатия
                return b'GZIP:' + compressed_data
            
            return json_bytes
            
        except Exception as e:
            print(f"❌ Ошибка сериализации: {e}")
            return b''
    
    def _deserialize_data(self, data: bytes) -> Optional[Dict]:
        """
        📦 Десериализация данных с поддержкой сжатия
        """
        try:
            # Проверяем сжатие
            if data.startswith(b'GZIP:'):
                import gzip
                compressed_data = data[5:]  # Убираем маркер 'GZIP:'
                json_bytes = gzip.decompress(compressed_data)
            else:
                json_bytes = data
            
            # Десериализуем JSON
            json_data = json_bytes.decode('utf-8')
            return json.loads(json_data)
            
        except Exception as e:
            print(f"❌ Ошибка десериализации: {e}")
            return None
    
    def _get_local_cache(self, cache_key: str) -> Optional[Dict]:
        """
        📁 Получение из локального кеша
        """
        try:
            # Сначала проверяем память
            if cache_key in self.local_cache:
                cache_entry = self.local_cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    return cache_entry['data']
                else:
                    del self.local_cache[cache_key]
            
            # Проверяем файловый кеш
            cache_file = Path(self.config.local_cache_dir) / f"{cache_key.replace(':', '_')}.cache"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    cache_entry = pickle.load(f)
                
                if self._is_cache_valid(cache_entry):
                    # Загружаем в память для быстрого доступа
                    self.local_cache[cache_key] = cache_entry
                    return cache_entry['data']
                else:
                    cache_file.unlink()  # Удаляем устаревший файл
            
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка локального кеша при чтении: {e}")
            return None
    
    def _set_local_cache(self, cache_key: str, data: Dict, ttl: int) -> bool:
        """
        📁 Сохранение в локальный кеш
        """
        try:
            cache_entry = {
                'data': data,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
            
            # Сохраняем в память
            self.local_cache[cache_key] = cache_entry
            
            # Сохраняем в файл
            cache_file = Path(self.config.local_cache_dir) / f"{cache_key.replace(':', '_')}.cache"
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_entry, f)
            
            # Очищаем старые файлы если нужно
            self._cleanup_local_cache()
            
            return True
            
        except Exception as e:
            print(f"⚠️ Ошибка локального кеша при записи: {e}")
            return False
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """
        ⏰ Проверка валидности кеша по TTL
        """
        return time.time() < cache_entry.get('expires_at', 0)
    
    def _cleanup_local_cache(self):
        """
        🧹 Очистка устаревших файлов локального кеша
        """
        try:
            cache_dir = Path(self.config.local_cache_dir)
            if not cache_dir.exists():
                return
            
            current_time = time.time()
            total_size = 0
            cache_files = []
            
            # Собираем информацию о файлах
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    stat = cache_file.stat()
                    total_size += stat.st_size
                    cache_files.append({
                        'file': cache_file,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    })
                except:
                    continue
            
            # Обновляем статистику
            self.cache_stats['cache_size_mb'] = total_size / 1024 / 1024
            
            # Удаляем устаревшие файлы
            for file_info in cache_files:
                try:
                    with open(file_info['file'], 'rb') as f:
                        cache_entry = pickle.load(f)
                    
                    if not self._is_cache_valid(cache_entry):
                        file_info['file'].unlink()
                        total_size -= file_info['size']
                except:
                    # Удаляем поврежденные файлы
                    try:
                        file_info['file'].unlink()
                        total_size -= file_info['size']
                    except:
                        pass
            
            # Если размер превышает лимит, удаляем старые файлы
            max_size_bytes = self.config.local_cache_max_size_mb * 1024 * 1024
            if total_size > max_size_bytes:
                # Сортируем по времени модификации (старые первыми)
                cache_files.sort(key=lambda x: x['mtime'])
                
                for file_info in cache_files:
                    if total_size <= max_size_bytes:
                        break
                    
                    try:
                        file_info['file'].unlink()
                        total_size -= file_info['size']
                    except:
                        pass
            
            # Обновляем статистику
            self.cache_stats['cache_size_mb'] = total_size / 1024 / 1024
            
        except Exception as e:
            print(f"⚠️ Ошибка очистки кеша: {e}")
    
    def clear_cache(self, pattern: str = None) -> int:
        """
        🧹 Очистка кеша
        
        Args:
            pattern: Паттерн для очистки (например, "extract:*" или "ocr:*")
        
        Returns:
            Количество удаленных ключей
        """
        deleted_count = 0
        
        # Очистка Redis
        if self.redis_client:
            try:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        deleted_count += self.redis_client.delete(*keys)
                else:
                    self.redis_client.flushdb()
                    deleted_count += 1
            except Exception as e:
                print(f"⚠️ Ошибка очистки Redis: {e}")
        
        # Очистка локального кеша
        if self.config.enable_local_cache:
            try:
                cache_dir = Path(self.config.local_cache_dir)
                if pattern:
                    # Конвертируем Redis паттерн в glob паттерн
                    glob_pattern = pattern.replace(':', '_').replace('*', '*')
                    for cache_file in cache_dir.glob(f"{glob_pattern}.cache"):
                        cache_file.unlink()
                        deleted_count += 1
                else:
                    for cache_file in cache_dir.glob("*.cache"):
                        cache_file.unlink()
                        deleted_count += 1
                
                # Очищаем память
                if pattern:
                    keys_to_delete = [k for k in self.local_cache.keys() if k.startswith(pattern.replace('*', ''))]
                    for key in keys_to_delete:
                        del self.local_cache[key]
                else:
                    self.local_cache.clear()
                    
            except Exception as e:
                print(f"⚠️ Ошибка очистки локального кеша: {e}")
        
        print(f"🧹 Очищено {deleted_count} записей кеша")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        📊 Получение статистики кеша
        """
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / max(1, total_requests)) * 100
        
        return {
            **self.cache_stats,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'redis_available': self.redis_client is not None,
            'local_cache_enabled': self.config.enable_local_cache,
            'compression_enabled': self.config.enable_compression
        }


# Глобальный экземпляр кеша
_global_cache = None


def get_result_cache(config: CacheConfig = None) -> ResultCache:
    """
    🏭 Фабрика для получения глобального экземпляра кеша
    """
    global _global_cache
    
    if _global_cache is None:
        _global_cache = ResultCache(config)
    
    return _global_cache