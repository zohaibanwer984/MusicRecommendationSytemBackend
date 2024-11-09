from django.urls import path
from .views import PromptView, FavoritesListView, AddFavoriteView, RemoveFavoriteView, DiscoverView, GetUserName

urlpatterns = [
    path('prompt/', PromptView.as_view(), name='prompt'),
    path('favorites/', FavoritesListView.as_view(), name='favorites-list'),
    path('favorites/add/', AddFavoriteView.as_view(), name='favorites-add'),
    path('favorites/remove/<str:track_id>/', RemoveFavoriteView.as_view(), name='favorites-remove'),
    path('discover/', DiscoverView.as_view(), name='discover-view'),
    path('username/', GetUserName.as_view(), name="get-username"),
]
