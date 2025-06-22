from flask import Flask, render_template, request, jsonify
import json
import re
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

# 환경변수에서 설정 읽기
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", "./openhermes-2.5-mistral-7b.Q4_K_M.gguf")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-production")

# YouTube API 키 확인
if not YOUTUBE_API_KEY:
    print("⚠️ YouTube API 키가 설정되지 않았습니다. 환경변수를 확인해주세요.")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DATA_API_KEY")
    if not YOUTUBE_API_KEY:
        YOUTUBE_API_KEY = "AIzaSyBn_AhmUqK4Gn2Yq-gLEv1vKKra_ahcHps"
        print("⚠️ 기본 API 키를 사용합니다. 프로덕션에서는 환경변수를 설정해주세요.")
    else:
        print("✅ 환경변수에서 API 키를 찾았습니다.")

app.secret_key = SECRET_KEY

IS_PRODUCTION = os.getenv('VERCEL') or os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('HEROKU') or os.getenv('FLASK_ENV') == 'production'

_llm_model = None
_youtube = None

# 교육 분야별 인기 유튜버 채널 ID 리스트 (구독자 수 순으로 정렬)
POPULAR_EDUCATIONAL_CHANNELS = {
    'language': {
        'english': [
            ('UC0gkIRsU6C5NiWIbRjuGy8A', '야나두', 1500000),  # 야나두 - 150만
            ('UCzGjO40hA1IMUOv-bTVlqyg', '라이브아카데미', 1200000),  # 라이브아카데미 - 120만
            ('UCQzJm6xkGCvI4nJUVa6mFrw', '영어맨', 800000),  # 영어맨 - 80만
            ('UC4Xe9ggYjNiKnPCBPKJZZww', '영어회화 100일의 기적', 600000),  # 영어회화 100일의 기적 - 60만
            ('UCfnlDaLDjhw8RlNrWU0sZmA', '진짜미국영어', 400000),  # 진짜미국영어 - 40만
        ],
        'chinese': [
            ('UCPqgBhAKwh4Ql0K6gLVUzDg', '중국어맨', 300000),  # 중국어맨 - 30만
            ('UCqhTjsU5Hg7M4CpLGZd2qxQ', '차이홍', 200000),  # 차이홍 - 20만
            ('UCMdz7wlsVhYfD6bwF1Nz5wQ', '중국어공부', 150000),  # 중국어공부 - 15만
        ],
        'japanese': [
            ('UCVx6RFaEAg46xfAsD2zz16w', '일본어맨', 250000),  # 일본어맨 - 25만
            ('UCgqHDxKzjgJGdFTCgLbGVig', '히라가나', 180000),  # 히라가나 - 18만
            ('UCOPCJJgHfKdVYGNJBKWuPmg', '일본어공부', 120000),  # 일본어공부 - 12만
        ]
    },
    'programming': [
        ('UCUpJs89fSBXNolQGOYKn0YQ', '코딩애플', 800000),  # 코딩애플 - 80만
        ('UCqMTJfbOZ5XLs8JwKWjVhzQ', '생활코딩', 600000),  # 생활코딩 - 60만
        ('UCGhqkImhurjuEr3KKLBSqpg', '노마드코더', 500000),  # 노마드코더 - 50만
        ('UC7iAOLiALt2rtMVAWWl4pnw', '드림코딩', 400000),  # 드림코딩 - 40만
        ('UCQjrcbAYBAHFKoNKnbzfJbA', '조코딩', 350000),  # 조코딩 - 35만
        ('UCZ30aWiMw5C8mGcESlAGQdA', '빵형의 개발도상국', 300000),  # 빵형의 개발도상국 - 30만
    ],
    'hobby': [
        ('UCOxqgCwjGl5T4N-5UbdNWKg', '백종원의 요리비책', 2000000),  # 백종원의 요리비책 - 200만
        ('UCYEf5JPp4JzMIKnlyRCVNKg', '쿠킹트리', 1500000),  # 쿠킹트리 - 150만
        ('UCnM1fLy1qRKuSP3bFVqSMOQ', '혼밥연구소', 800000),  # 혼밥연구소 - 80만
        ('UCzDMwOYYgdymd8NfKTJSaiA', '그림그리기', 300000),  # 그림그리기 - 30만
    ],
    'certificate': [
        ('UCpOG7oIiJNXi7pjqjkYVFdQ', '해커스토익', 400000),  # 해커스토익 - 40만
        ('UCKvqhQYh3YKMaEOQGxdgFBQ', '토익스피킹', 200000),  # 토익스피킹 - 20만
        ('UCKr6B9tSP8YvPFNgFjj7nKQ', '컴활', 150000),  # 컴활 - 15만
        ('UC9-y-6csu5WGm29I7JiwpnA', '정보처리기사', 100000),  # 정보처리기사 - 10만
    ]
}

