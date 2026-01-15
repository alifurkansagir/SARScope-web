from celery import shared_task
import time
from django.contrib.auth import get_user_model
from .models import Product
from .services import fetch_competitor_price, send_email_alert

@shared_task
def ornek_gorev():
    """
    Celery'nin düzgün çalışıp çalışmadığını test etmek için basit bir görev.
    """
    print("Örnek görev çalışıyor...")
    time.sleep(2)
    return "Görev tamamlandı!"

@shared_task
def scan_product_task(product_id):
    try:
        product = Product.objects.get(id=product_id)
        # Ürüne ait tüm rakipleri gez
        for competitor in product.competitors.all():
            result = fetch_competitor_price(competitor.url)
            if result:
                old_price = competitor.current_price
                new_price = result['price']
                
                # Fiyat değiştiyse güncelle
                if old_price != new_price:
                    competitor.current_price = new_price
                    competitor.in_stock = result['in_stock']
                    competitor.save()
                    
                    # KRİTİK: Rakip fiyatı bizim fiyatımızın altına düştüyse bildirim at!
                    if new_price < product.my_price:
                        msg = f"🚨 DİKKAT: {product.name} ürününde rakip fiyatı düştü!\nRakip: {new_price} TL\nSizin: {product.my_price} TL\nLink: {competitor.url}"
                        
                        # Email Gönder (Kullanıcının emaili varsa)
                        if product.user.email:
                            send_email_alert(f"Fiyat Alarmı: {product.name}", msg, [product.user.email])
    except Product.DoesNotExist:
        pass

@shared_task
def scan_all_products_task():
    """
    Sistemdeki tüm kullanıcıların ürünlerini tarar.
    Değişiklik olanlar için kullanıcılara toplu rapor maili atar.
    """
    User = get_user_model()
    print("🔄 Saatlik genel tarama başladı...")
    
    for user in User.objects.all():
        if not user.email:
            continue
            
        products = Product.objects.filter(user=user)
        changes = []
        
        for product in products:
            for competitor in product.competitors.all():
                result = fetch_competitor_price(competitor.url)
                if result:
                    new_price = result['price']
                    old_price = competitor.current_price
                    
                    if old_price != new_price:
                        competitor.current_price = new_price
                        competitor.in_stock = result['in_stock']
                        competitor.save()
                        
                        changes.append(f"📦 {product.name}\n   🔗 {competitor.marketplace_name or 'Rakip'}: {old_price} TL -> {new_price} TL")

        if changes:
            subject = "📢 SarScope Saatlik Fiyat Raporu"
            message = f"Merhaba {user.username},\n\nSon taramada {len(changes)} adet fiyat değişikliği tespit edildi:\n\n"
            message += "\n\n".join(changes)
            message += "\n\nDetaylar için panele giriş yapınız."
            
            send_email_alert(subject, message, [user.email])
            print(f"📧 Rapor gönderildi: {user.username}")