from django import forms
from .models import Product, Competitor

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'cost_price', 'my_price', 'min_price_limit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örn: Bosch Matkap'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU-123'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'my_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_price_limit': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CompetitorForm(forms.ModelForm):
    class Meta:
        model = Competitor
        fields = ['url', 'marketplace_name']
        widgets = {
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'marketplace_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trendyol, Amazon vb.'}),
        }