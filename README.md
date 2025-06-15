<<<<<<< HEAD
# EduTube Navigator

YouTube 학습 컨텐츠를 빠르게 찾을 수 있는 웹 플랫폼입니다.

## 주요 기능

- 📚 교육용 YouTube 콘텐츠 검색 및 추천
- 🎯 카테고리별 분류 (프로그래밍, 언어학습, 취미)  
- 📱 Video/Shorts 탭 구분
- 🔍 고급 필터링 (시간, 난이도, 정렬)
- ❤️ 북마크 기능 (로컬 저장)
- 🌐 한국어/영어 지원

## 배포 방법

### Railway 배포

1. Railway 계정 생성: https://railway.app
2. GitHub에 코드 업로드
3. Railway에서 "New Project" → "Deploy from GitHub repo" 선택
4. 환경변수 설정:
   - `YOUTUBE_API_KEY`: YouTube Data API v3 키

### 환경변수 설정

- `YOUTUBE_API_KEY`: YouTube Data API v3 키 (필수)
- `PORT`: 서버 포트 (자동 설정됨)

## 로컬 실행

```bash
# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
export YOUTUBE_API_KEY="your_youtube_api_key"

# 서버 실행  
python app.py
```

## 기술 스택

- Backend: Flask, Python
- Frontend: Bootstrap 5, JavaScript
- API: YouTube Data API v3
- 배포: Railway, Gunicorn

## 라이선스

MIT License 
=======
# 🎯 EduTube Navigator

YouTube 학습 콘텐츠 큐레이션 플랫폼

## 🚀 배포 정보
- **최초 배포**: 2025년 6월 9일
- **최근 업데이트**: 2025년 6월 9일 21:30
- **배포 URL**: https://edutube-navigator.vercel.app

## 📊 주요 기능
- YouTube 교육 콘텐츠 검색 & 필터링
- 카테고리별 큐레이션 (프로그래밍, 언어학습, 취미 등)
- AdSense 광고 연동
- 반응형 디자인
- 북마크 기능

## 🎨 기술 스택
- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **API**: YouTube Data API v3
- **배포**: Vercel
- **광고**: Google AdSense

## 📞 문의
- **광고 문의**: miriv10@naver.com
- **기술 문의**: GitHub Issues

---
*Made with ❤️ for better learning experiences* 
>>>>>>> ffee8f7 (0615 배포)
