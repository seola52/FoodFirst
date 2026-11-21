import os
import re
from datetime import date, datetime
from pathlib import Path

import requests
import streamlit as st
from supabase import create_client

# ---------- 기본 페이지 설정 ----------
st.set_page_config(
    page_title="FoodFirst - 맛있는 식재료 구출 대작전",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- 환경 및 경로 설정 ----------
APP_DIR = Path(__file__).resolve().parent
API_URL = "https://openapi.foodsafetykorea.go.kr/api"

# ---------- Supabase 연결 ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

if "supabase" not in st.session_state:
    st.session_state["supabase"] = create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = st.session_state["supabase"]

# ---------- 로그인 상태 관리 ----------
if "user" not in st.session_state:
    st.session_state["user"] = None

if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""


# ---------- 회원가입 및 로그인 ----------
def show_auth():
    st.title("🧊 FoodFirst")
    st.subheader("나만의 냉장고를 관리해 보세요!")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_password")

        if st.button("로그인", use_container_width=True):
            try:
                result = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password,
                })
                st.session_state["user"] = result.user
                st.session_state["user_email"] = result.user.email
                st.rerun()
            except Exception:
                st.error("로그인에 실패했습니다. 이메일과 비밀번호를 확인해 주세요.")

    with tab2:
        new_email = st.text_input("이메일", key="signup_email")
        new_password = st.text_input(
            "비밀번호 (6자 이상)", type="password", key="signup_password"
        )

        if st.button("회원가입", use_container_width=True):
            if len(new_password) < 6:
                st.error("비밀번호는 6자 이상 입력해 주세요.")
            else:
                try:
                    supabase.auth.sign_up({
                        "email": new_email,
                        "password": new_password,
                    })
                    st.success(
                        "회원가입 요청이 완료되었습니다. 이메일 인증이 필요할 수 있습니다."
                    )
                except Exception:
                    st.error("회원가입에 실패했습니다. 입력 정보를 확인해 주세요.")


# ---------- 로그인 여부 확인 ----------
if st.session_state["user"] is None:
    show_auth()
    st.stop()

# ---------- 로그인 사용자 정보 ----------
st.sidebar.success(f"로그인: {st.session_state['user_email']}")

if st.sidebar.button("로그아웃"):
    supabase.auth.sign_out()
    st.session_state["user"] = None
    st.session_state["user_email"] = ""
    st.rerun()


# ---------- 헬퍼 함수 ----------
def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except Exception:
        return None


def days_until(expiry):
    d = parse_date(expiry)
    return (d - date.today()).days if d else None


