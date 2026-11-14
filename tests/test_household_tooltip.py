"""Execute placement with synthetic viewport geometry; not browser rendering."""
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('popover',['yes','no'])
def test_overlay_escapes_table_and_clamps_to_viewport(popover):
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const handlers={},globalEvents={},viewportEvents={},docEvents={};
const viewport={width:640,height:600,offsetLeft:0,offsetTop:0,addEventListener:(e,f)=>viewportEvents[e]=f};
const wrapper={contains:target=>target===wrapper,getAttribute:()=> 'help',getBoundingClientRect:()=>({right:638,bottom:590,top:550}),matches:()=>false,addEventListener:(e,f)=>handlers[e]=f};
const originalRect=JSON.stringify(wrapper.getBoundingClientRect());let appended,opened=false;
const tip={style:{},setAttribute(){},matches:()=>opened,
 getBoundingClientRect(){return {width:Math.min(260,parseFloat(this.style.maxWidth)||260),height:72};}};
if(process.argv[2]==='yes'){tip.showPopover=()=>{opened=true;};tip.hidePopover=()=>{opened=false;};}
const document={querySelectorAll:()=>[wrapper],createElement:()=>tip,body:{append:n=>appended=n},
 getElementById:()=>({textContent:'Move or remove all residents before deleting this household.'}),
 documentElement:{clientWidth:640},addEventListener:(e,f)=>docEvents[e]=f};
const window={visualViewport:viewport,innerHeight:600,addEventListener:(e,f)=>globalEvents[e]=f};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window});
assert.strictEqual(appended,tip);assert.equal(tip.hidden,true);
handlers.mouseenter();
assert.equal(tip.hidden,false);assert.equal(tip.textContent,'Move or remove all residents before deleting this household.');
assert(parseFloat(tip.style.left)>=8);assert(parseFloat(tip.style.left)+tip.getBoundingClientRect().width<=632);
assert(parseFloat(tip.style.top)<550);assert(parseFloat(tip.style.top)+72<=592);
assert.equal(JSON.stringify(wrapper.getBoundingClientRect()),originalRect);
handlers.mouseleave();assert.equal(tip.hidden,true);
viewport.width=180;viewport.height=300;handlers.focusin();
assert(parseFloat(tip.style.left)>=8);assert(parseFloat(tip.style.left)+tip.getBoundingClientRect().width<=172);
assert(parseFloat(tip.style.top)>=8);assert(parseFloat(tip.style.top)+72<=292);
docEvents.keydown({key:'Escape'});assert.equal(tip.hidden,true);
handlers.focusin();globalEvents.scroll();assert.equal(tip.hidden,true);
handlers.focusin();viewportEvents.resize();assert.equal(tip.hidden,true);
handlers.focusin();docEvents.pointerdown({target:wrapper});assert.equal(tip.hidden,false);
docEvents.pointerdown({target:{}});assert.equal(tip.hidden,true);
handlers.focusin();docEvents.focusin({target:{}});assert.equal(tip.hidden,true);
handlers.focusin();globalEvents.pagehide();assert.equal(tip.hidden,true);
handlers.focusin();globalEvents.pageshow();assert.equal(tip.hidden,true);
'''
    result=subprocess.run(['node','-e',script,str(ROOT/'static/js/household-delete-tooltip.js'),popover],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_tooltip_layout_contract_and_native_disabled_description():
    css=(ROOT/'static/css/admin-form-controls.css').read_text(encoding='utf-8')
    assert '.household-delete-tooltip{position:fixed;' in css
    assert '.household-delete-description{position:absolute;' in css
    assert 'pointer-events:none;z-index:10000' in css
    assert ':focus-within) .household-delete-tooltip{display:block}' not in css
    assert '.header-actions .household-delete-blocked{flex:0 0 auto;height:40px}' in css
    partial=(ROOT/'templates/household_delete_control.html').read_text(encoding='utf-8')
    assert 'type="button" disabled' in partial
    assert 'tabindex="0"' in partial and 'aria-describedby="deleteHouseholdHelp' in partial
    assert 'class="household-delete-description" role="tooltip"' in partial
