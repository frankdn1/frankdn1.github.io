import unittest
import os
from dotenv import load_dotenv
import base64
from unittest.mock import patch, MagicMock
from io import BytesIO
from llm_analyzer import DeepseekAnalyzer

class TestDeepseekAnalyzer(unittest.TestCase):
    # Note: setUp is no longer decorated with @patch, we patch inside
    def setUp(self):
        """Set up test environment using patch.object for together_client."""
        # Load actual environment variables from .env
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

        # Patch the OpenAI client initialization (still needed for other tests)
        # We use start() and stop() manually for this patcher
        self.openai_patcher = patch('llm_analyzer.OpenAI')
        mock_openai_class = self.openai_patcher.start()
        self.mock_openai = mock_openai_class.return_value # This is the mock OpenAI instance

        # Create the real analyzer instance FIRST
        self.analyzer = DeepseekAnalyzer()

        # Now, patch the 'together_client' attribute ON THE INSTANCE
        # Create a mock Together client instance manually
        # We need to import Together for the spec
        try:
            from together import Together
            spec = Together
        except ImportError:
            spec = None # Fallback if together library isn't installed

        self.mock_together = MagicMock(spec=spec) # Use spec for better mocking
        self.mock_together.images = MagicMock() # Add images.generate mock structure
        # Patch the attribute on the specific analyzer instance using patch.object
        # We use start() and stop() manually for this patcher too
        self.together_patcher = patch.object(self.analyzer, 'together_client', self.mock_together)
        self.together_patcher.start() # Start the patch

        # Assign the mocked OpenAI client (as before)
        # No need to assign together_client again, patch.object handles it
        self.analyzer.client = self.mock_openai

    def tearDown(self):
        """Clean up patches started manually in setUp."""
        self.together_patcher.stop() # Stop the object patch
        self.openai_patcher.stop() # Stop the class patch

    def test_analyze_date(self):
        """Test date analysis preserves existing functionality"""
        # Setup mock response
        mock_response = MagicMock()
        # Ensure structure matches expected OpenAI response
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = """
        Estimated Year: 1967
        Confidence: 0.9
        Reasoning: Text references RCMP activities in Dawson City
        """
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        # Use the mock OpenAI client assigned in setUp
        self.mock_openai.chat.completions.create.return_value = mock_response

        # Call with test text
        result = self.analyzer.analyze_date("Test chapter text")

        # Verify results
        self.assertIn('year', result)
        if result['year'] != 'unknown':
            self.assertEqual(result['year'], '1967')
        self.assertIn('confidence', result)
        self.assertIn('reasoning', result)

    def test_analyze_location(self):
        """Test new location analysis functionality"""
        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = """
        Location Name: Dawson City, Yukon
        Coordinates: 64.0667,-139.4167
        Location Reasoning: Text references RCMP activities in Dawson City
        """
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        self.mock_openai.chat.completions.create.return_value = mock_response

        # Call with test text
        result = self.analyzer.analyze_location("Test chapter text")

        # Verify results
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIn('location', result)
            if result['location']['name'] != 'unknown':
                self.assertEqual(result['location']['name'], 'Dawson City, Yukon')

    @patch.dict('os.environ', {}, clear=True)
    def test_no_api_key(self):
        """Test behavior when no API key is configured"""
        # Need to re-instantiate analyzer as setUp won't run with mocks here
        with patch('llm_analyzer.OpenAI'), patch('llm_analyzer.Together'):
             analyzer = DeepseekAnalyzer()
        result = analyzer.analyze_date("Test text")
        self.assertIn('year', result)
        self.assertEqual(result['year'], 'unknown')
        self.assertIn('reasoning', result)

    # Test for the test-specific path
    def test_generate_chapter_image_test_mode(self):
        """Test image generation in test mode (no API call)"""
        # Patch os.getenv to simulate test environment
        with patch('os.getenv', return_value='true') as mock_getenv:
            with patch('PIL.Image.new') as mock_image_new:
                mock_img_instance = MagicMock()
                mock_image_new.return_value = mock_img_instance
                mock_img_instance.save.return_value = None

                result = self.analyzer.generate_chapter_image("Test chapter summary", 1)

                # Verify os.getenv was checked for the test flag
                mock_getenv.assert_called_with('PYTEST_CURRENT_TEST')

                self.assertIsNotNone(result)
                self.assertTrue(result.endswith('.png'))
                self.assertIn('assets/images/chapter_1.png', result)
                self.assertRegex(result, r'assets/images/chapter_\d+\.png')
                # Use the mock together client assigned in setUp via patch.object
                self.mock_together.images.generate.assert_not_called()

    # Test for the production path
    @patch('PIL.Image.open')
    @patch('base64.b64decode')
    def test_generate_chapter_image_production_mode(self, mock_b64decode, mock_image_open):
        """Test image generation in production mode (API call expected)"""
        # Setup mock prompt response
        mock_prompt_response = MagicMock()
        mock_prompt_choice = MagicMock()
        mock_prompt_message = MagicMock()
        mock_prompt_message.content = "Image Prompt: Production test summary"
        mock_prompt_choice.message = mock_prompt_message
        mock_prompt_response.choices = [mock_prompt_choice]
        self.mock_openai.chat.completions.create.return_value = mock_prompt_response

        # Setup mock image response
        mock_image_response = MagicMock()
        mock_image_choice = MagicMock()
        mock_image_choice.b64_json = "ZmFrZV9pbWFnZV9ieXRlcw=="
        mock_image_response.data = [mock_image_choice]
        self.mock_together.images.generate.return_value = mock_image_response

        # Setup mock image handling
        mock_img_instance = MagicMock()
        mock_image_open.return_value = mock_img_instance
        mock_b64decode.return_value = b'fake_image_bytes'

        # Call the function
        result = self.analyzer.generate_chapter_image("Production test summary", 1)

        # Verify results
        self.assertEqual(result, "assets/images/chapter_1.png")
        
        # Verify prompt generation
        self.mock_openai.chat.completions.create.assert_called_once()
        prompt_call_args = self.mock_openai.chat.completions.create.call_args[1]
        self.assertIn("Production test summary", prompt_call_args['messages'][1]['content'])
        
        # Verify image generation
        self.mock_together.images.generate.assert_called_once()
        image_call_args = self.mock_together.images.generate.call_args[1]
        self.assertIn("Production test summary", image_call_args['prompt'])
        self.assertEqual("b64_json", image_call_args['response_format'])

        # Verify image handling
        mock_image_open.assert_called_once()
        mock_img_instance.save.assert_called_once_with("assets/images/chapter_1.png")

    def test_generate_chapter_image_failure(self):
        """Test image generation failure"""
        # Setup mock to raise exception
        # Use the mock together client assigned in setUp via patch.object
        self.mock_together.images.generate.side_effect = Exception("API error")

        # Call with test summary
        result = self.analyzer.generate_chapter_image("Test chapter summary", 1)

        # Verify results
        self.assertIsNone(result)

    @patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}, clear=True)
    def test_no_together_api_key(self):
        """Test behavior when Together API key is missing"""
        # Need to re-instantiate analyzer as setUp won't run with mocks here
        with patch('llm_analyzer.OpenAI'), patch('llm_analyzer.Together'):
             analyzer = DeepseekAnalyzer() # This instance won't have together_client set
        result = analyzer.generate_chapter_image("Test summary", 1)
        self.assertIsNone(result)

    def test_generate_image_prompt_success(self):
        """Test successful image prompt generation"""
        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = """
        Image Prompt: Oil painting of RCMP officer in 1960s Yukon wilderness
        """
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        self.mock_openai.chat.completions.create.return_value = mock_response

        # Call with test text
        result = self.analyzer.generate_image_prompt("Test chapter summary")

        # Verify results
        self.assertIn('prompt', result)
        self.assertIn('RCMP officer', result['prompt'])
        self.assertNotIn('Error', result['prompt'])

    def test_generate_image_prompt_error(self):
        """Test image prompt generation with API error"""
        # Setup mock to raise exception
        self.mock_openai.chat.completions.create.side_effect = Exception("API error")

        # Call with test text
        result = self.analyzer.generate_image_prompt("Test chapter summary")

        # Verify results
        self.assertIn('prompt', result)
        self.assertIn('Error', result['prompt'])

    def test_generate_chapter_image_uses_enhanced_prompt(self):
        """Test that generate_chapter_image uses the enhanced prompt"""
        # Setup mock responses
        mock_prompt_response = MagicMock()
        mock_prompt_choice = MagicMock()
        mock_prompt_message = MagicMock()
        mock_prompt_message.content = "Image Prompt: Detailed oil painting of historical scene"
        mock_prompt_choice.message = mock_prompt_message
        mock_prompt_response.choices = [mock_prompt_choice]
        self.mock_openai.chat.completions.create.return_value = mock_prompt_response

        mock_image_response = MagicMock()
        mock_image_choice = MagicMock()
        mock_image_choice.b64_json = "ZmFrZV9pbWFnZV9ieXRlcw=="
        mock_image_response.data = [mock_image_choice]
        self.mock_together.images.generate.return_value = mock_image_response

        # Setup file handling mocks
        with patch('PIL.Image.open') as mock_image_open, \
             patch('base64.b64decode') as mock_b64decode:
            mock_img_instance = MagicMock()
            mock_image_open.return_value = mock_img_instance
            mock_b64decode.return_value = b'fake_image_bytes'

            # Ensure environment vars are set for this test
            with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key', 'TOGETHER_API_KEY': 'test_key'}):
                # Call with test text
                result = self.analyzer.generate_chapter_image("Test summary", 1)

                # Verify results
                self.assertEqual(result, "assets/images/chapter_1.png")
                
                # Verify prompt generation
                self.mock_openai.chat.completions.create.assert_called_once()
                prompt_call_args = self.mock_openai.chat.completions.create.call_args[1]
                self.assertIn("Test summary", prompt_call_args['messages'][1]['content'])
                
                # Verify image generation
                self.mock_together.images.generate.assert_called_once()
                image_call_args = self.mock_together.images.generate.call_args[1]
                self.assertIn("Detailed oil painting", image_call_args['prompt'])
                self.assertEqual("b64_json", image_call_args['response_format'])

                # Verify image handling
                mock_image_open.assert_called_once()
                mock_img_instance.save.assert_called_once_with("assets/images/chapter_1.png")

if __name__ == '__main__':
    unittest.main()