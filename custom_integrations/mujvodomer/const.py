from datetime import timedelta

DOMAIN = "mujvodomer"

LOGIN_URL = "https://chyne.mujvodomer.cz/login"
DATA_URL = "https://chyne.mujvodomer.cz/smartMeteringSpotrebaMultitenant"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

UPDATE_INTERVAL = timedelta(minutes=120)