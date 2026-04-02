async def search_music(query: str, ctx: any):
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

async def search_books(query: str, ctx: any):
    results = await ctx.hardcover.search_books_by_genre(query)
    items = []
    for result in results:
        items.append(result['document']['title'])
    return items
