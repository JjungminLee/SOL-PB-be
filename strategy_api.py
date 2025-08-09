# app.py
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
import re

from openai import OpenAI


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
client = OpenAI(api_key="")


from calendar_scraper import (
    scrape_applyhome_calendar,  # -> List[Dict[str, Any]]
    scrape_myhome_notices,      # -> List[Dict[str, Any]]
    filter_by_week,             # -> List[Dict[str, Any]]
)

class StrategyRequest(BaseModel):
    isHomeless: bool
    isMarried: bool
    marriageYears: int
    childrenCount: int
    isHouseholder: bool
    hasAccount: bool
    hasHouseHistory: bool


KST = timezone(timedelta(hours=9))

def current_week_range_kst():
    today = datetime.now(KST).date()
    week_start = today - timedelta(days=today.weekday())   # 월요일
    week_end = week_start + timedelta(days=6)              # 일요일
    return week_start.isoformat(), week_end.isoformat()


def to_prompt_notice(n: Dict[str, Any]) -> Dict[str, Any]:
    """
    입력 n 예시(각 사이트별 키가 다를 수 있으므로 안전하게 파싱):
    {
      "title": "고양시 A아파트",
      "region": "경기",
      "start_date": "2025-08-15",
      "end_date": "2025-08-17",
      "announce_date": "2025-08-24",  # 없을 수 있음
      "price": None,                  # 또는 숫자
      "types": ["신혼부부특공","국민주택"],  # 없을 수 있음
      "needs_homeless": True,
      "needs_householder": True,
      "max_marriage_years": 7,
      "children_scoring": True
    }
    """
    name = n.get("title") or n.get("이름") or "이름미상"
    region = n.get("region") or n.get("지역") or "지역미상"
    start = n.get("start_date") or n.get("접수시작") or n.get("접수일")
    end = n.get("end_date") or n.get("접수마감") or n.get("접수일")
    announce = n.get("announce_date") or n.get("발표일")
    price = n.get("price") if n.get("price") not in ["", None] else None

    types = n.get("types") or n.get("공급유형") or []
    if isinstance(types, str):
        # "신혼부부특공,국민주택" 같은 경우 분리
        types = [t.strip() for t in types.split(",") if t.strip()]

    return {
        "이름": name,
        "접수시작": start,
        "접수마감": end,
        "발표일": announce,
        "분양가": price if isinstance(price, (int, float)) else None,
        "지역": region,
        "공급유형": types,
        "무주택필수": bool(n.get("needs_homeless", False)),
        "세대주필수": bool(n.get("needs_householder", False)),
        "혼인연한최대": n.get("max_marriage_years"),
        "자녀가점": bool(n.get("children_scoring", False)),
    }


