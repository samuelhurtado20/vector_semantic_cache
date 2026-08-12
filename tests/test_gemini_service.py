"""
Integration tests for the Gemini SDK service (US-003).

Verifies acceptance criteria:
  - UC-3.1 (AC-1, AC-2): get_embedding() returns a 3072-dimensional list of floats (gemini-embedding-001).
  - UC-3.2 (AC-3): generate_response() returns a non-empty string from the Gemini model.
"""

import unittest

from services.gemini import generate_response, get_embedding


class TestGetEmbedding(unittest.TestCase):
    """UC-3.1: Generate Embeddings via SDK."""

    def test_returns_list_of_floats(self) -> None:
        """AC-1 / AC-2: SDK is initialised and returns a 3072-dimensional float list.

        Note: gemini-embedding-001 (the current available embedding model) produces
        3072-dimensional vectors. The original US-003 spec referenced text-embedding-004
        (768-dim) which is no longer available in the API.

        Returns:
        A list of 3072 floats representing the dense vector embedding.
        """
        result = get_embedding("What is FastAPI?")

        self.assertIsInstance(result, list, "Embedding must be a list.")
        self.assertEqual(len(result), 3072, "gemini-embedding-001 must return 3072 dimensions.")
        self.assertTrue(
            all(isinstance(v, float) for v in result),
            "Every element in the embedding must be a float.",
        )


class TestGenerateResponse(unittest.TestCase):
    """UC-3.2: Generate Text Response via SDK."""

    def test_returns_string_response(self) -> None:
        """AC-3: Service returns a non-empty string from Gemini."""
        result = generate_response("Translate hello to Spanish")

        self.assertIsInstance(result, str, "Response must be a string.")
        self.assertGreater(len(result), 0, "Response must not be empty.")
        self.assertIn(
            "hola",
            result.lower(),
            "Response should contain 'hola' when asked to translate 'hello' to Spanish.",
        )


if __name__ == "__main__":
    unittest.main()
