from providers.base import BaseAsyncClient
from typing import Optional

class TMDBClient(BaseAsyncClient):
    """ Client for TMDB API. """
    def __init__(
        self,
        token: Optional[str]=None,
        language: str='en',
    ):
        headers = {
            'Authorization': f'Bearer {token}',
            'accept': 'application/json',
        }
        super().__init__(
            base_url='https://api.themoviedb.org',
            headers=headers,
        )
        
        self.language = 'en'
    
    async def list_movie_genres(self):
        """ Retrieve id-genre name mappings for movies listed on TMDB. """
        params = {
            'language': self.language,
        }
        resp = await self.client.get('/3/genre/movie/list', params=params)
        resp.raise_for_status()
        data = resp.json()
        return data

    async def list_tv_genres(self):
        """ Retrieve id-genre name mappings for tv series listed on TMDB. """
        params = {
            'language': self.language,
        }
        resp = await self.client.get('/3/genre/tv/list', params=params)
        resp.raise_for_status()
        data = resp.json()
        return data
    
    async def search_movie_by_title(
        self,
        query: str,
    ):
        params = {
            'query': query,
        }
        resp = await self.client.get('/3/search/movie', params=params)
        resp.raise_for_status()
        data = resp.json()
        
        results = data['results']
        return results

    async def search_movie_by_filter(
        self,
        with_cast: Optional[str],
        without_cast: Optional[str],
        with_genres: Optional[str],
        without_genres: Optional[str],
    ):
        params = {}
        
        if with_cast is not None:
            params['with_cast'] = with_cast

        if with_genres is not None:
            params['with_genres'] = with_genres

        resp = await self.client.get('/3/discover/movie', params=params)
        resp.raise_for_status()
        data = resp.json()
        return data

    async def search_tv_by_title(
        self,
        query: str,
    ):
        params = {
            'query': query,
        }
        resp = await self.client.get('/3/search/tv', params=params)
        resp.raise_for_status()
        data = resp.json()

        results = data['results']
        return results
        
