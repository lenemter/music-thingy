# Документация Backend API: Получение треков и информации о них

Данный сервис реализует API для поиска, получения информации о треках, альбомах, артистах и плейлистах, параметров воспроизведения и прямого аудиостриминга из внешних музыкальных сервисов.

Архитектура построена на базе шаблона **Адаптер (Adapter)** и **Агрегатора (Aggregator)**:
- Подключён рабочий адаптер **Яндекс Музыки** (`yandex-music`).
- Агрегатор автоматически объединяет результаты запросов, выполняет дедупликацию треков и объединение тегов источников (`sources: ["ЯМ", ...]`).
- Новые сервисы (Spotify, SoundCloud, YouTube) подключаются без изменения контракта API через реализацию `BaseMusicAdapter` и метод `aggregator.register_adapter(...)`.
- Для сервисов без подключённого адаптера статус возвращается как `online: false`, а при поиске возвращается информативное сообщение об ошибке в поле `errors` без падения сервиса.

---

## 1. Базовые сведения

- **Base URL:** `http://localhost:8000` (в Docker или локально)
- **OpenAPI / Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 2. Эндпоинты

### 2.1. Список доступных сервисов-источников
- **Маршрут:** `GET /api/services` или `GET /api/music/services`
- **Описание:** Возвращает перечень всех музыкальных сервисов, их названия, краткие коды (`ЯМ`, `SP`, `SC`, `YT`) и статус `online` (доступность адаптера).
- **Ответ (200 OK):**
```json
[
  {
    "code": "ЯМ",
    "name": "Яндекс Музыка",
    "shortName": "Яндекс",
    "service": "yandex",
    "online": true
  },
  {
    "code": "SP",
    "name": "Spotify",
    "shortName": "Spotify",
    "service": "spotify",
    "online": false
  },
  {
    "code": "SC",
    "name": "SoundCloud",
    "shortName": "SoundCloud",
    "service": "soundcloud",
    "online": false
  },
  {
    "code": "YT",
    "name": "YouTube",
    "shortName": "YouTube",
    "service": "youtube",
    "online": false
  }
]
```

---

### 2.2. Мультисервисный поиск
- **Маршрут:** `GET /api/music/search`
- **Query параметры:**
  - `q` (string, обязательный, min_length=1): Поисковый запрос (например `Queen`, `Meteora`).
  - `services` (string, опционально): Список сервисов через запятую (например `yandex` или `yandex,spotify`). По умолчанию опрашиваются все поддерживаемые сервисы.
  - `types` (string, опционально): Типы сущностей через запятую: `track`, `album`, `artist`, `playlist` (по умолчанию `track,album`).
  - `limit` (int, опционально, по умолчанию 10, максимум 50): Лимит результатов на сервис.
- **Пример запроса:**
  ```http
  GET /api/music/search?q=Queen&services=yandex&types=track,album&limit=5
  ```
- **Ответ (200 OK):**
```json
{
  "query": "Queen",
  "tracks": [
    {
      "id": 87491164,
      "track_key": "yandex:87491164:16916643",
      "service": "yandex",
      "service_id": "87491164:16916643",
      "title": "Queen",
      "artist": "KVPV",
      "artists": ["KVPV"],
      "artist_ids": ["5801667"],
      "album": "Queen",
      "cover": "https://avatars.yandex.net/get-music-content/13043189/18a7b164.a.16916643-2/400x400",
      "artwork_url": "https://avatars.yandex.net/get-music-content/13043189/18a7b164.a.16916643-2/400x400",
      "duration": 157,
      "duration_ms": 157710,
      "sources": ["ЯМ"],
      "source": "ЯМ",
      "is_playable": true,
      "edited": false,
      "liked": false,
      "playback": {
        "kind": "yandex_iframe",
        "ref": "87491164/16916643"
      },
      "direct_audio_url": null,
      "stream_url": "/api/music/tracks/yandex/87491164:16916643/stream",
      "external_url": "https://music.yandex.ru/album/16916643/track/87491164"
    }
  ],
  "albums": [
    {
      "id": 16916643,
      "service": "yandex",
      "service_id": "16916643",
      "title": "Queen",
      "subtitle": "KVPV · альбом",
      "artist": "KVPV",
      "year": 2021,
      "cover": "https://avatars.yandex.net/get-music-content/13043189/18a7b164.a.16916643-2/400x400",
      "artwork_url": "https://avatars.yandex.net/get-music-content/13043189/18a7b164.a.16916643-2/400x400",
      "external_url": "https://music.yandex.ru/album/16916643",
      "tracks_count": 1,
      "tracks": null
    }
  ],
  "artists": [],
  "playlists": [],
  "errors": []
}
```

