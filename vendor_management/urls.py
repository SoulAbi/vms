from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, PurchaseOrderViewSet, VendorPerformanceViewSet

router = DefaultRouter()
router.register(r'vendors', VendorViewSet)
router.register(r'purchase_orders', PurchaseOrderViewSet)

urlpatterns = [
    path('vendors/<int:pk>/performance/', VendorPerformanceViewSet.as_view({'get': 'retrieve'}), name='vendor_performance'),
]

urlpatterns += router.urls
