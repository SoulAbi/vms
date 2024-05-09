from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Count, Avg, F
from django.utils import timezone
from .models import Vendor, PurchaseOrder, HistoricalPerformance
from .serializers import VendorSerializer, PurchaseOrderSerializer
from django.db.models import F, Case, When, BooleanField
from datetime import datetime


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer

    def perform_create(self, serializer):
        serializer.save(issue_date=timezone.now())

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status == 'completed':
            self.update_performance_metrics(instance.vendor)

    def update_performance_metrics(self, vendor):
        completed_orders = vendor.purchase_orders.filter(status='completed')
        total_completed_orders = completed_orders.count()
        
        if total_completed_orders > 0:
            on_time_delivery_count = completed_orders.annotate(
                is_on_time=Case(
                    When(delivery_date__lte=F('acknowledgment_date'), then=True),
                    default=False,
                    output_field=BooleanField()
                )
            ).filter(is_on_time=True).count()
            on_time_delivery_rate = (on_time_delivery_count / total_completed_orders) * 100
            
            quality_rating_avg = completed_orders.aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0
                        
            response_time_avg_seconds = completed_orders.aggregate(
                response_time_avg=Avg(F('acknowledgment_date') - F('issue_date'))
            )['response_time_avg']
            response_time_avg = response_time_avg_seconds.total_seconds() if response_time_avg_seconds else 0

            fulfillment_rate = (completed_orders.exclude(quality_rating=None).count() / total_completed_orders) * 100
            
            HistoricalPerformance.objects.create(
                vendor=vendor,
                date=timezone.now(),
                on_time_delivery_rate=on_time_delivery_rate,
                quality_rating_avg=quality_rating_avg,
                average_response_time=response_time_avg,
                fulfillment_rate=fulfillment_rate
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        vendor_id = request.query_params.get('vendor')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VendorPerformanceViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None):
        vendor = Vendor.objects.get(pk=pk)
        last_performance_record = vendor.historical_performance.last()

        if last_performance_record:
            data = {
                'vendor': last_performance_record.vendor_id,
                'date': last_performance_record.date,
                'on_time_delivery_rate': last_performance_record.on_time_delivery_rate,
                'quality_rating_avg': last_performance_record.quality_rating_avg,
                'average_response_time': last_performance_record.average_response_time,
                'fulfillment_rate': last_performance_record.fulfillment_rate
            }
        else:
            data = {
                'vendor': vendor.id,
                'date': datetime.now(),
                'on_time_delivery_rate': 0,
                'quality_rating_avg': 0,
                'average_response_time': 0,
                'fulfillment_rate': 0
            }

        return Response(data)
