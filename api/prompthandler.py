from fuzzywuzzy import fuzz, process
import numpy as np

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
    if "80s" in prompt:
        year_filter = (1980, 1989)
    elif "90s" in prompt:
        year_filter = (1990, 1999)
    elif "2000s" in prompt:
        year_filter = (2000, 2009)
    elif "2010s" in prompt:
        year_filter = (2010, 2019)
    elif "2020s" in prompt:
        year_filter = (2020, 2029)
    elif any(year in prompt for year in map(str, range(1900, 2030))):
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