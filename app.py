def search_youtube_videos(query, max_results=40, category=None, subcategory=None, duration=None, difficulty=None, language=None, page_token=None, is_shorts=False, recent_month=True):
    youtube = get_youtube_service()
    if youtube is None:
        print("❌ YouTube 서비스를 사용할 수 없습니다.")
        return {'videos': [], 'nextPageToken': None}

    # 카테고리/서브카테고리에 따른 기본 검색어 설정 (교육 키워드 강화)
    if not query:
        if category == 'language' and subcategory == 'english':
            query = 'english grammar conversation tutorial education'
        elif category == 'language' and subcategory == 'chinese':
            query = '중국어 배우기 회화 문법 기초 강의 HSK 중국어 교육'
        elif category == 'language' and subcategory == 'japanese':
            query = '일본어 배우기 회화 문법 기초 강의 일본어 교육'
        elif category == 'programming':
            query = '프로그래밍 강의 코딩 배우기 한국어 교육 튜토리얼'
        elif category == 'hobby':
            query = '취미 배우기 만들기 한국어 강의 교육'
        elif category == 'certificate':
            if subcategory == '토익':
                query = '토익 TOEIC 문법 단어 리스닝 리딩 공부법 강의 교육'
            elif subcategory == '토플':
                query = '토플 TOEFL IBT 스피킹 라이팅 리스닝 리딩 강의 교육'
            elif subcategory == '컴활':
                query = '컴활 컴퓨터활용능력 엑셀 파워포인트 컴퓨터 자격증 강의 교육'
            elif subcategory == '정보처리기사':
                query = '정보처리기사 필기 실기 프로그래밍 데이터베이스 강의 교육'
            else:
                query = '자격증 시험 공부 강의 한국어 교육'
        else:
            query = '교육 강의 학습 한국어 튜토리얼'

    original_query = query
    if query and len(query) > 15:
        query = simplify_search_query(query)
    print(f"검색 요청: query='{query}', category='{category}', subcategory='{subcategory}', language='{language}', recent_month={recent_month}")

    search_params = {
        'q': query,
        'part': 'snippet',
        'maxResults': 50 if not is_shorts else 100,
        'type': 'video',
        'order': 'viewCount'
    }

    if recent_month:
        one_month_ago = datetime.now() - timedelta(days=30)
        published_after = one_month_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        search_params['publishedAfter'] = published_after
        print(f"최근 한달 필터 적용: {published_after} 이후 영상만")
    elif search_params['order'] == 'date':
        three_months_ago = datetime.now() - timedelta(days=90)
        published_after = three_months_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        search_params['publishedAfter'] = published_after
        print(f"최신순 검색: 최근 3개월 ({published_after}) 이후 영상 검색")

    if page_token:
        search_params['pageToken'] = page_token

    # 언어별 지역 및 언어 필터 적용 (중국어 등 예외 처리)
    if language == 'ko':
        search_params['regionCode'] = 'KR'
        search_params['relevanceLanguage'] = 'ko'

        # 중국어, 일본어 서브카테고리는 예외 처리 (한국어 키워드 강제 추가 생략)
        if not (category == 'language' and subcategory in ['chinese', '일본어']):
            if '한국어' not in query:
                search_params['q'] = f"{query} 한국어"
        print(f"한국어 지역/언어 필터 적용")
    elif language == 'en':
        search_params['regionCode'] = 'US'
        search_params['relevanceLanguage'] = 'en'
        print(f"영어 지역/언어 필터 적용")

    if duration and not is_shorts:
        if duration == 'short':
            search_params['videoDuration'] = 'short'
        elif duration == 'medium':
            search_params['videoDuration'] = 'medium'
        elif duration == 'long':
            search_params['videoDuration'] = 'long'

    print(f"YouTube API 검색 파라미터: {search_params}")

    # 이하 기존 코드 동일: YouTube API 호출 및 결과 파싱
    # (생략 가능 / 위에서 수정된 부분만 전체 코드에 반영하면 됨)

    # ...

    return 결과