def norm(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


def split_ingredients(text):
    """
    단순 문자열 분리 헬퍼 (AI 분석기가 아님을 명시)
    단위, 수량, 괄호 부가설명을 제거하여 매칭용 재료명 목록을 반환합니다.
    """
    bits = re.split(r"[,，、\n;/]+", text or "")
    cleaned = []
    unit_pattern = r"\d+(?:\.\d+)?\s*(g|kg|ml|l|개|모|통|반|공기|단|팩|봉|캔|큰술|작은술|컵|T|t|장|줄기|쪽|줌|꼬집|인분)"
    for bit in bits:
        bit = bit.strip()
        bit = re.sub(r"\([^)]*\)", "", bit).strip()
        bit = re.sub(r"\[[^\]]*\]", "", bit).strip()
        bit = re.sub(unit_pattern, "", bit, flags=re.I).strip()
        bit = re.sub(r"^[-·•*]\s*", "", bit).strip()
        if bit and bit not in cleaned:
            cleaned.append(bit)
    return cleaned


def get_ingredients():
    user_id = str(st.session_state["user"].id)
    result = (
        supabase.table("ingredients")
        .select("*")
        .eq("user_id", user_id)
        .order("id", desc=True)
        .execute()
    )
    return result.data or []


def get_user_recipes():
    result = (
        supabase.table("user_recipes")
        .select("*")
        .order("id", desc=True)
        .execute()
    )
    return result.data or []


def get_total_creator_points():
    result = supabase.table("user_recipes").select("points_awarded").execute()
    rows = result.data or []
    return sum(int(row.get("points_awarded") or 0) for row in rows)


# 70종 이상의 친근한 식재료 이모지 매핑 딕셔너리
EMOJI_MAP = {
    # 채소류
    "양파": "🧅", "대파": "🌱", "쪽파": "🌱", "파": "🌱", "마늘": "🧄", "고추": "🌶️",
    "당근": "🥕", "감자": "🥔", "고구마": "🍠", "토마토": "🍅", "오이": "🥒", "가지": "🍆",
    "호박": "🎃", "애호박": "🥒", "버섯": "🍄", "표고": "🍄", "팽이": "🍄", "시금치": "🥬",
    "콩나물": "🌱", "숙주": "🌱", "배추": "🥬", "양배추": "🥗", "상추": "🥬", "깻잎": "🍃",
    "무": "🥕", "브로콜리": "🥦", "파프리카": "🫑", "피망": "🫑", "옥수수": "🌽",
    # 육류 및 해산물
    "돼지": "🥩", "소고기": "🥩", "쇠고기": "🥩", "고기": "🥩", "닭": "🍗", "치킨": "🍗",
    "오리": "🦆", "햄": "🍖", "소시지": "🌭", "베이컨": "🥓", "생선": "🐟", "고등어": "🐟",
    "연어": "🍣", "새우": "🦐", "오징어": "🦑", "문어": "🐙", "조개": "🦪", "멸치": "🐟",
    "참치": "🐟", "어묵": "🍢",
    # 알류 및 콩/유제품
    "달걀": "🥚", "계란": "🥚", "두부": "🧊", "순두부": "🧊", "우유": "🥛", "치즈": "🧀",
    "버터": "🧈", "요거트": "🥣", "콩": "🫘",
    # 과일류
    "사과": "🍎", "바나나": "🍌", "딸기": "🍓", "포도": "🍇", "수박": "🍉", "레몬": "🍋",
    "오렌지": "🍊", "귤": "🍊", "복숭아": "🍑", "망고": "🥭",
    # 곡물/가공식품/양념
    "밥": "🍚", "쌀": "🌾", "빵": "🍞", "식빵": "🍞", "떡": "🍡", "라면": "🍜",
    "면": "🍝", "국수": "🍜", "파스타": "🍝", "김치": "🥬", "된장": "🫙", "고추장": "🌶️",
    "간장": "🍾", "식초": "🍾", "참기름": "🧴", "설탕": "🧂", "소금": "🧂", "후추": "🧂",
    "케첩": "🥫", "마요네즈": "🥫", "잼": "🍯", "꿀": "🍯", "물": "💧", "만두": "🥟",
}


def get_ingredient_emoji(name):
    clean_name = str(name).strip()
    for key, emoji in EMOJI_MAP.items():
        if key in clean_name:
            return emoji
    return "🏷️"


def days_label(expiry):
    d = days_until(expiry)
    if d is None:
        return "기한 미입력", "neutral"
    if d < 0:
        return f"{abs(d)}일 지남 (확인 필요)", "expired"
    if d == 0:
        return "오늘 마감 (D-Day)", "urgent"
    if d <= 3:
        return f"D-{d} (임박)", "warning"
    return f"D-{d}", "safe"


def fetch_public_recipes(api_key, start=1, end=50):
    """식품안전나라 '조리식품의 레시피 DB' 공개 API 연동"""
    if not api_key:
        return [], "API 인증키를 입력하면 식품안전나라의 공식 공개 레시피를 실시간으로 불러옵니다."

    url = f"{API_URL}/{api_key}/COOKRCP01/json/{start}/{end}"
    try:
        response = requests.get(url, timeout=12)
        response.raise_for_status()

        try:
            payload = response.json()
        except Exception:
            return [], "API 응답이 올바른 JSON 형식이 아닙니다. 인증키나 서비스 상태를 확인해 주세요."

        if "RESULT" in payload and "COOKRCP01" not in payload:
            err_info = payload.get("RESULT", {})
            return [], f"API 오류 ({err_info.get('CODE', '')}): {err_info.get('MSG', '인증키를 확인해 주세요.')}"

        root = payload.get("COOKRCP01", {})
        res_info = root.get("RESULT", {})
        code = res_info.get("CODE", "")

        if code and code != "INFO-000":
            return [], f"식품안전나라 안내 ({code}): {res_info.get('MSG', '요청 처리에 실패했습니다.')}"

        rows = root.get("row", [])
        if not rows:
            return [], "가져온 공개 레시피가 없습니다."

        recipes = []
        for row in rows:
            steps = []
            for i in range(1, 21):
                step = (row.get(f"MANUAL{i:02d}") or "").strip()
                if step:
                    step_clean = re.sub(r"^[0-9]+[\.\)]\s*", "", step).strip()
                    steps.append(step_clean if step_clean else step)

            raw_parts = row.get("RCP_PARTS_DTLS", "")
            recipes.append({
                "source": "식품안전나라 공개 레시피",
                "id": f"gov-{row.get('RCP_SEQ', '')}",
                "title": row.get("RCP_NM", "이름 없는 레시피"),
                "ingredient_text": raw_parts,
                "ingredients": split_ingredients(raw_parts),
                "steps": steps,
                "cook_minutes": 25,
                "method": row.get("RCP_WAY2", "일반 조리"),
                "category": row.get("RCP_PAT2", "기타"),
                "image": row.get("ATT_FILE_NO_MAIN", ""),
                "url": "https://www.foodsafetykorea.go.kr/",
                "creator": "식품의약품안전처",
                "user_created": False,
            })
        return recipes, None
    except requests.exceptions.SSLError:
        return [], "SSL 보안 연결 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    except requests.exceptions.Timeout:
        return [], "식품안전나라 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
    except requests.RequestException as e:
        return [], f"공개 레시피 서버 연결 실패: 네트워크 또는 방화벽 설정을 확인해 주세요. ({e})"
    except Exception as e:
        return [], f"레시피 데이터를 처리하는 중 예상치 못한 오류가 발생했습니다: {e}"


def match_recipe(recipe_ingredients, selected_names):
    """선택한 재료와 레시피 재료의 일치도 분석"""
    selected_norm = [norm(x) for x in selected_names if norm(x)]
    matched = []
    missing = []
    for item in recipe_ingredients:
        n = norm(item)
        if not n:
            continue
        if any(s in n or n in s for s in selected_norm):
            matched.append(item)
        else:
            missing.append(item)

    total_count = max(1, len(recipe_ingredients))
    score = len(matched) / total_count
    return matched, missing, score


# ---------- 귀엽고 따뜻한 게임풍 UI 스타일링 (CSS) ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800&family=Gaegu:wght@700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }

    /* 게임 스타일 상단 히어로 배너 */
    .game-banner {
        background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%);
        border-radius: 20px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.2rem;
        border: 3px solid #FFFFFF;
        box-shadow: 0 8px 24px rgba(149, 157, 165, 0.15);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .game-banner-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #2D3748;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .game-banner-sub {
        font-size: 0.95rem;
        color: #4A5568;
        margin-top: 0.25rem;
    }
    .game-stat-pill {
        background: rgba(255, 255, 255, 0.85);
        border: 2px solid #E2E8F0;
        border-radius: 14px;
        padding: 0.5rem 1rem;
        font-weight: 700;
        color: #2D3748;
        font-size: 0.9rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
    }

    /* 가상 냉장고 외관 */
    .fridge-container {
        background: #F0F4F8;
        border: 4px solid #CBD5E1;
        border-radius: 24px;
        padding: 16px;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.04), 0 10px 20px rgba(0,0,0,0.06);
    }
    .fridge-zone-header {
        font-size: 1.1rem;
        font-weight: 700;
        padding: 6px 12px;
        border-radius: 12px;
        display: inline-block;
        margin-bottom: 8px;
    }
    .zone-chilled { background: #E0F2FE; color: #0369A1; border: 1.5px solid #BAE6FD; }
    .zone-frozen { background: #EDE9FE; color: #6D28D9; border: 1.5px solid #DDD6FE; }
    .zone-room { background: #FEF3C7; color: #B45309; border: 1.5px solid #FDE68A; }

    .fridge-shelf {
        background: rgba(255, 255, 255, 0.65);
        border-radius: 16px;
        border: 2px dashed #CBD5E1;
        border-bottom: 6px solid #94A3B8;
        padding: 14px;
        margin-bottom: 18px;
        min-height: 110px;
    }

    /* 재료 아이템 카드 */
    .item-card {
        background: #FFFFFF;
        border: 2px solid #E2E8F0;
        border-radius: 16px;
        padding: 10px 12px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .item-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: #38BDF8;
    }
    .item-emoji {
        font-size: 2.2rem;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    .item-name {
        font-weight: 700;
        font-size: 1rem;
        color: #1E293B;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .item-qty {
        font-size: 0.8rem;
        color: #64748B;
        min-height: 1.1rem;
    }

    /* 유통기한 뱃지 */
    .badge-urgent, .badge-expired {
        background: #FEE2E2;
        color: #DC2626;
        border-radius: 8px;
        padding: 2px 6px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        margin-top: 4px;
    }
    .badge-warning {
        background: #FFEDD5;
        color: #EA580C;
        border-radius: 8px;
        padding: 2px 6px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        margin-top: 4px;
    }
    .badge-safe {
        background: #DCFCE7;
        color: #16A34A;
        border-radius: 8px;
        padding: 2px 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 4px;
    }
    .badge-neutral {
        background: #F1F5F9;
        color: #64748B;
        border-radius: 8px;
        padding: 2px 6px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-block;
        margin-top: 4px;
    }

    /* 알림 배너 */
    .urgent-banner {
        background: #FFF1F2;
        border-left: 5px solid #F43F5E;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 1rem;
        color: #9F1239;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)
