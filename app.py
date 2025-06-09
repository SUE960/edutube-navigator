from flask import Flask, render_template, request, jsonify
import json
import re
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# 환경변수에서 설정 읽기
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", "./openhermes-2.5-mistral-7b.Q4_K_M.gguf")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-production")

# YouTube API 키 확인
if not YOUTUBE_API_KEY:
    print("⚠️ YouTube API 키가 설정되지 않았습니다. 환경변수를 확인해주세요.")
    # Vercel 환경변수 재확인 시도
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DATA_API_KEY")
    
    # 여전히 없으면 기본값 사용 (개발용 - 실제 배포에서는 환경변수 필수)
    if not YOUTUBE_API_KEY:
        YOUTUBE_API_KEY = "AIzaSyBn_AhmUqK4Gn2Yq-gLEv1vKKra_ahcHps"
        print("⚠️ 기본 API 키를 사용합니다. 프로덕션에서는 환경변수를 설정해주세요.")
    else:
        print("✅ 환경변수에서 API 키를 찾았습니다.")

# Flask 설정
app.secret_key = SECRET_KEY

# 배포 환경 감지
IS_PRODUCTION = os.getenv('VERCEL') or os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('HEROKU') or os.getenv('FLASK_ENV') == 'production'

# 전역 변수로 모델을 한 번만 로드
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

# ISO 8601 duration을 사람이 읽을 수 있는 형식으로 변환
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

# ISO 8601 duration을 초 단위로 변환
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

def load_gguf_model(model_path: str):
    global _llm_model
    # 배포 환경이 아닌 로컬 환경에서는 모델 로딩 시도
    if IS_PRODUCTION:
        print("배포 환경에서는 GGUF 모델을 사용하지 않습니다.")
        return None
    
    # 모델 파일이 존재하지 않으면 건너뛰기
    if not os.path.exists(model_path):
        print(f"GGUF 모델 파일을 찾을 수 없습니다: {model_path}")
        return None
        
    if _llm_model is None:
        print(f"GGUF 모델 '{model_path}'을 로드 중입니다.")
        print("(최초 로드 시 시간이 소요될 수 있습니다.)")
        try:
            _llm_model = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=-1 if torch.cuda.is_available() else 0,
                verbose=False
            )
            print("GGUF 모델 로드 완료!")
        except Exception as e:
            print(f"GGUF 모델 로드 실패: {e}")
            return None
    return _llm_model

def generate_text_with_gguf_model(llm_model, prompt_text: str, max_tokens: int = 250, temperature: float = 0.2, top_p: float = 0.98):
    if llm_model is None:
        return "N/A"  # 모델이 없을 때 기본값 반환
        
    response = llm_model.create_completion(
        prompt=prompt_text,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stop=["###JSON_END###", "---"],
        echo=False
    )
    return response['choices'][0]['text']

