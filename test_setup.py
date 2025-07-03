# test_setup.py
import os
from pathlib import Path

def test_project_setup():
    print("🧪 Testing project setup...")
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check if directories exist
    directories = ['data', 'data/static', 'data/dynamic', 'data/raw', 'chroma_db']
    for dir_name in directories:
        if Path(dir_name).exists():
            print(f"✅ {dir_name} exists")
        else:
            print(f"❌ {dir_name} missing")
            Path(dir_name).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created {dir_name}")
    
    # Check if .env file exists
    if Path('.env').exists():
        print("✅ .env file exists")
    else:
        print("⚠️  .env file missing - create it with your OpenAI API key")
    
    # Test basic imports
    try:
        import requests
        import bs4
        import langchain
        print("✅ All basic packages imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test simple web request
    try:
        import requests
        response = requests.get("https://httpbin.org/json", timeout=5)
        if response.status_code == 200:
            print("✅ Internet connection and requests working")
        else:
            print(f"⚠️  Request failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False
    
    print("\n🎉 Project setup complete!")
    return True

if __name__ == "__main__":
    success = test_project_setup()
    if success:
        print("\n✅ Ready to create web scraping files!")
    else:
        print("\n❌ Please fix the issues above before continuing")