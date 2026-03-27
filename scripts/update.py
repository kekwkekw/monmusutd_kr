import httpx
from pathlib import Path
from crypto import decrypt_monmusu
from utils import write_json

class Updater:
    BASE_URL = "https://assets.game-monmusu-td.net/assetbundles" #
    
    def __init__(self, translation_dir: str | Path, download_dir: str | Path):
        self.translation_dir = Path(translation_dir)
        self.download_dir = Path(download_dir)
        self.client = httpx.Client()

    def run(self):
        # 1. 최신 버전 및 에셋 목록 확보
        cvr = self.client.get(self.APP_INFO_URL).json()["free_appinfo"]["app_version_name"]
        res = self.client.post(self.VERSION_API, json={"cvr": cvr, "provider": "dmm"}).json()
        bundle_ver = f"ver_{res['data']['version']}"
        
        ablist_url = f"https://assets.game-monmusu-td.net/assetbundles/{bundle_ver}/webgl_r18/ablist.json"
        ab = self.client.get(ablist_url).json()
        
        # 2. 시나리오 파일 다운로드 및 복호화
        base_url = f"https://assets.game-monmusu-td.net/assetbundles/ver_{ab['baseVersion']}/webgl_r18"
        for asset in ab["data"]:
            if "scenario" in asset["path"]: # Utage 시나리오 파일 식별
                file_url = f"{base_url}/{asset['hash']}{asset['path']}"
                content = self.client.get(file_url).content
                
                # 복호화 후 유니티 에셋 파싱 로직으로 전달
                decrypted = decrypt_monmusu(content)
                # (이후 parse.py의 로직을 호출하여 JSON으로 저장)
                print(f"Downloaded & Decrypted: {asset['path']}")