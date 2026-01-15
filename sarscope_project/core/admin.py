from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.management import call_command
from django.template.response import TemplateResponse
from .models import Product, Competitor

class CompetitorInline(admin.TabularInline):
    model = Competitor
    extra = 0
    readonly_fields = ('last_updated',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'my_price', 'competitor_count')
    search_fields = ('name', 'sku')
    inlines = [CompetitorInline]
    actions = ['send_test_mail_action']
    change_list_template = "admin/core/product/change_list.html"

    def competitor_count(self, obj):
        return obj.competitors.count()
    competitor_count.short_description = 'Rakip Sayısı'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-inventory/', self.admin_site.admin_view(self.sync_inventory_view), name='product_sync_inventory'),
            path('run-trend-hunter/', self.admin_site.admin_view(self.run_trend_hunter_view), name='product_run_trend_hunter'),
            path('run-price-patrol/', self.admin_site.admin_view(self.run_price_patrol_view), name='product_run_price_patrol'),
        ]
        return custom_urls + urls

    # --- ACTIONS (Seçili Ürünler İçin) ---
    def send_test_mail_action(self, request, queryset):
        """Seçili ürünler için mail gönderir"""
        count = 0
        for product in queryset:
            try:
                # Komutu çağırıyoruz (ID parametresi ile)
                call_command('send_product_alert', str(product.id))
                count += 1
            except Exception as e:
                self.message_user(request, f"Hata ({product.name}): {e}", level=messages.ERROR)
        
        if count > 0:
            self.message_user(request, f"{count} ürün için test maili gönderildi.", level=messages.SUCCESS)
    send_test_mail_action.short_description = "📨 Seçili ürünler için Test Maili Gönder"

    # --- VIEWS (Genel Butonlar İçin) ---
    def sync_inventory_view(self, request):
        try:
            call_command('sync_inventory')
            self.message_user(request, "Envanter senkronizasyonu tamamlandı.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Hata: {e}", level=messages.ERROR)
        return HttpResponseRedirect("../")

    def run_price_patrol_view(self, request):
        try:
            call_command('run_price_patrol')
            self.message_user(request, "Price Patrol taraması tamamlandı. Mailler gönderildi.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Hata: {e}", level=messages.ERROR)
        return HttpResponseRedirect("../")

    def run_trend_hunter_view(self, request):
        if request.method == 'POST':
            url = request.POST.get('url')
            if url:
                try:
                    call_command('run_trend_hunter', url)
                    self.message_user(request, "Trend Hunter raporu admine gönderildi.", level=messages.SUCCESS)
                    return HttpResponseRedirect("../")
                except Exception as e:
                    self.message_user(request, f"Hata: {e}", level=messages.ERROR)
        
        context = dict(
           self.admin_site.each_context(request),
           title="Trend Hunter Başlat",
        )
        return TemplateResponse(request, "admin/core/product/trend_hunter_form.html", context)

@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ('product', 'marketplace_name', 'current_price', 'last_updated')
    list_filter = ('marketplace_name',)