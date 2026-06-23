# Bingle 배포 가이드 v2

> ✅ Supabase 설정은 이미 완료된 상태입니다.
> 이번 버전은 DB를 사용하지 않으므로 Supabase는 더 이상 필요하지 않습니다.

---

## 프로젝트 구조

```
bingle/
├── main.py                        ← FastAPI 앱 진입점
├── requirements.txt               ← Python 라이브러리
├── Procfile                       ← Railway 실행 명령
├── railway.toml                   ← Railway 설정
├── .env.example                   ← 환경변수 예시
├── backend/
│   ├── config.py                  ← 환경변수 관리
│   └── routers/
│       └── chat.py                ← POST /api/conversation, POST /api/respond
└── frontend/
    ├── index.html                 ← 웹앱
    └── data/sentences.json        ← 영어 문장 200개
```

---

## STEP 1. VSCode에서 로컬 실행

```bash
# 1. 가상환경 생성 (최초 1회)
python -m venv venv

# 2. 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 라이브러리 설치
pip install -r requirements.txt

# 4. .env 파일 생성
# .env.example 을 복사해서 .env 로 저장 후 API 키 입력
# Windows:
copy .env.example .env
# Mac/Linux:
cp .env.example .env

# 5. .env 파일 편집 — ANTHROPIC_API_KEY 값 입력
# (https://console.anthropic.com 에서 발급)

# 6. 서버 실행
uvicorn main:app --reload --port 8000
```

브라우저에서 http://localhost:8000 접속 → 앱 확인!

---

## STEP 2. Railway 배포

### 2-1. GitHub에 코드 올리기

```bash
# Git 초기화 (최초 1회)
git init
git add .
git commit -m "Bingle v2 초기 배포"

# GitHub에 새 저장소 만들고 연결
# github.com → New repository → bingle
git remote add origin https://github.com/[내계정]/bingle.git
git push -u origin main
```

### 2-2. Railway 배포

1. https://railway.app 접속 → GitHub 로그인
2. **New Project → Deploy from GitHub repo** 선택
3. bingle 저장소 선택 → Deploy

---

## STEP 3. Railway 환경변수 설정

Railway 대시보드 → 프로젝트 → **Variables** 탭:

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `ANTHROPIC_API_KEY` | `sk-ant-xxxxx` | Anthropic Console에서 복사 |
| `ALLOWED_ORIGIN` | `https://[Railway URL]` | 배포 후 URL 확인 후 입력 |
| `SESSION_MAX_MINUTES` | `30` | 세션 최대 시간 |
| `POOR_REPEAT_MIN` | `5` | 못했을 때 최소 반복 횟수 |
| `POOR_REPEAT_MAX` | `8` | 못했을 때 최대 반복 횟수 |

변수 추가 후 → **Redeploy** 클릭

---

## STEP 4. 도메인 확인 및 인사이트베이 연결

1. Railway 대시보드 → Settings → **Generate Domain** 클릭
   - 예시: `https://bingle-production.up.railway.app`

2. 커스텀 도메인 사용 시 (예: practice.bingle.co):
   - Railway → Settings → Custom Domain → 입력
   - 도메인 업체 DNS에서 CNAME 추가

3. **인사이트베이 My Page 연결**:
   - 수강 내역 페이지에서 Bingle 항목 링크를 위 URL로 설정
   - 별도 인증 없이 URL 접속 시 바로 토픽 선택 → 연습 시작

---

## 동작 흐름

```
1. 수강생이 인사이트베이 My Page → Bingle 링크 클릭
        ↓
2. Bingle 웹앱 열림 → 토픽 20개 중 선택
        ↓
3. 선택한 토픽의 문장 10개로 Claude가 자연스러운 대화 생성
        ↓
4. AI가 TTS로 대화 시작 → 수강생이 마이크로 응답
        ↓
5. 잘하면(good) → 격려 후 다음 문장으로 이동 (1회 반복)
   못하면(poor) → 힌트 제공 + 5~8회 반복 연습
        ↓
6. 30분 후 자동 종료 → 결과 화면 표시
```

---

## 앱 사용법 (수강생 안내용)

- **Chrome 브라우저** 사용 (Safari, Firefox는 음성 인식 미지원)
- 마이크 권한 허용 필수
- 마이크 버튼(🎤)을 누르고 영어로 말하기
- 말을 멈추면 자동으로 분석 시작
- 잘 못하겠으면 💡 힌트를 보고 따라 말하기
- 30분 타이머가 끝나면 세션 자동 종료

---

## 비용 예상 (월간)

| 항목 | 비용 |
|------|------|
| Railway (Starter) | $5/월 고정 |
| Claude API | 대화 1회 약 1,000~1,500 토큰 → 수강생 10명 기준 월 $5~15 |
| **합계** | 약 **$10~20/월** |

> Supabase, DB, 이메일 비용 없음 — 이전 버전 대비 비용 대폭 절감