def extract_learning_conditions_with_gguf_llm(user_input: str) -> dict:
    # 배포 환경에서는 간단한 키워드 매칭으로 대체
    if IS_PRODUCTION:
        return {
            "주제": "일반 검색",
            "난이도": "N/A",
            "형식": "N/A", 
            "시간": "N/A",
            "강사_목소리": "N/A",
            "기타_요구사항": "N/A"
        }
    
    llm_model = load_gguf_model(GGUF_MODEL_PATH)
    if llm_model is None:
        return {
            "주제": "일반 검색",
            "난이도": "N/A",
            "형식": "N/A",
            "시간": "N/A", 
            "강사_목소리": "N/A",
            "기타_요구사항": "N/A"
        }

    prompt = f"""<|im_start|>system
너는 사용자의 교육 콘텐츠 검색 쿼리에서 학습 조건을 JSON 형식으로 정확하게 추출하는 AI 비서야.
각 항목은 반드시 빠짐없이 채워야 하며, 없으면 "N/A"로 표기해.
각 항목의 예시를 참고해서 최대한 구체적으로 추출해.
결과는 오직 ###JSON_START###와 ###JSON_END### 사이에 JSON만 출력해.

### 예시 ###
입력: 파이썬 초급 강의 중 실습 위주로 30분 내 영상인데, 강사님 목소리가 또렷했으면 좋겠어요.
출력:
###JSON_START###
{{
  "주제": "파이썬",
  "난이도": "초급",
  "형식": "실습 위주",
  "시간": "30분 내",
  "강사_목소리": "또렷함",
  "기타_요구사항": "N/A"
}}
###JSON_END###

입력: 데이터 분석 입문 영상인데, 자막 있으면 좋겠고, 강사님이 차분했으면 좋겠어.
출력:
###JSON_START###
{{
  "주제": "데이터 분석",
  "난이도": "입문",
  "형식": "N/A",
  "시간": "N/A",
  "강사_목소리": "차분함",
  "기타_요구사항": "자막 제공"
}}
###JSON_END###

입력: {user_input}
출력:
###JSON_START###
"""

    generated_text = generate_text_with_gguf_model(llm_model, prompt, max_tokens=350, temperature=0.1, top_p=0.99)

    extracted_conditions = {
        "주제": "N/A", "난이도": "N/A", "형식": "N/A",
        "시간": "N/A", "강사_목소리": "N/A", "기타_요구사항": "N/A"
    }

    pattern_with_markers = r'###JSON_START###\s*(.*?)\s*###JSON_END###'
    match_with_markers = re.search(pattern_with_markers, generated_text, re.DOTALL)

    json_text_candidate = ""
    if match_with_markers:
        json_text_candidate = match_with_markers.group(1).strip()
    else:
        json_start = generated_text.find('{')
        json_end = generated_text.rfind('}')
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_text_candidate = generated_text[json_start : json_end + 1].strip()
        else:
            return {
                "주제": "오류", "난이도": "오류", "형식": "오류",
                "시간": "오류", "강사_목소리": "오류", "기타_요구사항": "오류",
                "에러_메시지": "생성된 텍스트에 JSON 패턴 없음"
            }

    # 값 정규화 사전
    difficulty_map = {"초급": "초급", "입문": "입문", "중급": "중급", "고급": "고급"}
    format_map = {"실습 위주": "실습 위주", "이론 위주": "이론 위주", "문제풀이": "문제풀이"}

    def normalize_value(key, value):
        value = value.strip().replace("\n", " ").replace("  ", " ")
        if key == "난이도":
            for k in difficulty_map:
                if k in value:
                    return difficulty_map[k]
            return "N/A"
        if key == "형식":
            for k in format_map:
                if k in value:
                    return format_map[k]
            return "N/A"
        if not value or value.lower() == "n/a":
            return "N/A"
        return value

    try:
        parsed_json = json.loads(json_text_candidate)
        for key in extracted_conditions.keys():
            value = parsed_json.get(key, "N/A")
            extracted_conditions[key] = normalize_value(key, value)
        return extracted_conditions
    except json.JSONDecodeError as e:
        return {
            "주제": "오류", "난이도": "오류", "형식": "오류",
            "시간": "오류", "강사_목소리": "오류", "기타_요구사항": "오류",
            "에러_메시지": f"JSON 파싱 실패: {e}"
        }
    except Exception as e:
        return {
            "주제": "오류", "난이도": "오류", "형식": "오류",
            "시간": "오류", "강사_목소리": "오류", "기타_요구사항": "오류",
            "에러_메시지": f"일반 오류: {e}"
        }

