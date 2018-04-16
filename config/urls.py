# -*- coding: utf-8 -*-
"""WAStD URLs."""
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin import site
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView
from django.views import defaults as default_views

from adminactions import actions
from djgeojson.views import GeoJSONLayerView, TiledGeoJSONLayerView
from rest_framework.authtoken import views as drf_authviews
from rest_framework.documentation import include_docs_urls
from ajax_select import urls as ajax_select_urls

# from dynamic_rest import routers as dr

# from graphene_django.views import GraphQLView
# from wastd.schema import schema

from wastd.api import router  # , sync_route
from wastd.observations.models import Area, Encounter, AnimalEncounter
from wastd.observations.views import (schema_view, HomeView,
                                      EncounterTableView, AnimalEncounterTableView)
from taxonomy.views import update_taxon, TaxonListView, CommunityListView

# register all adminactions
actions.add_to_site(site)

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='home'),
    url(r'^map/$', HomeView.as_view(), name='map'),


    url(r'^species/$', TaxonListView.as_view(), name='species-list'),
    url(r'^communities/$', CommunityListView.as_view(), name='community-list'),


    url(r'^about/$', TemplateView.as_view(template_name='pages/about.html'), name='about'),

    url(r'^grappelli/', include('grappelli.urls')),  # grappelli URLs
    url(r'^ajax_select/', include(ajax_select_urls)),  # ajax select URLs
    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, include(admin.site.urls)),

    # User management
    url(r'^users/', include('wastd.users.urls', namespace='users')),
    url(r'^accounts/', include('allauth.urls')),

    # Encounters
    url(r'^encounters/$', EncounterTableView.as_view(), name="encounter_list"),
    url(r'^animal-encounters/$', AnimalEncounterTableView.as_view(), name="animalencounter_list"),

    # API
    url(r'^api/1/swagger/$', schema_view, name="api-docs"),
    url(r'^api/1/docs/', include_docs_urls(title='API')),
    url(r'^api/1/', include(router.urls, namespace="api")),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', drf_authviews.obtain_auth_token, name="api-auth"),

    # GraphQL
    # url(r'^graphql', GraphQLView.as_view(graphiql=True, schema=schema)),

    # Synctools
    # url("^sync/", include(sync_route.urlpatterns)),

    url(r'^adminactions/', include('adminactions.urls')),
    url(r'^select2/', include('django_select2.urls')),

    # Djgeojson
    url(r'^observations.geojson$',
        GeoJSONLayerView.as_view(model=Encounter,
                                 properties=('as_html', ),
                                 geometry_field="where"),
        name='observation-geojson'),

    url(r'^areas.geojson$',
        GeoJSONLayerView.as_view(
            model=Area,
            properties=('leaflet_title', 'as_html')),
        name='areas-geojson'),

    # Encounter as tiled GeoJSON
    url(r'^data/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+).geojson$',
        TiledGeoJSONLayerView.as_view(
            model=AnimalEncounter,
            properties=(
                'as_html',
                'leaflet_title',
                'leaflet_icon',
                'leaflet_colour'),
            geometry_field="where"),
        name='encounter-tiled-geojson'),

    # url(r'^areas/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+).geojson$',
    #     TiledGeoJSONLayerView.as_view(
    #         model=Area,
    #         properties=('name',),
    #         geometry_field="geom"),
    #     name='area-tiled-geojson'),

    url(r'^action/update-taxon/$', update_taxon, name="update-taxon"),

    url(r'^400/$', default_views.bad_request,
        kwargs={'exception': Exception('Bad Request!')}),

    url(r'^403/$', default_views.permission_denied,
        kwargs={'exception': Exception('Permission Denied')}),

    url(r'^404/$', default_views.page_not_found,
        kwargs={'exception': Exception('Page not Found')}),

    # url(r'^500/$', default_views.server_error,
    #     kwargs={'exception': Exception('Infernal Server Error')}),

] +\
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) +\
    staticfiles_urlpatterns() +\
    [url(r'^performance/', include('silk.urls', namespace='silk'))]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls)), ]
