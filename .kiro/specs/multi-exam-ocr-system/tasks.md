# Implementation Plan: Multi-Exam OCR System (MVP - First Iteration)

## Overview

This implementation plan focuses on delivering a working MVP with core multi-exam functionality and basic OCR capabilities using Tesseract. The scope is intentionally reduced to deliver value quickly while establishing the foundation for future enhancements.

**In Scope for First Iteration**:
- Core domain entities with relationships (Exam, Question, Participant, Response)
- Database migration from single-exam to multi-exam structure
- Tesseract OCR integration for answer key and answer sheet processing
- Automated score calculation with essay points support
- Basic exam history and results viewing
- Excel export functionality
- FastAPI REST endpoints (no WebSocket/real-time features)
- Web-based admin interface for CRUD operations

**Explicitly Out of Scope**:
- Real-time dashboard with WebSocket/SSE
- Cross-exam performance comparison
- Multiple OCR engine backends (only Tesseract)
- OCR confidence scoring and manual review workflow
- Mobile-optimized photo upload interface
- Monitor client functionality
- Answer sheet template system (use single hardcoded template)

## Tasks

- [x] 1. Database schema design and migration
  - [x] 1.1 Create enhanced entity models with exam_id relationships
    - Create Exam entity model with all fields (exam_id, exam_name, questions_numbers, symbolic_note, timestamps, status)
    - Add exam_id foreign key to Question entity
    - Add exam_id foreign key to Participant entity
    - Add exam_id foreign key to Response entity
    - Add question_correct_answer field to Question entity
    - Replace acertou boolean with marked_answer string in Response entity
    - Add essay_points field to Participant entity
    - Define all SQLAlchemy relationships (one-to-many, cascade deletes)
    - Add database indexes on foreign keys for performance
    - Add unique constraints (exam_id + numero for questions, user_id + quest_id for responses)
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 3.3, 4.1, 18.1_
  
  - [ ]* 1.2 Write property test for exam creation completeness
    - **Property 1: Exam Creation Completeness**
    - **Validates: Requirements 1.1**
  
  - [ ]* 1.3 Write property test for exam ID uniqueness
    - **Property 2: Exam ID Uniqueness**
    - **Validates: Requirements 1.2**
  
  - [x] 1.4 Create database migration script
    - Write migration script to add new tables and columns
    - Create default "Legacy Exam" record for existing data
    - Associate all existing Participante, Questao, Resposta records with legacy exam
    - Migrate Config.nota_max and Config.nota_simb to legacy exam configuration
    - Transform existing Resposta.acertou boolean to marked_answer placeholders
    - Add validation checks for data integrity after migration
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.7_
  
  - [ ]* 1.5 Write unit tests for database migration
    - Test migration creates legacy exam correctly
    - Test all existing records are associated with legacy exam
    - Test data integrity after migration
    - _Requirements: 13.2, 13.3_

- [x] 2. Repository layer with dependency injection
  - [x] 2.1 Create repository interfaces
    - Create IExamRepository interface with CRUD methods
    - Create IQuestionRepository interface with bulk operations
    - Create IResponseRepository interface with upsert support
    - Create IParticipantRepository interface with exam filtering
    - Define async method signatures for all operations
    - _Requirements: 1.1, 2.1, 3.1, 4.1_
  
  - [x] 2.2 Implement async repository classes
    - Implement AsyncExamRepository with SQLAlchemy async queries
    - Implement AsyncQuestionRepository with bulk insert support
    - Implement AsyncResponseRepository with create_or_update logic
    - Implement AsyncParticipantRepository with exam-scoped queries
    - Use async session management with proper transaction handling
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 6.8_
  
  - [ ]* 2.3 Write property test for response uniqueness constraint
    - **Property 6: Response Uniqueness Constraint**
    - **Validates: Requirements 3.6**
  
  - [ ]* 2.4 Write property test for response upsert behavior
    - **Property 9: Response Upsert Behavior**
    - **Validates: Requirements 6.8**
  
  - [ ]* 2.5 Write unit tests for repository layer
    - Test CRUD operations for all repositories
    - Test transaction rollback on errors
    - Test cascade delete behavior
    - _Requirements: 1.7, 3.6, 6.8_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Pydantic schemas for data validation
  - [ ] 4.1 Create request/response schemas
    - Create ExamCreate, ExamUpdate, ExamResponse schemas with validation
    - Create QuestionCreate, QuestionUpdate, QuestionResponse schemas
    - Create ParticipantCreate, ParticipantUpdate, ParticipantResponse schemas
    - Create ResponseCreate, ResponseUpdate, ResponseResponse schemas
    - Add field validators (min/max length, positive integers, valid answer options)
    - _Requirements: 1.3, 1.4, 1.5, 2.1, 2.4, 2.5, 3.1, 3.5, 4.3_
  
  - [ ] 4.2 Create OCR and scoring schemas
    - Create ExtractedAnswer schema with question_number, answer, confidence fields
    - Create AnswerKeyResult schema for OCR processing results
    - Create AnswerSheetResult schema for participant answer extraction
    - Create ScoreBreakdown schema with all score components
    - Create ExamStatistics schema for aggregate metrics
    - _Requirements: 5.2, 6.3, 7.4, 7.5, 9.4_
  
  - [ ]* 4.3 Write property test for exam name validation
    - **Property 3: Exam Name Validation**
    - **Validates: Requirements 1.3**
  
  - [ ]* 4.4 Write property test for OCR answer option validation
    - **Property 8: OCR Answer Option Validation**
    - **Validates: Requirements 5.4**

