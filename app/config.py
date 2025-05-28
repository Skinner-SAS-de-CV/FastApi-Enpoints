import os
# Eventualmente deberíamos hacer algo así: https://fastapi.tiangolo.com/advanced/settings/#settings-in-another-module
FRONTEND_URL = os.getenv("FRONTEND_URL")
# Remover localhost:3000 cuando cambiemos a nestjs backend
ORIGINS = ["http://localhost:3000", "http://localhost:3001", FRONTEND_URL]
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", 'https://api.openai.com/v1')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")