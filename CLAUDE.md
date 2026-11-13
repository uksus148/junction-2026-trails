# GOPSTOP.PROTOCOL — Junction 2026

AI-навигатор: пользователь пишет в чат или отмечает на карте, что хочет увидеть (замки, водопады, виды),
и получает пешеходный маршрут A→B через эти места с реальными фото видов по пути и ссылками на источники.

Этот файл — единый источник правды для команды и для AI-ассистентов. Обновляем его при каждом решении.

## Челленджи (черновик подан 13.11 23:59)
- **Main:** The Internet Butler / Your Personal Assistant — **Exa**. Судят: использование Exa для данных, которых нет в обучении модели;
  польза конкретной группе (хайкеры/туристы); видимые источники; оригинальность; демо работает на **живых запросах судей**.
- **Tech:** Best Use of **Aiven**. Meaningful use 40% / техника 30% / влияние на продукт 20% / креатив 10%.
- Опционально: Cloudinary (отдельная форма https://cld.media/hackathon-survey) — если загрузка фото пойдёт через него.

## Правила Junction (важное)
- Весь код пишется на хакатоне (старт 13.11 19:30). Репозиторий **публичный**, лицензия **MIT**.
- **Final Submission: вс 15.11 10:00** — перевести Draft → Final. Опозданий не принимают.
- Видео-питч **строго ≤ 2:00**, публичная ссылка (YouTube/Vimeo). Pitch deck PDF.
- **Вс 10:30–13:00 peer review — все трое на площадке**, иначе нет права на главный приз.
- Топ-5: питч 3 мин + 3 мин вопросов.

## Бюджет: ничего не покупаем
| Нужно | Берём | Цена для нас |
|---|---|---|
| Веб-поиск мест/фото | **Exa** $50 × 3 = $150 | бесплатно (кредиты) |
| LLM агента | **Claude** $20 × 3 (`claude-haiku-5-5` по умолчанию, `claude-sonnet-5-5` только для планировщика) | кредиты |
| Эмбеддинги | **Gemini API** (бесплатные кредиты/free tier) | бесплатно |
| Помощь в кодинге | Codex $100, Claude Code | кредиты |
| БД | **Aiven PostgreSQL** free plan (проверить pgvector+PostGIS в консоли) | бесплатно |
| Кэш | **Aiven Valkey** free plan | бесплатно |
| Очередь событий | **Aiven Kafka** — за кредиты $50, минимальный план, выключать когда не нужен | кредиты |
| Наблюдаемость (stretch) | Aiven ClickHouse — только если останутся кредиты | кредиты |
| Карта | MapLibre GL + OpenFreeMap тайлы (без ключа) | бесплатно |
| Точки интереса | OSM Overpass API (`historic=castle`, `waterway=waterfall`, `tourism=viewpoint`, `natural=peak`) | бесплатно |
| Пешеходный роутинг | OpenRouteService `foot-hiking` (free key, ~2000 запросов/день) | бесплатно |
| Фото | Wikimedia Commons API, Mapillary (free token), Exa; загрузки пользователей — Cloudinary free tier | бесплатно |
| Хостинг API/агента | Aiven Runtime (если хватает кредитов) → запасной Modal $100 | кредиты |
| Хостинг фронта | Cloudflare Pages / Vercel free | бесплатно |

**Не используем:** Oxylabs (нужна карта и подписка), платные плагины генерации видео, Verda/Featherless GPU (не нужны).
**Экономия:** каждый ответ Exa и роутинга кэшируем в Valkey (ключ = хэш запроса, TTL 24ч). Во время разработки — фикстуры, а не живые вызовы.

## Архитектура
```
frontend (React+Vite+Tailwind+MapLibre)
   │ REST
   ├──► api (Spring Boot, Java)        — места, маршруты, загрузки, PostGIS-запросы, роутинг ORS
   │       │ Kafka: photo.uploaded, route.requested
   └──► agent (FastAPI, Python)        — чат, извлечение намерений LLM, Exa-поиск, эмбеддинги, фото-пайплайн
           │
   Aiven PostgreSQL (PostGIS + pgvector) · Aiven Valkey (кэш, сессии чата) · Aiven Kafka
```

### Демо-сценарий (единственный, который обязан работать идеально)
Высокие Татры: «Хочу из Штрбске Плесо подняться на Рысы и по пути увидеть водопад Скок, люблю дикие виды».
→ агент находит Скок и Рысы → маршрут через них → на карте трек + точки + фото каждого участка с источниками.
Плюс судья вводит свой запрос — должно отработать (регион не хардкодим, но Татры тестируем глубже всего).

### Контракт API (меняется только по договорённости, правки фиксировать здесь)
- `POST /api/chat` `{sessionId, message}` → `{reply, places:[Place], routeId?}` (agent)
- `GET /api/places?bbox=minLon,minLat,maxLon,maxLat&tags=castle,waterfall` → `[Place]` (api)
- `POST /api/places` `{name, lat, lon, tags[]}` — ручное добавление (api)
- `POST /api/routes` `{start:{lat,lon}, end:{lat,lon}, placeIds[], preferences[]}` → `Route` (api)
- `GET /api/routes/{id}` → `Route`
- `POST /api/photos` multipart `{file, lat, lon}` → кладёт в Kafka `photo.uploaded`
- `Place = {id, name, lat, lon, tags[], photos:[Photo], source}`
- `Photo = {url, thumbUrl, author, license, sourceUrl, lat, lon}`
- `Route = {id, geojson(LineString), distanceKm, ascentM, durationMin, places:[Place], segments:[{fromKm,toKm,photos:[Photo]}]}`

### Структура репозитория
```
/frontend   — Даниил
/api        — Мурат
/agent      — Мухамед
/infra      — docker-compose для локалки, SQL-миграции, .env.example
```
Секреты только в `.env` (в .gitignore). В репо — `.env.example`.

## Команда и задачи

### Мурат — backend (Java + Spring Boot, SQL, Docker, тесты)
1. Монорепо, `.gitignore`, `.env.example`, `docker-compose` (локальный Postgres+PostGIS для разработки)
2. Создать Aiven PostgreSQL (free), включить `postgis`, `vector`. Схема: `places`, `photos`, `routes`, `route_places`
3. Spring Boot: `/api/places` (bbox + теги через PostGIS), `/api/routes` (вызов ORS foot-hiking через waypoint'ы, сохранение)
4. Импорт POI региона Татр из Overpass в `places` (одноразовый скрипт)
5. «Фото вдоль маршрута»: `ST_DWithin(photo.geom, route.geom, 300м)` → нарезка по сегментам
6. Kafka producer `photo.uploaded`; Valkey-кэш ответов ORS
7. Тесты на PostGIS-запросы, деплой

### Мухамед — AI-агент (Python, LLM, RAG)
1. FastAPI сервис `/api/chat`, сессии в Valkey
2. Извлечение намерений: свободный текст → `{start, end, mustSee[], preferences[]}` (Claude tool use / structured output)
3. Exa: поиск места по описанию («водопад из TikTok у Штрбске Плесо»), поиск фото и описаний троп; **всегда сохранять sourceUrl**
4. Геокодинг найденного (Nominatim/OSM) → `Place`
5. Эмбеддинги (Gemini) мест и подписей фото → pgvector; ранжирование «что пользователю понравится»
6. Kafka consumer `photo.uploaded`: EXIF-геотег → эмбеддинг → привязка к ближайшей тропе
7. Кэш Exa в Valkey. Пойти на воркшоп Exa (сб 16:30, Loft 4 этаж)

### Даниил — frontend + продукт/питч (React, Tailwind)
1. Vite + React + Tailwind, MapLibre с OpenFreeMap
2. Экран: карта + боковая панель (чат | ручное добавление мест)
3. Отрисовка маршрута (GeoJSON), маркеры мест, клик → фото + источник
4. Лента «что увидишь по пути» по сегментам маршрута (горизонтальная галерея, синхронна с картой)
5. Загрузка своего фото
6. Пока бэкенды не готовы — работать на моках по контракту выше
7. Деплой фронта; 2-минутное видео, pitch deck PDF, финальный текст сабмита

## Таймлайн
| Когда | Цель |
|---|---|
| Пт/Сб 00:00–03:00 | Кредиты получены (Exa, Claude, Gemini, Aiven), репо создано, Aiven-сервисы подняты, скелеты 3 сервисов, моки |
| Сб 03:00–09:00 | Сон по сменам (минимум 4–5 ч каждому) |
| **Сб 12:00** | **Сквозной MVP:** чат → места → маршрут на карте (пусть без фото) |
| Сб 12:00–20:00 | Фото вдоль маршрута, загрузки + Kafka, кэш, ручное добавление |
| Сб 16:30 | Воркшоп Exa (Мухамед, по возможности все) |
| Сб 20:00–02:00 | Деплой на публичный URL, полировка демо-сценария, stretch (ClickHouse) |
| Вс 02:00–07:00 | **Фичфриз.** Видео ≤2:00, deck PDF, описание, README |
| **Вс 09:30** | **Submit Final** (дедлайн 10:00) |
| Вс 10:30 | Peer review — все на месте |

## Инструменты для Claude Code
- MCP: `context7` (доки библиотек) — уже подключён. Добавить **Exa MCP** и **Aiven MCP** (https://aiven.io/docs/tools/mcp-server):
  ```
  claude mcp add --transport http exa https://mcp.exa.ai/mcp
  ```
- Скиллы по ролям:
  - Мурат: `ecc:springboot-patterns`, `ecc:springboot-tdd`, `ecc:postgres-patterns`, `ecc:docker-patterns`, `ecc:java-reviewer` (агент)
  - Мухамед: `ecc:fastapi-patterns`, `ecc:exa-search`, `claude-api`, `ecc:rag-pipeline-reviewer` (агент), `ecc:redis-patterns` (Valkey совместим)
  - Даниил: `ecc:react-patterns`, `impeccable` / `ecc:frontend-design-direction` (UI), `ecc:frontend-slides` или `anthropic-skills:pptx` (deck), `ecc:remotion-video-creation` (видео)
  - Все: `ecc:api-design`, `code-review`, `ecc:security-review` перед финалом (нет ли ключей в репо)

## Журнал решений
- 13.11 — Main: Exa Internet Butler; Tech: Aiven. Причина: продукт = агент, делающий нудный ресёрч по живому вебу с источниками.
- 13.11 — Ничего не покупаем: только партнёрские кредиты и free tier (таблица бюджета выше).
- 13.11 — Один регион для демо (Высокие Татры), но без хардкода, чтобы проходили запросы судей.
- 13.11 — Два бэкенда по стеку команды: Spring Boot (данные/гео) + FastAPI (агент). Общаются через БД и Kafka, фронт ходит в оба.

- 14.11 — Локальная БД и CI используют PostgreSQL 18 с PostGIS и pgvector. Порт задаётся POSTGRES_PORT. Docker init включает только расширения, таблицы создаются миграциями Flyway в api. CI запускается в PR при изменениях infra/**. Проверено локально и в GitHub Actions, PR #1.

## Открытые вопросы
- [x] PostGIS и pgvector доступны на Aiven PostgreSQL Free. 14.11 проверено SQL на сервисе junction: PostgreSQL 18.7, postgis 3.6.4, vector 0.8.7. Оба расширения включены, геозапрос и расстояние между векторами проверены.
- [ ] Цена Aiven Runtime в кредитах → решить, где хостим API/агент
- [ ] Лицензии фото: показываем только с автором и ссылкой; TikTok не скрейпим — пользователь вставляет ссылку/описание, ищем через Exa
