import logging
import time

from django.shortcuts import render
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse

import selenium.webdriver

from . import models

driver = selenium.webdriver.PhantomJS()
def _capture_screenshot(width, url):
    driver.set_window_size(width, 100)
    driver.get(url)
    png_binary = driver.get_screenshot_as_png()
    return HttpResponse(png_binary, 'image/png')


#############################################################################
# Index page

def index(request):
    context = models.get_headlines()

    context['showing_all_sponsors'] = 'all' in request.GET
    context['activate_search'] = 'search' in request.GET
    if context['activate_search']:
        context['showing_all_sponsors'] = True

    if context['showing_all_sponsors']:
        context['sponsors'] = models.get_all_sponsors()
    else:
        context['sponsors'] = models.get_major_sponsors()
    context['load_js_at_start'] = True

    context['social_image'] = request.build_absolute_uri(
        reverse("index_screenshot_png")
    )

    return render(request, "index.html", context=context)

def index_screenshot(request):
    context = models.get_headlines().copy()
    context['taking_screenshot'] = True
    return render(request, "index_screenshot.html", context=context)

def index_screenshot_png(request):
    return _capture_screenshot(1024, request.build_absolute_uri(
        reverse("index_screenshot"))
    )


#############################################################################
# Sponsor page

def sponsor(request, slug):
    return _sponsor(request, slug, "sponsor.html", False)

def sponsor_screenshot(request, slug):
    return _sponsor(request, slug, "sponsor_screenshot.html", True)

def _sponsor(request, slug, template_name, taking_screenshot):
    context = models.get_sponsor(slug).copy()

    context['trials'] = models.get_trials(slug)
    context['load_js_at_start'] = True
    context['taking_screenshot'] = taking_screenshot

    if not taking_screenshot:
        context['social_image'] = request.build_absolute_uri(
            reverse("sponsor_screenshot_png", kwargs={"slug": slug})
        )
    return render(request, template_name, context=context)

def sponsor_screenshot_png(request, slug):
    return _capture_screenshot(1024, request.build_absolute_uri(
        reverse("sponsor_screenshot", kwargs={"slug": slug}))
    )


#############################################################################
# About page

def about(request):
    context = models.get_headlines()

    context['social_image'] = request.build_absolute_uri(
        reverse("index_screenshot_png")
    )

    return render(request, "about.html", context=context)