- [ ] 5. Service layer with business logic
  - [ ] 5.1 Implement ExamManagerService
    - Create ExamManagerService with dependency-injected repositories
    - Implement create_exam, get_exam, update_exam, delete_exam methods
    - Implement list_exams with filtering support
    - Implement add_participant_to_exam method
    - Add validation for exam configuration fields
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7, 17.1, 17.2, 17.3, 17.4_
  
  - [ ]* 5.2 Write property test for cascade delete integrity
    - **Property 4: Cascade Delete Integrity**
    - **Validates: Requirements 1.7**
  
  - [ ]* 5.3 Write property test for question number uniqueness
    - **Property 5: Question Number Uniqueness Within Exam**
    - **Validates: Requirements 2.7**
  
  - [ ] 5.4 Implement ScoreCalculatorService
    - Create ScoreCalculatorService with dependency-injected repositories
    - Implement calculate_participant_score method comparing marked vs correct answers
    - Implement case-insensitive answer comparison logic
    - Calculate raw score as sum of weights for correct responses
    - Calculate normalized score using formula: (raw_score / total_possible_score) * symbolic_note
    - Add essay_points to normalized score for final_score calculation
    - Implement calculate_all_scores for batch processing
    - Implement get_score_breakdown with detailed response analysis
    - Implement calculate_exam_statistics for aggregate metrics
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 18.7, 18.8, 9.4_
  
  - [ ]* 5.5 Write property test for score calculation correctness
    - **Property 10: Score Calculation Correctness**
    - **Validates: Requirements 7.1, 7.2**
  
  - [ ]* 5.6 Write property test for normalized score formula
    - **Property 11: Normalized Score Formula**
    - **Validates: Requirements 7.5**
  
  - [ ]* 5.7 Write property test for final score calculation
    - **Property 12: Final Score Calculation**
    - **Validates: Requirements 18.7, 18.8**
  
  - [ ] 5.8 Implement ExamHistoryService
    - Create ExamHistoryService with dependency-injected repositories
    - Implement get_exam_results with ranked participant list
    - Implement export_results_to_excel using pandas
    - Implement get_question_statistics for difficulty analysis
    - Calculate aggregate statistics (average, median, highest, lowest scores)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  
  - [ ]* 5.9 Write unit tests for service layer
    - Test exam creation and deletion workflows
    - Test score calculation with various scenarios
    - Test exam history retrieval and filtering
    - Test error handling and validation
    - _Requirements: 1.1, 7.1, 8.1, 9.1_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. OCR service with Tesseract integration
  - [ ] 7.1 Implement image preprocessing pipeline
    - Create OCRService class with image preprocessing methods
    - Implement grayscale conversion
    - Implement orientation detection and correction
    - Implement adaptive histogram equalization for lighting correction
    - Implement denoising with fastNlMeansDenoising
    - Implement binarization using Otsu's method
    - _Requirements: 5.1, 6.1_
  
  - [ ] 7.2 Implement answer key OCR processing
    - Create process_answer_key method accepting image file and exam_id
    - Extract question numbers and correct answers using Tesseract
    - Validate extracted question numbers are within exam range
    - Validate extracted answers match valid answer characters
    - Create or update Question records with extracted correct_answer values
    - Return AnswerKeyResult with extraction summary
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7_
  
  - [ ]* 7.3 Write property test for OCR question number validation
    - **Property 7: OCR Question Number Validation**
    - **Validates: Requirements 5.3**
  
  - [ ] 7.4 Implement answer sheet OCR processing
    - Create process_answer_sheet method accepting image file, participant_id, exam_id
    - Extract marked answers for each question using Tesseract
    - Validate extracted question numbers correspond to existing questions
    - Validate extracted marked answers match valid answer characters
    - Create or update Response records with extracted marked_answer values
    - Return AnswerSheetResult with extraction summary
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.8_
  
  - [ ]* 7.5 Write unit tests for OCR service
    - Test image preprocessing with various image conditions
    - Test answer key extraction with sample images
    - Test answer sheet extraction with sample images
    - Test validation logic for extracted data
    - Test error handling for invalid images
    - _Requirements: 5.2, 6.3_

