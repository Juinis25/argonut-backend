"""
Test suite completo para Argonut API.

Usa SQLite en memoria + TestClient — no requiere PostgreSQL ni servidor corriendo.
El motor SQLite se activa automáticamente cuando DATABASE_URL empieza con "sqlite".
"""

import os
import sys
import pytest

# ─── Env vars de test — ANTES de cualquier import de la app ─────────────────
os.environ["DATABASE_URL"]  = "sqlite:///:memory:"
os.environ["SECRET_KEY"]    = "test-secret-key-at-least-32-chars-long-for-argonut!!"
os.environ["ENVIRONMENT"]   = "test"
os.environ["SMTP_USER"]     = "test@test.com"
os.environ["SMTP_PASSWORD"] = "test-password"
os.environ["SMTP_HOST"]     = "localhost"
os.environ["SMTP_PORT"]     = "465"
os.environ["FRONTEND_URL"]  = "http://localhost:3000"

# ─── Limpiamos cache de settings si existe de una ejecución previa ───────────
sys.path.insert(0, "/sessions/sweet-elegant-noether/mnt/Argonut/backend")

from core.config import get_settings
get_settings.cache_clear()

# ─── Imports de la app (database.py ya detecta SQLite y usa StaticPool) ──────
from database import engine, get_db
from models   import Base
from main     import app
from fastapi.testclient import TestClient

# ─── Override de get_db para usar el engine SQLite de test ───────────────────
from sqlalchemy.orm import sessionmaker
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# ─── Crear tablas en SQLite ───────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

TEST_USER = {
    "email": "test@argonut.ar",
    "password": "TestPass123!",
    "nombre": "Usuario Test",
}

@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

