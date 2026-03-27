import os
import re
import httpx
import UnityPy
from pathlib import Path

# 기존 프로젝트 파일들에서 함수 임포트
from crypto import decrypt_monmusu
from parse import parse_bundle, parse_script
from utils import write_json, read_json

class Updater:
    # 몬무스 TD 전용 엔드포인트 설정
    APP_INFO_URL = "https://api.store.games.dmm.com/freeapp/688044"
    VERSION_API = "https://gapi.game-monmusu-td.net/api/asset_bundle/version"
    ASSET_BASE_URL = "https://assets.game-monmusu-td.net/assetbundles"

    def __init__(self, translation_dir: str | Path, download_dir: str | Path):
        """
        translation_dir: montrans 루트 폴더
        download_dir: MonTransl/sampleProject/gt_input (원본 JSON 저장소)
        """
        self.translation_dir = Path(translation_dir)
        self.download_dir = Path(download_dir)
        self.client = httpx.Client()
        self.ablist = None

    def run(self):
        """파이프라인 실행 메인 로직"""
        print("=== [1/4] 몬무스 TD 데이터 수집 시작 ===")
        try:
            self.fetch_version_and_list()
            self.update_novels()
            print("=== 데이터 수집 및 복호화 완료 ===")
        except Exception as e:
            print(f"  [Critical] 작업 중 오류 발생: {e}")

    def fetch_version_and_list(self):
        """최신 클라이언트 및 에셋 버전 정보 획득"""
        try:
            # 1. DMM API를 통해 앱 버전(cvr) 확인
            resp = self.client.get(self.APP_INFO_URL)
            resp.raise_for_status()
            cvr = resp.json()["free_appinfo"]["app_version_name"]
            print(f"  > Client Version (cvr): {cvr}")

            # 2. 게임 API를 통해 에셋 번들 버전 확인
            payload = {"cvr": cvr, "provider": "dmm"}
            resp = self.client.post(self.VERSION_API, json=payload)
            resp.raise_for_status()
            ver = resp.json()["data"]["version"]
            bundle_ver = f"ver_{ver}"
            print(f"  > Bundle Version: {bundle_ver}")

            # 3. 전체 에셋 목록(ablist.json) 다운로드
            ablist_url = f"{self.ASSET_BASE_URL}/{bundle_ver}/webgl_r18/ablist.json"
            self.ablist = self.client.get(ablist_url).json()
            print(f"  > Fetched ablist.json (Base Version: {self.ablist['baseVersion']})")
        
        except Exception as e:
            print(f"  [Error] 버전 정보를 가져오는데 실패했습니다: {e}")
            raise

    def update_novels(self):
        """시나리오 에셋 다운로드 및 텍스트 추출"""
        if not self.ablist:
            print("  [Error] 에셋 리스트가 없습니다.")
            return

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        novels_dir = self.translation_dir / 'novels'
        novels_dir.mkdir(parents=True, exist_ok=True)
        existed_novels = os.listdir(novels_dir)

        print(f"  > 총 {len(self.ablist['data'])}개의 에셋 스캔 중...")
        
        count = 0
        for asset in self.ablist["data"]:
            asset_path = asset["path"]
            
            # 필터링 조건: 몬무스에 맞게 scenario, adv, event 등을 포함
            is_scenario = any(k in asset_path.lower() for k in ["scenario", "adv", "event"])
            
            if is_scenario:
                # 파일명에서 ID 추출
                match = re.search(r'\d+', Path(asset_path).stem)
                novel_id = match.group() if match else Path(asset_path).stem
                
                # 중복 체크
                if novel_id in existed_novels:
                    continue

                print(f"    [Found] 다운로드 시작: {asset_path}") # 실제 다운로드 시 출력
                file_url = f"{base_url}/{asset['hash']}{asset_path}"
                
                try:
                    resp = self.client.get(file_url)
                    resp.raise_for_status()
                    
                    decrypted_data = decrypt_monmusu(resp.content)
                    result = parse_bundle(decrypted_data)
                    
                    if result:
                        script_name, script_text = result
                        script_messages = parse_script(script_text)
                        write_json(self.download_dir / f'{script_name}.json', script_messages)
                        count += 1
                except Exception as e:
                    print(f"    [Warning] {asset_path} 처리 오류: {e}")
        
        print(f"  > 총 {count}개의 시나리오 파일이 gt_input에 저장되었습니다."))

if __name__ == '__main__':
    # 독립 실행 시 기본 경로 설정
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()