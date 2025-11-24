![GithubCI](https://github.com/SergTyapkin/velo-marshals-backend/actions/workflows/deployMain.yml/badge.svg)

# Velo Marshals Backend
Бэкенд для сайта веломаршалов московских велофестивалей
[Репозиторий фронтенда с картинками](https://github.com/SergTyapkin/velo-marshals-frontend)

Используемые технологии:

> - Flask
> - Flask-mail
> - GeoIp2
> - Postgres + Psycopg2
> - Docker

---

## Запуск с Docker через Makefile _(в прод)_
### Настройка всего окружения и запуск контейнеров
```shell
make all
```
#### Полный список действий скриптов в `make all`

1. Устанавливает `docker`, если его ещё нет
2. Добавляет текущего пользователя в группу `Docker`, чтобы запускать его без `sudo`
3. Предлагает настроить `.env` файл
4. Создаёт пару SSH ключей, публичный добавляет в `~/.ssh/authorized_keys`, приватный выводит в консоль, его нужно добавить как секретную переменную среды `SSH_DEPLOY_KEY` в настройках Github.
5. Собирает приложение из последнего коммита в ветку, указанную в `.env` файле, запускает финальный docker-контейнер с ним.
6. Показывает остальеые переменные, которые необходимо установить в настройках GitHub для настройки CI/CD.

### Для управления контейнерами, когда это необходимо, используйте команды:
```shell
make run
```
```shell
make down
```
```shell
make build
```

> [!NOTE]
> Документация будет доступна по адресу [http:\\\127.0.0.1:9000\docs](http:\\127.0.0.1:9000\docs)

---

## Запуск без Docker _(локально)_:
### Virtualenv
```shell
python -m venv venv
```
- Linux / MacOS
```shell
venv/bin/activate
```
- Windows
```shell
python venv\Scripts\activate
```

### Установка poetry (не обязательно)
```shell
pip install poetry
```
### Установка зависимостей
```shell
poetry install
```
или
```shell
pip install -r requirements.txt
```

### База данных
В файл `.env` прописать свои настройки Postgres

### Старт
```shell
python main.py
```

### Перейти по адресу
```shell
http:\\127.0.0.1:8000\docs
```
