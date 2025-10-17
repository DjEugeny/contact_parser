#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 Repository для работы с таблицей contact_mentions.

Хранит упоминания контактов без способов связи (email/телефон),
отфильтрованных на этапе постобработки (GID v2, Этап 1).

Author: Cascade AI
Created: 2025-10-17
"""

import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_URL = os.getenv("DB_URL", "sqlite:///./crm.db")


def _resolve_db_path(db_url: Optional[str]) -> Path:
    """Преобразует DB URL в путь к файлу."""
    if not db_url:
        db_url = DEFAULT_DB_URL

    if db_url.startswith("sqlite:///"):
        raw_path = db_url[len("sqlite:///"):]
        if raw_path == ":memory:":
            return Path(raw_path)
        return Path(raw_path).expanduser().resolve()
    if db_url.startswith("sqlite://"):
        raw_path = db_url[len("sqlite://"):]
        if raw_path == ":memory:":
            return Path(raw_path)
        return Path(raw_path).expanduser().resolve()
    return Path(db_url).expanduser().resolve()


@dataclass
class ContactMention:
    """Упоминание контакта без способов связи."""
    id: Optional[int]
    name: str
    position: Optional[str]
    organization_id: Optional[int]
    interaction_id: Optional[int]
    mention_type: Optional[str]
    role_in_message: Optional[str]
    confidence: Optional[float]
    source_file: Optional[str]
    source_context: Optional[str]
    created_at: Optional[str]


class ContactMentionsRepository:
    """
    🗄️ SQLite-backed repository для упоминаний контактов.
    
    Используется для сохранения контактов без способов связи,
    отфильтрованных на этапе постобработки.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Инициализация репозитория.
        
        Args:
            db_url: URL базы данных (по умолчанию из DB_URL env)
        """
        self.db_path = _resolve_db_path(db_url)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        logger.info(f"📂 ContactMentionsRepository initialized: {self.db_path}")

    # ------------------------------------------------------------------
    # Connectivity helpers
    # ------------------------------------------------------------------
    def _get_connection(self) -> sqlite3.Connection:
        """Создаёт подключение к БД с настройками."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _ensure_schema(self) -> None:
        """Создаёт таблицу contact_mentions, если её нет."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS contact_mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    position TEXT,
                    organization_id INTEGER,
                    interaction_id INTEGER,
                    mention_type TEXT,
                    role_in_message TEXT,
                    confidence REAL,
                    source_file TEXT,
                    source_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_contact_mentions_name 
                ON contact_mentions(name);

                CREATE INDEX IF NOT EXISTS idx_contact_mentions_org 
                ON contact_mentions(organization_id);

                CREATE INDEX IF NOT EXISTS idx_contact_mentions_interaction 
                ON contact_mentions(interaction_id);

                CREATE INDEX IF NOT EXISTS idx_contact_mentions_type 
                ON contact_mentions(mention_type);

                CREATE INDEX IF NOT EXISTS idx_contact_mentions_created 
                ON contact_mentions(created_at);

                CREATE INDEX IF NOT EXISTS idx_contact_mentions_dedup 
                ON contact_mentions(name, organization_id, interaction_id);
                """
            )

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------
    def save_contact_mentions(
        self,
        mentions: List[Dict[str, Any]],
        interaction_id: Optional[int] = None,
        source_file: Optional[str] = None,
    ) -> int:
        """
        💾 Сохраняет упоминания контактов без способов связи.
        
        Args:
            mentions: Список упоминаний контактов
            interaction_id: ID взаимодействия (письма)
            source_file: Имя файла-источника
            
        Returns:
            Количество сохранённых записей
            
        Examples:
            >>> repo = ContactMentionsRepository()
            >>> mentions = [
            ...     {
            ...         "name": "Иванов Иван",
            ...         "position": "Директор",
            ...         "organization_id": 1,
            ...         "role_in_message": "mentioned",
            ...         "confidence": 0.85
            ...     }
            ... ]
            >>> count = repo.save_contact_mentions(mentions, interaction_id=42)
            >>> print(f"Saved {count} mentions")
        """
        if not mentions:
            logger.debug("📭 No mentions to save")
            return 0

        saved_count = 0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for mention in mentions:
                try:
                    # Извлекаем данные из mention
                    name = mention.get("name")
                    if not name:
                        logger.warning("⚠️ Skipping mention without name")
                        continue
                    
                    position = mention.get("position")
                    organization_id = mention.get("organization_id")
                    mention_type = mention.get("mention_type")
                    role_in_message = mention.get("role_in_message")
                    confidence = mention.get("confidence")
                    city = mention.get("city")
                    address = mention.get("address")
                    
                    # Формируем контекст упоминания
                    source_context_parts = []
                    if position:
                        source_context_parts.append(f"Должность: {position}")
                    if city:
                        source_context_parts.append(f"Город: {city}")
                    if address:
                        source_context_parts.append(f"Адрес: {address}")
                    source_context = "; ".join(source_context_parts) if source_context_parts else None
                    
                    # Вставляем запись
                    cursor.execute(
                        """
                        INSERT INTO contact_mentions (
                            name, position, organization_id, interaction_id,
                            mention_type, role_in_message, confidence,
                            source_file, source_context
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            name,
                            position,
                            organization_id,
                            interaction_id,
                            mention_type,
                            role_in_message,
                            confidence,
                            source_file,
                            source_context,
                        ),
                    )
                    saved_count += 1
                    
                    logger.debug(
                        f"✅ Saved mention: {name} "
                        f"(org_id={organization_id}, interaction_id={interaction_id})"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Failed to save mention {mention.get('name')}: {e}")
                    continue
            
            conn.commit()
        
        if saved_count > 0:
            logger.info(f"💾 Saved {saved_count} contact mentions to database")
        
        return saved_count

    def get_mentions_by_interaction(self, interaction_id: int) -> List[ContactMention]:
        """
        🔍 Получает все упоминания для конкретного взаимодействия.
        
        Args:
            interaction_id: ID взаимодействия
            
        Returns:
            Список упоминаний контактов
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM contact_mentions
                WHERE interaction_id = ?
                ORDER BY created_at DESC
                """,
                (interaction_id,),
            )
            rows = cursor.fetchall()
            
            return [
                ContactMention(
                    id=row["id"],
                    name=row["name"],
                    position=row["position"],
                    organization_id=row["organization_id"],
                    interaction_id=row["interaction_id"],
                    mention_type=row["mention_type"],
                    role_in_message=row["role_in_message"],
                    confidence=row["confidence"],
                    source_file=row["source_file"],
                    source_context=row["source_context"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_mentions_by_organization(self, organization_id: int) -> List[ContactMention]:
        """
        🔍 Получает все упоминания для конкретной организации.
        
        Args:
            organization_id: ID организации
            
        Returns:
            Список упоминаний контактов
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM contact_mentions
                WHERE organization_id = ?
                ORDER BY created_at DESC
                """,
                (organization_id,),
            )
            rows = cursor.fetchall()
            
            return [
                ContactMention(
                    id=row["id"],
                    name=row["name"],
                    position=row["position"],
                    organization_id=row["organization_id"],
                    interaction_id=row["interaction_id"],
                    mention_type=row["mention_type"],
                    role_in_message=row["role_in_message"],
                    confidence=row["confidence"],
                    source_file=row["source_file"],
                    source_context=row["source_context"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def search_mentions_by_name(self, name_pattern: str) -> List[ContactMention]:
        """
        🔍 Поиск упоминаний по имени (LIKE).
        
        Args:
            name_pattern: Паттерн для поиска (например, "%Иванов%")
            
        Returns:
            Список упоминаний контактов
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM contact_mentions
                WHERE name LIKE ?
                ORDER BY created_at DESC
                """,
                (name_pattern,),
            )
            rows = cursor.fetchall()
            
            return [
                ContactMention(
                    id=row["id"],
                    name=row["name"],
                    position=row["position"],
                    organization_id=row["organization_id"],
                    interaction_id=row["interaction_id"],
                    mention_type=row["mention_type"],
                    role_in_message=row["role_in_message"],
                    confidence=row["confidence"],
                    source_file=row["source_file"],
                    source_context=row["source_context"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        📊 Получает статистику по упоминаниям.
        
        Returns:
            Словарь со статистикой
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Общее количество
            cursor.execute("SELECT COUNT(*) as total FROM contact_mentions")
            total = cursor.fetchone()["total"]
            
            # По типам упоминаний
            cursor.execute(
                """
                SELECT mention_type, COUNT(*) as count
                FROM contact_mentions
                GROUP BY mention_type
                ORDER BY count DESC
                """
            )
            by_type = {row["mention_type"]: row["count"] for row in cursor.fetchall()}
            
            # По организациям (топ-10)
            cursor.execute(
                """
                SELECT organization_id, COUNT(*) as count
                FROM contact_mentions
                WHERE organization_id IS NOT NULL
                GROUP BY organization_id
                ORDER BY count DESC
                LIMIT 10
                """
            )
            by_org = {row["organization_id"]: row["count"] for row in cursor.fetchall()}
            
            return {
                "total_mentions": total,
                "by_mention_type": by_type,
                "top_organizations": by_org,
            }

    def delete_mentions_by_interaction(self, interaction_id: int) -> int:
        """
        🗑️ Удаляет все упоминания для конкретного взаимодействия.
        
        Args:
            interaction_id: ID взаимодействия
            
        Returns:
            Количество удалённых записей
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM contact_mentions WHERE interaction_id = ?",
                (interaction_id,),
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️ Deleted {deleted_count} mentions for interaction {interaction_id}")
            
            return deleted_count
