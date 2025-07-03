# simple_scraper.py
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

class SimpleWebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_url(self, url):
        """Scrape a single URL"""
        print(f"🔍 Scraping: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            result = {
                'url': url,
                'title': soup.title.string if soup.title else '',
                'content': text,
                'scraped_at': datetime.now().isoformat(),
                'content_length': len(text)
            }
            
            print(f"✅ Successfully scraped {len(text)} characters")
            return result
            
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            return None
    
    def save_result(self, result, filename):
        """Save scraping result to file"""
        if result:
            with open(f"data/{filename}", 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved to data/{filename}")

def test_scraper():
    """Test the scraper with a simple website"""
    scraper = SimpleWebScraper()
    
    # Test with a simple, reliable website
    test_url = "https://www.tradeup.com/help?lang=en-US"
    
    result = scraper.scrape_url(test_url)
    
    if result:
        print(f"\n📊 Results:")
        print(f"   Title: {result['title']}")
        print(f"   Content length: {result['content_length']} characters")
        print(f"   First 200 chars: {result['content'][:200]}...")
        
        # Save the result
        scraper.save_result(result, "test_scrape.json")
        return True
    else:
        return False

if __name__ == "__main__":
    print("🚀 Testing Simple Web Scraper")
    print("=" * 40)
    
    success = test_scraper()
    
    if success:
        print("\n🎉 Web scraping is working!")
        print("✅ Ready to scrape real websites")
    else:
        print("\n❌ Something went wrong")