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
        'order': 'viewCount'  # 인기순으로 고정
    }
    
    # 기본적으로 최근 한달 필터 적용
    if recent_month:
        one_month_ago = datetime.now() - timedelta(days=30)
        published_after = one_month_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        search_params['publishedAfter'] = published_after
        print(f"최근 한달 필터 적용: {published_after} 이후 영상만")
    
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
                    'viewCount': views
                })
                if len(videos) >= max_results:
                    break
            except Exception as e:
                print(f"비디오 정보 처리 오류: {e}")
                continue
        next_page_token = search_response.get('nextPageToken')
        return {
            'videos': videos,
            'nextPageToken': next_page_token
        }
    except HttpError as e:
        print(f'YouTube API 오류: {e}')
        return {'videos': [], 'nextPageToken': None}

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
    
    results = search_youtube_videos(
        query=query,
        category=category,
        subcategory=subcategory,
        language=language,
        recent_month=recent_month,
        is_shorts=is_shorts,
        page_token=None if page == 1 else f"page_{page}"
    )
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
