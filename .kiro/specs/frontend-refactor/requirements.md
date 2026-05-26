# Requirements Document

## Introduction

This document defines the requirements for the "frontend-refactor" feature of the "Enem da Read" system. The feature introduces two new client interfaces — a Flet-based desktop application and a mobile-optimized HTML/Tailwind web page — that consume the existing FastAPI REST API. It also adds minimal backend extensions: a bulk-import endpoint, a per-participant response-detail endpoint, a finish-exam endpoint, a presence filter on the participants list, and an `ended_at` field on the Exam entity.

## Glossary

- **App**: The Flet desktop application (`src/frontend/desktop/`)
- **APIClient**: The async HTTP wrapper (`api_client.py`) used by the desktop app to call the FastAPI backend
- **APILauncher**: The subprocess manager (`api_launcher.py`) that auto-starts uvicorn when the desktop app opens
- **MobileServerLauncher**: The static file server (`mobile_server.py`) that serves the mobile upload page over LAN
- **SharePanel**: The Flet component that displays the mobile URL as a QR code and copyable link
- **HomeView**: The entry screen for creating or opening an exam
- **DashboardView**: The ranked participant table and statistics view
- **PresenceView**: The attendance management view with per-participant presence toggles
- **ParticipantDetailView**: The overlay showing full per-participant score and per-question answer breakdown
- **EndExamButton**: The component that triggers the exam-finish confirmation flow
- **ReadOnlyBanner**: The banner displayed when an exam is locked (status = "completed")
- **i18n_Module**: The `i18n.py` module providing translated strings via `t(key)` for the desktop app
- **AppConfig**: The `app_config.py` module persisting language and theme to `~/.enem_da_read/config.json`
- **LanguageSelectView**: The first-launch language selection screen
- **Mobile_Page**: The HTML + Tailwind upload page (`src/frontend/mobile/index.html`)
- **API**: The FastAPI REST backend (`src/backend/api/`)
- **Exam**: The exam entity and its associated SQLAlchemy model and Pydantic schemas
- **ImportResult**: The JSON response shape `{"imported": int, "skipped": int, "errors": list[str]}`
- **QuestionResponseDetail**: The Pydantic schema for per-question answer breakdown returned by the responses endpoint

---

## Requirements

### Requirement 1: Desktop App Startup and API Auto-Start

**User Story:** As an exam administrator, I want the desktop app to start the API server automatically, so that I do not need to run a separate terminal command before using the application.

#### Acceptance Criteria

1. WHEN the App starts, THE APILauncher SHALL probe `GET /health` and, if the server is not reachable, spawn a uvicorn subprocess
2. WHEN the API server becomes reachable within the configured timeout, THE App SHALL hide the loading indicator and display the main UI
3. IF the API server does not become reachable within the configured timeout, THEN THE App SHALL display a blocking error dialog with the message from `t("api_start_error")`
4. WHEN the App window closes, THE APILauncher SHALL terminate any uvicorn subprocess it started
5. THE APILauncher SHALL NOT terminate a server that was already running before the App started

---

### Requirement 2: Mobile Static File Server

**User Story:** As an exam administrator, I want the desktop app to serve the mobile upload page over the local network, so that participants can access it from their phones without any additional setup.

#### Acceptance Criteria

1. WHEN `MobileServerLauncher.start()` is called, THE MobileServerLauncher SHALL detect the machine's LAN IP and return a URL of the form `http://{lan_ip}:{port}/index.html`
2. IF LAN IP detection fails, THEN THE MobileServerLauncher SHALL fall back to `127.0.0.1`, log a warning, and show a snackbar with `t("mobile_server_warning")`
3. IF the requested port is already in use, THEN THE MobileServerLauncher SHALL retry on `port+1` and `port+2` before raising `OSError`
4. WHEN the App window closes, THE MobileServerLauncher SHALL stop the background HTTP server thread

---

### Requirement 3: SharePanel

**User Story:** As an exam administrator, I want to share the mobile upload URL with participants via QR code or a copyable link, so that they can quickly access the upload page on their phones.

#### Acceptance Criteria

