from django.shortcuts import render, redirect, get_object_or_404
import sys
import os
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from .models import Product, Competitor
from .services import fetch_competitor_price, send_email_alert
from .forms import ProductForm, CompetitorForm
from .tasks import scan_product_task

@login_required
def home(request):
    """Ana Sayfa / Landing Page"""
    return render(request, 'core/home.html')

@login_required
def trend_hunter(request):
    """Trend Avcısı Sayfası"""
    results = []
    error = None
    url = ""
    
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            try:
                # SarScope kütüphanesini import etmeye çalış
                # Proje yapısına göre path ayarı gerekebilir
                try:
                    from sarscope.core.trend_hunter import TrendHunter
                except ImportError:
                    # Eğer path'de yoksa, repo kök dizinini ekle
                    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    if repo_root not in sys.path:
                        sys.path.append(repo_root)
                    from sarscope.core.trend_hunter import TrendHunter

                hunter = TrendHunter()
                scraped_data = hunter.scan_category(url)
                
                # Sonuçları işle (Envanter kontrolü basitçe)
                my_products = Product.objects.filter(user=request.user).values_list('name', flat=True)
                my_products_lower = [p.lower() for p in my_products]

                for item in scraped_data:
                    item['in_inventory'] = any(item['name'].lower() in p for p in my_products_lower)
                    results.append(item)
                
            except Exception as e:
                error = f"Hata oluştu: {str(e)}"
    
    return render(request, 'core/trend_hunter.html', {'results': results, 'error': error, 'url': url})

@login_required
def run_price_patrol(request):
    """Tüm ürünler için fiyat taramasını tetikler"""
    products = Product.objects.filter(user=request.user)
    count = 0
    for product in products:
        if product.competitors.exists():
            scan_product_task.delay(product.id)
            count += 1
    
    messages.success(request, f"🚀 {count} ürün için Fiyat Devriyesi başlatıldı! Sonuçlar birazdan panele yansır.")
    return redirect('dashboard')

@login_required
def send_report(request, report_type):
    """Panel ve Analiz sayfaları için mail gönderimi"""
    user_email = request.user.email
    if not user_email:
        messages.error(request, "Rapor almak için profilinizde kayıtlı bir e-posta adresi olmalıdır.")
        return redirect('dashboard')

    if report_type == 'dashboard':
        products = Product.objects.filter(user=request.user).prefetch_related('competitors')
        lines = ["SARSCOPE TAKİP PANELİ RAPORU", "="*30, ""]
        for p in products:
            line = f"Ürün: {p.name} | Fiyat: {p.my_price} TL"
            comps = p.competitors.all()
            if comps:
                min_comp = min([c.current_price for c in comps if c.current_price] or [0])
                if min_comp > 0:
                    line += f" | En Düşük Rakip: {min_comp} TL"
                    if p.my_price > min_comp:
                        line += " [⚠️ RAKİP DAHA UCUZ]"
            lines.append(line)
        
        if send_email_alert("Takip Paneli Raporu", "\n".join(lines), [user_email]):
            messages.success(request, f"Panel raporu {user_email} adresine gönderildi.")
        else:
            messages.error(request, "E-posta gönderilemedi! Lütfen settings.py dosyasındaki SMTP ayarlarını kontrol edin.")
            
        return redirect('dashboard')

    elif report_type == 'analysis':
        products = Product.objects.filter(user=request.user).prefetch_related('competitors')
        total_products = products.count()
        cheaper_count = 0
        for p in products:
            comps = p.competitors.all()
            valid_prices = [c.current_price for c in comps if c.current_price]
            if valid_prices and p.my_price < min(valid_prices):
                cheaper_count += 1
        
        advantage = int((cheaper_count / total_products * 100)) if total_products > 0 else 0
        body = f"SARSCOPE ANALİZ RAPORU\n{'='*25}\nToplam Ürün: {total_products}\nRekabet Avantajı: %{advantage}\n\nDetaylar için paneli ziyaret edin."
        
        if send_email_alert("Analiz Raporu", body, [user_email]):
            messages.success(request, f"Analiz raporu {user_email} adresine gönderildi.")
        else:
            messages.error(request, "E-posta gönderilemedi! Lütfen settings.py dosyasındaki SMTP ayarlarını kontrol edin.")
            
        return redirect('analysis')
    
    return redirect('dashboard')

@login_required
def send_trend_report(request):
    """Trend Avcısı sonuçlarını mail atar"""
    if request.method == 'POST':
        url = request.POST.get('url')
        user_email = request.user.email
        
        if url and user_email:
            # Not: Burada tekrar tarama yapmak yerine session kullanılabilir ama
            # basitlik adına kullanıcıya bilgi verip yönlendiriyoruz.
            # Gerçek senaryoda sonuçları session'dan alıp atmak daha hızlıdır.
            messages.info(request, f"Trend raporu isteğiniz {user_email} adresine alındı. (Not: Sonuçları tekrar taratmanız gerekebilir)")
            # Basit entegrasyon için şimdilik sadece bilgi veriyoruz, 
            # gelişmiş versiyonda 'trend_hunter' view'ı içinde mail atma opsiyonu olmalı.
            return redirect('trend_hunter')
            
    return redirect('trend_hunter')

