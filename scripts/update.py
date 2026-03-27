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
        """해시 파일의 내용물을 직접 열어 scenario_name을 역추적"""
        target_scenarios = self.get_target_scenarios()
        print(f"  > 추적 대상 시나리오: {len(target_scenarios)}개")

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        novels_dir = self.translation_dir / 'novels'
        novels_dir.mkdir(parents=True, exist_ok=True)
        existed_ids = os.listdir(novels_dir)

        count = 0
        total_assets = self.ablist["data"]
        
        # 속도 향상을 위해 타겟 이름을 셋(set)으로 변환
        target_names = set(target_scenarios.keys())

        for idx, asset in enumerate(total_assets):
            # 시나리오 파일은 보통 5KB ~ 500KB 사이
            file_size = int(asset.get('size', 0))
            if not (1000 < file_size < 1000000): continue

            if idx % 1000 == 0:
                print(f"    [분석 중] {idx}/{len(total_assets)}... (찾은 시나리오: {count})")

            file_url = f"{base_url}/{asset['hash']}{asset['path']}"
            
            try:
                resp = self.client.get(file_url)
                decrypted = decrypt_monmusu(resp.content)
                
                # 텍스트로 디코딩 (Utage는 보통 UTF-8 사용)
                content_sample = decrypted.decode('utf-8', errors='ignore')
                
                # 핵심: 복호화된 내용물 안에 타겟 시나리오 이름이 있는지 확인
                # Utage 파일은 상단에 자신의 scenario_name을 기록하는 경우가 많음
                matched_name = None
                
                # Utage 특유의 헤더(#Tag, Command)가 있는지 먼저 확인하여 속도 최적화
                if "#Tag" in content_sample or "Command" in content_sample:
                    for name in target_names:
                        if name in content_sample:
                            matched_name = name
                            break
                
                if matched_name:
                    if matched_name in existed_ids: continue
                    
                    # 찾은 경우 parse_script로 대사 추출
                    script_messages = parse_script(content_sample)
                    if script_messages:
                        write_json(self.download_dir / f'{matched_name}.json', script_messages)
                        count += 1
                        print(f"      [매칭 성공!] {matched_name} -> {target_scenarios[matched_name]}")
            except:
                continue

if __name__ == '__main__':
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()