def simplify_search_query(query: str) -> str:
    """긴 자연어 검색어를 YouTube 검색에 적합한 핵심 키워드로 변환"""
    if not query or len(query) < 20:
        return query
    
    # 핵심 기술/언어 키워드
    tech_keywords = [
        '파이썬', 'python', '자바스크립트', 'javascript', 'java', 'c++', 'html', 'css',
        '리액트', 'react', '노드', 'node', '데이터분석', '머신러닝', '딥러닝',
        '웹개발', '앱개발', '프로그래밍', '코딩'
    ]
    
    # 학습 관련 키워드
    learning_keywords = [
        '강의', '배우기', '학습', '공부', '튜토리얼', '기초', '입문', '초급', '중급', '고급',
        '실습', '예제', '따라하기', '완전정복', '마스터'
    ]
    
    # 언어학습 키워드
    language_keywords = [
        '영어', '일본어', '중국어', '언어', '회화', '문법', '발음', '어학', 'TOEIC', 'IELTS'
    ]
    
    # 취미 키워드
    hobby_keywords = [
        '요리', '그림', '운동', '취미', 'DIY', '만들기', '음악', '사진'
    ]
    
    all_keywords = tech_keywords + learning_keywords + language_keywords + hobby_keywords
    
    # 검색어에서 핵심 키워드 추출
    found_keywords = []
    query_lower = query.lower()
    
    for keyword in all_keywords:
        if keyword in query_lower:
            found_keywords.append(keyword)
    
    # 핵심 키워드가 있으면 해당 키워드들로 검색어 구성
    if found_keywords:
        # 중복 제거 및 최대 5개까지만
        unique_keywords = list(set(found_keywords))[:5]
        simplified = ' '.join(unique_keywords)
        print(f"검색어 간소화: '{query}' → '{simplified}'")
        return simplified
    
    # 키워드가 없으면 첫 10글자만 사용
    simplified = query[:10].strip()
    print(f"검색어 간소화: '{query}' → '{simplified}'")
    return simplified

