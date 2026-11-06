"""Global presentation tests; mocked records and deterministic DOM/timers only."""
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import subprocess
import xml.etree.ElementTree as ET

import pytest
from flask import render_template,session

from tests.test_defense_refinement import role_store

ROOT=Path(__file__).resolve().parents[1]


def test_all_flash_types_are_escaped_deduplicated_and_consumed_once(app):
    with app.test_request_context('/login'):
        session['_flashes']=[('success','Saved once'),('success','Saved once'),('danger','<script>untrusted</script>'),
            ('warning','Review the selection'),('info','Preparation started'),('household_head_success','Head saved')]
        html=render_template('toast_region.html')
        assert html.count('data-toast data-toast-type=')==5
        assert html.count('Saved once')==1 and '&lt;script&gt;untrusted&lt;/script&gt;' in html
        assert '<script>untrusted</script>' not in html
        assert all('app-toast--'+kind in html for kind in ['success','error','warning','info'])
        assert html.count('role="alert"')==2 and html.count('role="status"')==3
        assert html.count('data-toast-close')==5 and '_flashes' not in session


@pytest.mark.parametrize('operation',['resident_create','resident_edit','household_create','household_edit'])
def test_post_redirect_shows_one_toast_and_refresh_does_not_repeat(client,csrf,role_store,operation):
    if operation.startswith('resident'):
        path='/add_member' if operation.endswith('create') else '/edit_member/2'
        data=dict(firstname='Fictional',surname='Resident',household_id='1',gender='Female',civil_status='Single',status='Active')
    else:
        path='/add_household' if operation.endswith('create') else '/edit_household/1'
        data=dict(surname='Fictional new home',house_number='Test-20',address='Fictional address')
    response=client.post(path,data=data,headers=csrf)
    assert response.status_code==302
    first=client.get(response.location)
    assert first.status_code==200 and first.text.count('data-toast data-toast-type=')==1
    assert 'app-toast--success' in first.text
    assert 'id="recordRegistrationSuccess"' not in first.text and 'office-feedback-region' not in first.text
    assert 'data-toast data-toast-type=' not in client.get(response.location).text


@pytest.mark.parametrize('path,title',[('/login','Login'),('/forgot-password','Forgot Password'),
    ('/view_household/1','Household Details'),('/add_member','Add Resident'),('/add_household','Add Household')])
def test_favicon_and_toast_assets_on_authenticated_and_auth_pages(client,role_store,path,title):
    with client.session_transaction() as state:state['_flashes']=[('info','Synthetic notice')]
    response=client.get(path);assert response.status_code==200
    html=response.text;head=html.split('</head>',1)[0]
    assert f'<title>{title} | Barangay Household Information Management System</title>' in head
    assert 'css/toasts.css' in head and 'js/toasts.js' in head
    assert html.count('data-toast-region')==1 and html.count('Synthetic notice')==1
    for asset in ['icons/favicon.svg','icons/favicon-32.png','icons/favicon.ico']:
        assert asset+'?v=1' in head
        result=client.get('/static/'+asset+'?v=1')
        assert result.status_code==200 and result.mimetype.startswith('image/')
        assert result.headers['Cache-Control']=='public, max-age=86400'
    assert response.headers['Cache-Control']=='no-store'
    assert client.get('/static/css/style.css').headers['Cache-Control']=='no-store'


def test_reset_error_and_print_documents_use_system_identity_without_changing_content(app):
    with app.test_request_context('/reset-password/synthetic'):
        session['_flashes']=[('danger','Synthetic correction')]
        html=render_template('reset_password.html')
        assert '<title>Reset Password | Barangay Household Information Management System</title>' in html
        assert html.count('Synthetic correction')==1 and 'warning-box' in html
        assert 'favicon.svg?v=1' in html
        error=render_template('request_error.html',status=403,message='Synthetic refusal')
        assert '<title>Request 403 | Barangay Household Information Management System</title>' in error
        assert 'role="alert"' in error and 'Synthetic refusal' in error


def test_favicon_contains_house_and_three_people_with_valid_local_fallbacks():
    svg=ET.fromstring((ROOT/'static/icons/favicon.svg').read_bytes())
    ns={'s':'http://www.w3.org/2000/svg'}
    assert svg.attrib['viewBox']=='0 0 32 32' and len(svg.findall('.//s:circle',ns))==3
    assert not svg.findall('.//s:text',ns) and not svg.findall('.//s:image',ns) and not svg.findall('.//s:script',ns)
    assert '#1b3a57' in ET.tostring(svg,encoding='unicode')
    png=(ROOT/'static/icons/favicon-32.png').read_bytes()
    assert png.startswith(b'\x89PNG\r\n\x1a\n') and struct.unpack('>II',png[16:24])==(32,32)
    ico=(ROOT/'static/icons/favicon.ico').read_bytes()
    assert struct.unpack('<HHH',ico[:6])==(0,1,2)
    for i,size in enumerate([16,32]):
        width,height,_,_,_,bits,length,offset=struct.unpack('<BBBBHHII',ico[6+16*i:22+16*i])
        assert (width,height,bits)==(size,size,32)
        assert ico[offset:offset+length].startswith(b'\x89PNG')


