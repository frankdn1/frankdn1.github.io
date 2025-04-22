#!/usr/bin/env python3
"""Tests for analyze_chapter_dates.py"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Import the module directly since we're in the same directory
import analyze_chapter_dates
from llm_analyzer import DeepseekAnalyzer

class TestDateAnalysis(unittest.TestCase):
    """Test cases for chapter date analysis functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_extract_chapter_info(self):
        """Test filename parsing."""
        test_cases = [
            # Standard cases
            ("01_My_Earlier_Years_that_I_Can_Remember.txt", {
                'number': 1,
                'title': "My Earlier Years that I Can Remember",
                'year': "unknown"
            }),
            ("02_Hunting_and_Fishing_in_The_Yukon_1965.txt", {
                'number': 2,
                'title': "Hunting and Fishing in The Yukon 1965",
                'year': "1965"
            }),
            ("03_The_Story_Of_The_219_Zipper_Improved_Rifle_1972.txt", {
                'number': 3,
                'title': "The Story Of The 219 Zipper Improved Rifle 1972",
                'year': "1972"
            }),
            
            # Edge cases
            ("99_A_Very_Long_Title_With_Many_Underscores_And_Numbers_123_456_789_2023.txt", {
                'number': 99,
                'title': "A Very Long Title With Many Underscores And Numbers 123 456 789 2023",
                'year': "2023"
            }),
            ("10_Short_2025.txt", {
                'number': 10,
                'title': "Short 2025",
                'year': "2025"
            }),
            ("100_Just_Number.txt", {
                'number': 100,
                'title': "Just Number",
                'year': "unknown"
            })
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = analyze_chapter_dates.extract_chapter_info(filename)
                self.assertEqual(result, expected)

    def test_extract_chapter_info_invalid(self):
        """Test invalid filenames return None."""
        self.assertIsNone(analyze_chapter_dates.extract_chapter_info("invalid.txt"))

    @patch('llm_analyzer.OpenAI')
    def test_process_chapter(self, mock_openai):
        """Test chapter processing with mock LLM."""
        test_cases = [
            {
                'filename': "01_Test_Chapter.txt",
                'content': "Sample chapter content from 1965",
                'llm_response': """Estimated Year: 1965
Confidence: 0.8
Reasoning: The text describes events from the mid-1960s""",
                'expected': {
                    'number': 1,
                    'title': "Test Chapter",
                    'llm_year': "1965",
                    'confidence': 0.8,
                    'reasoning': "mid-1960s",
                    'validation_status': "Consistent"
                }
            },
            {
                'filename': "02_Chapter_With_Year_1970.txt",
                'content': "Content from around 1975",
                'llm_response': """Estimated Year: 1975
Confidence: 0.6
Reasoning: Text suggests mid-1970s""",
                'expected': {
                    'number': 2,
                    'title': "Chapter With Year 1970",
                    'llm_year': "1975",
                    'confidence': 0.6,
                    'reasoning': "mid-1970s",
                    'validation_status': "Conflict: filename=1970 vs LLM=1975"
                }
            },
            {
                'filename': "03_No_Year.txt",
                'content': "Ancient history content",
                'llm_response': """Estimated Year: 1950
Confidence: 0.3
Reasoning: Hard to determine exact year""",
                'expected': {
                    'number': 3,
                    'title': "No Year",
                    'llm_year': "1950",
                    'confidence': 0.3,
                    'reasoning': "Hard to determine",
                    'validation_status': "Low confidence"
                }
            }
        ]
        
        for case in test_cases:
            with self.subTest(filename=case['filename']):
                # Setup mock response
                mock_response = MagicMock()
                mock_response.choices[0].message.content = case['llm_response']
                
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                # Create test chapter file
                test_file = os.path.join(self.test_dir, case['filename'])
                with open(test_file, 'w') as f:
                    f.write(case['content'])

                # Test processing
                result = analyze_chapter_dates.process_chapter(test_file)
                self.assertEqual(result['number'], case['expected']['number'])
                self.assertEqual(result['title'], case['expected']['title'])
                self.assertEqual(result['llm_year'], case['expected']['llm_year'])
                self.assertEqual(result['confidence'], case['expected']['confidence'])
                self.assertIn(case['expected']['reasoning'], result['reasoning'])
                self.assertEqual(result['validation_status'], case['expected']['validation_status'])

    def test_validate_analysis(self):
        """Test validation logic."""
        test_cases = [
            # Consistent cases
            ({'year': '1965'}, {'year': '1965', 'confidence': 0.9}, "Consistent"),
            ({'year': 'unknown'}, {'year': '1970', 'confidence': 0.9}, "Consistent"),  # No filename year to conflict
            
            # Low confidence cases
            ({'year': '1965'}, {'year': '1970', 'confidence': 0.4}, "Low confidence"),
            ({'year': '1965'}, {'year': '1970', 'confidence': 0.49}, "Low confidence"),  # Edge case
            
            # Conflict cases
            ({'year': '1965'}, {'year': '1970', 'confidence': 0.5}, "Conflict: filename=1965 vs LLM=1970"),  # Edge case
            ({'year': '1965'}, {'year': '1970', 'confidence': 0.8}, "Conflict: filename=1965 vs LLM=1970"),
            
            # Error cases
            ({'year': '1965'}, {'year': None, 'confidence': 0.8}, "Analysis error: Invalid LLM year"),
            ({'year': '1965'}, {'year': '1970', 'confidence': None}, "Analysis error: Invalid confidence")
        ]
        
        for base_info, llm_data, expected in test_cases:
            with self.subTest(base_info=base_info, llm_data=llm_data):
                result = analyze_chapter_dates.validate_analysis(base_info, llm_data)
                self.assertEqual(result, expected)

    @patch('analyze_chapter_dates.process_chapter')
    def test_main(self, mock_process):
        """Test main execution."""
        # Setup test chapters
        os.makedirs(os.path.join(self.test_dir, "chapters"))
        test_chapters = [
            ("01_Chapter_One.txt", "1960"),
            ("02_Chapter_Two.txt", "1965"),
            ("03_Chapter_Three.txt", "1970"),
            ("99_Invalid_Chapter.txt", None)  # Should be skipped
        ]
        
        for filename, year in test_chapters:
            with open(os.path.join(self.test_dir, "chapters", filename), 'w') as f:
                f.write(f"Content for {filename}")

        # Mock process_chapter to return test data or raise error
        def mock_process_impl(filepath):
            filename = os.path.basename(filepath)
            if "Invalid" in filename:
                raise ValueError("Invalid chapter format")
            num = int(filename.split('_')[0])
            return {
                'number': num,
                'title': f"Chapter {'One' if num == 1 else 'Two' if num == 2 else 'Three'}",
                'year': f"196{num}" if num < 10 else "unknown",
                'llm_year': f"196{num + 1}" if num < 10 else "unknown",
                'confidence': 0.8 if num < 10 else 0.3,
                'reasoning': "Mock reasoning",
                'validation_status': "Consistent" if num == 1 else "Conflict" if num == 2 else "Low confidence"
            }
        mock_process.side_effect = mock_process_impl

        # Test main execution
        output_file = os.path.join(self.test_dir, "report.md")
        analyze_chapter_dates.main(chapters_dir=os.path.join(self.test_dir, "chapters"),
                                 output_file=output_file)

        # Verify report was created with expected content
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, 'r') as f:
            content = f.read()
            self.assertIn("Chapter Dates Analysis Report", content)
            for num in [1, 2, 3]:
                self.assertIn(f"Chapter {'One' if num == 1 else 'Two' if num == 2 else 'Three'}", content)
            self.assertNotIn("Invalid", content)  # Should be skipped

    def test_process_chapter_error_handling(self):
        """Test error handling in process_chapter."""
        # Test invalid filename format first
        result = analyze_chapter_dates.process_chapter("invalid.txt")
        self.assertIsNone(result.get('number'))
        self.assertEqual(result['validation_status'], "Invalid filename format")
            
        # Test file not found with valid filename format
        valid_but_missing = os.path.join(self.test_dir, "99_Valid_Chapter.txt")
        result = analyze_chapter_dates.process_chapter(valid_but_missing)
        self.assertEqual(result['validation_status'], f"Analysis error: File not found: {valid_but_missing}")

