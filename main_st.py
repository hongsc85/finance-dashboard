# main_st.py

import datetime as dt
import time
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
import FinanceDataReader as fdr
from urllib.parse import quote

# ==================================================================
# 기본 UI 설정
# ==================================================================
st.set_page_config(page_title="실시간 금융 대시보드", layout="wide")
st.title("📈 실시간 금융 대시보드")
st.caption("데이터 출처: 네이버금융 · FinanceDataReader · Investing.com")


HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
}


# ==================================================================
# 자동 새로고침 설정
# ==================================================================
st.sidebar.header("⚙ 설정")
refresh_interval = st.sidebar.selectbox(
    "⏱ 자동 새로고침 주기",
    ("수동", "10초", "30초", "60초"),
    index=0,
    key="auto_refresh_key"
)

interval_map = {
    "수동": 0,
    "10초": 10,
    "30초": 30,
    "60초": 60,
}

if interval_map[refresh_interval] > 0:
    time.sleep(interval_map[refresh_interval])
    st.rerun()


# ==================================================================
# 데이터 수집 함수들
# ==================================================================

# 1. 네이버 환율 스냅샷
def get_fx_snapshot():
    url = "https://finance.naver.com/marketindex/"
    html = requests.get(url, headers=HEADERS).text
    soup = BeautifulSoup(html, "lxml")

    result = {}

    names = soup.select("h3.h_lst span.blind")
    values = soup.select(".value")

    for n, v in zip(names, values):
        if "미국 USD" in n.text:
            result["USD/KRW"] = v.text
        elif "일본 JPY" in n.text:
            result["JPY/100KRW"] = v.text
        elif "유럽연합 EUR" in n.text:
            result["EUR/KRW"] = v.text
        elif "중국 CNY" in n.text:
            result["CNY/KRW"] = v.text

    return result


# 2. 국내 지수
def get_korea_index():
    url = "https://finance.naver.com/sise/"
    html = requests.get(url, headers=HEADERS).text
    soup = BeautifulSoup(html, "lxml")

    data = {}

    kospi = soup.select_one("#KOSPI_now").text
    kospi_chg = soup.select_one("#KOSPI_change").contents[2].strip()

    kosdaq = soup.select_one("#KOSDAQ_now").text
    kosdaq_chg = soup.select_one("#KOSDAQ_change").contents[2].strip()

    data["KOSPI"] = (kospi, kospi_chg)
    data["KOSDAQ"] = (kosdaq, kosdaq_chg)

    return data


# 3. 미국 지수
def get_us_index():
    today = dt.date.today()
    start = today - dt.timedelta(days=10)

    symbols = {"다우지수": "DJI", "나스닥": "IXIC", "S&P500": "US500"}

    result = {}

    for name, code in symbols.items():
        try:
            df = fdr.DataReader(code, start, today)
            last = df.iloc[-1]["Close"]
            prev = df.iloc[-2]["Close"]
            diff = last - prev
            pct = diff / prev * 100
            result[name] = (f"{last:,.2f}", f"{diff:+.2f} ({pct:+.2f}%)")
        except:
            result[name] = ("-", "-")

    return result


# ==================================================================
# 종목명 → 코드 검색 (FDR 기반)
# ==================================================================
def find_stock_code(keyword):
    df = fdr.StockListing('KRX')  # KOSPI + KOSDAQ + KONEX 전체
    result = df[df['Name'].str.contains(keyword, case=False, na=False)]

    if len(result) == 0:
        return None, None

    row = result.iloc[0]
    return row['Name'], row['Code']


# 개별 종목 차트
def load_stock_chart(code):
    today = dt.date.today()
    start = today - dt.timedelta(days=90)
    df = fdr.DataReader(code, start, today)
    return df


# ==================================================================
# UI Tabs
# ==================================================================
tab_summary, tab_search = st.tabs(["📊 요약 (카드형 UI)", "🔍 종목 검색"])

# ==================================================================
# TAB 1: 카드형 UI
# ==================================================================
with tab_summary:

    st.subheader("📌 시장 요약 정보")

    col1, col2, col3 = st.columns(3)

    # 1) 카드: 환율
    with col1:
        st.markdown("### 🌏 환율")
        fx = get_fx_snapshot()
        for k, v in fx.items():
            st.metric(k, v)
        st.markdown("---")

    # 2) 카드: 국내 지수
    with col2:
        st.markdown("### 🇰🇷 국내 지수")
        idx = get_korea_index()
        for name, (val, chg) in idx.items():
            st.metric(name, val, chg)
        st.markdown("---")

    # 3) 카드: 미국 지수
    with col3:
        st.markdown("### 🇺🇸 미국 지수")
        us_idx = get_us_index()
        for name, (val, chg) in us_idx.items():
            st.metric(name, val, chg)
        st.markdown("---")


# ==================================================================
# TAB 2: 종목 검색
# ==================================================================
with tab_search:

    st.subheader("🔍 네이버 종목 검색 (FDR 기반)")

    keyword = st.text_input("종목명 입력", placeholder="예: 삼성전자, 카카오, 넷플릭스, 테슬라")

    if st.button("검색"):

        name, code = find_stock_code(keyword)

        if not code:
            st.error("❌ 종목을 찾을 수 없습니다. 정확한 이름으로 다시 입력하세요.")
        else:
            st.success(f"✔ {name} ({code}) 검색됨")

            df = load_stock_chart(code)

            last = df.iloc[-1]["Close"]
            prev = df.iloc[-2]["Close"]
            diff = last - prev
            pct = diff / prev * 100

            st.metric("현재가", f"{last:,.2f}", f"{diff:+.2f} ({pct:+.2f}%)")

            st.line_chart(df["Close"])
            st.dataframe(df.tail(10))