- [ ] 8. FastAPI endpoints and routing
  - [ ] 8.1 Create exam management endpoints
    - Create POST /api/v1/exams endpoint for exam creation
    - Create GET /api/v1/exams endpoint for listing exams
    - Create GET /api/v1/exams/{exam_id} endpoint for exam details
    - Create PATCH /api/v1/exams/{exam_id} endpoint for exam updates
    - Create DELETE /api/v1/exams/{exam_id} endpoint for exam deletion
    - Add dependency injection for services
    - Add error handling with proper HTTP status codes
    - _Requirements: 1.1, 1.6, 1.7_
  
  - [ ] 8.2 Create participant management endpoints
    - Create POST /api/v1/exams/{exam_id}/participants endpoint for manual participant addition
    - Create GET /api/v1/exams/{exam_id}/participants endpoint for listing participants
    - Create PATCH /api/v1/participants/{participant_id} endpoint for updating participant (name, attendance, essay_points)
    - Create DELETE /api/v1/participants/{participant_id} endpoint for participant deletion
    - Add validation for participant data
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 18.3, 18.4, 18.5_
  
  - [ ] 8.3 Create OCR processing endpoints
    - Create POST /api/v1/exams/{exam_id}/ocr/answer-key endpoint for answer key upload
    - Create POST /api/v1/exams/{exam_id}/ocr/answer-sheet endpoint for answer sheet upload
    - Handle multipart/form-data file uploads
    - Add file type validation (JPEG, PNG only for MVP)
    - Add file size validation (max 5MB)
    - Return OCR processing results with extraction summary
    - _Requirements: 5.1, 5.5, 6.1, 6.2, 6.6_
  
  - [ ] 8.4 Create results and export endpoints
    - Create GET /api/v1/exams/{exam_id}/results endpoint for exam results with ranking
    - Create GET /api/v1/exams/{exam_id}/statistics endpoint for aggregate statistics
    - Create GET /api/v1/exams/{exam_id}/export/excel endpoint for Excel export
    - Return ranked participant list with scores
    - Return question statistics with correct answer rates
    - Generate Excel file with pandas and return as downloadable file
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  
  - [ ]* 8.5 Write integration tests for API endpoints
    - Test complete exam creation workflow
    - Test OCR upload and processing workflow
    - Test score calculation and results retrieval
    - Test Excel export functionality
    - Test error responses and validation
    - _Requirements: 1.1, 5.5, 6.6, 9.5_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Configuration and error handling
  - [ ] 10.1 Create application configuration
    - Create Settings class using pydantic-settings
    - Configure database URL (SQLite for development)
    - Configure file upload settings (max size, allowed types)
    - Configure OCR settings (Tesseract path, preprocessing parameters)
    - Add environment variable support with .env file
    - _Requirements: 5.1, 6.1_
  
  - [ ] 10.2 Implement custom exception classes
    - Create AppException base class with status_code and message
    - Create ValidationException for input validation errors
    - Create NotFoundException for missing resources
    - Create OCRProcessingException for OCR failures
    - Create global exception handler for FastAPI
    - Return standardized error response format
    - _Requirements: 5.6, 6.7_
  
  - [ ]* 10.3 Write unit tests for error handling
    - Test validation exceptions are raised correctly
    - Test not found exceptions return 404
    - Test OCR exceptions return appropriate errors
    - Test global exception handler formats errors correctly
    - _Requirements: 5.6, 6.7_

- [ ] 11. Database initialization and async connection
  - [ ] 11.1 Create async database connection handler
    - Create AsyncDBConnectionHandler with async engine
    - Implement get_session dependency for FastAPI
    - Configure connection pooling for async operations
    - Add session lifecycle management (commit/rollback)
    - _Requirements: 1.1, 2.1, 3.1, 4.1_
  
  - [ ] 11.2 Create database initialization script
    - Create init_db function to create all tables
    - Run database migration script if needed
    - Add command-line interface for database setup
    - _Requirements: 13.1, 13.2_

- [ ] 12. Integration and wiring
  - [ ] 12.1 Create FastAPI application instance
    - Create main FastAPI app with metadata
    - Configure CORS middleware for development
    - Register all API routers
    - Add global exception handlers
    - Add startup event for database initialization
    - _Requirements: 1.1, 5.1, 6.1, 9.1_
  
  - [ ] 12.2 Create dependency injection setup
    - Create get_exam_repository dependency
    - Create get_question_repository dependency
    - Create get_response_repository dependency
    - Create get_participant_repository dependency
    - Create get_exam_manager_service dependency
    - Create get_score_calculator_service dependency
    - Create get_exam_history_service dependency
    - Create get_ocr_service dependency
    - Wire all dependencies together
    - _Requirements: 1.1, 5.1, 6.1, 7.1, 9.1_
  
  - [ ]* 12.3 Write end-to-end integration tests
    - Test complete exam workflow from creation to results export
    - Test OCR workflow from upload to score calculation
    - Test participant management workflow
    - Test error scenarios and edge cases
    - _Requirements: 1.1, 5.5, 6.6, 7.1, 9.5_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- This MVP focuses on core functionality with Tesseract OCR only
- Real-time dashboard, multiple OCR engines, and advanced features are deferred to future iterations
- The implementation uses Python with FastAPI, SQLAlchemy async, and Pydantic for validation
- Database migration preserves existing data by creating a "Legacy Exam" record