def get_youtube_service():
    global _youtube
    if _youtube is None:
        try:
            if not YOUTUBE_API_KEY:
                print("⚠️ YouTube API 키가 없습니다!")
                return None
            _youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            print("✅ YouTube 서비스 연결 성공")
        except Exception as e:
            print(f"❌ YouTube 서비스 연결 실패: {e}")
            return None
    return _youtube

def parse_duration(duration):
    try:
        td = isodate.parse_duration(duration)
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes}:{seconds:02}"
    except Exception:
        return ""

def parse_duration_to_seconds(duration):
    try:
        td = isodate.parse_duration(duration)
        return int(td.total_seconds())
    except Exception:
        return 0

def format_published_date(published_at):
    try:
        dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return published_at

def simplify_search_query(query: str) -> str:
    if not query or len(query) < 20:
        return query
    tech_keywords = [
        '파이썬', 'python', '자바스크립트', 'javascript', 'java', 'c++', 'html', 'css',
        '리액트', 'react', '노드', 'node', '데이터분석', '머신러닝', '딥러닝',
        '웹개발', '앱개발', '프로그래밍', '코딩'
    ]
    learning_keywords = [
        '강의', '배우기', '학습', '공부', '튜토리얼', '기초', '입문', '초급', '중급', '고급',
        '실습', '예제', '따라하기', '완전정복', '마스터'
    ]
    language_keywords = [
        '영어', '일본어', '중국어', '언어', '회화', '문법', '발음', '어학', 'TOEIC', 'IELTS'
    ]
    hobby_keywords = [
        '요리', '그림', '운동', '취미', 'DIY', '만들기', '음악', '사진'
    ]
    all_keywords = tech_keywords + learning_keywords + language_keywords + hobby_keywords
    found_keywords = []
    query_lower = query.lower()
    for keyword in all_keywords:
        if keyword in query_lower:
            found_keywords.append(keyword)
    if found_keywords:
        unique_keywords = list(set(found_keywords))[:5]
        simplified = ' '.join(unique_keywords)
        print(f"검색어 간소화: '{query}' → '{simplified}'")
        return simplified
    simplified = query[:10].strip()
    print(f"검색어 간소화: '{query}' → '{simplified}'")
    return simplified