---

### 2.3. Получение информации о треке
- **Маршрут:** `GET /api/music/tracks/{service}/{service_id}`
- **Параметры пути:**
  - `service`: Код или имя сервиса (например `yandex`, `ЯМ`).
  - `service_id`: Идентификатор трека в сервисе (для Яндекса — `track_id` или `track_id:album_id`).
- **Ответ (200 OK):**
```json
{
  "id": 178529,
  "track_key": "yandex:178529:21940",
  "service": "yandex",
  "service_id": "178529:21940",
  "title": "Numb",
  "artist": "Linkin Park",
  "artists": ["Linkin Park"],
  "artist_ids": ["36800"],
  "album": "Meteora",
  "cover": "https://avatars.yandex.net/get-music-content/142001/a92a262f.a.21940-7/400x400",
  "artwork_url": "https://avatars.yandex.net/get-music-content/142001/a92a262f.a.21940-7/400x400",
  "duration": 187,
  "duration_ms": 187520,
  "sources": ["ЯМ"],
  "source": "ЯМ",
  "is_playable": true,
  "edited": false,
  "liked": false,
  "playback": {
    "kind": "yandex_iframe",
    "ref": "178529/21940",
    "direct_audio_url": "https://api.music.yandex.net/get-mp3/..."
  },
  "direct_audio_url": "https://api.music.yandex.net/get-mp3/...",
  "stream_url": "/api/music/tracks/yandex/178529:21940/stream",
  "external_url": "https://music.yandex.ru/album/21940/track/178529"
}
```

---

### 2.4. Параметры воспроизведения трека (Playback)
- **Маршрут:** `GET /api/music/playback/{service}/{service_id}`
- **Описание:** Возвращает тип плеера (`yandex_iframe`, `spotify_sdk`, `soundcloud_widget`, `youtube_iframe`, `direct_url`) и его референс.
- **Ответ (200 OK):**
```json
{
  "kind": "yandex_iframe",
  "ref": "178529/21940",
  "direct_audio_url": "https://api.music.yandex.net/get-mp3/..."
}
```

---

### 2.5. Стриминг аудиодорожки
- **Маршрут:** `GET /api/music/tracks/{service}/{service_id}/stream`
- **Query параметры:**
  - `redirect` (bool, по умолчанию `false`):
    - При `false` сервер проксирует аудиопоток с поддержкой HTTP Range (`206 Partial Content`), что позволяет использовать `<audio src="/api/music/tracks/yandex/178529:21940/stream">` с мгновенной перемоткой без проблем с CORS.
    - При `true` сервер возвращает `307 Temporary Redirect` сразу на прямую ссылку CDN провайдера.

---

### 2.6. Получение информации об альбоме
- **Маршрут:** `GET /api/music/albums/{service}/{service_id}`
- **Описание:** Возвращает информацию об альбоме и список входящих в него треков.
- **Ответ (200 OK):**
```json
{
  "id": 21940,
  "service": "yandex",
  "service_id": "21940",
  "title": "Meteora",
  "subtitle": "Linkin Park · альбом",
  "artist": "Linkin Park",
  "year": 2003,
  "cover": "https://avatars.yandex.net/get-music-content/142001/a92a262f.a.21940-7/400x400",
  "artwork_url": "https://avatars.yandex.net/get-music-content/142001/a92a262f.a.21940-7/400x400",
  "external_url": "https://music.yandex.ru/album/21940",
  "tracks_count": 16,
  "tracks": [ ... ]
}
```

---

### 2.7. Получение информации об исполнителе
- **Маршрут:** `GET /api/music/artists/{service}/{service_id}`
- **Ответ (200 OK):**
```json
{
  "service": "yandex",
  "service_id": "36800",
  "name": "Linkin Park",
  "genres": ["numetal", "alternative"],
  "cover": "https://avatars.yandex.net/get-music-content/...",
  "artwork_url": "https://avatars.yandex.net/get-music-content/...",
  "external_url": "https://music.yandex.ru/artist/36800"
}
```

---

### 2.8. Получение информации о плейлисте
- **Маршрут:** `GET /api/music/playlists/{service}/{service_id}`
- **Параметры:**
  - `service`: `yandex`
  - `service_id`: `owner_uid:kind` (например `103372440:2131`)
- **Ответ (200 OK):**
```json
{
  "id": 2131,
  "service": "yandex",
  "service_id": "103372440:2131",
  "name": "Рок",
  "title": "Рок",
  "cover": "https://avatars.yandex.net/...",
  "description": "Лучшие рок-композиции",
  "owner_name": "Яндекс Музыка",
  "tracks_count": 108,
  "external_url": "https://music.yandex.ru/users/music-blog/playlists/2131",
  "tracks": [ ... ]
}
```