@router.post("/api/strategy")
async def strategy(req: StrategyRequest):
    # 1) 사용자 입력(dict)
    user_data = req.dict()

    # 2) 실시간 청약 일정 수집
    applyhome = scrape_applyhome_calendar()
    myhome = scrape_myhome_notices()
    combined = (applyhome or []) + (myhome or [])
    weekly = filter_by_week(combined)  # 이번 주 공고만

    # 3) notices를 구조화(프롬프트용)
    notices_struct = [to_prompt_notice(n) for n in weekly]

    # 4) 주차 범위
    weekStart, weekEnd = current_week_range_kst()

    # 5) 프롬프트 생성 (값을 실제 치환)
    prompt_payload = {
        "isHomeless": user_data["isHomeless"],
        "isMarried": user_data["isMarried"],
        "marriageYears": user_data["marriageYears"],
        "childrenCount": user_data["childrenCount"],
        "isHouseholder": user_data["isHouseholder"],
        "hasAccount": user_data["hasAccount"],
        "hasHouseHistory": user_data["hasHouseHistory"],
        "weekStart": weekStart,
        "weekEnd": weekEnd,
        "notices": notices_struct,
    }

    prompt = (
        "다음은 청약 지원자 정보와 이번 주 청약 공고입니다. 규칙에 따라 필터링/정렬하고 JSON만 출력하세요.\n\n"
        f"지원자: {json.dumps({k: prompt_payload[k] for k in ['isHomeless','isMarried','marriageYears','childrenCount','isHouseholder','hasAccount','hasHouseHistory']}, ensure_ascii=False)}\n"
        f"기간: {prompt_payload['weekStart']} ~ {prompt_payload['weekEnd']}\n"
        "공고목록: "
        f"{json.dumps(prompt_payload['notices'], ensure_ascii=False)}\n\n"
        "요구사항:\n"
        "1) 필터:\n"
        "- 무주택필수==true 이면 isHomeless==true 인 경우만\n"
        "- 세대주필수==true 이면 isHouseholder==true 인 경우만\n"
        "- 혼인연한최대가 있으면 marriageYears ≤ 혼인연한최대\n"
        "- 공급유형에 '신혼부부특공' 포함 시 isMarried==true 권장(미충족이면 제외)\n"
        "- 접수 기간(접수시작~접수마감)이 기간과 겹치는 공고만\n"
        "2) 정렬 우선순위: (a) 사용자와 맞는 공급유형 우선 → (b) 접수마감 임박 순 → (c) 분양가 낮은 순(null은 뒤)\n"
        "3) 추천 지역: 최종 선정 공고의 지역 상위 3곳(빈도 순, 동률 시 평균 분양가 낮은 순)\n"
        "4) 출력 스키마(오직 JSON):\n"
        "{\n"
        '  "추천 지역": string[],\n'
        '  "청약 목록": [{"이름": string, "접수일": string, "발표일": string|null, "분양가": number|null}]\n'
        "}\n"
        "5) 값이 없으면 발표일/분양가는 null로.\n"
        "오직 JSON만 출력하세요."
    )

    # 6) OpenAI 호출 (JSON 스키마 강제 -> 실패 시 chat.completions로 폴백)
    schema = {
        "type": "object",
        "properties": {
            "추천 지역": {"type": "array", "items": {"type": "string"}},
            "청약 목록": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "이름": {"type": "string"},
                        "접수일": {"type": "string"},
                        "발표일": {"type": ["string", "null"]},
                        "분양가": {"type": ["number", "null"]},
                    },
                    "required": ["이름", "접수일", "발표일", "분양가"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["추천 지역", "청약 목록"],
        "additionalProperties": False,
    }

    content_text: Optional[str] = None
    try:
        resp = client.responses.create(
            model="gpt-5.0-mini",
            input=prompt,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "HousingRecommendation", "schema": schema, "strict": True},
            },
            temperature=0,
        )
        content_text = resp.output_text
    except Exception:
        try:
            resp = client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": prompt}],
            )
            content_text = resp.choices[0].message.content
        except Exception as e:
            return {"error": f"OpenAI 호출 실패: {str(e)}"}

    if not content_text:
        return {"error": "빈 응답"}

    # 7) JSON만 남기기
    cleaned = re.sub(r"```json|```", "", content_text).strip()

    # 8) 파싱 & 검증(최소한)
    try:
        data = json.loads(cleaned)
        # 최소 필드 보정
        if "추천 지역" not in data:
            data["추천 지역"] = []
        if "청약 목록" not in data or not isinstance(data["청약 목록"], list):
            data["청약 목록"] = []

        # 형식 보정: 발표일/분양가 null 처리
        for item in data["청약 목록"]:
            if "발표일" not in item or item["발표일"] in ("", "null"):
                item["발표일"] = None
            if "분양가" not in item or item["분양가"] in ("", "null"):
                item["분양가"] = None
        return data
    except json.JSONDecodeError:
        # 모델이 설명을 섞어 보냈을 때 대비
        # 중괄호/대괄호 블록 중 첫 유효 JSON 추출 시도
        m = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if not m:
            return {"error": "JSON 파싱 실패", "raw": cleaned}
        try:
            return json.loads(m.group(1))
        except Exception:
            return {"error": "JSON 파싱 실패", "raw": cleaned}

app.include_router(router)


