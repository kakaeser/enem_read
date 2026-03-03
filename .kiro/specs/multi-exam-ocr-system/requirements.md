# Requirements Document: Multi-Exam OCR System

## Introduction

This document specifies requirements for transforming the "Enem da Read" application from a single-exam system into a multi-exam system with OCR (Optical Character Recognition) capabilities. The system will enable administrators to manage multiple exam sessions, import answer keys and participant responses via photo scanning, and maintain historical exam data with automated scoring.

## Glossary

- **Exam**: A complete exam session with associated questions, participants, and configuration settings
- **Exam_Manager**: The system component responsible for creating and managing exam sessions
- **Answer_Key**: The official list of correct answers for all questions in an exam
- **Answer_Sheet**: A participant's marked answers for an exam
- **OCR_Service**: The system component that extracts text and answer data from uploaded photos
- **Question**: An individual exam question with a number, weight, and correct answer
- **Participant**: A person taking an exam, associated with a specific exam session
- **Response**: A participant's marked answer for a specific question
- **Score_Calculator**: The system component that calculates participant scores by comparing marked answers with correct answers
- **Exam_History_Service**: The system component that retrieves and displays past exam data
- **Photo_Upload_Interface**: The mobile web interface for uploading photos via mobile devices
- **Web_PC_Admin_Interface**: The desktop web interface for exam control, participant management, and real-time monitoring (accessible via localhost)
- **Monitor_Client**: Any PC connected to localhost that can view the real-time exam dashboard in read-only mode
- **Administrator**: A user with permissions to create exams, upload photos, and view results
- **Marked_Answer**: The answer option (A, B, C, D, E, etc.) that a participant selected
- **Correct_Answer**: The official correct answer option for a question
- **Symbolic_Note**: The maximum normalized score for an exam (e.g., 1000 points)

## Requirements

### Requirement 1: Exam Entity Management

**User Story:** As an administrator, I want to create and manage multiple exam sessions, so that I can organize different exams independently with their own configurations.

#### Acceptance Criteria

1. THE Exam_Manager SHALL create a new Exam entity with exam_id, exam_name, questions_numbers, and symbolic_note
2. WHEN an Exam is created, THE Exam_Manager SHALL assign a unique exam_id as the primary key
3. THE Exam_Manager SHALL store exam_name as a text field with minimum length of 1 character and maximum length of 255 characters
4. THE Exam_Manager SHALL store questions_numbers as a positive integer representing the total number of questions
5. THE Exam_Manager SHALL store symbolic_note as a positive integer representing the maximum normalized score
6. THE Exam_Manager SHALL allow administrators to update exam configuration fields after creation
7. WHEN an Exam is deleted, THE Exam_Manager SHALL cascade delete all associated Questions, Responses, and Participant associations

### Requirement 2: Enhanced Question Entity

**User Story:** As an administrator, I want questions to store correct answers and be associated with specific exams, so that the system can automatically grade participant responses.

#### Acceptance Criteria

1. THE Exam_Manager SHALL add a question_correct_answer field to the Questao entity storing answer options (A, B, C, D, E, or other valid options)
2. THE Exam_Manager SHALL add an exam_id foreign key field to the Questao entity referencing the Exam table
3. WHEN a Question is created, THE Exam_Manager SHALL require a valid exam_id association
4. THE Exam_Manager SHALL maintain existing numero (question number) and peso (weight) fields
5. THE Exam_Manager SHALL enforce that question_correct_answer contains only valid answer option characters
6. THE Exam_Manager SHALL allow question_correct_answer to be null initially and populated later via OCR import
7. FOR ALL Questions associated with an Exam, THE Exam_Manager SHALL ensure question numbers are unique within that exam

### Requirement 3: Enhanced Response Entity

**User Story:** As an administrator, I want responses to store the actual marked answers instead of just boolean correctness, so that I can review participant answers and support flexible grading.

#### Acceptance Criteria

