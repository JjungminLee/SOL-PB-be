from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from time import sleep
import re

# 공통 Chrome Driver 설정
def get_safe_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

# [1] 청약홈 일정 스크래핑
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
                try:
                    title = a.find_element(By.TAG_NAME, "span").text.strip()
                except:
                    continue
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

# [2] 마이홈 공고 스크래핑
def scrape_myhome_notices() -> List[Dict]:
    url = "https://www.myhome.go.kr/hws/portal/sch/selectRsdtRcritNtcView.do"
    driver = get_safe_chrome_driver()
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "searchTyId")))
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

# [3] 이번 주 범위 계산
def get_current_week_range():
    today = datetime.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.date(), end.date()

# [4] 주간 공고 필터링
def filter_by_week(notices: List[Dict]) -> List[Dict]:
    start, end = get_current_week_range()
    return [
        notice for notice in notices
        if start <= datetime.strptime(notice["start_date"], "%Y-%m-%d").date() <= end
    ]
