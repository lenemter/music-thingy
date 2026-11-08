# Документация Backend API для Фронтендера

Добро пожаловать! Этот бэкенд реализует всю функциональность ТЗ музыкального агрегатора:
мультисервисный поиск, воспроизведение, плейлисты, избранное, история прослушиваний, рекомендации, "Волна дня", загрузка пользовательских аудиофайлов и встроенный аудиоредактор с эффектами.

- **Base URL:** `http://localhost:8000` (при разработке с Vite запросы проксируются через `/api/...`)
- **Интерактивная OpenAPI документация (Swagger UI):** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Альтернативная документация (ReDoc):** [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
- **Готовый TypeScript клиент:** уже подготовлен и настроен в [`frontend/src/shared/api.ts`](file:///c:/Users/Leo/Desktop/music-thingy/frontend/src/shared/api.ts)

---

## 1. Авторизация и JWT

Все приватные эндпоинты требуют заголовок:
```http
Authorization: Bearer <access_token>
```

### 1.1. Регистрация
- **Метод:** `POST /api/auth/register`
- **Тело запроса:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123",
    "display_name": "Leo"
  }
  ```
- **Ответ (201 Created):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "display_name": "Leo"
  }
  ```

### 1.2. Вход (Получение токенов)
- **Метод:** `POST /api/auth/token` (или `POST /api/auth/login`)
- **Тело запроса:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123"
  }
  ```
- **Ответ (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "access": "eyJhbGciOi...",
    "refresh": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### 1.3. Обновление токена
- **Метод:** `POST /api/auth/token/refresh`
- **Тело запроса:**
  ```json
  {
    "refresh": "eyJhbGciOi..."
  }
  ```

### 1.4. Текущий пользователь
- **Метод:** `GET /api/auth/me`
- **Заголовки:** `Authorization: Bearer <token>`
- **Ответ:** `{ "id": 1, "email": "user@example.com", "display_name": "Leo" }`

---

## 2. Сервисы-источники музыки (Navbar & Header)

Поддерживаемые сервисы:
- `yandex` / `ЯМ` (Яндекс Музыка)
- `spotify` / `SP` (Spotify)
- `soundcloud` / `SC` (SoundCloud)
- `youtube` / `YT` (YouTube)
- `local` / `ФАЙЛ` (Загруженные пользователем треки)

### 2.1. Список сервисов и статус онлайн
- **Метод:** `GET /api/services`
- **Описание:** Возвращает список всех сервисов, их названия, бейджи и статус `online` (с учётом персональных настроек пользователя, если передан токен).
- **Ответ (200 OK):** Совпадает с типом `Service[]` во фронтенде:
  ```json
  [
    { "code": "ЯМ", "name": "Яндекс Музыка", "shortName": "Яндекс", "service": "yandex", "online": true },
    { "code": "SP", "name": "Spotify", "shortName": "Spotify", "service": "spotify", "online": true },
    { "code": "SC", "name": "SoundCloud", "shortName": "SoundCloud", "service": "soundcloud", "online": true },
    { "code": "YT", "name": "YouTube", "shortName": "YouTube", "service": "youtube", "online": true }
  ]
  ```

### 2.2. Настройка включённых сервисов
- **Метод:** `PUT /api/services/preferences`
- **Заголовки:** `Authorization: Bearer <token>`
- **Тело запроса:**
  ```json
  {
    "enabled_services": ["ям", "spotify"]
  }
  ```
- **Ответ (200 OK):** Обновлённый список сервисов `Service[]`.

---

## 3. Мультисервисный поиск и воспроизведение

### 3.1. Агрегированный поиск
- **Метод:** `GET /api/music/search`
- **Параметры запроса (Query Params):**
  - `q` (обязательный): поисковая строка (например, `Queen`, `Орбита 9`)
  - `services` (опционально): через запятую, например `services=yandex,spotify,youtube` (по умолчанию используются все включённые сервисы)
  - `types` (опционально): через запятую, например `types=track,album,artist,playlist` (по умолчанию `track,album`)
  - `limit` (опционально, 1-50): число результатов на каждый сервис (по умолчанию `10`)
- **Ответ (200 OK):**
  ```json
  {
    "query": "Queen",
    "tracks": [
      {
        "id": 8392104,
        "track_key": "yandex:12345",
        "service": "yandex",
        "service_id": "12345",
        "title": "Bohemian Rhapsody",
        "artist": "Queen",
        "cover": "https://avatars.yandex.net/get-music-content/...",
        "duration": 354,
        "sources": ["ЯМ", "SP"],
        "source": "ЯМ",
        "edited": false,
        "liked": false,
        "playback": {
          "kind": "yandex_iframe",
          "ref": "12345/6789"
        },
        "direct_audio_url": "https://...",
        "external_url": "https://music.yandex.ru/album/6789/track/12345"
      }
    ],
    "albums": [
      {
        "id": 492104,
        "service": "spotify",
        "service_id": "alb_1",
        "title": "A Night at the Opera",
        "subtitle": "Queen · альбом",
        "cover": "https://..."
      }
    ],
    "artists": [
      {
        "service": "yandex",
        "service_id": "792",
        "name": "Queen",
        "genres": ["rock"],
        "cover": "https://..."
      }
    ],
    "playlists": [],
    "errors": []
  }
  ```

> [!NOTE]
> Если один и тот же трек найден в нескольких сервисах, бэкенд автоматически объединяет их и возвращает в `sources` массив всех доступных сервисов (например `["ЯМ", "SP", "SC"]`), что в точности соответствует бейджам в дизайне карточки трека!

### 3.2. Получение трека по id
- **Метод:** `GET /api/music/tracks/{service}/{service_id}`
- **Пример:** `GET /api/music/tracks/yandex/12345`

### 3.3. Информация для плеера (Playback)
- **Метод:** `GET /api/music/playback/{service}/{service_id}`
- **Ответ:**
  ```json
  {
    "kind": "youtube_iframe",
    "ref": "fJ9rUzIMcZQ"
  }
  ```
- **Типы плеера (`kind`):**
  - `youtube_iframe`: в `ref` передан videoId (можно использовать `<iframe src="https://www.youtube.com/embed/{ref}">` или YouTube IFrame API)
  - `soundcloud_widget`: в `ref` передан URL трека (виджет `https://w.soundcloud.com/player/?url={encodeURIComponent(ref)}`)
  - `yandex_iframe`: в `ref` передан `{track_id}/{album_id}`
  - `spotify_sdk`: в `ref` передан URI трека `spotify:track:...`
  - `audio_stream`: в `ref` передан локальный URL потока (например, `/api/uploads/1/stream`)

