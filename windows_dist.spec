# -*- mode: python -*-
a = Analysis(['app.py'],
             pathex=['C:\\Users\\Matthew\\Dropbox\\progs\\visram'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
# the following removes a warning popup
# see http://stackoverflow.com/questions/19055089
for d in a.datas:
    if 'pyconfig' in d[0]:
        a.datas.remove(d)
        break
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='visram.exe',
          debug=False,
          strip=None,
          upx=True,
          console=False )
