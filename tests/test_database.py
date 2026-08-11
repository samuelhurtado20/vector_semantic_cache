import os
import tempfile
import unittest

from database import get_session_factory, init_db, save_interaction, get_all_interactions


class DatabaseSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            self.db_path = tmp_file.name
        self.database_url = f"sqlite:///{self.db_path}"
        self.engine = init_db(self.database_url)
        self.SessionLocal = get_session_factory(self.database_url)

    def tearDown(self) -> None:
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db_creates_table_and_persists_records(self) -> None:
        with self.assertRaises(Exception):
            with self.engine.connect() as connection:
                connection.execute("SELECT * FROM missing_table")

        session = self.SessionLocal()
        try:
            saved = save_interaction(session, "What is FastAPI?", "A web framework.", [0.1, 0.2, 0.3])
            session.commit()
            session.refresh(saved)

            self.assertIsNotNone(saved.id)
            with self.engine.connect() as connection:
                self.assertTrue(self.engine.dialect.has_table(connection, "interaction_cache"))

            records = get_all_interactions(session)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].question, "What is FastAPI?")
            self.assertEqual(records[0].response, "A web framework.")
            self.assertEqual(records[0].embedding, "[0.1, 0.2, 0.3]")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
