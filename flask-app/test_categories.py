import base64
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import app as reporting

class CategoryDashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.directory.name, 'categories.db')
        self.db_patch = patch.object(reporting, 'SQLITE_DB_PATH', self.path)
        self.db_patch.start()
        user, password = next(iter(reporting.USER_DATA.items()))
        self.headers = {'Authorization': 'Basic ' + base64.b64encode((user + ':' + password).encode()).decode()}
        self.client = reporting.app.test_client()

    def tearDown(self):
        self.db_patch.stop()
        self.directory.cleanup()

    def check_pages(self):
        for path in ['/categories', '/category/Analysis']:
            self.assertEqual(self.client.get(path, headers=self.headers).status_code, 200)

    def test_missing_database_is_empty_without_creating_a_file(self):
        self.check_pages()
        self.assertFalse(os.path.exists(self.path))

    def test_database_without_category_table_is_empty(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute('CREATE TABLE unrelated (id INTEGER)')
        self.check_pages()

    def test_existing_categories_are_still_displayed(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute('CREATE TABLE message_categories (message_id TEXT, category TEXT, confidence REAL, message_text TEXT, processed_at TEXT)')
            conn.execute('INSERT INTO message_categories VALUES (?, ?, ?, ?, ?)', ('test-message', 'Analysis', .9, 'Synthetic regression message', '2026-10-09'))
        self.check_pages()
        self.assertIn(b'Synthetic regression message', self.client.get('/category/Analysis', headers=self.headers).data)

if __name__ == '__main__':
    unittest.main()