@login_required
def dashboard(request):
    products = Product.objects.filter(user=request.user).prefetch_related('competitors')
    
    # 1. Markaları Çıkar (Ürün adının ilk kelimesi)
    all_brands = set()
    for p in products:
        if p.name:
            # İlk kelimeyi al, büyük harfe çevir
            brand = p.name.split()[0].upper()
            all_brands.add(brand)
            # Template'de kullanmak için objeye geçici özellik ekle
            p.brand_name = brand

    # 2. Filtreleme İşlemleri
    query = request.GET.get('q')
    selected_brand = request.GET.get('brand')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    
    if selected_brand:
        # Case-insensitive (büyük/küçük harf duyarsız) başlangıç kontrolü
        products = [p for p in products if p.name.split()[0].upper() == selected_brand]

    context = {
        'products': products,
        'brands': sorted(list(all_brands)),
        'selected_brand': selected_brand,
        'query': query
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            messages.success(request, 'Ürün başarıyla eklendi!')
            return redirect('dashboard')
    else:
        form = ProductForm()
    return render(request, 'core/product_form.html', {'form': form, 'title': 'Yeni Ürün Ekle'})

@login_required
def add_competitor(request, product_id):
    product = get_object_or_404(Product, id=product_id, user=request.user)
    if request.method == 'POST':
        form = CompetitorForm(request.POST)
        if form.is_valid():
            competitor = form.save(commit=False)
            competitor.product = product
            competitor.save()
            messages.success(request, 'Rakip linki eklendi!')
            return redirect('dashboard')
    else:
        form = CompetitorForm()
    return render(request, 'core/product_form.html', {'form': form, 'title': f'{product.name} için Rakip Ekle'})

@login_required
def find_competitors(request, product_id):
    """Otomatik Rakip Bulucu"""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            Competitor.objects.create(product=product, url=url)
            messages.success(request, "Rakip başarıyla eklendi!")
            # Kullanıcı daha fazla eklemek isteyebilir, sayfada kalalım veya panele dönelim
            # Şimdilik panele dönüyoruz
            return redirect('dashboard')

    # Scraper'ı import et (Path sorunu yaşamamak için dinamik import)
    try:
        from sarscope.core.scraper import SarScopeScraper
    except ImportError:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if repo_root not in sys.path:
            sys.path.append(repo_root)
        from sarscope.core.scraper import SarScopeScraper

    results = []
    try:
        scraper = SarScopeScraper()
        # Ürün adını kullanarak arama yap
        results = scraper.search_products(product.name)
    except Exception as e:
        messages.error(request, f"Arama sırasında hata oluştu: {e}")

    return render(request, 'core/find_competitors.html', {'product': product, 'results': results})

@login_required
def scan_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, user=request.user)
    competitors = product.competitors.all()
    
    if not competitors:
        messages.warning(request, "Bu ürüne ait rakip linki bulunamadı.")
        return redirect('dashboard')

    # Celery ile asenkron tarama başlat
    scan_product_task.delay(product.id)
    
    messages.info(request, f"{product.name} için tarama arka planda başlatıldı. Sayfayı bir süre sonra yenileyin.")
    return redirect('dashboard')

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, user=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Ürün başarıyla silindi.')
        return redirect('dashboard')
    return render(request, 'core/product_confirm_delete.html', {'product': product})

@login_required
def analysis(request):
    """Grafik ve Analiz Sayfası"""
    products = Product.objects.filter(user=request.user).prefetch_related('competitors')
    
    labels = []
    my_prices = []
    comp_prices = []
    
    total_products = products.count()
    cheaper_count = 0
    total_profit = 0
    products_with_cost = 0
    total_competitors = 0
    platform_counts = {}
    
    for p in products:
        labels.append(p.name[:15] + "..." if len(p.name) > 15 else p.name)
        my_prices.append(float(p.my_price))
        
        # Kar hesaplama
        if p.cost_price:
            total_profit += (float(p.my_price) - float(p.cost_price))
            products_with_cost += 1

        # En düşük rakip fiyatını bul
        comps = p.competitors.all()
        total_competitors += comps.count()
        
        valid_prices = [float(c.current_price) for c in comps if c.current_price]
        
        if valid_prices:
            min_comp = min(valid_prices)
            comp_prices.append(min_comp)
            if float(p.my_price) < min_comp:
                cheaper_count += 1
        else:
            comp_prices.append(0)
            
        # Platform dağılımı
        for c in comps:
            name = c.marketplace_name or "Diğer"
            platform_counts[name] = platform_counts.get(name, 0) + 1

    # İstatistikler
    competitive_advantage = int((cheaper_count / total_products * 100)) if total_products > 0 else 0
    avg_profit = round(total_profit / products_with_cost, 2) if products_with_cost > 0 else 0
    
    platform_labels = list(platform_counts.keys())
    platform_data = list(platform_counts.values())

    context = {
        'labels': labels,
        'my_prices': my_prices,
        'comp_prices': comp_prices,
        'total_products': total_products,
        'competitive_advantage': competitive_advantage,
        'avg_profit': avg_profit,
        'total_competitors': total_competitors,
        'platform_labels': platform_labels,
        'platform_data': platform_data,
    }
    return render(request, 'core/analysis.html', context)
