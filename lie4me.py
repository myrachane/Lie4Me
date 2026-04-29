"""
╔══════════════════════════════════════╗
║  LIE4ME  -  Terminal Sniper Game     ║
╚══════════════════════════════════════╝
Controls (in-game):
  ARROW KEYS  - Move crosshair
  SPACE       - Toggle hold-breath (steadies aim, expires)
  ENTER       - Fire / Confirm
  ESC / Q     - Back / Quit
  enjoy gurls
"""

import sys, os, time, math, random, signal

IS_WIN = sys.platform == 'win32'

# Auto-install colorama 
if IS_WIN:
    try:
        import colorama
    except ImportError:
        os.system(f'"{sys.executable}" -m pip install colorama -q --disable-pip-version-check')
        import colorama
    colorama.init()
    import msvcrt, ctypes
    k32 = ctypes.windll.kernel32
  
    k32.SetConsoleMode(k32.GetStdHandle(-11), 7)
    os.system('mode con: cols=92 lines=42 >nul 2>&1')
    os.system('title LIE4ME >nul 2>&1')
else:
    import tty, termios, select


def fc(r, g, b):
    return f'\033[38;2;{r};{g};{b}m'

RST   = '\033[0m'
BLD   = '\033[1m'
HIDE  = '\033[?25l'
SHOW  = '\033[?25h'
HOME  = '\033[H'
CLR   = '\033[2J\033[H'
SAVEC = '\033[s'
LODC  = '\033[u'

# Palette
G_  = fc(0,255,65)      # green bright
GD  = fc(0,130,42)      # green dim
GK  = fc(0,60,18)       # green dark
GP  = fc(0,14,6)        # green near-black
YE  = fc(240,207,24)    # yellow
YD  = fc(122,96,8)      # yellow dim
RE  = fc(255,32,32)     # red
RD  = fc(136,16,16)     # red dim
CY  = fc(0,216,248)     # cyan
CD  = fc(0,80,100)      # cyan dim
WH  = fc(204,255,204)   # white-green
WB  = fc(238,255,238)   # white bright
GR  = fc(68,119,68)     # grey-green
GRD = fc(34,51,34)      # grey-green dark
OR  = fc(255,136,0)     # orange
BL  = fc(170,0,0)       # blood red
MF  = fc(255,238,136)   # muzzle flash
SRM = fc(0,48,64)       # scope rim


W, H      = 90, 38
TARGET_Y  = 24
GROUND_Y  = 25
SCOPE_RX  = 17    # half-width  in columns
SCOPE_RY  = 8     # half-height in rows
FPS       = 14


# Each cell: (char, colour_str, bold_bool)
_BLANK = (' ', GP, False)
grid = [list([_BLANK] * W) for _ in range(H)]

def mk():
    global grid
    grid = [list([_BLANK] * W) for _ in range(H)]

def sc(x, y, ch, col=None, bold=False):
    if 0 <= x < W and 0 <= y < H:
        grid[y][x] = (ch, col if col is not None else G_, bold)

def st(x, y, s, col=None, bold=False):
    for i, ch in enumerate(s):
        sc(x + i, y, ch, col, bold)

def fl(x, y, w, h, ch, col=None):
    c = col if col is not None else GP
    for j in range(y, min(y + h, H)):
        for i in range(x, min(x + w, W)):
            grid[j][i] = (ch, c, False)

def bx(x, y, w, h, col, style=0):
    if style == 1:
        tl,tr,bl,br,hz,vt = '╔','╗','╚','╝','═','║'
    else:
        tl,tr,bl,br,hz,vt = '┌','┐','└','┘','─','│'
    sc(x, y, tl, col)
    sc(x+w-1, y, tr, col)
    sc(x, y+h-1, bl, col)
    sc(x+w-1, y+h-1, br, col)
    for i in range(1, w-1):
        sc(x+i, y, hz, col)
        sc(x+i, y+h-1, hz, col)
    for j in range(1, h-1):
        sc(x, y+j, vt, col)
        sc(x+w-1, y+j, vt, col)

def render():
    buf = [HOME]
    for row in grid:
        prev_col = None
        prev_bold = False
        for ch, col, bold in row:
            # Bold transition
            if bold and not prev_bold:
                buf.append(BLD)
            elif not bold and prev_bold:
                buf.append(RST)
                prev_col = None  
          
            if col != prev_col:
                buf.append(col)
                prev_col = col
            buf.append(ch)
            prev_bold = bold
        buf.append(RST + '\n')
    sys.stdout.write(''.join(buf))
    sys.stdout.flush()


# Returns a set of key-name strings pressed since last call.
# Also maintains a global `keys_down` set for continuous hold tracking.
keys_down = set()
_ARROW_MAP_WIN = {'\x48': 'UP', '\x50': 'DOWN', '\x4b': 'LEFT', '\x4d': 'RIGHT'}
_ARROW_MAP_NIX = {'[A': 'UP', '[B': 'DOWN', '[D': 'LEFT', '[C': 'RIGHT'}

