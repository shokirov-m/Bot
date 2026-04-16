#!/usr/bin/env python3
"""
Генерация PDF-руководства по игре «Башня Испытаний» (tower_bot).
Запуск из каталога tower_bot: python scripts/generate_game_manual_pdf.py
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _find_unicode_font() -> str:
    system = platform.system()
    if system == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        for name in ("arial.ttf", "Arial.ttf", "segoeui.ttf", "SegoeUI.ttf"):
            p = Path(windir) / "Fonts" / name
            if p.is_file():
                return str(p)
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ):
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(
        "Не найден TTF со кириллицей (Arial/Segoe на Windows или DejaVu на Linux).",
    )


def _build_story(font_name: str) -> list:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleRu",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=20,
        leading=26,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    h1 = ParagraphStyle(
        "H1Ru",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceBefore=14,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "H2Ru",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "BodyRu",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
    )
    small = ParagraphStyle(
        "SmallRu",
        parent=body,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#333333"),
    )

    def p(text: str, style=body) -> Paragraph:
        # ReportLab XML: экранирование
        esc = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return Paragraph(esc.replace("\n", "<br/>"), style)

    story: list = []

    story.append(p("Башня Испытаний", title))
    story.append(p("Telegram-бот tower_bot: описание игры, механики и оформление", small))
    story.append(Spacer(1, 0.4 * cm))

    story.append(p("1. Общее описание", h1))
    story.append(
        p(
            "Это пошаговая RPG в формате чат-бота: игрок поднимается по башне из 100 этажей, "
            "сражается с монстрами, получает золото и опыт, открывает классы, титулы, "
            "города и дополнительные системы прогрессии. Весь интерфейс строится на сообщениях "
            "Telegram с HTML-разметкой (жирный текст, курсив, ссылки) и inline-кнопках.",
        ),
    )
    story.append(Spacer(1, 0.2 * cm))

    story.append(p("2. Оформление и UI", h1))
    story.append(
        p(
            "<b>Текст.</b> Подписи к полоскам здоровья и маны, разделители секций и числа "
            "форматируются утилитами проекта. Разделитель секций в чате — линия из дефисов "
            "(ASCII), чтобы корректно отображаться на всех устройствах.<br/>"
            "<b>Полоски HP/MP.</b> Визуально: блоки █ и ░, пороги цветовых подсказок "
            "(красный/оранжевый при низком HP).<br/>"
            "<b>Эмодзи.</b> Используются для зон, монстров, кнопок меню и боевых тегов "
            "(элита, мини-босс, босс).<br/>"
            "<b>Кнопки.</b> Главное меню, этаж, бой, инвентарь, ежедневка, арена и др. — "
            "через callback_data; игровой экран по возможности обновляется редактированием "
            "одного сообщения.",
        ),
    )

    story.append(p("3. Персонаж и ресурсы", h1))
    story.append(
        p(
            "<b>Статы:</b> сила, ловкость, интеллект, выносливость, удача — влияют на урон, "
            "защиту, ману, HP, уклонение и др.<br/>"
            "<b>Уровень и опыт:</b> начисляется за победы и активности; при повышении уровня "
            "выдаются очки статов.<br/>"
            "<b>HP и MP:</b> текущие и максимальные значения; в бою отображаются полосками.<br/>"
            "<b>Стамина:</b> обычный бой тратит 1 единицу; лимит и скорость восстановления "
            "задаются настройками бота (интервал регенерации по времени).<br/>"
            "<b>Золото и руны:</b> валюта и ресурс для эндгейм-механик (заточки, руны и т.д.).",
        ),
    )

    story.append(p("4. Старт, классы и ветвление", h1))
    story.append(
        p(
            "Новый игрок создаёт героя-<b>странника</b> (универсальный класс). "
            "С <b>10 уровня</b> на <b>11 этаже</b> у наставника открывается выбор <b>базового класса</b> "
            "(статы сдвигаются в плюс и в минус от шаблона); "
            "на <b>57 этаже</b> — выбор <b>подкласса</b> с усилением характеристик. "
            "У каждого класса свой набор из трёх навыков в бою (стоимость MP, перезарядка, эффекты).",
        ),
    )

    story.append(p("5. Башня: этажи и зоны", h1))
    story.append(
        p(
            "Всего <b>100 этажей</b>. Этажи сгруппированы в тематические зоны; у каждой зоны "
            "своё имя, эмодзи и краткое описание. На каждом этаже дополнительно показывается "
            "<b>«комната»</b> — короткий эпитет из фиксированного набора, циклически по номеру этажа, "
            "чтобы локации не повторялись монотонно.",
        ),
    )

    zones_data = [
        ("1–10", "Лес Начал", "Нижние кольца, простые противники."),
        ("11–20", "Гнилые Болота", "Туман, нежить, слизи."),
        ("21–30", "Пещеры Теней", "Тени и твари тьмы."),
        ("31–40", "Ледяные Пики", "Мороз и големы."),
        ("41–50", "Пустыня Забвения", "Жар и пески."),
        ("51–60", "Вулканические Руины", "Лава и огненные угрозы."),
        ("61–70", "Небесная Крепость", "Вихри, грифоны, хаос."),
        ("71–80", "Бездна Хаоса", "Демоны и искажения."),
        ("81–99", "Зал Вечности", "Поздний контент, сильные враги."),
        ("100", "Страж Башни (финал)", "Финальное испытание, особая зона."),
    ]
    t = Table(
        [["Этажи", "Зона", "Тема"]] + [list(row) for row in zones_data],
        colWidths=[2.2 * cm, 4.5 * cm, 9.8 * cm],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
            ],
        ),
    )
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))

    story.append(p("6. Города и сервисы на этаже", h1))
    story.append(
        p(
            "<b>Города-хабы</b> на этажах <b>31, 61 и 91</b>: безопасные зоны с кузницей, таверной, "
            "лавкой и поручениями стражи.<br/>"
            "<b>Торговец (лавка)</b> — на каждом этаже, номер которого кратен <b>5</b>.<br/>"
            "<b>Квестовый NPC («Странник»)</b> — на этажах, номер которых кратен <b>3</b>.<br/>"
            "<b>Мини-босс</b> — на этажах ×5, но не на ×10.<br/>"
            "<b>Сильный босс</b> — на этажах ×10 и на финале.<br/>"
            "Обычное прохождение: нужно победить <b>все цели</b> на текущем этаже, после чего "
            "открывается следующий этаж и расширяется свободная навигация ⬆️/⬇️ по уже достигнутым уровням.",
        ),
    )

    story.append(p("7. Особый сценарий — «длинный этаж» (пилот)", h1))
    story.append(
        p(
            "На <b>этаже 15</b> доступен отдельный сценарий <b>long_floor_v1</b>: фазы "
            "<b>ключи → две волны боёв → NPC → босс</b>. Пока сценарий не завершён, обычный список "
            "целей этажа скрыт; <b>номер этажа не меняется</b> до победы над боссом сценария, "
            "после чего действует обычная логика подъёма. Прогресс хранится в meta_progress персонажа.",
        ),
    )

    story.append(p("8. Тайник", h1))
    story.append(
        p(
            "Кнопка поиска тайника на экране этажа: один бросок за «заход» на этаж (после боя можно снова). "
            "Базовый шанс успеха — <b>15%</b>. При удаче — золото, опыт, иногда предмет в сумку; "
            "при неудаче — короткий флавор-текст.",
        ),
    )

    story.append(p("9. Бой", h1))
    story.append(
        p(
            "<b>Пошаговость:</b> ход игрока (атака, навыки, предмет из сумки, побег), затем ход монстра.<br/>"
            "<b>Автоатака</b> учитывает атаку оружия (или голыми руками), статы, пассивы класса, "
            "звания башни, глобальные пассивы и <b>мастерство оружия</b> по типу оружия.<br/>"
            "<b>Навыки</b> тратят MP и имеют перезарядку; эффекты зависят от класса (лечение, блок, "
            "уклонение, щиты, урон и т.д.).<br/>"
            "<b>Монстры</b> имеют шаблоны с элементами, фразами-провокациями, режимами AI; у боссов возможны "
            "фазы и усиления.<br/>"
            "<b>Побег</b> — шанс от ловкости; в учебном бою недоступен.<br/>"
            "<b>Поражение:</b> потеря предмета из сумки, шанс снижения заточки оружия, частичное восстановление "
            "HP/MP, сброс к началу текущего этажа (логика смерти в сервисе боя).",
        ),
    )

    story.append(p("10. Звание башни, титулы и учебный бой", h1))
    story.append(
        p(
            "<b>Звание башни</b> (path ranks) — отдельно от <b>титулов</b>: выдаётся по итогам "
            "<b>учебного боя</b> на 1 этаже (два раунда против манекенов). От звания зависят бонусы к статам "
            "и отдельный пассив, суммирующийся с классом и глобальными бонусами.<br/>"
            "<b>Титулы</b> открываются за достижения, отображаются в профиле и могут давать бонусы к наградам; "
            "активный титул выбирается игроком в разделе «Титулы».",
        ),
    )

    story.append(p("11. Ежедневка и канал", h1))
    story.append(
        p(
            "За <b>3 победы в боях за календарный день (UTC)</b> можно забрать награду; ведётся <b>стрик</b> "
            "дней с наградой подряд. Для получения награды требуется подписка на канал, задаваемый "
            "настройкой <b>REQUIRED_CHANNEL_USERNAME</b>; для разработки возможен флаг "
            "<b>SKIP_CHANNEL_SUBSCRIPTION_CHECK</b>. Интерфейс ежедневки и главного хаба поддерживает "
            "локализацию ru/en.",
        ),
    )

    story.append(p("12. Прочие режимы", h1))
    story.append(
        p(
            "<b>Арена теней</b> — дуэль против «тени» другого игрока или башни по реальному билду из базы.<br/>"
            "<b>Топ игроков</b> — таблицы по разным метрикам.<br/>"
            "<b>Инвентарь</b> — экипировка, сумка, использование расходников.<br/>"
            "<b>Кузница / таверна</b> — в городах: улучшение снаряжения, отдых с таймером восстановления HP/MP.",
        ),
    )

    story.append(p("13. Технические заметки", h1))
    story.append(
        p(
            "Данные персонажа и прогресс хранятся в SQLite; FSM боя может использовать Redis при настройке. "
            "Античит и сезонные параметры включаются конфигом. Документ сгенерирован автоматически по структуре "
            "репозитория tower_bot и отражает реализованные на момент сборки механики.",
        ),
    )

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        p(
            "Исходный код и актуальные формулы — в каталоге tower_bot (game/, services/, bot/).",
            small,
        ),
    )

    return story


def main() -> int:
    root = _root_dir()
    out_dir = root / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Башня_Испытаний_описание_игры.pdf"

    font_path = _find_unicode_font()
    font_name = "GameManualFont"
    pdfmetrics.registerFont(TTFont(font_name, font_path))

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Башня Испытаний — описание игры",
        author="tower_bot",
    )
    doc.build(_build_story(font_name))
    print(f"OK: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
