import random
import sys
import pygame

pygame.init()
WIDTH, HEIGHT = 800, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Space Invaders ULTRA - Asteroids, Energy & Elite Aliens')
clock = pygame.time.Clock()
FONT = pygame.font.SysFont('consolas', 23)
SMALL = pygame.font.SysFont('consolas', 17)
BIG = pygame.font.SysFont('consolas', 49, bold=True)
WHITE, GREEN, RED = (235, 240, 255), (70, 255, 140), (255, 85, 110)
CYAN, YELLOW, PURPLE, ORANGE = (75, 225, 255), (255, 225, 90), (190, 115, 255), (255, 145, 55)
ALIEN_COLORS = [(255, 100, 160), (255, 190, 80), (100, 235, 255), (155, 120, 255)]
POWERUPS = {
    'triple': (PURPLE, '3', 'TRIPLE SHOT', 11000),
    'rapid': (YELLOW, 'R', 'RAPID FIRE', 10000),
    'shield': (CYAN, 'S', 'SHIELD', 12000),
    'laser': (ORANGE, 'L', 'POWER LASER', 9000),
    'bigship': (GREEN, 'B', 'BIG SHIP', 14000),
    'repair': (GREEN, '+', 'REPAIR +25 HP', 0),
    'overdrive': (ORANGE, 'O', 'OVERDRIVE', 9000),
}
SHOP = [
    ('damage', 'Weapon damage +1', 70, 200),
    ('fire', 'Faster shooting', 65, 100),
    ('speed', 'Faster movement', 50, 100),
    ('life', 'Extra life (+1)', 90, 1000),
    ('armor', 'Damage protection (1 hit)', 100, 100),
    ('spread', 'Permanent multi-shot', 130, 10),
    ('pet', 'Robot companion', 120, 10),
    ('rocket', 'Rocket ammo (+3)', 75, 100),
    ('bomb', 'Bomb ammo (+2)', 95, 100),
    ('super', 'Super beam charge (+1)', 160, 100),
]
stars = [(random.randrange(WIDTH), random.randrange(HEIGHT), random.choice((1, 1, 2))) for _ in range(90)]

def text(message, font, color, x, y, center=False):
    img = font.render(str(message), True, color)
    screen.blit(img, img.get_rect(center=(x, y)) if center else (x, y))

def alien(x, y, row=0, reinforcement=False):
    return {'rect': pygame.Rect(x, y, 38, 29), 'color': ALIEN_COLORS[row % 4],
            'hp': 2 if reinforcement else 1, 'reinforcement': reinforcement, 'elite': False}

