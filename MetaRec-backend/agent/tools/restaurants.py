async def search_restaurants_google(query: str, ctx: any):
    results = await ctx.serpapi.search_google(query)
    items = []
    for result in results:
        items.append(result['title'])
    return items

async def search_restaurants_yelp(query: str, location: str, ctx: any):
    results = await ctx.serpapi.search_yelp(query, location)
    items = []
    for result in results:
        items.append(result['title'])
    return items
