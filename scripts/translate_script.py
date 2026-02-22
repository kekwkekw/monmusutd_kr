import os
import json
import time
from openai import OpenAI

# ================= 설정 구간 =================
INPUT_FOLDER = 'GalTransl/sampleProject/gt_input'
OUTPUT_FOLDER = 'GalTransl/sampleProject/transl_cache'

# LM Studio 로컬 서버 주소 및 포트 (기본값: 1234)
LOCAL_API_BASE = "http://localhost:1234/v1"
LOCAL_API_KEY = "lm-studio" # LM Studio는 키를 검사하지 않지만 비워둘 수 없습니다.

client = OpenAI(base_url=LOCAL_API_BASE, api_key=LOCAL_API_KEY)

# 번역 품질을 결정하는 시스템 프롬프트 (입맛에 맞게 수정하세요)
SYSTEM_PROMPT = """당신은 일본 미소녀 게임(Galgame)을 한국어로 번역하는 전문 번역가입니다.
다음 규칙을 엄격하게 준수하세요:
1. 문맥에 맞는 자연스러운 한국어로 번역하세요.
2. <br> 같은 HTML 태그나 특수 기호(「」, 『』, … 등)는 원본 그대로 유지해야 합니다.
3. 부가적인 설명이나 인사말 없이, 오직 번역된 텍스트 결과만 출력하세요.
"""

# 로컬 환경이므로 GitHub Actions의 6시간 제한은 없지만, 
# 안전한 저장을 위해 1000개 단위 등 원하는 시간/개수로 제한을 둘 수 있습니다.
SAVE_INTERVAL = 50 
# ===========================================

def translate_text(text):
    """
    LM Studio를 통해 텍스트를 번역합니다.
    """
    if not text:
        return ""
    
    # 의미 없는 기호나 점만 있는 경우 (번역할 필요가 없는 경우)
    # AI가 헛소리를 만들어내는 것(Hallucination)을 방지하기 위해 원문 통과
    if text.strip() in ["「…………」", "…………", "……", "「……」"]:
        return text

    try:
        response = client.chat.completions.create(
            model="local-model", # LM Studio에 로드된 현재 모델을 자동 사용합니다.
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.3, # 창의성 조절 (직역 위주면 낮게, 의역 위주면 높게)
            max_tokens=1000
        )
        translated = response.choices[0].message.content.strip()
        
        # 간혹 AI가 응답을 안 주거나 이상하게 줬을 경우 방어 코드
        if not translated:
            return text
            
        return translated

    except Exception as e:
        print(f"    [Warning] 로컬 AI 번역 실패: {str(text)[:10]}... -> {e}")
        return text # 에러 시 원문 유지

def run_local_translation():
    print(f"=== 로컬 LM Studio 번역 파이프라인 시작 ===")
    
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    if not os.path.exists(INPUT_FOLDER):
        print(f"알림: {INPUT_FOLDER} 폴더가 없습니다. 원본 데이터 다운로드를 먼저 진행하세요.")
        return

    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.json')]
    total_files = len(files)
    
    if total_files == 0:
        print("알림: 번역할 파일이 없습니다.")
        return

    processed_files = set(os.listdir(OUTPUT_FOLDER))
    processed_count = 0
    skipped_count = 0

    for idx, filename in enumerate(files):
        if filename in processed_files:
            skipped_count += 1
            if skipped_count % 100 == 0:
                print(f"[{idx+1}/{total_files}] 이미 완료됨 (Skipping...)")
            continue

        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, filename)
        
        print(f"[{idx+1}/{total_files}] 로컬 번역 중: {filename}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            translated_data = []
            
            for item in data:
                original_text = item.get('message', '')
                if not original_text:
                    continue
                
                # LM Studio로 번역 요청
                translated_text = translate_text(original_text)
                
                translated_data.append({
                    "pre_jp": original_text,
                    "post_zh_preview": translated_text,
                    "index": 0,
                    "pre_zh": "",
                    "tokens": 0
                })
            
            # 파일 1개 단위로 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=4)
            
            processed_count += 1
                
        except Exception as e:
            print(f"  [Critical] 파일 처리 중 치명적 오류: {filename} - {e}")

    print(f"\n=== 로컬 번역 작업 완료 ===")
    print(f"완료: {processed_count}, 건너뜀: {skipped_count}, 남음: {total_files - (processed_count + skipped_count)}")

if __name__ == "__main__":
    run_local_translation()
