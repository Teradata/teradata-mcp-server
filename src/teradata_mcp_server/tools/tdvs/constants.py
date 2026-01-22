# -------------------------------------------------------------------------------#
#  Copyright (C) 2025 by Teradata Corporation.                                   #
#  All Rights Reserved.                                                          #
#                                                                                #
#  File: constants.py                                                            #
#                                                                                #
#  Description:                                                                  #
#    This template defines default constants and  settings                       #
#    for generated tools, such as:                                               #
#      - Internal service URLs                                                   #
#      - Supported authentication types                                          #
#      - Default timeouts and error messages                                     #
#                                                                                #
#  ⚠️ WARNING:                                                                   #
#    DO NOT expose or commit credentials/secrets in version control.             #
#                                                                                #
#  Customize by replacing `{{app_name}}` with the appropriate  name.             #
# TD_{{app_name.upper()}}_URL = "https://private-td-url.com"                     #
#  Supported authentication methods                                              #
# TD_{{app_name.upper()}}_SUPPORTED_AUTH_TYPES = ["BasicAuth", "JWTAuth"]        #
#  Optional: Default timeout (in seconds)                                        #
# DEFAULT_TIMEOUT = 30                                                           #
# Optional: Common error messages                                                #
# ERROR_INVALID_INPUT = "The input provided is invalid."                         #
#                                                                                #
#  Optional: Feature toggles                                                     #
# TD_FEATURE_X_ENABLED = True                                                    #
# -------------------------------------------------------------------------------#
import os

from dotenv import load_dotenv

load_dotenv()

TD_VS_BASE_URL = os.getenv("TD_BASE_URL", None)
TD_PAT_TOKEN = os.getenv("TD_PAT") or None
TD_PEM_FILE = os.getenv("TD_PEM") or None
DATABASE_URI = os.getenv("DATABASE_URI", None)  # e.g., "teradatasql://user:password@host/database"