def poll_keys():
    """Return list of newly-pressed key names (non-blocking)."""
    pressed = []
    if IS_WIN:
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ('\x00', '\xe0'):
                ch2 = msvcrt.getwch()
                if ch2 in _ARROW_MAP_WIN:
                    pressed.append(_ARROW_MAP_WIN[ch2])
            elif ch == '\x1b':
                pressed.append('ESC')
            elif ch in ('\r', '\n'):
                pressed.append('ENTER')
            elif ch == ' ':
                pressed.append('SPACE')
            elif ch.lower() == 'q':
                pressed.append('ESC')
            elif ch.lower() == 'w':
                pressed.append('UP')
            elif ch.lower() == 's':
                pressed.append('DOWN')
            elif ch.lower() == 'a':
                pressed.append('LEFT')
            elif ch.lower() == 'd':
                pressed.append('RIGHT')
    else:
        old = termios.tcgetattr(sys.stdin.fileno())
        try:
            tty.setraw(sys.stdin.fileno())
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    r2, _, _ = select.select([sys.stdin], [], [], 0.04)
                    if r2:
                        seq = sys.stdin.read(2)
                        if seq in _ARROW_MAP_NIX:
                            pressed.append(_ARROW_MAP_NIX[seq])
                        else:
                            pressed.append('ESC')
                    else:
                        pressed.append('ESC')
                elif ch in ('\r', '\n'):
                    pressed.append('ENTER')
                elif ch == ' ':
                    pressed.append('SPACE')
                elif ch.lower() == 'q':
                    pressed.append('ESC')
                elif ch.lower() == 'w':
                    pressed.append('UP')
                elif ch.lower() == 's':
                    pressed.append('DOWN')
                elif ch.lower() == 'a':
                    pressed.append('LEFT')
                elif ch.lower() == 'd':
                    pressed.append('RIGHT')
        except Exception:
            pass
        finally:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
    return pressed




MISSIONS = [
    dict(
        id=1, code='CLEAN HANDS', bg=0,
        target='Viktor Renko', alias='"The Accountant"',
        loc='Central District - Meridian Boulevard',
        intel=[
            'Launders funds for three separate cartels.',
            'Routine walk: 1400hrs, east-to-west, boulevard.',
            'One window. Clear line of sight. Use it.',
        ],
        warning='Unarmed civilian escort present. Collateral forbidden.',
        dist='387m', wind=2.0, wdir=1, guards=2, speed=0.09, sway=0.9,
        gcols=[OR, OR],
        goff=[(10, 0), (-12, 0)],
    ),
    dict(
        id=2, code='BLIND EYE', bg=1,
        target='Col. Marek Doss', alias='"The Hangman"',
        loc='Industrial Port - Loading Sector 9',
        intel=[
            'Convicted war criminal with active diplomatic immunity.',
            'Oversees illegal arms shipments every week.',
            'Body armor confirmed. Head shot is required.',
        ],
        warning='Armed escort - 3 guards. Body armor. Head shot only.',
        dist='512m', wind=5.5, wdir=-1, guards=3, speed=0.13, sway=1.4,
        gcols=[OR, OR, RE],
        goff=[(9, 0), (-13, 0), (20, -1)],
    ),
    dict(
        id=3, code='FINAL ECHO', bg=2,
        target='Anya Voss', alias='"The Handler"',
        loc='Hotel Kronos - Rooftop Exchange',
        intel=[
            'Sells operative identities to hostile buyers.',
            'Exchange: 2100hrs, rooftop access only.',
            'Window closes the moment the deal is struck.',
        ],
        warning='Multiple armed buyers on site. Rooftop - maximum exposure.',
        dist='274m', wind=1.0, wdir=1, guards=4, speed=0.18, sway=0.75,
        gcols=[OR, RE, OR, RE],
        goff=[(8, 0), (-10, 0), (16, -1), (-20, 0)],
    ),
]

SETUP_DUR = [55, 70, 80, 100]
SETUP_LABELS = [
    ('UNLOCKING CASE',     'Pelican 1720 - combo redacted - contents nominal'),
    ('LOADING MAGAZINE',   '7.62x51mm NATO - 5 rounds seated - bolt cycled'),
    ('MOUNTING STOCK',     'McMillan A5 - bipod deployed - 65 in-lb torque'),
    ('CALIBRATING SCOPE',  'S&B 5-25x56 - mil-dots zeroed - parallax set'),
]


state       = 'title'
mis_idx     = 0
frame       = 0

setup_phase = 0
setup_tick  = 0

tx          = 10.0   
tvx         = 0.09   
cx          = 45      # crosshair col (int)
cy          = 19      # crosshair row (int)

sway_phase  = 0.0
breath_held = False   # True while player is holding breath
breath_tick = 0       # counts up while held; auto-releases at limit

is_hit      = False
shot_tick   = 0

kills       = 0
shots_fired = 0


def get_sway():
    if breath_held:
        return 0.0, 0.0
    sp = MISSIONS[mis_idx]['sway']
    sx = math.sin(sway_phase * 1.3) * 2.3 * sp + math.cos(sway_phase * 0.78) * 1.2 * sp
    sy = math.sin(sway_phase * 0.97) * 1.6 * sp + math.cos(sway_phase * 1.1) * 0.85 * sp
    return sx, sy