1. THE Exam_Manager SHALL add a marked_answer field to the Resposta entity storing the answer option the participant selected
2. THE Exam_Manager SHALL add an exam_id foreign key field to the Resposta entity referencing the Exam table
3. THE Exam_Manager SHALL remove the acertou (boolean) field from the Resposta entity
4. THE Exam_Manager SHALL maintain existing user_id and quest_id foreign key fields
5. THE Exam_Manager SHALL enforce that marked_answer contains only valid answer option characters
6. THE Exam_Manager SHALL maintain the unique constraint on (user_id, quest_id) combination
7. WHEN a Response is created, THE Exam_Manager SHALL require valid user_id, quest_id, and exam_id associations

### Requirement 4: Enhanced Participant Entity

**User Story:** As an administrator, I want participants to be associated with specific exam sessions, so that I can track which participants took which exams.

#### Acceptance Criteria

1. THE Exam_Manager SHALL add an exam_id foreign key field to the Participante entity referencing the Exam table
2. WHEN a Participant is registered, THE Exam_Manager SHALL require a valid exam_id association
3. THE Exam_Manager SHALL maintain existing nome (name) and presente (attendance) fields
4. THE Exam_Manager SHALL allow the same person name to participate in multiple exams with different exam_id values
5. THE Exam_Manager SHALL enforce that each Participant record is uniquely associated with one exam session

### Requirement 5: Official Answer Key OCR Import

**User Story:** As an administrator, I want to upload photos of official answer keys and have the system extract correct answers automatically, so that I can quickly populate question data without manual entry.

#### Acceptance Criteria

1. WHEN an administrator uploads an answer key photo, THE Photo_Upload_Interface SHALL accept image files in JPEG, PNG, PDF, or HEIC formats
2. WHEN an answer key photo is uploaded, THE OCR_Service SHALL extract question numbers and corresponding correct answer options
3. THE OCR_Service SHALL validate that extracted question numbers are positive integers within the exam's questions_numbers range
4. THE OCR_Service SHALL validate that extracted answer options match valid answer characters (A, B, C, D, E, etc.)
5. WHEN OCR extraction completes successfully, THE Exam_Manager SHALL populate the Questao table with question numbers and correct_answer values for the specified exam_id
6. IF OCR extraction fails or produces invalid data, THEN THE OCR_Service SHALL return a descriptive error message indicating the failure reason
7. WHEN answer key data is imported, THE Exam_Manager SHALL allow administrators to manually edit question weights after import
8. THE OCR_Service SHALL process answer key photos within 30 seconds for standard answer sheets containing up to 100 questions

### Requirement 6: Participant Answer Sheet OCR Import

**User Story:** As an administrator, I want to upload photos of participant answer sheets and have the system extract marked answers automatically, so that I can efficiently process exam corrections without manual data entry.

#### Acceptance Criteria

1. WHEN an administrator uploads a participant answer sheet photo, THE Photo_Upload_Interface SHALL accept image files in JPEG, PNG, or HEIC formats
2. WHEN an answer sheet photo is uploaded, THE Photo_Upload_Interface SHALL require the administrator to specify the associated participant_id and exam_id
3. WHEN an answer sheet photo is uploaded, THE OCR_Service SHALL extract marked answer options for each question
4. THE OCR_Service SHALL validate that extracted question numbers correspond to existing questions in the specified exam
5. THE OCR_Service SHALL validate that extracted marked answers match valid answer option characters
6. WHEN OCR extraction completes successfully, THE Exam_Manager SHALL populate the Resposta table with user_id, quest_id, exam_id, and marked_answer values
7. IF OCR extraction fails or produces invalid data, THEN THE OCR_Service SHALL return a descriptive error message indicating the failure reason
8. WHEN a Response already exists for a participant-question combination, THE Exam_Manager SHALL update the marked_answer value instead of creating a duplicate
9. THE OCR_Service SHALL process answer sheet photos within 30 seconds for standard sheets containing up to 100 questions
10. IF the OCR_Service cannot confidently identify a marked answer for a question, THEN THE OCR_Service SHALL flag that question for manual review

### Requirement 7: Automated Score Calculation

