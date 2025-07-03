# dynamic_scraper.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

class DynamicScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome driver"""
        print("🔧 Setting up Chrome driver...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            print("   Running in headless mode")
        
        # Performance optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            # Auto-install ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Chrome driver ready")
            return True
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            return False
    
    def scrape_url(self, url, wait_time=5):
        """Scrape URL with dynamic content loading"""
        if not self.driver:
            if not self.setup_driver():
                return None
        
        print(f"🔍 Dynamic scraping: {url}")
        
        try:
            # Load the page
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait additional time for dynamic content
            print(f"⏳ Waiting {wait_time} seconds for dynamic content...")
            time.sleep(wait_time)
            
            # Scroll to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get page source and parse
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean text
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if len(line) > 3:  # Filter out very short lines
                    cleaned_lines.append(line)
            
            cleaned_text = '\n'.join(cleaned_lines)
            
            result = {
                'url': url,
                'title': self.driver.title,
                'content': cleaned_text,
                'scraped_at': datetime.now().isoformat(),
                'content_length': len(cleaned_text),
                'method': 'dynamic'
            }
            
            print(f"✅ Successfully scraped {len(cleaned_text)} characters (dynamic)")
            return result
            
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            return None
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("🔐 Browser closed")

def test_dynamic_scraping():
    """Test dynamic scraping with TradeUP"""
    scraper = DynamicScraper(headless=True)
    
    # Test TradeUP URL
    test_url = "https://www.tradeup.com/help?lang=en-US"
    
    result = scraper.scrape_url(test_url, wait_time=10)
    
    if result:
        print(f"\n📊 Dynamic Scraping Results:")
        print(f"   Title: {result['title']}")
        print(f"   Content length: {result['content_length']} characters")
        print(f"   First 300 chars: {result['content'][:300]}...")
        
        # Save the result
        with open("data/dynamic_scrape.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("💾 Saved to data/dynamic_scrape.json")
        
        # Compare with static scraping
        print(f"\n📈 Comparison:")
        print(f"   Static scraping: 54 characters")
        print(f"   Dynamic scraping: {result['content_length']} characters")
        print(f"   Improvement: {result['content_length']/54:.1f}x more content!")
        
        scraper.close()
        return True
    else:
        scraper.close()
        return False

if __name__ == "__main__":
    print("🤖 Testing Dynamic Web Scraping")
    print("=" * 50)
    
    success = test_dynamic_scraping()
    
    if success:
        print("\n🎉 Dynamic scraping is working!")
        print("✅ Ready to scrape complex trading sites!")
    else:
        print("\n❌ Dynamic scraping needs troubleshooting")