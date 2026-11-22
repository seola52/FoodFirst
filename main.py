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


def show_auth():
    st.title("🧊 FoodFirst")
    st.subheader("나만의 냉장고를 관리해 보세요!")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_password")
        if st.button("로그인", use_container_width=True):
            if not email.strip() or not password:
                st.warning("이메일과 비밀번호를 입력해 주세요.")
            else:
                try:
                    result = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                    st.session_state["user"] = result.user
                    st.session_state["user_email"] = result.user.email or email.strip()
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 오류: {e}")

    with tab2:
        new_email = st.text_input("이메일", key="signup_email")
        new_password = st.text_input("비밀번호 (6자 이상)", type="password", key="signup_password")
        if st.button("회원가입", use_container_width=True):
            if not new_email.strip():
                st.error("이메일을 입력해 주세요.")
            elif len(new_password) < 6:
                st.error("비밀번호는 6자 이상 입력해 주세요.")
            else:
                try:
                    result = supabase.auth.sign_up({"email": new_email.strip(), "password": new_password})
                    if result.session:
                        st.success("회원가입이 완료되었습니다. 로그인해 주세요.")
                    else:
                        st.success("회원가입 요청이 완료되었습니다. 이메일 인증 후 로그인해 주세요.")
                except Exception as e:
                    st.error(f"회원가입 오류: {e}")


if st.session_state["user"] is None:
    show_auth()
    st.stop()

st.sidebar.success(f"로그인: {st.session_state['user_email']}")
if st.sidebar.button("로그아웃"):
    try:
        supabase.auth.sign_out()
    finally:
        st.session_state["user"] = None
        st.session_state["user_email"] = ""
        st.rerun()

CURRENT_USER_ID = str(st.session_state["user"].id)

def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except Exception:
