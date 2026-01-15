from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', verbose_name="Kullanıcı")
    name = models.CharField(max_length=255, verbose_name="Ürün Adı")
    sku = models.CharField(max_length=100, blank=True, null=True, verbose_name="Stok Kodu")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Maliyet")
    my_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Satış Fiyatım")
    min_price_limit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Min. Fiyat Limiti")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

class Competitor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='competitors', verbose_name="Bağlı Ürün")
    url = models.URLField(max_length=500, verbose_name="Rakip Linki")
    marketplace_name = models.CharField(max_length=100, verbose_name="Pazaryeri (Trendyol/Amazon)")
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Güncel Fiyat")
    in_stock = models.BooleanField(default=True, verbose_name="Stokta Var mı?")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Son Güncelleme")

    def __str__(self):
        return f"{self.marketplace_name} - {self.product.name}"

    class Meta:
        verbose_name = "Rakip"
        verbose_name_plural = "Rakipler"