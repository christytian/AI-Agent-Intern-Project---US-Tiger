#!/usr/bin/env python3

# Test script to check which imports work in your environment

print("Testing LangChain imports...")

try:
    from langchain_community.document_loaders import TextLoader, JSONLoader, DirectoryLoader
    print("✓ langchain_community.document_loaders imports work")
except ImportError as e:
    print(f"✗ langchain_community.document_loaders import failed: {e}")

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("✓ langchain_text_splitters import works")
except ImportError as e:
    print(f"✗ langchain_text_splitters import failed: {e}")

try:
    from langchain_openai import OpenAIEmbeddings
    print("✓ langchain_openai import works")
except ImportError as e:
    print(f"✗ langchain_openai import failed: {e}")

try:
    from langchain_community.vectorstores import FAISS
    print("✓ langchain_community.vectorstores import works")
except ImportError as e:
    print(f"✗ langchain_community.vectorstores import failed: {e}")

try:
    from langchain_core.documents import Document
    print("✓ langchain_core.documents import works")
except ImportError as e:
    print(f"✗ langchain_core.documents import failed: {e}")

print("\nTesting alternative imports...")

try:
    from langchain.document_loaders import TextLoader, JSONLoader, DirectoryLoader
    print("✓ Old langchain.document_loaders imports still work")
except ImportError as e:
    print(f"✗ Old langchain.document_loaders import failed: {e}")

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    print("✓ Old langchain.text_splitter import works")
except ImportError as e:
    print(f"✗ Old langchain.text_splitter import failed: {e}")

print("\nImport test completed!")