**User Story:** As an administrator, I want the system to automatically calculate participant scores by comparing marked answers with correct answers, so that I can get instant results without manual grading.

#### Acceptance Criteria

1. WHEN calculating a participant's score, THE Score_Calculator SHALL compare each Response.marked_answer with the corresponding Question.question_correct_answer
2. THE Score_Calculator SHALL count a response as correct when marked_answer exactly matches question_correct_answer (case-insensitive)
3. WHEN calculating total score, THE Score_Calculator SHALL sum the peso (weight) values for all correct responses
4. THE Score_Calculator SHALL calculate the raw score as the sum of weights for correct answers
5. THE Score_Calculator SHALL calculate the normalized score using the formula: (raw_score / total_possible_score) * symbolic_note
6. WHERE a Response has a null or empty marked_answer, THE Score_Calculator SHALL treat it as incorrect
7. WHERE a Question has a null or empty question_correct_answer, THE Score_Calculator SHALL exclude that question from score calculation
8. THE Score_Calculator SHALL provide score calculation results within 2 seconds for exams with up to 1000 participants

### Requirement 8: Exam History Management

**User Story:** As an administrator, I want to view a list of all past exams with their details, so that I can access historical exam data and results.

#### Acceptance Criteria

1. THE Exam_History_Service SHALL retrieve all Exam records ordered by creation date descending
2. WHEN displaying exam list, THE Exam_History_Service SHALL show exam_name, exam_date, total participants count, and total questions count for each exam
3. WHEN an administrator selects a specific exam, THE Exam_History_Service SHALL display complete exam details including all configuration fields
4. WHEN viewing exam details, THE Exam_History_Service SHALL display the list of all participants associated with that exam
5. WHEN viewing exam details, THE Exam_History_Service SHALL display the list of all questions with their numbers, weights, and correct answers
6. THE Exam_History_Service SHALL allow administrators to filter exams by date range
7. THE Exam_History_Service SHALL allow administrators to search exams by name using partial text matching

### Requirement 9: Exam Results Viewing

**User Story:** As an administrator, I want to view detailed results for a specific exam, so that I can analyze participant performance and identify trends.

#### Acceptance Criteria

1. WHEN viewing results for an exam, THE Exam_History_Service SHALL display a ranked list of all participants with their calculated scores
2. THE Exam_History_Service SHALL display both raw scores and normalized scores for each participant
3. WHEN viewing a participant's exam results, THE Exam_History_Service SHALL display all questions with marked answers, correct answers, and correctness status
4. THE Exam_History_Service SHALL calculate and display aggregate statistics including average score, median score, highest score, and lowest score
5. THE Exam_History_Service SHALL allow administrators to export exam results to Excel format with participant names, scores, and detailed answer breakdowns
6. THE Exam_History_Service SHALL display the percentage of participants who answered each question correctly
7. THE Exam_History_Service SHALL identify questions with the lowest correct answer rates for difficulty analysis

### Requirement 10: Cross-Exam Performance Comparison

**User Story:** As an administrator, I want to compare participant performance across multiple exams, so that I can track progress and identify learning trends.

#### Acceptance Criteria

1. WHERE a participant has taken multiple exams, THE Exam_History_Service SHALL display a performance timeline showing scores across all exams
2. THE Exam_History_Service SHALL calculate average performance metrics for participants across multiple exams
3. THE Exam_History_Service SHALL allow administrators to select multiple exams for side-by-side comparison
4. WHEN comparing exams, THE Exam_History_Service SHALL normalize scores to a common scale for fair comparison
5. THE Exam_History_Service SHALL identify participants who appear in multiple selected exams
6. THE Exam_History_Service SHALL display performance trends using visual indicators (improving, declining, stable)

### Requirement 11: OCR Confidence and Manual Review

**User Story:** As an administrator, I want to review OCR results with low confidence scores, so that I can ensure data accuracy before finalizing exam results.

#### Acceptance Criteria

