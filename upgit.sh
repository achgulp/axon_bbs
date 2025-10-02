INCDATE=`date +%Y%m%d%H%M%S`
git status
git add -A
git status
git commit -m "Update GEMINI_${INCDATE}"
git push origin main