class TestDeepseekAnalyzer(unittest.TestCase):
    """Test cases for DeepseekAnalyzer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.analyzer = DeepseekAnalyzer()
        self.valid_response = """Estimated Year: 1965
Confidence: 0.8
Reasoning: The text describes events from 1965"""
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_chapter_success(self, mock_openai):
        """Test successful API call."""
        # Setup mock response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = self.valid_response
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Test with API key configured
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
            result = self.analyzer.analyze_chapter("Test content")
            
        self.assertEqual(result['year'], '1965')
        self.assertEqual(result['confidence'], 0.8)
        self.assertIn('1965', result['reasoning'])
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_chapter_error(self, mock_openai):
        """Test API error handling."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai.return_value = mock_client
        
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
            result = self.analyzer.analyze_chapter("Test content")
            
        self.assertEqual(result['year'], 'unknown')
        self.assertEqual(result['confidence'], 0)
        self.assertIn('API error', result['reasoning'])
    
    def test_analyze_chapter_no_api_key(self):
        """Test behavior when API key is not configured."""
        result = self.analyzer.analyze_chapter("Test content")
        self.assertEqual(result['year'], 'unknown')
        self.assertEqual(result['confidence'], 0)
        self.assertIn('DEEPSEEK_API_KEY not configured', result['reasoning'])
    
    def test_parse_response_valid(self):
        """Test parsing valid response."""
        result = self.analyzer._parse_response(self.valid_response)
        self.assertEqual(result['year'], '1965')
        self.assertEqual(result['confidence'], 0.8)
        self.assertIn('1965', result['reasoning'])
    
    def test_parse_response_invalid(self):
        """Test parsing invalid response formats."""
        test_cases = [
            ("Invalid response", {'year': 'unknown', 'confidence': 0, 'reasoning': ''}),
            ("Estimated Year: 1965", {'year': '1965', 'confidence': 0, 'reasoning': ''}),
            ("Confidence: 0.8", {'year': 'unknown', 'confidence': 0.8, 'reasoning': ''}),
            ("Reasoning: Test", {'year': 'unknown', 'confidence': 0, 'reasoning': 'Test'})
        ]
        
        for response, expected in test_cases:
            with self.subTest(response=response):
                result = self.analyzer._parse_response(response)
                self.assertEqual(result, expected)
    
    @patch('llm_analyzer.logger')
    @patch('llm_analyzer.OpenAI')
    def test_logging(self, mock_openai, mock_logger):
        """Test logging behavior."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = self.valid_response
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
            self.analyzer.analyze_chapter("Test content")
            
        # Verify logging calls
        mock_logger.info.assert_any_call("Starting Deepseek API call")
        mock_logger.debug.assert_any_call("Request content: Test content...")
        mock_logger.info.assert_any_call("Deepseek API call successful")
        mock_logger.debug.assert_any_call(f"Response: {self.valid_response}")

if __name__ == '__main__':
    unittest.main()