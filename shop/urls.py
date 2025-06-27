from django.contrib import admin
from django.urls import path
from shop import views

urlpatterns = [
    path("products/", views.bulk_order, name="bulk_order"),
    path("products/<int:product_id>", views.product_search, name="product"),
]