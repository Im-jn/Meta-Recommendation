from typing import Optional

async def search_music(query: str, ctx: any):
    """
    Lucene query. 
    see: https://musicbrainz.org/doc/MusicBrainz_API/Search#Recording
    """

    results = await ctx.musicbrainz.search_recordings(query)
    items = []
    for result in results:
        items.append(result['title'])
    
    return items

async def search_movies_by_title(query: str, ctx: any):
    results = await ctx.tmdb.search_movie_by_title(query)
    items = []
    for result in results:
        items.append(result['original_title'])
    return items

async def search_tv_by_title(query: str, ctx: any):
    results = await ctx.tmdb.search_tv_by_title(query)
    items = []
    for result in results:
        items.append(result['original_name'])
    return items

async def search_movies_by_filter(
        with_cast: Optional[str],
        without_cast: Optional[str],
        with_genres: Optional[str],
        without_genres: Optional[str],
        ctx: any,
    ):
    
    results = await ctx.tmdb.search_movies_by_filter(
        with_cast=with_cast,
        without_cast=without_cast,
        with_genres=with_genres,
        without_genres=without_genres,
    )
    items = []
    for result in results:
        print(result)
        items.append('placeholder movie')
    return items

async def search_books(query: str, ctx: any):
    """
    graphql query
    """
    results = await ctx.hardcover.search_books_by_genre(query)
    items = []
    for result in results:
        items.append(result['document']['title'])
    return items