1. WHEN the OCR_Service processes a photo, THE OCR_Service SHALL assign a confidence score (0-100%) to each extracted answer
2. WHERE an extracted answer has confidence below 80%, THE OCR_Service SHALL flag it for manual review
3. THE Photo_Upload_Interface SHALL display flagged answers with visual indicators requiring administrator verification
4. THE Photo_Upload_Interface SHALL allow administrators to manually correct or confirm flagged answers
5. WHEN an administrator corrects an OCR result, THE Exam_Manager SHALL update the corresponding database record with the corrected value
6. THE Photo_Upload_Interface SHALL display the original photo alongside extracted data for verification context
7. THE Exam_Manager SHALL track which responses were manually reviewed and corrected for audit purposes

### Requirement 12: Photo Upload Interface Requirements

**User Story:** As an administrator, I want a mobile-friendly web interface for uploading photos, so that I can easily capture and submit answer sheets using my smartphone.

#### Acceptance Criteria

1. THE Photo_Upload_Interface SHALL provide a responsive web interface optimized for mobile devices with screen widths from 320px to 768px
2. THE Photo_Upload_Interface SHALL allow administrators to capture photos directly using the device camera
3. THE Photo_Upload_Interface SHALL allow administrators to select existing photos from device storage
4. WHEN uploading a photo, THE Photo_Upload_Interface SHALL display a preview before submission
5. THE Photo_Upload_Interface SHALL compress photos to maximum 2MB file size before upload while maintaining OCR readability
6. THE Photo_Upload_Interface SHALL display upload progress with percentage completion
7. WHEN upload completes, THE Photo_Upload_Interface SHALL display OCR processing status with real-time updates
8. IF upload fails due to network issues, THEN THE Photo_Upload_Interface SHALL allow retry without requiring photo reselection
9. THE Photo_Upload_Interface SHALL support batch upload of multiple answer sheets with queue management

### Requirement 13: Database Migration and Backward Compatibility

**User Story:** As a system administrator, I want the database schema to migrate smoothly from the single-exam to multi-exam structure, so that existing data is preserved and the system remains functional during transition.

#### Acceptance Criteria

1. THE Exam_Manager SHALL provide a database migration script that adds new fields to existing entities
2. WHEN migration executes, THE Exam_Manager SHALL create a default Exam record for existing data with exam_name "Legacy Exam"
3. THE Exam_Manager SHALL associate all existing Participante, Questao, and Resposta records with the default Exam
4. THE Exam_Manager SHALL convert existing Config.nota_max and Config.nota_simb values to the default Exam configuration
5. WHERE existing Resposta records have acertou=True, THE Exam_Manager SHALL populate marked_answer with a placeholder value indicating correctness
6. THE Exam_Manager SHALL create database indexes on all new foreign key fields (exam_id) for query performance
7. THE Exam_Manager SHALL validate data integrity after migration and report any inconsistencies

### Requirement 14: OCR Service Integration and Configuration

**User Story:** As a system administrator, I want to configure OCR service parameters, so that I can optimize accuracy for different answer sheet formats.

#### Acceptance Criteria

1. THE OCR_Service SHALL support configuration of answer sheet templates for different exam formats
2. THE OCR_Service SHALL allow administrators to define answer option layouts (vertical, horizontal, grid)
3. THE OCR_Service SHALL support configuration of valid answer characters per exam (e.g., A-E for multiple choice, 0-9 for numeric)
4. THE OCR_Service SHALL allow administrators to specify image preprocessing parameters (contrast, brightness, rotation correction)
5. THE OCR_Service SHALL log all OCR operations with timestamps, input files, extracted data, and confidence scores for debugging
6. WHERE OCR accuracy falls below 90% for a specific template, THE OCR_Service SHALL alert administrators to review template configuration
7. THE OCR_Service SHALL support multiple OCR engine backends (Tesseract, Google Vision API, AWS Textract) with configurable selection

### Requirement 15: Answer Key and Answer Sheet Parsing

**User Story:** As a developer, I want the OCR service to accurately parse structured answer key and answer sheet formats, so that data extraction is reliable and consistent.

