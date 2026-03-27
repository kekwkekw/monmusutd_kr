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
            return

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        # 결과물을 저장할 폴더 생성
        novels_dir = self.translation_dir / 'novels'
        novels_dir.mkdir(parents=True, exist_ok=True)
        existed_novels = os.listdir(novels_dir)

        print("  > 시나리오 파일 확인 및 다운로드 중...")
        
        for asset in self.ablist["data"]:
            asset_path = asset["path"]
            
            # Utage 시나리오 파일 식별 (경로에 scenario 또는 adv 포함 여부)
            if "scenario" in asset_path.lower():
                # 파일명에서 숫자 ID 추출
                match = re.search(r'\d+', Path(asset_path).stem)
                novel_id = match.group() if match else Path(asset_path).stem
                
                # 이미 번역 폴더가 존재하면 스킵
                if novel_id in existed_novels:
                    continue

                print(f"    - Downloading: {asset_path}")
                file_url = f"{base_url}/{asset['hash']}{asset_path}"
                
                try:
                    resp = self.client.get(file_url)
                    resp.raise_for_status()
                    
                    # 1. 몬무스 전용 XOR 복호화 적용
                    decrypted_data = decrypt_monmusu(resp.content)
                    
                    # 2. 유니티 에셋 파싱 (UnityPy 활용)
                    # parse_bundle은 유니티 파일 내 TextAsset을 추출함
                    result = parse_bundle(decrypted_data)
                    if not result:
                        continue
                        
                    script_name, script_text = result
                    
                    # 3. 텍스트 스크립트에서 대사 메시지 추출
                    # 주의: Utage 스크립트 형식에 맞춰 parse_script 수정이 필요할 수 있음
                    script_messages = parse_script(script_text)

                    # 4. MonTransl/sampleProject/gt_input 폴더에 JSON 저장
                    write_json(self.download_dir / f'{script_name}.json', script_messages)
                    
                except Exception as e:
                    print(f"    [Warning] {asset_path} 처리 실패: {e}")

if __name__ == '__main__':
    # 독립 실행 시 기본 경로 설정
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()