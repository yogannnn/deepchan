import base64
import hashlib
import hmac
import html
import io
import json
import os
import random
import re
import secrets
import subprocess
import time

from flask import abort, current_app, request
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from models import Post
from services.captcha import generate_captcha
from services.csrf import generate_csrf_token, verify_csrf_token
from services.media import (
    add_watermark,
    clean_media_metadata,
    generate_audio_thumbnail,
    generate_video_thumbnail,
    get_media_duration,
    save_files,
)
from services.radio import convert_for_radio, get_file_hash
from services.security import apply_word_filters, check_ban, check_rate_limit
from services.text import parse_bbcode, process_comment, process_urls
from services.tripcodes import generate_tripcode
