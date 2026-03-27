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
        if not self.ablist: return

        # 1. 시나리오로 의심되는 파일 경로 20개만 출력해보기 
        print("\n  [탐색] 시나리오 후보 파일 경로 샘플:")
        sample_count = 0
        for asset in self.ablist["data"]:
            path = asset["path"].lower()
            # 보통 시나리오는 .bytes, .csv, .json 또는 특정 폴더에 들어있습니다. 
            if any(k in path for k in [".bytes", ".csv", "story", "res"]):
                print(f"    - {asset['path']}")
                sample_count += 1
            if sample_count >= 20: break 
            
        # 2. 전체 경로에서 특정 단어가 들어간 파일이 몇 개인지 확인 
        keywords = ["scenario", "adv", "event", "story", "talk", "novel"]
        for k in keywords:
            found = sum(1 for a in self.ablist["data"] if k in a["path"].lower())
            print(f"  > 키워드 '{k}' 검색 결과: {found}개")

if __name__ == '__main__':
    # 독립 실행 시 기본 경로 설정
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()