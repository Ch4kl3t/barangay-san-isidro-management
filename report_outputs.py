"""One allowlisted data/column contract for preview, browser print and DOCX."""
from io import BytesIO
from urllib.parse import urlsplit
from flask import abort,g,jsonify,render_template,request,send_file
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from database import transaction
from office_time import now_local,local_timestamp

COLUMNS={
 'residents': [('full_name','Full name'),('id','Resident ID'),('birthdate','Birthdate'),('age','Age'),('gender','Gender'),('civil_status','Civil status'),('household_name','Household'),('household_number','House no.'),('occupation','Occupation'),('status','Resident status'),('registration_date','Registered'),('death_date','Reported death date'),('mental_health_status','Mental Health Status'),('current_health_status','Current Health Status')],
 'households':[('surname','Household'),('house_number','House no.'),('address','Address'),('member_count','Members'),('active_count','Active'),('deceased_count','Deceased')],
 'audit':[('created_at_display','Event time (PHT)'),('username','Actor'),('action_type','Action'),('target_type','Entity'),('target_id','Record ID'),('details','Summary'),('status','Recorded outcome')]
}
REQUIRED={'residents':{'full_name','id'},'households':{'surname','house_number'},'audit':{'created_at_display','username','action_type','target_type','target_id'}}
DEFAULTS={'residents':['full_name','id','birthdate','age','gender','household_name','household_number','status'],'households':[c[0] for c in COLUMNS['households']],'audit':[c[0] for c in COLUMNS['audit']]}
FILTER_KEYS={'scope','resident_id','household_id','mode','gender','status','civil_status','age_min','age_max','date_basis','month','year','date_from','date_to','empty','username','action_type','target_type','outcome'}

def column_weight(key):return 2.2 if key in {'full_name','address','details','mental_health_status','current_health_status'} else .9 if key=='id' else .55 if key=='age' else 1


def effective_kind(kind,args):
    if kind not in COLUMNS:raise ValueError('Invalid report type')
    if kind=='households' and args.get('mode','summary') not in {'summary','members'}:raise ValueError('Invalid household report mode')
    return 'residents' if kind=='households' and args.get('mode')=='members' else kind


def selected_columns(kind,args):
    wanted=args.get('columns')
    wanted=set(wanted.split(',')) if wanted else set(DEFAULTS[kind])
    allowed=dict(COLUMNS[kind])
    if wanted-set(allowed):raise ValueError('Unsupported report column')
    wanted|=REQUIRED[kind]
    return [(key,label) for key,label in COLUMNS[kind] if key in wanted]


