# 🏠 AI와 함께하는 주택 청약 체크리스트

AI가 함께하는 **스마트 주택 청약 준비 도우미** 🏡  
청약 일정 관리부터 추천 지역, 이후 자금 계획까지 한 번에 해결하세요.

---

## ✨ 주요 기능

### 1️⃣ 청약 일정 자동 캘린더 등록 🗓️

- **마이홈**·**청약홈** 등에서 청약 공고 스크래핑
- **[캘린더 다운하기]** 버튼 클릭 시,
  - 접수 시작일
  - 마감일
  - 당첨 발표일  
    을 `.ics` 로 반환하여 **Apple / Samsung 캘린더**에 바로 등록 가능

---

### 2️⃣ AI 기반 청약 추천 지역 📍

- **GPT 5.0 nano 모델**이 사용자 입력
  - 혼인 여부
  - 무주택 여부
  - 소득
  - 청약통장 보유 여부  
    등을 분석하여 최적의 청약 지역 추천

---

### 3️⃣ 청약 이후 TODO 📋

- 청약 이후 진행해야 할 **계약금, 보조금, 잔금 납부** TODO 리스트 제공
- 납부 시 유용한 **신한은행 대출 상품 추천**

---

## 📸 서비스 화면 예시

| 화면                                                                                                                                                                                                            | 설명                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| ![청약을 위한 개인 정보 입력](https://github.com/user-attachments/assets/028024b7-e59a-423a-b36c-592c2f023961)                                                                                                  | 결혼 여부, 무주택 여부 등 청약에 필요한 정보를 입력합니다.<br>입력한 정보를 기반으로 특별공급 대상자인지 판별합니다. |
| ![청약 일정 캘린더](https://github.com/user-attachments/assets/a4f117b1-e436-490a-bb64-ba27ee307333) <br> ![청약 일정 캘린더2](https://github.com/user-attachments/assets/25f256dc-e245-4a55-a01e-f00969cd1e0b) | **청약 일정 자동 등록**<br>마이홈·청약홈에서 스크래핑한 일정이 캘린더에 자동 등록됩니다.                             |
| ![AI 추천 지역](https://github.com/user-attachments/assets/055575bd-b2f2-478d-9102-d75dd8f323bf)                                                                                                                | **AI 기반 추천 지역**<br>사용자 조건을 분석하여 최적의 청약 지역을 추천합니다.                                       |
| ![청약 이후 TODO](https://github.com/user-attachments/assets/ff32b522-5652-4aa1-a218-6c9883eb9ce6)                                                                                                              | **청약 이후 TODO**<br>계약금, 보조금, 잔금 납부 계획과 함께 금융 상품을 안내합니다.                                  |

## 🖥 기술 스택

**Frontend**

- ⚛️ React
- 🗂 Zustand (상태관리)
- 🎨 Styled-components

**Backend**

- 🚀 FastAPI (Python)
- 🕷 Selenium (웹 스크래핑)
- 📅 ics (캘린더 파일 생성)
- 🤖 OpenAI (AI 분석)

---

## 📦 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/username/gp-service.git
cd gp-service

# 2. 가상환경 및 패키지 설치
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경변수 설정
# strategy_api.py 의 15번째 줄에 제공해 드린 API Key를 넣어주시면 테스트 가능합니다.

# 4. 백엔드 서버 실행
uvicorn app:app --reload --port 8000
```
