from django.contrib import admin
from django.urls import path
from shop import views

urlpatterns = [
    path("",views.store_page,name="store_page"),
    path("products/",views.product_list,name="product_list"),
    # 批量订单路径
    path("products/bulk_order/", views.bulk_order, name="bulk_order"),
    # 单个商品详情路径（如果需要）
    path('products/search/', views.product_search, name='product_search'),
]