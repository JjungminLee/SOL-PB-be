from fastapi import  Response
from fastapi import APIRouter
from ics import Calendar, Event
from datetime import datetime, timedelta
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep
import re


router = APIRouter()


def get_safe_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

# 청약홈 일정 스크래핑
def scrape_applyhome_calendar() -> List[Dict]:
    driver = get_safe_chrome_driver()
    driver.get("https://www.applyhome.co.kr/ai/aib/selectSubscrptCalenderView.do")

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "calTable")))
        sleep(2)

        notices = []
        cells = driver.find_elements(By.CSS_SELECTOR, "#calTable tbody td")

        year = driver.find_element(By.ID, "sel_year").get_attribute("value")
        month = driver.find_element(By.CSS_SELECTOR, ".cal_bottom .active").get_attribute("data-val")

        for cell in cells:
            day = cell.get_attribute("data-ids")
            if not day:
                continue

            links = cell.find_elements(By.TAG_NAME, "a")
            if not links:
                continue

            date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            for a in links:
                title = a.find_element(By.TAG_NAME, "span").text.strip()
                url = a.get_attribute("href") or "https://www.applyhome.co.kr"
                notices.append({
                    "title": title,
                    "region": "전국",
                    "income_limit": 99999,
                    "url": url,
                    "start_date": date,
                    "end_date": date
                })
        return notices

    except Exception as e:
        print("[❌ applyhome] 스크래핑 실패:", e)
        return []
    finally:
        driver.quit()

#  마이홈 신혼부부 공고 스크래핑
def scrape_myhome_newlywed_notices() -> List[Dict]:
    url = "https://www.myhome.go.kr/hws/portal/sch/selectRsdtRcritNtcView.do"
    driver = get_safe_chrome_driver()
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "searchTyId")))
        # 신혼부부 버튼 강제 클릭 스크립트
        driver.execute_script("document.querySelector('input[name=searchTyId][value=FIXES100002]').click()")
        # dom에 그려지기까지 시간 두기
        driver.execute_script("fnSearch('1')")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".tb-list.list-announce tbody tr"))
        )
        sleep(1)

        notices = []
        rows = driver.find_elements(By.CSS_SELECTOR, ".tb-list.list-announce tbody tr")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 2:
                continue

            lines = cols[1].text.strip().split("\n")
            if len(lines) < 2:
                continue

            region = lines[0].strip()
            title = lines[1].strip()

            date_match = next((l.strip() for l in lines if re.match(r"\d{4}-\d{2}-\d{2}", l.strip())), None)
            if not date_match:
                continue

            try:
                start_date = datetime.strptime(date_match, "%Y-%m-%d").date()
            except ValueError:
                continue

            notices.append({
                "title": f"[신혼부부] {title}",
                "start_date": str(start_date),
                "end_date": str(start_date),
                "region": region,
                "income_limit": 99999,
            })

        return notices

    except Exception as e:
        print("[❌ myhome] 스크래핑 실패:", e)
        return []
    finally:
        driver.quit()


# 이번 주 필터링
def get_current_week_range():
    today = datetime.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.date(), end.date()

def filter_by_week(notices: List[Dict]) -> List[Dict]:
    start, end = get_current_week_range()
    return [
        notice for notice in notices
        if start <= datetime.strptime(notice["start_date"], "%Y-%m-%d").date() <= end
    ]

# ICS 변환
def create_ics_content(notices: List[Dict]) -> str:
    cal = Calendar()
    for notice in notices:
        e = Event()
        e.name = notice["title"]
        e.begin = notice["start_date"]
        e.end = notice["start_date"]
        e.url = notice.get("url", "")
        e.description = "청약 일정입니다."
        cal.events.add(e)
    return str(cal)

# API 라우터
@router.get("/calendar")
def get_combined_calendar():
    applyhome = scrape_applyhome_calendar()
    myhome = scrape_myhome_newlywed_notices()
    combined = applyhome + myhome
    weekly = filter_by_week(combined)
    ics_content = create_ics_content(weekly)
    return Response(content=ics_content, media_type="text/calendar")
