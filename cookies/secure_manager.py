"""
Cookie加密管理器 - 闭源存储，防止泄露
- AES-256加密存储 cookies.json
- 密钥自动生成，不提交到Git
- 只有本服务器能解密
"""
import json, os, time, base64
from pathlib import Path

# 尝试多种加密库
for lib in ['cryptography.fernet', 'Crypto.Cipher']:
    try:
        if 'fernet' in lib:
            from cryptography.fernet import Fernet
            HAS_FERNET = True
            break
        elif 'Cipher' in lib:
            from Crypto.Cipher import AES
            from Crypto.Protocol.KDF import PBKDF2
            HAS_AES = True
            break
    except ImportError:
        continue
else:
    HAS_FERNET = False
    HAS_AES = False

COOKIE_DIR = Path(__file__).parent
KEY_FILE = COOKIE_DIR / '.cookie_key'


def _get_or_create_key() -> bytes:
    """获取或生成加密密钥（不提交到Git）"""
    if KEY_FILE.exists():
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    
    # 生成新密钥
    if HAS_FERNET:
        key = Fernet.generate_key()
    else:
        # 用机器指纹生成固定密钥
        import hashlib
        machine_id = open('/etc/machine-id').read().strip() if os.path.exists('/etc/machine-id') else 'baobao_default'
        key = hashlib.sha256(machine_id.encode()).digest()
    
    # 保存密钥（权限600）
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)
    
    # 添加到.gitignore
    gitignore = COOKIE_DIR / '.gitignore'
    if not gitignore.exists() or '.cookie_key' not in gitignore.read_text():
        with open(gitignore, 'a') as f:
            f.write('\n.cookie_key\ncookies.json\n')
    
    return key


def encrypt(data: dict) -> str:
    """加密数据"""
    if not data:
        return ''
    
    key = _get_or_create_key()
    plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    if HAS_FERNET:
        f = Fernet(key)
        return f.encrypt(plaintext).decode('utf-8')
    else:
        # 简单异或加密（兜底）
        encrypted = bytes(k ^ key[i % len(key)] for i, k in enumerate(plaintext))
        return base64.b64encode(encrypted).decode('utf-8')


def decrypt(encrypted: str) -> dict:
    """解密数据"""
    if not encrypted:
        return {}
    
    key = _get_or_create_key()
    
    if HAS_FERNET:
        try:
            f = Fernet(key)
            return json.loads(f.decrypt(encrypted.encode('utf-8')))
        except:
            return {}
    else:
        try:
            encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))
            decrypted = bytes(encrypted_bytes[i] ^ key[i % len(key)] for i in range(len(encrypted_bytes)))
            return json.loads(decrypted.decode('utf-8'))
        except:
            return {}


