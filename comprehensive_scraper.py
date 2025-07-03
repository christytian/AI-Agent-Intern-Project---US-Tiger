# tradeup_comprehensive_scraper.py
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
import re

class TradeUPComprehensiveScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.scraped_articles = []
        self.base_url = "https://www.tradeup.com"
    
    def setup_driver(self):
        """Setup Chrome driver"""
        print("🔧 Setting up Chrome driver...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            print("   Running in headless mode")
        else:
            print("   Running with visible browser")
        
        # Performance optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # User agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Chrome driver ready")
            return True
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            return False
    
    def find_all_help_links(self, help_url):
        """Find all clickable help articles/questions"""
        print(f"🔍 Finding all help articles on: {help_url}")
        
        try:
            self.driver.get(help_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for dynamic content
            time.sleep(5)
            
            # Find all clickable help links
            help_links = []
            
            # Common selectors for help articles
            link_selectors = [
                'a[href*="help"]',
                'a[href*="faq"]',
                'a[href*="support"]',
                '.help-item a',
                '.faq-item a',
                '.question a',
                '.article-link',
                '.help-link'
            ]
            
            for selector in link_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        text = element.text.strip()
                        
                        if href and text and len(text) > 3:
                            # Make sure it's a help/support related link
                            if any(keyword in href.lower() for keyword in ['help', 'faq', 'support', 'guide']):
                                help_links.append({
                                    'url': href,
                                    'text': text,
                                    'selector': selector
                                })
                except Exception as e:
                    continue
            
            # Remove duplicates
            unique_links = []
            seen_urls = set()
            for link in help_links:
                if link['url'] not in seen_urls:
                    seen_urls.add(link['url'])
                    unique_links.append(link)
            
            print(f"✅ Found {len(unique_links)} unique help articles")
            return unique_links
            
        except Exception as e:
            print(f"❌ Error finding help links: {e}")
            return []
    
    def scrape_help_article(self, article_url, article_title):
        """Scrape content from a specific help article"""
        print(f"📄 Scraping article: {article_title}")
        
        try:
            self.driver.get(article_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for content to load
            time.sleep(3)
            
            # Scroll to make sure all content is loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Parse content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Extract main content
            content_selectors = [
                '.content',
                '.main-content',
                '.article-content',
                '.help-content',
                '.faq-content',
                'main',
                '.container',
                'body'
            ]
            
            main_content = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = content_elem.get_text(separator='\n', strip=True)
                    break
            
            if not main_content:
                main_content = soup.get_text(separator='\n', strip=True)
            
            # Clean content
            lines = main_content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if len(line) > 5:  # Filter out very short lines
                    cleaned_lines.append(line)
            
            cleaned_content = '\n'.join(cleaned_lines)
            
            article_data = {
                'url': article_url,
                'title': article_title,
                'content': cleaned_content,
                'content_length': len(cleaned_content),
                'scraped_at': datetime.now().isoformat()
            }
            
            print(f"   ✅ Scraped {len(cleaned_content)} characters")
            return article_data
            
        except Exception as e:
            print(f"   ❌ Error scraping article: {e}")
            return None
    
    def comprehensive_scrape(self, help_url, max_articles=20):
        """Scrape all help articles comprehensively"""
        print("🚀 Starting comprehensive TradeUP scraping...")
        print(f"📚 Target: {help_url}")
        
        if not self.setup_driver():
            return []
        
        try:
            # Find all help article links
            help_links = self.find_all_help_links(help_url)
            
            if not help_links:
                print("❌ No help articles found")
                return []
            
            print(f"📋 Found {len(help_links)} articles to scrape")
            print(f"🎯 Will scrape up to {max_articles} articles")
            
            # Scrape each article
            scraped_count = 0
            for i, link in enumerate(help_links[:max_articles]):
                print(f"\n📄 [{i+1}/{min(len(help_links), max_articles)}] {link['text']}")
                
                article_data = self.scrape_help_article(link['url'], link['text'])
                
                if article_data:
                    self.scraped_articles.append(article_data)
                    scraped_count += 1
                    
                    # Save individual article
                    filename = f"data/article_{i+1}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(article_data, f, indent=2, ensure_ascii=False)
                
                # Be nice to the server
                time.sleep(2)
            
            print(f"\n🎉 Successfully scraped {scraped_count} articles!")
            
            # Save combined data
            combined_data = {
                'scraped_at': datetime.now().isoformat(),
                'total_articles': len(self.scraped_articles),
                'help_url': help_url,
                'articles': self.scraped_articles
            }
            
            with open('data/tradeup_comprehensive.json', 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
            
            print("💾 Saved comprehensive data to data/tradeup_comprehensive.json")
            
            return self.scraped_articles
            
        except Exception as e:
            print(f"❌ Error in comprehensive scraping: {e}")
            return []
        finally:
            self.close()
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("🔐 Browser closed")

def test_comprehensive_scraping():
    """Test comprehensive scraping of TradeUP help center"""
    print("🚀 Testing Comprehensive TradeUP Scraping")
    print("=" * 60)
    
    # Initialize scraper
    scraper = TradeUPComprehensiveScraper(headless=True)
    
    # TradeUP help center URL
    help_url = "https://www.tradeup.com/help?lang=en-US"
    
    # Start comprehensive scraping
    articles = scraper.comprehensive_scrape(help_url, max_articles=10)
    
    if articles:
        print(f"\n📊 Scraping Summary:")
        print(f"   Total articles scraped: {len(articles)}")
        
        total_content = sum(len(article['content']) for article in articles)
        print(f"   Total content: {total_content:,} characters")
        
        print(f"\n📋 Articles scraped:")
        for i, article in enumerate(articles, 1):
            print(f"   {i}. {article['title'][:50]}... ({article['content_length']} chars)")
        
        print(f"\n✅ All content saved to individual files and combined file")
        return True
    else:
        print("❌ No articles were scraped")
        return False

if __name__ == "__main__":
    success = test_comprehensive_scraping()
    
    if success:
        print("\n🎉 Comprehensive scraping completed successfully!")
        print("✅ Ready to build RAG system with full content!")
    else:
        print("\n❌ Comprehensive scraping failed")