1. WHEN SharePanel is built with a URL, THE SharePanel SHALL display a QR code image generated from that URL, a read-only URL text field, and a "Copy link" button
2. WHEN the "Copy link" button is clicked, THE SharePanel SHALL call `page.set_clipboard(url)` with the panel's URL

---

### Requirement 4: HomeView — Create and Open Exams

**User Story:** As an exam administrator, I want a home screen where I can create a new exam or open an existing one, so that I can manage multiple exam sessions.

#### Acceptance Criteria

1. WHEN HomeView loads, THE HomeView SHALL call `list_exams()` and render the returned exams in the "Open Existing Exam" list
2. WHEN the exam list is empty, THE HomeView SHALL display the message from `t("no_exams")`
3. WHEN a user submits the create form with a blank exam name or a non-positive-integer question count or symbolic note, THE HomeView SHALL display inline `error_text` on each offending field and make no API call
4. WHEN a user submits a valid create form, THE HomeView SHALL call `create_exam()` and invoke `on_exam_ready` with the new `exam_id`
5. WHEN a user clicks an existing exam row, THE HomeView SHALL invoke `on_exam_ready` with that exam's `exam_id`
6. WHEN a completed exam is shown in the list, THE HomeView SHALL display a lock icon (🔒) and the `t("exam_completed")` status badge alongside it

---

### Requirement 5: DashboardView

**User Story:** As an exam administrator, I want to see a ranked table of participants with scores and statistics, so that I can monitor exam performance in real time.

#### Acceptance Criteria

1. WHEN DashboardView loads, THE DashboardView SHALL display a `ft.DataTable` with columns Rank, Name, Score, and Accuracy %
2. WHEN DashboardView loads, THE DashboardView SHALL display aggregate statistics (average, highest, and lowest score) above the table
3. WHEN the refresh button is clicked, THE DashboardView SHALL call `load()` again to fetch updated data
4. WHEN a participant row is clicked, THE DashboardView SHALL open `ParticipantDetailView` for that participant
5. WHILE `read_only=True`, THE DashboardView SHALL still allow opening `ParticipantDetailView` on row click

---

### Requirement 6: PresenceView — Attendance Management

**User Story:** As an exam administrator, I want to toggle participant attendance, so that only present participants are included in the mobile upload selector.

#### Acceptance Criteria

1. WHEN PresenceView loads, THE PresenceView SHALL call `list_participants(exam_id)` and render each participant as a row with a name and a presence toggle
2. WHEN a presence toggle is changed, THE PresenceView SHALL immediately call `update_participant(id, {"presente": new_value})` (optimistic UI)
3. IF `update_participant` returns an error, THEN THE PresenceView SHALL revert the toggle to its previous state and display a snackbar with the error message
4. WHILE `read_only=True`, THE PresenceView SHALL disable all presence toggles and hide the "Import Participants" button
5. WHEN a participant name is clicked (not the toggle), THE PresenceView SHALL open `ParticipantDetailView` for that participant

---

### Requirement 7: ParticipantDetailView

**User Story:** As an exam administrator, I want to see a participant's full score breakdown and per-question answers, so that I can review and correct their results.

#### Acceptance Criteria

1. WHEN ParticipantDetailView loads, THE ParticipantDetailView SHALL call `get_participant_score` and `get_participant_responses` in parallel and render the participant's name, rank badge, final score, score breakdown row, and per-question table
2. WHEN the per-question table is rendered, THE ParticipantDetailView SHALL display columns: Q#, Correct Answer, Their Answer, Result (✓ / ✗ / —), and Weight
3. WHEN the user enters a valid non-negative number in the essay points field and clicks "Save essay points", THE ParticipantDetailView SHALL call `update_participant` with `{"essay_points": value}` and show a `t("saved")` snackbar
4. IF the essay points value is negative or non-numeric, THEN THE ParticipantDetailView SHALL show a validation snackbar with `t("error_essay_points")` and make no API call
5. WHILE `read_only=True`, THE ParticipantDetailView SHALL render the essay points field as read-only and hide the "Save essay points" button
6. WHEN the close button is clicked, THE ParticipantDetailView SHALL invoke `on_close()`

---

### Requirement 8: End Exam and Read-Only Mode

**User Story:** As an exam administrator, I want to permanently lock an exam when it is finished, so that results cannot be accidentally modified after the session ends.

