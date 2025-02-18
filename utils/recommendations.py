import requests
import urllib.parse
from config import LASTFM_API_KEY
from sqlDb.db import get_recent_searches

async def get_similar_tracks(artist: str, track: str):
    # Кодуємо параметри для URL
    artist_enc = urllib.parse.quote(artist)
    track_enc = urllib.parse.quote(track)
    url = f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={artist_enc}&track={track_enc}&api_key={LASTFM_API_KEY}&format=json"
    response = requests.get(url)
    data = response.json()
    similar_tracks = []
    for t in data.get('similartracks', {}).get('track', []):
        similar_tracks.append({
            'title': t.get('name'),
            'artist': t.get('artist', {}).get('name'),
            'url': t.get('url')
        })
    return similar_tracks

async def get_recommendations(user_id, limit=5):
    recent_tracks = await get_recent_searches(user_id)
    recommendations = []
    for track in recent_tracks:
        # Тепер track – це словник з ключами 'artist' і 'song'
        similar = await get_similar_tracks(track['artist'], track['song'])
        recommendations.extend(similar)
    # Далі можна агрегувати дані за частотою чи рейтингом
    return recommendations[:limit]