def prepare(kind,args,limit=None):
    import reporting
    from report_context import enforce
    args=enforce(kind,args);effective=effective_kind(kind,args)
    if kind=='households' and args.get('mode')=='members':
        args['scope']='household'
        if not args.get('household_id'):raise ValueError('Select one household for a member roster')
    validate_filters(kind,args,effective)
    columns=selected_columns(effective,args)
    from privacy import HEALTH_FIELDS
    health_columns = {key for key,label in columns} & HEALTH_FIELDS
    if health_columns and (not g.get('identity') or g.identity.get('role') != 'admin' or g.identity.get('status') != 'approved'):
        abort(403)
    rows,total,basis=(reporting.rows_for(effective,args,limit,health_columns=health_columns)
                      if health_columns else reporting.rows_for(effective,args,limit))
    if effective=='residents' and args.get('scope')=='resident' and not total:raise ValueError('Selected resident is no longer available. Return to records and select again.')
    if effective=='audit':
        # Historical free text cannot be assumed to be free of secrets or health
        # values. Standard reports use classified summaries, never raw payload text.
        labels={'ADD':'Creation event','UPDATE':'Update event','DELETE':'Deletion event','LOGIN':'Sign-in event','LOGIN_DENIED':'Sign-in denied','LOGOUT':'Sign-out event','SIGNUP':'Registration event','PASSWORD_CHANGE':'Password-change event','PASSWORD_RESET_REQUEST':'Password-reset request','PASSWORD_RESET_SUCCESS':'Password-reset event','REPORT_GENERATE':'Report generation event'}
        for row in rows:row['details']=labels.get(row.get('action_type'),'Recorded audit event')
    # Stable ISO calendar dates in every output, including JSON previews.
    from datetime import date,datetime
    for row in rows:
        for key in ['birthdate','registration_date','death_date']:
            if isinstance(row.get(key),(date,datetime)):row[key]=row[key].isoformat()
    scope=None
    if args.get('scope')=='household':
        with transaction() as cursor:
            cursor.execute('SELECT id,surname,house_number,address FROM households WHERE id=%s',(reporting.positive_id(args.get('household_id')),));scope=cursor.fetchone()
        if not scope:abort(404,description='Household not found; no wider report was generated')
    title={'residents':'Residents','households':'Households','audit':'Audit Log'}[kind]
    if scope:title='Household information and member roster'
    if args.get('scope')=='resident':title='Individual resident record'
    labels={'search':'Search','search_extra':'Refine search','household_id':'Household ID','resident_id':'Resident ID','date_basis':'Date basis','date_from':'From','date_to':'Through','age_min':'Minimum age','age_max':'Maximum age','civil_status':'Civil status','action_type':'Action','target_type':'Entity','username':'Actor','empty':'Members'}
    summary=[title]
    for key,value in args.items():
        if value and key in FILTER_KEYS|{'search','search_extra'} and key not in {'scope','mode'}:summary.append(labels.get(key,key.replace('_',' ').title())+': '+str(value))
    if not any(args.get(k) for k in ['month','year','date_from','date_to']):summary.append('All time')
    summary.append(str(total)+' matching records')
    weights=[column_weight(k) for k,l in columns]
    return dict(kind=kind,effective_kind=effective,title=title,columns=columns,column_widths=[100*w/sum(weights) for w in weights],rows=rows,total=total,shown=len(rows),sample=len(rows)<total,basis=basis,scope=scope,
                summary=' · '.join(summary),generated=now_local().strftime('%b %d, %Y %I:%M:%S %p PHT'),preparer=g.identity['username'],args=args)


def record_generation(data,output):
    from account_routes import audit
    # Search values may be personal. Record only that search was used, not text.
    config={k:v for k,v in data['args'].items() if k in FILTER_KEYS and v}
    config.update(columns=[c[0] for c in data['columns']],search_applied=bool(data['args'].get('search') or data['args'].get('search_extra')))
    with transaction() as cursor:
        audit(cursor,'REPORT_GENERATE','System','report','Print view opened; physical printing not confirmed' if output=='browser_print_view' else 'Word document generated',
              new=dict(report_type=data['kind'],scope=data['args'].get('scope','all_matching'),configuration=config,matching_count=data['total'],output_format=output))


def history_entry(item):
    """Legacy audit JSON is untrusted shape; reruns require fresh health opt-in."""
    import json
    from flask import url_for
    from privacy import HEALTH_FIELDS
    try:meta=json.loads(item.get('new_value') or '{}')
    except (ValueError,TypeError):meta={}
    if not isinstance(meta,dict):meta={}
    configuration=meta.get('configuration')
    if not isinstance(configuration,dict):configuration={}
    kind=meta.get('report_type')
    known_kind=isinstance(kind,str) and kind in COLUMNS
    if not known_kind:
        kind='residents'
        configuration={}
    config={k:v for k,v in configuration.items() if k in FILTER_KEYS and
            isinstance(v,(str,int)) and not isinstance(v,bool)}
    # Health column names remain truthful audit metadata, but must never become
    # a renewed selection simply by following an older generation link.
    columns=configuration.get('columns')
    effective='residents' if kind=='households' and config.get('mode')=='members' else kind
    if isinstance(columns,list):
        selected=[v for v in columns if isinstance(v,str) and v in dict(COLUMNS[effective])
                  and v not in HEALTH_FIELDS]
        if selected:config['columns']=','.join(dict.fromkeys(selected))
    output=meta.get('output_format')
    output={'browser_print_view':'Print view opened','docx':'Word document generated'}.get(output,'Not recorded') if isinstance(output,str) else 'Not recorded'
    count=meta.get('matching_count')
    return dict(time=local_timestamp(item.get('created_at')),report_type=kind if known_kind else 'Not recorded',
        count=count if type(count) is int and count>=0 else 'Not recorded',
        output=output,search_omitted=configuration.get('search_applied') is True,
        rerun=url_for('print_reports',kind=kind,**config) if known_kind else url_for('print_reports'))


