# GOPSTOP.PROTOCOL — бриф команды (Junction 2026)

> Прочитай целиком, это 5 минут. Здесь всё, что нужно знать, чтобы мы делали одно и то же.
> Полная версия плана лежит в `CLAUDE.md` в корне репозитория. Её же читает Claude Code, так что вайбкодим по одному плану.

---

## 1. Что делаем (одним абзацем)

AI-навигатор для пеших маршрутов. Человек пишет в чат свободным текстом
(«хочу из Штрбске Плесо подняться на Рысы и по пути увидеть водопад из TikTok»)
или отмечает места на карте. Приложение находит эти места в интернете, строит маршрут A→B через них
и показывает **реальные фото видов, которые встретятся по пути**, со ссылкой на источник каждой фотографии.

**Какую проблему решаем:** люди часами сидят во вкладках и блогах, пока собирают маршрут к тому, что хотят увидеть.

---

## 2. Где участвуем

| | Челлендж | Что важно судьям |
|---|---|---|
| **Основной** | **The Internet Butler / Your Personal Assistant** (Exa) | Exa даёт данные, которых нет в обучении модели; у всего видны источники; демо работает на **живых запросах судей** |
| **Дополнительный** | **Best Use of Aiven** | Сервисы Aiven осмысленно используются (40%), техника (30%), влияние на продукт (20%), креатив (10%) |

Черновик проекта уже подан. Остальные вступают в команду на платформе по коду команды.

---

## 3. Правила, нарушать нельзя

- ⏰ **Финальная сдача: воскресенье 15.11, 10:00.** Сдаём в **09:30**. Опоздание = дисквалификация.
- 🎥 Видео-питч **не длиннее 2:00** (режут строго), публичная ссылка на YouTube.
- 📄 Pitch deck в PDF.
- 👥 **Вс 10:30–13:00 peer review: все трое на площадке.** Если кого-то нет, теряем право на главный приз.
- 💻 Весь код пишется на хакатоне. Репозиторий **публичный**, лицензия MIT.
- 🔑 **Никаких ключей в git.** Только в `.env`, он в `.gitignore`. В репо лежит `.env.example`.

---

## 4. Деньги: ничего не покупаем

Карту никуда не вводим. Работаем только на кредитах партнёров и бесплатных тарифах.

| Для чего | Используем |
|---|---|
| Поиск мест, фото, описаний троп | **Exa**, $50 на каждого. **Каждый забирает свои кредиты** |
| LLM агента | **Claude**, $20 на каждого (модель `claude-haiku-5-5`, для сложного шага `claude-sonnet-5-5`) |
| Эмбеддинги | **Gemini API**, бесплатные кредиты |
| Кодинг | Claude Code, Codex ($100 на каждого) |
| База данных | **Aiven PostgreSQL**, бесплатный план |
| Кэш | **Aiven Valkey**, бесплатный план |
| События | **Aiven Kafka**, за кредиты Aiven ($50), минимальный план |
| Карта | MapLibre + OpenFreeMap (без ключа) |
| Точки интереса | OpenStreetMap Overpass API |
| Пешеходный маршрут | OpenRouteService, профиль `foot-hiking` (бесплатный ключ) |
| Фото | Wikimedia Commons, Mapillary, Exa; загрузки пользователей через Cloudinary (free) |

❌ **Не используем:** Oxylabs (требует карту), платные AI-генераторы видео, GPU-облака (не нужны).

💡 **Экономим кредиты:** любой ответ Exa или роутинга кэшируем в Valkey. Во время разработки работаем на сохранённых
JSON-фикстурах, живые запросы шлём только когда проверяем.

---

## 5. Архитектура

```
         ┌──────────── frontend (React + Vite + Tailwind + MapLibre) ────────────┐
         │                                                                       │
         ▼                                                                       ▼
   api (Spring Boot)                                                  agent (FastAPI, Python)
   места, маршруты, загрузки фото,                                    чат, понимание запроса (LLM),
   гео-запросы PostGIS, роутинг                                       поиск через Exa, эмбеддинги
         │                                                                       │
         └───────────────► Aiven PostgreSQL (PostGIS + pgvector) ◄───────────────┘
                           Aiven Valkey (кэш, сессии чата)
                           Aiven Kafka (photo.uploaded → обработка фото агентом)
```

**Репозиторий:**
```
/frontend   — Даниил
/api        — Мурат
/agent      — Мухамед
/infra      — docker-compose, SQL-миграции, .env.example
```

