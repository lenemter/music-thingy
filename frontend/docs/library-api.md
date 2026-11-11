# Медиатека — что ждёт фронтенд

Сейчас в бэкенде нет эндпоинтов для своей музыки, поэтому фронтенд хранит загруженные файлы, название, исполнителя
и обложку в браузере (IndexedDB, база `signal-library`, отдельно для каждого пользователя по email).
Минусы: музыка видна только в этом браузере и пропадёт при очистке данных сайта.

Чтобы перенести медиатеку на сервер, нужны эндпоинты (все с `Authorization: Bearer <access>`):

- `GET /api/uploads` — список `UserFileRead`
- `POST /api/uploads` — `multipart/form-data`: `file`, `title`, `artist`
- `DELETE /api/uploads/{id}`
- `GET /api/uploads/{id}/stream` — аудио с поддержкой Range, без авторизации (для `<audio src>`)
- `PATCH /api/uploads/{id}` — `{ "title": "...", "artist": "..." }`
- `PUT /api/uploads/{id}/cover` — `multipart/form-data`, поле `file` (JPEG); `DELETE` — убрать обложку

```json
{ "id": 12, "name": "Радиовышка", "artist": "Low Tower", "type": "MP3", "duration": 276, "size": 8.4,
  "audio_url": "/api/uploads/12/stream", "cover_url": "/api/uploads/12/cover" }
```

Обложку из тегов (ID3 `APIC`, FLAC `pictures`, M4A `covr`, OGG `METADATA_BLOCK_PICTURE`) можно доставать через `mutagen`.
Если её нет, фронтенд выбирает случайную обложку из `src/shared/images/covers`.

## Плейлисты

В медиатеке три вида плейлистов:

- **«Понравившиеся»**: собирается сам. В него попадают лайки, поставленные у нас, и лайки из подключённых сервисов (`GET /api/music/me/favorites`).
  Если снять у нас лайк с трека, который лайкнут в сервисе, трек просто скрывается из списка. В самом сервисе лайк остаётся.
- **Свои плейлисты**: пользователь создаёт, переименовывает и удаляет их сам и добавляет треки кнопкой «+».
  Пока хранятся в `localStorage` (`signal-playlists:<email>`) как копии треков, поэтому видны только в этом браузере.
- **Плейлисты из сервисов**: приходят из `GET /api/music/me/playlists`, треки подгружаются из `GET /api/music/playlists/{service}/{id}`
  (с аккаунтом пользователя, чтобы открывались и закрытые). Последний список кэшируется, и когда сервис отключён, его плейлисты
  показываются серыми с подписью «Недоступно · подключите …».

Чтобы перенести свои плейлисты и лайки на сервер, нужны:

- `GET /api/playlists`, `POST /api/playlists` `{ "name": "..." }`, `PATCH /api/playlists/{id}`, `DELETE /api/playlists/{id}`
- `POST /api/playlists/{id}/tracks` `{ "service": "vk", "service_id": "..." }`, `DELETE /api/playlists/{id}/tracks/{service}/{service_id}`
- `PUT` / `DELETE /api/music/tracks/{service}/{service_id}/like` — лайк у нас (и, по возможности, в самом сервисе)

## Где это на фронтенде

- `src/shared/playlists.ts`, `src/shared/favorites.ts` — свои плейлисты и лайки
- `src/shared/usePlaylists.ts` — собирает все плейлисты для медиатеки и меню слева
- `src/entities/PlaylistCover.tsx` — обложка: коллаж из 4 обложек, сгенерированная, «недоступно», заглушка при загрузке
- `src/widgets/PlaylistView.tsx`, `AddToPlaylistModal.tsx`, `PlaylistNameModal.tsx`

- `src/shared/library.ts` — хранение файлов и правок (сейчас IndexedDB, потом — запросы к серверу)
- `src/shared/audioTags.ts` — чтение тегов ID3 и FLAC в браузере
- `src/widgets/TrackEditModal.tsx` — окно редактирования
- `src/pages/LibraryPage.tsx` — страница «Медиатека»
