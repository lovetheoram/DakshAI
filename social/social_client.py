import requests
from django.conf import settings
import json
class SocialService:
    BASE = settings.SOCIAL_SERVICE_BASE_URL
    TENANT_ID = settings.SOCIAL_TENANT_ID
    API_KEY = settings.SOCIAL_API_KEY

    @classmethod
    def _headers(cls):
        return {
            "X-TENANT-ID": cls.TENANT_ID,
            "X-API-KEY": cls.API_KEY,
            "Content-Type": "application/json"
        }

    @classmethod
    def create_post(cls, author_id, content):
        print("hlleljelrkj")
        url = f"{cls.BASE}/posts/create/"
        payload = {
            "author_id": author_id,
            "content": content
        }
        print(cls._headers())
        r = requests.post(url, json=payload, headers=cls._headers())
        return r.json()

    # @classmethod
    # def get_feed(cls):
    #     url = f"{cls.BASE}/posts/feed/"
    #     r = requests.get(url, headers=cls._headers())
        
    #     return r.json()

    @classmethod
    def get_feed(cls):
        url = f"{cls.BASE}/posts/feed/"
        r = requests.get(url, headers=cls._headers())

        clean = r.text.strip().replace("\ufeff", "")
        print(clean)
        return json.loads(clean)
