@echo off
chcp 65001 > nul

echo =========================================
echo 몬무스 TD (montrans) AI 번역 파이프라인
echo =========================================

echo.
echo [1/4] 몬무스 서버에서 데이터 수집 중...
python scripts/run.py 

echo.
echo [2/4] LM Studio (MonTransl) 번역 시작...
python scripts/translate_script.py

echo.
echo [3/4] 번역 데이터 병합 및 ko_KR.json 생성...
python scripts/merge.py

echo.
echo [4/4] montrans 저장소 업데이트...
git add .
git commit -m "Monmusu TD Auto-Update"
git push

echo.
echo =========================================
echo 작업 완료! montrans 폴더의 결과를 확인하세요.
echo =========================================
pause