# DB Playground

PostgreSQL과 MongoDB를 한 화면에서 비교하며 배우는 로컬 데이터베이스 실습 환경입니다. Phase 1부터 7까지 전 과정이 구현되어 있습니다: 서비스 실행과 연결 상태 확인, 온라인 쇼핑몰 샘플 데이터, PostgreSQL 테이블/SQL 콘솔, MongoDB 컬렉션/mongosh 스타일 콘솔, 두 구조를 나란히 보는 비교 화면, 트랜잭션·인덱스 실습, 그리고 핵심 개념을 정리한 학습 노트까지 한 번에 실습할 수 있습니다.

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
- 전체 상태(대시보드용, 항상 200): http://localhost:8000/api/health
- 준비 상태(오케스트레이션용, 하나라도 장애면 503): http://localhost:8000/api/health/ready

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

`POSTGRES_USER`/`PASSWORD`와 `MONGODB_USERNAME`/`PASSWORD`는 앱이 실제로 접속하는 최소 권한 계정입니다(각각 `NOSUPERUSER`, `root` 아님 — 두 컨테이너가 최초 부팅 시 `backend/docker/postgres-init`, `backend/docker/mongo-init` 스크립트로 직접 생성합니다). `POSTGRES_ADMIN_PASSWORD`/`MONGODB_ADMIN_PASSWORD`는 각 이미지 자체의 부트스트랩 관리자 계정 비밀번호로, 그 초기화 스크립트만 사용하고 앱은 절대 사용하지 않습니다. 네 값 모두 `.env`에 반드시 설정해야 하며, 비워두면 `docker compose`가 즉시 실패합니다(알려진 기본값으로 조용히 기동되는 것을 방지). 기본 예시값 `change-me`/`change-me-admin`은 로컬 실행용이며 공유 환경에서는 반드시 변경하세요. `VITE_API_URL`에는 브라우저에서 접근 가능한 백엔드 API 주소를 지정해야 합니다.

## 현재 범위

Phase 1부터 7까지 모두 구현되어 있습니다.

- Docker Compose 기반 실행 환경과 연결 상태 API (Phase 1)
- Docker 없이 실습할 수 있는 독립형 macOS 앱(.dmg) 배포 경로
- 온라인 쇼핑몰 샘플 데이터 모델(PostgreSQL 정규화 테이블 vs MongoDB 내장 문서)과 생성·초기화·현황 API (Phase 2)
- PostgreSQL 스키마를 위한 Alembic 마이그레이션 (Docker·macOS 앱 모두 시작 시 자동 적용)
- 테이블/행 탐색과 SQL(SELECT·INSERT·UPDATE·DELETE) 실행 콘솔 (Phase 3)
- 컬렉션/문서 탐색과 mongosh 스타일 명령 콘솔 (Phase 4)
- 같은 주문을 PostgreSQL 조인 결과와 MongoDB 임베디드 문서로 나란히 보는 구조 비교 화면 (Phase 5)
- EXPLAIN ANALYZE 기반 인덱스 실습과 BEGIN/COMMIT/ROLLBACK 트랜잭션 샌드박스 (Phase 6)
- 핵심 개념을 정리한 학습 노트 (Phase 7)
- 백엔드·프론트엔드 테스트, GitHub Actions CI, 개발 문서

Phase 3 완료 후 보안·안정성 하드닝을 별도로 진행했습니다 — PostgreSQL/MongoDB 모두 앱이 관리자 계정이 아닌 최소 권한 계정으로 접속하고, 쿼리 제한(타임아웃·최대 행 수)이 백엔드에서 강제되고, 컨테이너/앱 헬스체크는 `/api/health/ready`를 보고, 두 저장소는 서로 독립적으로 장애를 보고합니다. 자세한 내용은 `AGENTS.md`의 "Security and reliability"와 `docs/architecture.md`의 "Decisions (Hardening)"을 참고하세요.

설계는 `docs/architecture.md`, 각 단계 구현 범위는 `docs/phase-1.md`부터 `docs/phase-7.md`까지, 검증 결과는 `docs/validation.md`, macOS 앱 구조는 `docs/desktop-app.md`를 참고하세요.