def preview(kind):
    try:data=prepare(kind,request.args,100)
    except ValueError as exc:return jsonify(error=str(exc)),400
    items=[{key:row.get(key) for key,label in data['columns']} for row in data['rows']]
    return jsonify(items=items,total=data['total'],shown=data['shown'],sample=data['sample'],date_basis=data['basis'],summary=data['summary'],columns=[dict(key=k,label=l) for k,l in data['columns']],scope=data['scope'])


def print_view(kind):
    try:data=prepare(kind,request.args)
    except ValueError as exc:abort(400,description=str(exc))
    record_generation(data,'browser_print_view')
    return render_template('report_print.html',**data)


def document(data):
    doc=Document();section=doc.sections[0];landscape=len(data['columns'])>6
    if landscape:section.orientation=WD_ORIENT.LANDSCAPE;section.page_width,section.page_height=Inches(11.69),Inches(8.27)
    else:section.page_width,section.page_height=Inches(8.27),Inches(11.69)
    section.left_margin=section.right_margin=Inches(.6);section.top_margin=section.bottom_margin=Inches(.6)
    doc.styles['Normal'].font.name='Arial';doc.styles['Normal'].font.size=Pt(10)
    for style in ['Title','Heading 1']:doc.styles[style].font.color.rgb=RGBColor(0,0,0)
    doc.add_paragraph('Barangay San Isidro','Title');doc.add_paragraph('Municipality of Bongabong, Oriental Mindoro')
    doc.add_paragraph(data['title'],'Heading 1');doc.add_paragraph(data['summary']);doc.add_paragraph('Date basis: '+data['basis'])
    doc.add_paragraph('Generated '+data['generated']+' · Prepared by '+data['preparer'])
    if data['scope']:
        h=data['scope'];doc.add_paragraph(f"House {h['house_number']} · {h['surname']} · {h['address']}")
    table=doc.add_table(rows=1,cols=len(data['columns']));table.style='Table Grid';table.autofit=False
    width=(10.49 if landscape else 7.07)/len(data['columns'])
    weights=[column_weight(k) for k,l in data['columns']]
    available=10.49 if landscape else 7.07
    for column,weight in zip(table.columns,weights):column.width=Inches(available*weight/sum(weights))
    for cell,(key,label) in zip(table.rows[0].cells,data['columns']):
        cell.text=label
        for run in cell.paragraphs[0].runs:run.bold=True
    repeat=OxmlElement('w:tblHeader');table.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in data['rows']:
        cells=table.add_row().cells
        for cell,(key,label) in zip(cells,data['columns']):cell.text=str(row.get(key)) if row.get(key) is not None else 'Not recorded'
        props=table.rows[-1]._tr.get_or_add_trPr();props.append(OxmlElement('w:cantSplit'))
    for row in table.rows:
        for cell,weight in zip(row.cells,weights):cell.width=Inches(available*weight/sum(weights))
    if not data['rows']:doc.add_paragraph('No records match the selected filters.')
    stream=BytesIO();doc.save(stream);stream.seek(0);return stream


def docx_report(kind,args):return document(prepare(kind,args))


def download(kind):
    try:data=prepare(kind,request.args);stream=document(data)
    except ValueError as exc:abort(400,description=str(exc))
    record_generation(data,'docx')
    return send_file(stream,as_attachment=True,download_name='San_Isidro_'+kind+'_'+now_local().strftime('%Y-%m-%d')+'.docx')


def safe_return(value):
    from record_navigation import safe_destination
    return safe_destination(value)


def validate_filters(kind,args,effective=None):
    """Reject active unsupported controls independently of client visibility."""
    effective=effective or effective_kind(kind,args)
    dates={'month','year','date_from','date_to'}
    allowed=dates|({'scope','resident_id','household_id','gender','status','civil_status','age_min','age_max','date_basis'} if effective=='residents' else {'household_id','empty','gender','status'} if effective=='households' else {'username','action_type','target_type','outcome'})
    if kind=='households':allowed.add('mode')
    if effective=='residents' and args.get('scope')=='resident':
        allowed={'scope','resident_id'}
        if args.get('search') or args.get('search_extra'):raise ValueError('An individual report uses the selected resident, not additional search filters.')
    if any(args.get(key) not in (None,'') for key in FILTER_KEYS-allowed):raise ValueError('This filter does not apply to the selected report. Reset filters or reopen the report.')
