import os
import re
import json
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
    initial_sidebar_state="collapsed"
)

# ---------- 환경 및 경로 설정 ----------
APP_DIR = Path(__file__).resolve().parent
API_URL = "https://openapi.foodsafetykorea.go.kr/api"
# ---------- Supabase 연결 ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

if "supabase" not in st.session_state:
    st.session_state["supabase"] = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

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
                    "password": password
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
                        "password": new_password
                    })
                    st.success("회원가입 요청이 완료되었습니다. 이메일 인증이 필요할 수 있습니다.")
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
        return date.fromisoformat(str(value).strip())
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
        # 남은 특수문자나 군더더기 정리
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

    return result.data


def get_user_recipes():
    result = (
        supabase.table("user_recipes")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    return result.data


def get_total_creator_points():
    result = (
        supabase.table("user_recipes")
        .select("points_awarded")
        .execute()
    )

    return sum(
        int(row.get("points_awarded") or 0)
        for row in result.data
    )

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
    "케첩": "🥫", "마요네즈": "🥫", "잼": "🍯", "꿀": "🍯", "물": "💧", "만두": "🥟"
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

    # SSL 및 타임아웃 예외 처리 강화
    url = f"{API_URL}/{api_key}/COOKRCP01/json/{start}/{end}"
    try:
        response = requests.get(url, timeout=12)
        response.raise_for_status()

        # 식품안전나라 API 응답 파싱
        try:
            payload = response.json()
        except Exception:
            return [], "API 응답이 올바른 JSON 형식이 아닙니다. 인증키나 서비스 상태를 확인해 주세요."

        # 최상위 에러 체크 (예: {"RESULT": {"CODE": "INFO-100", "MSG": "인증키가 유효하지 않습니다."}})
        if "RESULT" in payload and "COOKRCP01" not in payload:
            err_info = payload.get("RESULT", {})
            return [], f"API 오류 ({err_info.get('CODE', '')}): {err_info.get('MSG', '인증키를 확인해 주세요.')}"

        root = payload.get("COOKRCP01", {})
        res_info = root.get("RESULT", {})
        code = res_info.get("CODE", "")

        # 정상 응답 코드는 주로 INFO-000
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
                    # 줄바꿈 및 번호 정리
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
                "cook_minutes": 25, # 공공 API에 시간 항목이 없을 경우 기본값
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
        # 양방향 부분 일치 검사
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
    .badge-urgent {
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

# ---------- 상단 대시보드 배너 ----------
ingredients_all = get_ingredients()
total_items_count = len(ingredients_all)
urgent_items = [
    x for x in ingredients_all
    if days_until(x["expiry_date"]) is not None and days_until(x["expiry_date"]) <= 3
]
total_points = get_total_creator_points()

st.markdown(f"""
<div class="game-banner">
  <div>
    <div class="game-banner-title">🥬 FoodFirst 레시피 팩토리</div>
    <div class="game-banner-sub">냉장고 속 재료를 구출하고, 창작 레시피로 요리 포인트를 모아보세요!</div>
  </div>
  <div style="display: flex; gap: 8px; flex-wrap: wrap;">
    <div class="game-stat-pill">🧊 보유 식재료: <span style="color:#0284C7;">{total_items_count}개</span></div>
    <div class="game-stat-pill">⏰ 소비 기한 임박: <span style="color:#E11D48;">{len(urgent_items)}개</span></div>
    <div class="game-stat-pill">✨ 내 창작 포인트: <span style="color:#D97706;">{total_points} P</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# 탭 메뉴
tab_fridge, tab_recipes, tab_creator, tab_settings = st.tabs(
    ["🧊 가상 냉장고", "🍳 재료 맞춤 레시피", "✨ 레시피 창작소", "⚙️ 설정 및 안내"]
)

# ==============================================================================
# TAB 1: 가상 냉장고
# ==============================================================================
with tab_fridge:
    # 기한 임박 경고 배너를 탭 상단에 강조 표시
    if urgent_items:
        urgent_text_list = []
        for x in urgent_items:
            lbl, _ = days_label(x["expiry_date"])
            urgent_text_list.append(f"<b>{x['name']}</b> ({lbl})")
        st.markdown(
            f"""
            <div class="urgent-banner">
                📢 <b>기한 확인 알림:</b> {', '.join(urgent_text_list)}<br>
                <span style="font-size:0.85rem; color:#881337;">
                ※ 유통기한·소비기한 날짜만으로 식품 안전을 완전히 보장할 수 없습니다. 섭취 전 냄새, 색상, 보관 상태를 반드시 육안으로 확인하세요.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    col_input, col_fridge = st.columns([1.1, 1.9], gap="large")

    # [좌측] 재료 등록 폼
    with col_input:
        st.subheader("➕ 식재료 넣기")
        st.caption("새로운 식재료를 가상 냉장고에 추가합니다.")

        # 사진 업로드 (AI 미구현 명시 안내)
        with st.expander("📷 식재료 사진 첨부 (선택)", expanded=False):
            photo = st.file_uploader(
                "식재료 또는 냉장고 사진",
                type=["png", "jpg", "jpeg"],
                key="fridge_photo_uploader",
                help="현재 버전은 사진 자동 인식 모델이 탑재되지 않았습니다. 사진을 보면서 아래 폼에 재료명을 직접 입력해 주세요."
            )
            if photo:
                st.image(photo, caption="첨부된 사진", use_container_width=True)
                st.info("💡 사진 속 재료의 이름과 수량을 아래 입력창에 직접 작성해 주세요.")

                        with st.form("form_add_ingredient", clear_on_submit=True):
            f_name = st.text_input("식재료 이름 *", placeholder="예: 두부, 양파, 계란, 소고기")
            f_qty = st.text_input("수량 / 메모", placeholder="예: 1모, 반 개, 500g")
            f_loc = st.selectbox("보관 위치 *", ["냉장실", "냉동실", "실온"])
            f_exp = st.date_input("유통/소비기한 (선택)", value=None, format="YYYY-MM-DD")

            add_submit = st.form_submit_button(
                "냉장고에 쏙 넣기 📥",
                use_container_width=True,
                type="primary"
            )
            f_qty = st.text_input("수량 / 메모", placeholder="예: 1모, 반 개, 500g")
            f_loc = st.selectbox("보관 위치 *", ["냉장실", "냉동실", "실온"])
            f_exp = st.date_input("유통/소비기한 (선택)", value=None, format="YYYY-MM-DD")

            add_submit = st.form_submit_button(
                "냉장고에 쏙 넣기 📥",
                use_container_width=True,
                type="primary"
            )

        if add_submit:
            if not f_name or not f_name.strip():
                st.error("식재료 이름을 입력해 주세요!")
            else:
                exp_str = f_exp.isoformat() if f_exp else ""
                photo_name = photo.name if photo else ""

                try:
                    supabase.table("ingredients").insert({
                        "user_id": str(st.session_state["user"].id),
                        "name": f_name.strip(),
                        "quantity": f_qty.strip(),
                        "location": f_loc,
                        "expiry_date": exp_str,
                        "image_name": photo_name,
                        "created_at": datetime.now().isoformat(timespec="seconds")
                    }).execute()

                    st.toast(f"'{f_name.strip()}' 재료를 {f_loc}에 넣었습니다! ✨")
                    st.rerun()

                except Exception as e:
                    st.error(f"식재료 저장에 실패했습니다: {e}")

        # [재료 수정/삭제 섹션] - 선택되었을 때만 표시
        manage_id = st.session_state.get("manage_item_id")
        if manage_id:
            target_item = next((x for x in ingredients_all if x["id"] == manage_id), None)
            if target_item:
                st.markdown("---")
                st.markdown(f"### ✏️ '{target_item['name']}' 정보 수정")
                with st.form(f"form_edit_item_{manage_id}"):
                    e_name = st.text_input("식재료 이름", value=target_item["name"])
                    e_qty = st.text_input("수량 / 메모", value=target_item["quantity"] or "")
                    
                    loc_options = ["냉장실", "냉동실", "실온"]
                    cur_loc_idx = loc_options.index(target_item["location"]) if target_item["location"] in loc_options else 0
                    e_loc = st.selectbox("보관 위치", loc_options, index=cur_loc_idx)
                    
                    cur_exp = parse_date(target_item["expiry_date"])
                    e_exp = st.date_input("유통/소비기한", value=cur_exp, format="YYYY-MM-DD")

                    col_save, col_del, col_cancel = st.columns([1, 1, 1])
                    btn_save = col_save.form_submit_button("저장", type="primary", use_container_width=True)
                    btn_del = col_del.form_submit_button("삭제", use_container_width=True)
                    btn_cancel = col_cancel.form_submit_button("닫기", use_container_width=True)

                                      if btn_save:
                        if not e_name.strip():
                            st.error("재료 이름을 입력해 주세요.")
                        else:
                            exp_val = e_exp.isoformat() if e_exp else ""

                            try:
                                supabase.table("ingredients").update({
                                    "name": e_name.strip(),
                                    "quantity": e_qty.strip(),
                                    "location": e_loc,
                                    "expiry_date": exp_val
                                }).eq(
                                    "id", manage_id
                                ).eq(
                                    "user_id", str(st.session_state["user"].id)
                                ).execute()

                                st.session_state.pop("manage_item_id", None)
                                st.toast("재료 정보가 수정되었습니다.")
                                st.rerun()

                            except Exception as e:
                                st.error(f"재료 수정에 실패했습니다: {e}")

                    if btn_del:
                        try:
                            supabase.table("ingredients").delete().eq(
                                "id", manage_id
                            ).eq(
                                "user_id", str(st.session_state["user"].id)
                            ).execute()

                            st.session_state.pop("manage_item_id", None)
                            st.toast("재료가 삭제되었습니다.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"재료 삭제에 실패했습니다: {e}")

                    if btn_cancel:
                        st.session_state.pop("manage_item_id", None)
                        st.rerun()
    # [우측] 시각화된 가상 냉장고 (게임 인벤토리 뷰)
    with col_fridge:
        st.subheader("🧊 내 가상 냉장고 현황")
        st.caption("구역별 식재료를 확인하고, 카드를 눌러 수정하거나 삭제하세요.")

        if not ingredients_all:
            st.info("💡 냉장고가 비어있어요! 왼쪽에서 재료를 등록해 보세요.")
        else:
            st.markdown('<div class="fridge-container">', unsafe_allow_html=True)
            zones = [
                ("냉장실", "zone-chilled", "❄️ 냉장실 (신선 보관)"),
                ("냉동실", "zone-frozen", "🧊 냉동실 (장기 보관)"),
                ("실온", "zone-room", "🧺 실온 / 팬트리 (건조 보관)")
            ]

            for loc_key, zone_css, zone_title in zones:
                zone_items = [x for x in ingredients_all if x["location"] == loc_key]
                st.markdown(f'<div class="fridge-zone-header {zone_css}">{zone_title} ({len(zone_items)})</div>', unsafe_allow_html=True)
                st.markdown('<div class="fridge-shelf">', unsafe_allow_html=True)

                if zone_items:
                    # 3열 반응형 그리드
                    grid_cols = st.columns(3)
                    for idx, item in enumerate(zone_items):
                        c = grid_cols[idx % 3]
                        with c:
                            emoji = get_ingredient_emoji(item["name"])
                            lbl, badge_cls = days_label(item["expiry_date"])
                            qty_display = item["quantity"] if item["quantity"] else "수량 미기재"

                            # HTML 카드 렌더링
                            st.markdown(f"""
                            <div class="item-card">
                                <div class="item-emoji">{emoji}</div>
                                <div class="item-name" title="{item['name']}">{item['name']}</div>
                                <div class="item-qty">{qty_display}</div>
                                <div><span class="badge-{badge_cls}">{lbl}</span></div>
                            </div>
                            """, unsafe_allow_html=True)

                            # 관리 버튼
                            if st.button("수정 / 삭제", key=f"btn_manage_{item['id']}", use_container_width=True):
                                st.session_state["manage_item_id"] = item["id"]
                                st.rerun()
                else:
                    st.markdown("<p style='color:#94A3B8; font-size:0.9rem; margin:10px 0;'>보관 중인 재료가 없습니다.</p>", unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# TAB 2: 재료 맞춤 레시피 찾기
# ==============================================================================
with tab_recipes:
    st.subheader("🍳 냉장고 속 재료로 무엇을 만들까요?")
    st.caption("선택한 재료가 포함된 공공 레시피와 사용자 창작 레시피를 추천해 드립니다.")

    # 1. 냉장고 식재료 선택 바
    ing_names = [x["name"] for x in ingredients_all]
    
    col_sel, col_quick = st.columns([3, 1])
    with col_sel:
        selected_ingredients = st.multiselect(
            "요리에 사용할 냉장고 재료를 선택하세요:",
            options=ing_names,
            default=st.session_state.get("selected_ingredients_cache", []),
            placeholder="재료를 선택하세요 (다중 선택 가능)"
        )
        st.session_state["selected_ingredients_cache"] = selected_ingredients

    with col_quick:
        st.write("") # 간격 맞춤
        col_q1, col_q2 = st.columns(2)
        if col_q1.button("모두 선택", use_container_width=True):
            st.session_state["selected_ingredients_cache"] = ing_names
            st.rerun()
        if col_q2.button("선택 해제", use_container_width=True):
            st.session_state["selected_ingredients_cache"] = []
            st.rerun()

    # 2. 공개 레시피 API 연동 영역 (환경변수 또는 사용자 입력)
    env_api_key = os.environ.get("FOOD_SAFETY_API_KEY", "")
    with st.expander("🌐 식품안전나라 공개 레시피 API 설정", expanded=False):
        st.markdown("""
        식품의약품안전처 **'조리식품의 레시피 DB'** 공식 API를 연결할 수 있습니다.  
        인증키가 없어도 **사용자 창작 레시피**는 자유롭게 검색하고 이용할 수 있습니다.
        """)
        api_key_input = st.text_input(
            "공개 API 인증키",
            value=env_api_key,
            type="password",
            key="food_safety_api_key_input",
            help="공식 웹사이트(foodsafetykorea.go.kr)에서 발급받은 인증키를 입력하세요."
        )
        c_count, c_fetch = st.columns([1, 1])
        req_count = c_count.selectbox("불러올 레시피 수", [30, 50, 100], index=1)
        btn_fetch_api = c_fetch.button("공개 레시피 불러오기", type="primary", use_container_width=True)

        if btn_fetch_api:
            with st.spinner("식품안전나라에서 공공 레시피를 가져오는 중..."):
                fetched_data, err_msg = fetch_public_recipes(api_key_input.strip(), 1, req_count)
                st.session_state["public_recipes"] = fetched_data
                st.session_state["public_recipes_error"] = err_msg
            if err_msg:
                st.warning(err_msg)
            else:
                st.success(f"공개 레시피 {len(fetched_data)}건을 성공적으로 불러왔습니다!")

    # API 에러 안내 (인증키 미입력 상태는 정상 fallback으로 처리)
    api_error = st.session_state.get("public_recipes_error")
    if api_error and api_key_input:
        st.info(f"ℹ️ {api_error}")

    # 3. 레시피 데이터 수집 (공개 레시피 + 사용자 창작 레시피)
    public_recipes = st.session_state.get("public_recipes", [])
    user_recipes_raw = get_user_recipes()

    combined_recipes = []
    # 공공 레시피 추가
    for r in public_recipes:
        combined_recipes.append(r)

    # 사용자 창작 레시피 추가
    for ur in user_recipes_raw:
        parsed_steps = [s.strip() for s in str(ur["steps"]).splitlines() if s.strip()]
        combined_recipes.append({
            "source": "FoodFirst 사용자 창작",
            "id": f"user-{ur['id']}",
            "title": ur["title"],
            "ingredient_text": ur["ingredients"],
            "ingredients": split_ingredients(ur["ingredients"]),
            "steps": parsed_steps,
            "cook_minutes": ur["cook_minutes"] or 20,
            "method": f"약 {ur['cook_minutes'] or 20}분 소요",
            "category": "사용자 창작",
            "image": "",
            "url": "",
            "creator": ur["creator"],
            "user_created": True,
            "user_id": ur["id"],
            "uses": ur["uses"],
            "points_awarded": ur["points_awarded"],
        })

    # 4. 정렬 및 필터링 옵션
    if not combined_recipes:
        st.info("💡 등록된 레시피가 없습니다. '✨ 레시피 창작소' 탭에서 나만의 레시피를 직접 등록해 보세요!")
    else:
        # 매칭 점수 계산
        scored_recipes = []
        for r in combined_recipes:
            matched, missing, score = match_recipe(r["ingredients"], selected_ingredients)
            # 재료를 선택한 경우 매칭된 재료가 1개 이상 있는 레시피만 우선 추천
            if selected_ingredients:
                if matched:
                    scored_recipes.append({
                        "recipe": r,
                        "matched": matched,
                        "missing": missing,
                        "score": score,
                        "match_count": len(matched),
                        "missing_count": len(missing),
                        "cook_minutes": r.get("cook_minutes", 20)
                    })
            else:
                scored_recipes.append({
                    "recipe": r,
                    "matched": [],
                    "missing": r["ingredients"],
                    "score": 0.0,
                    "match_count": 0,
                    "missing_count": len(r["ingredients"]),
                    "cook_minutes": r.get("cook_minutes", 20)
                })

        col_count_info, col_sort = st.columns([2, 1])
        with col_count_info:
            st.markdown(f"**총 {len(scored_recipes)}개의 요리법** (공공 레시피 {len(public_recipes)}개 + 창작 레시피 {len(user_recipes_raw)}개)")
        with col_sort:
            sort_criterion = st.selectbox(
                "정렬 기준",
                ["재료 일치율 높은 순", "보유 재료 많은 순", "추가 재료 적은 순", "조리 시간 짧은 순"],
                index=0
            )

        # 정렬 수행
        if sort_criterion == "재료 일치율 높은 순":
            scored_recipes.sort(key=lambda x: (x["score"], x["match_count"]), reverse=True)
        elif sort_criterion == "보유 재료 많은 순":
            scored_recipes.sort(key=lambda x: (x["match_count"], x["score"]), reverse=True)
        elif sort_criterion == "추가 재료 적은 순":
            scored_recipes.sort(key=lambda x: (x["missing_count"], -x["match_count"]))
        elif sort_criterion == "조리 시간 짧은 순":
            scored_recipes.sort(key=lambda x: x["cook_minutes"])

        # 5. 레시피 카드 목록 출력
        for item in scored_recipes[:30]:
            r = item["recipe"]
            matched = item["matched"]
            missing = item["missing"]
            score = item["score"]

            with st.container(border=True):
                c_img, c_detail = st.columns([1, 3.5], gap="medium")
                with c_img:
                    if r.get("image"):
                        st.image(r["image"], use_container_width=True)
                    else:
                        st.markdown("<div style='font-size:4rem; text-align:center; padding:10px;'>🍲</div>", unsafe_allow_html=True)
                    
                    if r.get("user_created"):
                        st.markdown("<div style='text-align:center;'><span style='background:#FEF3C7; color:#B45309; padding:3px 8px; border-radius:8px; font-weight:700; font-size:0.8rem;'>⭐ 창작 레시피</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:center;'><span style='background:#E0F2FE; color:#0369A1; padding:3px 8px; border-radius:8px; font-weight:600; font-size:0.8rem;'>🏛️ 공공 DB</span></div>", unsafe_allow_html=True)

                with c_detail:
                    st.markdown(f"### {r['title']}")
                    st.caption(f"작성자: {r.get('creator', '익명')} | 조리방법: {r.get('method', '일반')} | 분류: {r.get('category', '요리')}")

                    if selected_ingredients:
                        st.progress(min(1.0, score), text=f"보유 재료 일치율: {score:.0%} ({len(matched)}/{len(r['ingredients'])}개)")

                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            matched_badges = " ".join([f"`{m}`" for m in matched]) if matched else "_일치 재료 없음_"
                            st.markdown(f"**🟢 있는 재료:** {matched_badges}")
                        with col_m2:
                            missing_sample = missing[:6]
                            missing_badges = " ".join([f"`{m}`" for m in missing_sample]) if missing_sample else "_추가 재료 없음_"
                            st.markdown(f"**⚪ 추가 필요 재료:** {missing_badges}")

                    with st.expander("📖 재료 목록 및 조리 순서 확인하기", expanded=False):
                        st.markdown("**[필요 재료 원문]**")
                        st.write(r.get("ingredient_text", "재료 정보가 없습니다."))

                        st.markdown("**[조리 순서]**")
                        steps = r.get("steps", [])
                        if steps:
                            for idx, s in enumerate(steps, 1):
                                st.write(f"**{idx}.** {s}")
                        else:
                            st.write("등록된 조리 순서가 없습니다.")

                        if r.get("url"):
                            st.markdown(f"[🔗 공식 출처 방문]({r['url']})")

                    # 사용자 창작 레시피일 경우 '만들어 봤어요' 보상 버튼 제공
                    if r.get("user_created"):
                        c_stat, c_action = st.columns([2, 1])
                        c_stat.caption(f"🍳 다른 사용자가 만들어 본 횟수: **{r.get('uses', 0)}회** | 적립된 창작 포인트: **{r.get('points_awarded', 0)} P**")
                       if c_action.button("이 레시피를 만들어 봤어요 (+5P) 💖", key=f"btn_used_{r['user_id']}", use_container_width=True):
    try:
        supabase.rpc(
            "record_recipe_action",
            {"p_recipe_id": int(r["user_id"])}
        ).execute()

        st.toast("요리 활용 완료! 창작자에게 5 포인트가 지급되었습니다! 🎉")
        st.rerun()

    except Exception as e:
        st.error(f"요리 활용 기록에 실패했습니다: {e}")

# ==============================================================================
# TAB 3: 레시피 창작소 (사용자 창작 레시피 등록 & 보상)
# ==============================================================================
with tab_creator:
    st.subheader("✨ 나만의 창작 레시피 등록")
    st.markdown("""
    직접 개발한 요리법이나 나만의 꿀조합을 공유해 보세요!  
    다른 사용자가 내 레시피를 보고 **'만들어 봤어요'**를 누를 때마다 **창작 포인트(+5P)**가 적립됩니다.
    """)

    col_create_form, col_my_list = st.columns([1.1, 1], gap="large")

    with col_create_form:
        st.markdown("#### 📝 새 레시피 작성")
        with st.form("form_create_user_recipe", clear_on_submit=True):
            cr_author = st.text_input("창작자 닉네임 *", value="나", placeholder="예: 요리꿈나무")
            cr_title = st.text_input("레시피 이름 *", placeholder="예: 남은 채소와 두부로 만든 두부스테이크")
            cr_ingredients = st.text_area(
                "재료 목록 * (쉼표 또는 줄바꿈으로 구분)",
                placeholder="예: 두부 1모, 양파 1/2개, 대파 1대, 간장 2큰술, 참기름 1큰술",
                height=110
            )
            cr_steps = st.text_area(
                "조리 순서 * (한 줄에 한 단계씩 작성)",
                placeholder="1. 두부는 물기를 빼고 으깬다.\n2. 양파와 대파를 잘게 다져 두부와 섞는다.\n3. 팬에 노릇하게 굽고 양념장을 곁들인다.",
                height=150
            )
            cr_minutes = st.number_input("예상 조리 시간 (분)", min_value=1, max_value=300, value=20)
            
            st.markdown("---")
            cr_consent = st.checkbox(
                "내가 직접 작성했거나 공유 권한이 있는 콘텐츠이며, 타인의 글·사진을 무단 도용하지 않았음을 확인합니다. (필수)",
                value=False
            )

            submit_recipe = st.form_submit_button("레시피 등록하고 포인트 받기 🚀", type="primary", use_container_width=True)

            if submit_recipe:
                if not cr_title.strip() or not cr_ingredients.strip() or not cr_steps.strip():
                    st.error("레시피 이름, 재료 목록, 조리 순서를 모두 입력해 주세요.")
                elif not cr_consent:
                    st.error("저작권 및 공유 권한 동의 확인란에 체크해 주세요.")
                else:
                                        try:
                        supabase.table("user_recipes").insert({
                            "user_id": str(st.session_state["user"].id),
                            "title": cr_title.strip(),
                            "ingredients": cr_ingredients.strip(),
                            "steps": cr_steps.strip(),
                            "cook_minutes": int(cr_minutes),
                            "creator": cr_author.strip() or "익명",
                            "created_at": datetime.now().isoformat(timespec="seconds"),
                            "points_awarded": 10
                        }).execute()

                        st.toast(f"'{cr_title.strip()}' 레시피가 등록되었습니다! 최초 등록 보너스 10P 지급! 🎉")
                        st.rerun()

                    except Exception as e:
                        st.error(f"레시피 등록에 실패했습니다: {e}")

    with col_my_list:
        st.markdown("#### 🏆 내가 등록한 레시피 & 보상 현황")
        my_recipes = get_user_recipes()

        if not my_recipes:
            st.info("아직 등록된 창작 레시피가 없습니다. 왼쪽 폼에서 첫 번째 레시피를 공유해 보세요!")
        else:
            for ur in my_recipes:
                with st.container(border=True):
                    c_title, c_del = st.columns([3, 1])
                    c_title.markdown(f"**{ur['title']}**")
                                       if c_del.button("삭제", key=f"btn_del_ur_{ur['id']}", use_container_width=True):
                        try:
                            supabase.table("user_recipes").delete().eq(
                                "id", ur["id"]
                            ).eq(
                                "user_id", str(st.session_state["user"].id)
                            ).execute()

                            supabase.table("recipe_actions").delete().eq(
                                "recipe_id", ur["id"]
                            ).eq(
                                "user_id", str(st.session_state["user"].id)
                            ).execute()

                            st.toast("레시피가 삭제되었습니다.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"레시피 삭제에 실패했습니다: {e}")

                    st.caption(f"👤 창작자: {ur['creator']} | ⏱️ {ur['cook_minutes']}분 | 📅 등록일: {ur['created_at'][:10]}")
                    
                    # 포인트 뱃지
                    st.markdown(f"""
                    <div style="background:#FEF3C7; border:1px solid #FCD34D; border-radius:10px; padding:6px 12px; margin:6px 0; font-size:0.88rem; color:#92400E;">
                        🍳 다른 사용자 활용: <b>{ur['uses']}회</b> &nbsp;|&nbsp; 💰 획득 포인트: <b>{ur['points_awarded']} P</b>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"<span style='font-size:0.85rem; color:#475569;'><b>재료:</b> {ur['ingredients']}</span>", unsafe_allow_html=True)

                    with st.expander("조리 단계 보기"):
                        st.write(ur["steps"])

# ==============================================================================
# TAB 4: 설정 및 안내
# ==============================================================================
with tab_settings:
    st.subheader("⚙️ 시스템 설정 및 프로젝트 안내")

    col_info, col_manage = st.columns([1.2, 1], gap="large")

    with col_info:
        st.markdown("""
        #### 📌 FoodFirst 서비스 개요
        FoodFirst는 가상의 게임형 냉장고에서 식재료를 시각적으로 관리하고, 기한 임박 재료를 구출하며, 
        나만의 레시피를 공유해 포인트를 적립하는 친환경 식재료 관리 웹 애플리케이션입니다.

        ---
        #### 🛡️ 식품 안전 및 저작권 안내
        - **식품 안전 주의:** 본 앱의 유통기한·소비기한 알림은 단순 날짜 비교에 의한 참고 정보입니다. 보관 온도, 개봉 여부, 냄새, 색상에 따라 상태가 다를 수 있으므로 섭취 전 반드시 식품 상태를 직접 확인하세요.
        - **저작권 및 출처:** 공공 레시피는 식품의약품안전처 '식품안전나라 조리식품의 레시피 DB'를 기반으로 합니다. 사용자가 직접 등록하는 레시피는 본인 저작물이거나 공유 가능한 콘텐츠여야 합니다.
        - **포인트 정책:** 현재 버전의 포인트는 교육 및 프로토타입 시연용 가상 점수입니다. 실제 서비스 환경에서는 중복 및 어뷰징 방지, 본인 인증, 신고 및 검수 시스템이 필요합니다.
        """)

    with col_manage:
        st.markdown("#### 💾 로컬 데이터베이스 상태")
        db_size_kb = (DB_PATH.stat().st_size / 1024) if DB_PATH.exists() else 0
        st.markdown(f"""
        - **데이터베이스 파일 위치:** `{DB_PATH.name}`
        - **파일 용량:** `{db_size_kb:.1f} KB`
        - **등록된 냉장고 재료:** `{len(ingredients_all)} 건`
        - **사용자 창작 레시피:** `{len(get_user_recipes())} 건`
        """)

        st.markdown("---")
        st.markdown("#### ⚠️ 데이터 초기화 (주의)")
        st.caption("주의: 로컬 SQLite 데이터베이스의 모든 재료 및 사용자 레시피가 영구 삭제됩니다.")

        confirm_reset = st.checkbox("데이터 초기화에 동의하며, 복구할 수 없음을 이해했습니다.", key="chk_db_reset")
       if st.button("모든 로컬 데이터 초기화", type="secondary", disabled=not confirm_reset):
    try:
        user_id = str(st.session_state["user"].id)

        supabase.table("ingredients").delete().eq(
            "user_id", user_id
        ).execute()

        supabase.table("user_recipes").delete().eq(
            "user_id", user_id
        ).execute()

        supabase.table("recipe_actions").delete().eq(
            "user_id", user_id
        ).execute()

        st.session_state.pop("public_recipes", None)
        st.session_state.pop("selected_ingredients_cache", None)
        st.session_state.pop("manage_item_id", None)

        st.success("내 데이터가 초기화되었습니다.")
        st.rerun()

    except Exception as e:
        st.error(f"데이터 초기화에 실패했습니다: {e}")
