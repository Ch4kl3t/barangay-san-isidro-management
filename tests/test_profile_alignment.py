"""Profile composition, sizing and bundled-icon regression contracts."""
from html.parser import HTMLParser
from pathlib import Path
import json
import subprocess

from tests.test_approved_profile import profile_store

ROOT=Path(__file__).resolve().parents[1]


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(); self.root=dict(tag='root',attrs={},children=[]); self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        node=dict(tag=tag,attrs=dict(attrs),children=[],parent=self.stack[-1])
        self.stack[-1]['children'].append(node)
        if tag not in {'input','meta','link','img','br','hr','source','area','base','wbr'}:self.stack.append(node)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i]['tag']==tag:
                self.stack=self.stack[:i]; break


def nodes(node):
    yield node
    for child in node['children']:yield from nodes(child)


def test_profile_header_and_quick_link_composition(client,monkeypatch):
    profile_store(monkeypatch,[])
    response=client.get('/profile')
    tree=Tree();tree.feed(response.get_data(as_text=True))
    all_nodes=list(nodes(tree.root))
    personal=next(n for n in all_nodes if n['attrs'].get('id')=='personalTitle')
    header=personal['parent']['parent']
    assert header['attrs']['class']=='info-card-header'
    assert [n['tag'] for n in header['children']]==['i','div','button']
    assert header['children'][1]['children'][1]['tag']=='p'
    assert header['children'][2]['attrs']['onclick']=="openModal('editModal')"
    security=next(n for n in all_nodes if n['attrs'].get('class')=='security-summary')
    assert [n['tag'] for n in security['children']]==['i','div','button']
    assert security['children'][2]['attrs']['onclick']=="openModal('passwordModal')"
    links=[n for n in all_nodes if n['attrs'].get('class')=='quick-link-item']
    assert len(links)==4
    assert [n['attrs']['href'] for n in links]==['/view_members','/view_households','/analytics','/print_reports']
    for link in links:
        assert [n['tag'] for n in link['children']]==['i','span','i']
        assert link['children'][2]['attrs']['data-lucide']=='chevron-right'
    for identifier in ['editModal','passwordModal']:
        modal=next(n for n in all_nodes if n['attrs'].get('id')==identifier)
        assert any(n['attrs'].get('name')=='csrf_token' for n in nodes(modal))
    # Evaluate the actual offline icon registry; names from Profile must resolve.
    profile=next(n for n in all_nodes if 'profile-approved' in n['attrs'].get('class','').split())
    names=[n['attrs']['data-lucide'] for n in nodes(profile) if 'data-lucide' in n['attrs']]
    script="const fs=require('fs'),vm=require('vm');const c=vm.createContext({document:{readyState:'loading',addEventListener(){}}});vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);process.stdout.write(JSON.stringify(vm.runInContext('Object.keys(ICONS)',c)));"
    result=subprocess.run(['node','-e',script,str(ROOT/'static/icons/lucide-icons.js')],capture_output=True,text=True,check=True)
    assert set(names)<=set(json.loads(result.stdout))


def test_desktop_sizing_and_deliberate_mobile_stacking():
    template=(ROOT/'templates/profile.html').read_text(encoding='utf-8')
    legacy=template.split('.btn-primary, .btn-secondary {',1)[1].split('}',1)[0]
    assert 'width: auto' in legacy and 'width: 100%' not in legacy
    css=(ROOT/'static/css/profile-approved.css').read_text(encoding='utf-8')
    desktop=css.split('@media(max-width:1100px)',1)[0]
    assert '.info-card-header{display:grid;grid-template-columns:24px minmax(0,1fr) auto' in desktop
    assert '.security-summary{display:grid;grid-template-columns:24px minmax(0,1fr) auto' in desktop
    assert '.quick-link-item{display:grid;grid-template-columns:22px minmax(0,1fr) 16px' in desktop
    assert '.quick-link-item>[data-lucide]:last-child' in desktop
    assert 'width:auto' in desktop and 'white-space:nowrap' in desktop
    mobile=css.split('@media(max-width:760px)',1)[1]
    assert '.profile-container{grid-template-columns:1fr}' in mobile
    assert 'grid-column:2;justify-self:start;width:auto;white-space:normal' in mobile
