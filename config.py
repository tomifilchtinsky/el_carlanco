"""
Configuración central de la aplicación.
Lee variables de entorno (para Railway/producción) o .env local (para desarrollo).
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Cargar .env si existe (para desarrollo local)
load_dotenv()

# --- Variables de entorno ---
DB_HOST = os.getenv("DB_HOST", "aws-1-sa-east-1.pooler.supabase.com")
DB_PORT = os.getenv("DB_PORT", "6543")
DB_USER = os.getenv("DB_USER", "postgres.wredobesrluxodxgmgbp")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "postgres")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "carlanco123")
SECRET_KEY = os.getenv("SECRET_KEY", "el-galpon-secret-key-cambiar-en-prod")
PORT = int(os.getenv("PORT", "8080"))

# --- Engine SQLAlchemy (singleton) ---
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
    return _engine