def search_youtube_videos(query, max_results=40, category=None, subcategory=None, duration=None, difficulty=None, sortOrder='relevance', language=None, page_token=None, is_shorts=False, recent_month=True):
    youtube = get_youtube_service()
    if youtube is None:
        print("❌ YouTube 서비스를 사용할 수 없습니다.")
        return {'videos': [], 'nextPageToken': None}
    
    # 카테고리/서브카테고리에 따른 기본 검색어 설정 (교육 키워드 강화)
    if not query:
        if category == 'language' and subcategory == 'english':
            if language == 'ko':
                query = '영어 회화 문법 공부 강의 한국어 설명 교육'  # 교육 키워드 추가
            else:
                query = 'english grammar conversation tutorial education'
        elif category == 'programming':
            if language == 'ko':
                query = '프로그래밍 강의 코딩 배우기 한국어 교육 튜토리얼'  # 교육 키워드 추가
            else:
                query = 'programming tutorial coding course education'
        elif category == 'hobby':
            if language == 'ko':
                query = '취미 배우기 만들기 한국어 강의 교육'  # 교육 키워드 추가
            else:
                query = 'hobby tutorial how to make education'
        elif category == 'certificate':
            if language == 'ko':
                # 구체적인 자격증별 검색어 설정
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
                if subcategory == 'toeic':
                    query = 'TOEIC listening reading grammar vocabulary test prep education'
                elif subcategory == 'toefl':
                    query = 'TOEFL IBT speaking writing listening reading test prep education'
                else:
                    query = 'certificate exam preparation course education'
        else:
            if language == 'ko':
                query = '교육 강의 학습 한국어 튜토리얼'  # 교육 키워드 강화
            else:
                query = 'education tutorial learning course'
    
    original_query = query
    if query and len(query) > 15:
        query = simplify_search_query(query)
    print(f"검색 요청: query='{query}', category='{category}', subcategory='{subcategory}', language='{language}', recent_month={recent_month}")
    
    search_params = {
        'q': query,
        'part': 'snippet',
        'maxResults': 50 if not is_shorts else 100,
        'type': 'video',
        'order': 'viewCount' if sortOrder == 'viewCount' else 'date'  # 정렬 옵션 동적 적용
    }
    
    # 기본적으로 최근 한달 필터 적용
    if recent_month:
        one_month_ago = datetime.now() - timedelta(days=30)
        published_after = one_month_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        search_params['publishedAfter'] = published_after
        print(f"최근 한달 필터 적용: {published_after} 이후 영상만")
    elif sortOrder == 'date':
        # 최신순 정렬 시에는 최근 3개월로 범위 확장하여 더 많은 최신 영상 확보
        three_months_ago = datetime.now() - timedelta(days=90)
        published_after = three_months_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        search_params['publishedAfter'] = published_after
        print(f"최신순 검색: 최근 3개월 ({published_after}) 이후 영상 검색")
    
    if page_token:
        search_params['pageToken'] = page_token
        
    # 언어별 지역 및 언어 필터 적용
    if language == 'ko':
        search_params['regionCode'] = 'KR'
        search_params['relevanceLanguage'] = 'ko'
        # 한국어 필터링을 위한 추가 검색어 조정
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
    try:
        # 1단계: 인기 유튜버 채널에서 영상 가져오기 (전체 결과의 30% 정도)
        popular_videos = []
        if not query:  # 기본 검색인 경우에만 인기 유튜버 영상 포함
            popular_videos = get_popular_channel_videos(
                category=category, 
                subcategory=subcategory, 
                language=language, 
                max_results=50,  # 더 많은 인기 유튜버 영상 (각 유튜버당 1개씩)
                sortOrder=sortOrder,
                recent_month=recent_month
            )
            print(f"인기 유튜버 영상 {len(popular_videos)}개 발견")
        
        # 2단계: 일반 YouTube 검색 (인기 유튜버 영상이 많으면 일반 검색 줄임)
        general_search_count = max(20, max_results - len(popular_videos))
        search_response = youtube.search().list(**search_params).execute()
        videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            try:
                video_response = youtube.videos().list(
                    part='contentDetails,statistics',
                    id=video_id
                ).execute()
                if not video_response['items']:
                    continue
                video_details = video_response['items'][0]
                duration_str = video_details['contentDetails']['duration']
                parsed_duration = parse_duration(duration_str)
                duration_seconds = parse_duration_to_seconds(duration_str)
                views = int(video_details['statistics'].get('viewCount', 0))
                published_at = item['snippet']['publishedAt']
                formatted_published_date = format_published_date(published_at)
                if is_shorts:
                    if duration_seconds >= 60:
                        continue
                else:
                    if duration_seconds < 60:
                        continue
                title = item['snippet']['title']
                description = item['snippet']['description']
                
                # 교육 콘텐츠 필터링 강화
                educational_keywords = ['강의', '교육', '배우기', '학습', '공부', '튜토리얼', '설명', '가르치', '레슨', '강좌', '코스']
                non_educational_keywords = ['먹방', '브이로그', 'vlog', '일상', '리뷰', '언박싱', '게임', '오락', '예능', '웃긴', 'funny', 'meme']
                
                title_lower = title.lower()
                description_lower = description.lower()
                
                # 교육 키워드 포함 여부 확인
                has_educational = any(keyword in title_lower or keyword in description_lower for keyword in educational_keywords)
                has_non_educational = any(keyword in title_lower or keyword in description_lower for keyword in non_educational_keywords)
                
                # 비교육 콘텐츠 제외
                if has_non_educational and not has_educational:
                    continue
                
                # 한국어 필터링 강화: 제목에서 한글 비율 확인
                if language == 'ko':
                    korean_chars = len([c for c in title if '\uac00' <= c <= '\ud7af'])
                    total_chars = len([c for c in title if c.isalpha()])
                    if total_chars > 0 and korean_chars / total_chars < 0.3:  # 한글 비율이 30% 미만이면 제외
                        continue
                
                videos.append({
                    'title': title,
                    'description': description[:200] + '...' if len(description) > 200 else description,
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'videoId': video_id,
                    'channelTitle': item['snippet']['channelTitle'],
                    'publishedAt': formatted_published_date,
                    'duration': parsed_duration,
                    'viewCount': views,
                    'isPopularChannel': False
                })
                if len(videos) >= general_search_count:  # 인기 유튜버 영상 수만큼 빼고 검색
                    break
            except Exception as e:
                print(f"비디오 정보 처리 오류: {e}")
                continue
        
        # 3단계: 인기 유튜버 영상과 일반 영상 혼합
        all_videos = popular_videos + videos
        
        # 중복 제거 (같은 videoId)
        seen_ids = set()
        unique_videos = []
        for video in all_videos:
            if video['videoId'] not in seen_ids:
                seen_ids.add(video['videoId'])
                unique_videos.append(video)
        
        # 최종 정렬
        if sortOrder == 'viewCount':
            unique_videos.sort(key=lambda x: x['viewCount'], reverse=True)
        elif sortOrder == 'date':
            unique_videos.sort(key=lambda x: x['publishedAt'], reverse=True)
        
        next_page_token = search_response.get('nextPageToken')
        print(f"최종 결과: 인기 유튜버 {len(popular_videos)}개 + 일반 검색 {len(videos)}개 = 총 {len(unique_videos)}개")
        return {
            'videos': unique_videos[:max_results],
            'nextPageToken': next_page_token
        }
    except HttpError as e:
        print(f'YouTube API 오류: {e}')
        return {'videos': [], 'nextPageToken': None}