---

## 3. Привязка музыкальных сервисов (Подключение аккаунтов)

Пользователь может привязать свои личные аккаунты сервисов (**Яндекс Музыка**, **YouTube Music**, **VK Музыка**). Привязанные сервисы хранятся в базе данных (`UserServiceAccount`), могут временно выключаться/включаться (`toggle`), а также автоматически участвуют в поиске и выгрузке плейлистов/избранного.

### 3.1. Получение статуса подключений пользователя
- **Маршрут:** `GET /api/services/connections`
- **Заголовки:** `Authorization: Bearer <jwt_token>`
- **Ответ (200 OK):**
```json
[
  {
    "service": "yandex",
    "code": "ЯМ",
    "name": "Яндекс Музыка",
    "connected": true,
    "is_active": true,
    "account_name": "Иван Иванов",
    "account_id": "12345678"
  },
  {
    "service": "youtube",
    "code": "YT",
    "name": "YouTube",
    "connected": false,
    "is_active": false,
    "account_name": null,
    "account_id": null
  },
  {
    "service": "vk",
    "code": "VK",
    "name": "VK Музыка",
    "connected": false,
    "is_active": false,
    "account_name": null,
    "account_id": null
  }
]
```

---

### 3.2. Подключение сервиса
- **Маршрут:** `POST /api/services/{service}/connect`
- **Заголовки:** `Authorization: Bearer <jwt_token>`
- **Параметр пути:** `service` (`yandex`, `youtube`, `vk`)

#### Вариант А: Яндекс Музыка
- **Тело запроса (JSON):**
```json
{
  "token": "y0_AgAAAA..."
}
```

#### Вариант Б: VK Музыка
- **Тело запроса (JSON):**
```json
{
  "token": "vk1.a.abc...",
  "user_agent": "VKAndroidApp/8.0-1234 (Android 12; SDK 31; arm64-v8a; ...)"
}
```
*Поле `user_agent` опционально.*

#### Вариант В: YouTube Music (ручной токен или oauth.json)
- **Тело запроса (JSON):**
```json
{
  "token": "...",
  "auth_json": "{\"access_token\": \"...\", \"refresh_token\": \"...\"}"
}
```

---

### 3.3. YouTube OAuth Device Code Flow (Google TV Flow)

1. **Шаг 1: Получение кода для устройства**
   - **Маршрут:** `POST /api/services/youtube/oauth/device-code`
   - **Заголовки:** `Authorization: Bearer <jwt_token>`
   - **Ответ (200 OK):**
   ```json
   {
     "device_code": "...",
     "user_code": "ABCD-EFGH",
     "verification_url": "https://www.google.com/device",
     "expires_in": 1800,
     "interval": 5
   }
   ```
   *Фронтенд показывает пользователю `verification_url` и код `user_code`.*

2. **Шаг 2: Опрос готовности токена (Polling)**
   - **Маршрут:** `POST /api/services/youtube/oauth/poll-token`
   - **Заголовки:** `Authorization: Bearer <jwt_token>`
   - **Тело запроса:**
   ```json
   {
     "device_code": "..."
   }
   ```
   - **Ответ (200 OK):** `ServiceConnectionStatus` с `"connected": true`.

---

### 3.4. Отключение сервиса
- **Маршрут:** `DELETE /api/services/{service}/disconnect`
- **Заголовки:** `Authorization: Bearer <jwt_token>`

---

### 3.5. Включение / отключение активности привязанного сервиса
- **Маршрут:** `PUT /api/services/{service}/toggle`
- **Заголовки:** `Authorization: Bearer <jwt_token>`
- **Тело запроса:** `{"is_active": false}`

---

### 3.6. Персональные плейлисты пользователя
- **Маршрут:** `GET /api/music/me/playlists`
- **Заголовки:** `Authorization: Bearer <jwt_token>`
- **Query параметры:** `services` (опционально)

---

### 3.7. Избранные треки пользователя
- **Маршрут:** `GET /api/music/me/favorites`
- **Заголовки:** `Authorization: Bearer <jwt_token>`
- **Query параметры:** `services`, `limit`

---

## 4. Пользовательские загрузки (`/api/uploads`)

Позволяет пользователю загружать собственные аудиофайлы (MP3, WAV, FLAC, OGG, M4A, AAC до 50 МБ), редактировать их метаданные (название, исполнитель), управлять обложками (загруженная картинка или шаблонная обложка `template:<номер>`), и воспроизводить аудио через `<audio src="...">` со стримингом и поддержкой HTTP Range (`206 Partial Content`).