def search_youtube_videos(query, max_results=40, category=None, subcategory=None, duration=None, difficulty=None, sortOrder='relevance', language=None, page_token=None, is_shorts=False):
    youtube = get_youtube_service()
    
    # YouTube 서비스 연결 확인
    if youtube is None:
        print("❌ YouTube 서비스를 사용할 수 없습니다.")
        return {'videos': [], 'nextPageToken': None}
    
    # 검색어 간소화 (긴 자연어 검색어 처리)
    original_query = query
    if query and len(query) > 15:
        query = simplify_search_query(query)
    
    print(f"검색 요청: query='{query}', category='{category}', subcategory='{subcategory}', duration='{duration}', difficulty='{difficulty}', language='{language}', sortOrder='{sortOrder}', page_token='{page_token}', is_shorts='{is_shorts}'")
    
    # 검색어가 없고 카테고리도 없으면 교육 콘텐츠 검색
    if not query and not category:
        print("교육 관련 콘텐츠를 검색합니다...")
        # 한국어 교육 전용 검색어 (더 구체적으로)
        if language == 'ko':
            if is_shorts:
                query = "프로그래밍 코딩 개발 파이썬 자바스크립트 웹개발 팁 꿀팁"
            else:
                query = "프로그래밍 강의 파이썬 기초 자바스크립트 튜토리얼 웹개발 입문 코딩 배우기"
        else:
            if is_shorts:
                query = "programming coding python javascript web development tips"
            else:
                query = "programming tutorial learn coding python javascript course beginner"
        
        if not is_shorts:
            duration = 'medium'  # Video 탭: 10-30분 영상 우선
        sortOrder = 'viewCount'  # 인기순으로 정렬
    
    # 하위 카테고리별 한국어 검색 키워드
    if category and subcategory and language == 'ko':
        subcategory_queries = {
            # 언어 학습 하위 카테고리
            'language': {
                'english': "영어 회화 문법 발음 TOEIC IELTS 영어공부 영어배우기",
                'chinese': "중국어 중국어회화 중국어공부 HSK 중국어발음",
                'japanese': "일본어 일본어회화 일본어공부 JLPT 일본어발음",
                'other': "스페인어 프랑스어 독일어 외국어 언어학습"
            },
            # 프로그래밍 하위 카테고리  
            'programming': {
                'python': "파이썬 파이썬강의 파이썬기초 파이썬입문 파이썬튜토리얼",
                'javascript': "자바스크립트 자바스크립트강의 자바스크립트기초 JS",
                'web': "웹개발 HTML CSS 웹프로그래밍 프론트엔드 백엔드",
                'data': "데이터분석 데이터사이언스 머신러닝 AI 인공지능"
            },
            # 취미/자격증 하위 카테고리
            'hobby': {
                'hobby': "취미 그림그리기 음악 악기 사진 공예 DIY",
                'certificate': "자격증 컴활 정보처리 토익 회계 기사",
                'exercise': "운동 헬스 요가 필라테스 홈트레이닝 스트레칭",
                'cooking': "요리 요리배우기 레시피 쿠킹 베이킹 한식"
            }
        }
        
        if category in subcategory_queries and subcategory in subcategory_queries[category]:
            if is_shorts:
                query = subcategory_queries[category][subcategory].replace("강의 기초 입문 튜토리얼 배우기 공부", "팁 꿀팁")
            else:
                query = subcategory_queries[category][subcategory] + " 강의 입문 기초 튜토리얼"
            sortOrder = 'viewCount'  # 인기순
            print(f"하위 카테고리 검색어 적용: {query}")
    
    # 카테고리별 한국어 검색 키워드 강화 (하위 카테고리가 없는 경우)
    elif category and not subcategory and language == 'ko':
        if is_shorts:
            category_korean_queries = {
                'programming': "프로그래밍 코딩 개발 파이썬 자바스크립트 웹개발 팁",
                'language': "영어 일본어 중국어 언어 회화 발음 팁",
                'hobby': "취미 요리 운동 그림 DIY"
            }
        else:
            category_korean_queries = {
                'programming': "프로그래밍 강의 파이썬 기초 자바스크립트 튜토리얼 웹개발 입문 코딩 배우기 개발자 공부",
                'language': "영어 배우기 일본어 중국어 언어 학습 회화 문법 발음 어학 TOEIC IELTS 외국어",
                'hobby': "요리 배우기 그림 그리기 운동 입문 취미 활동 DIY 만들기 handmade 배우는"
            }
        if category in category_korean_queries:
            query = category_korean_queries[category]
            sortOrder = 'viewCount'  # 인기순
    
    # 카테고리 문자열을 YouTube 숫자 ID로 매핑 - 제한 완화
    category_mapping = {
        'language': None, # 언어학습은 카테고리 제한 없음
        'programming': None, # 프로그래밍도 제한 완화
        'hobby': None # 취미도 제한 완화
    }
    
    # 모든 카테고리에서 제한을 완화하여 더 많은 결과 확보
    youtube_category_id = None
    
    # 배포 환경에서 안정성을 위해 카테고리 ID 완전 제거
    # Shorts의 경우 카테고리 제한을 완화 (더 많은 결과를 위해)
    # if is_shorts:
    #     youtube_category_id = None  # 카테고리 제한 없음
    # else:
    #     youtube_category_id = category_mapping.get(category, '27')  # 기본값을 교육으로
    
    # 기본 검색 파라미터
    search_params = {
        'q': query,
        'part': 'snippet',
        'maxResults': 50 if not is_shorts else 100,  # API에서 더 많이 가져오기
        'type': 'video',
        'order': sortOrder
    }
    
    # 페이지네이션 토큰 추가
    if page_token:
        search_params['pageToken'] = page_token

    # 언어 필터 적용 - 한국어 우선
    if language == 'ko':
        search_params['regionCode'] = 'KR'  # 한국 지역 우선
        search_params['relevanceLanguage'] = 'ko'
        print(f"한국어 지역/언어 필터 적용")
    elif language:
        search_params['relevanceLanguage'] = language
        print(f"언어 필터 적용: {language}")
    
    # 시간 필터 적용
    if duration and not is_shorts:  # Shorts는 duration 필터 적용 안 함
        if duration == 'short':
            search_params['videoDuration'] = 'short'
        elif duration == 'medium':
            search_params['videoDuration'] = 'medium'
        elif duration == 'long':
            search_params['videoDuration'] = 'long'
    
    print(f"YouTube API 검색 파라미터: {search_params}")
    
    try:
        search_response = youtube.search().list(**search_params).execute()
        initial_results = len(search_response.get('items', []))
        print(f"YouTube API 응답 받음: {initial_results}개 영상")
        
        # 첫 번째 검색에서 결과가 적을 때 백업 검색 실행
        if initial_results < 5 and category:
            print(f"⚠️ 결과가 부족합니다. 백업 검색을 시도합니다...")
            
            # 백업 검색어 (더 간단하고 광범위하게)
            backup_queries = {
                'programming': "파이썬 강의" if not is_shorts else "코딩 팁",
                'language': "영어 배우기" if not is_shorts else "영어 팁", 
                'hobby': "요리 배우기" if not is_shorts else "요리 팁"
            }
            
            if category in backup_queries:
                backup_params = search_params.copy()
                backup_params['q'] = backup_queries[category]
                backup_params['maxResults'] = 30
                
                print(f"백업 검색 파라미터: {backup_params}")
                
                try:
                    backup_response = youtube.search().list(**backup_params).execute()
                    backup_results = len(backup_response.get('items', []))
                    print(f"백업 검색 응답: {backup_results}개 영상")
                    
                    if backup_results > initial_results:
                        print(f"✅ 백업 검색이 더 좋은 결과를 제공했습니다.")
                        search_response = backup_response
                except Exception as e:
                    print(f"❌ 백업 검색 실패: {e}")
        
        videos = []
        
        # 한국어 교육 필수 키워드 (더 엄격하게)
        korean_educational_keywords = [
            '강의', '배우기', '학습', '공부', '튜토리얼', '가이드', '설명', '방법',
            '프로그래밍', '코딩', '개발', '파이썬', '자바스크립트', '웹개발',
            '초급', '중급', '고급', '기초', '입문', '강좌', '수업', '교육',
            '실습', '예제', '따라하기', '만들기', '배우는', '익히기', '알아보기',
            '완전정복', '마스터', '정리', '총정리', '핵심', '필수', '기본',
            '실무', '현업', '취업', '개념', '원리', '이해하기', '쉽게',
            '처음', '시작', '입문자', '초보자', '혼자', '독학', '스터디',
            '과정', '단계별', '차근차근', '완벽', '전체', '시리즈',
            # 언어학습 전용 키워드 추가
            '영어', '일본어', '중국어', '언어', '회화', '문법', '발음', '단어',
            '어학', 'TOEIC', 'IELTS', '외국어', '번역', '해석', '리스닝', '스피킹',
            # 취미/자격증 전용 키워드 추가
            '요리', '레시피', '쿠킹', '베이킹', '한식', '양식', '중식', '일식',
            '그림', '그리기', '드로잉', '스케치', '페인팅', '미술', '디자인',
            '운동', '헬스', '요가', '필라테스', '홈트', '스트레칭', '다이어트',
            '취미', '자격증', '컴활', '정보처리', '토익', '회계', '기사',
            'DIY', '만들기', '공예', '핸드메이드', '수공예', '취미생활',
            '음악', '악기', '기타', '피아노', '드럼', '노래', '작곡',
            '사진', '촬영', '카메라', '편집', '포토샵', '영상'
        ]
        
        # 영어 교육 키워드
        english_educational_keywords = [
            'tutorial', 'learn', 'learning', 'course', 'lesson', 'programming', 'coding', 
            'python', 'javascript', 'java', 'html', 'css', 'react', 'node', 'data', 
            'algorithm', 'development', 'developer', 'guide', 'how to', 'beginner',
            'intermediate', 'advanced', 'education', 'study', 'training', 'skill',
            'web development', 'software', 'computer science', 'math', 'science',
            'english', 'language', 'grammar', 'vocabulary', 'speaking', 'listening',
            'masterclass', 'bootcamp', 'crash course', 'complete', 'full', 'comprehensive',
            'step by step', 'basics', 'fundamentals', 'introduction', 'explained'
        ]
        
        # 확실히 제외할 키워드 (매우 엄격하게 - 뉴스/방송/사건사고 포함)
        excluded_keywords = [
            # 한국어 비교육 키워드
            '먹방', '브이로그', '일상', '놀이', '게임', '웃긴', '재밌는', '연예인',
            '패션', '뷰티', '메이크업', '여행', '맛집', '리뷰', '언박싱', '쇼핑',
            '챌린지', '댄스', '커버', '노래', '음악', '영화', '드라마', 'asmr',
            '집중', '수면', '명상', '힐링', '플레이리스트', '믹스', '컴필레이션',
            # 뉴스/방송/정치/사건사고 관련 키워드 (매우 엄격하게)
            '뉴스', '속보', '사건', '사고', '논란', '갈등', '정치', '국정감사',
            '탄핵', '대통령', '의원', '국회', '정부', '부처', '장관', '시장',
            '경찰', '검찰', '법원', '판사', '변호사', '수사', '기소', '재판',
            '체포', '구속', '영장', '피의자', '용의자', '범인', '살인', '강도',
            '방송사고', '돌발', '우왕좌왕', '혼란', '실수', '오류', '트럼프',
            '윤상현', '돌비', 'KBS', 'MBC', 'SBS', '뉴스데스크', '뉴스투데이',
            '9시뉴스', '종합뉴스', '아침뉴스', '저녁뉴스', '특보', '긴급', '생방송',
            '방송', '송출', '중계', '시험감독', '시험감독관', '휴대전화', '소음',
            # 영어 비교육 키워드  
            'mix', 'playlist', 'compilation', 'asmr', 'relaxing', 'chill', 'sleep',
            'meditation', 'music', 'song', 'dance', 'funny', 'comedy', 'meme',
            'entertainment', 'vlog', 'travel', 'food', 'cooking', 'recipe',
            'fashion', 'beauty', 'makeup', 'gaming', 'game', 'play', 'challenge',
            'reaction', 'review', 'unboxing', 'lifestyle', 'daily', 'routine',
            'breaking', 'news', 'scandal', 'politics', 'arrest', 'court', 'trump',
            'president', 'government', 'police', 'crime', 'murder', 'accident',
            'broadcast', 'reporter', 'anchor', 'breaking news'
        ]
        
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            
            # 비디오 상세 정보 가져오기
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
                
                # 영상 길이에 따른 필터링
                if is_shorts:
                    # Shorts 탭: 1분(60초) 미만만 표시
                    if duration_seconds >= 60:
                        print(f"Shorts 길이 초과: {item['snippet']['title'][:50]}... ({duration_seconds}초)")
                        continue
                else:
                    # Video 탭: 1분(60초) 이상만 표시
                    if duration_seconds < 60:
                        print(f"Video 길이 부족: {item['snippet']['title'][:50]}... ({duration_seconds}초)")
                        continue
                
                # 제목과 설명을 결합하여 교육 콘텐츠 여부 판단
                title = item['snippet']['title']
                description = item['snippet']['description']
                content_text = f"{title} {description}".lower()
                
                # 제외 키워드 확인 (더 엄격하게)
                excluded_matches = [keyword for keyword in excluded_keywords if keyword in content_text]
                
                # 제외 키워드가 하나라도 있으면 무조건 제외 (뉴스/방송 필터링 강화)
                if excluded_matches:
                    print(f"제외 키워드 발견: {title[:50]}... ({excluded_matches[:3]})")
                    continue
                
                # 한국어 필터가 활성화된 경우
                if language == 'ko':
                    # 한국어 문자 포함 여부 확인
                    has_korean_chars = any(char in content_text for char in '가나다라마바사아자차카타파하힘ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ')
                    
                    # 한국어 교육 키워드 매칭
                    korean_edu_matches = [keyword for keyword in korean_educational_keywords if keyword in content_text]
                    english_edu_matches = [keyword for keyword in english_educational_keywords if keyword in content_text]
                    
                    # 한국어 콘텐츠인 경우 한국어 교육 키워드가 필수 (취미는 예외)
                    if has_korean_chars and len(korean_edu_matches) == 0 and category != 'hobby':
                        print(f"한국어 교육키워드 없음: {title[:50]}...")
                        continue
                    
                    # 영어 콘텐츠인 경우 영어 교육 키워드가 필수
                    if not has_korean_chars and len(english_edu_matches) < 2:
                        print(f"영어 교육키워드 부족: {title[:50]}...")
                        continue
                    
                    # 교육 점수 계산 (한국어 가중치)
                    korean_score = len(korean_edu_matches) * 3  # 한국어 키워드 더 높은 가중치
                    english_score = len(english_edu_matches)
                    total_edu_score = korean_score + english_score
                    
                    # 카테고리별 점수 기준 완화
                    if category == 'language':
                        min_score = 1 if is_shorts else 1  # 언어학습은 점수 기준 완화
                    elif category == 'hobby':
                        min_score = 1 if is_shorts else 1  # 취미도 점수 기준 완화
                    else:
                        # Shorts는 교육 점수 기준을 완화 (더 많은 콘텐츠 표시)
                        min_score = 1 if is_shorts else 3
                        
                    if total_edu_score < min_score:
                        print(f"교육점수 부족: {title[:50]}... (점수: {total_edu_score}, 최소: {min_score})")
                        continue
                        
                else:
                    # 영어 모드에서는 영어 교육 키워드 필수
                    english_edu_matches = [keyword for keyword in english_educational_keywords if keyword in content_text]
                    min_english_keywords = 1 if is_shorts else 3
                    if len(english_edu_matches) < min_english_keywords:
                        continue
                
                # 난이도 필터링 (조회수 기반)
                if difficulty:
                    if difficulty == 'beginner' and views > 1000000:  # 초급자용은 너무 인기있는 것 제외
                        continue
                    elif difficulty == 'intermediate' and (views < 10000 or views > 2000000):
                        continue
                    elif difficulty == 'advanced' and views < 100000:
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
                
                # 원하는 수만큼 수집되면 중단
                if len(videos) >= max_results:
                    break
                    
            except Exception as e:
                print(f"비디오 정보 처리 오류: {e}")
                continue
        
        print(f"필터링 후 교육 콘텐츠: {len(videos)}개")
        
        # 다음 페이지 토큰 반환
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