# bg
BLDG_SETS = [
    # 0 - Central district
    [(0,8,10,16),(11,5,8,19),(20,9,10,15),(31,4,6,20),
     (38,7,11,17),(50,6,9,18),(60,9,8,15),(69,7,8,17),(78,10,8,14)],
    # 1 - Industrial port
    [(0,7,13,17),(14,10,8,14),(23,5,19,19),(43,9,9,15),
     (53,8,7,16),(61,6,13,18),(75,9,9,15)],
    # 2 - Night rooftop
    [(0,3,10,21),(11,1,8,23),(20,5,7,19),(28,2,14,22),
     (43,4,9,20),(53,6,11,18),(65,3,9,21),(75,7,9,17)],
]

def draw_city(style):
    # Sky
    for y in range(GROUND_Y):
        fl(0, y, W, 1, ' ', GP)
    # Stars
    for sx2, sy2, ch in [(3,0,'*'),(14,1,'.'),(22,0,'.'),(35,2,'*'),
                          (47,0,'.'),(58,1,'*'),(66,0,'.'),(75,2,'.')]:
        sc(sx2, sy2, ch, GK)
    if style == 2:
        sc(76, 0, 'O', GRD)  # moon
    if style == 1:            # crane
        for j in range(2, 12):
            sc(60, j, '|', GRD)
        st(44, 2, '----------------', GRD)
        sc(60, 2, '+', GRD)
    # Buildings
    for bx2, by, bw, bh in BLDG_SETS[style]:
        for j in range(by, min(by + bh, GROUND_Y)):
            for i in range(bx2, min(bx2 + bw, W)):
                if (i + j) % 4 == 0:
                    ch = '#'
                elif (i * 3 + j * 7) % 4 == 1:
                    ch = '|'
                else:
                    ch = ':'
                sc(i, j, ch, GK)
       
        for i in range(bx2, min(bx2 + bw, W)):
            sc(i, by, '-', GRD)
        sc(bx2, by, '+', GRD)
        if bx2 + bw - 1 < W:
            sc(bx2 + bw - 1, by, '+', GRD)
       
        for j in range(by + 1, by + bh - 1, 2):
            for i in range(bx2 + 1, bx2 + bw - 1, 3):
                if (i * 13 + j * 7 + frame) % 31 < 5:
                    sc(i, j, '#', GK)
    # Ground
    fl(0, GROUND_Y, W, 1, '=', GRD)
    fl(0, GROUND_Y + 1, W, 1, '%', GP)
    for j in range(GROUND_Y + 2, H):
        fl(0, j, W, 1, ' ', GP)
    
    fl(0, H-5, 20, 1, '%', GK)
    fl(0, H-4, 14, 1, '%', GK)
    fl(0, H-3, 10, 1, '%', GK)
    fl(0, H-2,  8, 1, '%', GK)
    fl(0, H-1,  7, 1, '%', GK)

