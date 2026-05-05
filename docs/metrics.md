# ImmediateOutfit Metrics

Набор метрик, который закрывает учебное требование `11+ метрик` и привязан к событиям в боте.

1. `quiz_started` — сколько раз пользователи запускали подбор.
2. `quiz_completed` — сколько раз доходили до конца анкеты.
3. `quiz_completion_rate = quiz_completed / quiz_started`.
4. `result_view_rate = results_viewed / quiz_started`.
5. `dropoff_by_step` — количество ответов на каждом шаге анкеты.
6. `save_rate = saved_outfits_total / results_viewed`.
7. `show_more_rate = show_more / results_viewed`.
8. `repeat_usage_rate = users_with_2plus_active_days / total_users`.
9. `profile_completion_rate = profiles_completed / total_users`.
10. `weather_usage_rate = weather_selected / quiz_started`.
11. `owned_item_usage_rate = item_flow_started / quiz_started`.
12. `outfit_check_usage_rate = review_started / total_users`.
13. `reference_click_rate = reference_opened / results_viewed`.
14. `premium_interest_rate = premium_interest / total_users`.
15. `satisfaction_rate` — средняя оценка полезности подборки.
16. `review_satisfaction_rate` — средняя оценка сценария разбора образа.

События, на которых это держится:
- `bot_started`
- `quiz_started`
- `question_answered`
- `weather_selected`
- `quiz_completed`
- `results_viewed`
- `outfit_saved`
- `show_more`
- `reference_opened`
- `links_opened`
- `profile_updated`
- `item_flow_started`
- `review_started`
- `review_completed`
- `result_feedback`
- `review_feedback`
- `premium_viewed`
- `premium_interest`