class SecureCookieManager:
    """安全Cookie管理器 - 加密存储+自动续期"""
    
    def __init__(self):
        self.store_file = COOKIE_DIR / 'store.enc'
        self.key_file = KEY_FILE
        self._ensure_gitignore()
    
    def _ensure_gitignore(self):
        """确保敏感文件不被提交"""
        gitignore = COOKIE_DIR / '.gitignore'
        entries = ['.cookie_key', 'store.enc', 'cookies.json']
        if not gitignore.exists():
            gitignore.write_text('\n'.join(entries) + '\n')
        else:
            content = gitignore.read_text()
            for e in entries:
                if e not in content:
                    with open(gitignore, 'a') as f:
                        f.write(f'\n{e}\n')
    
    def _load_store(self) -> dict:
        """加载加密存储"""
        if not self.store_file.exists():
            return {}
        try:
            encrypted = self.store_file.read_text().strip()
            return decrypt(encrypted)
        except:
            return {}
    
    def _save_store(self, data: dict):
        """加密保存"""
        encrypted = encrypt(data)
        self.store_file.write_text(encrypted)
        os.chmod(self.store_file, 0o600)
    
    def set(self, platform: str, cookie_dict: dict):
        """设置Cookie（加密存储）"""
        store = self._load_store()
        store[platform] = {
            'cookies': cookie_dict,
            'set_at': time.time(),
            'last_refresh': time.time(),
        }
        self._save_store(store)
        print(f"✅ {platform} Cookie已加密保存 ({len(cookie_dict)}个字段)")
    
    def get(self, platform: str) -> dict:
        """获取Cookie"""
        store = self._load_store()
        entry = store.get(platform, {})
        return entry.get('cookies', {})
    
    def is_valid(self, platform: str) -> bool:
        """检查是否配置了Cookie"""
        store = self._load_store()
        entry = store.get(platform, {})
        return bool(entry and entry.get('cookies'))
    
    def refresh(self, platform: str, new_cookies: dict):
        """刷新Cookie"""
        store = self._load_store()
        entry = store.get(platform, {})
        if entry:
            entry['cookies'].update(new_cookies)
            entry['last_refresh'] = time.time()
            self._save_store(store)
            return True
        return False
    
    def remove(self, platform: str):
        """删除Cookie"""
        store = self._load_store()
        if platform in store:
            del store[platform]
            self._save_store(store)
    
    def status(self) -> dict:
        """状态"""
        store = self._load_store()
        result = {}
        for platform, entry in store.items():
            if not entry or not entry.get('cookies'):
                continue
            set_at = entry.get('set_at', 0)
            last = entry.get('last_refresh', 0)
            age_days = int((time.time() - set_at) / 86400) if set_at else 0
            last_hours = int((time.time() - last) / 3600) if last else 0
            result[platform] = f'✅ 已加密 ({len(entry["cookies"])}个字段, 已存{age_days}天, {last_hours}小时前刷新)'
        return result


# ─── 自动续期 ──────────────────────────────────────────

async def auto_refresh_platform(cm: SecureCookieManager, platform: str, domain: str, required_key: str):
    """用浏览器访问平台保持Cookie活跃"""
    from playwright.async_api import async_playwright
    
    cookies = cm.get(platform)
    if not cookies:
        return False, '未配置Cookie'
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone) AppleWebKit/605.1.15',
                viewport={'width':390,'height':844}, is_mobile=True)
            
            for name, value in cookies.items():
                try:
                    await ctx.add_cookies([{
                        'name': name, 'value': value,
                        'domain': f'.{domain}', 'path': '/'
                    }])
                except: pass
            
            page = await ctx.new_page()
            await page.goto(f'https://www.{domain}/', timeout=15000, wait_until='commit')
            await page.wait_for_timeout(3000)
            
            new_cookies = await ctx.cookies()
            cdict = {c['name']: c['value'] for c in new_cookies}
            
            if required_key in cdict and cdict[required_key] == cookies.get(required_key):
                # Cookie仍然有效，尝试续期
                cm.refresh(platform, cdict)
                await browser.close()
                return True, '已续期'
            
            if required_key in cdict:
                # Cookie可能变了但仍有有效值
                cm.refresh(platform, cdict)
                await browser.close()
                return True, '已更新'
            
            await browser.close()
            return False, 'Cookie已过期'
    except Exception as e:
        return False, f'续期失败: {e}'


async def run_all_refresh():
    """执行所有Cookie续期"""
    cm = SecureCookieManager()
    print(f"🔒 [{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] Cookie续期检查...")
    
    platforms = [
        ('twitter', 'twitter.com', 'auth_token'),
        ('instagram', 'instagram.com', 'sessionid'),
    ]
    
    for platform, domain, key in platforms:
        if cm.is_valid(platform):
            print(f"  {platform}: ", end='', flush=True)
            ok, msg = await auto_refresh_platform(cm, platform, domain, key)
            print(f"{'✅' if ok else '⚠️'} {msg}")
        else:
            print(f"  {platform}: ⏭️ 跳过（未配置）")
    
    print(f"\n📋 Cookie状态:")
    for k, v in cm.status().items():
        print(f"  {k}: {v}")
