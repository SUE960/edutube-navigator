# 🎯 AdSense 연동 가이드

## 1. AdSense 승인 단계별 설정

### 1단계: Google AdSense 계정 생성
1. [Google AdSense](https://www.google.com/adsense/) 접속
2. 계정 생성 및 사이트 등록
3. ads.txt 파일 업로드 (서버 루트 디렉토리)

### 2단계: Publisher ID 교체
현재 코드에서 다음 부분들을 본인의 실제 ID로 교체:

```html
<!-- 모든 YOUR_PUBLISHER_ID를 실제 pub-id로 교체 -->
ca-pub-YOUR_PUBLISHER_ID → ca-pub-1234567890123456

<!-- 광고 슬롯 ID도 실제 슬롯 ID로 교체 -->
YOUR_AD_SLOT_ID → 1234567890
YOUR_SIDEBAR_AD_SLOT_ID → 0987654321
YOUR_FOOTER_AD_SLOT_ID → 1122334455
```

### 3단계: 광고 단위 위치
- **상단 배너**: 필터 아래 (반응형 광고)
- **사이드바**: 오른쪽 메인 영역 (사각형 광고)
- **푸터**: 콘텐츠 하단 (반응형 광고)

## 2. 수익 최적화 전략

### 광고 배치 권장사항
- **CTR 높은 위치**: 첫 번째 검색 결과 위
- **사용자 경험**: 콘텐츠와 자연스럽게 통합
- **모바일 최적화**: 반응형 광고 사용

### 예상 수익 (월간 1만 방문자 기준)
- **CPC**: $0.10 - $0.50
- **CTR**: 1-3%
- **월 수익**: $50 - $300

## 3. 대체 수익화 방안

### AdSense 승인 전
- 직접 광고 판매 (현재 구현됨)
- 제휴 마케팅 링크
- 프리미엄 구독 모델

### AdSense 승인 후
- 디스플레이 광고 + 제휴 마케팅 병행
- 스폰서드 콘텐츠 추가
- 이메일 뉴스레터 광고

## 4. 성능 모니터링

### Google Analytics 설정
```javascript
// 이미 head에 포함됨
gtag('config', 'GA_MEASUREMENT_ID');
```

### 주요 지표 추적
- 페이지뷰 수
- 클릭률 (CTR)
- 수익 per 방문자 (RPV)
- 사용자 행동 패턴 