"""
OCR Service for processing answer key and answer sheet images.

Architecture:
  - process_answer_key  → Tesseract OCR on clean computer-generated text images.
                          Minimal preprocessing (grayscale + optional Otsu).
                          Aggressive regex to extract number/letter pairs.

  - process_answer_sheet → Pure OpenCV OMR pipeline for ENEM-style bubble sheets.
                           No Tesseract. Contour detection + pixel density voting.
"""

import logging
import re
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pytesseract

from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.schemas.ocr import AnswerKeyResult, AnswerSheetResult, ExtractedAnswer

logger = logging.getLogger(__name__)

# Valid answer characters (A-E)
VALID_ANSWERS = set("ABCDE")

# Aggressive pattern: number, separator(s), then a single letter A-E.
#
# Key design decisions:
#   - \d{1,2}   — only 1 or 2 digit question numbers (1-99).  Prevents
#                 Tesseract noise like "810" matching as question 810 when
#                 the real question is 8.  Adjust to \d{1,3} for 100+ questions.
#   - [^a-zA-Z0-9]+  — ONE OR MORE non-alphanumeric chars as separator.
#                 This requires at least one separator (colon, space, dot, etc.)
#                 between the number and the letter, preventing "2C" from
#                 matching as question 2 = C when it is actually noise.
#   - (?![a-zA-Z])  — letter must not be followed by another letter (avoids
#                 matching mid-word like "ABCDE").
_ANSWER_PATTERN = re.compile(r"\b(\d{1,2})[^a-zA-Z0-9]+([A-Ea-e])(?![a-zA-Z])")

# OMR tuning constants
_MIN_BUBBLE_AREA = 200       # px² — discard tiny noise contours
_MAX_BUBBLE_AREA = 8000      # px² — discard large blobs (text blocks, borders)
_ASPECT_RATIO_TOLERANCE = 0.4  # |w/h - 1| must be < this to be considered circular
_ROW_CLUSTER_TOLERANCE = 0.5   # fraction of median bubble height for row grouping
_ANSWERS_PER_ROW = 5           # A B C D E


