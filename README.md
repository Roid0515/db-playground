# DB Playground

PostgreSQL과 MongoDB를 한 화면에서 비교하며 배우는 로컬 데이터베이스 실습 환경입니다. 현재 버전은 **Phase 3: 관계형 DB 실습**으로, 서비스 실행과 연결 상태 확인(Phase 1), 온라인 쇼핑몰 샘플 데이터(Phase 2)에 더해 PostgreSQL 테이블/행을 직접 살펴보고 SQL(SELECT·INSERT·UPDATE·DELETE)을 실행할 수 있습니다.

## 실행 방법 두 가지

- **개발용 (Docker Compose):** 아래 빠른 시작을 따르세요. 소스를 직접 수정하며 개발할 때 사용합니다.
- **배포용 (macOS 앱):** Docker나 Homebrew 설치 없이 `DB Playground.app`을 더블클릭해서 바로 실습할 수 있습니다. 실제 PostgreSQL과 MongoDB가 앱 안에 내장되어 로컬에서 그대로 실행됩니다. 빌드 방법과 구조는 [`docs/desktop-app.md`](docs/desktop-app.md)를 참고하세요.

## 준비물

- Docker Desktop 및 Docker Compose
- 로컬 개발 시 Node.js 20 이상 및 Python 3.11 이상

## 빠른 시작

macOS 또는 Linux:

```bash
cp .env.example .env
docker compose up -d --build
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

서비스가 준비되면 다음 주소를 엽니다.

- 대시보드: http://localhost:5173
- API 문서: http://localhost:8000/docs
- 전체 상태: http://localhost:8000/api/health

상태 확인:

```bash
docker compose ps
docker compose logs backend
```

종료:

```bash
docker compose down
```

데이터까지 모두 초기화하려면 아래 명령을 사용합니다. 이 작업은 PostgreSQL과 MongoDB의 영구 볼륨을 삭제합니다.

```bash
docker compose down -v
```

## 로컬 개발

루트의 `.env` 파일에서 데이터베이스 호스트 값을 `localhost`로 변경한 뒤 데이터베이스만 시작합니다.

```bash
docker compose up -d postgres mongodb
```

백엔드:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

`alembic upgrade head`는 PostgreSQL에 최신 스키마를 적용합니다. 완전히 새 데이터베이스라면 첫 `/api/dataset/generate` 호출 시 자동으로도 생성되지만, 이미 데이터가 있는 데이터베이스에 스키마 변경을 반영할 때는 항상 Alembic을 사용하세요. 스키마를 바꿀 때는 `alembic revision --autogenerate -m "설명"`으로 새 마이그레이션을 만듭니다.

프론트엔드:

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

## 품질 확인

백엔드:

```bash
cd backend
pytest
ruff check .
ruff format --check .
```

프론트엔드:

```bash
cd frontend
pnpm test --run
pnpm lint
pnpm build
```

## 샘플 데이터

온라인 쇼핑몰 도메인(고객·상품·주문)을 두 데이터베이스에 서로 다른 방식으로 생성합니다. PostgreSQL은 `customers`/`products`/`orders`/`order_items` 테이블로 정규화되어 주문 내역을 조인으로 조회하고, MongoDB는 `orders` 문서 안에 상품 스냅샷이 포함된 `items` 배열을 그대로 내장합니다. 매번 동일한 시드로 생성되므로 다시 생성해도 같은 데이터가 만들어집니다.

```bash
curl -X POST http://localhost:8000/api/dataset/generate   # 고객 24 · 상품 18 · 주문 40건 생성
curl http://localhost:8000/api/dataset/status              # 저장소별 현재 개수 확인
curl -X POST http://localhost:8000/api/dataset/reset        # 두 저장소 모두 비우기
```

## 관계형 DB 실습

대시보드의 "관계형 DB" 메뉴에서 테이블 목록·행 데이터를 살펴보고, SQL을 직접 실행해 볼 수 있습니다. SELECT/INSERT/UPDATE/DELETE만 허용되며(스키마를 바꾸는 DDL은 차단), 한 번에 한 문장만 실행됩니다.

```bash
curl http://localhost:8000/api/postgres/tables                          # 테이블 목록 + 행 개수
curl "http://localhost:8000/api/postgres/tables/customers/rows?page=1"   # 페이지네이션된 행 조회
curl -X POST http://localhost:8000/api/postgres/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM customers LIMIT 5"}'
```

## 환경 변수

`.env.example`을 `.env`로 복사해 사용합니다. 실제 `.env` 파일은 Git에 포함되지 않습니다.

기본 비밀번호 `change-me`는 로컬 실행을 위한 예시입니다. 공유 환경에서는 반드시 변경하세요. `VITE_API_URL`에는 브라우저에서 접근 가능한 백엔드 API 주소를 지정해야 합니다.

## 현재 범위와 다음 단계

Phase 1 + Phase 2 + Phase 3에서는 다음 항목을 제공합니다.

- Docker Compose 기반 실행 환경과 연결 상태 API (Phase 1)
- Docker 없이 실습할 수 있는 독립형 macOS 앱(.dmg) 배포 경로
- 온라인 쇼핑몰 샘플 데이터 모델(PostgreSQL 정규화 테이블 vs MongoDB 내장 문서)과 생성·초기화·현황 API (Phase 2)
- PostgreSQL 스키마를 위한 Alembic 마이그레이션
- 테이블/행 탐색과 SQL(SELECT·INSERT·UPDATE·DELETE) 실행 콘솔 (Phase 3)
- 백엔드·프론트엔드 테스트와 개발 문서

MongoDB 조회/쿼리 콘솔, 스키마 다이어그램, 구조 비교 학습 콘텐츠, 트랜잭션·인덱스 실습은 이후 단계에서 추가합니다. 설계는 `docs/architecture.md`, Phase 1 구현 범위는 `docs/phase-1.md`, Phase 2 구현 범위는 `docs/phase-2.md`, Phase 3 구현 범위는 `docs/phase-3.md`, 검증 결과는 `docs/validation.md`, macOS 앱 구조는 `docs/desktop-app.md`를 참고하세요.
