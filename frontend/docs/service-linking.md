# Привязка аккаунтов сервисов — что ждёт фронтенд

Сейчас токены сервисов общие и лежат в настройках сервера. Фронтенд уже умеет привязывать личный аккаунт пользователя,
бэкенду нужно добавить эндпоинты ниже в роутер `app/api/services.py`. Все запросы — с `Authorization: Bearer <access>`.

Если у пользователя привязан свой аккаунт, поиск и плеер должны использовать его токен, иначе — общий серверный.

## `GET /api/services`

К каждому сервису добавить поле `linked`: привязан ли личный аккаунт пользователя.

```json
{ "code": "ЯМ", "name": "Яндекс Музыка", "shortName": "Яндекс", "service": "yandex", "online": true, "linked": false }
```

## `POST /api/services/{service}/link`

Начинает вход. Два вида:

- `device_code` — для Яндекса: бэкенд запрашивает код у `oauth.yandex.ru` (Device Flow, от имени приложения Яндекс Музыки, как делает библиотека `yandex-music`), пользователь открывает `url` и вводит `user_code`, бэкенд сам опрашивает Яндекс и сохраняет токен.
- `redirect` — для Spotify, SoundCloud, Google: обычный OAuth, `redirect_uri` ведёт на бэкенд, бэкенд меняет `code` на токен.

```json
{
  "session_id": "b6f1c2...",
  "kind": "device_code",
  "url": "https://ya.ru/device",
  "user_code": "ABCD-1234",
  "expires_in": 300,
  "interval": 5
}
```

Для `redirect` поле `user_code` — `null`. `interval` — как часто (в секундах) фронтенд спрашивает статус.

## `GET /api/services/{service}/link/{session_id}`

```json
{ "status": "pending", "detail": null }
```

`pending` — ждём пользователя, `linked` — токен сохранён, `expired` — время вышло, `denied` — отказ или ошибка (текст в `detail`).

## `DELETE /api/services/{service}/link`

Удаляет личный токен пользователя. Ответ `204`.

## Где это на фронтенде

- `src/shared/api.ts` — `startServiceLink`, `getServiceLinkStatus`, `unlinkService`
- `src/widgets/SourcesModal.tsx` — кнопки «Привязать» / «Отвязать»
- `src/widgets/ServiceLink.tsx` — показ кода или кнопки входа и опрос статуса

Пока эндпоинтов нет, кнопка «Привязать» показывает «Сервер пока не поддерживает привязку аккаунтов».
