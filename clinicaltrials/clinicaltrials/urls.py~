"""euctr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.views.generic import TemplateView

import frontend.views

urlpatterns = [
    url(r'^$', frontend.views.index),
    url(r'^screenshot$', frontend.views.index_screenshot, name="index_screenshot"),
    url(r'^screenshot-0003.png$', frontend.views.index_screenshot_png, name="index_screenshot_png"),

    url(r'^sponsor/(?P<slug>[a-z0-9-]+)$', frontend.views.sponsor),
    url(r'^sponsor/(?P<slug>[a-z0-9-]+)/screenshot$', frontend.views.sponsor_screenshot, name="sponsor_screenshot"),
    url(r'^sponsor/(?P<slug>[a-z0-9-]+)/screenshot.png$', frontend.views.sponsor_screenshot_png, name="sponsor_screenshot_png"),

    url(r'^about$', frontend.views.about),
]
