# Локальная база для разработки

PostgreSQL 18 с PostGIS и pgvector соответствует основной версии тарифа Free в консоли Aiven. Для запуска нужны Docker с Compose и свободный порт на компьютере.

Из корня репозитория один раз скопируйте `.env.example` в `.env` и задайте `POSTGRES_PASSWORD`. Если порт 5432 занят, измените `POSTGRES_PORT` в `.env`. Этот же порт используется в `SPRING_DATASOURCE_URL` для API на хосте.

```sh
docker compose --env-file .env -f infra/compose.yaml up --build --wait
docker compose --env-file .env -f infra/compose.yaml exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < infra/smoke.sql
```

Проверка выполняет геозапрос и сравнивает два вектора. Она завершится с ошибкой, если начальная настройка пропустила расширение или результат вычисления неверен. Тот же SQL выполняется в GitHub Actions при изменениях в `infra/`.

```sh
docker compose --env-file .env -f infra/compose.yaml down
```

Данные остаются в именованном томе между запусками. При первом запуске на пустом томе PostgreSQL включает `postgis` и `vector`. Таблицы приложения создаются миграциями Flyway в модуле `api/` по мере его разработки.
