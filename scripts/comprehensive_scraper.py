# icon_click_scraper.py - Target the +/- icons specifically
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

class IconClickScraper:
    def __init__(self):
        self.driver = None
        os.makedirs('data', exist_ok=True)
        
    def setup_driver(self):
        """Setup Chrome driver"""
        print("🔧 Setting up Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Chrome driver ready")
            return True
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            return False
    
    def find_collapsed_faqs(self):
        """Find FAQs with + icons (collapsed) that need expanding"""
        collapsed_faqs = []
        
        try:
            # Find all FAQ containers
            faq_elements = self.driver.find_elements(By.CSS_SELECTOR, ".view___k3SX3")
            
            for faq_elem in faq_elements:
                try:
                    # Check the icon to see if it's collapsed (+) or expanded (-)
                    icon_elem = faq_elem.find_element(By.CSS_SELECTOR, ".icon___UkcJO")
                    icon_text = icon_elem.text.strip()
                    
                    # Get question text
                    question_elem = faq_elem.find_element(By.CSS_SELECTOR, ".text___hhr5e")
                    question = question_elem.text.strip()
                    
                    if icon_text == "+" and question:
                        # This FAQ is collapsed and needs expanding
                        collapsed_faqs.append({
                            'element': faq_elem,
                            'icon_element': icon_elem,
                            'question': question
                        })
                    elif icon_text == "-" and question:
                        # This FAQ is already expanded
                        print(f"   ✅ Found pre-expanded: {question[:50]}...")
                
                except Exception as e:
                    continue
            
            return collapsed_faqs
            
        except Exception as e:
            print(f"❌ Error finding collapsed FAQs: {e}")
            return []
    
    def expand_faq_by_icon(self, faq_info):
        """Expand FAQ by clicking the + icon specifically"""
        try:
            question = faq_info['question']
            icon_elem = faq_info['icon_element']
            faq_elem = faq_info['element']
            
            print(f"      🔄 Clicking + icon...")
            
            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", faq_elem)
            time.sleep(1)
            
            # Try clicking the icon directly
            try:
                icon_elem.click()
                time.sleep(3)
            except:
                # Fallback: JavaScript click on icon
                self.driver.execute_script("arguments[0].click();", icon_elem)
                time.sleep(3)
            
            # Verify expansion by checking if icon changed from + to -
            try:
                updated_icon = faq_elem.find_element(By.CSS_SELECTOR, ".icon___UkcJO")
                new_icon_text = updated_icon.text.strip()
                
                if new_icon_text == "-":
                    print(f"      ✅ SUCCESS! Icon changed from + to -")
                    return True
                else:
                    print(f"      ❌ Failed: Icon still shows '{new_icon_text}'")
                    return False
            except:
                print(f"      ❌ Failed: Could not verify icon change")
                return False
                
        except Exception as e:
            print(f"      ❌ Error expanding FAQ: {e}")
            return False
    
    def extract_expanded_content(self):
        """Extract content from all expanded FAQs (those with - icons)"""
        expanded_faqs = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all FAQ containers
            all_faqs = soup.find_all('div', class_='view___k3SX3')
            
            for faq in all_faqs:
                try:
                    # Check if this FAQ is expanded (has - icon)
                    icon_elem = faq.find('div', class_='icon___UkcJO')
                    if icon_elem and icon_elem.get_text(strip=True) == "-":
                        
                        # Get question
                        question_elem = faq.find('span', class_='text___hhr5e')
                        if question_elem:
                            question = question_elem.get_text(strip=True)
                            
                            # Get answer content
                            content_elem = faq.find('div', class_='content___Nqer7')
                            if content_elem:
                                # Remove feedback elements
                                for feedback in content_elem.find_all(class_='feedback___EtsDU'):
                                    feedback.decompose()
                                
                                answer = content_elem.get_text(separator='\n', strip=True)
                                answer = self.clean_answer(answer)
                                
                                if answer and len(answer) > 30:
                                    expanded_faqs.append({
                                        'question': question,
                                        'answer': answer
                                    })
                
                except Exception as e:
                    continue
            
            return expanded_faqs
            
        except Exception as e:
            print(f"❌ Error extracting content: {e}")
            return []
    
    def clean_answer(self, text):
        """Clean answer text"""
        if not text:
            return ""
        
        # Remove footer text
        if "Still got questions?" in text:
            text = text.split("Still got questions?")[0].strip()
        
        # Remove other common UI elements
        ui_phrases = [
            "Contact TradeUP Customer Support",
            "support@tradeup.com",
            "Live Chat",
            "Was this answer helpful?",
            "Yes", "No"
        ]
        
        for phrase in ui_phrases:
            text = text.replace(phrase, "")
        
        # Clean up whitespace
        lines = text.split('\n')
        clean_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 5]
        
        return '\n'.join(clean_lines).strip()
    
    def scrape_category_by_icon_clicking(self, parent_id):
        """Scrape category by specifically targeting +/- icons"""
        category_names = {
            22: "New Accounts", 23: "Funding/Withdrawal", 24: "Stock Trading - General",
            25: "Stock Trading - Order Types", 206: "Stock Trading - Fractional Shares",
            26: "Stock Trading - Extended Hours", 27: "Stock Trading - Cash Account",
            28: "Stock Trading - Margin Account", 29: "Stock Trading - Day Trading",
            211: "Stock Trading - OTC", 30: "Option Trading", 31: "Other",
            32: "TradeUP Authenticator", 252: "Fully Paid Securities Lending Program",
            317: "Taxes and Account Statements", 326: "Individual Retirement Account (IRA)"
        }
        
        category_name = category_names.get(parent_id, f"Category {parent_id}")
        url = f"https://www.tradeup.com/help/detail?parentId={parent_id}&lang=en_US"
        
        print(f"\n🎯 ICON-TARGETED SCRAPING")
        print(f"📂 Category: {category_name} (ID: {parent_id})")
        print(f"🎯 Strategy: Target + icons to expand FAQs")
        print(f"🔗 URL: {url}")
        
        if not self.setup_driver():
            return False
        
        try:
            # Navigate to page
            print("🔄 Loading page...")
            self.driver.get(url)
            time.sleep(5)
            
            # Find collapsed FAQs (those with + icons)
            print("🔍 Finding collapsed FAQs (+icons)...")
            collapsed_faqs = self.find_collapsed_faqs()
            
            print(f"📊 Found {len(collapsed_faqs)} collapsed FAQs to expand")
            
            # Try to expand each collapsed FAQ
            expansion_count = 0
            for i, faq_info in enumerate(collapsed_faqs, 1):
                question = faq_info['question']
                print(f"\n   📝 [{i}/{len(collapsed_faqs)}] {question[:50]}...")
                
                if self.expand_faq_by_icon(faq_info):
                    expansion_count += 1
                
                # Small delay between expansions
                time.sleep(1)
            
            print(f"\n📊 EXPANSION RESULTS:")
            print(f"   🎯 Attempted: {len(collapsed_faqs)}")
            print(f"   ✅ Successful: {expansion_count}")
            print(f"   📈 Success rate: {(expansion_count/max(len(collapsed_faqs),1)*100):.1f}%")
            
            # Extract content from all expanded FAQs
            print(f"\n📤 Extracting content from all expanded FAQs...")
            expanded_faqs = self.extract_expanded_content()
            
            if expanded_faqs:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"data/icon_click_{parent_id}_{timestamp}.json"
                
                data = {
                    'category_id': parent_id,
                    'category_name': category_name,
                    'extraction_method': 'icon_click_targeting',
                    'collapsed_faqs_found': len(collapsed_faqs),
                    'successful_expansions': expansion_count,
                    'total_extracted': len(expanded_faqs),
                    'scraped_at': datetime.now().isoformat(),
                    'qa_pairs': []
                }
                
                for i, faq in enumerate(expanded_faqs, 1):
                    qa_pair = {
                        'id': i,
                        'question': faq['question'],
                        'answer': faq['answer'],
                        'answer_length': len(faq['answer'])
                    }
                    data['qa_pairs'].append(qa_pair)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"\n🎉 SUCCESS! Extracted {len(expanded_faqs)} Q&A pairs")
                print(f"💾 SAVED TO: {filename}")
                
                print(f"\n📋 Q&A Preview:")
                for i, faq in enumerate(expanded_faqs, 1):
                    print(f"   ✅ Q{i}: {faq['question']}")
                    print(f"      A: {faq['answer'][:100]}...")
                    print(f"      📏 Length: {len(faq['answer'])} characters")
                
                expected_total = len(collapsed_faqs) + 1  # +1 for pre-expanded
                if len(expanded_faqs) >= expected_total * 0.8:
                    print(f"\n🎯 STATUS: ✅ EXCELLENT ({len(expanded_faqs)}/{expected_total} extracted)")
                elif len(expanded_faqs) >= expected_total * 0.5:
                    print(f"\n🎯 STATUS: ⚠️  GOOD ({len(expanded_faqs)}/{expected_total} extracted)")
                else:
                    print(f"\n🎯 STATUS: ❌ NEEDS IMPROVEMENT ({len(expanded_faqs)}/{expected_total} extracted)")
                
                return True
            else:
                print("❌ No Q&A pairs extracted")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            self.close()
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            print("🔐 Browser closed")

def main():
    scraper = IconClickScraper()
    
    print("🎯 ICON-TARGETED TradeUP FAQ Scraper")
    print("🔍 Based on HTML analysis: + icons = collapsed, - icons = expanded")
    print("=" * 60)
    
    try:
        category_id = int(input(f"Enter category ID to scrape [22]: ") or "22")
        success = scraper.scrape_category_by_icon_clicking(category_id)
        
        if success:
            print(f"\n✨ ICON-TARGETING WORKED! Try more categories.")
        else:
            print(f"\n⚠️  If still getting 1 Q&A, the + icon clicks may be blocked by the website")
        
    except ValueError:
        print("❌ Please enter a valid number")
    except KeyboardInterrupt:
        print("\n👋 Scraping cancelled")

if __name__ == "__main__":
    main()