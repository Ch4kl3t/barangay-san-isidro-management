"""Interpret recorded audit metadata without inventing historical actor roles."""
import json
from privacy import audit_value
from office_time import local_timestamp

def snapshot(raw):
    try:value=json.loads(raw) if isinstance(raw,str) else raw
    except (ValueError,TypeError):return {}
    return audit_value(value) if isinstance(value,dict) else {}

def present(log):
    old,new=snapshot(log.get('old_value')),snapshot(log.get('new_value'))
    role=new.pop('_actor_role',None)
    log['actor_role']={'admin':'Administrator','user':'User'}.get(role,'Not recorded')
    log['time_display']=local_timestamp(log.get('created_at'))
    # The legacy status default was SUCCESS even for denied authentication.
    # Expose that conflict honestly; do not rewrite historical records.
    recorded=log.get('status')
    log['outcome_display']='Denied (legacy outcome recorded as '+str(recorded)+')' if log.get('action_type')=='LOGIN_DENIED' and recorded!='DENIED' else (recorded or 'Not recorded')
    changed=[]
    if log.get('action_type')=='UPDATE':
        for key in sorted(set(old)|set(new)):
            if key.startswith('_') or key in {'updated_at','health_updated','health_information_changed'}:continue
            if old.get(key)!=new.get(key):changed.append(dict(field=key.replace('_',' ').title(),before=old.get(key),after=new.get(key)))
    log['detail_data']=dict(changes=changed,old=old,new=new,health_updated=bool(new.get('health_information_changed')),ip_address=log.get('ip_address'),device=log.get('user_agent'))
    log['old_value']=json.dumps(old,default=str);log['new_value']=json.dumps(new,default=str)
    return log
