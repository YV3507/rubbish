from dotenv import load_dotenv
from app.config.schema import ConfigSchema

# Load .env file from project root (backend/ or monorepo root)
load_dotenv(verbose=True)

# Global singleton config instance (env vars override defaults)
config = ConfigSchema()
config.apply_env_overrides()
