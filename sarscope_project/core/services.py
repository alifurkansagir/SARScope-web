import requests
import os
import re
from bs4 import BeautifulSoup
from django.core.mail import send_mail
from django.conf import settings

def fetch_competitor_price(url):
    """
    Verilen URL'den fiyat bilgisi çeker.
    Not: Bu fonksiyonu takip etmek istediğiniz sitelerin (Trendyol, Hepsiburada vb.)
    HTML yapısına göre özelleştirmeniz gerekecektir.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            price = None
            in_stock = True

            # 1. Trendyol Özel Ayrıştırıcı
            if "trendyol.com" in url:
                # Fiyat alanı genellikle prc-dsc veya product-price-container içindedir
                price_container = soup.find("div", class_="product-price-container") or soup.find("span", class_="prc-dsc")
                if price_container:
                    price = _parse_price(price_container.get_text())
                
                # Stok kontrolü (Sepete ekle butonu yoksa veya tükendi yazıyorsa)
                if "Tükendi" in soup.get_text() or soup.find("button", class_="add-to-basket", disabled=True):
                    in_stock = False

            # 2. Hepsiburada Özel Ayrıştırıcı
            elif "hepsiburada.com" in url:
                price_element = soup.find("span", attrs={"data-bind": "markupText:'currentPriceBeforePoint'"})
                if price_element:
                    price = _parse_price(price_element.get_text())
                else:
                    # Alternatif fiyat alanı
                    price_element = soup.find("div", class_="price-value")
                    if price_element:
                        price = _parse_price(price_element.get_text())

            # 3. Genel Yöntem (Meta Taglar - Amazon vb. için)
            if price is None:
                # Google ve Facebook için kullanılan standart meta etiketleri
                meta_price = soup.find("meta", property="product:price:amount") or \
                             soup.find("meta", property="og:price:amount")
                if meta_price:
                    try:
                        price = float(meta_price["content"])
                    except ValueError:
                        pass

            if price:
                return {
                    'price': price,
                    'in_stock': in_stock
                }
    except Exception as e:
        print(f"Fiyat çekme hatası ({url}): {e}")
    
    return None

def _parse_price(text):
    """Fiyat metnini (1.299,90 TL) float değere (1299.90) çevirir."""
    if not text: return None
    # TL, boşluk ve binlik ayırıcı noktayı kaldır, virgülü noktaya çevir
    clean_text = text.replace("TL", "").replace(" ", "").replace(".", "").replace(",", ".")
    # Regex ile sayısal değeri bul
    match = re.search(r"(\d+(\.\d+)?)", clean_text)
    if match:
        return float(match.group(1))
    return None

def send_email_alert(subject, message, recipient_list):
    """E-posta bildirimi gönderir."""
    try:
        # Gerçek e-posta gönderimi
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
        print(f"📧 EMAIL BAŞARIYLA GÖNDERİLDİ: {recipient_list}")
        return True
    except Exception as e:
        print(f"Email hatası: {e}")
        return False