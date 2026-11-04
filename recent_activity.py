"""Bounded, content-free homepage summaries of committed authorized staff events."""
from office_time import local_timestamp

LABELS={
    ('ADD','Resident'):'Resident registered',('ADD','Household'):'Household created',
    ('UPDATE','Resident'):'Resident updated',('UPDATE','Household'):'Household updated',
    ('DELETE','Resident'):'Resident deleted',('DELETE','Household'):'Household deleted',
}

def summaries(cursor):
    # Never select free text, snapshots, account identities or network metadata.
    cursor.execute("""SELECT id,action_type,target_type,created_at FROM audit_logs
        WHERE status='SUCCESS' AND
        ((action_type IN ('ADD','UPDATE','DELETE') AND target_type IN ('Resident','Household'))
         OR action_type='REPORT_GENERATE') ORDER BY created_at DESC NULLS LAST,id DESC LIMIT 6""")
    return [dict(id=row['id'],action_type=row['action_type'],target_type=row['target_type'],
        label=LABELS.get((row['action_type'],row['target_type']),'Report activity recorded'),
        time=local_timestamp(row['created_at'])) for row in cursor.fetchall()]