---

## 4. Плейлисты (Playlists)

### 4.1. Список плейлистов
- **Метод:** `GET /api/playlists`
- **Заголовки:** `Authorization: Bearer <token>` (для гостей возвращает публичные плейлисты)
- **Ответ (200 OK):**
  ```json
  [
    {
      "id": 1,
      "name": "Ночные поездки",
      "description": "Плейлист для ночного города",
      "cover": "https://...",
      "tracks_count": 64,
      "is_public": true
    }
  ]
  ```

### 4.2. Создание плейлиста
- **Метод:** `POST /api/playlists`
- **Заголовки:** `Authorization: Bearer <token>`
- **Тело запроса:**
  ```json
  {
    "name": "Лето 2026",
    "description": "Любимые треки лета",
    "cover_url": "https://...",
    "is_public": false
  }
  ```

### 4.3. Получение плейлиста с треками
- **Метод:** `GET /api/playlists/{playlist_id}`
- **Ответ (200 OK):**
  ```json
  {
    "id": 1,
    "name": "Ночные поездки",
    "cover": "https://...",
    "tracks_count": 2,
    "tracks": [
      {
        "id": 10,
        "playlist_id": 1,
        "service": "yandex",
        "service_id": "123",
        "title": "Радиовышка",
        "artist": "Low Tower",
        "cover": "https://...",
        "duration": 238,
        "position": 0
      }
    ]
  }
  ```

### 4.4. Добавление трека в плейлист
- **Метод:** `POST /api/playlists/{playlist_id}/tracks`
- **Тело запроса:**
  ```json
  {
    "service": "spotify",
    "service_id": "4cOdK2wGLETKBW3PvgPWqT",
    "title": "Never Gonna Give You Up",
    "artist": "Rick Astley",
    "duration": 213,
    "cover_url": "https://..."
  }
  ```

