from django.views.generic import TemplateView
from decimal import Decimal
from django.db.models import Sum
from .models import BunnyVideoAnalytics, BunnyRateConfiguration

class VideoCostDashboardView(TemplateView):
    """
    Specific visualization deck highlighting individual unit wastage and 
    peak load streams across global edge network delivery systems.
    """
    template_name = "bunny_analytics/video_intel_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Fetch ordered worst-offenders
        ranked_videos = BunnyVideoAnalytics.objects.all().order_by('-calculated_total_cost_usd')[:10]
        context['leaderboard'] = ranked_videos
        
        # Aggregates
        stats = BunnyVideoAnalytics.objects.aggregate(
            t_cost=Sum('calculated_total_cost_usd'),
            t_views=Sum('total_views'),
            t_storage=Sum('storage_size_bytes'),
            t_bw=Sum('bandwidth_used_bytes')
        )
        
        context['total_cost'] = stats.get('t_cost') or 0
        context['total_views'] = stats.get('t_views') or 0
        
        raw_gb = (stats.get('t_storage') or 0) / (1024**3)
        context['total_gb'] = Decimal(raw_gb).quantize(Decimal('0.01'))
        
        raw_bw = (stats.get('t_bw') or 0) / (1024**3)
        context['total_bw'] = Decimal(raw_bw).quantize(Decimal('0.01'))
        
        context['active_config'] = BunnyRateConfiguration.objects.filter(is_active=True).first()
        
        return context
