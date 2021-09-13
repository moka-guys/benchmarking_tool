import os
# read in secret credentials from .env file
from dotenv import load_dotenv
dirname = os.path.dirname(__file__)
env_path = os.path.abspath(os.path.join(dirname , os.pardir, ".env"))
load_dotenv(env_path)


print(os.getenv("EMAIL_USER"))
print(os.getenv("PW"))