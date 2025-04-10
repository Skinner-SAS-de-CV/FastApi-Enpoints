import os
# Eventualmente deberíamos hacer algo así: https://fastapi.tiangolo.com/advanced/settings/#settings-in-another-module
FRONTEND_URL = os.getenv("FRONTEND_URL")
ORIGINS = ["http://localhost:3000", FRONTEND_URL]