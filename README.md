# DB Playground

PostgreSQL과 MongoDB를 한 화면에서 비교하며 배우는 로컬 데이터베이스 실습 환경입니다. 현재 버전은 **Phase 1: 프로젝트 기반 구성**으로, 네 서비스의 실행과 데이터베이스 연결 상태 확인까지 제공합니다.

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
uvicorn app.main:app --reload
```

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

## 환경 변수

`.env.example`을 `.env`로 복사해 사용합니다. 실제 `.env` 파일은 Git에 포함되지 않습니다.

기본 비밀번호 `change-me`는 로컬 실행을 위한 예시입니다. 공유 환경에서는 반드시 변경하세요. `VITE_API_URL`에는 브라우저에서 접근 가능한 백엔드 API 주소를 지정해야 합니다.

## 현재 범위와 다음 단계

Phase 1에서는 다음 항목을 제공합니다.

- Docker Compose 기반 실행 환경
- PostgreSQL 및 MongoDB 연결 상태 API
- React 상태 대시보드
- 기본 테스트와 개발 문서

데이터 모델, 마이그레이션, 샘플 데이터 생성 및 초기화 API는 Phase 2에서 추가합니다. 자세한 설계는 `docs/architecture.md`, 구현 범위는 `docs/phase-1.md`, 검증 결과는 `docs/validation.md`를 참고하세요.
