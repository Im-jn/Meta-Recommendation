from providers.base import BaseAsyncClient
from typing import Optional

class TikHubClient(BaseAsyncClient):
    def __init__(
        self,
        api_key: Optional[str]=None,
    ):
        headers = {
            'Authorization': f'Bearer {api_key}',
        }
        super().__init__(
            base_url='https://api.tikhub.io',
            headers=headers,
        )
    
    async def search_xiaohongshu(
        self,
        keyword: str
    ):
        params = {
            'keyword': keyword,
            'sort': 'general',
            'noteType': '不限', # any
            'noteTime': '不限', # any
            'page': 1,
        }
            
        resp = await self.client.get('/api/v1/xiaohongshu/app/search_notes', params=params)
        resp.raise_for_status()

        data = resp.json()
        
        results = data.get('data', {}).get('data', {}).get('items', [])
        results = [result for result in results if result.get('model_type') == 'note']
        
        return results

    async def get_xiaohongshu_note_details(
        self,
        note_id: str
    ):
        params = {
            'note_id': note_id,
        }
            
        resp = await self.client.get('/api/v1/xiaohongshu/app/get_note_info', params=params)
        resp.raise_for_status()

        data = resp.json()
        return data

    async def get_xiaohongshu_note_comments(
        self,
        note_id: str
    ):
        params = {
            'note_id': note_id,
        }
            
        resp = await self.client.get('/api/v1/xiaohongshu/app/get_note_comments', params=params)
        resp.raise_for_status()

        data = resp.json()
        return data
    
