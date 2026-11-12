"""Execute the real theme script with browser storage and OS preference doubles."""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('saved,os_dark,expected', [
    ('', True, 'light'), ('', False, 'light'), ('dark', False, 'dark'),
    ('light', True, 'light'), ('system', True, 'light'), ('system', False, 'light'),
    ('invalid', True, 'light'),
])
def test_theme_initialization_and_navigation(saved, os_dark, expected):
    code = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const script=fs.readFileSync(process.argv[1],'utf8');
let stored=process.argv[2]||null,osDark=process.argv[3]==='True';
function page(){
 const events={},controls=['light','dark','system'].map(value=>({value,checked:false,addEventListener(){}}));
 const document={documentElement:{dataset:{},style:{}},querySelectorAll:()=>controls,
  dispatchEvent(){},addEventListener:(name,fn)=>{events[name]=fn;},getElementById:()=>null};
 const window={addEventListener:(name,fn)=>{events['window:'+name]=fn;}};
 let osQueries=0;
 const context=vm.createContext({window,document,matchMedia:()=>{osQueries++;return {matches:osDark,addEventListener(){}};},
  localStorage:{getItem:()=>stored,setItem:(key,value)=>{stored=value;}},
  CustomEvent:class{},setTimeout});
 vm.runInContext(script,context);context.officeAppearance=window.officeAppearance;
 events.DOMContentLoaded();
 assert.equal(osQueries,0,'Theme must never inspect the device color scheme');
 return {window,document,controls,events,context};
}
let p=page();
assert.equal(p.document.documentElement.dataset.theme,process.argv[4]);
assert.equal(p.controls.find(c=>c.checked).value,stored&&['light','dark','system'].includes(stored)?stored:'light');
p.window.officeAppearance.set('dark');p=page();assert.equal(p.document.documentElement.dataset.theme,'dark');
p.window.officeAppearance.set('system');
assert.equal(stored,'system');assert.equal(p.document.documentElement.dataset.theme,'light');
assert.equal(p.controls.find(c=>c.checked).value,'system');
p=page();assert.equal(p.document.documentElement.dataset.theme,'light');
assert.equal(p.window.officeAppearance.preference,'system');
assert.equal(p.controls.find(c=>c.checked).value,'system');
p.window.officeAppearance.set('dark');p=page();assert.equal(p.document.documentElement.dataset.theme,'dark');
assert.equal(p.controls.find(c=>c.checked).value,'dark');
p.events['window:storage']({key:'barangay-appearance',newValue:'system'});
assert.equal(p.document.documentElement.dataset.theme,'light');
assert.equal(p.controls.find(c=>c.checked).value,'system');
const owner=p.window.officeAppearance;vm.runInContext(script,p.context);assert.strictEqual(p.window.officeAppearance,owner);
p.events['window:storage']({key:'barangay-appearance',newValue:null});assert.equal(p.document.documentElement.dataset.theme,'light');
'''
    result = subprocess.run(['node', '-e', code, str(ROOT/'static/js/appearance.js'), saved, str(os_dark), expected], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('filename', ['base.html','login.html','forgot_password.html','reset_password.html'])
def test_light_fallback_and_versioned_blocking_theme_script(filename):
    source=(ROOT/'templates'/filename).read_text(encoding='utf-8')
    assert '<html lang="en" data-theme="light">' in source
    assert "filename='js/appearance.js',v='20261112-site-default'" in source
    assert source.index('early_paint.html') < source.index('js/appearance.js')


def test_current_light_stylesheet_is_requested(client):
    source=(ROOT/'templates/base.html').read_text(encoding='utf-8')
    assert "filename='css/appearance.css',v='20261112-light2'" in source
    response=client.get('/static/css/appearance.css?v=20261112-light2')
    assert response.status_code == 200


def test_system_description_and_no_os_detection():
    source=(ROOT/'static/js/appearance.js').read_text(encoding='utf-8')
    assert 'matchMedia' not in source and 'prefers-color-scheme' not in source
    controls=(ROOT/'templates/appearance_controls.html').read_text(encoding='utf-8')
    assert "Uses the website's default Light appearance." in controls
    assert 'follows your device' not in controls.lower()
