"""
Unit tests for DB-RAG system.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_rag.config import Config
from db_rag.db_connector import DatabaseConnector
from db_rag.document_loader import DocumentLoader
from db_rag.vector_store import VectorStoreManager


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def test_config_creation(self):
        """Test creating a config object."""
        config = Config()
        self.assertIsNotNone(config)
        self.assertEqual(config.db_type, "sqlite")
        self.assertEqual(config.chunk_size, 1000)
    
    def test_sqlite_url_generation(self):
        """Test SQLite database URL generation."""
        config = Config()
        config.db_type = "sqlite"
        config.db_name = "test.db"
        url = config.get_db_url()
        self.assertEqual(url, "sqlite:///test.db")
    
    def test_mysql_url_generation(self):
        """Test MySQL database URL generation."""
        config = Config()
        config.db_type = "mysql"
        config.db_user = "user"
        config.db_password = "pass"
        config.db_host = "localhost"
        config.db_port = 3306
        config.db_name = "testdb"
        url = config.get_db_url()
        self.assertEqual(url, "mysql+pymysql://user:pass@localhost:3306/testdb")


class TestDatabaseConnector(unittest.TestCase):
    """Test database connector."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Create test database
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        cursor.executemany(
            "INSERT INTO test_table VALUES (?, ?, ?)",
            [(1, "Alice", 100), (2, "Bob", 200), (3, "Charlie", 300)]
        )
        conn.commit()
        conn.close()
        
        # Create config
        self.config = Config()
        self.config.db_type = "sqlite"
        self.config.db_name = self.db_path
    
    def tearDown(self):
        """Clean up test database."""
        shutil.rmtree(self.temp_dir)
    
    def test_connection(self):
        """Test database connection."""
        db = DatabaseConnector(self.config)
        self.assertIsNotNone(db.engine)
        db.close()
    
    def test_get_table_names(self):
        """Test getting table names."""
        db = DatabaseConnector(self.config)
        tables = db.get_table_names()
        self.assertIn("test_table", tables)
        db.close()
    
    def test_get_table_schema(self):
        """Test getting table schema."""
        db = DatabaseConnector(self.config)
        schema = db.get_table_schema("test_table")
        self.assertEqual(len(schema), 3)
        column_names = [col["name"] for col in schema]
        self.assertIn("id", column_names)
        self.assertIn("name", column_names)
        self.assertIn("value", column_names)
        db.close()
    
    def test_execute_query(self):
        """Test executing SQL queries."""
        db = DatabaseConnector(self.config)
        results = db.execute_query("SELECT * FROM test_table WHERE value > 150")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Bob")
        db.close()
    
    def test_get_sample_data(self):
        """Test getting sample data."""
        db = DatabaseConnector(self.config)
        samples = db.get_sample_data("test_table", limit=2)
        self.assertEqual(len(samples), 2)
        db.close()
    
    def test_get_database_schema_text(self):
        """Test getting schema as text."""
        db = DatabaseConnector(self.config)
        schema_text = db.get_database_schema_text()
        self.assertIn("test_table", schema_text)
        self.assertIn("id", schema_text)
        self.assertIn("name", schema_text)
        db.close()


class TestDocumentLoader(unittest.TestCase):
    """Test document loader."""
    
    def setUp(self):
        """Set up test documents."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
    
    def tearDown(self):
        """Clean up test documents."""
        shutil.rmtree(self.temp_dir)
    
    def test_load_text_file(self):
        """Test loading text files."""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("This is a test document.")
        
        loader = DocumentLoader(self.config)
        docs = loader.load_text_file(test_file)
        self.assertGreater(len(docs), 0)
        self.assertIn("test document", docs[0].page_content)
    
    def test_load_from_text(self):
        """Test loading from raw text."""
        loader = DocumentLoader(self.config)
        text = "This is a test document with some content."
        docs = loader.load_from_text(text, metadata={"source": "test"})
        self.assertGreater(len(docs), 0)
        self.assertIn("test document", docs[0].page_content)
        self.assertEqual(docs[0].metadata["source"], "test")
    
    def test_load_directory(self):
        """Test loading from directory."""
        # Create test files
        for i in range(3):
            test_file = os.path.join(self.temp_dir, f"test{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"This is test document {i}.")
        
        loader = DocumentLoader(self.config)
        docs = loader.load_directory(self.temp_dir)
        self.assertGreater(len(docs), 0)


class TestVectorStoreManager(unittest.TestCase):
    """Test vector store manager."""
    
    def setUp(self):
        """Set up test vector store."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config.vector_store_path = os.path.join(self.temp_dir, "chroma_test")
        
        # Skip tests if OpenAI API key is not set
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY not set")
    
    def tearDown(self):
        """Clean up test vector store."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test vector store initialization."""
        vector_store = VectorStoreManager(self.config)
        self.assertIsNotNone(vector_store)
    
    def test_add_texts(self):
        """Test adding texts to vector store."""
        vector_store = VectorStoreManager(self.config)
        texts = ["This is document 1.", "This is document 2."]
        vector_store.add_texts(texts)
        
        # Search for documents
        results = vector_store.similarity_search("document", k=2)
        self.assertEqual(len(results), 2)
    
    def test_similarity_search_with_score(self):
        """Test similarity search with scores."""
        vector_store = VectorStoreManager(self.config)
        texts = ["Python programming", "JavaScript development"]
        vector_store.add_texts(texts)
        
        results = vector_store.similarity_search_with_score("Python", k=2)
        self.assertEqual(len(results), 2)
        # First result should be about Python
        self.assertIn("Python", results[0][0].page_content)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseConnector))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentLoader))
    
    # Only add vector store tests if OpenAI API key is available
    if os.getenv("OPENAI_API_KEY"):
        suite.addTests(loader.loadTestsFromTestCase(TestVectorStoreManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
