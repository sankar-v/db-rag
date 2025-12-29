"""
Setup configuration for db-rag package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="db-rag",
    version="0.1.0",
    author="Sankar V",
    description="A RAG system for structured and unstructured data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sankar-v/db-rag",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.1.0",
        "langchain-community>=0.0.10",
        "langchain-openai>=0.0.2",
        "chromadb>=0.4.22",
        "sqlalchemy>=2.0.25",
        "pymysql>=1.1.0",
        "psycopg2-binary>=2.9.9",
        "pypdf>=4.0.1",
        "python-docx>=1.1.0",
        "python-dotenv>=1.0.0",
        "openai>=1.7.2",
        "tiktoken>=0.5.2",
    ],
    entry_points={
        "console_scripts": [
            "db-rag=db_rag.cli:main",
        ],
    },
)