#### Acceptance Criteria

1. WHEN parsing an answer key, THE OCR_Service SHALL identify question numbers in sequential order from 1 to questions_numbers
2. THE OCR_Service SHALL extract answer options positioned adjacent to question numbers within a 50-pixel radius
3. WHEN parsing an answer sheet, THE OCR_Service SHALL identify marked answers by detecting filled circles, checkmarks, or shaded regions
4. THE OCR_Service SHALL distinguish between marked and unmarked answer options with minimum 70% confidence
5. WHERE multiple answer options appear marked for a single question, THE OCR_Service SHALL flag it as ambiguous for manual review
6. THE OCR_Service SHALL handle rotated images by detecting orientation and applying automatic rotation correction within ±15 degrees
7. THE OCR_Service SHALL handle poor lighting conditions by applying adaptive histogram equalization before text extraction
8. THE OCR_Service SHALL validate that extracted question numbers are sequential and report any missing or duplicate numbers

## Special Requirements: OCR Round-Trip Testing

### Requirement 16: OCR Accuracy Validation

**User Story:** As a quality assurance engineer, I want to validate OCR accuracy through round-trip testing, so that I can ensure reliable data extraction.

#### Acceptance Criteria

1. THE OCR_Service SHALL provide a test mode that generates synthetic answer sheet images from known data
2. WHEN processing synthetic images, THE OCR_Service SHALL extract data and compare it with the original known data
3. THE OCR_Service SHALL calculate accuracy metrics including precision, recall, and F1-score for OCR extraction
4. FOR ALL synthetic test images, THE OCR_Service SHALL achieve minimum 95% accuracy for answer extraction
5. THE OCR_Service SHALL maintain a test suite of diverse answer sheet formats (clean, noisy, rotated, low-contrast)
6. WHEN OCR accuracy drops below 95% on test suite, THE OCR_Service SHALL fail automated tests and prevent deployment
7. THE OCR_Service SHALL log detailed error analysis for failed extractions including image characteristics and extraction confidence



### Requirement 17: Manual Participant Addition

**User Story:** As an administrator using the desktop web interface, I want to manually add new participants after importing the participant list, so that I can accommodate late registrations or participants not included in the original import file.

#### Acceptance Criteria

1. WHEN viewing the participant list for an exam, THE Web_PC_Admin_Interface SHALL provide an "Add Participant" button or form
2. WHEN adding a participant manually, THE Web_PC_Admin_Interface SHALL require the administrator to enter the participant's name
3. THE Exam_Manager SHALL validate that the participant name is not empty and has minimum length of 1 character and maximum length of 255 characters
4. WHEN a participant is added manually, THE Exam_Manager SHALL create a new Participante record with the specified name and associate it with the current exam_id
5. THE Exam_Manager SHALL set the presente (attendance) field to False by default for manually added participants
6. THE Web_PC_Admin_Interface SHALL display the newly added participant in the participant list immediately after creation
7. THE Exam_Manager SHALL allow administrators to add multiple participants manually without navigating away from the participant list interface
8. WHEN a manually added participant has the same name as an existing participant in the same exam, THE Exam_Manager SHALL allow the creation but display a warning to the administrator
9. THE Web_PC_Admin_Interface SHALL provide inline editing capability to modify participant names after manual addition
10. THE Photo_Upload_Interface (mobile) SHALL NOT provide manual participant addition functionality

### Requirement 18: Essay Extra Points Management

**User Story:** As an administrator, I want to manually add extra points for essay components, so that I can include subjective grading in the final ranking when exams contain essay questions.

#### Acceptance Criteria

