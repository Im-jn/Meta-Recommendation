from hishel import CacheOptions, SpecificationPolicy
from hishel.httpx import AsyncCacheClient
from hishel import AsyncSqliteStorage

async def log_response(resp):
    is_cached = resp.extensions.get('hishel_from_cache', False)
    cached = 'HIT' if is_cached else 'MISS'
    status_code = resp.status_code
    url = resp.url 
    print(f'[{status_code}, CACHE {cached}] {url}')

class BaseAsyncClient:
    def __init__(self, *args, **kwargs):
        #print('init client', args, kwargs)
        storage = AsyncSqliteStorage(
            database_path='temp_cache.db'
        )
        
        event_hooks = {
            'response': [log_response],
        }
        self.client = AsyncCacheClient(
            *args, 
            **kwargs,
            policy=SpecificationPolicy(
                cache_options=CacheOptions(
                    shared=True,
                    allow_stale=True,
                ),
            ),
            storage=storage,
            event_hooks=event_hooks,
        )
    
    def log_response_cache_hit_status(self, resp):
        response_from_cache = resp.extensions.get('hishel_from_cache', False)
        #print(f'Using cached response? {response_from_cache}')


