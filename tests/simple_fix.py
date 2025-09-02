#!/usr/bin/env python3

"""
🔧 Скрипт для внесения точечных исправлений в advanced_email_fetcher_fixed.py
"""

import re

# Файл для исправления
input_file = 'src/advanced_email_fetcher_fixed.py'

# Чтение исходного файла
with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Обновление версии в комментариях
content = content.replace('Продвинутый IMAP-парсер v2.11', 'Продвинутый IMAP-парсер v2.12')
content = content.replace('🔥 Продвинутый парсер v2.11', '🔥 Продвинутый парсер v2.12')
content = content.replace('v2.11 - ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ БАГОВ', 'v2.12 - ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ БАГОВ')

# 2. Добавление расширения '.gif' в список EXCLUDED_EXTENSIONS
content = content.replace(
    "'.iso', '.img',  # Образы дисков\n}",
    "'.iso', '.img',  # Образы дисков\n    '.gif',  # GIF изображения\n}"
)

# 3. Добавление атрибута specific_excluded_files в __init__ метод
init_pattern = r'def __init__\(self, logger\):(.*?)# Счетчики для статистики'
replacement = lambda m: m.group(0).replace(
    "self.filters = EmailFilters(self.config_dir, self.logger)\n",
    """self.filters = EmailFilters(self.config_dir, self.logger)

        # 🔧 ИСПРАВЛЕНИЕ: список специфических исключаемых файлов
        self.specific_excluded_files = {
            "WRD0004.jpg",   # Мусорный файл Microsoft
            "_.jpg",         # Файл, состоящий из одного символа
            "blocked.gif",   # Мусорный GIF файл
            "image001.png",  # Мусорное изображение из подписи
            "image002.png"   # Мусорное изображение из подписи
        }
"""
)

content = re.sub(init_pattern, replacement, content, flags=re.DOTALL)

# 4. Добавление проверки specific_excluded_files в методе save_attachment_or_inline
attachment_pattern = r'# Декодируем имя файла\s+filename = self\.decode_header_value\(filename\)'
replacement = '''# Декодируем имя файла
            filename = self.decode_header_value(filename)
            
            # 🔧 ИСПРАВЛЕНИЕ: проверка специфических исключаемых файлов
            if filename in self.specific_excluded_files:
                self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО ИМЕНИ ФАЙЛА: {filename} - в списке специальных исключений")
                self.stats['excluded_filenames'] += 1
                return {
                    "original_filename": filename,
                    "status": "excluded_by_name",
                    "exclusion_reason": f"имя файла в списке исключений",
                    "is_inline": is_inline
                }'''

content = content.replace('# Декодируем имя файла\n            filename = self.decode_header_value(filename)', replacement)

# 5. Улучшение метода is_filename_excluded для улучшения проверки имен файлов
filename_pattern = r'def is_filename_excluded\(self, filename: str\)(.*?)def is_internal_mass_mailing'
replacement = '''def is_filename_excluded(self, filename: str) -> Optional[str]:
        """🚫 ИСПРАВЛЕННАЯ проверка имени файла с диагностикой"""
        if not filename or not self.filename_excludes:
            return None

        # ✅ ДОБАВИТЬ: диагностика для отладки
        self.logger.debug(f"🔍 Проверка файла '{filename}' против {len(self.filename_excludes)} паттернов")

        # 🔧 ИСПРАВЛЕНИЕ: проверка на одиночные символы и короткие имена
        if filename in ['_', '_', '__', '___', '____', '_____', '-', '--', '---', '----', '....', '----']:
            self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО КОРОТКОМУ ИМЕНИ: {filename}")
            return f"имя файла точно соответствует короткому исключению '{filename}'"
        
        # Оригинальный код с проверкой паттернов
        for exclude_pattern in self.filename_excludes:
            if '*' in exclude_pattern:
                # Wildcard паттерн
                if fnmatch.fnmatch(filename.lower(), exclude_pattern.lower()):
                    self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО ПАТТЕРНУ: {filename} → {exclude_pattern}")
                    return f"имя файла соответствует паттерну '{exclude_pattern}'"
            else:
                # Точное совпадение
                if filename.lower() == exclude_pattern.lower():  # Игнорируем регистр для точного совпадения
                    self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО ТОЧНОМУ ИМЕНИ: {filename}")
                    return f"имя файла точно соответствует '{exclude_pattern}'"

        # ✅ ДОБАВИТЬ: лог если фильтр не сработал
        self.logger.debug(f"✅ Файл '{filename}' прошел все фильтры имен")
        return None


    def is_internal_mass_mailing'''

content = re.sub(filename_pattern, replacement, content, flags=re.DOTALL)

# 6. Обновление описания исправлений в main
info_pattern = r'logger\.info\("🔧 ИСПРАВЛЕНЫ: черный список, decode_header_value, extract_raw_email"\)'
replacement = 'logger.info("🔧 ИСПРАВЛЕНЫ: черный список, decode_header_value, extract_raw_email, фильтрация GIF, специальные файлы")'
content = content.replace(info_pattern, replacement)

# 7. Добавление информации о новых исправлениях в финальный вывод
final_pattern = r'logger\.info\("   ✅ Убран дублированный код в process_single_email"\)'
replacement = '''logger.info("   ✅ Убран дублированный код в process_single_email")
            logger.info("   ✅ ИСПРАВЛЕНА фильтрация GIF файлов через EXCLUDED_EXTENSIONS")
            logger.info("   ✅ ИСПРАВЛЕНО исключение проблемных файлов через specific_excluded_files")'''
content = content.replace(final_pattern, replacement)

# Запись исправленного содержимого
with open(input_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Все исправления успешно внесены")
