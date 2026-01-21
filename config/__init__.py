import hashlib
import django.utils.crypto

# Monkey patch to add md5 back to django.utils.crypto for compatibility
django.utils.crypto.md5 = hashlib.md5