### 4.5. Удаление трека из плейлиста
- **Метод:** `DELETE /api/playlists/{playlist_id}/tracks/{track_id}`

### 4.6. Изменение порядка треков (Drag & Drop Reorder)
- **Метод:** `PUT /api/playlists/{playlist_id}/reorder`
- **Тело запроса:**
  ```json
  {
    "track_ids": [12, 10, 11]
  }
  ```

### 4.7. Удаление плейлиста
- **Метод:** `DELETE /api/playlists/{playlist_id}`

---

## 5. Избранное (Favorites / Лайки)

### 5.1. Получить список любимых треков
- **Метод:** `GET /api/favorites/tracks`
- **Заголовки:** `Authorization: Bearer <token>`
- **Ответ:** Список `Track[]`, где у каждого `liked: true`.

### 5.2. Добавить трек в избранное (Поставить лайк)
- **Метод:** `POST /api/favorites/tracks`
- **Заголовки:** `Authorization: Bearer <token>`
- **Тело запроса:**
  ```json
  {
    "service": "yandex",
    "service_id": "101",
    "title": "Радиовышка",
    "artist": "Low Tower",
    "duration": 238,
    "sources": ["ЯМ", "SP", "SC"]
  }
  ```

### 5.3. Удалить трек из избранного (Снять лайк)
- **Метод:** `DELETE /api/favorites/tracks/{service}/{service_id}`

### 5.4. Быстрая проверка лайков для текущего экрана
- **Метод:** `GET /api/favorites/check`
- **Ответ:**
  ```json
  {
    "liked_keys": ["yandex:101", "spotify:4cOdK..."]
  }
  ```

---

## 6. История, Рекомендации и Волна Дня

### 6.1. Зафиксировать прослушивание трека
- **Метод:** `POST /api/history`
- **Тело запроса:**
  ```json
  {
    "service": "yandex",
    "service_id": "101",
    "title": "Радиовышка",
    "artist": "Low Tower",
    "album": "Сигнал 404",
    "duration": 238
  }
  ```

### 6.2. "Продолжить слушать" (Виджет ContinueListening)
- **Метод:** `GET /api/history/albums?limit=6`
- **Ответ (200 OK):** Список `Album[]`:
  ```json
  [
    {
      "id": 1,
      "service": "yandex",
      "service_id": "alb_5",
      "title": "Сигнал 404",
      "subtitle": "Low Tower · альбом",
      "cover": ""
    }
  ]
  ```

### 6.3. "Рекомендации для вас" (Виджет Recommendations)
- **Метод:** `GET /api/recommendations?limit=10`
- **Описание:** Умный генератор персональной ленты на основе истории и любимых артистов из всех сервисов.
- **Ответ:** Список `Track[]` со всеми свойствами, включая `sources: ["ЯМ", "SP", "SC"]`, `duration`, `cover`, `liked`, `edited`.

### 6.4. "Волна дня" (Виджет WaveOfDay)
- **Метод:** `GET /api/wave`
- **Ответ (200 OK):**
  ```json
  {
    "date": "03.11",
    "title": "Эфир на закате",
    "description": "Собранный поток из Яндекс Музыки, Spotify, SoundCloud и YouTube...",
    "trackCount": 38,
    "duration": 4389,
    "tracks": [...]
  }
  ```

---

## 7. Своя музыка (Own Music & Uploads)

### 7.1. Список загруженных файлов
- **Метод:** `GET /api/uploads`
- **Заголовки:** `Authorization: Bearer <token>`
- **Ответ (200 OK):** Массив `UserFile[]`, полностью соответствующий интерфейсу фронтенда:
  ```json
  [
    {
      "id": 1,
      "name": "демо_гараж_v3",
      "type": "WAV",
      "duration": 171,
      "size": 31,
      "audio_url": "/api/uploads/1/stream",
      "is_edited": false
    }
  ]
  ```

### 7.2. Загрузка файла
- **Метод:** `POST /api/uploads`
- **Content-Type:** `multipart/form-data`
- **Поля формы:**
  - `file`: бинарный файл (`.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`)
  - `title` (опционально): название трека
  - `artist` (опционально): исполнитель
- **Ответ (201 Created):** Объект `UserFile`.

