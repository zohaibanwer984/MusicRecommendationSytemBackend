from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.cache import cache
from .models import Favorite
from django.conf import settings
import pandas as pd
import os
from .prompthandler import filter_songs_by_prompt

# Load and cache the dataset upon server start-up if not already cached
def load_dataset():
    if not cache.get('songs_df'):
        songs = pd.read_csv(os.path.join(settings.BASE_DIR, 'dataset', 'processes_dataset.csv'))
        songs = songs.drop_duplicates(subset=['track_id'])
        cache.set('songs_df', songs, timeout=None)  # No timeout to keep it persistently cached


# Ensure dataset is loaded at startup
load_dataset()

class IsLoggedin(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(
            {},
            status= status.HTTP_204_NO_CONTENT
        )

class GetUserName(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
         first_name = request.user.first_name
         last_name = request.user.last_name
         username = request.user.username
         return Response({
            "username": username,
            "firstname": first_name,
            "lastname": last_name,
        }, status=status.HTTP_200_OK)

class PromptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        prompt = request.data.get("prompt")
        if not prompt:
            return Response({"error": "No prompt provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the dataset from cache
        songs_df = cache.get('songs_df')
        recommendations = filter_songs_by_prompt(prompt, songs_df).head(10)
        recommendations = recommendations[["track_id", 
                                           "track_name", 
                                           "artist_names",
                                           "album_name",
                                           "year", 
                                           "duration_ms",
                                           "album_cover_64x64",
                                           "album_cover_640x640"
                                           ]]
        # Get track IDs from the Favorite model
        favorite_track_ids = set(Favorite.objects.filter(user=request.user).values_list('track_id', flat=True))

        # Create a new column in the DataFrame that checks if the track_id is in the favorites
        recommendations['is_favorite'] = recommendations['track_id'].isin(favorite_track_ids)
        
        return Response(recommendations.to_dict(orient='records'), status=status.HTTP_200_OK)

class DiscoverView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Retrieve the dataset from cache
        songs_df = cache.get('songs_df')

        if songs_df is None:
            return Response({"error": "Dataset is not available"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get query parameters for filtering and pagination
        filter_by = request.query_params.get('filter', 'popular')
        year = request.query_params.get('year')
        artist = request.query_params.get('artist')
        genre = request.query_params.get('genre')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Apply filters to the dataset
        filtered_df = songs_df.copy()

        # Filter by year if specified
        if year and year != 'null':
            filtered_df = filtered_df[filtered_df['year'] == int(year)]

        # Filter by artist if specified
        if artist!= 'null':
            filtered_df = filtered_df[
                filtered_df['artist_names'].apply(
                    lambda x: any(a.lower() == artist.lower() for a in x) if isinstance(x, list) else False
                )
            ]

        # Filter by genre if specified
        if genre!= 'null':
            filtered_df = filtered_df[
                filtered_df['genres'].apply(
                    lambda x: any(g.lower() == genre.lower() for g in x) if isinstance(x, list) else False
                )
            ]

        # Sort by popularity if requested
        if filter_by == 'popular':
            filtered_df = filtered_df.sort_values(by='popularity', ascending=False)
        
        if filter_by == 'new':
            filtered_df = filtered_df.sort_values(by='year', ascending=False)
        

        # Get track IDs from the Favorite model
        favorite_track_ids = set(Favorite.objects.filter(user=request.user).values_list('track_id', flat=True))

        # Create a new column in the DataFrame that checks if the track_id is in the favorites
        filtered_df = filtered_df[["track_id", 
                                           "track_name", 
                                           "artist_names",
                                           "album_name",
                                           "year", 
                                           "duration_ms",
                                           "album_cover_64x64",
                                           "album_cover_640x640"
                                           ]]
        filtered_df['is_favorite'] = filtered_df['track_id'].isin(favorite_track_ids)
        
        # Pagination
        total_songs = filtered_df['track_id'].nunique()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Ensure the end index does not exceed the total number of songs
        paginated_songs = filtered_df.iloc[start_idx:end_idx].to_dict(orient='records')
        
        return Response({
            "songs": paginated_songs,
            "page": page,
            "page_size": page_size,
            "total_songs": total_songs
        }, status=status.HTTP_200_OK)

class FavoritesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Retrieve user's favorites track IDs
        favorite_track_ids = Favorite.objects.filter(user=request.user).values_list('track_id', flat=True)

        # Retrieve the dataset from cache
        songs_df: pd.DataFrame = cache.get('songs_df')
        if songs_df is None:
            return Response({"error": "Dataset is not available"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Filter dataset to include only user's favorite tracks
        favorite_songs_df = songs_df[songs_df['track_id'].isin(favorite_track_ids)]

        # Format response data similar to other endpoints
        favorite_songs = favorite_songs_df[[
            "track_id", 
            "track_name", 
            "artist_names", 
            "album_name", 
            "year", 
            "duration_ms", 
            "album_cover_64x64", 
            "album_cover_640x640"
        ]].to_dict(orient='records')

        return Response(favorite_songs, status=status.HTTP_200_OK)


class AddFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        track_id = request.data.get("track_id")
        track_name = request.data.get("track_name")

        if not all([track_id, track_name]):
            return Response(
                {"error": "song_id and song_name both are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            track_id=track_id,
            defaults={
                'track_name': track_name,
            }
        )

        if created:
            return Response({"message": "Favorite added successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "Item already in favorites"}, status=status.HTTP_200_OK)

class RemoveFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, track_id):
        try:
            favorite = Favorite.objects.get(user=request.user, track_id=track_id)
            favorite.delete()
            return Response({"message": "Favorite removed successfully"}, status=status.HTTP_200_OK)
        except Favorite.DoesNotExist:
            return Response({"error": "Favorite item not found"}, status=status.HTTP_404_NOT_FOUND)
