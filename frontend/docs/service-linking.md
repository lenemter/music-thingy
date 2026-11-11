# Привязка сервисов — как это сделано

- список: `GET /api/services` + `GET /api/services/connections`
- включить или выключить в поиске: `PUT /api/services/{service}/toggle`
- отвязать: `DELETE /api/services/{service}/disconnect`

## Яндекс Музыка и YouTube — вход по коду

`POST /api/services/{yandex|youtube}/oauth/device-code` → показать `user_code` и `verification_url`,
затем раз в `interval` секунд `POST /api/services/{yandex|youtube}/oauth/poll-token` с `{ "device_code": "..." }`,
пока не придёт `{ "status": "connected" }`.

- Яндекс: через `yandex_music.Client.request_device_code()` / `poll_device_token()`. Яндекс показывает длинный список доступов —
  это доступы официального приложения Яндекс Музыки, сузить их нельзя.
- YouTube: нужны `YOUTUBE_CLIENT_ID` и `YOUTUBE_CLIENT_SECRET` (OAuth-клиент типа «TVs and Limited Input devices») в `backend/.env`.

## VK — логин и пароль

`POST /api/services/vk/login` с `{ "login": "...", "password": "...", "code": "..." }`. Запрос делается по шагам и ничего не хранит
между ними: фронтенд держит логин и пароль в памяти, пока идёт вход.

- `{ "status": "need_code", "validation_type": "sms", "phone_mask": "+7 *** ***-**-12" }` — повторить запрос с `code`
- `{ "status": "need_code", "invalid_code": true }` — код неверный
- `{ "status": "need_captcha" }` — VK требует капчу VK ID; пройти её с нашей страницы нельзя
- `{ "status": "connected" }` — токен и user_agent сохранены в `UserServiceAccount`

Вход неофициальный: `vkpymusic` входит от имени приложения VK для Android. VK может закрыть этот способ.
Пароль не сохраняется и не пишется в логи.

Лайки и история прослушиваний в бэкенде пока не хранятся — лайки сохраняются в браузере (`localStorage`, `signal-likes`).
