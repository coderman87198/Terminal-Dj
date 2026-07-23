from django.urls import path
from .views import (
    build_mix,
    curate_playlist,
    demo_mix,
    download_mix,
    download_track,
    index,
    search_tracks,
)

urlpatterns = [
    path('', index, name='index'),
    path('search/', search_tracks, name='search_tracks'),
    path('download/', download_track, name='download_track'),
    path('mix/', build_mix, name='build_mix'),
    path('curate/', curate_playlist, name='curate_playlist'),
    path('demo/', demo_mix, name='demo_mix'),
    path('download-mix/<path:filename>/', download_mix, name='download_mix'),
]
