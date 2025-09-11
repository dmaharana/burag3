from typing import Any
import psycopg2
from constants import ENV_FILE_PATH

def read_env_file(file_path: str = ENV_FILE_PATH) -> dict:
    env_vars = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")
    return env_vars