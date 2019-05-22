from django.urls import include
from django.urls import path
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from rest_framework import routers

from frontend.models import Sponsor
from frontend.models import Trial
from frontend import views
from frontend import management_views

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
        return ['views.latest_overdue',
                'views.rankings',
                'views.trials',
                'views.about',
                'views.fund',
                'views.trials']

    def location(self, item):
        return reverse(item)

urlpatterns = [
    path('', views.latest_overdue, name='views.latest_overdue'),
    path('rankings/', views.rankings, name='views.rankings'),
    path('api/performance/', views.performance, name='views.performance'),
    path('api/', include(router.urls)),
    path('trials/', views.trials, name='views.trials'),
    path('trial/<str:registry_id>/', views.trial, name='views.trial'),
    path('sponsor/<slug:slug>/', views.sponsor, name='views.sponsor'),
    path('api/', include('rest_framework.urls')),
    path('faq/', TemplateView.as_view(template_name="faq.html"), name='views.faq'),
    path('fund/', TemplateView.as_view(template_name="fund.html"), name='views.fund'),
    path('pages/<path:path>', views.static_markdown, name='views.static_markdown'),
    path('sitemap.xml', sitemap,
         {'sitemaps': {
             'static': StaticViewSitemap,
             'sponsor': GenericSitemap(
                 {'queryset': Sponsor.objects.all(),
                  'date_field': 'updated_date'}, priority=0.5),
             'trial': GenericSitemap(
                 {'queryset': Trial.objects.all(),
                  'date_field': 'updated_date'}, priority=0.5),
         }},
         name='django.contrib.sitemaps.views.sitemap'),
    path('accounts/', include('django.contrib.auth.urls')),

    # Redirects
    path('about/', RedirectView.as_view(url='/faq/', permanent=True), name='views.about'),

    # Management endpoints
    path('management/process_data/<path:path>', management_views.process_data),
    path('management/load_data/', management_views.load_data),

]
