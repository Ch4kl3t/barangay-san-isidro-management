"""Defense in depth for application-owned access logs. Hosting proxy logs need the same policy."""
import logging
import re

class PrivateRequestFilter(logging.Filter):
    def filter(self,record):
        message=record.getMessage()
        message=re.sub(r'(/reset-password/)[^\s?"\x1b]+',r'\1[redacted]',message)
        message=re.sub(r'(\b(?:GET|POST|HEAD|PUT|DELETE|PATCH)\s+[^?\s]+)\?[^\s]+',r'\1?[redacted]',message)
        record.msg=message
        record.args=()
        return True

def configure():
    for name in ['werkzeug','gunicorn.access','gunicorn.error']:
        logger=logging.getLogger(name)
        if not any(isinstance(f,PrivateRequestFilter) for f in logger.filters):
            logger.addFilter(PrivateRequestFilter())
