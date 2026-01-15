import time
import re
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class SarScopeScraper:
    def __init__(self):
        # Tarayıcı Ayarları
        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless") # Görmek için kapalı
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

    def clean_price(self, price_text):
        if not price_text: return None
        # Temizlik
        price_text = str(price_text).lower().replace('tl', '').replace('try', '').strip()
        price_text = price_text.replace('.', '').replace(',', '.') # TR Formatı: 1.234,56 -> 1234.56
        try:
            # Sayı avcısı (1234.56 formatını arar)
            clean_val = re.search(r"\d+(\.\d+)?", price_text)
            if clean_val: return float(clean_val.group())
        except: pass
        return None

    def fetch_price(self, url):
        # ... (Tekli ürün fiyatı çekme kısmı aynı kalsın) ...
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            driver.get(url)
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 400);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            price_text = None

            if "hepsiburada.com" in url:
                selectors = ['[data-test-id="price-current-price"]', '#offering-price', '.price-txt', 'span[itemprop="price"]', '.product-price']
                for sel in selectors:
                    el = soup.select_one(sel)
                    if el: price_text = el.get_text(); break
                    
            elif "trendyol.com" in url:
                selectors = ['.prc-dsc', '.product-price-container', '.price', '.ps-curr', 'span.prc-slg']
                for sel in selectors:
                    el = soup.select_one(sel)
                    if el: price_text = el.get_text(); break
                    
            elif "amazon" in url:
                selectors = ['.a-price .a-offscreen', '#priceblock_ourprice', '#priceblock_dealprice', '.a-color-price']
                for sel in selectors:
                    el = soup.select_one(sel)
                    if el: price_text = el.get_text(); break
                    
            else:
                el = soup.find(class_=re.compile('price|amount', re.IGNORECASE))
                if el: price_text = el.get_text()

            return self.clean_price(price_text)
        except Exception as e:
            print(f"❌ Hata: {e}")
            return None
        finally:
            if driver: driver.quit()

    def fetch_best_sellers(self, category_url):
        driver = None
        products = []
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            
            print(f"🌐 Siteye gidiliyor: {category_url}")
            driver.get(category_url)
            time.sleep(5)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # --- TRENDYOL ---
            if "trendyol.com" in category_url:
                cards = soup.select('.p-card-wrppr')
                if not cards: cards = soup.select('.product-card') # Yedek yapı
                
                print(f"🔎 Trendyol: {len(cards)} ürün kartı bulundu.")

                for card in cards[:25]:
                    try:
                        # İsim
                        product_name = "İsimsiz Ürün"
                        brand_el = card.select_one('.prdct-desc-cntnr-ttl')
                        model_el = card.select_one('.prdct-desc-cntnr-name')
                        if brand_el and model_el:
                            product_name = f"{brand_el.get_text().strip()} {model_el.get_text().strip()}"
                        else:
                            name_el = card.select_one('.prdct-desc-cntnr-name') or card.select_one('.product-name') or card.select_one('.prdct-desc-cntnr-ttl') or card.select_one('span.name')
                            if name_el: product_name = name_el.get_text().strip()

                        # Fiyat
                        price_el = card.select_one('.prc-box-dscntd') or card.select_one('.prc-box-sllng') or card.select_one('.product-price')
                        
                        # Link
                        link_el = card.select_one('a')
                        link = "https://www.trendyol.com" + link_el['href'] if link_el else ""

                        # Yorum Sayısı (Rating)
                        rating_el = card.select_one('.ratingCount') or card.select_one('.rating-count')
                        reviews = rating_el.get_text().strip('() ') if rating_el else "0"

                        if product_name and price_el:
                            products.append({'name': product_name, 'price': self.clean_price(price_el.get_text()), 'reviews': reviews, 'link': link})
                    except: continue

            # --- HEPSIBURADA (DETAYLI ANALİZ MODU) ---
            elif "hepsiburada.com" in category_url:
                # Geniş Kart Seçici
                cards = soup.select('li[id^="i"]') 
                if not cards: cards = soup.select('[data-test-id="product-card"]')
                
                print(f"🔎 Bulunan kart sayısı: {len(cards)}")

                for i, card in enumerate(cards[:30]):
                    try:
                        # 1. İSİM ARA
                        name_el = card.select_one('[data-test-id="product-card-name"]')
                        if not name_el: name_el = card.select_one('h3')
                        if not name_el: name_el = card.select_one('.product-title')
                        if not name_el: name_el = card.select_one('a[title]') # Linkin title'ına bak
                        
                        if name_el and 'title' in name_el.attrs:
                            product_name = name_el['title'].strip()
                        else:
                            product_name = name_el.get_text().strip() if name_el else "İsimsiz"
                        
                        # 2. FİYAT ARA (Gelişmiş)
                        price_val = None
                        
                        # Yöntem A: Belirli seçiciler
                        price_selectors = ['[data-test-id="price-current-price"]', '.price-value', '.product-price']
                        for sel in price_selectors:
                            p_el = card.select_one(sel)
                            if p_el:
                                price_val = self.clean_price(p_el.get_text())
                                if price_val: break
                        
                        # Yöntem B: Bulamazsan kartın içindeki tüm yazılarda "TL" ara (Kaba Kuvvet)
                        if not price_val:
                            all_text = card.get_text()
                            # 1.000,00 TL gibi desenleri yakala
                            match = re.search(r'(\d{1,3}(\.\d{3})*,\d{2})\s?TL', all_text)
                            if not match: # Belki binlik ayracı yoktur: 100,50 TL
                                match = re.search(r'(\d+,\d{2})\s?TL', all_text)
                            
                            if match:
                                raw_price = match.group(1)
                                price_val = self.clean_price(raw_price)

                        # 3. YORUM SAYISI
                        review_el = card.select_one('[data-test-id="review-count"]') or card.select_one('.evaluation-count')
                        reviews = review_el.get_text().strip() if review_el else "0"

                        # 4. LİNK
                        link_el = card.select_one('a')
                        link = "https://www.hepsiburada.com" + link_el['href'] if link_el else ""

                        # SONUÇ
                        if product_name and price_val:
                            # print(f"✅ Bulundu: {product_name[:20]}... -> {price_val} TL") # Terminali kirletmemesi için kapalı
                            products.append({'name': product_name, 'price': price_val, 'reviews': reviews, 'link': link})
                        else:
                            print(f"⚠️ Kart {i} eksik: İsim={bool(product_name)}, Fiyat={bool(price_val)}")
                            
                    except Exception as e:
                        print(f"Hata (Kart {i}): {e}")
                        continue

            # --- N11 ---
            elif "n11.com" in category_url:
                cards = soup.select('li.column')
                if not cards: cards = soup.select('.pro')

                for card in cards[:25]:
                    try:
                        # İsim
                        name_el = card.select_one('.productName') or card.select_one('h3.productName')
                        
                        # Fiyat
                        price_el = card.select_one('.newPrice ins') or card.select_one('.priceContainer span')
                        
                        # Link
                        link_el = card.select_one('a.plink')
                        link = link_el['href'] if link_el else ""

                        # Yorum Sayısı
                        rating_el = card.select_one('.ratingText')
                        reviews = rating_el.get_text().strip() if rating_el else "0"

                        if name_el and price_el:
                            products.append({'name': name_el.get_text().strip(), 'price': self.clean_price(price_el.get_text()), 'reviews': reviews, 'link': link})
                    except: continue
            
            # --- AMAZON ---
            elif "amazon" in category_url:
                # 1. Standart Arama/Kategori Yapısı
                cards = soup.select('div[data-component-type="s-search-result"]')
                
                # 2. Eğer bulamazsa genel sonuç öğelerine bak (ASIN içerenler)
                if not cards: 
                    cards = [c for c in soup.select('.s-result-item') if c.get('data-asin')]
                
                # 3. Çok Satanlar Sayfası (Best Sellers)
                if not cards:
                    cards = soup.select('.zg-item-immersion')
                
                print(f"🔎 Amazon: {len(cards)} ürün kartı bulundu.")

                for card in cards[:25]:
                    try:
                        # İsim
                        name_el = card.select_one('h2 span') or card.select_one('.a-text-normal') or card.select_one('.p13n-sc-truncate')
                        
                        # Fiyat
                        price_el = card.select_one('.a-price .a-offscreen')
                        if not price_el: price_el = card.select_one('.a-price')
                        if not price_el: price_el = card.select_one('.p13n-sc-price')
                        if not price_el: price_el = card.select_one('.a-color-price')

                        # Link
                        link_el = card.select_one('h2 a')
                        if not link_el: link_el = card.select_one('.a-link-normal')
                        
                        link = ""
                        if link_el and link_el.has_attr('href'):
                             href = link_el['href']
                             if href.startswith('http'): link = href
                             else: link = "https://www.amazon.com.tr" + href

                        # Yorum
                        rating_el = card.select_one('.a-icon-alt')
                        reviews = rating_el.get_text().strip() if rating_el else "0"

                        if name_el and price_el:
                            products.append({'name': name_el.get_text().strip(), 'price': self.clean_price(price_el.get_text()), 'reviews': reviews, 'link': link})
                    except: continue
            
            return products

        except Exception as e:
            print(f"❌ Ajan Hatası: {e}")
            return []
        finally:
            if driver: driver.quit()

    def search_products(self, query):
        """Trendyol, Hepsiburada ve Amazon'da ürün arar."""
        results = []
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            encoded_query = urllib.parse.quote_plus(query)
            
            # 1. Trendyol Araması
            try:
                url = f"https://www.trendyol.com/sr?q={encoded_query}"
                driver.get(url)
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.select('.p-card-wrppr') or soup.select('.product-card') or soup.select('div[class*="product-card"]') or soup.select('.prdct-cntnr-wrppr')
                cards = cards[:3] # İlk 3 sonuç
                for card in cards:
                    link_el = card.select_one('a')
                    if link_el:
                        href = link_el.get('href', '')
                        link = "https://www.trendyol.com" + href if not href.startswith('http') else href
                        
                        name_el = card.select_one('.prdct-desc-cntnr-name') or card.select_one('.product-name') or card.select_one('.prdct-desc-cntnr-ttl')
                        name = name_el.get_text().strip() if name_el else "Trendyol Ürünü"
                        price_el = card.select_one('.prc-box-dscntd') or card.select_one('.prc-box-sllng')
                        price = self.clean_price(price_el.get_text()) if price_el else 0
                        results.append({'source': 'Trendyol', 'name': name, 'price': price, 'link': link})
            except Exception as e: print(f"Trendyol search error: {e}")

            # 2. Hepsiburada Araması
            try:
                url = f"https://www.hepsiburada.com/ara?q={encoded_query}"
                driver.get(url)
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.select('li.productListContent-item') or soup.select('[data-test-id="product-card"]') or soup.select('div[class*="ProductCard"]') or soup.select('li[id^="i"]')
                cards = cards[:3]
                for card in cards:
                    link_el = card.select_one('a')
                    if link_el:
                        href = link_el.get('href', '')
                        link = "https://www.hepsiburada.com" + href if not href.startswith('http') else href
                        
                        name_el = card.select_one('h3') or card.select_one('[data-test-id="product-card-name"]')
                        name = name_el.get_text().strip() if name_el else "HB Ürünü"
                        price_el = card.select_one('[data-test-id="price-current-price"]') or card.select_one('.product-price')
                        price = self.clean_price(price_el.get_text()) if price_el else 0
                        results.append({'source': 'Hepsiburada', 'name': name, 'price': price, 'link': link})
            except Exception as e: print(f"HB search error: {e}")

            # 3. Amazon Araması
            try:
                url = f"https://www.amazon.com.tr/s?k={encoded_query}"
                driver.get(url)
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.select('div[data-component-type="s-search-result"]') or soup.select('.s-result-item[data-asin]')
                cards = [c for c in cards if c.select_one('h2 a')][:3]
                for card in cards:
                    link_el = card.select_one('h2 a')
                    if link_el:
                        href = link_el.get('href', '')
                        link = "https://www.amazon.com.tr" + href if not href.startswith('http') else href
                        name = link_el.get_text().strip()
                        price_el = card.select_one('.a-price .a-offscreen')
                        price = self.clean_price(price_el.get_text()) if price_el else 0
                        results.append({'source': 'Amazon', 'name': name, 'price': price, 'link': link})
            except Exception as e: print(f"Amazon search error: {e}")

            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []
        finally:
            if driver: driver.quit()