@pytest.fixture(scope="session")
def auth_headers(client):
    """Registra y loguea al usuario de test. Devuelve headers con Bearer token."""
    r = client.post("/auth/register", json=TEST_USER)
    assert r.status_code in (200, 201), f"Register falló: {r.status_code} — {r.text}"

    r = client.post("/auth/login", json={
        "email": TEST_USER["email"],
        "password": TEST_USER["password"],
    })
    assert r.status_code == 200, f"Login falló: {r.status_code} — {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SISTEMA
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystem:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data and "docs" in data and "version" in data
        print(f"\n    ✓ root: {data['message']}")

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        print("\n    ✓ health: ok")

    def test_docs_available(self, client):
        r = client.get("/docs")
        assert r.status_code == 200
        print("\n    ✓ /docs: disponible")

    def test_openapi_routes(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = list(r.json()["paths"].keys())
        assert len(paths) >= 10, f"Solo {len(paths)} rutas"
        print(f"\n    ✓ OpenAPI: {len(paths)} rutas → {', '.join(sorted(paths))}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AUTH
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuth:
    def test_register_success(self, client):
        r = client.post("/auth/register", json={
            "email": "nuevo@argonut.ar",
            "password": "NuevoPass123!",
            "nombre": "Nuevo",
        })
        assert r.status_code in (200, 201), r.text
        data = r.json()
        # /auth/register devuelve UserOut (perfil), no tokens
        assert "id" in data and "email" in data
        assert data["email"] == "nuevo@argonut.ar"
        print(f"\n    ✓ register: user id={data['id']} email={data['email']}")

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@argonut.ar", "password": "DupPass123!"}
        client.post("/auth/register", json=payload)
        r = client.post("/auth/register", json=payload)
        assert r.status_code in (400, 409), f"Esperaba 400/409, got {r.status_code}"
        print(f"\n    ✓ register duplicado: {r.status_code}")

    def test_register_weak_password(self, client):
        r = client.post("/auth/register", json={"email": "w@x.ar", "password": "123"})
        assert r.status_code == 422
        print("\n    ✓ password débil: 422")

    def test_register_invalid_email(self, client):
        r = client.post("/auth/register", json={"email": "no-es-email", "password": "Pass1234!"})
        assert r.status_code == 422
        print("\n    ✓ email inválido: 422")

    def test_login_success(self, client, auth_headers):
        # auth_headers fixture ya registró y logueó a TEST_USER — sólo verificamos login directo
        r = client.post("/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data and "refresh_token" in data
        print("\n    ✓ login: OK")

    def test_login_wrong_password(self, client):
        r = client.post("/auth/login", json={
            "email": TEST_USER["email"],
            "password": "Incorrecta999!",
        })
        assert r.status_code in (400, 401)
        print(f"\n    ✓ login password incorrecto: {r.status_code}")

    def test_login_nonexistent_user(self, client):
        r = client.post("/auth/login", json={
            "email": "fantasma@argonut.ar",
            "password": "Cualquiera123!",
        })
        assert r.status_code in (400, 401, 404)
        print(f"\n    ✓ login usuario inexistente: {r.status_code}")

    def test_get_profile(self, client, auth_headers):
        r = client.get("/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == TEST_USER["email"]
        assert "id" in data and "plan" in data
        print(f"\n    ✓ /auth/me: {data['email']} (plan={data['plan']})")

    def test_profile_unauthenticated(self, client):
        r = client.get("/auth/me")
        # FastAPI HTTPBearer devuelve 403 cuando no hay token, 401 cuando es inválido
        assert r.status_code in (401, 403)
        print(f"\n    ✓ /auth/me sin token: {r.status_code}")

    def test_refresh_token(self, client):
        r = client.post("/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        })
        refresh = r.json()["refresh_token"]
        r = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r.status_code == 200
        assert "access_token" in r.json()
        print("\n    ✓ /auth/refresh: nuevo access_token OK")

    def test_refresh_invalid_token(self, client):
        r = client.post("/auth/refresh", json={"refresh_token": "token.basura.falso"})
        assert r.status_code in (400, 401, 422)
        print(f"\n    ✓ refresh token inválido: {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MARCAS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarcas:
    MARCA = {
        "nombre": "ARGONUT",
        "clase": 36,
        "titular": "Argonut SAS",
        "contacto": "legal@argonut.ar",
        "notas": "Marca principal",
    }

    def test_crear_marca(self, client, auth_headers):
        r = client.post("/marcas/", json=self.MARCA, headers=auth_headers)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["nombre"] == "ARGONUT"
        assert data["clase"] == 36
        assert data["activa"] is True
        print(f"\n    ✓ crear marca: id={data['id']}")

    def test_nombre_uppercase(self, client, auth_headers):
        r = client.post("/marcas/",
                        json={**self.MARCA, "nombre": "minusculas", "clase": 1},
                        headers=auth_headers)
        assert r.status_code in (200, 201)
        assert r.json()["nombre"] == "MINUSCULAS"
        print("\n    ✓ auto-uppercase: OK")

    def test_clase_invalida_alta(self, client, auth_headers):
        r = client.post("/marcas/", json={**self.MARCA, "clase": 50}, headers=auth_headers)
        assert r.status_code == 422
        print("\n    ✓ clase=50: rechazada")

    def test_clase_invalida_baja(self, client, auth_headers):
        r = client.post("/marcas/", json={**self.MARCA, "clase": 0}, headers=auth_headers)
        assert r.status_code == 422
        print("\n    ✓ clase=0: rechazada")

    def test_nombre_vacio(self, client, auth_headers):
        r = client.post("/marcas/", json={**self.MARCA, "nombre": ""}, headers=auth_headers)
        assert r.status_code == 422
        print("\n    ✓ nombre vacío: rechazado")

    def test_listar_marcas(self, client, auth_headers):
        r = client.get("/marcas/", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 1
        print(f"\n    ✓ listar: {len(data)} marca(s)")

    def test_get_marca_por_id(self, client, auth_headers):
        r = client.post("/marcas/", json={**self.MARCA, "nombre": "GETTEST", "clase": 10}, headers=auth_headers)
        mid = r.json()["id"]
        r = client.get(f"/marcas/{mid}", headers=auth_headers)
        assert r.status_code == 200 and r.json()["id"] == mid
        print(f"\n    ✓ get marca {mid}")

    def test_actualizar_marca(self, client, auth_headers):
        # Reutilizamos una marca ya creada para no chocar con el límite de plan free (3 activas)
        lista = client.get("/marcas/", headers=auth_headers).json()
        mid = lista[0]["id"]
        r = client.put(f"/marcas/{mid}", json={"notas": "Actualizada via PUT"}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["notas"] == "Actualizada via PUT"
        print(f"\n    ✓ put marca {mid}")

    def test_eliminar_marca(self, client, auth_headers):
        # Soft-delete sobre la última marca de la lista
        lista = client.get("/marcas/", headers=auth_headers).json()
        mid = lista[-1]["id"]
        r = client.delete(f"/marcas/{mid}", headers=auth_headers)
        assert r.status_code in (200, 204)
        print(f"\n    ✓ delete marca {mid}")

    def test_marca_inexistente(self, client, auth_headers):
        r = client.get("/marcas/99999", headers=auth_headers)
        assert r.status_code in (403, 404)
        print(f"\n    ✓ marca inexistente: {r.status_code}")

    def test_sin_token_bloqueado(self, client):
        r = client.get("/marcas/")
        assert r.status_code in (401, 403)
        print(f"\n    ✓ sin token: {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ALERTAS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertas:
    def test_listar_alertas(self, client, auth_headers):
        r = client.get("/alertas/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"\n    ✓ alertas: {len(r.json())} alerta(s)")

    def test_sin_token(self, client):
        r = client.get("/alertas/")
        assert r.status_code in (401, 403)
        print(f"\n    ✓ sin token: {r.status_code}")

    def test_resolver_inexistente(self, client, auth_headers):
        r = client.post("/alertas/99999/resolver", json={}, headers=auth_headers)
        assert r.status_code in (403, 404)
        print(f"\n    ✓ resolver inexistente: {r.status_code}")

    def test_ignorar_inexistente(self, client, auth_headers):
        r = client.post("/alertas/99999/ignorar", headers=auth_headers)
        assert r.status_code in (403, 404)
        print(f"\n    ✓ ignorar inexistente: {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_stats(self, client, auth_headers):
        r = client.get("/dashboard/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for campo in ["total_marcas", "marcas_activas", "alertas_criticas",
                      "alertas_altas", "alertas_medias", "alertas_sin_resolver"]:
            assert campo in data, f"Falta: {campo}"
        print(f"\n    ✓ dashboard: marcas={data['total_marcas']}, "
              f"alertas_sin_resolver={data['alertas_sin_resolver']}")

    def test_sin_token(self, client):
        r = client.get("/dashboard/stats")
        assert r.status_code in (401, 403)
        print(f"\n    ✓ sin token: {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestMonitor:
    def test_listar_ejecuciones(self, client, auth_headers):
        # Ruta correcta según OpenAPI: /monitor/runs
        r = client.get("/monitor/runs", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"\n    ✓ runs: {len(r.json())} ejecución(es)")

    def test_run_inexistente(self, client, auth_headers):
        # GET /monitor/runs/{run_id} con ID inexistente → 404
        r = client.get("/monitor/runs/99999", headers=auth_headers)
        assert r.status_code == 404
        print("\n    ✓ run inexistente: 404")

    def test_sin_token(self, client):
        r = client.get("/monitor/runs")
        assert r.status_code in (401, 403)
        print(f"\n    ✓ sin token: {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SECURITY (unit tests, sin HTTP)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurity:
    def test_hash_y_verify(self):
        from core.security import hash_password, verify_password
        h = hash_password("MiPass123!")
        assert h != "MiPass123!"
        assert verify_password("MiPass123!", h)
        assert not verify_password("Incorrecta", h)
        print("\n    ✓ hash + verify: OK")

    def test_access_token_roundtrip(self):
        from core.security import create_access_token, decode_token
        token = create_access_token({"sub": "42"})
        payload = decode_token(token)
        assert payload["sub"] == "42" and payload["type"] == "access"
        print("\n    ✓ access token roundtrip: OK")

    def test_refresh_token_type(self):
        from core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "7"})
        assert decode_token(token)["type"] == "refresh"
        print("\n    ✓ refresh token type: OK")

    def test_token_invalido_401(self):
        from core.security import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token("un.token.falso")
        assert exc.value.status_code == 401
        print("\n    ✓ token inválido → 401")

    def test_token_manipulado(self):
        from core.security import create_access_token, decode_token
        from fastapi import HTTPException
        token = create_access_token({"sub": "1"})
        header, payload, _ = token.split(".")
        with pytest.raises(HTTPException):
            decode_token(f"{header}.{payload}.firma_falsa_abc")
        print("\n    ✓ token manipulado → detectado")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SCHEMAS (unit tests, sin HTTP)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemas:
    def test_user_register_valido(self):
        from schemas import UserRegister
        u = UserRegister(email="a@b.com", password="12345678")
        assert u.email == "a@b.com"
        print("\n    ✓ UserRegister válido")

    def test_user_register_email_invalido(self):
        from pydantic import ValidationError
        from schemas import UserRegister
        with pytest.raises(ValidationError):
            UserRegister(email="no-es-email", password="12345678")
        print("\n    ✓ email inválido → ValidationError")

    def test_user_register_password_corto(self):
        from pydantic import ValidationError
        from schemas import UserRegister
        with pytest.raises(ValidationError):
            UserRegister(email="a@b.com", password="corto")
        print("\n    ✓ password corto → ValidationError")

    def test_marca_uppercase_automatico(self):
        from schemas import MarcaCreate
        m = MarcaCreate(nombre="mi marca", clase=1, titular="Yo")
        assert m.nombre == "MI MARCA"
        print("\n    ✓ nombre uppercase automático")

    def test_marca_clase_bordes(self):
        from pydantic import ValidationError
        from schemas import MarcaCreate
        MarcaCreate(nombre="X", clase=1, titular="T")
        MarcaCreate(nombre="X", clase=45, titular="T")
        with pytest.raises(ValidationError):
            MarcaCreate(nombre="X", clase=0, titular="T")
        with pytest.raises(ValidationError):
            MarcaCreate(nombre="X", clase=46, titular="T")
        print("\n    ✓ clase 1-45: límites validados")

    def test_monitor_modos_validos(self):
        from schemas import MonitorRunRequest
        assert MonitorRunRequest(modo="demo").modo == "demo"
        assert MonitorRunRequest(modo="real").modo == "real"
        print("\n    ✓ modos demo/real: OK")

    def test_monitor_modo_invalido(self):
        from pydantic import ValidationError
        from schemas import MonitorRunRequest
        with pytest.raises(ValidationError):
            MonitorRunRequest(modo="hackme")
        print("\n    ✓ modo inválido → ValidationError")

    def test_dashboard_stats_schema(self):
        from schemas import DashboardStats
        s = DashboardStats(total_marcas=5, marcas_activas=4,
                           alertas_criticas=0, alertas_altas=1,
                           alertas_medias=2, alertas_sin_resolver=3,
                           ultima_ejecucion=None, proxima_ejecucion=None)
        assert s.total_marcas == 5
        print("\n    ✓ DashboardStats: OK")
