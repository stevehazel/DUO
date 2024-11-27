import os
from dotenv import dotenv_values

config = {
    **dotenv_values('./.env'),
    **dotenv_values('/opt/.env.shared'),
    **os.environ,
    'service_name': 'DUO'
}
