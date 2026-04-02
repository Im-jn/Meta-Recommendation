async def search_products_amazon(
    query: str,
    ctx: any,
):
    results = await ctx.serpapi.search_amazon(query)
    items = []
    for result in results:
        items.append(result['title'])
    return items

    