---

## 6. Контракт API (договорились: меняем только вместе)

Контракт нужен, чтобы каждый работал независимо. Фронт сидит на моках, пока бэкенды не готовы.

| Метод | Кто | Запрос → Ответ |
|---|---|---|
| `POST /api/chat` | agent | `{sessionId, message, mode, preferences}` → `{reply, places:[Place], mode, routeId?, itineraryId?, preferencesPatch?}` |
| `GET /api/places?bbox=minLon,minLat,maxLon,maxLat&tags=castle,waterfall` | api | → `[Place]` |
| `POST /api/places` | api | `{name, lat, lon, tags[]}` → `Place` (ручное добавление) |
| `POST /api/routes` | api | `{start:{lat,lon}, end:{lat,lon}, placeIds[], preferences[]}` → `Route` |
| `GET /api/routes/{id}` | api | → `Route` |
| `POST /api/photos` | api | multipart `{file, lat, lon}` → событие в Kafka `photo.uploaded` |
| `POST /api/itineraries` | api | `{start, placeIds[], preferences, startTime, endTime}` → `Itinerary` (план на день) |
| `GET /api/itineraries/{id}` | api | → `Itinerary` |
| `POST /api/itineraries/{id}/replan` | api | `{now, location?, skipPlaceIds[], donePlaceIds[], preferences?}` → `Itinerary` |

```
Place = {id, name, lat, lon, tags[], photos:[Photo], source,
         dwellMin?, priceLevel? (0-3), crowdLevel? (0-2), openingHours? {open, close}}
Photo = {url, thumbUrl, author, license, sourceUrl, lat, lon}
Route = {id, geojson (LineString), distanceKm, ascentM, durationMin,
         places:[Place], segments:[{fromKm, toKm, photos:[Photo]}]}

Preferences = {interests[], dislikes[], pace: relaxed|normal|intense,
               maxWalkKm, budget: 0-3, avoidCrowds}
Itinerary = {id, route, start, startTime, endTime, resumeAt, candidates:[Place], preferences,
             stops: [{place, arriveAt, leaveAt, travelMin, travelKm, travelMode: walk|transit,
                      status: planned|done|skipped}],
             dropped: [{place, reason: dislike|budget|closed|no_time|walk_limit|skipped_by_user}],
             walkKm}
```

### 6.1 Новые фичи (добавлены 14.11)
- **Персонализация:** вкладка «Me» (интересы, нелюбимое, темп, лимит ходьбы, бюджет, толпы). Агент также понимает это из текста и возвращает `preferencesPatch`.
- **План на день:** переключатель «Day plan» или фраза в чате («plan my day», «план на день»). Это расписание по времени, с часами работы и транспортом для длинных переходов.
- **Перестройка дня:** кнопки Done / Skip / Running late / Replan from now. Пересчитывается только остаток дня, на освободившееся время ставится другое место, а у выкинутых мест показана причина.
- **Эталонная логика уже написана** на фронте: `frontend/src/lib/planner.ts` (+ тесты). Бэкенд портирует её 1:1.

---

## 7. Кто что делает

### 🟦 Мурат: backend (Java, Spring Boot, SQL, Docker, тесты)
1. Публичный репозиторий на GitHub (MIT): структура папок, `.gitignore`, `.env.example`, docker-compose с локальным Postgres+PostGIS
2. Aiven PostgreSQL (бесплатный план): **проверить, ставятся ли расширения `postgis` и `vector`**, написать в чат
3. Схема БД: `places`, `photos`, `routes`, `route_places`
4. `GET /api/places`: поиск по области карты и тегам через PostGIS
5. `POST /api/routes`: вызов OpenRouteService `foot-hiking` через выбранные точки, сохранение маршрута
6. Импорт точек интереса Татр из Overpass (замки, водопады, смотровые, вершины)
7. «Фото вдоль маршрута»: фото в радиусе ~300 м от трека, разбивка по сегментам
8. Kafka producer `photo.uploaded`, кэш роутинга в Valkey, тесты, деплой
9. **Новое:** `/api/itineraries` (create / get / replan) — портировать `frontend/src/lib/planner.ts`, тесты повторить в JUnit

### 🟩 Мухамед: AI-агент (Python, LLM, RAG)
1. Сервис FastAPI `POST /api/chat`, история чата в Valkey
2. Разбор свободного текста → `{start, end, mustSee[], preferences[]}` (Claude, structured output)
3. Exa: найти место по описанию («водопад из TikTok у Штрбске Плесо»), найти фото и описания троп.
   **У каждого результата сохраняем `sourceUrl`**, судьи Exa на это смотрят