def new_wave(level):
    enemies = [alien(95 + col * 67, 75 + row * 52, row)
               for row in range(4) for col in range(9)]
    if level >= 2:
        for enemy in random.sample(enemies, min(len(enemies), 2 + level // 2)):
            enemy['elite'] = True
            enemy['hp'] = 2 + level // 3
            enemy['color'] = ORANGE
    return enemies

def make_boss(level):
    hp = 20 + level * 7
    return {'rect': pygame.Rect(WIDTH // 2 - 75, 90, 150, 65), 'hp': hp,
            'max_hp': hp, 'direction': 1, 'last_attack': 0, 'last_spawn': 0,
            'phase': 0, 'type': (level // 3 - 1) % 3}

def reset():
    return {'player': pygame.Rect(WIDTH // 2 - 23, HEIGHT - 76, 46, 32),
            'bullets': [], 'enemy_bullets': [], 'aliens': new_wave(1), 'boss': None,
            'drops': [], 'direction': 1, 'level': 1, 'score': 0, 'coins': 0,
            'lives': 3, 'hp': 100, 'max_hp': 100, 'dash_ready': 0, 'particles': [], 'energy': 0, 'asteroids': [], 'last_asteroid': 0, 'regen_clock': 0, 'kills_this_wave': 0, 'armor_hits': 0, 'upgrades': {}, 'last_shot': 0,
            'last_enemy_shot': 0, 'game_over': False, 'shop': False,
            'invulnerable_until': 0, 'active': {}, 'notice': 'LEVEL 1!',
            'notice_until': 1600, 'paused': False, 'combo': 0, 'last_kill': -10000, 'best_combo': 0, 'total_kills': 0, 'pets': 0, 'rockets': 2, 'bombs': 1, 'supers': 0, 'last_pet': 0, 'skin': 0, 'boxes': [], 'boxes_opened': 0, 'boss_kills': 0, 'achievements': set(), 'mission_claimed': set(), 'last_special': 0}

def notice(s, message, now, duration=1500):
    s['notice'], s['notice_until'] = message, now + duration

def finish_wave(s, now):
    s['shop'] = True
    s['bullets'].clear()
    s['enemy_bullets'].clear()
    s['drops'].clear()
    s['aliens'].clear()
    s['boss'] = None
    check_achievements(s, now)

def next_wave(s, now):
    s['level'] += 1
    s['boss'] = make_boss(s['level']) if s['level'] % 3 == 0 else None
    s['aliens'] = [] if s['boss'] else new_wave(s['level'])
    s['direction'] = 1
    s['shop'] = False
    s['last_enemy_shot'] = now
    s['boxes'].clear()
    s['asteroids'].clear()
    s['kills_this_wave'] = 0
    s['hp'] = min(s['max_hp'], s['hp'] + 15)
    check_achievements(s, now)
    notice(s, 'BOSS + ALIEN REINFORCEMENTS!' if s['boss'] else f'LEVEL {s["level"]}!', now, 1900)

def buy(s, index, now):
    if index in (12, 13):
        key = 'regen' if index == 12 else 'energy'
        cost = (110 if index == 12 else 100) + 15 * (s['level'] - 1)
        if s['coins'] < cost:
            notice(s, 'NOT ENOUGH COINS!', now)
        elif s['upgrades'].get(key, 0) >= 5:
            notice(s, 'UPGRADE MAXED!', now)
        else:
            s['coins'] -= cost
            s['upgrades'][key] = s['upgrades'].get(key, 0) + 1
            notice(s, 'AUTO REPAIR UPGRADED!' if index == 12 else 'ENERGY BOOST UPGRADED!', now)
        return
    if index in (10, 11):
        cost = (85 if index == 10 else 65) + 15 * (s['level'] - 1)
        if s['coins'] < cost:
            notice(s, 'NOT ENOUGH COINS!', now)
        elif index == 11 and s['hp'] == s['max_hp']:
            notice(s, 'HP ALREADY FULL!', now)
        else:
            s['coins'] -= cost
            if index == 10:
                s['max_hp'] += 25
                s['hp'] += 25
                notice(s, 'MAX HP +25!', now)
            else:
                s['hp'] = min(s['max_hp'], s['hp'] + 40)
                notice(s, 'SHIP REPAIRED +40 HP!', now)
        return
    key, name, base, cap = SHOP[index]
    count = s['upgrades'].get(key, 0)
    cost = base + 10 * (s['level'] - 1)
    if count >= cap:
        notice(s, 'UPGRADE MAXED OUT! No more upgrades available.', now)
    elif s['coins'] < cost:
        notice(s, 'SORRY, NOT ENOUGH COINS', now)
    else:
        s['coins'] -= cost
        s['upgrades'][key] = count + 1
        if key == 'life':
            s['lives'] += 1
        elif key == 'armor':
            s['armor_hits'] += 1
        elif key == 'pet':
            s['pets'] += 1
        elif key == 'rocket':
            s['rockets'] += 3
        elif key == 'bomb':
            s['bombs'] += 2
        elif key == 'super':
            s['supers'] += 1
        check_achievements(s, now)
        notice(s, name.upper() + ' BOUGHT!', now)

def spawn_shot(s):
    p = s['player']
    piercing = 'laser' in s['active']
    spread = s['upgrades'].get('spread', 0)
    offsets = (-36, -18, 0, 18, 36) if 'bigship' in s['active'] else (
        (-26, -13, 0, 13, 26) if spread >= 2 else
        (-17, 0, 17) if 'triple' in s['active'] or spread >= 1 else (0,))
    for offset in offsets:
        width = 10 if piercing else 6
        s['bullets'].append({'rect': pygame.Rect(p.centerx + offset - width // 2,
                         p.top - 19, width, 19), 'vx': -130 if offset < 0 else (130 if offset > 0 else 0),
                         'piercing': piercing, 'damage': 1 + s['upgrades'].get('damage', 0),
                         'hit': set()})

def draw_player(p, big=False, skin=0):
    x, y = p.center
    ship_color = (CYAN, PURPLE, ORANGE, YELLOW, GREEN)[skin % 5]
    if big:
        pygame.draw.polygon(screen, GREEN, [(x, y - 37), (x - 48, y + 13),
                            (x - 56, y + 26), (x + 56, y + 26), (x + 48, y + 13)])
        pygame.draw.polygon(screen, WHITE, [(x, y - 26), (x - 14, y + 5), (x + 14, y + 5)])
        pygame.draw.circle(screen, CYAN, (x, y + 8), 10)
    else:
        pygame.draw.polygon(screen, ship_color, [(x, y - 21), (x - 23, y + 14), (x + 23, y + 14)])
        pygame.draw.rect(screen, GREEN, (x - 7, y + 1, 14, 17))
        pygame.draw.rect(screen, WHITE, (x - 4, y - 10, 8, 10))

def draw_alien(a):
    r, c = a['rect'], a['color']
    pygame.draw.rect(screen, c, (r.x + 5, r.y + 3, r.width - 10, r.height - 9), border_radius=7)
    pygame.draw.rect(screen, c, (r.x, r.y + 11, r.width, 10), border_radius=4)
    pygame.draw.rect(screen, c, (r.x + 6, r.bottom - 7, 7, 7))
    pygame.draw.rect(screen, c, (r.right - 13, r.bottom - 7, 7, 7))
    pygame.draw.rect(screen, (12, 15, 33), (r.x + 11, r.y + 11, 5, 6))
    pygame.draw.rect(screen, (12, 15, 33), (r.right - 16, r.y + 11, 5, 6))
    if a['reinforcement'] or a.get('elite'):
        pygame.draw.rect(screen, YELLOW, r, 2, border_radius=5)
    if a.get('elite'):
        pygame.draw.circle(screen, WHITE, (r.centerx, r.y + 5), 3)

def draw_coin(cx, cy, radius=12):
    pygame.draw.circle(screen, (130, 75, 18), (cx + 2, cy + 2), radius + 1)
    pygame.draw.circle(screen, YELLOW, (cx, cy), radius)
    pygame.draw.circle(screen, (255, 250, 170), (cx, cy), radius - 4, 2)
    text('$', SMALL, (110, 75, 15), cx, cy - 1, center=True)

def draw_shopfront(cx, top):
    pygame.draw.rect(screen, (48, 59, 99), (cx - 75, top + 31, 150, 70), border_radius=8)
    pygame.draw.rect(screen, (35, 190, 220), (cx - 56, top + 54, 112, 35), border_radius=4)
    pygame.draw.rect(screen, (18, 29, 65), (cx - 12, top + 54, 24, 47))
    pygame.draw.polygon(screen, PURPLE, [(cx - 85, top + 33), (cx - 65, top + 4), (cx + 65, top + 4), (cx + 85, top + 33)])
    for i in range(6):
        pygame.draw.rect(screen, RED if i % 2 else WHITE, (cx - 75 + i * 25, top + 33, 25, 15))
    pygame.draw.rect(screen, (18, 26, 58), (cx - 62, top + 9, 124, 22), border_radius=5)
    text('SHOP', SMALL, YELLOW, cx, top + 20, center=True)

def draw_upgrade_icon(key, cx, cy):
    pygame.draw.rect(screen, (31, 46, 83), (cx - 22, cy - 20, 44, 40), border_radius=9)
    if key == 'damage':
        pygame.draw.polygon(screen, ORANGE, [(cx,cy-17),(cx-9,cy+1),(cx-1,cy+1),(cx-5,cy+17),(cx+12,cy-5),(cx+3,cy-5)])
    elif key == 'fire':
        for dx in (-10,0,10):
            pygame.draw.rect(screen, YELLOW, (cx+dx-3,cy-12,6,23), border_radius=3)
    elif key == 'speed':
        pygame.draw.polygon(screen, CYAN, [(cx+17,cy),(cx-5,cy-14),(cx-5,cy-5),(cx-17,cy-5),(cx-17,cy+5),(cx-5,cy+5),(cx-5,cy+14)])
    elif key == 'life':
        pygame.draw.circle(screen, RED, (cx-7,cy-5), 9)
        pygame.draw.circle(screen, RED, (cx+7,cy-5), 9)
        pygame.draw.polygon(screen, RED, [(cx-16,cy-3),(cx+16,cy-3),(cx,cy+17)])
    elif key == 'armor':
        pygame.draw.polygon(screen, CYAN, [(cx,cy-17),(cx+15,cy-10),(cx+12,cy+9),(cx,cy+18),(cx-12,cy+9),(cx-15,cy-10)])
        pygame.draw.line(screen, WHITE, (cx,cy-11), (cx,cy+11), 3)
    elif key == 'spread':
        for dx in (-12,0,12):
            pygame.draw.line(screen, GREEN, (cx,cy+12), (cx+dx,cy-13), 4)
    elif key == 'pet':
        pygame.draw.circle(screen, CYAN, (cx,cy), 13)
        for dx in (-5,5): pygame.draw.circle(screen, WHITE, (cx+dx,cy-3), 3)
    elif key in ('rocket','bomb','super'):
        pygame.draw.circle(screen, {'rocket':ORANGE,'bomb':RED,'super':PURPLE}[key], (cx,cy), 13)
        text({'rocket':'R','bomb':'B','super':'S'}[key], SMALL, WHITE, cx,cy,center=True)


ACHIEVEMENTS = [('first', 'FIRST CONTACT', 1), ('hunter', 'ALIEN HUNTER', 50),
                ('combo', 'COMBO MASTER', 10), ('boss', 'BOSS SLAYER', 1),
                ('box', 'LUCKY FIND', 3), ('rich', 'COIN COLLECTOR', 500)]

def check_achievements(s, now):
    values = {'first': s['total_kills'], 'hunter': s['total_kills'],
              'combo': s['best_combo'], 'boss': s['boss_kills'],
              'box': s['boxes_opened'], 'rich': s['coins']}
    for key, title, target in ACHIEVEMENTS:
        if values[key] >= target and key not in s['achievements']:
            s['achievements'].add(key)
            s['coins'] += 40
            notice(s, 'ACHIEVEMENT: ' + title + ' +40 COINS!', now, 2600)
    # Three repeatable mission milestones, paid once per run.
    for key, done, target, reward in [('kills',s['total_kills'],25,75), ('waves',s['level'],5,125), ('bosses',s['boss_kills'],2,200)]:
        if done >= target and key not in s['mission_claimed']:
            s['mission_claimed'].add(key)
            s['coins'] += reward
            notice(s, 'MISSION COMPLETE: ' + key.upper() + f' +{reward} COINS!', now, 2600)

def blast(s, x, y, radius, damage, now):
    for a in s['aliens'][:]:
        if (a['rect'].centerx-x)**2 + (a['rect'].centery-y)**2 <= radius**2:
            a['hp'] -= damage
            if a['hp'] <= 0:
                s['aliens'].remove(a)
                award_kill(s, a, now)
    if s['boss'] and (s['boss']['rect'].centerx-x)**2 + (s['boss']['rect'].centery-y)**2 <= (radius+65)**2:
        s['boss']['hp'] -= damage
        if s['boss']['hp'] <= 0:
            defeat_boss(s, now)

def make_particles(s, x, y, color, amount=12):
    for _ in range(amount):
        s['particles'].append({'x': float(x), 'y': float(y),
            'vx': random.uniform(-170, 170), 'vy': random.uniform(-170, 170),
            'life': random.uniform(.25, .7), 'color': color})

def hurt_player(s, now, damage=20):
    if now < s['invulnerable_until'] or 'shield' in s['active']:
        return
    if s['armor_hits']:
        s['armor_hits'] -= 1
        notice(s, 'ARMOR BLOCKED DAMAGE!', now)
    else:
        s['hp'] -= damage
        make_particles(s, *s['player'].center, RED, 16)
        notice(s, f'SHIP HIT! -{damage} HP', now)
        if s['hp'] <= 0:
            s['lives'] -= 1
            if s['lives'] <= 0:
                s['hp'] = 0
                s['game_over'] = True
            else:
                s['hp'] = s['max_hp']
                notice(s, 'SHIP DESTROYED! EXTRA LIFE USED!', now)
    s['invulnerable_until'] = now + 1400

def award_kill(s, a, now):
    s['combo'] = s['combo'] + 1 if now - s['last_kill'] < 2200 else 1
    s['last_kill'] = now
    s['best_combo'] = max(s['best_combo'], s['combo'])
    s['total_kills'] += 1
    s['kills_this_wave'] += 1
    s['energy'] = min(100, s['energy'] + 5 + s['upgrades'].get('energy', 0) * 2)
    mult = min(5, 1 + s['combo'] // 5)
    s['score'] += (25 if a.get('elite') else (15 if a['reinforcement'] else 10)) * mult
    s['coins'] += (14 if a.get('elite') else (8 if a['reinforcement'] else 5)) * mult
    make_particles(s, a['rect'].centerx, a['rect'].centery, a['color'], 10)
    if random.random() < 0.18:
        kind = random.choice(list(POWERUPS))
        s['drops'].append({'rect': pygame.Rect(a['rect'].centerx - 13,a['rect'].centery - 13,26,26),'kind':kind})
    if random.random() < 0.035:
        s['boxes'].append(pygame.Rect(a['rect'].centerx-15,a['rect'].centery-15,30,30))
    check_achievements(s, now)

def defeat_boss(s, now):
    if not s['boss']: return
    s['score'] += 500 + s['level'] * 100
    s['coins'] += 150 + s['level'] * 30
    s['boss_kills'] += 1
    make_particles(s, *s['boss']['rect'].center, ORANGE, 55)
    finish_wave(s, now)
    notice(s, 'GIANT BOSS DEFEATED! BONUS COINS!', now, 2000)

def open_box(s, now):
    reward = random.choice(('coins','life','rockets','bombs','super','shield','repair'))
    if reward == 'coins': s['coins'] += 100
    elif reward == 'life': s['lives'] += 1
    elif reward == 'repair': s['hp'] = min(s['max_hp'], s['hp'] + 45)
    elif reward == 'rockets': s['rockets'] += 4
    elif reward == 'bombs': s['bombs'] += 3
    elif reward == 'super': s['supers'] += 1
    else: s['active']['shield'] = now + 12000
    s['boxes_opened'] += 1
    notice(s, 'MYSTERY BOX: ' + reward.upper() + '!', now, 1800)
    check_achievements(s, now)

state = reset()
running = True
while running:
    dt = min(clock.tick(60) / 1000, 0.05)
    now = pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_p and not state['shop'] and not state['game_over']:
                state['paused'] = not state['paused']
                if not state['paused']:
                    state['invulnerable_until'] = now + 1500
                    state['last_enemy_shot'] = now
            elif state['paused']:
                pass
            elif state['game_over'] and event.key == pygame.K_r:
                state = reset()
            elif not state['shop'] and not state['game_over'] and event.key == pygame.K_g:
                if state['energy'] >= 100:
                    state['energy'] = 0
                    state['active']['overdrive'] = now + 9000
                    state['hp'] = min(state['max_hp'], state['hp'] + 20)
                    make_particles(state, *state['player'].center, ORANGE, 35)
                    notice(state, 'OVERDRIVE! FAST FIRE + HEAL!', now, 2200)
                else:
                    notice(state, 'ENERGY NOT FULL YET!', now, 900)
            elif not state['shop'] and not state['game_over'] and event.key in (pygame.K_q,pygame.K_e,pygame.K_f):
                if now - state['last_special'] > 400:
                    if event.key == pygame.K_q and state['rockets']:
                        state['rockets'] -= 1
                        target = state['boss']['rect'].center if state['boss'] else (random.choice(state['aliens'])['rect'].center if state['aliens'] else (400,160))
                        blast(state, *target, 105, 6, now)
                        notice(state, 'ROCKET EXPLOSION!', now)
                    elif event.key == pygame.K_e and state['bombs']:
                        state['bombs'] -= 1
                        blast(state, 400, 270, 650, 3, now)
                        notice(state, 'MEGA BOMB!', now)
                    elif event.key == pygame.K_f and state['supers']:
                        state['supers'] -= 1
                        blast(state, 400, 270, 900, 18, now)
                        notice(state, 'SUPER NOVA!', now)
                    state['last_special'] = now
            elif state['shop']:
                if event.key == pygame.K_h:
                    buy(state, 10, now)
                elif event.key == pygame.K_j:
                    buy(state, 11, now)
                elif event.key == pygame.K_k:
                    buy(state, 12, now)
                elif event.key == pygame.K_l:
                    buy(state, 13, now)
                if pygame.K_1 <= event.key <= pygame.K_9:
                    buy(state, event.key - pygame.K_1, now)
                elif event.key == pygame.K_0:
                    buy(state, 9, now)
                elif event.key == pygame.K_c:
                    state['skin'] = (state['skin'] + 1) % 5
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    next_wave(state, now)

    keys = pygame.key.get_pressed()
    s = state
    if not s['game_over'] and not s['shop'] and not s['paused']:
        p = s['player']
        for kind in list(s['active']):
            if now >= s['active'][kind]:
                del s['active'][kind]
        movement = round((340 + 55 * s['upgrades'].get('speed', 0)) * dt)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            p.x -= movement
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            p.x += movement
        if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and now >= s['dash_ready']:
            direction = (-1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else
                          1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0)
            if direction:
                make_particles(s, *p.center, CYAN, 18)
                p.x += direction * 125
                s['dash_ready'] = now + 3500
                s['invulnerable_until'] = max(s['invulnerable_until'], now + 300)
        p.clamp_ip(screen.get_rect())
        cooldown = 85 if 'rapid' in s['active'] else (145 if 'bigship' in s['active'] else 220)
        cooldown = max(55, cooldown - 25 * s['upgrades'].get('fire', 0))
        if 'overdrive' in s['active']:
            cooldown = max(40, cooldown // 2)
        if s['upgrades'].get('regen', 0) and now - s['regen_clock'] >= 2500:
            s['hp'] = min(s['max_hp'], s['hp'] + s['upgrades']['regen'] * 2)
            s['regen_clock'] = now
        # Falling asteroids become more frequent at higher levels.
        if s['level'] >= 2 and now - s['last_asteroid'] >= max(650, 2500 - s['level'] * 120):
            size = random.randint(20, 39)
            s['asteroids'].append({'rect': pygame.Rect(random.randint(20, WIDTH - size - 20), -size, size, size),
                                   'speed': random.randint(130, 190) + s['level'] * 12, 'hp': 2})
            s['last_asteroid'] = now
        for rock in s['asteroids'][:]:
            rock['rect'].y += max(1, round(rock['speed'] * dt))
            if rock['rect'].top > HEIGHT:
                s['asteroids'].remove(rock)
            elif rock['rect'].colliderect(p):
                s['asteroids'].remove(rock)
                hurt_player(s, now, 25)
                make_particles(s, *rock['rect'].center, ORANGE, 14)
        if keys[pygame.K_SPACE] and now - s['last_shot'] >= cooldown:
            spawn_shot(s)
            s['last_shot'] = now

        if s['pets'] and now - s['last_pet'] > max(200, 900 - s['pets']*160):
            for i in range(s['pets']):
                px = p.centerx + (i - (s['pets']-1)/2)*62
                s['bullets'].append({'rect':pygame.Rect(int(px),p.top-34,5,14),'vx':0,'piercing':False,'damage':1+s['upgrades'].get('damage',0),'hit':set()})
            s['last_pet'] = now
        for box in s['boxes'][:]:
            box.y += max(1,round(90*dt))
            if box.top > HEIGHT: s['boxes'].remove(box)
            elif box.colliderect(p):
                s['boxes'].remove(box)
                open_box(s,now)
        for bullet in s['bullets'][:]:
            r = bullet['rect']
            r.y -= max(1, round((680 if bullet['piercing'] else 550) * dt))
            r.x += round(bullet['vx'] * dt)
            if r.bottom < 0 or r.right < 0 or r.left > WIDTH:
                s['bullets'].remove(bullet)
                continue
            for rock in s['asteroids'][:]:
                if r.colliderect(rock['rect']):
                    rock['hp'] -= bullet['damage']
                    if rock['hp'] <= 0:
                        s['asteroids'].remove(rock)
                        s['coins'] += 3
                        s['energy'] = min(100, s['energy'] + 2)
                        make_particles(s, *rock['rect'].center, ORANGE, 12)
                    if not bullet['piercing'] and bullet in s['bullets']:
                        s['bullets'].remove(bullet)
                    break
            if bullet not in s['bullets']:
                continue
            for a in s['aliens'][:]:
                if r.colliderect(a['rect']) and id(a) not in bullet['hit']:
                    bullet['hit'].add(id(a))
                    a['hp'] -= bullet['damage']
                    if a['hp'] <= 0:
                        s['aliens'].remove(a)
                        award_kill(s, a, now)
                    if not bullet['piercing']:
                        s['bullets'].remove(bullet)
                        break

        boss = s['boss']
        if boss:
            br = boss['rect']
            br.x += round(boss['direction'] * (110 + s['level'] * 8) * dt)
            if br.left <= 20:
                br.left, boss['direction'] = 20, 1
            elif br.right >= WIDTH - 20:
                br.right, boss['direction'] = WIDTH - 20, -1
            boss['phase'] = 1 if boss['hp'] <= boss['max_hp'] // 2 else 0
            attack_delay = max(260, 1050 - s['level'] * 40 - boss['phase'] * 200 - boss['type'] * 90)
            if now - boss['last_attack'] >= attack_delay:
                offsets = ((-90,-60,-30,0,30,60,90) if boss['type']==2 else (-60,-30,0,30,60)) if boss['phase'] else ((-75,-25,25,75) if boss['type']==1 else (-45,0,45))
                for offset in offsets:
                    s['enemy_bullets'].append(pygame.Rect(br.centerx + offset - 5, br.bottom, 10, 19))
                boss['last_attack'] = now
            # Extra aliens spawn throughout the boss battle, with a population cap.
            if now - boss['last_spawn'] >= max(1700, 4200 - s['level'] * 120):
                free_slots = max(0, 12 - len(s['aliens']))
                for i in range(min(free_slots, 3 + boss['phase'] * 2)):
                    x = max(30, min(WIDTH - 68, br.centerx - 100 + i * 52))
                    s['aliens'].append(alien(x, 185 + (i % 2) * 43, i, True))
                boss['last_spawn'] = now
            for bullet in s['bullets'][:]:
                if bullet['rect'].colliderect(br) and 'boss' not in bullet['hit']:
                    bullet['hit'].add('boss')
                    boss['hp'] -= bullet['damage']
                    if not bullet['piercing']:
                        s['bullets'].remove(bullet)
                    if boss['hp'] <= 0:
                        defeat_boss(s, now)
                    break

        if not s['shop']:
            for drop in s['drops'][:]:
                drop['rect'].y += max(1, round(125 * dt))
                if drop['rect'].top > HEIGHT:
                    s['drops'].remove(drop)
                elif drop['rect'].colliderect(p):
                    kind = drop['kind']
                    if kind == 'repair':
                        s['hp'] = min(s['max_hp'], s['hp'] + 25)
                    else:
                        s['active'][kind] = now + POWERUPS[kind][3]
                    notice(s, POWERUPS[kind][2] + '!', now)
                    s['coins'] += 5
                    s['drops'].remove(drop)

            speed = 30 + s['level'] * 12 + max(0, 36 - len(s['aliens'])) * 1.5
            move = round(s['direction'] * speed * dt)
            if any(a['rect'].right + move >= WIDTH - 22 or a['rect'].left + move <= 22 for a in s['aliens']):
                s['direction'] *= -1
                for a in s['aliens']:
                    a['rect'].y += 19
            else:
                for a in s['aliens']:
                    a['rect'].x += move
            if s['aliens'] and now - s['last_enemy_shot'] > max(320, 1150 - s['level'] * 75):
                shooter = random.choice(s['aliens'])['rect']
                s['enemy_bullets'].append(pygame.Rect(shooter.centerx - 3, shooter.bottom, 6, 15))
                s['last_enemy_shot'] = now
            for enemy_bullet in s['enemy_bullets'][:]:
                enemy_bullet.y += max(1, round((240 + s['level'] * 30) * dt))
                if enemy_bullet.top > HEIGHT:
                    s['enemy_bullets'].remove(enemy_bullet)
                elif enemy_bullet.colliderect(p):
                    s['enemy_bullets'].remove(enemy_bullet)
                    hurt_player(s, now, 20 + min(20, s['level'] * 2))
            if any(a['rect'].bottom >= p.top for a in s['aliens']):
                s['game_over'] = True
            if not s['aliens'] and s['boss'] is None:
                finish_wave(s, now)

    for particle in s['particles'][:]:
        particle['x'] += particle['vx'] * dt
        particle['y'] += particle['vy'] * dt
        particle['life'] -= dt
        if particle['life'] <= 0:
            s['particles'].remove(particle)
    if now - s['last_kill'] > 2200:
        s['combo'] = 0
    screen.fill((8, 10, 27))
    for x, y, size in stars:
        pygame.draw.circle(screen, (65, 73, 115), (x, y), size)
    pygame.draw.line(screen, (50, 120, 110), (0, HEIGHT - 35), (WIDTH, HEIGHT - 35), 2)
    text(f'SCORE {s["score"]}', FONT, WHITE, 15, 12)
    text(f'LVL {s["level"]}', FONT, YELLOW, 230, 12)
    draw_coin(370, 25, 11)
    text(f'{s["coins"]}', FONT, ORANGE, 390, 12)
    text(f'LIVES {s["lives"]}', FONT, GREEN, 600, 12)
    pygame.draw.rect(screen, (65, 30, 45), (565, 45, 220, 17), border_radius=5)
    pygame.draw.rect(screen, GREEN if s['hp'] > s['max_hp'] * .3 else RED,
                     (565, 45, int(220 * max(0, s['hp']) / s['max_hp']), 17), border_radius=5)
    text(f'SHIP HP {s["hp"]}/{s["max_hp"]}', SMALL, WHITE, 580, 65)
    pygame.draw.rect(screen, (40, 42, 80), (15, 77, 185, 12), border_radius=4)
    pygame.draw.rect(screen, ORANGE, (15, 77, int(185 * s['energy'] / 100), 12), border_radius=4)
    text(f'ENERGY {s["energy"]}%  [G]', SMALL, WHITE, 15, 94)
    if s['combo'] >= 5 and not s['shop']:
        text(f'COMBO x{min(5, 1 + s["combo"] // 5)}  ({s["combo"]} KOs)', SMALL, YELLOW, 18, 46)
    for particle in s['particles']:
        pygame.draw.circle(screen, particle['color'], (int(particle['x']), int(particle['y'])),
                           max(1, int(4 * min(1, particle['life'] * 2))))
    for a in s['aliens']:
        draw_alien(a)
    if s['boss']:
        boss = s['boss']
        r = boss['rect']
        pygame.draw.ellipse(screen, (RED, ORANGE, PURPLE)[boss['type']] if boss['phase'] else (PURPLE,CYAN,GREEN)[boss['type']], r)
        pygame.draw.ellipse(screen, CYAN, r.inflate(-28, -22), 4)
        pygame.draw.rect(screen, RED, (r.centerx - 18, r.centery - 9, 36, 18), border_radius=8)
        pygame.draw.circle(screen, YELLOW, r.center, 7)
        pygame.draw.rect(screen, (80, 35, 65), (220, 49, 360, 15), border_radius=5)
        pygame.draw.rect(screen, RED, (220, 49, int(360 * max(0, boss['hp']) / boss['max_hp']), 15), border_radius=5)
        text(('TITAN','PHANTOM','OVERLORD')[boss['type']] + (' - RAGE' if boss['phase'] else ''), SMALL, WHITE, 330, 28)
    for rock in s['asteroids']:
        r = rock['rect']
        pygame.draw.circle(screen, (135, 113, 105), r.center, r.width // 2)
        pygame.draw.circle(screen, (88, 73, 80), (r.centerx - 5, r.centery - 4), max(3, r.width // 6))
    for bullet in s['bullets']:
        pygame.draw.rect(screen, ORANGE if bullet['piercing'] else GREEN, bullet['rect'], border_radius=3)
    for bullet in s['enemy_bullets']:
        pygame.draw.rect(screen, RED, bullet, border_radius=2)
    for box in s['boxes']:
        pygame.draw.rect(screen, PURPLE, box, border_radius=5)
        pygame.draw.rect(screen, YELLOW, box, 3, border_radius=5)
        text('?', FONT, WHITE, box.centerx, box.centery, center=True)
    for drop in s['drops']:
        color, label, _, _ = POWERUPS[drop['kind']]
        pygame.draw.circle(screen, color, drop['rect'].center, 15)
        pygame.draw.circle(screen, WHITE, drop['rect'].center, 15, 2)
        text(label, SMALL, (10, 10, 30), *drop['rect'].center, center=True)
    if not s['game_over'] and (now >= s['invulnerable_until'] or (now // 120) % 2 == 0):
        draw_player(s['player'], 'bigship' in s['active'], s['skin'])
        for i in range(s['pets']):
            px = int(s['player'].centerx + (i-(s['pets']-1)/2)*62)
            py = s['player'].top-35
            pygame.draw.circle(screen, PURPLE, (px,py), 13)
            pygame.draw.circle(screen, CYAN, (px-5,py-3), 3)
            pygame.draw.circle(screen, CYAN, (px+5,py-3), 3)
    if 'shield' in s['active'] and not s['game_over']:
        pygame.draw.circle(screen, CYAN, s['player'].center, 37, 3)
    text(f'Armor {s["armor_hits"]}  |  Q Rockets {s["rockets"]}  E Bombs {s["bombs"]}  F Super {s["supers"]}  |  P Pause', SMALL, WHITE, 16, HEIGHT - 29)
    text('SHIFT Dash: ' + ('READY' if now >= s['dash_ready'] else f'{(s["dash_ready"]-now)/1000:.1f}s'),
         SMALL, CYAN, 15, HEIGHT - 57)
    if now < s['notice_until'] and not s['game_over'] and not s['shop']:
        text(s['notice'], FONT, YELLOW, WIDTH // 2, 315, center=True)

    if s['shop']:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230))
        screen.blit(overlay, (0, 0))
        draw_shopfront(WIDTH // 2, 1)
        text('UPGRADE SHOP', FONT, CYAN, WIDTH // 2, 111, center=True)
        draw_coin(252, 145, 11)
        text(f'{s["coins"]} coins  |  Next: Level {s["level"] + 1}', SMALL, YELLOW, 272, 136)
        for i, (key, name, base, cap) in enumerate(SHOP):
            count = s['upgrades'].get(key, 0)
            cost = base + 10 * (s['level'] - 1)
            y = 174 + i * 38
            pygame.draw.rect(screen, (23, 34, 65), (68, y - 17, 664, 36), border_radius=10)
            draw_upgrade_icon(key, 100, y + 1)
            color = (115, 130, 155) if count >= cap else (GREEN if s['coins'] >= cost else RED)
            text(f'{i + 1}. {name}', SMALL, WHITE, 137, y - 6)
            text(f'Lv {count}', SMALL, CYAN, 468, y - 6)
            if count >= cap:
                text('MAX', SMALL, color, 630, y - 6)
            else:
                draw_coin(625, y + 2, 10)
                text(str(cost), SMALL, color, 646, y - 6)
        text('H: Max HP  J: Repair  K: Auto-repair  L: Energy boost', SMALL, GREEN, WIDTH // 2, 564, center=True)
        text('1-9, 0 buy | C skin | ENTER continue', SMALL, GREEN, WIDTH // 2, 584, center=True)
        text(f'HP {s["hp"]}/{s["max_hp"]} | G: Overdrive at 100% energy | SHIFT: Dash', SMALL, YELLOW, WIDTH // 2, 605, center=True)
        if now < s['notice_until']:
            text(s['notice'], SMALL, ORANGE, WIDTH // 2, 628, center=True)
    if s['paused']:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        text('PAUSED', BIG, CYAN, WIDTH // 2, 265, center=True)
        text('Press P to resume', FONT, WHITE, WIDTH // 2, 335, center=True)
    if s['game_over']:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        text('GAME OVER', BIG, RED, WIDTH // 2, 260, center=True)
        text(f'Score: {s["score"]}   Level: {s["level"]}', FONT, WHITE, WIDTH // 2, 335, center=True)
        text(f'Enemies: {s["total_kills"]}  Bosses: {s["boss_kills"]}  Best combo: {s["best_combo"]}', SMALL, YELLOW, WIDTH // 2, 370, center=True)
        text(f'Achievements: {len(s["achievements"])}/{len(ACHIEVEMENTS)}  |  Missions: {len(s["mission_claimed"])}/3  |  Boxes: {s["boxes_opened"]}', SMALL, CYAN, WIDTH // 2, 395, center=True)
        text('Press R to restart', FONT, GREEN, WIDTH // 2, 430, center=True)
    pygame.display.flip()

pygame.quit()
sys.exit()