#target
def draw_person(px, py, col, dead=False, alerted=False, walk=True):
    x = int(round(px))
    if not (2 <= x < W - 2):
        return
    if dead:
        st(x - 3, py, '--X--', BL)
        return
    wf = (frame // 6) % 4
    # Head
    sc(x, py - 3, 'O', col, alerted)
    # Body + arms
    sc(x,     py - 2, '|', col)
    sc(x - 1, py - 2, ['/', '|', '\\', '|'][wf] if walk else '/', col)
    sc(x + 1, py - 2, ['\\','|', '/', '|'][wf] if walk else '\\', col)
    sc(x, py - 1, '|', col)
    # Legs
    if walk:
        legs = ['/ \\', '/ |', '| \\', '\\_/'][wf]
        st(x - 1, py, legs, col)
    else:
        sc(x - 1, py, '/', col)
        sc(x + 1, py, '\\', col)
    # Alert markers
    if alerted:
        sc(x + 2, py - 4, '!', RE, True)
        sc(x + 3, py - 4, '!', RE, True)


def apply_scope(scx, scy):
    # Darken everything outside scope circle
    for y in range(H):
        for x in range(W):
            dx = (x - scx) / SCOPE_RX
            dy = (y - scy) / SCOPE_RY
            d  = math.sqrt(dx * dx + dy * dy)
            if d > 1.0:
                grid[y][x] = ('.', GP, False)
            elif d > 0.86:
                grid[y][x] = ('#', SRM, False)
    # Crosshair colour: green when breath held, red otherwise
    xh_col = CY if breath_held else RE
    # Horizontal line
    for i in range(scx - SCOPE_RX + 3, scx + SCOPE_RX - 3):
        if abs(i - scx) > 2 and 0 <= i < W:
            sc(i, scy, '-', xh_col)
    # Vertical line
    for j in range(scy - SCOPE_RY + 2, scy + SCOPE_RY - 2):
        if abs(j - scy) > 1 and 0 <= j < H:
            sc(scx, j, '|', xh_col)
    # Centre pip
    sc(scx, scy, '+', CY if breath_held else YE, True)
    # Mil dots
    for d in (-2, -1, 1, 2):
        sc(scx + d * 4, scy, 'o', CD)
        sc(scx, scy + d * 3, 'o', CD)


LOGO = [
    r'##      ## ######### ########  ##     ## ######## ',
    r'##      ##  ##    ## ##        ##     ## ##      ',
    r'##      ##  ##    ## #######   #########  ######  ',
    r'##      ##  ##    ## ##        ##     ## ##      ',
    r'######## ## ######### ########  ##     ## ######## ',
]

def draw_title():
    mk()
    # Noise
    for _ in range(45):
        sc(random.randint(0, W-1), random.randint(0, H-1), '.', GP)
    # Border bars
    for x in range(W):
        sc(x, 0, '=', GK)
        sc(x, H-1, '=', GK)
    # Logo
    lx = (W - 50) // 2
    glitch = frame % 110 < 3
    for i, line in enumerate(LOGO):
        col = CY if (glitch and i == random.randint(0, 4)) else G_
        st(lx, 3 + i, line, col, not glitch)
    if glitch:
        st(lx + random.randint(0, 15), 3 + random.randint(0, 4), '###%%###', CD)
    # Tagline
    sub = '-- one shot  .  one truth  .  no witnesses --'
    st((W - len(sub)) // 2, 10, sub, GD)
    st(5, 11, '-' * (W - 10), GP)
    # Decorative scope
    cxd, cyd = W // 2, 22
    for a in range(0, 360, 5):
        r2 = math.radians(a)
        ch = '#' if a % 30 == 0 else '.'
        sx2 = round(cxd + math.cos(r2) * 17)
        sy2 = round(cyd + math.sin(r2) * 6)
        sc(sx2, sy2, ch, GK)
    for i in range(cxd - 13, cxd + 14):
        if abs(i - cxd) > 2:
            sc(i, cyd, '-', GK)
    for j in range(cyd - 5, cyd + 6):
        if abs(j - cyd) > 1:
            sc(cxd, j, '|', GK)
    sc(cxd, cyd, '+', RD, True)
    # Blink prompt
    if frame // 25 % 2 == 0:
        msg = '[ ENTER ] Start    [ A/D ] Mission Select    [ Q ] Quit'
        st((W - len(msg)) // 2, 15, msg, YE, True)
    # Stats footer
    st(2, H-2, f'CONTRACTS: {len(MISSIONS)}   KILLS: {kills}   SHOTS: {shots_fired}', GK)
    st(W - 18, H-2, '// EYES ONLY //', GD)


def draw_select():
    mk()
    fl(0, 0, W, 1, '#', GK)
    fl(0, H-1, W, 1, '#', GK)
    st(2, 0, ' LIE4ME -- CONTRACT SELECTION', G_, True)
    bx(1, 1, W-2, H-2, GD, 1)
    st(4, 2, 'SELECT CONTRACT  |  W/S or ARROW KEYS to navigate', WB, True)
    st(4, 3, '-' * (W - 8), GP)
    for i, m in enumerate(MISSIONS):
        sel = (i == mis_idx)
        y0  = 5 + i * 9
        bx(3, y0, W-6, 8, G_ if sel else GK, 1 if sel else 0)
        if sel:
            fl(4, y0+1, W-8, 6, '.', GP)
        st(5, y0+1, f'[0{m["id"]}] OPERATION: {m["code"]}', YE if sel else GD, sel)
        st(5, y0+2, f'TARGET  : {m["target"]}  {m["alias"]}', WH if sel else GK, sel)
        st(5, y0+3, f'LOCATION: {m["loc"]}', CY if sel else GP)
        wd = '>>' if m['wdir'] > 0 else '<<'
        st(5, y0+4, f'RANGE: {m["dist"]}   WIND: {wd} {m["wind"]}mph   GUARDS: {m["guards"]}',
           GD if sel else GP)
        thr_bar = ['#...', '##..', '###.'][i]
        thr_col = [G_,    YE,     RE   ][i]
        thr_lbl = ['LOW', 'MEDIUM', 'HIGH'][i]
        st(5, y0+5, f'THREAT: [{thr_bar}] {thr_lbl}', thr_col if sel else GP, sel)
        if sel and frame // 20 % 2 == 0:
            st(W - 16, y0+3, '< SELECTED >', G_, True)
    st(4, H-3, '[ W/S ] Navigate   [ ENTER ] Deploy   [ ESC ] Back', GD)


def draw_brief():
    mk()
    m = MISSIONS[mis_idx]
    for _ in range(10):
        sc(random.randint(0, W-1), random.randint(0, H-1), '%', GP)
    fl(0, 0, W, 1, '#', GK)
    st(2, 0, f' LIE4ME -- MISSION 0{m["id"]}: {m["code"]}', G_, True)
    bx(1, 1, W-2, H-2, GD, 1)
    fl(2, 2, W-4, 1, '#', GK)
    st(3, 2, '| CLASSIFIED |  ORG: ECHO ZERO  | AUTHORIZED EYES ONLY |', YE, True)

    # Subject silhouette box
    bx(3, 4, 21, 13, GR)
    st(4, 4, ' | SUBJECT |', GD)
    sil = [
        '   /=========\\   ',
        '   | ####### |   ',
        '   | # ### # |   ',
        '   | ####### |   ',
        '   \\=========/   ',
        '   /=========\\   ',
    ]
    for i, line in enumerate(sil):
        st(3, 5 + i, line, GRD)
    st(4, 11, ' | CLASSIFIED |', RD)
    st(5, 12, f'   {m["alias"]}', GD)
    armed = 'YES' if m['id'] > 1 else 'NO'
    st(5, 13, f'   ARMED: {armed}', RE if m['id'] > 1 else G_)

    # Dossier panel
    st(26, 4,  '|-- TARGET DOSSIER ----------------------------------', GD)
    st(28, 6,  f'NAME     : {m["target"]}', WB, True)
    st(28, 7,  f'ALIAS    : {m["alias"]}', YE)
    st(28, 8,  f'LOCATION : {m["loc"]}', GD)
    st(26, 10, '|-- INTEL -------------------------------------------', GD)
    for i, line in enumerate(m['intel']):
        st(28, 12 + i, ' > ' + line, G_)
    st(26, 16, '|-- WARNING -----------------------------------------', RD)
    st(28, 17, ' ! ' + m['warning'], RE, True)

    # Engagement parameters
    st(3, 19,  '|-- ENGAGEMENT PARAMETERS ---------------------------', CD)
    wd = '>>' if m['wdir'] > 0 else '<<'
    st(5, 21,  f'DISTANCE : {m["dist"]}', CY)
    st(5, 22,  f'WIND     : {wd} {m["wind"]} mph', CY)
    st(5, 23,  f'GUARDS   : {m["guards"]} armed hostiles', RE)
    st(5, 24,  f'ROUNDS   : 5 x 7.62x51mm NATO    WEAPON: AS50', YE)
    thr_col = [G_, YE, RE][mis_idx]
    thr_lbl = ['LOW', 'MEDIUM', 'HIGH'][mis_idx]
    st(44, 21, f'THREAT   : {thr_lbl}', thr_col, True)
    st(44, 22, f'HANDLER  : ECHO ZERO', GD)

    # Quote
    st(3, 26, '-' * (W - 6), GP)
    st(5, 27, '"Hesitation is a luxury we cannot afford.', GD)
    st(5, 28, ' One shot. Clean. We were never here."  -- Echo Zero', GD)

    if frame // 28 % 2 == 0:
        st(12, 31, '[ ENTER ] Accept & Deploy              [ ESC ] Back', YE, True)


def art_case(t):
    st(7,  7,  '+' + '-'*72 + '+', GR)
    for j in range(8, 25):
        sc(7,  j, '|', GR)
        sc(80, j, '|', GR)
    st(7, 25, '+' + '-'*72 + '+', GR)
    fl(8, 8, 72, 17, '.', GP)
    bx(9, 9, 70, 14, GK)
    status = 'OPEN' if t > 0.5 else 'SEALED'
    col    = G_  if t > 0.5 else GD
    st(16, 11, f'PELICAN 1720  |  SERIAL: L4M-0099  |  STATUS: {status}', col)
    if t > 0.3:
        st(15, 15, '  |==|---------------------------------------|====|---> ', G_, True)
    else:
        st(15, 15, '  .................................................... ', GP)
    if t > 0.85:
        st(20, 20, 'CONTENTS: NOMINAL  --  READY FOR ASSEMBLY', G_, True)

def art_mag(t):
    rds = min(5, int(t * 6.2))
    bx(34, 5, 14, 20, GR)
    fl(35, 6, 12, 18, '.', GP)
    st(36, 6, ' ## MAG ##', GK)
    for r in range(5):
        loaded = r < rds
        y      = 8 + r * 3
        if loaded:
            st(36, y,   '|===========|', YE, True)
            st(36, y+1, '| 7.62 NATO |', YD)
        else:
            st(36, y, '.  .  .  .  .', GP)
    st(34, 26, '+------+-------+', GR)
    sc(41, 27, '|', GR)
    sc(41, 28, '|', GR)
    st(50, 15, '=' * 30, G_)
    st(50, 14, ' RECEIVER - CHAMBER CLEAR', GD)
    bar_str = '#' * rds + '.' * (5 - rds)
    st(16, 31, f'MAGAZINE: [{bar_str}]  {rds}/5 ROUNDS', YE, rds == 5)
    if rds == 5:
        st(24, 32, 'FULLY SEATED  .  BOLT CYCLED', G_, True)

def art_stock():
    y0 = 16
    st(3,  y0-2, '     /----\\', G_)
    st(3,  y0-1, '     |    |', G_)
    st(3,  y0,   '-----+    +-------------------------------------------> ', G_, True)
    st(3,  y0+1, '     |    |', G_)
    st(3,  y0+2, '     \\----/', G_)
    st(20, y0-2, '|==================|', G_, True)
    st(20, y0-1, '|                  |', G_, True)
    st(20, y0,   '+  AS50  Anti-Mat  +', G_, True)
    st(20, y0+1, '|                  |', G_, True)
    st(20, y0+2, '|=======+===========|', G_, True)
    st(20, y0+3, '        |  |======|', G_)
    st(20, y0+4, '        |  |  MAG |', G_)
    st(20, y0+5, '        +==+=======', G_)
    st(25, y0-4, '  |========================|', CY, True)
    st(25, y0-3, '  |  ~ ~ ~ S&B 5-25x56 ~   |< scope', CY, True)
    st(25, y0-2, '  |========================|', CY, True)
    st(21, y0+3, ' /             \\', GR)
    st(19, y0+4, '/                 \\', GR)
    st(57, y0-1, '|======|', GD)
    st(57, y0,   '| SUP  |', GD)
    st(57, y0+1, '|======|', GD)
    st(3, H-7, 'BIPOD : DEPLOYED [OK]     TORQUE: 65 in-lb [OK]     CHEEK: SET [OK]', CY)

def art_scope():
    cxd, cyd = 44, 17
    ry, rx = 8, 16
    for a in range(0, 360, 3):
        r2  = math.radians(a)
        ch  = '#' if a % 30 == 0 else '.'
        sx2 = round(cxd + math.cos(r2) * rx)
        sy2 = round(cyd + math.sin(r2) * ry)
        sc(sx2, sy2, ch, SRM)
    for i in range(cxd - rx + 3, cxd + rx - 3):
        if abs(i - cxd) > 2:
            sc(i, cyd, '-', CY)
    for j in range(cyd - ry + 2, cyd + ry - 2):
        if abs(j - cyd) > 1:
            sc(cxd, j, '|', CY)
    sc(cxd, cyd, '+', RE, True)
    for d in (-2, -1, 1, 2):
        sc(cxd + d * 4, cyd, 'o', CD)
        sc(cxd, cyd + d * 3, 'o', CD)
    st(3, H-7, 'ELEVATION: +2.4 MOA [OK]     WINDAGE: +0.5 MOA [OK]     MAG: 18x [OK]', GD)
    st(3, H-6, 'MIL-DOTS : CALIBRATED [OK]   PARALLAX: ZEROED [OK]', GD)

def draw_setup():
    mk()
    fl(0, 0, W, 1, '=', GK)
    fl(0, H-1, W, 1, '=', GK)
    st(2, 0, ' LIE4ME -- WEAPON ASSEMBLY SEQUENCE', G_, True)
    label, sub = SETUP_LABELS[setup_phase]
    st(2, 2, '> ' + label, WB, True)
    st(5, 4, sub, GD)
    t = min(setup_tick / SETUP_DUR[setup_phase], 1.0)
    if   setup_phase == 0: art_case(t)
    elif setup_phase == 1: art_mag(t)
    elif setup_phase == 2: art_stock()
    else:                  art_scope()
    # Step indicators
    for i, (lbl, _) in enumerate(SETUP_LABELS):
        if i < setup_phase:
            col, mk_ch = G_,  '[OK]'
        elif i == setup_phase:
            col, mk_ch = YE,  '[>>]'
        else:
            col, mk_ch = GK,  '[ ]'
        st(3 + i * 22, H-4, f'{mk_ch} {lbl}', col, i == setup_phase)
    # Progress bar
    bw     = 56
    filled = int(t * bw)
    bar    = '[' + '#' * filled + '.' * (bw - filled) + ']'
    st(16, H-2, bar, G_)
    st(74, H-2, f'{int(t*100)}%', YE, True)

# ─────────────────────────────────────────────────────────────
#  READY SCREEN
# ─────────────────────────────────────────────────────────────
READY_ART = [
    r'##  ##  ######  ##  ##  #####  ##  ## ',
    r'##  ## ##       ##  ## ##   ## ##  ## ',
    r'####### ######  ####### ##   ## ###### ',
    r'##  ## ##       ##  ## ##   ## ##  ## ',
    r'##  ##  ######  ##  ##  #####  ##  ## ',
]

def draw_ready():
    mk()
    fl(0, 0, W, 1, '=', GK)
    fl(0, H-1, W, 1, '=', GK)
    m  = MISSIONS[mis_idx]
    rx = (W - 38) // 2
    bx(rx - 3, 5, 44, 9, G_, 1)
    for i, line in enumerate(READY_ART):
        st(rx, 6 + i, line, G_, True)
    st(rx + 2, 12, 'WEAPON ASSEMBLED  .  POSITION ACQUIRED', GD)
    bx(rx - 3, 16, 44, 9, CD, 0)
    st(rx - 1, 17, f'TARGET  : {m["target"]}', YE, True)
    thr_lbl = ['LOW', 'MED', 'HIGH'][mis_idx]
    st(rx - 1, 18, f'RANGE   : {m["dist"]}    THREAT: {thr_lbl}', CY)
    wd = '>>' if m['wdir'] > 0 else '<<'
    st(rx - 1, 19, f'WIND    : {wd} {m["wind"]} mph', CY)
    st(rx - 1, 20, f'GUARDS  : {m["guards"]}  |  [SPACE] toggles hold-breath', GD)
    st(rx - 1, 21, f'AIM: ARROW KEYS   FIRE: ENTER', GD)
    st(rx - 1, 22, f'TIP: Aim first THEN hold breath. It times out.', GK)
    if frame // 25 % 2 == 0:
        st((W - 42) // 2, 27, '-->  PRESS  ENTER  TO  ASSUME  POSITION  <--', YE, True)


def draw_aim():
    m = MISSIONS[mis_idx]
    mk()
    draw_city(m['bg'])
    # Target
    draw_person(tx, TARGET_Y, YE, walk=True)
    # Guards
    for gi in range(m['guards']):
        ox, oy = m['goff'][gi]
        draw_person(tx + ox, TARGET_Y + oy, m['gcols'][gi], walk=True)
    # Scope with sway applied
    sw_x, sw_y = get_sway()
    scx = min(W-1, max(0, int(round(cx + sw_x))))
    scy = min(H-1, max(0, int(round(cy + sw_y))))
    apply_scope(scx, scy)
    # HUD strip
    fl(0, H-3, W, 3, ' ', GP)
    st(0, H-3, '-' * W, GK)
    breath_states = ['[=   ]', '[==  ]', '[=== ]', '[==  ]']
    bdisp  = '[HELD]' if breath_held else breath_states[frame // 8 % 4]
    sw_mag = math.sqrt(sw_x**2 + sw_y**2)
    wd     = '>' if m['wdir'] > 0 else '<'
    hud    = f'WIND:{wd}{m["wind"]}mph  DIST:{m["dist"]}  BREATH:{bdisp}  SWAY:{sw_mag:.1f}  G:{m["guards"]}'
    st(1, H-2, hud, CY if breath_held else GD)
    if breath_held:
        st(66, H-2, 'BREATH HELD [OK]', G_, True)
    if frame // 25 % 2 == 0:
        st(1, H-1, '[ENTER] Fire  [SPACE] Toggle Breath  [ESC] Abort', CY)
    # Crosshair position indicator (debugging aid)
    st(W - 12, H-1, f'X:{cx} Y:{cy}', GP)


def draw_end():
    m = MISSIONS[mis_idx]
    t = shot_tick
    mk()
    draw_city(m['bg'])

    if is_hit:
        if t < 4:
            # Muzzle flash whiteout
            fl(0, 0, W, H, '#', MF)
            st((W - 8) // 2, H // 2, 'B O O M', RE, True)
        else:
            if t < 20:
                draw_person(tx, TARGET_Y, RE)          # stagger
            else:
                itx = int(round(tx))
                st(itx - 3, TARGET_Y, '--X--', BL)    # body down
                for d in range(6):                      # blood
                    sc(itx - 2 + d, TARGET_Y - 1, '#', BL)
            # Muzzle flash lingers briefly
            if t < 10:
                sc(3, H-5, '*', MF, True)
                sc(4, H-5, '*', MF, True)
            if t < 16:
                st(1, H-6, '[FIRE]-->>>--', OR, True)
            # Guards scatter
            for gi in range(m['guards']):
                ox, oy = m['goff'][gi]
                if t > 14:
                    flee = ox + (1 if ox > 0 else -1) * int((t - 14) * 0.45)
                else:
                    flee = ox
                draw_person(tx + flee, TARGET_Y + oy, OR, alerted=True, walk=True)
        # Success card
        if t > 46:
            bx(10, 9, W - 20, 14, G_, 1)
            fl(11, 10, W - 22, 1, '#', GK)
            st(22, 10, ' [OK] TARGET NEUTRALIZED [OK] ', G_, True)
            st(14, 12, f'OPERATION {m["code"]}  .  FULFILLED', YE, True)
            st(14, 14, f'TARGET   : {m["target"]}', WH)
            st(14, 15, 'RESULT   : ELIMINATED  .  CLEAN SHOT', G_, True)
            st(14, 17, 'EXFIL    : IN PROGRESS  .  ETA 4 MIN', GD)
            st(14, 18, 'HANDLER  : "Good shot. We were never here."', GD)
            st(14, 20, 'STATUS   : [][] MISSION SUCCESS', G_, True)
            if frame // 22 % 2 == 0:
                if mis_idx < len(MISSIONS) - 1:
                    st(12, 22, '[ ENTER ] Next Contract        [ ESC ] Main Menu', CY, True)
                else:
                    st(16, 22, '[ ENTER ] Play Again    [ ESC ] Exit', CY, True)
    else:
        # Miss - target unharmed, guards alerted
        draw_person(tx, TARGET_Y, YE, alerted=t > 10, walk=True)
        for gi in range(m['guards']):
            ox, oy = m['goff'][gi]
            draw_person(tx + ox, TARGET_Y + oy, RE, alerted=t > 8)
        if t > 8 and frame // 7 % 2 == 0:
            st(11, 4, '!!! SHOT MISSED -- POSITION COMPROMISED !!!', RE, True)
        # Guard 1 return fire bullet travelling left
        if t > 35:
            bx2 = max(3, int(round(tx)) + 10 - int((t - 35) * 2.0))
            if 1 < bx2 < W - 1:
                sc(bx2,   TARGET_Y - 1, '*', OR, True)
                sc(bx2+1, TARGET_Y - 1, '-', OR)
        # Guard 2 fires at different angle
        if t > 42 and m['guards'] >= 2:
            bx3 = max(2, int(round(tx)) - 12 + int((t - 42) * 1.6))
            if 0 < bx3 < W - 2:
                sc(bx3, TARGET_Y, '>', RD, True)
        # Impact red flash
        if 65 < t < 73:
            fl(0, 0, W, H, '#', RD)
        elif t > 73:
            # Failure card
            bx(6, 8, W - 12, 16, RE, 1)
            fl(7, 9, W - 14, 1, '#', RD)
            st(16,  9, ' [X] OPERATIVE DOWN -- MISSION FAILED [X] ', RE, True)
            st(10, 11, '"They found the window."', WH)
            st(10, 12, '"The guards answered the shot."', WH)
            st(10, 13, '"You hesitated. It cost you everything."', RD)
            st(10, 15, f'OPERATION {m["code"]}   .   STATUS: FAILED', RE, True)
            st(10, 17, 'OPERATIVE : KIA', RE, True)
            st(10, 18, "HANDLER   : \"Echo Zero gone silent. You're alone.\"", GD)
            if frame // 22 % 2 == 0:
                st(10, 22, '[ ENTER ] Retry Mission        [ ESC ] Main Menu', YE, True)


def reset_aim():
    """Re-initialise all aim-state globals when entering aim screen."""
    global tx, tvx, cx, cy, sway_phase, breath_held, breath_tick
    m = MISSIONS[mis_idx]
    tx          = 10.0
    tvx         = m['speed']
    cx, cy      = 45, 19
    sway_phase  = 0.0
    breath_held = False
    breath_tick = 0

def main():
    global state, mis_idx, frame
    global setup_phase, setup_tick
    global tx, tvx, cx, cy, sway_phase, breath_held, breath_tick
    global is_hit, shot_tick, kills, shots_fired

    sys.stdout.write(CLR + HIDE)
    sys.stdout.flush()

    frame_dur = 1.0 / FPS
    last_t    = time.time()

    try:
        while True:
            # ── Timing ───────────────────────────────────────
            now = time.time()
            if now - last_t < frame_dur:
                time.sleep(0.005)
                continue
            last_t = now
            frame += 1

            # ── Input ────────────────────────────────────────
            keys = poll_keys()

            # ESC / Q always goes back one level
            if 'ESC' in keys:
                if   state == 'select': state = 'title';  frame = 0
                elif state == 'brief':  state = 'select'; frame = 0
                elif state == 'ready':  state = 'brief';  frame = 0
                elif state == 'aim':    state = 'brief';  frame = 0
                elif state == 'end':
                    state = 'title'; mis_idx = 0; frame = 0
                elif state == 'title':
                    break

            # State-specific input
            if state == 'title':
                if 'ENTER' in keys:
                    state = 'brief'; frame = 0
                if 'RIGHT' in keys or 'LEFT' in keys:
                    state = 'select'; frame = 0

            elif state == 'select':
                if 'DOWN' in keys:
                    mis_idx = min(len(MISSIONS) - 1, mis_idx + 1)
                if 'UP' in keys:
                    mis_idx = max(0, mis_idx - 1)
                if 'ENTER' in keys:
                    state = 'brief'; frame = 0

            elif state == 'brief':
                if 'ENTER' in keys:
                    state       = 'setup'
                    setup_phase = 0
                    setup_tick  = 0
                    frame       = 0

            elif state == 'setup':
              
                setup_tick += 1
                if setup_tick >= SETUP_DUR[setup_phase]:
                    setup_phase += 1
                    setup_tick   = 0
                    if setup_phase >= 4:
                        state = 'ready'; frame = 0

            elif state == 'ready':
                if 'ENTER' in keys:
                    state = 'aim'
                    reset_aim()
                    frame = 0

            elif state == 'aim':
                # Crosshair movement
                spd = 2
                if 'LEFT'  in keys: cx = max(SCOPE_RX + 1,     cx - spd)
                if 'RIGHT' in keys: cx = min(W - SCOPE_RX - 1, cx + spd)
                if 'UP'    in keys: cy = max(SCOPE_RY + 1,     cy - spd)
                if 'DOWN'  in keys: cy = min(H - SCOPE_RY - 3, cy + spd)
                # Breath toggle
                if 'SPACE' in keys:
                    if not breath_held:
                        breath_held = True
                        breath_tick = 0
                    else:
                        breath_held = False
                # Auto-expire breath hold
                if breath_held:
                    breath_tick += 1
                    if breath_tick > 15:
                        breath_held = False
                        breath_tick = 0
                # Fire
                if 'ENTER' in keys:
                    shots_fired += 1
                    sw_x, sw_y  = get_sway()
                    ax = cx + sw_x
                    ay = cy + sw_y
                    is_hit = (abs(ax - tx) <= 2.8 and abs(ay - TARGET_Y) <= 3.8)
                    if is_hit:
                        kills += 1
                    state     = 'end'
                    shot_tick = 0
                    frame     = 0
                # Physics update
                sway_phase += 0.07
                tx += tvx
                if tx > W - 6: tvx = -abs(tvx)
                if tx < 5:     tvx =  abs(tvx)

            elif state == 'end':
                shot_tick += 1
                # desicion
                done = (is_hit and shot_tick > 46) or (not is_hit and shot_tick > 73)
                if 'ENTER' in keys and done:
                    if is_hit and mis_idx < len(MISSIONS) - 1:
                        mis_idx += 1
                        state    = 'brief'
                    elif is_hit:
                        mis_idx = 0
                        state   = 'title'
                    else:
                        # Miss - retry same mission
                        state = 'brief'
                    frame = 0

            # ── Draw ─────────────────────────────────────────
            if   state == 'title':  draw_title()
            elif state == 'select': draw_select()
            elif state == 'brief':  draw_brief()
            elif state == 'setup':  draw_setup()
            elif state == 'ready':  draw_ready()
            elif state == 'aim':    draw_aim()
            elif state == 'end':    draw_end()

            render()

    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW + RST)
        sys.stdout.flush()
        print()
        print('Echo Zero signing off.')


if __name__ == '__main__':
    main()