@app.route('/analyze', methods=['POST'])
def analyze():
    user_input = request.json.get('query', '')
    if not user_input:
        return jsonify({"error": "검색어를 입력해주세요."}), 400
    
    # 배포 환경에서는 간단한 키워드 매칭으로 분석
    result = extract_learning_conditions_with_gguf_llm(user_input)
    
    # LLM 결과가 기본값이면 검색어 간소화도 시도
    if result.get("주제") == "일반 검색":
        simplified = simplify_search_query(user_input)
        if simplified != user_input:
            result["주제"] = simplified
            result["검색어_간소화"] = f"'{user_input}' → '{simplified}'"
    
    return jsonify(result)

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')
    category = data.get('category')
    subcategory = data.get('subcategory')
    duration = data.get('duration')
    difficulty = data.get('difficulty')
    language = data.get('language', 'ko')  # 기본값을 한국어로 설정
    sortOrder = data.get('sortOrder', 'viewCount')  # 기본값을 인기순으로 변경
    page_token = data.get('pageToken')  # 페이지네이션 토큰
    is_shorts = data.get('is_shorts', False)  # 추가된 is_shorts 매개변수

    if not query and not category:
        pass
    elif not query and category:
        query = ""

    if not query and not category:
        pass
    elif not query and category:
        query = category

    result = search_youtube_videos(
        query, 
        category=category, 
        subcategory=subcategory, 
        duration=duration, 
        difficulty=difficulty, 
        language=language, 
        sortOrder=sortOrder,
        page_token=page_token,
        is_shorts=is_shorts
    )
    
    return jsonify({
        "success": True, 
        "videos": result['videos'],
        "nextPageToken": result['nextPageToken']
    })

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

if __name__ == '__main__':
    # 로컬 개발용
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5005)), debug=False)
else:
    # Vercel 배포용 - 이 부분이 중요!
    app.debug = False
