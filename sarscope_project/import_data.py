import os
import django
import json
from decimal import Decimal
from urllib.parse import urlparse

# Django ortamını ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sarscope_project.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Product, Competitor

def import_data():
    # JSON dosyasının tam yolu
    json_path = '/Users/alifurkansagir/Desktop/sartech/sarscope/sarscope/data/products.json'
    
    if not os.path.exists(json_path):
        print(f'❌ Dosya bulunamadı: {json_path}')
        return

    # İlk kullanıcıyı al (Admin)
    user = User.objects.first()
    if not user:
        print('❌ Hiç kullanıcı bulunamadı. Lütfen önce "python manage.py createsuperuser" ile bir kullanıcı oluşturun.')
        return

    print(f"👤 Ürünler '{user.username}' kullanıcısına atanarak ekleniyor...")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for item in data:
        sku = item.get('sku')
        if not sku: continue

        # Eğer ürün zaten varsa tekrar ekleme
        if Product.objects.filter(sku=sku, user=user).exists():
            print(f"⚠️  Atlandı (Mevcut): {sku}")
            continue

        try:
            # Fiyatları Decimal formatına çevir
            my_price = Decimal(str(item.get('my_price', 0)))
            min_price = Decimal(str(item.get('min_price', 0)))
            
            # Maliyet verisi JSON'da yok, min_fiyat'ın %80'i olarak varsayalım
            cost_price = min_price * Decimal('0.8')

            # Ürünü oluştur
            product = Product.objects.create(
                user=user,
                name=item.get('name', 'İsimsiz Ürün')[:255], # İsim çok uzunsa kırp
                sku=sku,
                cost_price=cost_price,
                my_price=my_price,
                min_price_limit=min_price
            )
            
            # Rakip URL varsa Competitor tablosuna ekle
            comp_url = item.get('competitor_url')
            if comp_url and len(comp_url) > 10:
                # URL'den pazaryeri ismini çıkar (örn: hepsiburada.com -> Hepsiburada)
                try:
                    domain = urlparse(comp_url).netloc.replace('www.', '')
                    marketplace = domain.split('.')[0].capitalize()
                except:
                    marketplace = "Diğer"
                
                Competitor.objects.create(
                    product=product,
                    url=comp_url,
                    marketplace_name=marketplace
                )
            
            print(f"✅ Eklendi: {product.name[:40]}...")
            count += 1
            
        except Exception as e:
            print(f"❌ Hata ({sku}): {e}")

    print(f"\n🎉 İşlem tamamlandı! Toplam {count} yeni ürün veritabanına eklendi.")

if __name__ == "__main__":
    import_data()