def test_toast_lifecycle_accessibility_deduplication_and_safe_dom():
    script=(ROOT/'static/js/toasts.js').read_text(encoding='utf-8')
    harness=r'''
const vm=require('vm'),assert=require('assert');let now=0,next=0,motion=false,focuses=0;const timers=new Map(),events={},docEvents={};
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.handlers={};this.className='';this.isConnected=true;this.textContent='';
  this.classList={add:c=>{if(!this.className.split(' ').includes(c))this.className+=' '+c},remove:c=>this.className=this.className.split(' ').filter(x=>x!==c).join(' ')};}
 append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n)}}
 setAttribute(k,v){this.attrs[k]=v}addEventListener(k,fn){this.handlers[k]=fn}
 contains(el){return el===this||this.children.some(c=>c.contains(el))}
 querySelector(selector){for(const child of this.children){if(selector.startsWith('.')&&child.className.split(' ').includes(selector.slice(1)))return child;if(selector==='[data-toast-close]'&&'data-toast-close'in child.attrs)return child;const found=child.querySelector(selector);if(found)return found}return null}
 remove(){this.isConnected=false;this.parent.children=this.parent.children.filter(el=>el!==this)}
 focus(){focuses++;document.activeElement=this}set innerHTML(value){throw Error('Raw HTML prohibited')}
}
const body=new Element('body'),region=new Element('section'),field=new Element('input');body.append(region,field);
const document={body,activeElement:field,hidden:false,querySelector:()=>region,querySelectorAll:()=>[],createElement:tag=>new Element(tag),createElementNS(ns,tag){const n=new Element(tag);n.namespaceURI=ns;return n},addEventListener(k,fn){docEvents[k]=fn}};
const window={matchMedia:()=>({matches:motion}),addEventListener(k,fn){events[k]=fn},fetch(){throw Error('No networking allowed')}};
const context={window,document,Map,Set,Date:{now:()=>now},setTimeout(fn,delay){const id=++next;timers.set(id,{at:now+delay,fn});return id},clearTimeout:id=>timers.delete(id),requestAnimationFrame:fn=>fn()};
function advance(ms){const end=now+ms;while(true){const due=[...timers].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!due)break;now=due[1].at;timers.delete(due[0]);due[1].fn()}now=end}
vm.createContext(context);vm.runInContext(process.argv[1],context);const show=window.officeToast;
const success=show('Saved <img onerror=unsafe>',{type:'success'});assert.equal(focuses,0);assert.equal(success.attrs.role,'status');assert.equal(success.querySelector('.app-toast-message').textContent,'Saved <img onerror=unsafe>');assert.strictEqual(show('Saved <img onerror=unsafe>',{type:'success'}),success);assert.equal(region.children.length,1);
advance(2000);success.handlers.mouseenter();advance(10000);assert(success.isConnected);success.handlers.mouseleave();advance(2799);assert(success.isConnected);advance(161);assert(!success.isConnected);
const warning=show('Review',{type:'warning'}),error=show('Failure',{type:'error'});advance(30000);assert(warning.isConnected&&error.isConnected);assert.equal(error.attrs.role,'alert');
motion=true;document.activeElement=error.querySelector('[data-toast-close]');error.querySelector('[data-toast-close]').handlers.click();assert(!error.isConnected);assert(focuses>0);
show('One event',{type:'success',key:'event-1'});advance(5000);assert.equal(show('One event',{type:'success',key:'event-1'}),null);
const info=show('Preparing',{type:'info'});advance(1000);info.handlers.focusin({relatedTarget:field});advance(10000);assert(info.isConnected);info.handlers.focusout({relatedTarget:field});advance(3799);assert(info.isConnected);advance(1);assert(!info.isConnected);
const hidden=show('Pause tab',{type:'info'});advance(1000);document.hidden=true;docEvents.visibilitychange();advance(10000);assert(hidden.isConnected);document.hidden=false;docEvents.visibilitychange();advance(3800);assert(!hidden.isConnected);
window.officeFeedback('Unable to update','Legacy caller failure');assert(region.children.some(el=>el.querySelector('.app-toast-message').textContent==='Legacy caller failure'));
motion=false;const leaving=show('Closing before navigation',{type:'success'});leaving.querySelector('[data-toast-close]').handlers.click();assert(leaving.isConnected);
assert.equal(show('Unknown variant',{type:'constructor'}).attrs.role,'status');assert(show('Null options',null));
events.pageshow({persisted:true});assert.equal(region.children.length,0);assert.equal(show({password:'never stringify'}),null);
vm.runInContext(process.argv[1],context);assert.strictEqual(window.officeToast,show);
'''
    result=subprocess.run(['node','-e',harness,script],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
