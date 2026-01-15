from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('trend-hunter/', views.trend_hunter, name='trend_hunter'),
    path('run-price-patrol/', views.run_price_patrol, name='run_price_patrol'),
    path('send-report/<str:report_type>/', views.send_report, name='send_report'),
    path('send-trend-report/', views.send_trend_report, name='send_trend_report'),
    path('add-product/', views.add_product, name='add_product'),
    path('add-competitor/<int:product_id>/', views.add_competitor, name='add_competitor'),
    path('find-competitors/<int:product_id>/', views.find_competitors, name='find_competitors'),
    path('scan/<int:product_id>/', views.scan_product, name='scan_product'),
    path('delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('analysis/', views.analysis, name='analysis'),
]