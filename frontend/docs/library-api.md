# Медиатека и лайки — как фронтенд работает с бэкендом

## Свои загрузки — на сервере

Все запросы с `Authorization: Bearer <access>`.

| Действие | Запрос |
|---|---|
| Список (новые первыми) | `GET /api/uploads` |
| Загрузка | `POST /api/uploads` — `multipart/form-data`, поле `file`. Название, исполнителя и обложку из тегов сервер достаёт сам |
| Название и исполнитель | `PATCH /api/uploads/{id}` — `{ "title": "...", "artist": "..." }` |
| Шаблонная обложка | `PUT /api/uploads/{id}/cover` — JSON `{ "cover": "template:<номер>" }` |
| Своя картинка | `PUT /api/uploads/{id}/cover` — `multipart/form-data`, поле `file`. Фронтенд уменьшает её до 600 px |
| Убрать обложку | `DELETE /api/uploads/{id}/cover` |
| Удаление | `DELETE /api/uploads/{id}` |
| Аудио для плеера | `audio_url` из ответа: `/api/uploads/{id}/stream?sig=…`, подписанная ссылка на 7 дней, с поддержкой Range |

Если у файла нет обложки, фронтенд показывает шаблонную из `src/shared/images/covers`. Какую именно — зависит от id, поэтому у одного файла она всегда одна и та же.

Треки, восстановленные из истории или очереди, приходят без ссылки на аудио. Перед запуском плеер берёт свежую ссылку через `GET /api/uploads/{id}`.

## Лайки — на сервере

- `PUT /api/music/tracks/{service}/{id}/like` — тело `{ title, artist, cover, duration }`, чтобы сервер мог сразу сохранить данные трека.
- `DELETE /api/music/tracks/{service}/{id}/like` — снять лайк.
- `GET /api/music/me/liked?offset=&limit=` — «Понравившиеся»: лайки на сайте и лайки из подключённых сервисов одним списком. Фронтенд берёт до 5 страниц по 100.

Сердечко меняется сразу: фронтенд держит кэш списка (`signal-likes-cache:<email>`). Если сервер ответил ошибкой, сердечко возвращается обратно.

Если снять лайк с трека, лайкнутого в сервисе, сервер пытается снять его и там. Если сервис не дал (`synced: false`), трек скрывается из «Понравившихся» в этом браузере (`signal-unliked:<email>`).

## Разовый перенос из браузера

До появления этих эндпоинтов файлы лежали в IndexedDB `signal-library`, а лайки в `localStorage`. При входе фронтенд один раз:

1. Загружает старые файлы на сервер и удаляет их из IndexedDB. Если файл загрузить не удалось, он остаётся в браузере до следующего входа.
2. Меняет старые id файлов на новые в своих плейлистах, истории и очереди.
3. Отправляет старые лайки на сервер.

## Пока в браузере

- **Свои плейлисты:** `signal-playlists:<email>`.
- **История и запуски плейлистов:** `signal-history:<email>`, `signal-playlist-plays:<email>`.
- **Очередь плеера:** `signal-player-session:<email>`.

Для плейлистов нужны:
- `GET`, `POST /api/playlists`;
- `PATCH`, `DELETE /api/playlists/{id}`;
- `POST /api/playlists/{id}/tracks` и `DELETE /api/playlists/{id}/tracks/{service}/{service_id}`.

## Где это на фронтенде

- `src/shared/api.ts` — запросы к `/api/uploads` и лайкам
- `src/shared/library.ts` — свои загрузки и перенос из IndexedDB
- `src/shared/favorites.ts` — лайки и их кэш
- `src/shared/likesSync.ts` — загрузка «Понравившихся» с сервера и перенос старых лайков
- `src/shared/useUploader.ts` — загрузка файлов
- `src/shared/usePlaylists.ts` — собирает плейлисты для медиатеки, главной и меню слева
- `src/widgets/TrackEditModal.tsx` — окно редактирования трека
