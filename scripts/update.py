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
        self.translation_dir = Path(translation_dir)
        self.download_dir = Path(download_dir)
        self.client = httpx.Client()
        self.ablist = None

    def run(self):
        """전체 파이프라인 실행"""
        print("=== [1/4] 몬무스 TD 데이터 수집 시작 ===")
        try:
            # 1. 버전 및 에셋 리스트 가져오기
            self.fetch_version_and_list()
            # 2. 해시 파일 중 시나리오 데이터 탐색 및 수집
            self.update_novels()
            print("=== 데이터 수집 및 복호화 완료 ===")
        except Exception as e:
            print(f"  [Critical] 작업 중 오류 발생: {e}")

    def fetch_version_and_list(self):
        """최신 클라이언트 및 에셋 버전 정보 획득"""
        try:
            # 1. 앱 버전(cvr) 확인
            resp = self.client.get(self.APP_INFO_URL)
            resp.raise_for_status()
            cvr = resp.json()["free_appinfo"]["app_version_name"]
            print(f"  > Client Version (cvr): {cvr}")

            # 2. 에셋 번들 버전 확인
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
            print(f"  [Error] 버전 정보 획득 실패: {e}")
            raise

    def update_novels(self):
        """해시 파일들을 전수 조사하여 시나리오 데이터 추출"""
        if not self.ablist:
            return

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        # 중복 방지를 위한 체크
        novels_dir = self.translation_dir / 'novels'
        novels_dir.mkdir(parents=True, exist_ok=True)
        existed_novels = os.listdir(novels_dir)

        print(f"  > 총 {len(self.ablist['data'])}개의 에셋을 정밀 분석 중 (시간이 다소 소요됩니다)...")
        
        count = 0
        for asset in self.ablist["data"]:
            asset_path = asset["path"]
            
            # 용량이 너무 크거나 작은 파일은 시나리오가 아닐 확률이 높으므로 필터링 (선택 사항)
            # if not (1024 < int(asset['size']) < 500000): continue 

            file_url = f"{base_url}/{asset['hash']}{asset_path}"
            
            try:
                # 1. 파일 다운로드
                resp = self.client.get(file_url)
                if resp.status_code != 200: continue
                
                # 2. 몬무스 전용 XOR 복호화
                decrypted_data = decrypt_monmusu(resp.content)
                
                # 3. 내부 텍스트 확인 (Utage 시나리오 여부 판단)
                # Utage 스크립트 특유의 키워드가 있는지 확인합니다.
                decoded_sample = decrypted_data.decode('utf-8', errors='ignore')[:500]
                if any(k in decoded_sample for k in ["message", "Message", "title", "Title", "adv", "Scenario"]):
                    
                    # 유니티 번들인 경우와 텍스트 파일인 경우를 구분하여 처리
                    if decrypted_data.startswith(b"Unity"):
                        result = parse_bundle(decrypted_data)
                        if result:
                            script_name, script_text = result
                            script_messages = parse_script(script_text)
                        else: continue
                    else:
                        # 텍스트 데이터인 경우 바로 파싱
                        script_name = Path(asset_path).stem
                        script_messages = parse_script(decoded_sample)

                    if script_messages:
                        # gt_input에 저장
                        write_json(self.download_dir / f'{script_name}.json', script_messages)
                        count += 1
                        if count % 10 == 0:
                            print(f"    [Found] {count}번째 시나리오 확보: {script_name}")

            except Exception:
                continue
        
        print(f"  > 탐색 완료: 총 {count}개의 시나리오 파일을 찾았습니다.")

if __name__ == '__main__':
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()