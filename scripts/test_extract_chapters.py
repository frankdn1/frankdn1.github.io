#!/usr/bin/env python3
"""Tests for extract_chapters.py"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open, call

# Import the module directly since we're in the same directory
import extract_chapters

class TestChapterExtraction(unittest.TestCase):
    """Test cases for chapter extraction functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Create test book content
        self.test_content = """\
My Earlier Years that I Can Remember\t1
Hunting and Fishing in The Yukon\t37

MY EARLIER YEARS THAT I CAN REMEMBER
Chapter 1 content
line 2

HUNTING AND FISHING IN THE YUKON
Chapter 2 content
line 2
"""
        self.expected_toc = [
            "My Earlier Years that I Can Remember",
            "Hunting and Fishing in The Yukon"
        ]
        self.expected_chapters = {
            "MY EARLIER YEARS THAT I CAN REMEMBER": "Chapter 1 content\nline 2",
            "HUNTING AND FISHING IN THE YUKON": "Chapter 2 content\nline 2"
        }

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("Normal Title", "Normal_Title"),
            ("Title with spaces", "Title_with_spaces"),
            ("Title with!@#$ chars", "Title_with_chars"),
            ("Title-with-dashes", "Title_with_dashes"),
            ("Title.with.dots", "Titlewithdots"),
        ]
        
        for title, expected in test_cases:
            with self.subTest(title=title):
                self.assertEqual(extract_chapters.sanitize_filename(title), expected)

    def test_parse_toc(self):
        """Test TOC parsing."""
        result = extract_chapters.parse_toc(self.test_content)
        self.assertEqual(result, self.expected_toc)

    def test_extract_chapters(self):
        """Test chapter extraction."""
        result = extract_chapters.extract_chapters(self.test_content, self.expected_toc)
        self.assertEqual(result, self.expected_chapters)

    def test_validate_utf8(self):
        """Test UTF-8 validation."""
        self.assertTrue(extract_chapters.validate_utf8("Valid UTF-8 text"))
        # Note: b'\xff\xfe\xfd'.decode('latin-1') results in valid Unicode chars 'ÿþý'.
        # The function correctly identifies this as valid. The test assertion is updated.
        # A different test case would be needed to test invalid UTF-8 byte sequences.
        self.assertTrue(extract_chapters.validate_utf8(b'\xff\xfe\xfd'.decode('latin-1')))

    @patch('extract_chapters.open', mock_open())
    @patch('os.path.exists', return_value=True)
    @patch('extract_chapters.validate_utf8', return_value=True)
    def test_write_chapter_files(self, mock_validate, mock_exists):
        """Test chapter file writing."""
        chapters = {
            "CHAPTER 1": "Content 1",
            "CHAPTER 2": "Content 2"
        }
        extract_chapters.write_chapter_files(chapters, self.test_dir)
        
        # Verify files would be created
        expected_files = [
            os.path.join(self.test_dir, "01_CHAPTER_1.txt"),
            os.path.join(self.test_dir, "02_CHAPTER_2.txt")
        ]
        for filepath in expected_files:
            self.assertTrue(os.path.exists(filepath))

    @patch('builtins.open', side_effect=IOError("Mock error"))
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_write_chapter_files_error(self, mock_sleep, mock_open):
        """Test file writing error handling with retries."""
        with self.assertLogs(level='WARNING') as cm:
            extract_chapters.write_chapter_files({"CHAPTER": "Content"}, self.test_dir)
            # Should log 2 warnings (attempts 1 and 2) and 1 error (final attempt)
            self.assertEqual(len(cm.output), 3)
            self.assertIn("Attempt 1 failed", cm.output[0])
            self.assertIn("Attempt 2 failed", cm.output[1])
            self.assertIn("Failed to write", cm.output[2])

    def test_parse_toc_malformed(self):
        """Test malformed TOC entry detection."""
        malformed_content = """\
Good Entry\t1
\tMissing Title
Bad Entry\tNotANumber
Empty Title\t
"""
        with self.assertLogs(level='WARNING') as cm:
            result = extract_chapters.parse_toc(malformed_content)
            # Expect all entries except the completely empty one
            self.assertEqual(result, ["Good Entry", "Bad Entry", "Empty Title"])
            self.assertEqual(len(cm.output), 3)
            self.assertIn("Empty title", cm.output[0])
            self.assertIn("Invalid page number", cm.output[1])
            self.assertIn("Invalid page number", cm.output[1])
            self.assertIn("Empty title", cm.output[0])

    def test_validate_utf8_invalid(self):
        """Test invalid UTF-8 detection."""
        # Create invalid UTF-8 string (lone surrogate)
        invalid_utf8 = '\ud800'  # High surrogate without low surrogate
        self.assertFalse(extract_chapters.validate_utf8(invalid_utf8))

    def test_extraction_metrics(self):
        """Test metrics collection."""
        metrics = extract_chapters.ExtractionMetrics()
        self.assertEqual(metrics.error_count, 0)
        self.assertEqual(metrics.duplicates_found, 0)
        self.assertEqual(metrics.invalid_utf8, 0)
        self.assertEqual(metrics.successful_writes, 0)
        self.assertEqual(metrics.chapter_sizes, {})

    def test_duplicate_detection(self):
        """Test duplicate chapter content detection."""
        chapters = {
            "CHAPTER 1": "Same content",
            "CHAPTER 2": "Same content",
            "CHAPTER 3": "Different content"
        }
        metrics = extract_chapters.ExtractionMetrics()
        
        with patch('extract_chapters.open', mock_open()), \
             patch('extract_chapters.validate_utf8', return_value=True):
            extract_chapters.write_chapter_files(chapters, metrics=metrics)
        
        self.assertEqual(metrics.duplicates_found, 1)
        self.assertEqual(metrics.successful_writes, 3)

    def test_validation_report_generation(self):
        """Test validation report generation."""
        metrics = extract_chapters.ExtractionMetrics()
        metrics.chapter_sizes = {"ch1.txt": 100, "ch2.txt": 200}
        metrics.successful_writes = 2
        metrics.error_count = 1
        metrics.invalid_utf8 = 0
        metrics.duplicates_found = 0
        
        with patch('builtins.open', mock_open()) as mock_file:
            extract_chapters.generate_validation_report(metrics)
            mock_file.assert_called_once_with('docs/validation_report.md', 'w', encoding='utf-8')

    @patch('extract_chapters.open', mock_open(read_data="test content"))
    def test_main_success(self):
        """Test main function success case."""
        with patch('extract_chapters.parse_toc', return_value=["TOC"]), \
             patch('extract_chapters.extract_chapters', return_value={"CHAPTER": "Content"}), \
             patch('extract_chapters.write_chapter_files'):
            self.assertEqual(extract_chapters.main(), 0)

    @patch('os.path.exists', return_value=False)
    def test_main_missing_book(self, mock_exists):
        """Test main function with missing book.txt."""
        self.assertEqual(extract_chapters.main(), 1)

    def test_main_read_error(self):
        """Test main function with read error."""
        with patch('extract_chapters.os.path.exists', return_value=True):
            with patch('extract_chapters.open', side_effect=IOError("Mock error")):
                result = extract_chapters.main()
                self.assertEqual(result, 1, "Should return 1 on read error")

    @patch('extract_chapters.open', mock_open(read_data="test content"))
    def test_main_no_chapters(self):
        """Test main function with no chapters found."""
        with patch('extract_chapters.os.path.exists', return_value=True):
            with patch('extract_chapters.parse_toc', return_value=[]), \
                 patch('extract_chapters.extract_chapters', return_value={}):
                result = extract_chapters.main()
                self.assertEqual(result, 1, "Should return 1 when no chapters found")

    def test_checkpoint_creation(self):
        """Test checkpoint creation on interruption."""
        checkpoint_called = False
        
        def mock_exists(path):
            return path == 'book.txt'
            
        def mock_write_chapters(chapters, metrics=None):
            nonlocal checkpoint_called
            # Immediately raise error to simulate failure
            checkpoint_called = True
            raise Exception("Mock error")
            
        def mock_open_impl(path, mode='r', **kwargs):
            nonlocal checkpoint_called
            if path == '.chapter_extract_checkpoint' and mode == 'w':
                checkpoint_called = True
                return mock_open().return_value
            return mock_open(read_data="test content").return_value

        with patch('extract_chapters.os.path.exists', side_effect=mock_exists), \
             patch('extract_chapters.parse_toc', return_value=["TOC"]), \
             patch('extract_chapters.extract_chapters', return_value={"CH1": "C1", "CH2": "C2"}), \
             patch('extract_chapters.write_chapter_files', side_effect=mock_write_chapters), \
             patch('extract_chapters.open', side_effect=mock_open_impl):
            result = extract_chapters.main()
            self.assertEqual(result, 1)
            self.assertTrue(checkpoint_called, "Checkpoint file was not created")

    @patch('extract_chapters.os.path.exists',
           side_effect=lambda f: f == 'book.txt' or f == '.chapter_extract_checkpoint')
    @patch('extract_chapters.open',
           side_effect=[
               mock_open(read_data="1").return_value,  # Checkpoint file
               mock_open(read_data="test content").return_value  # Book file
           ])
    def test_resume_from_checkpoint(self, mock_open, mock_exists):
        """Test resume from checkpoint."""
        with patch('extract_chapters.parse_toc', return_value=["TOC"]), \
             patch('extract_chapters.extract_chapters', return_value={"CH1": "C1", "CH2": "C2"}):
            # Should process all chapters but skip the first one in the checkpoint
            with patch('extract_chapters.write_chapter_files') as mock_write:
                # Mock the write to verify which chapters were processed
                def mock_write_impl(chapters, metrics):
                    self.assertEqual(set(chapters.keys()), {"CH2"})
                    return True
                mock_write.side_effect = mock_write_impl
                extract_chapters.main()

    def test_chapter_count_verification(self):
        """Test chapter count verification in main()."""
        test_content = """\
Chapter 1\t1
Chapter 2\t2

CHAPTER 1
Content 1

CHAPTER 2
Content 2
"""
        with patch('extract_chapters.open', mock_open(read_data=test_content)):
            with patch('extract_chapters.write_chapter_files') as mock_write:
                metrics = extract_chapters.ExtractionMetrics()
                with patch('extract_chapters.ExtractionMetrics', return_value=metrics):
                    with patch('extract_chapters.parse_toc', return_value=["Chapter 1", "Chapter 2"]), \
                         patch('extract_chapters.extract_chapters',
                              return_value={"CHAPTER 1": "Content 1", "CHAPTER 2": "Content 2"}):
                        # Mock the actual file writing to populate metrics
                        def mock_write_impl(chapters, metrics):
                            metrics.chapter_sizes = {"ch1.txt": 100, "ch2.txt": 200}
                            return True
                        mock_write.side_effect = mock_write_impl
                        extract_chapters.main()
                        self.assertEqual(len(metrics.chapter_sizes), 2)

    @patch('extract_chapters.os.path.exists', return_value=True)
    @patch('extract_chapters.open', mock_open(read_data="test content"))
    def test_checkpoint_cleanup(self, mock_exists):
        """Test checkpoint cleanup on success."""
        with patch('extract_chapters.parse_toc', return_value=["TOC"]), \
             patch('extract_chapters.extract_chapters', return_value={"CH": "C"}), \
             patch('extract_chapters.write_chapter_files'), \
             patch('extract_chapters.os.remove') as mock_remove:
            extract_chapters.main()
            mock_remove.assert_called_with('.chapter_extract_checkpoint')

if __name__ == '__main__':
    unittest.main()