def get_popular_channel_videos(category, subcategory, language='ko', max_results=20, sortOrder='viewCount', recent_month=True):
    """인기 유튜버 채널에서 영상 가져오기 - 각 유튜버당 1개씩"""
    youtube = get_youtube_service()
    if youtube is None:
        return []
    
    # 카테고리별 채널 정보 가져오기 (채널ID, 이름, 구독자수)
    channel_info_list = []
    if category == 'language' and subcategory in POPULAR_EDUCATIONAL_CHANNELS['language']:
        channel_info_list = POPULAR_EDUCATIONAL_CHANNELS['language'][subcategory]
    elif category in POPULAR_EDUCATIONAL_CHANNELS:
        channel_info_list = POPULAR_EDUCATIONAL_CHANNELS[category]
    
    if not channel_info_list:
        return []
    
    print(f"인기 유튜버 채널에서 검색 중: {len(channel_info_list)}개 채널")
    
    all_videos = []
    
    # 각 유튜버당 1개씩 영상 가져오기
    for channel_id, channel_name, subscriber_count in channel_info_list:
        try:
            # 채널의 영상 1개만 검색
            search_params = {
                'part': 'snippet',
                'channelId': channel_id,
                'maxResults': 5,  # 5개 중에서 조건에 맞는 1개 선택
                'order': 'date' if sortOrder == 'date' else 'viewCount',
                'type': 'video'
            }
            
            if recent_month:
                one_month_ago = datetime.now() - timedelta(days=30)
                published_after = one_month_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
                search_params['publishedAfter'] = published_after
            
            search_response = youtube.search().list(**search_params).execute()
            
            # 이 채널에서 첫 번째 유효한 영상 1개만 가져오기
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                try:
                    # 비디오 상세 정보 가져오기
                    video_response = youtube.videos().list(
                        part='contentDetails,statistics',
                        id=video_id
                    ).execute()
                    
                    if not video_response['items']:
                        continue
                        
                    video_details = video_response['items'][0]
                    duration_str = video_details['contentDetails']['duration']
                    parsed_duration = parse_duration(duration_str)
                    duration_seconds = parse_duration_to_seconds(duration_str)
                    views = int(video_details['statistics'].get('viewCount', 0))
                    published_at = item['snippet']['publishedAt']
                    formatted_published_date = format_published_date(published_at)
                    
                    # 60초 미만 영상 제외 (쇼츠 제외)
                    if duration_seconds < 60:
                        continue
                    
                    all_videos.append({
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'][:200] + '...' if len(item['snippet']['description']) > 200 else item['snippet']['description'],
                        'thumbnail': item['snippet']['thumbnails']['high']['url'],
                        'videoId': video_id,
                        'channelTitle': channel_name + ' ⭐',  # 미리 저장된 채널명 사용
                        'publishedAt': formatted_published_date,
                        'duration': parsed_duration,
                        'viewCount': views,
                        'isPopularChannel': True,
                        'subscriberCount': subscriber_count  # 구독자 수 추가
                    })
                    
                    # 이 채널에서는 1개만 가져오므로 break
                    break
                        
                except Exception as e:
                    print(f"비디오 정보 처리 오류: {e}")
                    continue
                
        except Exception as e:
            print(f"채널 검색 오류: {e}")
            continue
    
    # 정렬: 인기순이면 구독자 수 순, 최신순이면 날짜 순
    if sortOrder == 'viewCount':
        # 구독자 수 순으로 정렬 (이미 리스트가 구독자 수 순이므로 순서 유지)
        all_videos.sort(key=lambda x: x['subscriberCount'], reverse=True)
    elif sortOrder == 'date':
        all_videos.sort(key=lambda x: x['publishedAt'], reverse=True)
    
    print(f"인기 유튜버 영상 수집 완료: {len(all_videos)}개 (각 유튜버당 1개씩)")
    return all_videos[:max_results]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '')
    category = request.form.get('category')
    subcategory = request.form.get('subcategory')
    language = request.form.get('language', 'ko')
    page = int(request.form.get('page', 1))
    recent_month = request.form.get('recent_month', 'true').lower() == 'true'
    content_type = request.form.get('content_type', 'video')  # 'video' 또는 'shorts'
    is_shorts = content_type == 'shorts'
    sortOrder = request.form.get('sortOrder', 'viewCount')
    
    # 페이지 1인 경우에만 실제 검색 수행, 그 외에는 캐시된 결과 사용
    if page == 1:
        results = search_youtube_videos(
            query=query,
            category=category,
            subcategory=subcategory,
            language=language,
            recent_month=recent_month,
            is_shorts=is_shorts,
            sortOrder=sortOrder,
            max_results=100  # 더 많은 결과를 한번에 가져옴
        )
        # 세션에 결과 저장 (간단한 캐싱)
        from flask import session
        session['last_search_results'] = results
        session['last_search_params'] = {
            'query': query, 'category': category, 'subcategory': subcategory,
            'language': language, 'sortOrder': sortOrder, 'content_type': content_type
        }
    else:
        # 캐시된 결과 사용
        from flask import session
        results = session.get('last_search_results', {'videos': [], 'nextPageToken': None})
    
    return jsonify(results)

@app.route('/categories')
def get_categories():
    categories = {
        'language': {
            'name': '언어',
            'subcategories': ['영어', '일본어', '중국어', '스페인어', '프랑스어']
        },
        'programming': {
            'name': '프로그래밍',
            'subcategories': ['Python', 'JavaScript', 'Java', 'C++', '데이터 분석', '웹 개발', '앱 개발']
        },
        'hobby': {
            'name': '취미',
            'subcategories': ['그림', '음악', '요리', '운동', '사진', '공예']
        }
    }
    return jsonify(categories)

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
