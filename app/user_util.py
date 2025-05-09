import os
from clerk_backend_api import Clerk

def onboard_user(clerk_user_id=str, user_id=str):
    sdk =Clerk(
        bearer_auth=os.getenv('CLERK_SECRET_KEY'),
    )
    res = sdk.users.update(user_id=clerk_user_id, external_id=user_id, public_metadata={ "onboardingComplete": True})
    return res