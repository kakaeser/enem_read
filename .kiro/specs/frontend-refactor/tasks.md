# Implementation Plan: Frontend Refactor

## Overview

Implement the Flet desktop app, mobile HTML upload page, and minimal backend additions for the "Enem da Read" system. Backend changes are additive (new column, new endpoints, new query param). All frontend files are new.

## Tasks

- [x] 1. Backend — Add `ended_at` to Exam entity and schemas
  - [x] 1.1 Add `ended_at = Column(DateTime, nullable=True, default=None)` to `src/backend/entities/exam.py`
    - _Requirements: 18.1_
  - [x] 1.2 Add `ended_at: Optional[datetime] = None` to `ExamResponse` and `ExamUpdate` in `src/backend/schemas/exam.py`
    - _Requirements: 18.2, 18.3_

- [x] 2. Backend — Presence filter on participants endpoint
  - [x] 2.1 Add optional `presente: bool | None = None` query param to `GET /exams/{exam_id}/participants` in `src/backend/api/v1/endpoints/participants.py`; filter queryset when param is provided
    - _Requirements: 14.1, 14.2, 14.3_
  - [ ]* 2.2 Write integration test for presence filter (Property 14)
    - **Property 14: Participants presence filter correctness**
    - **Validates: Requirements 14.1, 14.2, 14.3**

- [x] 3. Backend — Bulk participant import endpoint
  - [x] 3.1 Add `QuestionResponseDetail` schema to `src/backend/schemas/scoring.py`
    - Fields: `question_number: int`, `correct_answer: Optional[str]`, `marked_answer: Optional[str]`, `correct: Optional[bool]`, `peso: int`
    - _Requirements: 16.1_
  - [x] 3.2 Implement `POST /exams/{exam_id}/participants/import` in `src/backend/api/v1/endpoints/participants.py`
    - Accept `UploadFile`; detect CSV vs Excel by filename extension; parse with pandas; skip blank/duplicate names; return `ImportResult`
    - Raise 404 if exam not found; raise 422 for unsupported format or missing column
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_
  - [ ]* 3.3 Write property test for bulk import row conservation (Property 15)
    - **Property 15: Bulk import row conservation**
    - **Validates: Requirements 15.3**
  - [ ]* 3.4 Write integration test for import endpoint (blanks, duplicates, bad format)
    - **Validates: Requirements 15.4, 15.5, 15.6, 15.7**

- [x] 4. Backend — Per-participant response detail endpoint
  - [x] 4.1 Implement `GET /exams/{exam_id}/participants/{participant_id}/responses` in `src/backend/api/v1/endpoints/participants.py`
    - Join questions with responses; return `List[QuestionResponseDetail]` ordered by `question_number` ascending
    - `marked_answer=null, correct=false` for missing responses; `correct_answer=null, correct=null` for questions with no answer key
    - Raise 404 if exam or participant not found
    - _Requirements: 16.1, 16.2, 16.3, 16.4_
  - [ ]* 4.2 Write integration test for responses endpoint (Property 17)
    - **Property 17: Participant responses ordered by question number**
    - **Validates: Requirements 16.1**

- [x] 5. Backend — Finish exam endpoint
  - [x] 5.1 Implement `POST /exams/{exam_id}/finish` in `src/backend/api/v1/endpoints/exams.py`
    - Set `status="completed"` and `ended_at=datetime.utcnow()` server-side; return updated `ExamResponse`
    - Raise 409 if already completed; raise 404 if not found
    - _Requirements: 17.1, 17.2, 17.3, 17.4_
  - [ ]* 5.2 Write integration test for finish endpoint (Property 18)
    - **Property 18: Finish exam sets completed state atomically**
    - **Validates: Requirements 17.1, 17.3**

- [x] 6. Checkpoint — Backend complete
  - Ensure all backend tests pass. Ask the user if questions arise.

- [x] 7. Desktop — i18n module
  - [x] 7.1 Create `src/frontend/desktop/i18n.py` with `LANGUAGES`, `STRINGS` dict (pt_BR + en), `set_language`, `get_language`, and `t(key)` fallback helper
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [ ]* 7.2 Write property test for `t(key)` lookup and fallback (Property 9)
    - **Property 9: i18n translation lookup and fallback**
    - **Validates: Requirements 9.2, 9.3**
  - [ ]* 7.3 Write property test for `set_language` rejecting unsupported codes (Property 10)
    - **Property 10: i18n rejects unsupported language codes**
    - **Validates: Requirements 9.4**

- [x] 8. Desktop — AppConfig persistence
  - [x] 8.1 Create `src/frontend/desktop/app_config.py` with `load_config` (returns defaults when file absent) and `save_config` (creates `~/.enem_da_read/` if needed)
    - _Requirements: 10.1, 10.2, 10.3_
  - [ ]* 8.2 Write property test for save/load round-trip (Property 11)
    - **Property 11: AppConfig save/load round-trip**
    - **Validates: Requirements 10.2, 10.3**

- [x] 9. Desktop — Theme module
  - [x] 9.1 Create `src/frontend/desktop/theme.py` with `ThemeConfig` dataclass and `THEMES` dict containing `dark_blue`, `dark_green`, `light`, `high_contrast` entries
    - _Requirements: from design (ThemeConfig interface)_

