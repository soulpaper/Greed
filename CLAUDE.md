# MyButler - Claude Code 프로젝트 설정

## 언어 설정
- 모든 응답, 주석, 커밋 메시지는 **한국어**로 작성

## 프로젝트 개요
주식 포트폴리오 기록 및 스크리닝 시스템
- 일일 자산 기록 자동화 (KIS API 연동)
- 일목균형표 기반 스크리닝
- 기술적 분석 (볼린저밴드, 이동평균 정배열, 컵앤핸들)
- 펀더멘탈 분석 (ROE, GPM, 부채비율, CapEx)
- 자산 태그 기반 분류 시스템

## 기술 스택
- **Backend**: Python 3.12, FastAPI
- **Database**: SQLite (aiosqlite), Redis (캐시)
- **API**: 한국투자증권 KIS OpenAPI
- **Scheduler**: APScheduler

## 프로젝트 구조
```
MyButler/
├── main.py                 # FastAPI 앱 진입점
├── config.yaml             # KIS API 설정 (민감정보!)
├── app/
│   ├── config/             # DB, 스케줄러 설정
│   ├── models/             # Pydantic 모델
│   ├── services/           # 비즈니스 로직
│   │   ├── technical_analysis/   # 기술적 분석
│   │   └── fundamental_analysis/ # 펀더멘탈 분석
│   ├── controllers/        # API 엔드포인트
│   ├── scheduler/          # 스케줄러 및 작업
│   └── utils/              # 유틸리티
└── data/                   # SQLite DB 파일
```

## 주요 명령어
```bash
# 서버 실행
python main.py
# 또는
uvicorn main:app --reload --port 8000

# API 문서
http://localhost:8000/docs
```

## 주의사항
- `config.yaml`에 API 키와 계좌번호가 있음 - **절대 커밋 금지**
- Redis가 로컬에서 실행 중이어야 함 (선택적)
- KIS API는 Rate Limit이 있음 (kis_rate_limiter.py 참고)

## API 엔드포인트
| 경로 | 기능 |
|------|------|
| `/api/v1/history/*` | 자산 기록 관리 |
| `/api/v1/screening/*` | 주식 스크리닝 |
| `/api/v1/tags/*` | 자산 태그 관리 |

## 코드 컨벤션
- PEP 8 준수
- Type hints 필수
- Docstring 한국어 작성
- 비동기 함수는 `async/await` 사용
- DB 작업은 `async with` 컨텍스트 매니저 사용

## 지원 거래소
- NASD (나스닥)
- NYSE (뉴욕증권거래소)
- AMEX (아멕스)
- TKSE (도쿄증권거래소)

## 참조 디렉토리
- **MBT 작업 시 DB에 없는 데이터 검색이 필요할 때:**
  - `References_Project/` 디렉토리를 **최우선**으로 확인

## 작업 규칙
- **작업 완료 시 관련 문서 업데이트 필수**
  - 아키텍처 변경 → 프로젝트 구조/개요 업데이트
  - API 추가/변경 → API 엔드포인트 섹션 업데이트
  - 새 의존성 → 기술 스택 업데이트
  - 주요 기능 변경 → README 또는 CLAUDE.md 반영
