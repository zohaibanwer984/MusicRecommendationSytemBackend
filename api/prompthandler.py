from fuzzywuzzy import fuzz, process
import numpy as np
from .models import Favorite

# Dynamic threshold calculations for various attributes
def calculate_dynamic_thresholds(songs_df):
    thresholds = {}
    for column in ['acousticness', 'energy', 'valence', 'tempo']:
        mean = songs_df[column].mean()
        std_dev = songs_df[column].std()
        thresholds[column] = {
            "low": mean - std_dev,
            "medium": mean,
            "high": mean + std_dev
        }
    return thresholds

# Function to extract closest matching genre with fuzzy matching
def get_fuzzy_genre_match(prompt, all_genres, threshold=80):
    match, score = process.extractOne(prompt, all_genres, scorer=fuzz.token_sort_ratio)
    return match if score >= threshold else None

# Filter function with dynamic thresholds and fuzzy genre matching
def filter_songs_by_prompt(prompt, songs_df):
    # Calculate thresholds dynamically
    thresholds = calculate_dynamic_thresholds(songs_df)
    # Default filters
    genre_filter, artist_filter, mood_filter, tempo_filter, popularity_filter, year_filter = None, None, None, None, None, None
    # Lowercase the prompt for easier matching
    prompt = prompt.lower()
    # Genre extraction with fuzzy matching
    all_genres = set(g for sublist in songs_df['genres'] for g in sublist)
    genre_filter = get_fuzzy_genre_match(prompt, all_genres)
    # Artist extraction from dataset
    all_artists = set(a for sublist in songs_df['artist_names'] for a in sublist)
    for artist in all_artists:
        if artist.lower() in prompt:
            artist_filter = artist
            break
    # Mood-based filtering
    if "calm" in prompt or "chill" in prompt:
        mood_filter = ("energy", "<", thresholds["energy"]["low"])
        mood_filter = ("acousticness", ">", thresholds["acousticness"]["high"])
    elif "intense" in prompt or "high energy" in prompt:
        mood_filter = ("energy", ">", thresholds["energy"]["high"])
    elif "happy" in prompt:
        mood_filter = ("valence", ">", thresholds["valence"]["high"])
    elif "sad" in prompt:
        mood_filter = ("valence", "<", thresholds["valence"]["low"])
    # Tempo filtering
    if "fast" in prompt or "upbeat" in prompt:
        tempo_filter = ("tempo", ">", thresholds["tempo"]["high"])
    elif "slow" in prompt:
        tempo_filter = ("tempo", "<", thresholds["tempo"]["low"])
    # Popularity filtering
    if "popular" in prompt:
        popularity_filter = songs_df["popularity"] > songs_df["popularity"].mean()
    # Year filtering based on decades or specific years
    if any(year in prompt for year in map(str, range(1900, 2030))):
        for year in map(str, range(1900, 2030)):
            if year in prompt:
                year_filter = (int(year), int(year))
                break
    # Applying filters to the dataset
    filtered_songs = songs_df
    if genre_filter:
        filtered_songs = filtered_songs[filtered_songs["genres"].apply(lambda x: genre_filter in x)]
    if artist_filter:
        filtered_songs = filtered_songs[filtered_songs["artist_names"].apply(lambda x: artist_filter in x)]
    if mood_filter:
        column, operator, value = mood_filter
        if operator == "<":
            filtered_songs = filtered_songs[filtered_songs[column] < value]
        elif operator == ">":
            filtered_songs = filtered_songs[filtered_songs[column] > value]
    if tempo_filter:
        column, operator, value = tempo_filter
        if operator == "<":
            filtered_songs = filtered_songs[filtered_songs[column] < value]
        elif operator == ">":
            filtered_songs = filtered_songs[filtered_songs[column] > value]
    if popularity_filter is not None:
        filtered_songs = filtered_songs[popularity_filter]
    if year_filter:
        start_year, end_year = year_filter
    filtered_songs = filtered_songs[(filtered_songs["year"] >= start_year) & (filtered_songs["year"] <= end_year)]
    # Fallback: most popular songs if no strong filter match
    if filtered_songs.empty:
        filtered_songs = songs_df.sort_values(by="popularity", ascending=False).head(10)
    
    return filtered_songs

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def get_recommendations_from_favorites(user_id, songs_df, n_recommendations=10):
    """
    Generate song recommendations based on a user's favorite songs.
    
    Parameters:
    - user_id (int): The ID of the user whose favorites are used for recommendations.
    - songs_df (DataFrame): The main dataset containing all song details.
    - n_recommendations (int): Number of recommendations to return.

    Returns:
    - DataFrame: A DataFrame with recommended songs.
    """

    # Step 1: Retrieve favorite songs IDs from the database
    favorite_track_ids = list(Favorite.objects.filter(user_id=user_id).values_list('track_id', flat=True))
    if not favorite_track_ids:
        print("No favorites found for this user.")
        return pd.DataFrame()  # Return an empty DataFrame if no favorites

    # Step 2: Filter the songs_df to include only the user's favorite songs
    user_favorites_df = songs_df[songs_df['track_id'].isin(favorite_track_ids)].copy()

    # Step 3: Select features for clustering (e.g., popularity, year, and any other numeric features available)
    features = ['popularity', 'year']  # Adjust these features based on your dataset
    user_favorites_features = user_favorites_df[features]

    # Standardize the features
    scaler = StandardScaler()
    user_favorites_scaled = scaler.fit_transform(user_favorites_features)

    # Step 4: Apply K-means clustering to find clusters within favorite songs
    kmeans = KMeans(n_clusters=3, random_state=42)  # Adjust clusters as needed
    user_favorites_df['cluster'] = kmeans.fit_predict(user_favorites_scaled)

    # Step 5: Recommend songs from the main dataset that are in the same clusters
    # Select non-favorite songs for recommendations
    non_favorites_df = songs_df[~songs_df['track_id'].isin(favorite_track_ids)].copy()

    # Scale the features in the non-favorites dataset for consistent clustering
    non_favorites_scaled = scaler.transform(non_favorites_df[features])
    non_favorites_df['cluster'] = kmeans.predict(non_favorites_scaled)

    # Filter songs by matching clusters with user favorites
    recommended_df = non_favorites_df[non_favorites_df['cluster'].isin(user_favorites_df['cluster'].unique())]

    # Step 6: Return a sample of recommendations
    return recommended_df.sample(n=min(n_recommendations, len(recommended_df)), random_state=42)
