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
        """마스터 데이터를 기반으로 해시 파일 정밀 수집"""
        target_scenarios = self.get_target_scenarios()
        print(f"  > 추적 대상 시나리오: {len(target_scenarios)}개")

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        # novels 폴더에서 이미 받은 ID 체크
        novels_dir = self.translation_dir / 'novels'
        novels_dir.mkdir(parents=True, exist_ok=True)
        existed_ids = os.listdir(novels_dir)

        count = 0
        total_assets = self.ablist["data"]
        
        for idx, asset in enumerate(total_assets):
            # 용량 필터링 (2KB ~ 1MB 사이의 텍스트 에셋만 타겟팅하여 속도 향상)
            file_size = int(asset.get('size', 0))
            if not (2048 < file_size < 1048576): continue

            if idx % 1000 == 0:
                print(f"    [진행 중] {idx}/{len(total_assets)} 에셋 분석 중... (찾은 파일: {count})")

            file_url = f"{base_url}/{asset['hash']}{asset['path']}"
            
            try:
                resp = self.client.get(file_url)
                if resp.status_code != 200: continue
                
                # 몬무스 복호화
                decrypted = decrypt_monmusu(resp.content)
                
                # 유니티 번들인 경우에만 파싱 진행
                if decrypted.startswith(b"Unity"):
                    result = parse_bundle(decrypted)
                    if result:
                        script_name, script_text = result
                        # 마스터 데이터 리스트에 존재하는 이름인지 확인!
                        if script_name in target_scenarios:
                            if script_name in existed_ids: continue
                            
                            script_messages = parse_script(script_text)
                            write_json(self.download_dir / f'{script_name}.json', script_messages)
                            count += 1
                            print(f"      [매칭 성공!] {script_name} ({target_scenarios[script_name]})")
            except:
                continue

if __name__ == '__main__':
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()