import os
import re
import httpx
from pathlib import Path
from crypto import decrypt_monmusu
from parse import parse_bundle, parse_script
from utils import write_json, read_json

class Updater:
    APP_INFO_URL = "https://api.store.games.dmm.com/freeapp/688044"
    VERSION_API = "https://gapi.game-monmusu-td.net/api/asset_bundle/version"
    ASSET_BASE_URL = "https://assets.game-monmusu-td.net/assetbundles"

    def __init__(self, translation_dir: str | Path, download_dir: str | Path):
        self.translation_dir = Path(translation_dir)
        self.download_dir = Path(download_dir)
        self.client = httpx.Client()
        self.ablist = None

    def run(self):
        print("=== [1/4] 몬무스 TD 데이터 수집 및 정밀 분석 시작 ===")
        try:
            self.fetch_version_and_list()
            self.update_novels()
            print("\n=== 데이터 수집 및 복호화 완료 ===")
        except Exception as e:
            print(f"\n[Critical] 작업 중 오류 발생: {e}")

    def fetch_version_and_list(self):
        """최신 클라이언트 및 에셋 버전 정보 획득"""
        resp = self.client.get(self.APP_INFO_URL)
        cvr = resp.json()["free_appinfo"]["app_version_name"]
        
        payload = {"cvr": cvr, "provider": "dmm"}
        resp = self.client.post(self.VERSION_API, json=payload)
        bundle_ver = f"ver_{resp.json()['data']['version']}"
        
        ablist_url = f"{self.ASSET_BASE_URL}/{bundle_ver}/webgl_r18/ablist.json"
        self.ablist = self.client.get(ablist_url).json()
        print(f"  > 에셋 리스트 확보 완료 (Base Version: {self.ablist['baseVersion']})")

    def get_target_scenarios(self):
        """masterdata 폴더의 모든 시나리오 정보를 통합"""
        target_map = {}
        master_path = self.translation_dir / "masterdata" / "data"
        
        # 폴더 내 모든 story_data_*.json 탐색
        for file in master_path.glob("story_data_*.json"):
            data = read_json(file)
            for item in data.get('table', []):
                s_name = item.get('scenario_name')
                if s_name:
                    target_map[s_name] = item.get('title', s_name)
        return target_map

    def update_novels(self):
        """데이터의 실체를 파악하기 위한 샘플 덤프 로직"""
        if not self.ablist: return

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        dump_dir = Path("debug_dump")
        dump_dir.mkdir(parents=True, exist_ok=True)

        print(f"=== [탐지] 데이터 실체 파악을 위한 샘플 덤프 시작 ===")
        
        count = 0
        for asset in self.ablist["data"]:
            file_size = int(asset.get('size', 0))
            # 시나리오 파일일 확률이 높은 10KB ~ 100KB 사이만 타겟팅
            if 10000 < file_size < 100000:
                file_url = f"{base_url}/{asset['hash']}{asset['path']}"
                
                try:
                    resp = self.client.get(file_url)
                    # 우리가 알고 있는 몬무스 키로 복호화 수행
                    decrypted = decrypt_monmusu(resp.content)
                    
                    # 확장자를 .bin으로 저장하여 원본 상태 보존
                    dump_path = dump_dir / f"{asset['path']}.bin"
                    with open(dump_path, "wb") as f:
                        f.write(decrypted)
                    
                    count += 1
                    print(f"    [Dumped] {asset['path']} (Size: {file_size} bytes)")
                    
                    if count >= 20: break # 샘플 20개만 확보
                except:
                    continue

        print(f"=== 덤프 완료: 'debug_dump' 폴더를 확인해 주세요 ===")

if __name__ == '__main__':
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()