@echo off
:: 한글 깨짐 방지
chcp 65001 > nul

echo =========================================
echo 걸크리 로컬 AI 번역 파이프라인 시작
echo =========================================

echo.
echo [0/4] 깃허브 서버와 동기화 중 (충돌 방지)...
git pull origin main

echo.
echo [1/4] 게임 서버에서 원본 데이터 긁어오는 중...
python scripts/run.py dummy dummy dummy

echo.
echo [2/4] LM Studio 로컬 AI 번역 시작...
python scripts/translate_script.py

echo.
echo [3/4] 번역된 파일 병합 중...
python scripts/merge.py

echo.
echo [4/4] GitHub로 결과물 업로드 중...
git add .
git commit -m "Auto-update local AI translation"
git push

echo.
echo =========================================
echo 모든 작업이 완료되었습니다! 게임을 켜서 확인해 보세요.
echo =========================================
pause