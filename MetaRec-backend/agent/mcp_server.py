import dotenv
from fastmcp import FastMCP
from typing import Annotated, Optional
from context import ClientContext
import tools.restaurants
import tools.entertainment
import tools.shopping

# load environment variables
dotenv.load_dotenv(dotenv.find_dotenv())
mcp = FastMCP()
ctx = ClientContext()

# register tools
@mcp.tool(
    name="search.restaurants.google",
)
async def search_restaurants_google(
        query:str,
    ) -> list[dict]:
    """ Search for restaurants using Google Maps. """
    results = await tools.restaurants.search_restaurants_google(query, ctx)
    return results

@mcp.tool(
    name="search.restaurants.xhs",
)
async def search_restaurants_xhs(
        query:str,
    ) -> list[any]:
    """ Search for restaurants using XiaoHongShu. """
    results = await tools.restaurants.search_restaurants_xiaohongshu(query, ctx)
    return results

@mcp.tool(
    name="search.restaurants.yelp",
)
async def search_restaurants_yelp(
        query: str,
        location: Annotated[str, 'Location'],
    ) -> list[any]:
    """ Search for restaurants using Yelp. """
    results = await tools.restaurants.search_restaurants_yelp(query, location, ctx)
    return results

@mcp.tool(
    name="search.books",
)
async def search_books(
        query: str,
    ) -> list[dict]:
    """ Search for books by genre. """
    results = await tools.entertainment.search_books(query, ctx)
    return results

@mcp.tool(
    name="search.music",
)
async def search_music(
        query: str,
    ) -> list[dict]:
    """ Search for music (using MusicBrainz). """
    results = await tools.entertainment.search_music(query, ctx)
    return results

@mcp.tool(
    name="search.movies_by_title",
)
async def search_movies_by_title(
        query: str,
    ) -> list[dict]:
    """ Search for movies by their title using TMDB. """
    results = await tools.entertainment.search_movies_by_title(query, ctx)
    return results

@mcp.tool(
    name="search.movies_by_genres",
)
async def search_movies_by_genres(
        with_genres: Optional[str]=None,
        without_genres: Optional[str]=None,
    ) -> list[dict]:
    """ Search (discover) movies by their TMDB genre ids. """
    results = await tools.entertainment.search_movies_by_genres(
        with_genres,
        without_genres,
        ctx
    )
    return results

@mcp.tool(
    name="search.tv_series_by_genres",
)
async def search_tv_by_genres(
        with_genres: Optional[str]=None,
        without_genres: Optional[str]=None,
    ) -> list[dict]:
    """ Search (discover) TV series by their TMDB genre ids. """
    results = await tools.entertainment.search_tv_by_genres(
        with_genres,
        without_genres,
        ctx
    )
    return results

@mcp.tool(
    name="search.tv_series_by_title",
)
async def search_tv_by_title(
        query: str,
    ) -> list[dict]:
    """ Search for TV series by their using TMDB. """
    results = await tools.entertainment.search_tv_by_title(query, ctx)
    return results

@mcp.tool(
    name="search.products.amazon",
)
async def search_products_amazon(
        query: str,
    ) -> list[dict]:
    """ Search for products on Amazon. """
    results = await tools.shopping.search_products_amazon(query, ctx)
    return results

if __name__ == '__main__':
    from fastmcp import Client
    import asyncio
    import json
    
    async def main():
        ''' 
        WIP: testing tools
        '''

        client = Client(mcp)

        async with client:

            print(str(client.session))
            tools = await client.list_tools()
            print("\n--- MCP Server Tools ---")
            for tool in tools:
                print(f"Tool: {tool.name}")
                print(f"Description: {tool.description}")
                print(f"Arguments: {tool.inputSchema}")
                print(f"Outputs: {tool.outputSchema}")
                print("-" * 20)
            
            # doesnt work, api requires payment
            #res = await client.call_tool('search.restaurants.xhs', {'query': 'sichuan food Singapore, Chinatown'})
            
            #res = await client.call_tool('search.restaurants.google', {'query': 'sichuan food'})

            #res = await client.call_tool('search.products.amazon', {'query': 'nintendo switch'})

            #res = await client.call_tool('search.restaurants.yelp', {'query': 'sichuan food', 'location': 'Singapore, Chinatown'})
            
            #res = await client.call_tool('search.books', {'query': 'Science Fiction'})
            
            #res = await client.call_tool('search.music', {'query': 'tag:rock'})

            #res = await client.call_tool('search.movies_by_title', {'query': 'jaws'})
            #res = await client.call_tool('search.tv_series_by_title', {'query': 'jaws'})
            
            #res = await client.call_tool('search.movies_by_genres', {'with_genres': '99'})
            res = await client.call_tool('search.tv_series_by_genres', {'with_genres': '99'})

            text = res.content[0].text
            data = json.loads(text)
            output = json.dumps(data, indent=2)
            print(output)

    asyncio.run(main())
