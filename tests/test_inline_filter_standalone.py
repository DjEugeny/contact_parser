    def is_inline_image_excluded(self, filename: str, content_type: str, content_id: str = None) -> str:
        """🆕 Проверка inline изображения на исключение"""
        if not filename:
            return None

        filename_lower = filename.lower()

        # Проверяем Content-ID (характерно для встроенных изображений)
        if content_id:
            return f"изображение с Content-ID: {content_id}"

        # Проверяем на очень короткие имена файлов
        if len(filename) <= 3:
            return f"слишком короткое имя файла: {filename}"

        # Проверяем на случайные имена (только буквы и цифры, без пробелов и точек)
        if re.match(r'^[a-zA-Z0-9]+$', filename):
            # Исключаем, если длина больше 8 символов (вероятно случайное имя)
            if len(filename) > 8:
                return f"вероятно случайное имя файла: {filename}"

        # Проверяем паттерны мусорных inline изображений
        for pattern in self.inline_exclusion_patterns:
            if re.match(pattern, filename_lower, re.IGNORECASE):
                return f"соответствует паттерну исключения: {pattern}"

        return None