### 7.3. Стриминг аудио и перемотка (Scrubber)
- **Метод:** `GET /api/uploads/{id}/stream`
- **Поддержка Range:** Поддерживает заголовок `Range: bytes=START-END` и возвращает `206 Partial Content`.
  Это обеспечивает мгновенную и плавную перемотку в браузере в теге `<audio src="/api/uploads/{id}/stream">`!

### 7.4. Удаление файла
- **Метод:** `DELETE /api/uploads/{id}`

---

## 8. Аудиоредактор (Audio Editor)

Позволяет обрезать треки и накладывать аудио эффекты на сервере с сохранением результата.

### 8.1. Обрезка трека (Trim)
- **Метод:** `POST /api/editor/trim`
- **Тело запроса:**
  ```json
  {
    "upload_id": 1,
    "start_sec": 15.0,
    "end_sec": 45.5,
    "save_as_new": true,
    "new_name": "демо_гараж_обрезанный"
  }
  ```
- **Ответ:** Обновлённый или новый объект `UserFile` с флагом `is_edited: true`.

### 8.2. Наложение аудио эффектов
- **Метод:** `POST /api/editor/effects`
- **Тело запроса:**
  ```json
  {
    "upload_id": 1,
    "fade_in_sec": 1.5,
    "fade_out_sec": 2.0,
    "volume_gain_db": 3.0,
    "bass_boost_db": 4.5,
    "speed_factor": 1.05,
    "normalize": true,
    "reverse": false,
    "echo_delay_sec": 0.25,
    "echo_decay": 0.35,
    "save_as_new": true,
    "new_name": "демо_гараж_эффекты"
  }
  ```
- **Параметры эффектов:**
  - `fade_in_sec`: длительность нарастания громкости в секундах
  - `fade_out_sec`: длительность затухания в секундах
  - `volume_gain_db`: усиление/ослабление громкости в дБ (от -30 до +30)
  - `bass_boost_db`: усиление басов (низких частот) в дБ (от -12 до +24)
  - `speed_factor`: изменение скорости воспроизведения (например, `0.85` — slowed, `1.2` — speedup)
  - `normalize`: нормализация пикового уровня (true/false)
  - `reverse`: реверс аудио дорожки задом наперёд (true/false)
  - `echo_delay_sec`: задержка эхо в секундах
  - `echo_decay`: коэффициент затухания эхо (от 0.0 до 1.0)

### 8.3. Полный конвейер редактирования (Process)
- **Метод:** `POST /api/editor/process`
- **Тело запроса:** Совмещает обрезку, все эффекты и конвертацию формата (`output_format`: "WAV", "MP3", "FLAC", "OGG").

---

## 9. Как использовать в коде фронтенда

Все методы уже реализованы и типизированы в [`frontend/src/shared/api.ts`](file:///c:/Users/Leo/Desktop/music-thingy/frontend/src/shared/api.ts).

### Пример в компоненте React:

```tsx
import { useEffect, useState } from "react";
import {
  fetchServices,
  fetchRecommendations,
  fetchWave,
  fetchContinueListening,
  fetchUploads,
  uploadMusicFile,
  trimAudio,
  addFavoriteTrack,
  removeFavoriteTrack,
} from "../shared/api.ts";
import type { Track, UserFile, Service, Wave, Album } from "../shared/types.ts";

function MyMusicDashboard() {
  const [services, setServices] = useState<Service[]>([]);
  const [recommendations, setRecommendations] = useState<Track[]>([]);
  const [wave, setWave] = useState<Wave | null>(null);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [files, setFiles] = useState<UserFile[]>([]);

  useEffect(() => {
    // Загрузка реальных данных с бэкенда
    fetchServices().then(setServices);
    fetchRecommendations().then(setRecommendations);
    fetchWave().then(setWave);
    fetchContinueListening().then(setAlbums);
    fetchUploads().then(setFiles);
  }, []);

  async function handleToggleLike(track: Track) {
    if (track.liked) {
      await removeFavoriteTrack(track.source, String(track.id));
    } else {
      await addFavoriteTrack(track);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const uploaded = await uploadMusicFile(file);
    setFiles((prev) => [uploaded, ...prev]);
  }

  async function handleTrim(fileId: number) {
    const trimmed = await trimAudio(fileId, 0, 30, "Мой обрезанный рингтон");
    setFiles((prev) => [trimmed, ...prev]);
  }

  // ... рендер компонентов
}
```
