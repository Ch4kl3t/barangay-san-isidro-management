"""Actor/record-bound return context for read-only administrator navigation."""
import re
from urllib.parse import urlsplit
from flask import abort,current_app,g,request,url_for
from itsdangerous import URLSafeTimedSerializer,BadSignature


def safe_destination(value):
    if not isinstance(value,str) or any(ord(c)<32 for c in value) or '\\' in value:return '/view_members'
    try:parsed=urlsplit(value)
    except ValueError:return '/view_members'
    if parsed.scheme or parsed.netloc or parsed.fragment:return '/view_members'
    return value if re.fullmatch(r'/(?:view_members|view_households|analytics|audit-log|print_reports|resident/[1-9]\d*|view_household/[1-9]\d*)',parsed.path) else '/view_members'


def serializer():return URLSafeTimedSerializer(current_app.secret_key,salt='resident-navigation-v1')


def resident_url(identifier,return_to=None):
    destination=safe_destination(request.full_path.rstrip('?') if return_to is None else return_to)
    token=serializer().dumps(dict(actor=g.identity['id'],resident_id=int(identifier),return_to=destination))
    return url_for('resident_detail',id=identifier,nav=token)


def return_destination(identifier):
    token=request.args.get('nav')
    if not token:return '/view_members'
    try:data=serializer().loads(token,max_age=7200)
    except BadSignature:abort(400,description='Navigation context expired. Reopen this resident from the directory or household.')
    if data.get('actor')!=g.identity['id'] or data.get('resident_id')!=identifier:abort(403)
    return safe_destination(data.get('return_to'))
