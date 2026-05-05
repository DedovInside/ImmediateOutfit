# ImmediateOutfit Sprint Map

## Sprint 1
- Гипотеза: если сделать постоянное хранилище и событийную аналитику, команда сможет реально измерять прогресс, а не описывать его словами.
- Что реализовано: SQLite, `users/profiles/saved_outfits/events`, обновленный dashboard.
- Что смотрим: completion, save rate, repeat usage, premium interest.

## Sprint 2
- Гипотеза: если анкета будет учитывать погоду, бюджет и формат дня, релевантность выдачи вырастет.
- Что реализовано: weather step, budget step, быстрый старт для повторных пользователей, расширенный recommender.
- Что смотрим: quiz completion, result view rate, dropoff by step.

## Sprint 3
- Гипотеза: если рекомендации будут снабжены curated-объяснениями, референсами и артикулами, доверие к ним вырастет.
- Что реализовано: curation layer, `reference`, `purchase_links`, richer result cards.
- Что смотрим: reference click rate, save rate, result feedback.

## Sprint 4
- Гипотеза: если пользователь сможет сохранить предпочтения и ключевые вещи, бот станет восприниматься как личный помощник.
- Что реализовано: профиль, любимые цвета, anti-preferences, key items, item-based flow.
- Что смотрим: profile completion, repeat usage, owned item usage.

## Sprint 5
- Гипотеза: второй сценарий `проверь мой образ` повысит возвращаемость и даст новую ценность.
- Что реализовано: структурированный review вместо простого keyword-match, feedback after review.
- Что смотрим: outfit check usage, review satisfaction.

## Sprint 6
- Гипотеза: спрос на premium лучше валидировать до полноценной оплаты через interest-flow.
- Что реализовано: premium page, early-access CTA, метрика `premium_interest_rate`.
- Что смотрим: premium viewed, premium interest.

## Sprint 7
- Гипотеза: если собрать roadmap, метрики, спринты и unit economics в единый narrative, защита станет опираться на факты.
- Что реализовано: docs-артефакты, dashboard links, product narrative base.
- Что смотрим: полноту материалов для отчета и презентации.
