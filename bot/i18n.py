"""Короткие строки RU/EN: меню, частые экраны. Язык: meta персонажа или Telegram."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from db.models.character import Character

LOCALE_KEY = "locale"  # в character.meta_progress

STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "menu_profile": "🗡️ Профиль",
        "profile_invite_btn": "🔗 Пригласить друга",
        "profile_referral_back": "⬅️ К профилю",
        "menu_floor": "🗺️ Этаж",
        "menu_inv": "🎒 Инвентарь",
        "menu_titles": "🏆 Титулы",
        "menu_top": "📊 Топ игроков",
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
            "• <b>2</b> простых предмета экипировки в сумку\n"
            "• <b>+100</b> опыта на твоего героя\n\n"
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
        "settings_my_id": "Твой <b>Telegram ID</b> (для вызова на арене и т.п.):\n<code>{tid}</code>",
        "settings_tips_body": (
            "💡 <b>Подсказки</b>\n"
            "• Стамина тратится на бои на этаже; восстанавливается со временем.\n"
            "• Ежедневка — после побед и подписки на канал.\n"
            "• Арена: можно вызвать игрока по его Telegram ID (раздел «Мой ID»).\n"
            "• Команда <code>/lang ru</code> или <code>/lang en</code> — то же, что кнопка языка.\n"
            "• Промокод каждый можно ввести только один раз."
        ),
        "settings_combat_block": "Сначала заверши бой.",
        "settings_lang_switched": "Язык меню: <b>{lang}</b>",
        "menu_hub_title": "🏰 <b>Башня</b> — выбери раздел:",
        "welcome_back": (
            "С возвращением в <b>Башня Испытаний</b>.\n"
            "Выбери раздел кнопками ниже. Настройки, имя и промокоды — <b>⚙️ Настройки</b> или <code>/settings</code>.\n"
            "Команды /profile, /floor, /inv, /titles, /top тоже работают."
        ),
        "lang_usage": "Использование: <code>/lang ru</code> или <code>/lang en</code>",
        "lang_set": "Язык интерфейса (меню): <b>{lang}</b>",
        "daily_header": "📅 <b>Ежедневка</b>",
        "hub_title": "🏰 <b>Башня — штаб</b>",
        "hub_floor_line": "📍 Этаж <b>{floor}</b> / 100 · Ур. <b>{level}</b>",
        "hub_rank_line": "🎖️ Звание: <b>{rank}</b>",
        "hub_title_line": "🏆 Титул: <b>{title}</b>",
        "hub_daily_hint": "<i>Ежедневка — канал «{channel}» (кнопка ниже).</i>",
        "channel_display_name": "Испытание тьмы",
        "daily_today_kills": "Сегодня (UTC): побед <b>{kc}</b> / {goal}.",
        "daily_streak_line": "🔥 Стрик дней с наградой: <b>{streak}</b>.",
        "daily_claimed_today": "✅ Награда сегодня уже получена. Завтра снова.",
        "daily_can_claim_hint": "Нажми «Забрать награду» или команду ещё раз.",
        "daily_need_kills": "Осталось побед: <b>{need}</b>.",
        "daily_sub_required": "⚠️ <b>Нужна подписка</b> на канал «{channel}»: {link}\nПосле подписки нажми «Проверить» или снова открой ежедневку.",
        "daily_sub_ok": "✅ Канал: подписка учтена.",
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
        "arena_title": "⚔️ <b>Арена теней</b>",
        "arena_no_char": "Сначала создай героя через /start.",
        "arena_result_win": "🏆 <b>Победа!</b> Твоя тень сильнее.\n+{gold} 💰",
        "arena_result_lose": "💀 <b>Поражение.</b> Тень оказалась жёстче. Попробуй позже.",
        "arena_busy": "Сначала заверши текущий бой.",
        "arena_draw": "🤝 <b>Ничья.</b> Никто не получил награду.",
        "arena_help": (
            "<b>Арена</b> — дуэль «теней» по <b>реальному билду</b> из базы (статы + надетое оружие).\n\n"
            "• <code>/arena</code> — случайный живой игрок или тень башни, если вы один.\n"
            "• <code>/arena 123456789</code> — вызов по <b>Telegram ID</b> игрока.\n"
            "• <code>/arena @ник</code> или <code>/arena ник</code> — по <b>username</b> в Telegram.\n"
            "• Ответьте <code>/arena</code> на <b>сообщение</b> соперника в этом чате.\n\n"
            "<i>Соперник не должен быть в бою; это не заменяет PvP в реальном времени.</i>"
        ),
        "arena_err_self": "Нельзя вызвать самого себя.",
        "arena_err_not_found": "Пользователь не найден в башне (не писал боту или неверный ник).",
        "arena_err_no_hero_target": "У этого игрока ещё нет героя.",
        "arena_err_target_banned": "Этот аккаунт заблокирован.",
    },
    "en": {
        "menu_profile": "🗡️ Profile",
        "profile_invite_btn": "🔗 Invite a friend",
        "profile_referral_back": "⬅️ Back to profile",
        "menu_floor": "🗺️ Floor",
        "menu_inv": "🎒 Inventory",
        "menu_titles": "🏆 Titles",
        "menu_top": "📊 Leaderboard",
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
            "• <b>2</b> simple gear items to your bag\n"
            "• <b>+100</b> XP for your hero\n\n"
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
        "settings_my_id": "Your <b>Telegram ID</b> (for arena challenges, etc.):\n<code>{tid}</code>",
        "settings_tips_body": (
            "💡 <b>Tips</b>\n"
            "• Stamina is spent on floor battles; it regenerates over time.\n"
            "• Daily reward: wins + channel subscription.\n"
            "• Arena: challenge others by Telegram ID (see «My ID»).\n"
            "• <code>/lang ru</code> or <code>/lang en</code> — same as the language button.\n"
            "• Each promo code works once per account."
        ),
        "settings_combat_block": "Finish your current battle first.",
        "settings_lang_switched": "Menu language: <b>{lang}</b>",
        "menu_hub_title": "🏰 <b>Tower</b> — pick a section:",
        "welcome_back": (
            "Welcome back to <b>Tower of Trials</b>.\n"
            "Use the buttons below. Settings, name & promos: <b>⚙️ Settings</b> or <code>/settings</code>.\n"
            "Commands /profile, /floor, /inv, /titles, /top also work."
        ),
        "lang_usage": "Usage: <code>/lang ru</code> or <code>/lang en</code>",
        "lang_set": "Menu language: <b>{lang}</b>",
        "daily_header": "📅 <b>Daily reward</b>",
        "hub_title": "🏰 <b>Tower — HQ</b>",
        "hub_floor_line": "📍 Floor <b>{floor}</b> / 100 · Lv. <b>{level}</b>",
        "hub_rank_line": "🎖️ Path rank: <b>{rank}</b>",
        "hub_title_line": "🏆 Title: <b>{title}</b>",
        "hub_daily_hint": "<i>Daily reward — channel «{channel}» (button below).</i>",
        "channel_display_name": "Trial of Darkness",
        "daily_today_kills": "Today (UTC): wins <b>{kc}</b> / {goal}.",
        "daily_streak_line": "🔥 Reward streak (days): <b>{streak}</b>.",
        "daily_claimed_today": "✅ Reward already claimed today. Come back tomorrow.",
        "daily_can_claim_hint": "Tap «Claim reward» or use the command again.",
        "daily_need_kills": "Wins left: <b>{need}</b>.",
        "daily_sub_required": "⚠️ <b>Subscription required</b> for «{channel}»: {link}\nAfter subscribing, tap «Verify» or open daily again.",
        "daily_sub_ok": "✅ Channel subscription OK.",
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
        "arena_title": "⚔️ <b>Shadow arena</b>",
        "arena_no_char": "Create a hero with /start first.",
        "arena_result_win": "🏆 <b>Victory!</b> Your shadow was stronger.\n+{gold} 💰",
        "arena_result_lose": "💀 <b>Defeat.</b> The shadow was tougher. Try again later.",
        "arena_busy": "Finish your current battle first.",
        "arena_draw": "🤝 <b>Draw.</b> No reward.",
        "arena_help": (
            "<b>Arena</b> — shadow duel using <b>real builds</b> from the DB (stats + equipped weapon).\n\n"
            "• <code>/arena</code> — random player, or tower shadow if you are alone.\n"
            "• <code>/arena 123456789</code> — challenge by <b>Telegram user ID</b>.\n"
            "• <code>/arena @nick</code> or <code>/arena nick</code> — by Telegram <b>username</b>.\n"
            "• Reply with <code>/arena</code> to someone's <b>message</b> in this chat.\n\n"
            "<i>Not real-time PvP; the opponent is not notified.</i>"
        ),
        "arena_err_self": "You cannot challenge yourself.",
        "arena_err_not_found": "User not in the tower DB (never /start or wrong username).",
        "arena_err_no_hero_target": "That player has no hero yet.",
        "arena_err_target_banned": "That account is banned.",
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
