"""Короткие строки интерфейса (только русский)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from db.models.character import Character

LOCALE_KEY = "locale"  # устарело: интерфейс только на русском, ключ не используется

STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "menu_profile": "🗡️ Статус",
        "profile_skills_btn": "⚔️ Навыки",
        "profile_spec_btn": "🎭 Специализация",
        "profile_spec_intro": (
            "<i>Титулы, архетипы и боевые навыки — выбери раздел ниже.</i>"
        ),
        "profile_ranker_name_badge": "🏅 Ранкер ",
        "skills_screen_title": "⚔️ <b>Боевые навыки</b>",
        "skills_slot_btn": "Слот {n}",
        "skills_equip_hint": (
            "<i>В бою доступны только <b>три</b> выбранных навыка. Магия тянется от ИНТ, удары — от СИЛ.</i>"
        ),
        "profile_back_compact": "⬅️ К статусу",
        "profile_class_btn": "📜 Класс",
        "profile_class_screen_title": "📜 <b>Класс героя</b>",
        "profile_rest_btn_start": "🛏️ Передышка (1 мин)",
        "profile_rest_btn_wait": "🛏️ ~{sec} с до полного HP/MP",
        "rest_complete_notify": (
            "🛏️ <b>Передышка окончена.</b> HP и MP восстановлены до максимума. "
            "Открой /profile, если карточка ещё не обновилась."
        ),
        "menu_home": "🏠 Дом",
        "menu_workshop": "🔧 Мастерская",
        "menu_lavka": "🏪 Лавка",
        "menu_floor": "🗺️ Этаж",
        "menu_inv": "🎒 Инвентарь",
        "menu_titles": "🏆 Титулы",
        "menu_top": "📊 Топ игроков",
        "menu_city": "🏙️ Город",
        "menu_portal": "🌀 Портал",
        "menu_city_unavailable": "Город только на городских этажах. Открой этаж с хабом или спустись к нему.",
        "portal_intro": (
            "🌀 <b>Портал</b>\n"
            "Мгновенный переход на <b>важные этажи</b> башни (список можно расширить в настройках игры).\n"
            "Сейчас: <b>{floors}</b>.\n"
            "<i>Нужен открытый маршрут: твой «максимум этажа» ≥ цели. Город по-прежнему с кнопки "
            "«Город» на карте этажа, если ты уже на городском ярусе.</i>"
        ),
        "portal_btn_floor": "{n}",
        "portal_btn_floor_locked": "🔒 {n}",
        "portal_locked_alert": "Этаж {n} ещё не открыт — поднимись выше в башне.",
        "portal_same_floor": "Ты уже на этом этаже.",
        "portal_back_menu": "📋 В меню",
        "menu_daily": "📅 Ежедневка",
        "menu_arena": "⚔️ Арена",
        "menu_coliseum": "🏛️ Колизей",
        "menu_locations": "🗺 Локации",
        "menu_locations_intro": (
            "🗺 <b>Локации</b>\n\n"
            "<i>Арена PvP, Колизей PvE, ремесло, торговля и клан.</i>"
        ),
        "menu_sticker_btn": "🎴 Стикер-арена",
        "sticker_arena_title": "🎴 <b>Стикер-арена</b>",
        "sticker_arena_subtitle": (
            "<i>Виртуальная коллекция и дуэли по ATK/DEF и стихии (огонь / вода / земля).</i>"
        ),
        "sticker_arena_free_left": "Бесплатных круток сегодня осталось: <b>{n}</b>.",
        "sticker_arena_paid_left": "Платных круток сегодня осталось: <b>{n}</b> (по {gold} 💰).",
        "sticker_arena_stars_line": "Крутка за звёзды: <b>{stars}</b> ⭐ (из дневного лимита платных).",
        "sticker_arena_pack_link": '<a href="https://t.me/addstickers/{pack}">Добавить набор в Telegram</a>',
        "sticker_kb_free": "🎰 Бесплатная крутка",
        "sticker_kb_gold": "💰 Крутка за {gold} золота",
        "sticker_kb_stars": "⭐ Крутка за {stars} звёзд",
        "sticker_kb_album": "📦 Альбом",
        "sticker_kb_top": "🏆 ТОП дуэлей",
        "sticker_kb_duel": "⚔️ Вызвать на дуэль",
        "sticker_kb_back_loc": "⬅ В локации",
        "sticker_kb_cancel": "⬅ Отмена",
        "sticker_unlock_alert": "Откроется с {level} ур.",
        "sticker_duel_start_prompt": (
            "⚔️ <b>Дуэль</b>\nВыбери карту, затем укажи соперника: "
            "<b>ответом на его сообщение</b>, <b>@username</b> или <b>число</b> (игровой или Telegram ID из профиля)."
        ),
        "sticker_duel_enter_target": (
            "Введи <b>@ник</b>, число (игровой или Telegram ID) или ответь реплаем на сообщение соперника:"
        ),
        "sticker_duel_need_target": "Нужен соперник: реплай, @ник или число.",
        "sticker_combat_busy": "Сначала заверши бой.",
        "sticker_no_stickers_for_duel": "Сначала получи стикеры в гаче.",
        "sticker_duel_invalid_card": "Нет такой карты.",
        "sticker_duel_pick_card_hint": "Теперь укажи соперника.",
        "sticker_duel_session_reset": "Сессия сброшена. Начни снова из меню Стикер-арена.",
        "sticker_duel_waiting": "<i>Ожидаем ответ соперника.</i>",
        "sticker_challenged_notify": (
            "⚔️ Тебя вызвали на <b>стикер-дуэль</b>!\n"
            "Код: <code>{code}</code>\n"
            "Введи: <code>/duel_accept {code}</code>"
        ),
        "sticker_spin_free_ok": "Выпало!",
        "sticker_spin_paid_ok": "Куплено!",
        "sticker_stars_disabled": "Крутка за звёзды отключена.",
        "sticker_invoice_title": "Стикер-гача",
        "sticker_invoice_desc": "Дополнительная крутка (из дневного лимита платных круток).",
        "sticker_invoice_label": "Крутка стикер-гачи",
        "sticker_top_title": "🏆 <b>ТОП-10 стикер-дуэлянтов</b>",
        "sticker_top_line": "{i}. {who} — <b>{rating}</b> ({wins} побед)",
        "sticker_top_self": "<i>Твой рейтинг: <b>{rating}</b> (место #{place})</i>",
        "sticker_duel_accept_usage": "Использование: <code>/duel_accept КОД</code>",
        "sticker_duel_no_cards_defend": "У тебя нет стикеров для ответа.",
        "sticker_duel_pick_defender": "Код вызова: <code>{code}</code>\nВыбери карту для боя:",
        "sticker_challenge_not_found": "Код не найден или устарел.",
        "menu_quests": "📋 Задания",
        "menu_settings": "⚙️ Настройки",
        "menu_auction": "🛒 Магазин",
        "settings_title": "⚙️ <b>Настройки</b>",
        "settings_intro": "Имя героя, промокоды, реферальная ссылка, язык и подсказки.",
        "settings_rename_btn": "✏️ Сменить имя",
        "settings_promo_btn": "🎁 Промокод",
        "settings_referral_btn": "👥 Пригласить друга",
        "settings_referral_title": "👥 <b>Реферальная программа</b>",
        "settings_referral_body": (
            "Отправь другу ссылку ниже. Если он <b>впервые</b> зайдёт в бота по ней и "
            "создаст героя, а потом <b>достигнет 2 уровня</b>, ты получишь:\n"
            "• <b>2</b> предмета экипировки <b>редкой</b> редкости в сумку\n"
            "• <b>+200</b> опыта на твоего героя\n\n"
            "Если по твоей ссылке зарегистрируется <b>пять разных</b> игроков и у каждого герой "
            "достигнет <b>3 уровня</b>, ты получишь <b>эпическое ожерелье</b> (амулет) в сумку "
            "и <b>+5</b> свободных очков характеристик (нужна свободная ячейка в сумке).\n\n"
            "<b>Твоя ссылка:</b>\n<code>{link}</code>"
        ),
        "settings_referral_no_username": "У бота нет username в Telegram — задай имя в @BotFather, чтобы ссылка работала.",
        "settings_my_id_btn": "🆔 Мой Telegram ID",
        "settings_tips_btn": "💡 Подсказки",
        "settings_images_disable": "🖼 Выключить фото этажа и портрет",
        "settings_images_enable": "🖼 Включить фото этажа и портрет",
        "settings_golden_goblin_notify_disable": "💰 Отключить оповещения о золотом гоблине",
        "settings_golden_goblin_notify_enable": "💰 Включить оповещения о золотом гоблине",
        "settings_reset_btn": "🗑️ Сбросить весь прогресс",
        "settings_reset_warn": (
            "⚠️ <b>Сбросить весь прогресс?</b>\n\n"
            "Обнулятся этаж, инвентарь, квесты, золото, опыт, подкласс, титул и прочий прогресс в JSON. "
            "Останутся <b>имя героя</b> и <b>класс</b> (статы класса с начала).\n\n"
            "<i>Действие необратимо.</i>"
        ),
        "settings_reset_yes": "⚠️ Да, сбросить всё",
        "settings_reset_no": "⬅ Назад",
        "settings_reset_done": (
            "✅ <b>Прогресс сброшен.</b> Ты на 1 этаже со стартовой экипировкой и хлебом, как после регистрации. "
            "Имя и класс не менялись — можно сразу идти на этаж."
        ),
        "settings_stat_reset_btn": "📊 Сброс распределения статов",
        "settings_stat_reset_warn": (
            "<b>Сброс вложенных очков характеристик</b>\n\n"
            "Стоимость: <b>{gold}</b> 💰. Не чаще <b>одного раза в календарный день (UTC)</b>.\n"
            "Очки, вложенные через /stats сверх базы класса, вернутся в <b>свободные</b>; "
            "статы станут как у класса (с учётом подкласса ×2, если он есть).\n\n"
            "Сейчас можно вернуть: <b>{points}</b> оч.\n\n"
            "<i>Бонусы экипировки и титула не сбрасываются.</i>"
        ),
        "settings_stat_reset_yes": "✅ Сбросить за {gold} 💰",
        "settings_stat_reset_no": "⬅ Отмена",
        "settings_stat_reset_done": (
            "✅ <b>Сброс выполнен.</b> Возвращено <b>{points}</b> свободных очков. "
            "Списано <b>{gold}</b> 💰. Распредели заново через /stats."
        ),
        "settings_stat_reset_today": "Сброс статов уже использован сегодня (UTC). Завтра снова.",
        "settings_stat_reset_none": "Нет вложенных очков — нечего сбрасывать (команда /stats).",
        "settings_stat_reset_no_gold": "Недостаточно золота. Нужно <b>{gold}</b> 💰.",
        "settings_back_menu": "📋 В меню",
        "settings_rename_intro": "Стоимость смены имени: <b>{gold}</b> 💰. Напиши новое имя <b>одним сообщением</b> (2–32 символа, буквы и цифры).",
        "settings_rename_done": "✅ Имя изменено на: <b>{name}</b>\nСписано <b>{gold}</b> 💰.",
        "settings_rename_no_gold": "Недостаточно золота. Нужно <b>{gold}</b> 💰.",
        "settings_promo_prompt": "Введи промокод <b>одним сообщением</b> (латиница и цифры).",
        "settings_promo_ok": "🎁 Промокод принят!\n+{gold} 💰 · +{xp} опыта.{rune_part}{level_part}{items_part}{pet_part}",
        "settings_promo_rune": "\n⚗️ +{rune} рунных камней",
        "settings_promo_levels": "\n📈 Новых уровней: <b>{n}</b>",
        "settings_promo_items": "\n🎒 В сумку: <b>{items}</b>",
        "settings_promo_pet_new": "\n🐾 Питомец добавлен: <b>{name}</b> (смотри статус → «Питомец»).",
        "settings_promo_pet_dup": "\n🐾 Питомец <b>{name}</b> уже был — повторно не выдаётся; остальные награды начислены.",
        "settings_promo_bag_full": "В сумке нет двух свободных ячеек — освободи место и введи код снова.",
        "settings_promo_bad_format": "Неверный формат кода.",
        "settings_promo_unknown": "Такого промокода нет или он отключён.",
        "settings_promo_used": "Этот промокод уже активирован на твоём аккаунте.",
        "settings_promo_expired": "Срок действия промокода истёк.",
        "settings_promo_exhausted": "Лимит активаций этого промокода исчерпан.",
        "settings_promo_disabled": "Промокод отключён администратором.",
        "settings_promo_not_started": "Промокод ещё не активен.",
        "settings_name_short": "Имя слишком короткое (минимум 2 символа).",
        "settings_name_long": "Имя слишком длинное (максимум 32 символа).",
        "settings_name_chars": "Допустимы буквы (кириллица и латиница), цифры, пробел, дефис, точка посередине.",
        "settings_cancel_btn": "✖️ Отмена",
        "settings_fsm_cancelled": "Отменено.",
        "settings_my_id": "Твой <b>Telegram ID</b>:\n<code>{tid}</code>\n\n<i>Для вызова на арене используй <b>игровой ID</b> из раздела «Статус».</i>",
        "settings_tips_body": (
            "💡 <b>Подсказки</b>\n"
            "• Стамина тратится на бои на этаже; восстанавливается со временем.\n"
            "• Ежедневка — после побед и подписки на канал.\n"
            "• Арена: вызов по <b>игровому ID</b> из статуса — <code>/arena 5</code>; случайный поединок — кнопка в разделе «Арена».\n"
            "• Промокод каждый можно ввести только один раз."
        ),
        "settings_combat_block": "Сначала заверши бой.",
        "menu_hub_title": "🏰 <b>Башня</b> — выбери раздел:",
        "welcome_back": (
            "С возвращением в <b>Башня Испытаний</b>.\n"
            "Выбери раздел кнопками ниже. Настройки, имя и промокоды — <b>⚙️ Настройки</b> или <code>/settings</code>.\n"
            "Команды /status, /floor, /inv, /titles, /top тоже работают."
        ),
        "daily_header": "📅 <b>Ежедневка</b>",
        "hub_title": "🏰 <b>Башня — штаб</b>",
        "hub_floor_line": "📍 Этаж <b>{floor}</b> / 135 · Ур. <b>{level}</b>",
        "hub_rank_line": "🎖️ Звание: <b>{rank}</b>",
        "hub_title_line": "🏆 Титул: <b>{title}</b>",
        "hub_pet_line": (
            "<i>🐾 Питомцы: пассив в бою, активен <b>один</b> — призыв в <b>городе</b>, "
            "смена в разделе <b>«Статус»</b>.</i>"
        ),
        "hub_daily_hint": "<i>Ежедневка — канал «{channel}» (кнопка ниже).</i>",
        "channel_display_name": "Испытание тьмы",
        "daily_today_kills": "Сегодня (UTC): побед <b>{kc}</b> / {goal}.",
        "daily_progress_done": (
            "⚔️ <b>Победы сегодня (UTC):</b> <b>{kc}</b> — цель <b>{goal}</b> выполнена ✅"
        ),
        "daily_progress_need": "⚔️ <b>Победы сегодня (UTC):</b> <b>{kc}</b> из <b>{goal}</b>.",
        "daily_streak_line": "🔥 <b>Стрик наград</b> (дней подряд): <b>{streak}</b>",
        "daily_reward_section_title": "🎁 <b>Награда</b>",
        "daily_reward_preview": (
            "Если забрать сегодня: <b>+{gold}</b> 💰 · <b>+{xp}</b> опыта · серия станет <b>{streak}</b> дн."
        ),
        "daily_reward_streak_note": (
            "<i>Каждый новый день с наградой подряд увеличивает золото и опыт (формула в бою после 3 побед).</i>"
        ),
        "daily_claimed_reward_hint": (
            "Текущая серия: <b>{streak}</b> дн. — завтра (UTC) снова <b>3 победы</b>, и награда вырастет."
        ),
        "daily_claimed_today": "✅ <b>Сегодня награда уже получена.</b> Новый цикл — с полуночи UTC.",
        "daily_can_claim_hint": "👉 Нажми <b>«Забрать награду»</b> ниже.",
        "daily_need_kills": "Ещё нужно побед до цели: <b>{need}</b>.",
        "daily_conditions_short": (
            "📌 <b>Условия:</b> <b>3 победы</b> в боях за календарный день (UTC) и активная подписка на канал башни."
        ),
        "daily_sub_required": (
            "────────────\n"
            "📢 <b>Канал</b>\n"
            "⚠️ Подпишись на «{channel}»: {link}\n"
            "<i>Затем «Проверить подписку» или заново открой ежедневку.</i>"
        ),
        "daily_sub_ok": (
            "────────────\n"
            "📢 <b>Канал</b>\n"
            "✅ <b>Подписка засчитана.</b> Когда будет 3 победы — жми «Забрать награду»."
        ),
        "daily_btn_channel": "📢 Канал: {channel}",
        "daily_btn_verify": "✅ Проверить подписку",
        "daily_btn_claim": "🎁 Забрать награду",
        "daily_claim_need": "Нужно {goal} победы сегодня. Осталось: {need}.",
        "daily_claim_reward": "🎁 <b>Награда!</b> +{gold} 💰, +{xp} опыта.{bonus}\nСтрик: <b>{streak}</b> дн.",
        "sub_err_channel_config": (
            "⚠️ <b>Подписка не проверяется:</b> бот не видит канал или не администратор в нём. "
            "Попроси владельца добавить бота в канал как администратора (или проверь имя канала в настройках бота)."
        ),
        "sub_err_generic": "⚠️ Не удалось проверить подписку через Telegram. Попробуй позже или напиши администратору.",
        "arena_title": "⚔️ <b>Арена</b>",
        "arena_menu_intro": (
            "⚔️ <b>Арена</b>\n\n"
            "• <b>Поединок 1×1</b> с реальным героем по <b>игровому ID</b> (см. в «Статус»):\n"
            "<code>/arena 3</code> — вызов игрока с ID 3.\n"
            "• Случайный соперник из базы (или тень башни, если вы один) — кнопка ниже.\n\n"
            "<i>Бой считается по силе билда (статы + оружие), без пошагового боя в чате.</i>"
        ),
        "arena_random_btn": "🎲 Случайный поединок",
        "arena_by_id_btn": "🆔 Вызов по ID",
        "arena_back_btn": "⬅️ Назад",
        "arena_your_game_id": "<i>Твой игровой ID (для друзей): <b>{gid}</b></i>",
        "arena_no_game_id_yet": "<i>Игровой ID появится после сохранения героя в базе.</i>",
        "arena_id_hint_alert": "Напиши в чат: /arena N — N = игровой ID соперника (в его «Статус»). Твой: {gid}.",
        "arena_id_hint_no_gid": "Напиши в чат: /arena N — N из статуса соперника. У тебя пока нет игрового ID.",
        "profile_pet_btn": "🐾 Питомец",
        "profile_pet_switch_btn": "🔄 Сменить питомца",
        "profile_pet_single_hint": (
            "Один питомец уже даёт пассив в бою. Ещё можно призвать в городе; "
            "активного выбирай в «Статус» или на полном экране характеристик."
        ),
        "profile_pet_none_hint": (
            "Питомцев пока нет. Призыв — в разделе «Город» (лавка хаба), когда этаж с городом доступен."
        ),
        "profile_pets_pick_header": "🐾 <b>Твои питомцы</b>",
        "profile_pets_pick_footer": "Нажми кнопку с именем — этот питомец станет активным в бою.",
        "profile_pet_active_mark": "(активен)",
        "profile_pet_passive_label": "Пассив:",
        "profile_pet_pick_back": "⬅️ К статусу",
        "profile_pet_set_ok": "Активен: {name}",
        "arena_no_char": "Сначала создай героя через /start.",
        "arena_result_win": "🏆 <b>Победа!</b> Твой билд сильнее.\n+{gold} 💰",
        "arena_result_lose": "💀 <b>Поражение.</b> У соперника билд жёстче. Попробуй позже.",
        "arena_result_lose_penalty": "💀 <b>Поражение.</b> У соперника билд жёстче.\nШтраф: <b>-{gold}</b> 💰",
        "arena_result_lose_no_gold": (
            "💀 <b>Поражение.</b> У соперника билд жёстче.\n"
            "<i>Штраф в золоте не списан — у героя не было чего удержать.</i>"
        ),
        "arena_daily_limit": "⚔️ Лимит арены: {limit} поединков за календарный день (UTC). Завтра снова.",
        "arena_menu_limits": (
            "<i>Лимит: <b>{limit}</b> поединков в сутки (UTC). За поражение — штраф в золоте "
            "(≈40% от базовой награды арены, не больше текущего баланса). "
            "Сегодня осталось: <b>{left}</b>.</i>"
        ),
        "arena_busy": "Сначала заверши текущий бой.",
        "arena_draw": "🤝 <b>Ничья.</b> Никто не получил награду.",
        "arena_help": (
            "<b>Арена</b>\n\n"
            "• <code>/arena 5</code> — поединок с героем с <b>игровым ID 5</b> (см. «Статус»).\n"
            "• <code>/arena</code> — случайный соперник (как кнопка в меню арены).\n"
            "• <code>/arena 123456789</code> — по <b>Telegram ID</b>, если нет героя с таким игровым ID.\n"
            "• <code>/arena @ник</code> / ник — по username; ответ на сообщение — тоже вызов.\n"
            "• Не больше <b>10</b> поединков в сутки (UTC); за поражение списывается золото.\n\n"
            "<i>Три раунда по силе билда (статы + оружие).</i>"
        ),
        "arena_err_self": "Нельзя вызвать самого себя.",
        "arena_err_not_found": "Пользователь не найден в башне (не писал боту или неверный ник).",
        "arena_err_no_hero_target": "У этого игрока ещё нет героя.",
        "arena_err_target_banned": "Этот аккаунт заблокирован.",
        "combat_revive_btn": "✨ Возродиться — на этаж",
        "top_ranker_badge": "· 🏅 <i>Ранкер</i>",
        "combat_rune_weak_spot": "🎯 <b>Слабое место!</b> Стихийный урон +{pct}%",
        "combat_rune_elemental_hit": "🔥 <b>Элементальный удар</b> +{pct}% к стихийному урону",
        "top_ranker_rule_hint": (
            "<i>Метка «Ранкер» у первых пяти в каждой категории. "
            "Лучшее место среди четырёх топов: <b>1-е</b> — +10% золота и +5% опыта с монстров; "
            "<b>2-е</b> — +8% / +3%; <b>3-е</b> — +6% / +1%; <b>4–5-е</b> — +5% золота (без опыта). "
            "Суммируется с титулами по отдельным множителям.</i>"
        ),
        "combat_leader_tier_1_note": (
            "<i>🏅 <b>Топ-1 рейтинга:</b> золото с монстра +10%, опыт +5%.</i>"
        ),
        "combat_leader_tier_2_note": (
            "<i>🏅 <b>Топ-2 рейтинга:</b> золото с монстра +8%, опыт +3%.</i>"
        ),
        "combat_leader_tier_3_note": (
            "<i>🏅 <b>Топ-3 рейтинга:</b> золото с монстра +6%, опыт +1%.</i>"
        ),
        "combat_leader_tier_mid_note": (
            "<i>🏅 <b>Топ-4–5 рейтинга:</b> золото с монстра +5%.</i>"
        ),
        "profile_ranker_tier_1_line": (
            "🏅 <b>Ранкер (лучшее место — 1-е)</b> <i>+10% золота и +5% опыта с монстров; не титул.</i>"
        ),
        "profile_ranker_tier_2_line": (
            "🏅 <b>Ранкер (лучшее место — 2-е)</b> <i>+8% золота и +3% опыта с монстров; не титул.</i>"
        ),
        "profile_ranker_tier_3_line": (
            "🏅 <b>Ранкер (лучшее место — 3-е)</b> <i>+6% золота и +1% опыта с монстров; не титул.</i>"
        ),
        "profile_ranker_tier_45_line": (
            "🏅 <b>Ранкер (топ-4–5)</b> <i>+5% золота с монстров; не титул.</i>"
        ),
        "profile_ranker_badge_tier_1": "🏅 Ранкер (1 место)",
        "profile_ranker_badge_tier_2": "🏅 Ранкер (2 место)",
        "profile_ranker_badge_tier_3": "🏅 Ранкер (3 место)",
        "profile_ranker_badge_tier_45": "🏅 Ранкер (топ-4–5)",
        "profile_ranker_effect_tier_1": (
            "🏅 Ранкер (1 место) +10% золота и +5% опыта с монстров; не титул."
        ),
        "profile_ranker_effect_tier_2": (
            "🏅 Ранкер (2 место) +8% золота и +3% опыта с монстров; не титул."
        ),
        "profile_ranker_effect_tier_3": (
            "🏅 Ранкер (3 место) +6% золота и +1% опыта с монстров; не титул."
        ),
        "profile_ranker_effect_tier_45": "🏅 Ранкер (топ-4–5) +5% золота с монстров; не титул.",
    },
}


def resolve_locale_from_telegram(language_code: str | None) -> str:
    return "ru"


def get_locale(character: "Character | None", telegram_language_code: str | None) -> str:
    return "ru"


def set_locale(character: "Character", code: str) -> None:
    """Раньше переключали язык; оставлено для совместимости вызовов — без эффекта."""
    return


def t(locale: str, key: str, **fmt: Any) -> str:
    _ = locale
    s = STRINGS["ru"].get(key) or key
    return s.format(**fmt) if fmt else s