4. Геокодинг найденного через Nominatim/OSM → `Place`
5. Эмбеддинги (Gemini) мест и фото → pgvector, ранжирование «что понравится пользователю»
6. Kafka consumer `photo.uploaded`: геотег из EXIF → эмбеддинг → привязка к тропе
7. Кэш Exa в Valkey. **Сходить на воркшоп Exa: сб 16:30, Loft, 4 этаж**
8. **Новое:** в `/api/chat` определять `mode` (route/day) и возвращать `preferencesPatch` (эталон: `frontend/src/lib/intent.ts` + тесты).
   Через Exa добывать для мест `openingHours`, `priceLevel`, `crowdLevel`, `dwellMin`

### 🟧 Даниил: frontend + питч (React, Tailwind)
1. Vite + React + Tailwind, карта MapLibre
2. Экран: карта и боковая панель с вкладками «Чат» и «Добавить место»
3. Маршрут на карте, маркеры мест, по клику фото и ссылка на источник
4. Лента «Что увидишь по пути»: галерея по сегментам, синхронная с картой
5. Загрузка своего фото
6. Пока бэкенды не готовы, работаю на моках по контракту
7. Деплой фронта, видео 2:00, pitch deck PDF, финальный текст сабмита

---

## 8. Таймлайн

| Когда | Цель |
|---|---|
| **Сб до ~03:00** | Кредиты получены, репо создано, Aiven поднят, скелеты всех трёх сервисов |
| Сб 03:00–09:00 | Спим по очереди, **минимум 4–5 часов каждый** |
| **Сб 12:00** | ✅ **Сквозной MVP:** чат → места → маршрут на карте (можно пока без фото) |
| Сб 12:00–20:00 | Фото вдоль маршрута, загрузки через Kafka, кэш, ручное добавление мест |
| Сб 16:30 | Воркшоп Exa |
| Сб 20:00–02:00 | Деплой на публичный URL, полировка демо |
| **Вс 02:00** | 🧊 **Фичфриз.** Новых фич больше нет, только баги, видео, презентация, README |
| **Вс 09:30** | 🚀 **Submit Final** |
| Вс 10:30 | Peer review, все на месте |

---

## 9. Демо-сценарий (должен работать идеально)

> «Хочу из Штрбске Плесо подняться на Рысы и по пути увидеть водопад Скок, люблю дикие виды»

→ агент находит Скок и Рысы → маршрут через них → трек на карте, точки и фото каждого участка с источниками.

Регион в коде **не хардкодим**: судья может ввести свой запрос, и он тоже должен отработать.

---

## 10. Как работаем

- **Git:** каждый работает в своей папке и своей ветке (`front/...`, `api/...`, `agent/...`), мержим в `main` часто и маленькими кусками
- **Коммиты:** `feat: ...`, `fix: ...`, `chore: ...`
- **Claude Code:** запускать из корня репо, тогда он прочитает `CLAUDE.md` и будет знать весь план.
  Полезно подключить MCP Exa: `claude mcp add --transport http exa https://mcp.exa.ai/mcp`
- **Полезные скиллы Claude Code:**
  - Мурат: `ecc:springboot-patterns`, `ecc:springboot-tdd`, `ecc:postgres-patterns`, `ecc:docker-patterns`
  - Мухамед: `ecc:fastapi-patterns`, `ecc:exa-search`, `claude-api`, `ecc:redis-patterns`
  - Даниил: `ecc:react-patterns`, `impeccable`, `ecc:frontend-slides`, `ecc:remotion-video-creation`
  - Все перед финалом: `/code-review`, `/security-review` (нет ли ключей в репо)
- **Застрял больше чем на 30 минут?** Пиши в общий чат. Менторы Exa и Aiven весь уикенд на площадке, можно подойти.
- **Меняешь контракт API или принимаешь решение?** Напиши в чат, Даниил обновит `CLAUDE.md`.

---

## 11. Открытые вопросы

- [ ] Есть ли `postgis` и `vector` на бесплатном Aiven PostgreSQL? *(Мурат)*
- [ ] Сколько кредитов съедает Aiven Runtime? Там хостим API и агента или на Modal? *(Мурат)*
- [ ] TikTok не скрейпим: пользователь вставляет ссылку или описание, место ищем через Exa *(Мухамед)*
