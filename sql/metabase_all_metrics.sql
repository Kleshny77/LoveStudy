-- LoveStudy · Metabase · PostgreSQL
--
-- Как пользоваться
--   1. «+ Новый» → «SQL запрос» → база db1.
--   2. Скопируй ОДИН блок от линии ━━━ до следующей ━━━ (включая SELECT).
--   3. При сохранении вопроса вставь строку из «Сохранить как: …» в имя.
--   4. «Визуализация» → тип из строки «График:» (названия как в русском Metabase:
--      Тренд, Таблица, Число, Строка, Пирог, Воронка, Линия, Область, Гистограмма, Комбо,
--      Прогресс, Прибор, Сводная таблица, Детали, Разброс, Водопад, Карта, Box Plot, Sankey).
--
-- Колонки в кавычках — русские заголовки в таблице результата.
--
-- «Тренд» в Metabase (см. документацию: https://www.metabase.com/docs/latest/questions/visualizations/trend ):
--   • Это НЕ график с осями X/Y. На экране — одно крупное число за самый последний период (последняя дата/неделя/месяц
--     в результате) и сравнение с предыдущим периодом или целью. Период задаётся полем времени в GROUP BY.
--   • В запросе нужны: поле времени + одна агрегированная метрика (как «число заказов по дате создания» в доках).
--   • «Данные» → «Основной номер» = колонка метрики (как в AS "…"). Сравнения — «Предыдущий период» / «Предыдущее значение»
--     и т.д. Если предыдущей точки нет (одна строка, пустой день) — будет «Н/Д» / сравнение скрыто.
--   • Чтобы видеть кривую по ВСЕМ датам с осями — визуализации «Линия», «Область» или «Гистограмма», не «Тренд».
--   • Несколько метрик в одном SELECT: для кривой — «Комбо» / «Линия»; «Тренд» — по одной метрике (или отдельный вопрос на каждую).
--   • В блоках ниже фраза про «Тренд» и «вкладки „Оси“ нет» — то же самое: это не Линия/Область, нет настройки осей как в «Области значений».
--   • Один сохранённый вопрос = одна визуализация: нельзя одновременно и Область, и Тренд. Нужны оба — дублируй вопрос (тот же SQL) или две карточки на дашборде.
--
-- «Линия», «Область», «Гистограмма», «Комбо» — боковая панель «Область значений», вкладка «Данные» (у «Линии» те же поля, что у «Области»):
--   • Ось абсцисс — временная или категориальная колонка из SQL (имя как в AS "…").
--   • Ось ординат — числовая метрика; несколько рядов — несколько метрик на оси ординат (Комбо / Линия).
--   Подписи и шкалы — вкладки «Вид», «Оси». «Строка» / «Пирог»: те же имена колонок в «Данные».

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Всего зарегистрированных пользователей
-- Метрика: сколько строк в таблице пользователей (все время).
-- График: Число (если Metabase не даёт — Таблица из одной ячейки).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT count(*) AS "Всего пользователей"
FROM users;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Новые регистрации по дням
-- Метрика: сколько новых пользователей зарегистрировалось каждый день (90 дней).
-- График: Линия или Область — «Данные»: Ось абсцисс «Дата», Ось ординат «Новых пользователей». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(*) AS "Новых пользователей"
FROM users
WHERE created_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: DAU — активные пользователи по дням
-- Метрика: уникальные пользователи с хотя бы одним событием за календарный день (UTC).
-- График: Линия или Область — «Данные»: Ось абсцисс «Дата», Ось ординат «Активных пользователей (DAU)». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(DISTINCT user_telegram_id) AS "Активных пользователей (DAU)"
FROM analytics_events
WHERE user_telegram_id IS NOT NULL
  AND created_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: WAU — активные по неделям (пн–вс, UTC)
-- Метрика: уникальные пользователи за неделю; неделя с понедельника по воскресенье.
-- Если в Metabase «Показать 1 строка» и на графике одна точка — это не ошибка SQL: в analytics_events за период
--   попадает только одна неделя (мало истории). Подписи вдоль X вроде «5 апр, 6 апр, 6 апр» при одной строке —
--   не твои данные: линейный график по дате сам рисует тики на временной шкале вокруг одной точки (дубли — косяк авто-тиков).
-- Проверка числа недель: SELECT count(DISTINCT date_trunc('week', created_at AT TIME ZONE 'UTC')) FROM analytics_events
--   WHERE user_telegram_id IS NOT NULL AND created_at >= now() - interval '365 days';
-- График: Гистограмма или Линия — «Данные»: Ось абсцисс «Неделя с (понедельник UTC)», Ось ординат «Активных пользователей (WAU)»; колонку «По воскресенью» скрой. Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('week', created_at AT TIME ZONE 'UTC')::date AS "Неделя с (понедельник UTC)",
  (date_trunc('week', created_at AT TIME ZONE 'UTC') + interval '6 days')::date AS "По воскресенье (UTC)",
  count(DISTINCT user_telegram_id) AS "Активных пользователей (WAU)"
FROM analytics_events
WHERE user_telegram_id IS NOT NULL
  AND created_at >= now() - interval '365 days'
GROUP BY 1, 2
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: MAU — активные по месяцам
-- Метрика: уникальные пользователи за календарный месяц (UTC).
-- График: Гистограмма или Линия — «Данные»: Ось абсцисс «Месяц», Ось ординат «Активных пользователей (MAU)». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('month', created_at AT TIME ZONE 'UTC')::date AS "Месяц",
  count(DISTINCT user_telegram_id) AS "Активных пользователей (MAU)"
FROM analytics_events
WHERE user_telegram_id IS NOT NULL
  AND created_at >= now() - interval '730 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Помодоро — активность по дням
-- Метрика: по завершённым рабочим сессиям из лога — DAU помодоро, число сессий, минуты работы.
-- График: Комбо или Линия — «Данные»: Ось абсцисс «Дата»; на оси ординат три ряда — «Уникальных пользователей», «Завершённых сессий работы», «Минут работы всего». Тренд — отдельный вопрос на одну метрику.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', completed_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(DISTINCT user_telegram_id) AS "Уникальных пользователей",
  count(*) AS "Завершённых сессий работы",
  coalesce(sum(work_minutes), 0) AS "Минут работы всего"
FROM pomodoro_session_logs
WHERE completed_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: События за 30 дней — что происходило чаще всего
-- Метрика: сколько раз сработало каждое имя события.
-- График: Строка — в «Данные» выбери колонки «Событие» и «Сколько раз» (подпись и длина полосы).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  CASE event_name
    WHEN 'bot_started' THEN 'Старт бота (/start)'
    WHEN 'main_menu_shown' THEN 'Главное меню показано'
    WHEN 'open_screen' THEN 'Открыт раздел меню'
    WHEN 'material_saved' THEN 'Материал сохранён'
    WHEN 'deadline_created' THEN 'Дедлайн создан'
    WHEN 'pomodoro_work_completed' THEN 'Помодоро: работа завершена'
    WHEN 'quiz_generated' THEN 'Тест сгенерирован'
    WHEN 'quiz_session_completed' THEN 'Тест пройден (сессия)'
    WHEN 'subscription_paid' THEN 'Оплата подписки'
    ELSE event_name
  END AS "Событие",
  count(*) AS "Сколько раз"
FROM analytics_events
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Какие разделы открывали из меню (30 дней)
-- Метрика: нажатия по пунктам главного меню (событие open_screen).
-- График: Строка или Пирог — «Данные»: для Строки «Раздел» и «Сколько раз открыли»; сортировка в SQL уже по убыванию.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  CASE coalesce(properties->>'screen', '')
    WHEN 'materials_hub' THEN 'Материалы (хаб)'
    WHEN 'subjects' THEN 'Предметы'
    WHEN 'profile' THEN 'Профиль'
    WHEN 'deadlines' THEN 'Дедлайны'
    WHEN 'friends' THEN 'Друзья'
    WHEN 'pomodoro' THEN 'Помодоро'
    WHEN '' THEN 'Не указано'
    ELSE properties->>'screen'
  END AS "Раздел",
  count(*) AS "Сколько раз открыли"
FROM analytics_events
WHERE event_name = 'open_screen'
  AND created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Старт бота — новые и возвращающиеся (по дням)
-- Метрика: по событию bot_started — первый визит vs повторный /start.
-- График: Комбо или Линия — «Данные»: Ось абсцисс «Дата»; на оси ординат — «Первый раз зашли», «Уже были (повторный /start)» (при желании + «Всего нажатий /start»). Тренд — отдельный вопрос на одну колонку.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(*) FILTER (WHERE coalesce((properties->>'is_new_user')::boolean, false)) AS "Первый раз зашли",
  count(*) FILTER (WHERE NOT coalesce((properties->>'is_new_user')::boolean, false)) AS "Уже были (повторный /start)",
  count(*) AS "Всего нажатий /start"
FROM analytics_events
WHERE event_name = 'bot_started'
  AND created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Главное меню — зашли по инвайту или нет
-- Метрика: за 30 дней, сколько показов меню после ссылки друга vs обычный вход.
-- График: Пирог или Строка (в результате две строки — наглядна доля).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH t AS (
  SELECT coalesce((properties->>'from_invite')::boolean, false) AS по_инвайту
  FROM analytics_events
  WHERE event_name = 'main_menu_shown'
    AND created_at >= now() - interval '30 days'
)
SELECT 'Перешли по ссылке друга (инвайт)' AS "Тип входа", count(*) AS "Сколько раз показали меню"
FROM t WHERE по_инвайту
UNION ALL
SELECT 'Без ссылки друга', count(*) FROM t WHERE NOT по_инвайту;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Откуда пришли пользователи (канал в ссылке /start)
-- Метрика: распределение по полю acquisition_ref (если колонки нет — обнови бота/миграции).
-- График: Строка — «Данные»: «Канал / метка» и «Пользователей».
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  coalesce(acquisition_ref, 'Канал не зафиксирован') AS "Канал / метка",
  count(*) AS "Пользователей"
FROM users
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Подписка Premium — сколько сейчас активно
-- Метрика: активная подписка (срок не истёк) и доля от всех.
-- График: Таблица (одна строка, несколько колонок). Отдельные KPI — отдельные вопросы с типом Число.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  count(*) FILTER (WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at > now()) AS "Сейчас с активной подпиской",
  count(*) AS "Всего пользователей в базе",
  round(
    100.0 * count(*) FILTER (WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at > now())
    / nullif(count(*), 0),
    1
  ) AS "Доля с подпиской, %"
FROM users;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Оплаты подписки за 30 дней (Telegram Stars)
-- Метрика: число оплат и сумма Stars по событиям subscription_paid.
-- График: Таблица. Только «всего Stars» — можно Число (отдельный упрощённый запрос).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  count(*) AS "Число оплат",
  coalesce(sum((properties->>'total_amount')::bigint), 0) AS "Сумма Stars за период",
  max(properties->>'currency') AS "Валюта (как в событии)"
FROM analytics_events
WHERE event_name = 'subscription_paid'
  AND created_at >= now() - interval '30 days';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Средний чек платящих за 30 дней (Stars на пользователя)
-- Метрика: среди тех, кто платил — средняя сумма Stars на человека.
-- График: Таблица (одна строка, три колонки). Либо три отдельных вопроса с типом Число.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH pay AS (
  SELECT
    user_telegram_id,
    sum((properties->>'total_amount')::bigint) AS stars
  FROM analytics_events
  WHERE event_name = 'subscription_paid'
    AND created_at >= now() - interval '30 days'
    AND user_telegram_id IS NOT NULL
  GROUP BY 1
)
SELECT
  count(*) AS "Платящих пользователей",
  sum(stars) AS "Всего Stars",
  round(sum(stars)::numeric / nullif(count(*), 0), 2) AS "В среднем Stars на платящего"
FROM pay;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Генерация тестов за 30 дней — сколько и сколько вопросов в среднем
-- Метрика: события quiz_generated.
-- График: Таблица (одна строка). Либо два отдельных вопроса с типом Число.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  count(*) AS "Сколько раз сгенерировали тест",
  round(avg((properties->>'question_count')::numeric), 1) AS "Среднее число вопросов в генерации"
FROM analytics_events
WHERE event_name = 'quiz_generated'
  AND created_at >= now() - interval '30 days';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Генерация тестов — по всему предмету или по одному файлу
-- Метрика: поле kind в событии quiz_generated.
-- График: Пирог или Гистограмма — «Данные»: Ось абсцисс «Тип генерации», Ось ординат «Сколько раз».
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  CASE coalesce(properties->>'kind', '')
    WHEN 'subject' THEN 'По всему предмету'
    WHEN 'file' THEN 'По одному файлу'
    WHEN '' THEN 'Не указано'
    ELSE properties->>'kind'
  END AS "Тип генерации",
  count(*) AS "Сколько раз"
FROM analytics_events
WHERE event_name = 'quiz_generated'
  AND created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Прохождение тестов — сдали или нет (30 дней)
-- Метрика: событие quiz_session_completed; средние правильные/неправильные ответы.
-- График: Пирог по «Результат» (доли); полная строка с средними — Таблица.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  CASE WHEN coalesce((properties->>'passed')::boolean, false) THEN 'Тест пройден (зачёт)'
       ELSE 'Тест не пройден'
  END AS "Результат",
  count(*) AS "Сколько сессий",
  round(avg((properties->>'correct_answers')::numeric), 1) AS "Среднее верных ответов",
  round(avg((properties->>'wrong_answers')::numeric), 1) AS "Среднее неверных ответов"
FROM analytics_events
WHERE event_name = 'quiz_session_completed'
  AND created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Новые материалы по дням
-- Метрика: строки в таблице materials.
-- График: Линия / Область / Гистограмма — «Данные»: Ось абсцисс «Дата», Ось ординат «Добавлено материалов». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(*) AS "Добавлено материалов"
FROM materials
WHERE created_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Сохранение материала — новая папка или существующая
-- Метрика: событие material_saved, флаг new_subject.
-- График: Пирог или Гистограмма — «Данные»: Ось абсцисс «Как сохраняли», Ось ординат «Сколько раз».
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  CASE WHEN coalesce((properties->>'new_subject')::boolean, false) THEN 'Создали новую папку (предмет)'
       ELSE 'Добавили в уже существующую папку'
  END AS "Как сохраняли",
  count(*) AS "Сколько раз"
FROM analytics_events
WHERE event_name = 'material_saved'
  AND created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Новые дедлайны по дням
-- Метрика: записи в таблице deadlines.
-- График: Линия или Гистограмма — «Данные»: Ось абсцисс «Дата», Ось ординат «Создано дедлайнов». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(*) AS "Создано дедлайнов"
FROM deadlines
WHERE created_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Дедлайн привязан к предмету или без предмета
-- Метрика: событие deadline_created.
-- График: Пирог или Строка — «Данные»: «Тип дедлайна» и «Сколько раз».
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  CASE WHEN coalesce((properties->>'has_subject_id')::boolean, false) THEN 'С привязкой к предмету'
       ELSE 'Без привязки к предмету'
  END AS "Тип дедлайна",
  count(*) AS "Сколько раз"
FROM analytics_events
WHERE event_name = 'deadline_created'
  AND created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Новые предметы (папки) по дням
-- Метрика: таблица subjects.
-- График: Линия или Гистограмма — «Данные»: Ось абсцисс «Дата», Ось ординат «Создано предметов (папок)». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(*) AS "Создано предметов (папок)"
FROM subjects
WHERE created_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Новые дружбы по дням
-- Метрика: таблица friendships.
-- График: Линия или Гистограмма — «Данные»: Ось абсцисс «Дата», Ось ординат «Новых пар дружбы». Тренд — плитка последнего периода + сравнение; вкладки «Оси» нет.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS "Дата",
  count(*) AS "Новых пар дружбы"
FROM friendships
WHERE created_at >= now() - interval '90 days'
GROUP BY 1
ORDER BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Воронка — сколько людей дошло до каждого шага (всё время)
-- Метрика: уникальные пользователи, у которых когда-либо было событие (накопительно).
-- График: Воронка (этапы по убыванию). Альт.: Строка — «Этап» и «Пользователей».
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT * FROM (
  SELECT 1 AS ord, 'Все зарегистрированные' AS "Этап", (SELECT count(*)::bigint FROM users) AS "Пользователей"
  UNION ALL
  SELECT 2, 'Видели главное меню', (SELECT count(DISTINCT user_telegram_id) FROM analytics_events WHERE event_name = 'main_menu_shown' AND user_telegram_id IS NOT NULL)
  UNION ALL
  SELECT 3, 'Сохраняли материал', (SELECT count(DISTINCT user_telegram_id) FROM analytics_events WHERE event_name = 'material_saved' AND user_telegram_id IS NOT NULL)
  UNION ALL
  SELECT 4, 'Создавали дедлайн', (SELECT count(DISTINCT user_telegram_id) FROM analytics_events WHERE event_name = 'deadline_created' AND user_telegram_id IS NOT NULL)
  UNION ALL
  SELECT 5, 'Генерировали тест', (SELECT count(DISTINCT user_telegram_id) FROM analytics_events WHERE event_name = 'quiz_generated' AND user_telegram_id IS NOT NULL)
  UNION ALL
  SELECT 6, 'Завершали сессию теста', (SELECT count(DISTINCT user_telegram_id) FROM analytics_events WHERE event_name = 'quiz_session_completed' AND user_telegram_id IS NOT NULL)
  UNION ALL
  SELECT 7, 'Завершали работу в помодоро (событие)', (SELECT count(DISTINCT user_telegram_id) FROM analytics_events WHERE event_name = 'pomodoro_work_completed' AND user_telegram_id IS NOT NULL)
  UNION ALL
  SELECT 8, 'Есть лог завершённого помодоро', (SELECT count(DISTINCT user_telegram_id) FROM pomodoro_session_logs)
) x
ORDER BY ord;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Удержание D1 / D7 / D30 по когортам регистрации
-- Метрика: % пользователей, у кого был любой ивент ровно на 1-й, 7-й и 30-й день после даты регистрации (UTC).
-- График: Таблица (когорты — строки). Динамика во времени — отдельный запрос + Линия («Данные»: Ось абсцисс — дата, Ось ординат — метрика).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH regs AS (
  SELECT
    telegram_id,
    (created_at AT TIME ZONE 'UTC')::date AS reg_date
  FROM users
  WHERE created_at >= now() - interval '120 days'
),
act AS (
  SELECT DISTINCT
    user_telegram_id,
    (created_at AT TIME ZONE 'UTC')::date AS d
  FROM analytics_events
  WHERE user_telegram_id IS NOT NULL
)
SELECT
  r.reg_date AS "Дата регистрации (когорта)",
  count(*) AS "Размер когорты",
  round(
    100.0 * count(*) FILTER (
      WHERE EXISTS (
        SELECT 1 FROM act a
        WHERE a.user_telegram_id = r.telegram_id AND a.d = r.reg_date + 1
      )
    ) / nullif(count(*), 0),
    1
  ) AS "Вернулись на день 1, %",
  round(
    100.0 * count(*) FILTER (
      WHERE EXISTS (
        SELECT 1 FROM act a
        WHERE a.user_telegram_id = r.telegram_id AND a.d = r.reg_date + 7
      )
    ) / nullif(count(*), 0),
    1
  ) AS "Активны на день 7, %",
  round(
    100.0 * count(*) FILTER (
      WHERE EXISTS (
        SELECT 1 FROM act a
        WHERE a.user_telegram_id = r.telegram_id AND a.d = r.reg_date + 30
      )
    ) / nullif(count(*), 0),
    1
  ) AS "Активны на день 30, %"
FROM regs r
GROUP BY r.reg_date
ORDER BY r.reg_date;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: До первого сохранения материала — сколько часов ждали
-- Метрика: только у тех, у кого вообще было material_saved; среднее и медиана часов от регистрации.
-- График: Таблица (два числа в одной строке). Либо два вопроса с типом Число.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH first_mat AS (
  SELECT user_telegram_id, min(created_at) AS first_at
  FROM analytics_events
  WHERE event_name = 'material_saved'
    AND user_telegram_id IS NOT NULL
  GROUP BY 1
)
SELECT
  round(
    avg(extract(epoch from (f.first_at - u.created_at)) / 3600.0)::numeric,
    1
  ) AS "Среднее часов до первого материала",
  round(
    (percentile_cont(0.5) WITHIN GROUP (
      ORDER BY extract(epoch from (f.first_at - u.created_at)) / 3600.0
    ))::numeric,
    1
  ) AS "Медиана часов"
FROM users u
JOIN first_mat f ON f.user_telegram_id = u.telegram_id
WHERE u.created_at IS NOT NULL;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: В первый день после регистрации — какие события были
-- Метрика: в календарный день регистрации (UTC), какие event_name встречались.
-- График: Строка — «Данные»: «Событие в первый день» и «Сколько раз».
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH regs AS (
  SELECT
    telegram_id,
    (created_at AT TIME ZONE 'UTC')::date AS reg_date
  FROM users
)
SELECT
  CASE e.event_name
    WHEN 'bot_started' THEN 'Старт бота (/start)'
    WHEN 'main_menu_shown' THEN 'Главное меню показано'
    WHEN 'open_screen' THEN 'Открыт раздел меню'
    WHEN 'material_saved' THEN 'Материал сохранён'
    WHEN 'deadline_created' THEN 'Дедлайн создан'
    WHEN 'pomodoro_work_completed' THEN 'Помодоро: работа завершена'
    WHEN 'quiz_generated' THEN 'Тест сгенерирован'
    WHEN 'quiz_session_completed' THEN 'Тест пройден (сессия)'
    WHEN 'subscription_paid' THEN 'Оплата подписки'
    ELSE e.event_name
  END AS "Событие в первый день",
  count(*) AS "Сколько раз"
FROM analytics_events e
JOIN regs r ON r.telegram_id = e.user_telegram_id
WHERE e.user_telegram_id IS NOT NULL
  AND (e.created_at AT TIME ZONE 'UTC')::date = r.reg_date
GROUP BY 1
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Активность по пользователям за 28 дней (сырые ряды)
-- Метрика: сколько событий каждого типа на user_id — для выгрузки / сегментации.
-- График: Таблица (сырая выгрузка по пользователям; для дашборда обычно не нужна).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT
  user_telegram_id AS "ID в Telegram",
  count(*) FILTER (WHERE event_name = 'pomodoro_work_completed') AS "Помодоро (события)",
  count(*) FILTER (WHERE event_name = 'quiz_session_completed') AS "Тесты завершены",
  count(*) FILTER (WHERE event_name = 'material_saved') AS "Материалы сохранены",
  count(*) AS "Всего событий за 28 дней"
FROM analytics_events
WHERE created_at >= now() - interval '28 days'
  AND user_telegram_id IS NOT NULL
GROUP BY 1;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: «Отвалились» за 2 недели (грубая оценка)
-- Метрика: были активны в окне 28–15 дней назад, но не было событий в последние 14 дней.
-- График: Число.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH active_old AS (
  SELECT DISTINCT user_telegram_id
  FROM analytics_events
  WHERE created_at >= now() - interval '28 days'
    AND created_at < now() - interval '14 days'
    AND user_telegram_id IS NOT NULL
),
active_recent AS (
  SELECT DISTINCT user_telegram_id
  FROM analytics_events
  WHERE created_at >= now() - interval '14 days'
    AND user_telegram_id IS NOT NULL
)
SELECT count(*) AS "Пользователей без активности последние 14 дней (но были раньше)"
FROM active_old o
WHERE NOT EXISTS (
  SELECT 1 FROM active_recent r WHERE r.user_telegram_id = o.user_telegram_id
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Удержание на 7-й день по каналу привлечения
-- Метрика: среди зарегистрированных за 90 дней — % с активностью ровно на день +7.
-- График: Строка — «Данные»: «Канал» + «Активны на день 7, %» (или «Зарегистрировалось» для объёма когорты).
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH regs AS (
  SELECT
    telegram_id,
    coalesce(acquisition_ref, 'Канал не зафиксирован') AS ref,
    (created_at AT TIME ZONE 'UTC')::date AS reg_date
  FROM users
  WHERE created_at >= now() - interval '90 days'
),
act AS (
  SELECT DISTINCT user_telegram_id, (created_at AT TIME ZONE 'UTC')::date AS d
  FROM analytics_events
  WHERE user_telegram_id IS NOT NULL
)
SELECT
  r.ref AS "Канал",
  count(*) AS "Зарегистрировалось",
  round(
    100.0 * count(*) FILTER (
      WHERE EXISTS (
        SELECT 1 FROM act a
        WHERE a.user_telegram_id = r.telegram_id AND a.d = r.reg_date + 7
      )
    ) / nullif(count(*), 0),
    1
  ) AS "Активны на день 7, %"
FROM regs r
GROUP BY r.ref
ORDER BY 2 DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Поле last_activity_date = сегодня (UTC)
-- Метрика: только если бот реально обновляет last_activity_date.
-- График: Число.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT count(*) AS "Пользователей с отметкой активности «сегодня» (UTC)"
FROM users
WHERE last_activity_date = (now() AT TIME ZONE 'UTC')::date;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Сохранить как: Конверсия «сгенерировали тест → прошли сессию» за 7 дней
-- Метрика: у кого за неделю было quiz_generated, сколько из них же имели quiz_session_completed.
-- График: Таблица (одна строка). Либо отдельные вопросы с типом Число на каждый показатель.
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITH gen AS (
  SELECT DISTINCT user_telegram_id
  FROM analytics_events
  WHERE event_name = 'quiz_generated'
    AND created_at >= now() - interval '7 days'
    AND user_telegram_id IS NOT NULL
),
done AS (
  SELECT DISTINCT user_telegram_id
  FROM analytics_events
  WHERE event_name = 'quiz_session_completed'
    AND created_at >= now() - interval '7 days'
    AND user_telegram_id IS NOT NULL
)
SELECT
  (SELECT count(*) FROM gen) AS "Генерировали тест (уникальных, 7 дней)",
  (SELECT count(*) FROM gen g WHERE EXISTS (SELECT 1 FROM done d WHERE d.user_telegram_id = g.user_telegram_id)) AS "Из них же проходили тест (7 дней)",
  round(
    100.0 * (SELECT count(*) FROM gen g WHERE EXISTS (SELECT 1 FROM done d WHERE d.user_telegram_id = g.user_telegram_id))
    / nullif((SELECT count(*) FROM gen), 0),
    1
  ) AS "Конверсия, %";
