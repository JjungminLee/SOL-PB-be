from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict
from openai import OpenAI
import json
from fastapi.middleware.cors import CORSMiddleware
import re
from datetime import datetime
from calendar_scraper import scrape_applyhome_calendar, scrape_myhome_notices, filter_by_week



app = FastAPI()
client = OpenAI(api_key="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")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://sol-pb-fe.vercel.app/"],  # 프론트 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StrategyRequest(BaseModel):
    isHomeless: bool
    isMarried: bool
    marriageYears: int
    childrenCount: int
    isHouseholder: bool
    hasAccount: bool
    hasHouseHistory: bool

@app.post("/api/strategy")
async def strategy(req: StrategyRequest):
    # 1. 사용자 입력
    user_data = req.dict()

    # 2. 실시간 청약 일정 수집
    applyhome = scrape_applyhome_calendar()
    myhome = scrape_myhome_notices()
    combined = applyhome + myhome
    weekly = filter_by_week(combined)

    # 3. 요약된 텍스트 생성 (GPT에 넣을용)
    summary_lines = []
    for n in weekly:
        summary_lines.append(
            f"{n['title']} ({n['region']}) - {n['start_date']} ~ {n['end_date']}"
        )
    notice_summary = "\n".join(summary_lines) or "이번 주 청약 일정이 없습니다."

    # 4. GPT 프롬프트
    prompt = f"""
다음은 청약 지원자 정보입니다.
- 무주택 여부: {user_data["isHomeless"]}
- 결혼 여부: {user_data["isMarried"]}
- 결혼 기간: {user_data["marriageYears"]}년
- 자녀 수: {user_data["childrenCount"]}
- 세대주 여부: {user_data["isHouseholder"]}
- 청약통장 보유: {user_data["hasAccount"]}
- 주택 소유 이력: {user_data["hasHouseHistory"]}

이번 주 청약 공고 목록은 다음과 같습니다:
{notice_summary}

이 정보를 바탕으로 아래 형식의 JSON을 출력해 주세요:
- 추천 지역: 문자열 배열
- 청약 목록: 객체 배열 (이름, 접수일, 발표일, 분양가)
JSON 코드만 출력하세요. 마크다운 코드블록 없이.
    """

    # 5. GPT 호출
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    content = response.choices[0].message.content
    json_str = re.sub(r"```json|```", "", content).strip()

    # 6. JSON 응답 반환
    return json.loads(json_str)