- [x] 10. Desktop — APILauncher
  - [x] 10.1 Create `src/frontend/desktop/api_launcher.py` with `APILauncher` class
    - `start_if_needed()`: probe `/health`; if unreachable, spawn uvicorn subprocess and poll until ready or timeout; raise `RuntimeError` on timeout
    - `stop()`: terminate only the subprocess this instance started
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 11. Desktop — MobileServerLauncher
  - [x] 11.1 Create `src/frontend/desktop/mobile_server.py` with `MobileServerLauncher` class
    - LAN IP detection via `socket.getaddrinfo`; fallback to `127.0.0.1` with warning
    - Port retry on `port+1`, `port+2`; raise `OSError` if all fail
    - Serve `mobile_dir` via `http.server.HTTPServer` in a daemon thread
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 12. Desktop — APIClient
  - [x] 12.1 Create `src/frontend/desktop/api_client.py` with `APIClient` async httpx wrapper
    - Implement all methods from design: `list_exams`, `get_exam_results`, `get_exam_statistics`, `list_participants` (with optional `presente` param), `update_participant`, `add_participant`, `import_participants`, `get_participant_score`, `get_participant_responses`, `create_exam`, `finish_exam`
    - Raise `APIError` on non-2xx; never return `None` (return `[]` or `{}` for empty)
    - _Requirements: from design (APIClient interface)_
  - [ ]* 12.2 Write unit tests for `APIClient` using `respx` mocks
    - Cover: `list_participants?presente=true`, `import_participants`, `finish_exam` (404 and 409), `get_participant_responses`
    - _Requirements: from design testing strategy_

- [x] 13. Desktop — Shared components
  - [x] 13.1 Create `src/frontend/desktop/views/components.py` with `SharePanel`, `LanguageSwitcher`, `EndExamButton`, `ReadOnlyBanner`
    - `SharePanel`: QR code via `qrcode` lib → base64 → `ft.Image`; read-only URL field; copy-link button
    - `EndExamButton`: confirmation dialog; calls `finish_exam`; handles 409 as success; re-enables on other errors
    - `ReadOnlyBanner`: lock icon + `ended_at` timestamp; amber background
    - `LanguageSwitcher`: `ft.Dropdown` pre-selected to `get_language()`; calls `on_change(lang)` on selection
    - _Requirements: 3.1, 3.2, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 14. Desktop — LanguageSelectView
  - [x] 14.1 Create `src/frontend/desktop/views/language_select.py` with `LanguageSelectView`
    - Two large buttons (🇧🇷 Português / 🇺🇸 English); calls `on_language_selected(lang)`; does not call `set_language` or `save_config` directly
    - _Requirements: 11.1, 11.2_

- [x] 15. Desktop — HomeView
  - [x] 15.1 Create `src/frontend/desktop/views/home.py` with `HomeView`
    - Section A: create form with inline validation (blank name, non-positive int); calls `create_exam` on valid submit; invokes `on_exam_ready`
    - Section B: scrollable exam list from `list_exams()`; empty state message; refresh button; 🔒 badge for completed exams
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 16. Desktop — DashboardView
  - [x] 16.1 Create `src/frontend/desktop/views/dashboard.py` with `DashboardView`
    - `ft.DataTable` with Rank, Name, Score, Accuracy % columns; stats row (avg/highest/lowest) above table
    - Refresh button; row click opens `ParticipantDetailView`; `read_only` flag passed through
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 17. Desktop — PresenceView
  - [x] 17.1 Create `src/frontend/desktop/views/presence.py` with `PresenceView`
    - Participant rows with `ft.Switch` bound to `presente`; optimistic toggle with revert on API error
    - `read_only=True` disables all switches and hides import button; name click opens `ParticipantDetailView`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 18. Desktop — ParticipantDetailView
  - [x] 18.1 Create `src/frontend/desktop/views/participant_detail.py` with `ParticipantDetailView`
    - `asyncio.gather` for parallel `get_participant_score` + `get_participant_responses` calls
    - Header: name, rank badge, final score; score breakdown row; per-question `ft.DataTable` (Q#, Correct Answer, Their Answer, Result ✓/✗/—, Weight)
    - Essay points field with save button; validation (negative/non-numeric → snackbar, no API call); `read_only` hides save button
    - Close button invokes `on_close()`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 19. Checkpoint — Desktop views complete
  - Ensure all desktop view files are importable and tests pass. Ask the user if questions arise.

- [x] 20. Desktop — main.py entry point
  - [x] 20.1 Create `src/frontend/desktop/main.py` wiring everything together
    - On startup: `load_config()` → show `LanguageSelectView` if no language saved → `set_language` → start `APILauncher` → start `MobileServerLauncher` → show `HomeView`
    - `openExamWorkspace(exam_id)`: fetch exam, determine `read_only`, build `DashboardView` + `PresenceView` + `SharePanel` + `EndExamButton`/`ReadOnlyBanner`
    - `page.on_disconnect`: call `launcher.stop()` and `mobile_server.stop()`
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 11.1, 11.2, 11.3_

- [ ] 21. Mobile — HTML upload page
  - [ ] 21.1 Create `src/frontend/mobile/index.html` with Tailwind CSS upload page
    - Exam `<select>` populated via `GET /api/v1/exams` on load; participant `<select>` populated via `?presente=true` on exam change
    - File input with live image preview; client-side validation (5 MB limit, JPEG/PNG only)
    - Inline i18n via `data-i18n` attributes and `STRINGS` object (pt_BR + en); language flag toggle; `localStorage` persistence
    - Submit button re-enabled after completion; result shown inline
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 13.1, 13.2, 13.3_
  - [ ] 21.2 Create `src/frontend/mobile/static/upload.js` with fetch-based form submission logic
    - `submitForm()`, `loadPresentParticipants(examId)`, `previewImage(input)`, `setLanguage(lang)`, `applyTranslations()`
    - _Requirements: 12.4, 13.2_

- [ ] 22. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use `hypothesis`; API integration tests use `pytest-asyncio` + `httpx.AsyncClient`; `APIClient` unit tests use `respx`
- Each task references specific requirements for traceability
- Backend tasks (1–5) should be completed before desktop tasks that depend on new endpoints
