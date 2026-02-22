import os
import json
import time
from deep_translator import GoogleTranslator

# ================= 설정 구간 =================
INPUT_FOLDER = 'GalTransl/sampleProject/gt_input'
OUTPUT_FOLDER = 'GalTransl/sampleProject/transl_cache'

SOURCE_LANG = 'ja'
TARGET_LANG = 'ko'
DELAY = 0.2

# [설정] 5시간 30분(19800초)이 지나면 작업을 안전하게 중단하고 저장
# (GitHub Actions 6시간 제한 대비)
TIME_LIMIT_SECONDS = 5.5 * 60 * 60 
# ===========================================

def translate_text(text, translator):
    """
    텍스트 번역 함수 (예외 처리 강화됨)
    """
    if not text:
        return ""
    
    try:
        # 1. <br> 태그 임시 보호
        text_to_translate = text.replace("<br>", "\n")
        
        # 2. 번역 요청
        translated = translator.translate(text_to_translate)
        
        # [수정된 부분] 번역 결과가 None인 경우 (기호만 있는 경우 등) 원문 반환
        if translated is None:
            return text

        # 3. <br> 태그 복구 및 반환
        return translated.replace("\n", "<br>")

    except Exception as e:
        # 번역 실패 시 에러 로그 출력 후 원문 반환
        print(f"    [Warning] 번역 건너뜀: {str(text)[:10]}... -> {e}")
        return text

def run_translation():
    start_time = time.time() # 시작 시간 기록
    
    # 폴더 생성
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # 입력 폴더 확인
    if not os.path.exists(INPUT_FOLDER):
        print(f"알림: {INPUT_FOLDER} 폴더가 없습니다.")
        return

    # JSON 파일 목록 가져오기
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.json')]
    total_files = len(files)
    
    if total_files == 0:
        print("알림: 번역할 파일이 없습니다.")
        return

    print(f"=== 번역 시작: 총 {total_files}개 파일 (제한 시간: 5.5시간) ===")
    
    translator = GoogleTranslator(source=SOURCE_LANG, target=TARGET_LANG)
    
    # 이미 작업된 파일 확인 (중복 방지)
    processed_files = set(os.listdir(OUTPUT_FOLDER))

    processed_count = 0
    skipped_count = 0

    for idx, filename in enumerate(files):
        # [시간 체크] 제한 시간이 넘었는지 확인
        elapsed_time = time.time() - start_time
        if elapsed_time > TIME_LIMIT_SECONDS:
            print(f"\n[시간 제한 도달] {elapsed_time/3600:.1f}시간 경과. 작업을 안전하게 종료합니다.")
            print("진행된 내용은 저장되며, 남은 파일은 다음 실행 때 이어집니다.")
            break

        # 이미 번역된 파일은 건너뛰기
        if filename in processed_files:
            skipped_count += 1
            # 로그가 너무 많으면 보기 힘드므로 100개마다 한 번씩만 출력
            if skipped_count % 100 == 0:
                print(f"[{idx+1}/{total_files}] 이미 완료됨 (Skipping...)")
            continue

        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, filename)
        
        print(f"[{idx+1}/{total_files}] 번역 중: {filename}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            translated_data = []
            
            for item in data:
                original_text = item.get('message', '')
                
                # 텍스트가 없으면 건너뜀
                if not original_text:
                    continue
                
                # 번역 수행 (위에서 만든 함수 사용)
                translated_text = translate_text(original_text, translator)
                
                # 결과 데이터 구조 만들기
                translated_data.append({
                    "pre_jp": original_text,
                    "post_zh_preview": translated_text,
                    "index": 0,
                    "pre_zh": "",
                    "tokens": 0
                })
                
                # API 차단 방지 딜레이
                time.sleep(DELAY)
            
            # 파일 저장 (한 파일 끝날 때마다 저장)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=4)
            
            processed_count += 1
                
        except Exception as e:
            print(f"  [Critical] 파일 처리 중 치명적 오류: {filename} - {e}")

    print(f"\n=== 작업 종료 ===")
    print(f"완료: {processed_count}, 건너뜀: {skipped_count}, 남음: {total_files - (processed_count + skipped_count)}")

if __name__ == "__main__":
    run_translation()
