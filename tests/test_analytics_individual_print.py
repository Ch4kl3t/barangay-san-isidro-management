"""Isolated average comparisons and selected resident output parity."""
from pathlib import Path
import subprocess
from io import BytesIO
from docx import Document
import pytest
from tests.test_ui_simplification import dashboard
from tests.test_predefense_workflows import _cursor

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('basis,column',[('members','member_count'),('active','active_count'),('deceased','deceased_count')])
def test_average_uses_filtered_population_before_sort_and_page(client,dashboard,basis,column):
    for i,row in enumerate(dashboard.homes):row[column]=2+i%3 if i<27 else 0
    population=[r for r in dashboard.homes if r[column]>=2 and r[column]<=4]
    average=sum(r[column] for r in population)/len(population)
    expected=sorted([r for r in population if r[column]>=average],key=lambda r:r['id'])
    query=dict(household_basis=basis,household_size='2-4',household_group='average',households_page=1,household_sort='desc')
    data=client.get('/api/dashboard',query_string=query).json
    assert len(data['household_summary'])==len(population)
    assert data['pagination']['households']['total']==len(expected)
    assert [r['id'] for r in data['households']]==[r['id'] for r in expected[:10]]
    assert data['stats']['total']==125
    query['households_page']=2
    data=client.get('/api/dashboard',query_string=query).json
    assert [r['id'] for r in data['households']]==[r['id'] for r in expected[10:]]
    query.update(household_group='total',households_page=1)
    assert client.get('/api/dashboard',query_string=query).json['pagination']['households']['total']==len(population)


def test_empty_average_is_safe(client,dashboard):
    dashboard.homes=[]
    data=client.get('/api/dashboard?household_group=average').json
    assert data['households']==[] and data['pagination']['households']['total']==0


@pytest.mark.parametrize('columns,expected',[
    ('id,full_name',{'Resident ID','Full name'}),
    ('id,full_name,occupation,household_address',{'Resident ID','Full name','Occupation','Address'}),
    ('id,full_name,current_health_status',{'Resident ID','Full name','Current Health Status'}),
])
def test_individual_customization_preview_print_word(client,monkeypatch,columns,expected):
    def rows(kind,args,limit=None,**kwargs):
        assert kind=='residents' and args['resident_id']=='41' and args['scope']=='resident'
        return [dict(id=41,full_name='Synthetic Selected Resident',occupation='Teacher',
                     household_id=3,household_address='Synthetic Road',current_health_status='Synthetic private value')],1,'Registered'
    monkeypatch.setattr('reporting.rows_for',rows)
    monkeypatch.setattr('report_outputs.transaction',_cursor())
    monkeypatch.setattr('report_outputs.record_generation',lambda *a:None)
    query=dict(scope='resident',resident_id='41',columns=columns)
    preview=client.get('/api/preview/residents',query_string=query)
    assert preview.status_code==200
    assert {f['label'] for f in preview.json['profile_fields']}==expected
    printed=client.get('/reports/print/residents',query_string=query)
    word=client.get('/print_all_members',query_string=query)
    assert printed.status_code==word.status_code==200
    document=Document(BytesIO(word.data))
    labels={row.cells[0].text for table in document.tables for row in table.rows}
    assert labels==expected
    for label in expected:assert f'<dt>{label}</dt>' in printed.text
    for label in {'Birthdate','Gender','Occupation','Address','Current Health Status'}-expected:
        assert f'<dt>{label}</dt>' not in printed.text
    assert 'Synthetic Selected Resident' in printed.text


def test_chart_average_and_individual_report_option_use_existing_paths():
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const fn=source.match(/function householdComparison\([\s\S]*?\n}/)[0];
const context={hhMap:{1:{members:0},2:{members:2},3:{members:5}},householdCard:'average'};
vm.runInNewContext(fn+';result=householdComparison("members");',context);
assert.deepEqual(Array.from(context.result,x=>x[0]),['3']);
context.householdCard='total';vm.runInNewContext('result=householdComparison("members");',context);
assert.equal(context.result.length,3);
const report=fs.readFileSync(process.argv[2],'utf8');
const output=report.match(/const outputKind=\(\)=>[^;]+;/)[0];
const category=report.match(/function category\(\)[^\n]+/)[0];
vm.runInNewContext(output+category+';assert.equal(outputKind(),"residents");assert.equal(category(),"individual");',{kind:{value:'individual'},assert});
const value=report.match(/cell\('td',(item.value==null[^)]+)\)/)[1];
vm.runInNewContext('assert.strictEqual('+value+',0);',{item:{value:0},assert});
'''
    result=subprocess.run(['node','-e',script,str(ROOT/'templates/analytics.html'),str(ROOT/'static/js/report-center.js')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert '<option value="individual">Individual Resident Report</option>' in (ROOT/'templates/report_workspace.html').read_text(encoding='utf-8')
