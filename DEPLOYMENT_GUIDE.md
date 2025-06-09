# 🚀 EduTube Navigator 배포 가이드

## 1. 빠른 배포 옵션들

### 🟢 추천: Vercel (무료)
**장점**: 매우 쉬움, GitHub 연동, 자동 배포
```bash
# 1. GitHub에 코드 업로드
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/edutube-navigator.git
git push -u origin main

# 2. Vercel.com 접속 → GitHub 연동 → 자동 배포
```

### 🟡 Heroku (무료/유료)
**장점**: Flask 지원 우수, 데이터베이스 연동 쉬움
```bash
# 1. Heroku CLI 설치
# 2. requirements.txt 생성 필요
pip freeze > requirements.txt

# 3. Procfile 생성
echo "web: python app.py" > Procfile

# 4. 배포
heroku create edutube-navigator
git push heroku main
```

### 🟠 DigitalOcean App Platform
**장점**: 성능 좋음, 한국어 지원
- GitHub 연동으로 자동 배포
- 월 $5부터 시작

## 2. 배포 전 체크리스트

### ✅ 필수 설정
- [ ] YouTube API 키 환경변수 설정
- [ ] Flask SECRET_KEY 설정  
- [ ] AdSense Publisher ID 교체
- [ ] Google Analytics ID 교체
- [ ] 포트 설정 (production용으로 변경)

### ✅ 파일 정리
- [ ] `.env` 파일 생성 (API 키 보안)
- [ ] `requirements.txt` 생성
- [ ] `README.md` 업데이트
- [ ] 불필요한 파일 제거

## 3. 환경변수 설정

### `.env` 파일 생성
```bash
# YouTube API
YOUTUBE_API_KEY=AIzaSyBn_AhmUqK4Gn2Yq-gLEv1vKKra_ahcHps

# Flask 설정
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# 광고 설정
ADSENSE_PUBLISHER_ID=ca-pub-YOUR_PUBLISHER_ID
GA_MEASUREMENT_ID=GA_MEASUREMENT_ID
```

### `app.py` 수정 필요
```python
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
```

## 4. 단계별 배포 과정

### 1단계: 로컬 테스트
```bash
python app.py
# http://127.0.0.1:5005 접속해서 정상 작동 확인
```

### 2단계: GitHub 업로드
```bash
git init
git add .
git commit -m "Ready for deployment"
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### 3단계: 플랫폼별 배포

#### Vercel 배포
1. vercel.com 접속
2. GitHub 계정 연동
3. Repository 선택
4. 환경변수 설정
5. Deploy 클릭

#### Heroku 배포
```bash
heroku create your-app-name
heroku config:set YOUTUBE_API_KEY=your-key
heroku config:set SECRET_KEY=your-secret
git push heroku main
```

## 5. 배포 후 해야할 일

### 🎯 즉시 설정
- [ ] 도메인 연결 (선택사항)
- [ ] SSL 인증서 확인
- [ ] Google Search Console 등록
- [ ] Google Analytics 설정

### 📈 마케팅 시작
- [ ] 소셜미디어 계정 생성
- [ ] 교육 커뮤니티에 홍보
- [ ] SEO 최적화 시작
- [ ] 광고 문의 연락처 확인

## 6. 지속적인 업데이트 방법

### 코드 수정 후 배포
```bash
# 수정 작업 후
git add .
git commit -m "Feature: 새로운 기능 추가"
git push origin main

# Vercel/Netlify는 자동 배포
# Heroku는 git push heroku main
```

### 실시간 모니터링
- Google Analytics 대시보드 확인
- AdSense 수익 모니터링  
- 사용자 피드백 수집
- 오류 로그 확인

## 7. 수익화 전략 타임라인

### 배포 1주차
- [ ] SEO 기본 설정 완료
- [ ] 소셜미디어 홍보 시작
- [ ] 친구/지인에게 공유

### 배포 1개월차  
- [ ] 월 1,000 방문자 목표
- [ ] AdSense 신청
- [ ] 사용자 피드백 반영

### 배포 3개월차
- [ ] 월 10,000 방문자 목표
- [ ] 첫 광고 수익 발생
- [ ] 프리미엄 기능 추가

## 8. 문제해결

### 자주 발생하는 오류
- **API 키 오류**: 환경변수 설정 확인
- **빌드 실패**: requirements.txt 확인  
- **CORS 오류**: Flask-CORS 설정
- **속도 저하**: 캐싱 구현 필요

### 지원 받기
- GitHub Issues 활용
- 개발자 커뮤니티 질문
- 플랫폼별 공식 문서 참조

---

**🎉 배포 성공 후 miriv10@naver.com으로 사이트 URL 공유해주세요!** 