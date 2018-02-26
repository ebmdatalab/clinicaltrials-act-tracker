from datetime import date
from django.urls import include
from django.urls import path
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import reverse
from django.views.generic import TemplateView

from rest_framework import routers

from frontend.models import Ranking
from frontend.models import Trial
from frontend.models import Sponsor
from frontend import views

from .custom_rest_views import TrialViewSet
from .custom_rest_views import RankingViewSet
from .custom_rest_views import SponsorViewSet


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'trials', TrialViewSet, base_name='trials')
router.register(r'rankings', RankingViewSet)
router.register(r'sponsors', SponsorViewSet)

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['index',
                'views.trials',
                'views.about',
                'views.fund',
                'views.trials']

    def location(self, item):
        return reverse(item)

urlpatterns = [
    path('', views.index, name='index'),
    path('api/performance/', views.performance, name='performance'),
    path('api/', include(router.urls)),
    path('trials/', views.trials, name='views.trials'),
    path('sponsor/<slug:slug>/', views.sponsor, name='views.sponsor'),
    path('api/', include('rest_framework.urls')),
    path('about/', TemplateView.as_view(template_name="about.html"), name='views.about'),
    path('fund/', TemplateView.as_view(template_name="fund.html"), name='views.fund'),
    path('sitemap.xml', sitemap,
         {'sitemaps': {
             'static': StaticViewSitemap,
             'sponsor': GenericSitemap(
                 {'queryset': Sponsor.objects.all(),
                  'date_field': 'updated_date'}, priority=0.5),
         }},
         name='django.contrib.sitemaps.views.sitemap'),
    path('accounts/', include('django.contrib.auth.urls')),
]
