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

    def update_novels(self):
        """파일명이 해시이므로 내부 데이터를 확인하여 수집"""
        if not self.ablist: return

        base_ver = self.ablist["baseVersion"]
        base_url = f"{self.ASSET_BASE_URL}/ver_{base_ver}/webgl_r18"
        
        print("  > 해시 파일 분석 및 테이블 데이터 수집 중...")
        
        count = 0
        for asset in self.ablist["data"]:
            asset_path = asset["path"] # 예: 0006a5...bytes
            
            # 1. 일단 모든 .bytes 파일을 대상으로 시도 (용량이 작은 것부터 확인 권장)
            file_url = f"{base_url}/{asset['hash']}{asset_path}"
            
            try:
                # 팁: 우선 헤더만 확인하기 위해 5바이트만 먼저 받아볼 수도 있음
                resp = self.client.get(file_url)
                resp.raise_for_status()
                
                # 유니티 번들 파일이 아니면 (몬무스 암호화 파일일 가능성 높음)
                if not resp.content.startswith(b"Unity"):
                    # 2. 몬무스 전용 복호화 시도
                    decrypted = decrypt_monmusu(resp.content)
                    
                    # 3. 복호화된 데이터가 Utage 시나리오(CSV/TSV/JSON)인지 확인
                    # 몬무스는 테이블 데이터가 많으므로, 특정 단어가 포함된 데이터만 선별
                    decoded_text = decrypted.decode('utf-8', errors='ignore')
                    if any(k in decoded_text for k in ["message", "Message", "title", "Title"]):
                        print(f"    [Found Scenario Table] {asset_path}")
                        write_json(self.download_dir / f"{asset_path}.json", {"content": decoded_text})
                        count += 1
                        
            except Exception:
                continue
        
        print(f"  > 총 {count}개의 데이터 테이블을 확보했습니다.")

if __name__ == '__main__':
    # 독립 실행 시 기본 경로 설정
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()