class OCRService:
    """Service for OCR processing of answer keys and answer sheets."""

    # ================================================================== #
    # Part 1 – process_answer_key (OCR on clean text images)             #
    # ================================================================== #

    async def process_answer_key(
        self,
        image_file: bytes,
        exam_id: int,
        exam_questions_numbers: int,
        question_repo,
    ) -> AnswerKeyResult:
        """
        Process an answer key image (clean, computer-generated text) and
        persist extracted correct answers.

        Pipeline:
          1. Decode bytes → numpy array
          2. Grayscale conversion
          3. Optional Otsu binarization (only when image is not already clean)
          4. pytesseract.image_to_string with --oem 3 --psm 6
          5. Aggressive regex extraction of all (number, letter) pairs

        Args:
            image_file: Raw image bytes (JPEG, PNG, etc.).
            exam_id: ID of the exam this answer key belongs to.
            exam_questions_numbers: Total number of questions in the exam.
            question_repo: Repository with get_by_exam_id, update, create_bulk.

        Returns:
            AnswerKeyResult with extraction summary.
        """
        try:
            nparr = np.frombuffer(image_file, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return AnswerKeyResult(
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="Failed to decode image file.",
                )

            preprocessed = self._preprocess_answer_key(image)

            # Split the image into vertical columns and run Tesseract on each
            # independently with PSM 6 (single uniform block).  This is far
            # more reliable than PSM 4 on the full image because Tesseract
            # never has to guess where one column ends and another begins.
            full_text = self._ocr_by_columns(preprocessed)

            logger.debug("=== RAW TESSERACT TEXT (answer key) ===\n%s\n===", full_text)
            print("\n\n=== TEXTO BRUTO DO TESSERACT (GABARITO) ===")
            print(full_text)
            print("============================================\n\n")

            extracted = self._parse_answer_key_text(
                full_text, exam_questions_numbers
            )

            if not extracted:
                return AnswerKeyResult(
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="No valid question-answer pairs found in image.",
                )

            await self._save_answer_key(exam_id, extracted, question_repo)

            # Answer key OCR confidence is fixed at 95 — Tesseract on clean
            # text is highly reliable; we don't call image_to_data to keep
            # the pipeline fast.
            avg_conf = 95.0
            flagged = 0

            return AnswerKeyResult(
                exam_id=exam_id,
                extracted_answers=extracted,
                avg_confidence=avg_conf,
                flagged_count=flagged,
                success=True,
            )

        except Exception as exc:
            logger.exception("process_answer_key failed for exam_id=%s", exam_id)
            return AnswerKeyResult(
                exam_id=exam_id,
                extracted_answers=[],
                avg_confidence=0.0,
                flagged_count=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Answer key preprocessing — minimal, non-destructive                 #
    # ------------------------------------------------------------------ #

    def _preprocess_answer_key(self, image: np.ndarray) -> np.ndarray:
        """
        Minimal preprocessing for clean, computer-generated answer key images.

        Steps:
          1. Grayscale conversion (always)
          2. Otsu binarization (only when the image is NOT already high-contrast)

        CLAHE and NlMeansDenoising are intentionally omitted — they destroy
        clean pixels and degrade Tesseract accuracy on digital documents.
        """
        gray = self._to_grayscale(image)

        if self._is_clean_image(gray):
            # Already high-contrast — return as-is to preserve pixel quality
            return gray

        # Low-contrast scan: a single Otsu pass is enough
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    # ------------------------------------------------------------------ #
    # Answer key column-split OCR                                        #
    # ------------------------------------------------------------------ #

    def _ocr_by_columns(self, image: np.ndarray) -> str:
        """
        Detect vertical text columns via projection profile, crop each one,
        upscale 2x, run Tesseract PSM 6 on each independently, and
        concatenate the results.

        Why this works better than running Tesseract on the full image:
          - PSM 6 on a single column is extremely reliable (one uniform block).
          - Tesseract never has to guess column boundaries, so rows are never
            merged across columns.
          - Each column is upscaled independently, maximising glyph resolution
            for the B↔8 / A↔4 disambiguation.

        Falls back to a single full-image pass if column detection fails.
        """
        columns = self._detect_columns(image)

        if not columns:
            # Fallback: treat the whole image as one column
            columns = [(0, image.shape[1])]

        config = r"--oem 3 --psm 6"
        parts: list[str] = []

        for x_start, x_end in columns:
            strip = image[:, x_start:x_end]

            # 2x upscale — most effective fix for small-glyph confusion
            upscaled = cv2.resize(
                strip,
                None,
                fx=2.0,
                fy=2.0,
                interpolation=cv2.INTER_CUBIC,
            )

            text = pytesseract.image_to_string(upscaled, config=config)
            parts.append(text.strip())

        return "\n".join(parts)

    def _detect_columns(self, image: np.ndarray) -> list[tuple[int, int]]:
        """
        Find vertical column boundaries using a horizontal projection profile.

        Algorithm:
          1. Binarise (invert so text pixels = 1).
          2. Sum pixel values along each column (vertical projection).
          3. Find contiguous runs of near-zero columns — these are the gaps
             between text columns.
          4. Return (x_start, x_end) pairs for each text region.

        Returns an empty list if fewer than 2 columns are found (caller falls
        back to full-image OCR).
        """
        # Work on a binary image: text pixels are white (255)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Invert so text = high values
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Vertical projection: sum of ink pixels per column
        col_sum = np.sum(binary, axis=0).astype(np.float32)

        # Smooth to avoid single-pixel gaps splitting a column
        kernel = np.ones(10, dtype=np.float32) / 10
        col_sum_smooth = np.convolve(col_sum, kernel, mode="same")

        # A column is a "gap" if its smoothed ink density is below 1% of max
        threshold = col_sum_smooth.max() * 0.01
        is_gap = col_sum_smooth < threshold

        # Find transitions: gap→text (start) and text→gap (end)
        width = image.shape[1]
        columns: list[tuple[int, int]] = []
        in_text = False
        col_start = 0

        for x in range(width):
            if not in_text and not is_gap[x]:
                in_text = True
                col_start = x
            elif in_text and is_gap[x]:
                in_text = False
                # Add a small horizontal padding so we don't clip edge glyphs
                x_s = max(0, col_start - 4)
                x_e = min(width, x + 4)
                columns.append((x_s, x_e))

        if in_text:
            columns.append((max(0, col_start - 4), width))

        # Merge very narrow regions (< 30px) — likely noise, not real columns
        columns = [(s, e) for s, e in columns if (e - s) >= 30]

        return columns

    # ------------------------------------------------------------------ #
    # Answer key text parsing                                             #
    # ------------------------------------------------------------------ #

    def _parse_answer_key_text(
        self,
        text: str,
        max_question: int,
    ) -> List[ExtractedAnswer]:
        """
        Use _ANSWER_PATTERN to extract all (question_number, answer) pairs
        from the full OCR text in a single pass.

        The aggressive regex tolerates arbitrary garbage between the number
        and the letter (colons, spaces, dots, Tesseract noise characters).
        """
        results: List[ExtractedAnswer] = []
        seen: set[int] = set()

        for match in _ANSWER_PATTERN.finditer(text):
            q_num = int(match.group(1))
            answer = match.group(2).upper()

            if q_num < 1 or q_num > max_question:
                continue
            if answer not in VALID_ANSWERS:
                continue
            if q_num in seen:
                continue

            seen.add(q_num)
            # Confidence is fixed at 95 for clean-text OCR (see process_answer_key)
            results.append(ExtractedAnswer(
                question_number=q_num,
                answer=answer,
                confidence=95.0,
            ))

        return results

    # ================================================================== #
    # Part 2 – process_answer_sheet (OMR on bubble sheets)               #
    # ================================================================== #

    async def process_answer_sheet(
        self,
        image_file: bytes,
        participant_id: int,
        exam_id: int,
        question_repo,
        response_repo,
    ) -> AnswerSheetResult:
        """
        Process a participant answer sheet (ENEM-style bubble form) using a
        pure OpenCV OMR pipeline.  Tesseract is NOT used here.

        Pipeline:
          1. Decode bytes → numpy array
          2. Grayscale → Gaussian Blur → Otsu threshold (inverted)
          3. findContours to locate all blobs
          4. Filter by area and aspect ratio to isolate circular bubbles
          5. Sort bubbles top-to-bottom (rows) then left-to-right (columns)
          6. For each row (question), pick the bubble with the highest
             black-pixel density as the marked answer
          7. Map row index to question_map

        Args:
            image_file: Raw image bytes (JPEG, PNG, etc.).
            participant_id: ID of the participant whose sheet is being processed.
            exam_id: ID of the exam this answer sheet belongs to.
            question_repo: Repository with get_by_exam_id method.
            response_repo: Repository with create_or_update method.

        Returns:
            AnswerSheetResult with extraction summary.
        """
        try:
            nparr = np.frombuffer(image_file, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="Failed to decode image file.",
                )

            # Fetch questions to validate against
            existing_questions: list[Questao] = await question_repo.get_by_exam_id(exam_id)
            question_map: dict[int, Questao] = {q.numero: q for q in existing_questions}

            if not question_map:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message=f"No questions found for exam_id={exam_id}.",
                )

            extracted = self._run_omr_pipeline(image, question_map)

            if not extracted:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="OMR pipeline could not detect any marked bubbles.",
                )

            await self._save_answer_sheet(
                participant_id, exam_id, extracted, question_map, response_repo
            )

            avg_conf = sum(e.confidence for e in extracted) / len(extracted)
            flagged = sum(1 for e in extracted if e.confidence < 80.0)

            return AnswerSheetResult(
                participant_id=participant_id,
                exam_id=exam_id,
                extracted_answers=extracted,
                avg_confidence=round(avg_conf, 2),
                flagged_count=flagged,
                success=True,
            )

        except Exception as exc:
            logger.exception(
                "process_answer_sheet failed for participant_id=%s exam_id=%s",
                participant_id,
                exam_id,
            )
            return AnswerSheetResult(
                participant_id=participant_id,
                exam_id=exam_id,
                extracted_answers=[],
                avg_confidence=0.0,
                flagged_count=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------ #
    # OMR pipeline                                                        #
    # ------------------------------------------------------------------ #

    def _run_omr_pipeline(
        self,
        image: np.ndarray,
        question_map: dict,
    ) -> List[ExtractedAnswer]:
        """
        Full OMR pipeline for a bubble-sheet image.

        Returns a list of ExtractedAnswer objects, one per detected question row.
        """
        # Step 1 – Grayscale
        gray = self._to_grayscale(image)

        # Step 2 – Gaussian Blur to reduce noise before thresholding
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Step 3 – Otsu threshold (inverted so bubbles are white on black)
        _, thresh = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Step 4 – Find all external contours
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Step 5 – Filter to keep only bubble-shaped contours
        bubbles = self._filter_bubble_contours(contours)

        if not bubbles:
            logger.warning("OMR: no bubble contours found after filtering.")
            return []

        # Step 6 – Sort into rows (top-to-bottom) and columns (left-to-right)
        rows = self._cluster_bubbles_into_rows(bubbles)

        # Step 7 – For each row, pick the darkest bubble and map to a question
        return self._extract_answers_from_rows(rows, thresh, question_map)

    def _filter_bubble_contours(
        self,
        contours: tuple,
    ) -> List[Tuple[int, int, int, int]]:
        """
        Filter contours to keep only those that look like circular bubbles.

        Criteria:
          - Area between _MIN_BUBBLE_AREA and _MAX_BUBBLE_AREA
          - Bounding-box aspect ratio (w/h) close to 1.0 (circular)

        Returns a list of (x, y, w, h) bounding rectangles for valid bubbles.
        """
        valid: List[Tuple[int, int, int, int]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < _MIN_BUBBLE_AREA or area > _MAX_BUBBLE_AREA:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0:
                continue

            aspect_ratio = w / float(h)
            if abs(aspect_ratio - 1.0) > _ASPECT_RATIO_TOLERANCE:
                continue

            valid.append((x, y, w, h))

        return valid

    def _cluster_bubbles_into_rows(
        self,
        bubbles: List[Tuple[int, int, int, int]],
    ) -> List[List[Tuple[int, int, int, int]]]:
        """
        Group bubble bounding boxes into rows by their vertical (y) position.

        Bubbles whose top-y values are within (median_height * tolerance) of
        each other are considered to be on the same row.

        Returns a list of rows, each row sorted left-to-right by x.
        The outer list is sorted top-to-bottom by the row's minimum y.
        """
        if not bubbles:
            return []

        # Estimate a typical bubble height
        heights = [h for _, _, _, h in bubbles]
        median_h = float(np.median(heights))
        tolerance = median_h * _ROW_CLUSTER_TOLERANCE

        # Sort all bubbles top-to-bottom first
        sorted_bubbles = sorted(bubbles, key=lambda b: b[1])

        rows: List[List[Tuple[int, int, int, int]]] = []
        current_row: List[Tuple[int, int, int, int]] = [sorted_bubbles[0]]
        current_row_y = sorted_bubbles[0][1]

        for bubble in sorted_bubbles[1:]:
            _, y, _, _ = bubble
            if abs(y - current_row_y) <= tolerance:
                current_row.append(bubble)
            else:
                # Sort current row left-to-right before saving
                rows.append(sorted(current_row, key=lambda b: b[0]))
                current_row = [bubble]
                current_row_y = y

        # Don't forget the last row
        rows.append(sorted(current_row, key=lambda b: b[0]))

        return rows

    def _extract_answers_from_rows(
        self,
        rows: List[List[Tuple[int, int, int, int]]],
        thresh: np.ndarray,
        question_map: dict,
    ) -> List[ExtractedAnswer]:
        """
        For each row that has exactly _ANSWERS_PER_ROW bubbles, determine
        which bubble is filled by counting non-zero (white) pixels inside
        each bubble mask on the inverted threshold image.

        The bubble with the highest pixel count is the marked answer.
        Maps row index to question numbers from question_map (sorted).

        Confidence is computed as the ratio of the winning bubble's pixel
        count to the total pixels in the bubble area, scaled to 0-100.
        """
        # Build an ordered list of question numbers from the map
        sorted_question_numbers = sorted(question_map.keys())

        results: List[ExtractedAnswer] = []
        answer_letters = ["A", "B", "C", "D", "E"]

        question_idx = 0

        for row in rows:
            # Only process rows that have exactly 5 bubbles (A-E columns)
            if len(row) != _ANSWERS_PER_ROW:
                logger.debug(
                    "OMR: skipping row with %d bubbles (expected %d)",
                    len(row),
                    _ANSWERS_PER_ROW,
                )
                continue

            if question_idx >= len(sorted_question_numbers):
                break  # More rows than questions — stop

            q_num = sorted_question_numbers[question_idx]
            question_idx += 1

            # Count filled pixels in each bubble
            pixel_counts: List[int] = []
            for x, y, w, h in row:
                # Create a mask for this bubble's bounding box
                mask = np.zeros(thresh.shape, dtype=np.uint8)
                mask[y : y + h, x : x + w] = thresh[y : y + h, x : x + w]
                count = cv2.countNonZero(mask)
                pixel_counts.append(count)

            best_idx = int(np.argmax(pixel_counts))
            marked_answer = answer_letters[best_idx]

            # Confidence: winning count / total bubble area, clamped to 100
            x_b, y_b, w_b, h_b = row[best_idx]
            bubble_area = w_b * h_b
            raw_confidence = (pixel_counts[best_idx] / bubble_area) * 100.0 if bubble_area > 0 else 0.0
            confidence = min(round(raw_confidence, 2), 100.0)

            results.append(ExtractedAnswer(
                question_number=q_num,
                answer=marked_answer,
                confidence=confidence,
            ))

        return results

    # ================================================================== #
    # Shared persistence helpers                                          #
    # ================================================================== #

    async def _save_answer_key(
        self,
        exam_id: int,
        extracted: List[ExtractedAnswer],
        question_repo,
    ) -> None:
        """
        Update Question records with extracted correct answers.

        IMPORTANT — only updates question_correct_answer.  peso and all other
        fields are intentionally left untouched so that weights configured at
        exam-creation time are never overwritten by OCR.

        Questions that were pre-created by ExamManagerService.create_exam are
        updated in-place.  If a question number from OCR has no matching row
        (e.g. a phantom number produced by Tesseract noise) it is silently
        skipped — we never create new rows here.
        """
        existing: list[Questao] = await question_repo.get_by_exam_id(exam_id)
        existing_map: dict[int, Questao] = {q.numero: q for q in existing}

        for item in extracted:
            q = existing_map.get(item.question_number)
            if q is None:
                # OCR produced a question number that doesn't exist in this exam.
                # Log and skip — do NOT create a new row with peso=1.
                logger.warning(
                    "_save_answer_key: question %d not found in exam %d — skipping",
                    item.question_number,
                    exam_id,
                )
                continue

            # Only touch the answer field; preserve peso and everything else.
            q.question_correct_answer = item.answer
            await question_repo.update_answer_only(q.id, item.answer)

    async def _save_answer_sheet(
        self,
        participant_id: int,
        exam_id: int,
        extracted: List[ExtractedAnswer],
        question_map: dict,
        response_repo,
    ) -> None:
        """Create or update Response records with extracted marked answers."""
        for item in extracted:
            question = question_map.get(item.question_number)
            if question is None:
                continue

            response = Resposta(
                user_id=participant_id,
                quest_id=question.id,
                exam_id=exam_id,
                marked_answer=item.answer,
                confidence_score=item.confidence,
                manually_reviewed=False,
            )
            await response_repo.create_or_update(response)

    # ================================================================== #
    # Shared image utilities                                              #
    # ================================================================== #

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if it is not already."""
        if image is None:
            raise ValueError("Image cannot be None")

        if len(image.shape) == 2:
            return image.copy()

        if len(image.shape) == 3:
            channels = image.shape[2]
            if channels == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if channels == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

        raise ValueError(f"Unsupported image shape: {image.shape}")

    def _is_clean_image(self, gray: np.ndarray) -> bool:
        """
        Return True if the image is already high-contrast and clean.

        Heuristic: if more than 85% of pixels are near-white (>200) or
        near-black (<50), no further preprocessing is needed.
        """
        total = gray.size
        if total == 0:
            return False
        near_white = int(np.sum(gray > 200))
        near_black = int(np.sum(gray < 50))
        ratio = (near_white + near_black) / total
        return ratio > 0.85