#### Acceptance Criteria

1. WHEN the "End Exam" button is clicked, THE App SHALL display a confirmation dialog with `t("end_exam_confirm")` and `t("end_exam_warning")`
2. WHEN the user confirms the dialog, THE App SHALL call `finish_exam(exam_id)` and transition the entire workspace to read-only mode
3. IF `finish_exam` returns 409 Conflict, THEN THE App SHALL treat it as success and set the workspace to read-only without showing an error
4. IF `finish_exam` returns any other error, THEN THE App SHALL show a snackbar with the error message and re-enable the "End Exam" button
5. WHILE `exam["status"] == "completed"`, THE App SHALL display `ReadOnlyBanner` with the `ended_at` timestamp and hide the `EndExamButton`

---

### Requirement 9: Desktop i18n

**User Story:** As an exam administrator, I want the desktop application to be available in Portuguese (Brazil) and English, so that I can use it in my preferred language.

#### Acceptance Criteria

1. THE i18n_Module SHALL support the language codes `"pt_BR"` and `"en"`
2. WHEN `set_language(lang)` is called with a supported language code, THE i18n_Module SHALL return translated strings for that language via `t(key)`
3. WHEN `t(key)` is called with a key not present in the active language dictionary, THE i18n_Module SHALL return the key string itself without raising an exception
4. IF `set_language(lang)` is called with an unsupported language code, THEN THE i18n_Module SHALL raise `ValueError`

---

### Requirement 10: AppConfig — Settings Persistence

**User Story:** As an exam administrator, I want my language and theme preferences to be saved between sessions, so that I do not have to reconfigure the app every time I open it.

#### Acceptance Criteria

1. WHEN `load_config()` is called and no config file exists, THE AppConfig SHALL return `{"language": "pt_BR", "theme": "dark_blue"}`
2. WHEN `save_config(config)` is called, THE AppConfig SHALL write the config to `~/.enem_da_read/config.json`, creating the directory if it does not exist
3. WHEN `load_config()` is called after `save_config(config)`, THE AppConfig SHALL return a dict equivalent to the one that was saved

---

### Requirement 11: First-Launch Language Selection

**User Story:** As a first-time user, I want to choose my preferred language before the app loads, so that all UI text is immediately in my language.

#### Acceptance Criteria

1. WHEN the App starts and no config file exists, THE App SHALL display `LanguageSelectView` before showing `HomeView`
2. WHEN the user selects a language in `LanguageSelectView`, THE App SHALL call `on_language_selected` with the chosen language code, persist the choice via `save_config`, and proceed to the normal startup flow
3. WHEN the App starts and a config file with a language value exists, THE App SHALL skip `LanguageSelectView` and apply the saved language directly

---

### Requirement 12: Mobile Upload Page

**User Story:** As a participant, I want to upload my answer sheet image from my phone, so that my responses are recorded without needing a desktop computer.

#### Acceptance Criteria

1. WHEN the Mobile_Page loads, THE Mobile_Page SHALL populate the exam selector by calling `GET /api/v1/exams`
2. WHEN an exam is selected, THE Mobile_Page SHALL populate the participant selector by calling `GET /api/v1/exams/{exam_id}/participants?presente=true` and showing only present participants
3. WHEN a valid image file is selected, THE Mobile_Page SHALL display a preview of the image before submission
4. WHEN the user submits a valid form (exam selected, participant selected, image selected), THE Mobile_Page SHALL POST `multipart/form-data` to `/api/v1/exams/{exam_id}/ocr/answer-sheet?participant_id={id}` and display the result inline
5. IF the selected file exceeds 5 MB, THEN THE Mobile_Page SHALL display a client-side error message and not submit the form
6. IF the selected file is not JPEG or PNG, THEN THE Mobile_Page SHALL display a client-side error message and not submit the form
7. WHEN the form submission completes (success or error), THE Mobile_Page SHALL re-enable the submit button

---

### Requirement 13: Mobile i18n

**User Story:** As a participant, I want the mobile upload page to be available in Portuguese (Brazil) and English, so that I can use it in my preferred language.

#### Acceptance Criteria

