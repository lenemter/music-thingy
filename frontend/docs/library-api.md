# Медиатека — что ждёт фронтенд

Фронтенд уже умеет менять у загруженного трека название, исполнителя и обложку. Пока эндпоинтов ниже нет,
изменения сохраняются только в браузере пользователя (`localStorage`, ключ `signal-library`). Как только бэкенд их добавит,
фронтенд сам начнёт сохранять на сервер и уберёт локальные копии — менять фронтенд не придётся.

Все запросы — с `Authorization: Bearer <access>`, только для своих загрузок.

## `UserFileRead` — добавить поля

```json
{ "artist": "Low Tower", "cover_url": "/api/uploads/12/cover" }
```

`artist` уже хранится в `UserUpload.artist`, его нужно просто отдать. `cover_url` — `null`, если обложки нет.

## `PATCH /api/uploads/{id}`

```json
{ "title": "Радиовышка", "artist": "Low Tower" }
```

Ответ — обновлённый `UserFileRead`.

## `PUT /api/uploads/{id}/cover`

`multipart/form-data`, поле `file` — картинка (фронтенд шлёт JPEG). Сохранить файл, записать `cover_url`, ответ — `UserFileRead`.

## `DELETE /api/uploads/{id}/cover`

Убирает обложку. Ответ `204`.

## `GET /api/uploads/{id}/cover`

Отдаёт картинку обложки (без авторизации, как `/stream`, чтобы работал `<img src>`).

## Обложка из файла при загрузке

`AudioEditor.get_metadata` уже читает `title` и `artist` через `mutagen`. Встроенную обложку тоже можно достать оттуда:
кадр `APIC` в ID3 (MP3), `pictures` во FLAC, `covr` в M4A, `METADATA_BLOCK_PICTURE` в OGG — и сразу сохранить как обложку загрузки.
Пока этого нет, фронтенд сам читает обложку из MP3 и FLAC перед загрузкой и отправляет её через `PUT /api/uploads/{id}/cover`.
Если в файле обложки нет, фронтенд выбирает случайную шаблонную обложку и отправляет её тем же запросом (тоже JPEG).

## Где это на фронтенде

- `src/shared/library.ts` — сохранение изменений (сервер или браузер)
- `src/shared/audioTags.ts` — чтение тегов ID3 и FLAC в браузере
- `src/widgets/TrackEditModal.tsx` — окно редактирования
- `src/pages/LibraryPage.tsx` — страница «Медиатека»