1. THE Exam_Manager SHALL add an essay_points field to the Participante entity storing additional points awarded for essay components
2. THE Exam_Manager SHALL allow essay_points to be null or zero by default for participants without essay scores
3. WHEN viewing participant details, THE Web_PC_Admin_Interface SHALL display an editable field for essay_points
4. WHEN viewing participant details, THE Photo_Upload_Interface (mobile) SHALL display an editable field for essay_points
5. THE Web_PC_Admin_Interface SHALL validate that essay_points is a non-negative number (integer or decimal)
6. THE Photo_Upload_Interface SHALL validate that essay_points is a non-negative number (integer or decimal)
7. WHEN calculating final scores, THE Score_Calculator SHALL add essay_points to the normalized score for participants who have essay_points values
8. THE Score_Calculator SHALL calculate the final score using the formula: final_score = normalized_score + essay_points
9. WHEN displaying rankings, THE Exam_History_Service SHALL show both the objective score (without essay) and final score (with essay) for transparency
10. THE Web_PC_Admin_Interface SHALL allow administrators to bulk edit essay_points for multiple participants using a spreadsheet-like interface
11. THE Exam_Manager SHALL log all essay_points modifications with timestamps and administrator identifiers for audit purposes
12. WHEN exporting exam results, THE Exam_History_Service SHALL include essay_points as a separate column in the Excel export

### Requirement 19: Real-Time Exam Dashboard

**User Story:** As an administrator or monitor, I want to view a real-time dashboard showing the current exam status and participant rankings, so that I can monitor exam progress and see live updates as answer sheets are processed.

#### Acceptance Criteria

1. THE Web_PC_Admin_Interface SHALL provide a dedicated "Live Dashboard" view for exams with status "in_progress"
2. THE Web_PC_Admin_Interface SHALL allow the administrator to control the exam (start and end) from the dashboard
3. WHEN any PC connects to the localhost server, THE Web_PC_Admin_Interface SHALL allow Monitor_Clients to view the dashboard in read-only mode
4. THE Monitor_Clients SHALL NOT have access to exam control functions (start, end, edit participants, add essay points)
5. WHEN the dashboard is opened, THE Web_PC_Admin_Interface SHALL display the exam name, start time, and total number of participants
6. THE Web_PC_Admin_Interface SHALL display a real-time participant ranking list ordered by current scores (descending)
7. WHEN a participant's answer sheet is processed and scores are calculated, THE Web_PC_Admin_Interface SHALL update the ranking list within 5 seconds without requiring page refresh
8. THE Web_PC_Admin_Interface SHALL display the following information for each participant in the ranking: rank position, participant name, current score, and number of questions answered
9. THE Web_PC_Admin_Interface SHALL use visual indicators (colors, icons) to highlight score changes and rank position changes
10. THE Web_PC_Admin_Interface SHALL display aggregate statistics including: total participants, participants with submitted answers, participants pending submission, average score, and highest score
11. THE Web_PC_Admin_Interface SHALL display a progress bar showing the percentage of participants who have submitted answer sheets
12. THE Web_PC_Admin_Interface SHALL use WebSocket or Server-Sent Events (SSE) for real-time updates to minimize server load
13. WHEN multiple administrators or Monitor_Clients view the same dashboard, THE Web_PC_Admin_Interface SHALL synchronize updates across all connected clients
14. THE Web_PC_Admin_Interface SHALL allow administrators to filter the ranking view by attendance status (present/absent)
15. THE Web_PC_Admin_Interface SHALL display the dashboard on large screens (projectors, TVs) with optimized font sizes and layouts for visibility from distance
16. THE Web_PC_Admin_Interface SHALL provide a "freeze ranking" option to temporarily pause updates for announcement or screenshot purposes
17. WHEN essay_points are added for a participant, THE Web_PC_Admin_Interface SHALL immediately reflect the updated final score in the dashboard ranking
18. THE Web_PC_Admin_Interface SHALL display a timestamp showing when the ranking was last updated
19. THE Web_PC_Admin_Interface SHALL provide a "Copy Ranking as Text" button that copies the current ranking to clipboard in formatted text
20. WHEN the "Copy Ranking as Text" button is clicked, THE Web_PC_Admin_Interface SHALL format the ranking as: "1º - [Name] - [Score]\n2º - [Name] - [Score]\n..."
21. THE Photo_Upload_Interface (mobile) SHALL NOT provide access to the real-time dashboard view