1. WHEN the Mobile_Page loads, THE Mobile_Page SHALL apply the language stored in `localStorage` under the key `"lang"`, defaulting to `"pt_BR"` if not set
2. WHEN `setLanguage(lang)` is called, THE Mobile_Page SHALL update all `data-i18n` elements to the translated strings for `lang` and persist `lang` in `localStorage`
3. WHEN the language flag toggle is clicked, THE Mobile_Page SHALL call `setLanguage` with the corresponding language code

---

### Requirement 14: Backend — Participants Presence Filter

**User Story:** As a developer, I want the participants list endpoint to support filtering by presence, so that the mobile page can show only present participants.

#### Acceptance Criteria

1. WHEN `GET /exams/{exam_id}/participants` is called without the `presente` query parameter, THE API SHALL return all participants for that exam
2. WHEN `GET /exams/{exam_id}/participants?presente=true` is called, THE API SHALL return only participants where `presente=true`
3. WHEN `GET /exams/{exam_id}/participants?presente=false` is called, THE API SHALL return only participants where `presente=false`

---

### Requirement 15: Backend — Bulk Participant Import

**User Story:** As an exam administrator, I want to import a list of participants from a CSV or Excel file, so that I can quickly populate an exam without entering names one by one.

#### Acceptance Criteria

1. WHEN `POST /exams/{exam_id}/participants/import` is called with a valid CSV file containing a `nome` or `Nome` column, THE API SHALL create participants and return an `ImportResult`
2. WHEN `POST /exams/{exam_id}/participants/import` is called with a valid Excel file containing a `Nome` column, THE API SHALL create participants and return an `ImportResult`
3. FOR ALL valid import files, THE API SHALL ensure that `imported + skipped + len(errors)` equals the total number of non-header rows in the file
4. WHEN the import file contains blank rows or names already present in the exam, THE API SHALL skip those rows and increment the `skipped` count accordingly
5. IF the uploaded file format is not CSV or Excel, THEN THE API SHALL return `422 Unprocessable Entity`
6. IF the required column (`nome` / `Nome`) is missing from the file, THEN THE API SHALL return `422 Unprocessable Entity`
7. IF the `exam_id` does not exist, THEN THE API SHALL return `404 Not Found`

---

### Requirement 16: Backend — Per-Participant Response Detail

**User Story:** As an exam administrator, I want to see a per-question answer breakdown for each participant, so that I can identify which questions were answered incorrectly.

#### Acceptance Criteria

1. WHEN `GET /exams/{exam_id}/participants/{participant_id}/responses` is called, THE API SHALL return a list of `QuestionResponseDetail` objects ordered by `question_number` ascending
2. WHEN a question has no recorded response for the participant, THE API SHALL return `marked_answer=null` and `correct=false` for that question
3. WHEN a question has no `correct_answer` defined, THE API SHALL return `correct_answer=null` and `correct=null` for that question
4. IF the `exam_id` or `participant_id` does not exist, THEN THE API SHALL return `404 Not Found`

---

### Requirement 17: Backend — Finish Exam Endpoint

**User Story:** As an exam administrator, I want a dedicated endpoint to lock an exam, so that the completed state is set atomically with a server-side timestamp.

#### Acceptance Criteria

1. WHEN `POST /exams/{exam_id}/finish` is called, THE API SHALL set `status="completed"` and `ended_at` to the current UTC datetime and return the updated `ExamResponse`
2. THE API SHALL set `ended_at` server-side; the request body SHALL be empty
3. IF the exam is already `completed`, THEN THE API SHALL return `409 Conflict`
4. IF the `exam_id` does not exist, THEN THE API SHALL return `404 Not Found`

---

### Requirement 18: Backend — Exam Entity `ended_at` Field

**User Story:** As a developer, I want the Exam entity to record when an exam was finished, so that the desktop app can display the completion timestamp.

#### Acceptance Criteria

1. THE Exam entity SHALL include an `ended_at` column of type `DateTime`, nullable, with a default of `None`
2. THE `ExamResponse` Pydantic schema SHALL include `ended_at` as `Optional[datetime]`, defaulting to `None`
3. THE `ExamUpdate` Pydantic schema SHALL include `ended_at` as `Optional[datetime]`
