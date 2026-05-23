# ImmediateOutfit Unit Economics (учебная версия)

## Модель
- `Freemium`
- Free: быстрый подбор, базовые советы, профиль, сохранения.
- Premium hypothesis: недельные подборки, deep personalization, гардеробный разбор, расширенные командные подборки, photo-review как эксперимент.

## Что считать
- `CAC` в учебном формате: стоимость привлечения 1 тестового пользователя через посты, чаты, знакомых и каналы.
- `Activation`: дошел до результата подбора.
- `Retention proxy`: вернулся и использовал бот повторно.
- `Premium interest`: нажал early-access / оставил интерес.

## Упрощенная формула
- `Expected revenue per activated user = premium_interest_rate * expected_conversion_to_paid * premium_price`
- `Contribution margin = expected revenue - infra/support cost per active user`

## Что валидируем сейчас
- Не реальную прибыль, а наличие поведенческого сигнала, что пользователи готовы перейти от бесплатной пользы к расширенному предложению.
- Реальная оплата в MVP не включена: сначала собираем `premium_interest`, чтобы не тратить ресурс на платежный контур без подтвержденного спроса.

## Следующий шаг
- После первых пользовательских спринтов протестировать 1-2 варианта premium price point и сравнить interest-rate.
- Для цифрового Premium в Telegram рассмотреть Telegram Stars: это убирает необходимость карточного эквайринга внутри бота, но требует terms/support/refund flow и отдельной юридической проверки перед реальными продажами.
