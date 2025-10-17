#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Юнит-тесты для умной нормализации имён контактов.

Тестирует функцию norm_contact_name_smart(), которая приводит имена
к стабильному формату "фамилия имя отчество" независимо от исходного порядка.
"""

import pytest


def norm_contact_name_smart(value: str | None) -> str | None:
    """
    🔧 Приводит имя к стабильному формату: фамилия имя отчество.
    
    Использует эвристики для определения порядка:
    - Если первое слово заканчивается на типичное окончание имени (а, я, ия),
      считаем его ИМЕНЕМ и переставляем назад.
    
    Args:
        value: Исходное имя в любом порядке
    
    Returns:
        Нормализованное имя в формате "фамилия имя отчество" или None
    
    Examples:
        >>> norm_contact_name_smart("Екатерина Кондратюк")
        "кондратюк екатерина"
        >>> norm_contact_name_smart("Кондратюк Екатерина")
        "кондратюк екатерина"
    """
    import re
    
    if not value:
        return None
    
    # Базовая очистка
    SPACE_RE = re.compile(r"\s+")
    name = value.strip().lower()
    
    # Если после strip пустая строка, возвращаем None
    if not name:
        return None
    
    name = name.replace(".", " ")
    name = SPACE_RE.sub(" ", name)
    
    parts = name.split()
    if len(parts) < 2:
        return name  # Только одно слово
    
    # Эвристика: определяем, что стоит первым — имя или фамилия
    first = parts[0]
    second = parts[1] if len(parts) > 1 else ""
    
    # === ЖЕНСКИЕ ФАМИЛИИ (высокая специфичность) ===
    # Эти окончания почти всегда указывают на фамилию
    female_surname_endings = ('ова', 'ева', 'ская', 'цкая', 'ских', 'цких', 'ына')
    
    # === МУЖСКИЕ ФАМИЛИИ (высокая специфичность) ===
    # Эти окончания почти всегда указывают на фамилию
    male_surname_endings = ('ов', 'ев', 'ин', 'ын', 'ский', 'цкий', 'ских', 'цких', 'ой', 'ый')
    
    # === ЖЕНСКИЕ ИМЕНА (окончания) ===
    # Имена обычно заканчиваются на гласные
    female_name_endings = ('а', 'я', 'ия', 'ья', 'на', 'ла', 'ра', 'та', 'да', 'га', 'ка', 'ма', 'са', 'ва')
    
    # === МУЖСКИЕ ИМЕНА (окончания) ===
    # Мужские имена часто заканчиваются на согласные или -й, -ь, -а
    # Примеры: Алексей, Сергей, Андрей, Дмитрий, Юрий, Игорь, Олег, Иван
    male_name_endings = ('ей', 'ай', 'ий', 'рий', 'ой', 'уй', 'ль', 'нь', 'рь', 'ть', 'дь', 'сь', 'ан', 'он', 'ен', 'ег', 'ур', 'им', 'ил', 'ам')
    
    # Проверяем первое слово
    if len(first) > 2:
        # 1. Проверяем, что это НЕ фамилия
        is_surname = (first.endswith(female_surname_endings) or 
                      first.endswith(male_surname_endings))
        
        # 2. Особый случай: -ина может быть и именем (Екатерина), и фамилией (Ильина)
        # Эвристика: длинные слова (>6 букв) на -ина скорее имена
        if first.endswith('ина'):
            if len(first) > 6:
                is_surname = False  # Екатерина, Кристина, Валентина
            else:
                is_surname = True   # Ильина, Нина (как фамилия)
        
        # 3. Особый случай: -ин может быть и именем (Мартин), и фамилией (Ильин)
        # Проверяем второе слово для контекста
        if first.endswith('ин') and len(first) <= 6:
            # Если второе слово — явная фамилия, то первое — имя
            if second and second.endswith(male_surname_endings + female_surname_endings):
                is_surname = False  # "Мартин Иванов" → Мартин = имя
        
        # 4. Особый случай: -ий может быть и именем (Дмитрий, Юрий), и фамилией (Белый)
        # Эвристика: если второе слово — явная фамилия, то первое — имя
        if first.endswith('ий'):
            if second and second.endswith(male_surname_endings + female_surname_endings):
                is_surname = False  # "Дмитрий Иванов" → Дмитрий = имя
            # Если второе слово НЕ фамилия, то первое скорее фамилия
            elif second and not second.endswith(male_surname_endings + female_surname_endings):
                is_surname = True   # "Белый Дмитрий" → Белый = фамилия
        
        # 5. Проверяем, что это похоже на имя
        is_name = ((first.endswith(female_name_endings) or 
                    first.endswith(male_name_endings)) 
                   and not is_surname)
        
        if is_name:
            # Вероятно, имя стоит первым → переставляем в конец
            if len(parts) == 2:
                # "екатерина кондратюк" → "кондратюк екатерина"
                parts = [parts[1], parts[0]]
            elif len(parts) == 3:
                # Проверяем второе слово (может быть отчество)
                second = parts[1]
                if len(second) > 3 and second.endswith(('вна', 'ична', 'вич', 'ьич')):
                    # "екатерина юрьевна кондратюк" → "кондратюк екатерина юрьевна"
                    parts = [parts[2], parts[0], parts[1]]
                else:
                    # "екатерина кондратюк юрьевна" → "кондратюк екатерина юрьевна"
                    parts = [parts[1], parts[0], parts[2]]
    
    return ' '.join(parts)


class TestNameNormalizationBasic:
    """Базовые тесты нормализации имён."""
    
    def test_empty_input(self):
        """Тест: пустой ввод возвращает None."""
        assert norm_contact_name_smart(None) is None
        assert norm_contact_name_smart("") is None
        assert norm_contact_name_smart("   ") is None
    
    def test_single_word(self):
        """Тест: одно слово возвращается как есть (lowercase)."""
        assert norm_contact_name_smart("Иванов") == "иванов"
        assert norm_contact_name_smart("ПЕТРОВ") == "петров"
    
    def test_already_correct_order(self):
        """Тест: фамилия уже стоит первой → порядок сохраняется."""
        assert norm_contact_name_smart("Иванов Иван") == "иванов иван"
        assert norm_contact_name_smart("Петров Пётр Петрович") == "петров пётр петрович"
        assert norm_contact_name_smart("Сидоров Сергей") == "сидоров сергей"


class TestNameNormalizationReordering:
    """Тесты переставления имени и фамилии."""
    
    def test_name_first_two_words(self):
        """Тест: имя стоит первым (2 слова) → переставляем."""
        # Женские имена
        assert norm_contact_name_smart("Екатерина Кондратюк") == "кондратюк екатерина"
        assert norm_contact_name_smart("Светлана Воронова") == "воронова светлана"
        assert norm_contact_name_smart("Ольга Иванова") == "иванова ольга"
        assert norm_contact_name_smart("Мария Петрова") == "петрова мария"
        
        # Мужские имена
        assert norm_contact_name_smart("Алексей Иванов") == "иванов алексей"
        assert norm_contact_name_smart("Сергей Петров") == "петров сергей"
        assert norm_contact_name_smart("Дмитрий Сидоров") == "сидоров дмитрий"
        assert norm_contact_name_smart("Игорь Козлов") == "козлов игорь"
    
    def test_name_first_three_words(self):
        """Тест: имя стоит первым (3 слова) → переставляем."""
        # Имя + Отчество + Фамилия → Фамилия + Имя + Отчество
        assert norm_contact_name_smart("Екатерина Юрьевна Кондратюк") == "кондратюк екатерина юрьевна"
        assert norm_contact_name_smart("Светлана Александровна Воронова") == "воронова светлана александровна"
    
    def test_patronymic_detection(self):
        """Тест: правильное определение отчества."""
        # Отчества с типичными окончаниями: -вна, -ична
        assert norm_contact_name_smart("Анна Ивановна Смирнова") == "смирнова анна ивановна"
        assert norm_contact_name_smart("Елена Петровна Козлова") == "козлова елена петровна"


class TestNameNormalizationEdgeCases:
    """Тесты граничных случаев."""
    
    def test_dots_in_name(self):
        """Тест: точки в инициалах удаляются."""
        assert norm_contact_name_smart("Иванов И.И.") == "иванов и и"
        assert norm_contact_name_smart("Петров П. П.") == "петров п п"
    
    def test_multiple_spaces(self):
        """Тест: множественные пробелы схлопываются."""
        assert norm_contact_name_smart("Иванов  Иван   Иванович") == "иванов иван иванович"
        assert norm_contact_name_smart("Екатерина    Кондратюк") == "кондратюк екатерина"
    
    def test_mixed_case(self):
        """Тест: смешанный регистр приводится к lowercase."""
        assert norm_contact_name_smart("ИВАНОВ Иван") == "иванов иван"
        assert norm_contact_name_smart("ПеТрОв ПёТр") == "петров пётр"
    
    def test_ambiguous_names(self):
        """Тест: неоднозначные случаи (может быть и имя, и фамилия)."""
        # "Ольга" может быть и именем, и фамилией
        # Эвристика считает её именем (окончание -га)
        assert norm_contact_name_smart("Ольга Петрова") == "петрова ольга"
        
        # Но если "Ольга" — фамилия, эвристика ошибётся
        # Это известное ограничение


class TestNameNormalizationRealWorld:
    """Тесты на реальных данных из писем."""
    
    def test_real_case_kondratyuk(self):
        """Тест: реальный случай Кондратюк Екатерина."""
        # Оба варианта должны дать одинаковый результат
        result1 = norm_contact_name_smart("Кондратюк Екатерина")
        result2 = norm_contact_name_smart("Екатерина Кондратюк")
        assert result1 == result2
        assert result1 == "кондратюк екатерина"
    
    def test_real_case_voronova(self):
        """Тест: реальный случай Воронова Светлана."""
        # "Воронова" — фамилия (окончание -ова), не переставляется
        result1 = norm_contact_name_smart("Воронова Светлана")
        assert result1 == "воронова светлана"
        
        # "Светлана" — имя, переставляется назад
        result2 = norm_contact_name_smart("Светлана Воронова")
        assert result2 == "воронова светлана"
        
        # Оба варианта дают одинаковый результат
        assert result1 == result2
    
    def test_real_case_kostyusheva(self):
        """Тест: реальный случай Костюшева Евгения."""
        # "Костюшева" — фамилия (окончание -ева), не переставляется
        result1 = norm_contact_name_smart("Костюшева Евгения")
        assert result1 == "костюшева евгения"
        
        # "Евгения" — имя, переставляется назад
        result2 = norm_contact_name_smart("Евгения Костюшева")
        assert result2 == "костюшева евгения"
        
        # Оба варианта дают одинаковый результат
        assert result1 == result2


class TestNameNormalizationStability:
    """Тесты стабильности нормализации."""
    
    def test_idempotency(self):
        """Тест: повторная нормализация даёт тот же результат."""
        name1 = "Екатерина Кондратюк"
        normalized1 = norm_contact_name_smart(name1)
        normalized2 = norm_contact_name_smart(normalized1)
        assert normalized1 == normalized2
    
    def test_consistency_across_variations(self):
        """Тест: разные вариации одного имени дают одинаковый результат."""
        # Фамилия первая — порядок сохраняется
        result1 = norm_contact_name_smart("Иванов Иван Иванович")
        assert result1 == "иванов иван иванович"
        
        # Имя первое — переставляется
        result2 = norm_contact_name_smart("Иван Иванович Иванов")
        assert result2 == "иванов иван иванович"
        
        # Оба варианта дают одинаковый результат
        assert result1 == result2


class TestNameNormalizationPerformance:
    """Тесты производительности."""
    
    def test_large_batch(self):
        """Тест: обработка большого количества имён."""
        names = [
            "Иванов Иван",
            "Екатерина Петрова",
            "Сидоров Сергей Сергеевич",
        ] * 100
        
        results = [norm_contact_name_smart(name) for name in names]
        assert len(results) == 300
        assert all(r is not None for r in results)


# Дополнительные тесты для покрытия >80%
class TestNameNormalizationCoverage:
    """Дополнительные тесты для увеличения покрытия."""
    
    def test_short_first_word(self):
        """Тест: короткое первое слово (<=3 символа) не переставляется."""
        # "Ли" — короткая фамилия, не должна переставляться
        assert norm_contact_name_smart("Ли Анна") == "ли анна"
    
    def test_name_ending_variations(self):
        """Тест: различные окончания имён."""
        # Окончания -а, -я, -ия, -ья, -на, -ла
        assert norm_contact_name_smart("Анна Иванова") == "иванова анна"
        assert norm_contact_name_smart("Мария Петрова") == "петрова мария"
        assert norm_contact_name_smart("Наталия Сидорова") == "сидорова наталия"
        assert norm_contact_name_smart("Дарья Козлова") == "козлова дарья"
        assert norm_contact_name_smart("Светлана Смирнова") == "смирнова светлана"
        assert norm_contact_name_smart("Алла Волкова") == "волкова алла"
    
    def test_no_reordering_needed(self):
        """Тест: фамилия не заканчивается на типичное окончание имени."""
        # Фамилия "Кузнецов" не заканчивается на -а/-я → порядок сохраняется
        assert norm_contact_name_smart("Кузнецов Алексей") == "кузнецов алексей"
        assert norm_contact_name_smart("Смирнов Дмитрий") == "смирнов дмитрий"
