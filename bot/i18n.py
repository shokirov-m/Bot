"""Короткие строки RU/EN: меню, частые экраны. Язык: meta персонажа или Telegram."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from db.models.character import Character

LOCALE_KEY = "locale"  # в character.meta_progress

STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "menu_profile": "🗡️ Статус",
        "profile_back_compact": "⬅️ К статусу",
        "profile_class_btn": "📜 Класс",
        "profile_class_screen_title": "📜 <b>Класс героя</b>",
        "profile_rest_btn_start": "🛏️ Передышка (1 мин)",
        "profile_rest_btn_wait": "🛏️ ~{sec} с до полного HP/MP",
        "menu_floor": "🗺️ Этаж",
        "menu_inv": "🎒 Инвентарь",
        "menu_titles": "🏆 Титулы",
        "menu_top": "📊 Топ игроков",
        "menu_city": "🏙️ Город",
        "menu_city_unavailable": "Город только на городских этажах. Открой этаж с хабом или спустись к нему.",
        "city_pet_summon_1": "🐾 ×1 {cost}💰 · сегодня {left}/3",
        "city_pet_summon_3": "🐾 ×3 {cost}💰 · сегодня {left}/3",
        "pet_city_summon_limit": (
            "Лимит призывов за сегодня (UTC): <b>{limit}</b> броска. "
            "Свободно сейчас: <b>{left}</b> (×3 забирает три за раз)."
        ),
        "menu_daily": "📅 Ежедневка",
        "menu_arena": "⚔️ Арена",
        "menu_quests": "📋 Задания",
        "menu_settings": "⚙️ Настройки",
        "menu_auction": "🏛️ Аукцион",
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
            "<b>Твоя ссылка:</b>\n<code>{link}</code>"
        ),
        "settings_referral_no_username": "У бота нет username в Telegram — задай имя в @BotFather, чтобы ссылка работала.",
        "settings_lang_btn": "🌐 Язык RU/EN",
        "settings_my_id_btn": "🆔 Мой Telegram ID",
        "settings_tips_btn": "💡 Подсказки",
        "settings_images_disable": "🖼 Выключить фото этажа и портрет",
        "settings_images_enable": "🖼 Включить фото этажа и портрет",
        "settings_reset_btn": "🗑️ Сбросить весь прогресс",
        "settings_reset_warn": (
            "⚠️ <b>Сбросить весь прогресс?</b>\n\n"
            "Обнулятся этаж, инвентарь, квесты, золото, опыт, подкласс, титул и прочий прогресс в JSON. "
            "Останутся <b>имя героя</b> и <b>класс</b> (статы класса с начала), язык интерфейса не сбрасывается.\n\n"
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
        "settings_promo_ok": "🎁 Промокод принят!\n+{gold} 💰 · +{xp} опыта.{rune_part}{level_part}{items_part}",
        "settings_promo_rune": "\n⚗️ +{rune} рунных камней",
        "settings_promo_levels": "\n📈 Новых уровней: <b>{n}</b>",
        "settings_promo_items": "\n🎒 В сумку: <b>{items}</b>",
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
        "settings_name_chars": "Допустимы буквы (RU/EN), цифры, пробел, дефис, точка посередине.",
        "settings_cancel_btn": "✖️ Отмена",
        "settings_fsm_cancelled": "Отменено.",
        "settings_my_id": "Твой <b>Telegram ID</b>:\n<code>{tid}</code>\n\n<i>Для вызова на арене используй <b>игровой ID</b> из раздела «Статус».</i>",
        "settings_tips_body": (
            "💡 <b>Подсказки</b>\n"
            "• Стамина тратится на бои на этаже; восстанавливается со временем.\n"
            "• Ежедневка — после побед и подписки на канал.\n"
            "• Арена: вызов по <b>игровому ID</b> из статуса — <code>/arena 5</code>; случайный поединок — кнопка в разделе «Арена».\n"
            "• Команда <code>/lang ru</code> или <code>/lang en</code> — то же, что кнопка языка.\n"
            "• Промокод каждый можно ввести только один раз."
        ),
        "settings_combat_block": "Сначала заверши бой.",
        "settings_lang_switched": "Язык меню: <b>{lang}</b>",
        "menu_hub_title": "🏰 <b>Башня</b> — выбери раздел:",
        "welcome_back": (
            "С возвращением в <b>Башня Испытаний</b>.\n"
            "Выбери раздел кнопками ниже. Настройки, имя и промокоды — <b>⚙️ Настройки</b> или <code>/settings</code>.\n"
            "Команды /status, /floor, /inv, /titles, /top тоже работают."
        ),
        "lang_usage": "Использование: <code>/lang ru</code> или <code>/lang en</code>",
        "lang_set": "Язык интерфейса (меню): <b>{lang}</b>",
        "daily_header": "📅 <b>Ежедневка</b>",
        "hub_title": "🏰 <b>Башня — штаб</b>",
        "hub_floor_line": "📍 Этаж <b>{floor}</b> / 100 · Ур. <b>{level}</b>",
        "hub_rank_line": "🎖️ Звание: <b>{rank}</b>",
        "hub_title_line": "🏆 Титул: <b>{title}</b>",
        "hub_pet_line": (
            "<i>🐾 Питомцы: пассивный бонус в бою, активен <b>один</b> — призыв в "
            "<b>Городе</b>, смена в статусе или на этажах 8/48.</i>"
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
            "Один питомец уже даёт пассив в бою. Второго можно призвать в городе; "
            "смена активного — в статусе (кнопка ниже), на полном экране характеристик или на этажах 8/48."
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
    },
    "en": {
        "menu_profile": "🗡️ Status",
        "profile_back_compact": "⬅️ Back to status",
        "profile_class_btn": "📜 Class",
        "profile_class_screen_title": "📜 <b>Your class</b>",
        "profile_rest_btn_start": "🛏️ Rest (1 min)",
        "profile_rest_btn_wait": "🛏️ ~{sec}s to full HP/MP",
        "menu_floor": "🗺️ Floor",
        "menu_inv": "🎒 Inventory",
        "menu_titles": "🏆 Titles",
        "menu_top": "📊 Leaderboard",
        "menu_city": "🏙️ City",
        "menu_city_unavailable": "City hub is only on certain floors. Go to a city floor (or travel there).",
        "city_pet_summon_1": "🐾 ×1 {cost}💰 · today {left}/3",
        "city_pet_summon_3": "🐾 ×3 {cost}💰 · today {left}/3",
        "pet_city_summon_limit": (
            "Daily summon limit (UTC): <b>{limit}</b> pulls. "
            "Available now: <b>{left}</b> (×3 uses three at once)."
        ),
        "menu_daily": "📅 Daily",
        "menu_arena": "⚔️ Arena",
        "menu_quests": "📋 Quests",
        "menu_settings": "⚙️ Settings",
        "menu_auction": "🏛️ Auction",
        "settings_title": "⚙️ <b>Settings</b>",
        "settings_intro": "Hero name, promo codes, referral link, language, tips.",
        "settings_rename_btn": "✏️ Change name",
        "settings_promo_btn": "🎁 Promo code",
        "settings_referral_btn": "👥 Invite a friend",
        "settings_referral_title": "👥 <b>Referral program</b>",
        "settings_referral_body": (
            "Send the link below to a friend. If they <b>first</b> open the bot via it, create a hero, "
            "and reach <b>level 2</b>, you get:\n"
            "• <b>2</b> rare gear items in your bag\n"
            "• <b>+200</b> XP for your hero\n\n"
            "<b>Your link:</b>\n<code>{link}</code>"
        ),
        "settings_referral_no_username": "This bot has no @username — set it in @BotFather so the link works.",
        "settings_lang_btn": "🌐 Language RU/EN",
        "settings_my_id_btn": "🆔 My Telegram ID",
        "settings_tips_btn": "💡 Tips",
        "settings_images_disable": "🖼 Turn off floor & portrait photos",
        "settings_images_enable": "🖼 Turn on floor & portrait photos",
        "settings_reset_btn": "🗑️ Reset all progress",
        "settings_reset_warn": (
            "⚠️ <b>Reset all progress?</b>\n\n"
            "This wipes floor progress, inventory, quests, gold, XP, subclass, title, and other JSON meta. "
            "<b>Hero name</b> and <b>class</b> stay (class base stats). Menu language is kept.\n\n"
            "<i>Cannot be undone.</i>"
        ),
        "settings_reset_yes": "⚠️ Yes, reset everything",
        "settings_reset_no": "⬅ Back",
        "settings_reset_done": (
            "✅ <b>Progress reset.</b> You are on floor 1 with starter gear and bread, like a new hero. "
            "Name and class are unchanged — open the floor when ready."
        ),
        "settings_stat_reset_btn": "📊 Reset stat allocation",
        "settings_stat_reset_warn": (
            "<b>Reset manually placed stat points</b>\n\n"
            "Cost: <b>{gold}</b> gold. At most <b>once per calendar day (UTC)</b>.\n"
            "Points spent via /stats above your class baseline return to <b>unspent</b>; "
            "primary stats match the class again (×2 if you already picked a subclass).\n\n"
            "You can refund now: <b>{points}</b> pts.\n\n"
            "<i>Gear and title bonuses are unchanged — only manual allocation is reset.</i>"
        ),
        "settings_stat_reset_yes": "✅ Reset for {gold} gold",
        "settings_stat_reset_no": "⬅ Cancel",
        "settings_stat_reset_done": (
            "✅ <b>Allocation reset.</b> Refunded <b>{points}</b> unspent points. "
            "Charged <b>{gold}</b> gold. Redistribute with /stats."
        ),
        "settings_stat_reset_today": "Stat reset already used today (UTC). Try again tomorrow.",
        "settings_stat_reset_none": "No extra points invested — nothing to reset (/stats).",
        "settings_stat_reset_no_gold": "Not enough gold. Need <b>{gold}</b>.",
        "settings_back_menu": "📋 Main menu",
        "settings_rename_intro": "Name change costs <b>{gold}</b> gold. Send the new name in <b>one message</b> (2–32 chars, letters and numbers).",
        "settings_rename_done": "✅ Name set to: <b>{name}</b>\nCharged <b>{gold}</b> gold.",
        "settings_rename_no_gold": "Not enough gold. Need <b>{gold}</b>.",
        "settings_promo_prompt": "Send the promo code in <b>one message</b>.",
        "settings_promo_ok": "🎁 Promo accepted!\n+{gold} gold · +{xp} XP.{rune_part}{level_part}{items_part}",
        "settings_promo_rune": "\n⚗️ +{rune} rune stone(s)",
        "settings_promo_levels": "\n📈 Level-ups: <b>{n}</b>",
        "settings_promo_items": "\n🎒 To bag: <b>{items}</b>",
        "settings_promo_bag_full": "You need two free bag slots — free some space and enter the code again.",
        "settings_promo_bad_format": "Invalid code format.",
        "settings_promo_unknown": "Unknown or disabled code.",
        "settings_promo_used": "You already redeemed this code.",
        "settings_promo_expired": "This promo code has expired.",
        "settings_promo_exhausted": "This promo code has reached its redemption limit.",
        "settings_promo_disabled": "This promo code was disabled by an admin.",
        "settings_promo_not_started": "This promo code is not active yet.",
        "settings_name_short": "Name too short (min 2 characters).",
        "settings_name_long": "Name too long (max 32 characters).",
        "settings_name_chars": "Use letters (RU/EN), digits, space, hyphen, middle dot.",
        "settings_cancel_btn": "✖️ Cancel",
        "settings_fsm_cancelled": "Cancelled.",
        "settings_my_id": "Your <b>Telegram ID</b>:\n<code>{tid}</code>\n\n<i>For arena, use the <b>game ID</b> from «Status».</i>",
        "settings_tips_body": (
            "💡 <b>Tips</b>\n"
            "• Stamina is spent on floor battles; it regenerates over time.\n"
            "• Daily reward: wins + channel subscription.\n"
            "• Arena: duel by <b>game ID</b> from Status — <code>/arena 5</code>; random match — Arena menu button.\n"
            "• <code>/lang ru</code> or <code>/lang en</code> — same as the language button.\n"
            "• Each promo code works once per account."
        ),
        "settings_combat_block": "Finish your current battle first.",
        "settings_lang_switched": "Menu language: <b>{lang}</b>",
        "menu_hub_title": "🏰 <b>Tower</b> — pick a section:",
        "welcome_back": (
            "Welcome back to <b>Tower of Trials</b>.\n"
            "Use the buttons below. Settings, name & promos: <b>⚙️ Settings</b> or <code>/settings</code>.\n"
            "Commands /status, /floor, /inv, /titles, /top also work."
        ),
        "lang_usage": "Usage: <code>/lang ru</code> or <code>/lang en</code>",
        "lang_set": "Menu language: <b>{lang}</b>",
        "daily_header": "📅 <b>Daily reward</b>",
        "hub_title": "🏰 <b>Tower — HQ</b>",
        "hub_floor_line": "📍 Floor <b>{floor}</b> / 100 · Lv. <b>{level}</b>",
        "hub_rank_line": "🎖️ Path rank: <b>{rank}</b>",
        "hub_title_line": "🏆 Title: <b>{title}</b>",
        "hub_pet_line": (
            "<i>🐾 Pets: passive combat bonus, only <b>one</b> active — summon in "
            "<b>City</b>; switch in Status or on floors 8/48.</i>"
        ),
        "hub_daily_hint": "<i>Daily reward — channel «{channel}» (button below).</i>",
        "channel_display_name": "Trial of Darkness",
        "daily_today_kills": "Today (UTC): wins <b>{kc}</b> / {goal}.",
        "daily_progress_done": "⚔️ <b>Wins today (UTC):</b> <b>{kc}</b> — goal <b>{goal}</b> done ✅",
        "daily_progress_need": "⚔️ <b>Wins today (UTC):</b> <b>{kc}</b> / <b>{goal}</b>.",
        "daily_streak_line": "🔥 <b>Reward streak</b> (days in a row): <b>{streak}</b>",
        "daily_reward_section_title": "🎁 <b>Reward</b>",
        "daily_reward_preview": (
            "If you claim today: <b>+{gold}</b> 💰 · <b>+{xp}</b> XP · streak becomes <b>{streak}</b> day(s)."
        ),
        "daily_reward_streak_note": (
            "<i>Each consecutive reward day increases gold and XP (after 3 wins).</i>"
        ),
        "daily_claimed_reward_hint": (
            "Current streak: <b>{streak}</b> day(s) — tomorrow (UTC) again <b>3 wins</b> for the next reward."
        ),
        "daily_claimed_today": "✅ <b>Reward already claimed today.</b> Next cycle from UTC midnight.",
        "daily_can_claim_hint": "👉 Tap <b>«Claim reward»</b> below.",
        "daily_need_kills": "Wins still needed: <b>{need}</b>.",
        "daily_conditions_short": (
            "📌 <b>Rules:</b> <b>3 combat wins</b> per calendar day (UTC) and an active channel subscription."
        ),
        "daily_sub_required": (
            "────────────\n"
            "📢 <b>Channel</b>\n"
            "⚠️ Subscribe to «{channel}»: {link}\n"
            "<i>Then «Verify subscription» or open daily again.</i>"
        ),
        "daily_sub_ok": (
            "────────────\n"
            "📢 <b>Channel</b>\n"
            "✅ <b>Subscribed.</b> After 3 wins, tap «Claim reward»."
        ),
        "daily_btn_channel": "📢 Channel: {channel}",
        "daily_btn_verify": "✅ Verify subscription",
        "daily_btn_claim": "🎁 Claim reward",
        "daily_claim_need": "You need {goal} wins today. Remaining: {need}.",
        "daily_claim_reward": "🎁 <b>Reward!</b> +{gold} gold, +{xp} XP.{bonus}\nStreak: <b>{streak}</b> day(s).",
        "sub_err_channel_config": (
            "⚠️ <b>Cannot verify subscription:</b> the bot cannot see the channel or is not an admin. "
            "Ask the owner to add the bot as an admin (or check the channel username in bot settings)."
        ),
        "sub_err_generic": "⚠️ Telegram could not verify subscription. Try again later or contact an admin.",
        "arena_title": "⚔️ <b>Arena</b>",
        "arena_menu_intro": (
            "⚔️ <b>Arena</b>\n\n"
            "• <b>1×1 duel</b> with a real hero by <b>game ID</b> (see «Status»):\n"
            "<code>/arena 3</code> — challenge player with ID 3.\n"
            "• Random opponent from the DB (or tower shadow if you are alone) — button below.\n\n"
            "<i>Three rounds by build power (stats + weapon). Not turn-by-turn chat PvP.</i>"
        ),
        "arena_random_btn": "🎲 Random duel",
        "arena_by_id_btn": "🆔 Challenge by ID",
        "arena_back_btn": "⬅️ Back",
        "arena_your_game_id": "<i>Your game ID (for friends): <b>{gid}</b></i>",
        "arena_no_game_id_yet": "<i>Game ID appears after your hero is saved to the database.</i>",
        "arena_id_hint_alert": "Type in chat: /arena N — N = rival's game ID (their Status). Yours: {gid}.",
        "arena_id_hint_no_gid": "Type: /arena N — N from rival's Status. You have no game ID yet.",
        "profile_pet_btn": "🐾 Pet",
        "profile_pet_switch_btn": "🔄 Switch pet",
        "profile_pet_single_hint": (
            "One pet already gives a combat passive. Summon more in the City; "
            "switch the active pet in Status, on the full stats screen, or on floors 8/48."
        ),
        "profile_pet_none_hint": (
            "No pets yet. Summon them in City (hub shop) when a city floor is available."
        ),
        "profile_pets_pick_header": "🐾 <b>Your pets</b>",
        "profile_pets_pick_footer": "Tap a button below to set that pet as active in combat.",
        "profile_pet_active_mark": "(active)",
        "profile_pet_passive_label": "Passive:",
        "profile_pet_pick_back": "⬅️ Back to status",
        "profile_pet_set_ok": "Active: {name}",
        "arena_no_char": "Create a hero with /start first.",
        "arena_result_win": "🏆 <b>Victory!</b> Your build won.\n+{gold} 💰",
        "arena_result_lose": "💀 <b>Defeat.</b> The opponent's build was stronger. Try again later.",
        "arena_result_lose_penalty": "💀 <b>Defeat.</b> The opponent's build was stronger.\nPenalty: <b>-{gold}</b> 💰",
        "arena_result_lose_no_gold": (
            "💀 <b>Defeat.</b> The opponent's build was stronger.\n"
            "<i>No gold penalty — your balance was already empty.</i>"
        ),
        "arena_daily_limit": "⚔️ Arena limit: {limit} matches per calendar day (UTC). Come back tomorrow.",
        "arena_menu_limits": (
            "<i>Limit: <b>{limit}</b> matches per day (UTC). Defeat costs gold "
            "(~40% of the arena base reward, up to your current balance). "
            "Remaining today: <b>{left}</b>.</i>"
        ),
        "arena_busy": "Finish your current battle first.",
        "arena_draw": "🤝 <b>Draw.</b> No reward.",
        "arena_help": (
            "<b>Arena</b>\n\n"
            "• <code>/arena 5</code> — duel the hero with <b>game ID 5</b> (see «Status»).\n"
            "• <code>/arena</code> — same as «Random duel» in the Arena menu.\n"
            "• <code>/arena 123456789</code> — by <b>Telegram ID</b> if no hero has that game ID.\n"
            "• <code>/arena @nick</code> / nick — by username; reply with <code>/arena</code> to a message.\n"
            "• Up to <b>10</b> matches per day (UTC); defeats cost gold.\n\n"
            "<i>Three rounds by build power (stats + weapon).</i>"
        ),
        "arena_err_self": "You cannot challenge yourself.",
        "arena_err_not_found": "User not in the tower DB (never /start or wrong username).",
        "arena_err_no_hero_target": "That player has no hero yet.",
        "arena_err_target_banned": "That account is banned.",
        "combat_revive_btn": "✨ Revive — back to floor",
        "combat_rune_weak_spot": "🎯 <b>Weak spot!</b> Elemental damage +{pct}%",
        "combat_rune_elemental_hit": "🔥 <b>Elemental strike</b> +{pct}% elemental damage",
        "top_ranker_badge": "· 🏅 <i>Ranker</i>",
        "top_ranker_rule_hint": (
            "<i>«Ranker» tag for the top five in each category. "
            "Your <b>best</b> rank across four boards: <b>1st</b> — +10% gold and +5% XP from monsters; "
            "<b>2nd</b> — +8% / +3%; <b>3rd</b> — +6% / +1%; <b>4th–5th</b> — +5% gold (no XP). "
            "Stacks with titles as separate multipliers.</i>"
        ),
        "combat_leader_tier_1_note": (
            "<i>🏅 <b>Leaderboard #1 (best):</b> +10% monster gold, +5% XP.</i>"
        ),
        "combat_leader_tier_2_note": (
            "<i>🏅 <b>Leaderboard #2 (best):</b> +8% monster gold, +3% XP.</i>"
        ),
        "combat_leader_tier_3_note": (
            "<i>🏅 <b>Leaderboard #3 (best):</b> +6% monster gold, +1% XP.</i>"
        ),
        "combat_leader_tier_mid_note": (
            "<i>🏅 <b>Leaderboard #4–5 (best):</b> +5% monster gold.</i>"
        ),
        "profile_ranker_tier_1_line": (
            "🏅 <b>Ranker (best rank — 1st)</b> <i>+10% gold and +5% XP from monsters; not a title.</i>"
        ),
        "profile_ranker_tier_2_line": (
            "🏅 <b>Ranker (best rank — 2nd)</b> <i>+8% gold and +3% XP from monsters; not a title.</i>"
        ),
        "profile_ranker_tier_3_line": (
            "🏅 <b>Ranker (best rank — 3rd)</b> <i>+6% gold and +1% XP from monsters; not a title.</i>"
        ),
        "profile_ranker_tier_45_line": (
            "🏅 <b>Ranker (top 4–5)</b> <i>+5% gold from monsters; not a title.</i>"
        ),
    },
}


def resolve_locale_from_telegram(language_code: str | None) -> str:
    if not language_code:
        return "ru"
    lc = language_code.lower().split("-")[0]
    return "en" if lc == "en" else "ru"


def get_locale(character: "Character | None", telegram_language_code: str | None) -> str:
    if character is not None:
        meta = character.meta_progress or {}
        raw = meta.get(LOCALE_KEY)
        if raw in ("en", "ru"):
            return str(raw)
    return resolve_locale_from_telegram(telegram_language_code)


def set_locale(character: "Character", code: str) -> None:
    code = code.lower().strip()
    if code not in ("en", "ru"):
        return
    meta: dict[str, Any] = dict(character.meta_progress or {})
    meta[LOCALE_KEY] = code
    character.meta_progress = meta


def t(locale: str, key: str, **fmt: Any) -> str:
    loc = locale if locale in STRINGS else "ru"
    s = STRINGS[loc].get(key) or STRINGS["ru"].get(key) or key
    return s.format(**fmt) if fmt else s