Все загруженные треки доступны в общем формате `TrackRead` как `service = "local"`, `sources = ["ФАЙЛ"]`.

### 4.1. Список загрузок
- **Маршрут:** `GET /api/uploads`
- **Заголовки:** `Authorization: Bearer <access_token>`
- **Ответ (200 OK):**
```json
[
  {
    "id": 12,
    "name": "Радиовышка",
    "artist": "Low Tower",
    "type": "MP3",
    "duration": 276,
    "size": 8.4,
    "audio_url": "/api/uploads/12/stream?sig=...",
    "cover_url": "/api/uploads/12/cover",
    "created_at": "2026-11-11T12:00:00Z"
  }
]
```

---

### 4.2. Загрузка файла
- **Маршрут:** `POST /api/uploads`
- **Заголовки:** `Authorization: Bearer <access_token>`
- **Content-Type:** `multipart/form-data`
- **Параметры формы:**
  - `file`: Аудиофайл (обязательное; форматы MP3, WAV, FLAC, OGG, M4A, AAC; до 50 МБ).
  - `title`: Название (опционально; если не передано, извлекается из ID3/Vorbis/MP4 тегов через mutagen или из имени файла).
  - `artist`: Исполнитель (опционально; если не передано, извлекается из тегов или по умолчанию `"Моя музыка"`).
  - `cover`: Картинка обложки (файл JPEG/PNG) или строка шаблонной обложки (`"template:3"`). Если не передано, автоматически извлекается встроенная обложка из тегов аудиофайла (ID3 APIC, FLAC pictures, M4A covr, OGG metadata_block_picture).
- **Ответ (201 Created):** Объект `UserFileRead`.

---

### 4.3. Редактирование информации о треке
- **Маршрут:** `PATCH /api/uploads/{id}`
- **Заголовки:** `Authorization: Bearer <access_token>`
- **Тело запроса (JSON):**
```json
{
  "title": "Новое название",
  "artist": "Новый артист"
}
```
- **Ответ (200 OK):** Обновлённый объект `UserFileRead`.

---

### 4.4. Обновление обложки
- **Маршрут:** `PUT /api/uploads/{id}/cover`
- **Заголовки:** `Authorization: Bearer <access_token>`
- **Вариант 1 (Файл):** `multipart/form-data`, поле `file` с изображением (JPEG, PNG, WebP).
- **Вариант 2 (Шаблонная обложка):** JSON `{"cover": "template:5"}` или поле формы `cover: "template:5"`.
- **Ответ (200 OK):** Обновлённый объект `UserFileRead`.

---

### 4.5. Удаление обложки
- **Маршрут:** `DELETE /api/uploads/{id}/cover`
- **Заголовки:** `Authorization: Bearer <access_token>`
- **Ответ (200 OK):** Обновлённый объект `UserFileRead` (`cover_url: null`).

---

### 4.6. Удаление загрузки
- **Маршрут:** `DELETE /api/uploads/{id}`
- **Заголовки:** `Authorization: Bearer <access_token>`
- **Ответ (204 No Content):** Файл и обложка удаляются с диска и из базы данных.

---

### 4.7. Стриминг аудиодорожки
- **Маршрут:** `GET /api/uploads/{id}/stream`
- **Авторизация (любой из вариантов):**
  - Подписанный query-параметр `?sig=...` (сгенерирован сервером в `audio_url`, срок действия 7 дней, позволяет вставлять ссылку прямо в `<audio src="...">` без заголовков).
  - Query-параметр `?token=...` (JWT access token).
  - Cookie `access_token`.
  - Заголовок `Authorization: Bearer <access_token>`.
- **Поддержка HTTP Range:** Возвращает `206 Partial Content` с заголовками `Content-Range`, `Content-Length`, `Accept-Ranges: bytes` для мгновенной перемотки.

---

### 4.8. Получение картинки обложки
- **Маршрут:** `GET /api/uploads/{id}/cover`
- **Описание:** Отдаёт бинарный файл загруженной обложки (`image/jpeg`, `image/png`). Публично доступен для использования в `<img src="...">`.

---

## 5. Подключение новых адаптеров в будущем

Для добавления нового музыкального сервиса (например, Spotify или SoundCloud):
1. Реализуйте подкласс `BaseMusicAdapter` в `backend/services/music/<service>.py`.
2. Зарегистрируйте экземпляр адаптера в агрегаторе:
   ```python
   from services.music.aggregator import aggregator
   from services.music.spotify import SpotifyAdapter

   aggregator.register_adapter(SpotifyAdapter(...))
   ```
3. Сервис автоматически станет `online: true` в `/api/services` и начнёт участвовать в мультисервисном поиске без изменения логики контроллеров и фронтенда.
