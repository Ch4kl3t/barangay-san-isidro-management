"""Visual login contract keeps native Flask form/security behavior intact."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess


class Elements(HTMLParser):
    def __init__(self):super().__init__();self.elements=[]
    def handle_starttag(self,tag,attrs):self.elements.append((tag,dict(attrs)))


def test_login_visual_native_form_and_local_assets(client):
    response=client.get('/login');assert response.status_code==200
    html=response.get_data(as_text=True);p=Elements();p.feed(html)
    forms=[a for tag,a in p.elements if tag=='form']
    assert len(forms)==1 and forms[0]['action']=='/login' and forms[0]['method']=='POST'
    fields={a.get('name'):a for tag,a in p.elements if tag=='input'}
    assert fields['csrf_token']['value']=='test-csrf'
    assert fields['username']['autocomplete']=='username' and 'required' in fields['username']
    assert fields['password']['type']=='password' and fields['password']['autocomplete']=='current-password'
    assert not fields['password'].get('value')
    assert {a.get('for') for tag,a in p.elements if tag=='label'}=={'username','password'}
    assert any(tag=='a' and a.get('href')=='/forgot-password' for tag,a in p.elements)
    assert 'login-image-notice' not in html and 'Conceptual illustration' not in html
    assert any(tag=='img' and a.get('alt')=='Barangay San Isidro' and 'favicon.svg' in a.get('src','') for tag,a in p.elements)
    assert 'https://' not in html and '/signup' not in html
    for tag,a in p.elements:
        asset=a.get('src') if tag in {'script','img'} else a.get('href') if tag=='link' else None
        if asset and asset.startswith('/static/'):
            assert client.get(asset).status_code==200
    for key,value in {'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Cache-Control':'no-store'}.items():assert response.headers[key]==value


def test_login_presentation_script_does_not_own_submission():
    root=Path(__file__).resolve().parents[1];path=root/'static/js/login-lovable.js'
    script=path.read_text(encoding='utf-8')
    assert all(text not in script for text in ['fetch(','.submit(',"addEventListener('submit'",'bis-theme','localStorage.setItem'])
    assert 'window.officeAppearance.set' in script and 'aria-pressed' in script
    result=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_recovery_pages_share_theme_aware_recovery_presentation(client):
    root=Path(__file__).resolve().parents[1]
    css=(root/'static/css/auth-recovery.css').read_text(encoding='utf-8')
    dark_icon=(root/'static/icons/favicon-dark.svg').read_text(encoding='utf-8')
    assert 'html[data-theme=dark] body.auth-recovery' in css
    assert 'favicon-dark.svg' in css and 'fill="#d9efff"' in dark_icon
    for path in ['/forgot-password','/reset-password/fictional-token']:
        response=client.get(path)
        if response.status_code==200:
            html=response.get_data(as_text=True)
            assert 'class="auth-recovery"' in html
            assert 'css/auth-recovery.css' in html
            assert 'Household Information Management System' in html


def test_light_is_the_default_appearance_without_saved_browser_preference():
    root=Path(__file__).resolve().parents[1]
    script=(root/'static/js'/'appearance.js').read_text(encoding='utf-8')
    early=(root/'templates'/'early_paint.html').read_text(encoding='utf-8')
    assert "let preference='light'" in script
    assert 'html{background:#f8fafc;color:#1e293b;color-scheme:light}' in early
    assert 'html[data-theme=light] body.admin-workspace' in (root/'static/css'/'appearance.css').read_text(encoding='utf-8')
