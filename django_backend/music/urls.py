from django.urls import path
from .views import (
    build_mix,
    curate_playlist,
    demo_mix,
    download_mix,
    download_track,
    index,
    search_tracks,
    search_health,
)

urlpatterns = [
    path('', index, name='index'),
    path('api/search/', search_tracks, name='search_tracks'),
    path('api/search-health/', search_health, name='search_health'),
    path('api/download/', download_track, name='download_track'),
    path('api/mix/', build_mix, name='build_mix'),
    path('api/curate/', curate_playlist, name='curate_playlist'),
    path('api/demo/', demo_mix, name='demo_mix'),
    path('download-mix/<path:filename>/', download_mix, name='download_mix'),
]
