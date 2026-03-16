"""
OCR Service for processing answer key and answer sheet images.

Implements image preprocessing pipeline:
  grayscale → orientation detection/correction → CLAHE → denoising → Otsu binarization
"""

import logging
import re
from typing import List, Optional

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.schemas.ocr import AnswerKeyResult, AnswerSheetResult, ExtractedAnswer

logger = logging.getLogger(__name__)

# Valid answer characters (A-E, case-insensitive matching)
VALID_ANSWERS = set("ABCDE")

# Patterns to match lines like: "1. A", "1) A", "1 - A", "Q1: A", "1 A"
_ANSWER_PATTERN = re.compile(
    r"[Qq]?(\d+)\s*[.)\-:]\s*([A-Ea-e])\b"
    r"|[Qq]?(\d+)\s+([A-Ea-e])\b"
)


class OCRService:
    """Service for OCR processing of answer keys and answer sheets."""

    # ------------------------------------------------------------------ #
    # Public async API                                                     #
    # ------------------------------------------------------------------ #

    async def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Run the full preprocessing pipeline on a raw image.

        Pipeline:
          1. Grayscale conversion
          2. Orientation detection and correction
          3. Adaptive histogram equalization (CLAHE)
          4. Denoising (fastNlMeansDenoising)
          5. Binarization (Otsu's method)

        Args:
            image: Input image as a NumPy array (BGR or grayscale).

        Returns:
            Preprocessed binary image as a NumPy array.
        """
        gray = self._to_grayscale(image)
        corrected = self._correct_orientation(gray)
        equalized = self._apply_clahe(corrected)
        denoised = self._denoise(equalized)
        binary = self._binarize(denoised)
        return binary

    async def process_answer_key(
        self,
        image_file: bytes,
        exam_id: int,
        exam_questions_numbers: int,
        question_repo,
    ) -> AnswerKeyResult:
        """
        Process an answer key image and persist extracted correct answers.

        Args:
            image_file: Raw image bytes (JPEG, PNG, etc.).
            exam_id: ID of the exam this answer key belongs to.
            exam_questions_numbers: Total number of questions in the exam.
            question_repo: Repository with get_by_exam_id, update, create_bulk methods.

        Returns:
            AnswerKeyResult with extraction summary.
        """
        try:
            # Decode bytes → numpy array
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

            # Preprocess
            preprocessed = await self.preprocess_image(image)

            # --- Extract text with per-word confidence via image_to_data ---
            data = pytesseract.image_to_data(
                preprocessed, output_type=Output.DICT
            )
            full_text = pytesseract.image_to_string(preprocessed)

            # Build a word→confidence map (last occurrence wins for duplicates)
            word_conf: dict[str, float] = {}
            for word, conf in zip(data["text"], data["conf"]):
                word = word.strip()
                if word and conf != -1:
                    word_conf[word.upper()] = float(conf)

            # Parse answer patterns from full OCR text
            extracted = self._parse_answer_key_text(
                full_text, exam_questions_numbers, word_conf
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

            # Persist to database
            await self._save_answer_key(exam_id, extracted, question_repo)

            avg_conf = sum(e.confidence for e in extracted) / len(extracted)
            flagged = sum(1 for e in extracted if e.confidence < 80.0)

            return AnswerKeyResult(
                exam_id=exam_id,
                extracted_answers=extracted,
                avg_confidence=round(avg_conf, 2),
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
    # Private helpers for answer key processing                           #
    # ------------------------------------------------------------------ #

    def _parse_answer_key_text(
        self,
        text: str,
        max_question: int,
        word_conf: dict,
    ) -> List[ExtractedAnswer]:
        """
        Parse OCR text and return validated ExtractedAnswer objects.

        Supports patterns: "1. A", "1) A", "1 - A", "Q1: A", "1 A"
        """
        results: List[ExtractedAnswer] = []
        seen: set[int] = set()

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            match = _ANSWER_PATTERN.search(line)
            if not match:
                continue

            # Groups 1,2 cover separator patterns; groups 3,4 cover space-only
            q_str = match.group(1) or match.group(3)
            a_str = match.group(2) or match.group(4)

            if not q_str or not a_str:
                continue

            q_num = int(q_str)
            answer = a_str.upper()

            # Validate question number range
            if q_num < 1 or q_num > max_question:
                logger.debug("Skipping out-of-range question %d", q_num)
                continue

            # Validate answer character
            if answer not in VALID_ANSWERS:
                logger.debug("Skipping invalid answer '%s' for Q%d", answer, q_num)
                continue

            # Skip duplicates (keep first occurrence)
            if q_num in seen:
                continue
            seen.add(q_num)

            # Confidence: look up the answer letter in word_conf, default 50
            confidence = word_conf.get(answer, 50.0)

            results.append(
                ExtractedAnswer(
                    question_number=q_num,
                    answer=answer,
                    confidence=confidence,
                )
            )

        return results

    async def _save_answer_key(
        self,
        exam_id: int,
        extracted: List[ExtractedAnswer],
        question_repo,
    ) -> None:
        """Create or update Question records with extracted correct answers."""
        existing: list[Questao] = await question_repo.get_by_exam_id(exam_id)
        existing_map: dict[int, Questao] = {q.numero: q for q in existing}

        to_create: list[Questao] = []

        for item in extracted:
            if item.question_number in existing_map:
                q = existing_map[item.question_number]
                q.question_correct_answer = item.answer
                await question_repo.update(q)
            else:
                to_create.append(
                    Questao(
                        exam_id=exam_id,
                        numero=item.question_number,
                        peso=1,
                        question_correct_answer=item.answer,
                    )
                )

        if to_create:
            await question_repo.create_bulk(to_create)

    async def process_answer_sheet(
        self,
        image_file: bytes,
        participant_id: int,
        exam_id: int,
        question_repo,
        response_repo,
    ) -> AnswerSheetResult:
        """
        Process a participant answer sheet image and persist extracted marked answers.

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
            # Decode bytes → numpy array
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

            # Preprocess
            preprocessed = await self.preprocess_image(image)

            # Extract text with per-word confidence via image_to_data
            data = pytesseract.image_to_data(preprocessed, output_type=Output.DICT)
            full_text = pytesseract.image_to_string(preprocessed)

            # Build a word→confidence map (last occurrence wins for duplicates)
            word_conf: dict[str, float] = {}
            for word, conf in zip(data["text"], data["conf"]):
                word = word.strip()
                if word and conf != -1:
                    word_conf[word.upper()] = float(conf)

            # Fetch existing questions to validate against
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

            # Parse answer patterns from full OCR text
            extracted = self._parse_answer_sheet_text(full_text, question_map, word_conf)

            if not extracted:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="No valid question-answer pairs found in image.",
                )

            # Persist to database
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
    # Private helpers for answer sheet processing                         #
    # ------------------------------------------------------------------ #

    def _parse_answer_sheet_text(
        self,
        text: str,
        question_map: dict,
        word_conf: dict,
    ) -> List[ExtractedAnswer]:
        """
        Parse OCR text and return validated ExtractedAnswer objects for an answer sheet.

        Only accepts question numbers that correspond to existing questions in the exam.
        Supports patterns: "1. A", "1) A", "1 - A", "Q1: A", "1 A"
        """
        results: List[ExtractedAnswer] = []
        seen: set[int] = set()

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            match = _ANSWER_PATTERN.search(line)
            if not match:
                continue

            q_str = match.group(1) or match.group(3)
            a_str = match.group(2) or match.group(4)

            if not q_str or not a_str:
                continue

            q_num = int(q_str)
            answer = a_str.upper()

            # Validate question number exists in the exam
            if q_num not in question_map:
                logger.debug("Skipping question %d not found in exam", q_num)
                continue

            # Validate answer character
            if answer not in VALID_ANSWERS:
                logger.debug("Skipping invalid answer '%s' for Q%d", answer, q_num)
                continue

            # Skip duplicates (keep first occurrence)
            if q_num in seen:
                continue
            seen.add(q_num)

            confidence = word_conf.get(answer, 50.0)

            results.append(
                ExtractedAnswer(
                    question_number=q_num,
                    answer=answer,
                    confidence=confidence,
                )
            )

        return results

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

    # ------------------------------------------------------------------ #
    # Step 1 – Grayscale conversion                                        #
    # ------------------------------------------------------------------ #

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if it is not already."""
        if image is None:
            raise ValueError("Image cannot be None")

        if len(image.shape) == 2:
            # Already grayscale
            return image.copy()

        if len(image.shape) == 3:
            channels = image.shape[2]
            if channels == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if channels == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

        raise ValueError(f"Unsupported image shape: {image.shape}")

    # ------------------------------------------------------------------ #
    # Step 2 – Orientation detection and correction                        #
    # ------------------------------------------------------------------ #

    def _correct_orientation(self, gray: np.ndarray) -> np.ndarray:
        """
        Detect image orientation and rotate to upright position.

        Uses Tesseract OSD when available; falls back to a heuristic
        based on text-line detection via Hough transform.
        """
        angle = self._detect_orientation_angle(gray)
        if abs(angle) < 0.5:
            return gray

        return self._rotate_image(gray, angle)

    def _detect_orientation_angle(self, gray: np.ndarray) -> float:
        """
        Return the skew angle (degrees) that should be applied to straighten the image.

        Tries Tesseract OSD first; falls back to a Hough-line heuristic.
        """
        try:
            return self._osd_angle(gray)
        except Exception as exc:
            logger.debug("Tesseract OSD unavailable (%s); using heuristic.", exc)
            return self._heuristic_skew_angle(gray)

    def _osd_angle(self, gray: np.ndarray) -> float:
        """Use Tesseract OSD to detect orientation angle."""
        import pytesseract  # imported lazily to avoid hard dependency at module load

        osd = pytesseract.image_to_osd(gray, output_type=pytesseract.Output.DICT)
        rotate = int(osd.get("rotate", 0))
        # Tesseract reports the angle needed to make the text upright.
        # We negate it because cv2.getRotationMatrix2D rotates counter-clockwise.
        return -float(rotate)

    def _heuristic_skew_angle(self, gray: np.ndarray) -> float:
        """
        Estimate skew angle using Hough line detection on edge-detected image.

        Returns the median angle of detected near-horizontal lines, clamped to ±15°.
        """
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            rho, theta = line[0]
            # Convert to degrees; near-horizontal lines have theta ≈ 0 or ≈ π
            angle_deg = np.degrees(theta) - 90.0
            if abs(angle_deg) <= 15.0:
                angles.append(angle_deg)

        if not angles:
            return 0.0

        return float(np.median(angles))

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by *angle* degrees around its centre, filling with white."""
        h, w = image.shape[:2]
        centre = (w / 2.0, h / 2.0)
        matrix = cv2.getRotationMatrix2D(centre, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255,
        )
        return rotated

    # ------------------------------------------------------------------ #
    # Step 3 – Adaptive histogram equalization (CLAHE)                    #
    # ------------------------------------------------------------------ #

    def _apply_clahe(
        self,
        gray: np.ndarray,
        clip_limit: float = 2.0,
        tile_grid_size: tuple = (8, 8),
    ) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to
        correct uneven lighting conditions.

        Args:
            gray: Grayscale image.
            clip_limit: Threshold for contrast limiting.
            tile_grid_size: Size of grid for histogram equalization.

        Returns:
            Contrast-enhanced grayscale image.
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(gray)

    # ------------------------------------------------------------------ #
    # Step 4 – Denoising                                                   #
    # ------------------------------------------------------------------ #

    def _denoise(
        self,
        gray: np.ndarray,
        h: int = 10,
        template_window_size: int = 7,
        search_window_size: int = 21,
    ) -> np.ndarray:
        """
        Remove noise using Non-Local Means Denoising.

        Args:
            gray: Grayscale image.
            h: Filter strength (higher = more denoising, less detail).
            template_window_size: Size of template patch (must be odd).
            search_window_size: Size of search window (must be odd).

        Returns:
            Denoised grayscale image.
        """
        return cv2.fastNlMeansDenoising(
            gray,
            None,
            h=h,
            templateWindowSize=template_window_size,
            searchWindowSize=search_window_size,
        )

    # ------------------------------------------------------------------ #
    # Step 5 – Binarization (Otsu's method)                               #
    # ------------------------------------------------------------------ #

    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """
        Convert grayscale image to binary using Otsu's thresholding.

        Otsu's method automatically determines the optimal threshold value
        by minimising intra-class intensity variance.

        Returns:
            Binary image (0 = black, 255 = white).
        """
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return binary
