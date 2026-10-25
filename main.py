import os, math, random
import pygame

# WRAITH RUNNER V2 — Pydroid 3 / touch platformer
# Install in Pydroid Pip: pygame
pygame.init()
pygame.display.set_caption("Wraith Runner V2")
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SW, SH = screen.get_size()
clock = pygame.time.Clock()
ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(ROOT, "assets")

# Palette
INK=(10,15,29); SKY1=(15,22,43); SKY2=(45,60,86)
WHITE=(238,245,255); MUTED=(151,170,202); GOLD=(255,202,94)
CYAN=(91,224,236); BLUE=(65,143,255); PLATFORM=(42,53,76)
TOP=(106,126,158); GREEN=(113,223,174); RED=(255,106,119)

def load_seq(path):
    result=[]
    if os.path.isdir(path):
        for fn in sorted(os.listdir(path)):
            if fn.lower().endswith(".png"):
                try:
                    result.append(pygame.image.load(os.path.join(path,fn)).convert_alpha())
                except pygame.error:
                    pass
    return result

def load_water():
    p=os.path.join(ASSET,"water")
    frames=[]
    for fn in sorted(os.listdir(p)):
        if fn.endswith(".png"):
            try: frames.append(pygame.image.load(os.path.join(p,fn)).convert_alpha())
            except pygame.error: pass
    return frames
water_frames=load_water()

FONT=pygame.font.Font(None, max(24,int(SH*.042)))
SMALL=pygame.font.Font(None, max(18,int(SH*.027)))
TINY=pygame.font.Font(None, max(16,int(SH*.023)))

def text(s,x,y,font=SMALL,color=WHITE,center=False):
    surf=font.render(s,True,color)
    r=surf.get_rect()
    if center: r.center=(int(x),int(y))
    else: r.topleft=(int(x),int(y))
    screen.blit(surf,r)

def panel(rect, fill=(12,18,35,220), border=(75,97,135), radius=14, width=2):
    surf=pygame.Surface((rect[2],rect[3]),pygame.SRCALPHA)
    pygame.draw.rect(surf,fill,(0,0,rect[2],rect[3]),border_radius=radius)
    screen.blit(surf,(rect[0],rect[1]))
    pygame.draw.rect(screen,border,rect,width,border_radius=radius)

def background(cam=0):
    for y in range(0,SH,4):
        t=y/SH
        col=tuple(int(SKY1[i]*(1-t)+SKY2[i]*t) for i in range(3))
        pygame.draw.rect(screen,col,(0,y,SW,4))
    moon=(int(SW*.78),int(SH*.17))
    pygame.draw.circle(screen,(189,208,237),moon,max(16,int(SH*.035)))
    pygame.draw.circle(screen,(130,151,191),(moon[0]+7,moon[1]-4),max(13,int(SH*.031)))
    for i in range(12):
        x=int((i*190-cam*.17)%(SW+220)-110)
        peak=int(SH*(.46+(i%3)*.035))
        pygame.draw.polygon(screen,(31,42,66),[(x-120,SH),(x,peak),(x+150,SH)])
    for i in range(35):
        x=int((i*127-cam*.06)%SW); y=(i*59)%max(1,int(SH*.43))
        pygame.draw.circle(screen,(166,189,222),(x,y),1 if i%3 else 2)

# Full-screen coordinates; platform levels are generated for the current landscape dimensions.
ground_y=int(SH*.79)
level_end=6200
platforms=[
 (0,ground_y,900),(1030,ground_y-62,280),(1410,ground_y-132,260),
 (1770,ground_y-58,420),(2290,ground_y-112,300),(2700,ground_y-28,520),
 (3320,ground_y-92,320),(3750,ground_y-4,700),(4550,ground_y-95,380),
 (5050,ground_y-25,850),(5950,ground_y-70,300)
]
def draw_platforms(cam):
    for x,y,w in platforms:
        sx=int(x-cam)
        if sx>SW or sx+w<0: continue
        h=SH-y
        pygame.draw.rect(screen,PLATFORM,(sx,y,w,h))
        pygame.draw.rect(screen,TOP,(sx,y,w,max(8,int(SH*.018))))
        pygame.draw.rect(screen,GREEN,(sx,y,w,max(3,int(SH*.006))))
        step=max(28,int(SH*.055))
        for bx in range(sx+step,min(sx+w,SW),step):
            pygame.draw.line(screen,(57,70,97),(bx,y+10),(bx,SH),2)

# Load character packs, with stable foot anchoring from original 520x420 canvas.
characters=[]
for i in range(1,4):
    folder=os.path.join(ASSET,"characters",f"Wraith_{i:02d}")
    seqs={k:load_seq(os.path.join(folder,v)) for k,v in
          [("idle","idle"),("walk","walk"),("attack","attack"),("cast","cast"),("hurt","hurt")]}
    if not seqs["idle"]: continue
    # Use idle frame's alpha bbox to determine stable ground anchor and visible width.
    bbox=seqs["idle"][0].get_bounding_rect()
    characters.append({"name":f"Wraith {i}","seq":seqs,"bbox":bbox})
if not characters:
    raise SystemExit("Sprite tidak ditemukan. Ekstrak ulang ZIP project.")
char_index=0
selected=None

# Scale full frame so all animations share the same canvas/anchor.
# Source sprites are 520x420; visible bounds are roughly 200x285.
scale=max(.2,min(.85,(SH*.34)/300))
def scaled_frames(seq):
    return [pygame.transform.scale(im,(int(im.get_width()*scale),int(im.get_height()*scale))) for im in seq]

def prepare_character(ch):
    ch["scaled"]={k:scaled_frames(v) for k,v in ch["seq"].items()}
    # stable anchor based on first idle frame's alpha bbox
    b=ch["bbox"]
    ch["anchor_x"]=int((b.left+b.right)/2*scale)
    ch["anchor_y"]=int(b.bottom*scale)
    ch["visible_w"]=max(1,int(b.width*scale))
    ch["visible_h"]=max(1,int(b.height*scale))
for ch in characters: prepare_character(ch)

# UI layout scales to landscape devices.
joy_center=(int(SW*.13),int(SH*.80)); joy_r=max(45,int(SH*.105))
jump_center=(int(SW*.88),int(SH*.80)); action_center=(int(SW*.75),int(SH*.80))
jump_r=max(40,int(SH*.085)); action_r=max(38,int(SH*.078))
joy_dx=0.0; joy_finger=None; touch_map={}; mouse_joy=False
jump_down=False; attack_down=False; water_down=False
prev_jump=False; prev_attack=False; prev_water=False

def draw_button(center,r,label,color,pressed=False):
    x,y=center
    pygame.draw.circle(screen,(8,13,27),(x,y),r+5)
    pygame.draw.circle(screen,(41,55,83),(x,y),r)
    pygame.draw.circle(screen,color if pressed else (166,190,222),(x,y),r,3)
    text(label,x,y,SMALL,WHITE,True)

def draw_joystick():
    x,y=joy_center
    pygame.draw.circle(screen,(9,14,28),(x,y),joy_r+6)
    pygame.draw.circle(screen,(158,179,215),(x,y),joy_r,3)
    kx=x+int(joy_dx*joy_r*.62)
    pygame.draw.circle(screen,(50,70,108),(kx,y),int(joy_r*.46))
    pygame.draw.circle(screen,(121,153,211),(kx,y),int(joy_r*.46),3)

def button_hit(pos,center,r,ratio=1.35):
    return math.hypot(pos[0]-center[0],pos[1]-center[1])<r*ratio

retry_tap=False

def current_input_events():
    global joy_dx,joy_finger,jump_down,attack_down,water_down,mouse_joy,retry_tap
    global prev_jump,prev_attack,prev_water
    jump_down=attack_down=water_down=False
    retry_tap=False
    events=pygame.event.get()
    for e in events:
        if e.type==pygame.QUIT: return False
        if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return False
        if e.type==pygame.KEYDOWN:
            if e.key in (pygame.K_SPACE,pygame.K_UP): jump_down=True
            if e.key in (pygame.K_j,): attack_down=True
            if e.key in (pygame.K_k,): water_down=True
        if e.type==pygame.FINGERDOWN:
            p=(int(e.x*SW),int(e.y*SH))
            if ("game_over" in globals() and (game_over or won)
                and SW*.40 <= p[0] <= SW*.60 and SH*.55 <= p[1] <= SH*.67):
                retry_tap=True
            elif button_hit(p,jump_center,jump_r): touch_map[e.finger_id]="jump"; jump_down=True
            elif button_hit(p,action_center,action_r):
                # Left half of action button is melee; upper/right region water is handled below via split.
                if p[0] < action_center[0]:
                    touch_map[e.finger_id]="attack"; attack_down=True
                else:
                    touch_map[e.finger_id]="water"; water_down=True
            elif p[0]<SW*.38:
                touch_map[e.finger_id]="joy"; joy_finger=e.finger_id
                joy_dx=max(-1,min(1,(p[0]-joy_center[0])/joy_r))
            else: touch_map[e.finger_id]="other"
        elif e.type==pygame.FINGERMOTION:
            if touch_map.get(e.finger_id)=="joy":
                p=(int(e.x*SW),int(e.y*SH))
                joy_dx=max(-1,min(1,(p[0]-joy_center[0])/joy_r))
        elif e.type==pygame.FINGERUP:
            kind=touch_map.pop(e.finger_id,None)
            if kind=="joy": joy_dx=0; joy_finger=None
        if e.type==pygame.MOUSEBUTTONDOWN:
            p=e.pos
            if ("game_over" in globals() and (game_over or won)
                and SW*.40 <= p[0] <= SW*.60 and SH*.55 <= p[1] <= SH*.67):
                retry_tap=True
            elif button_hit(p,jump_center,jump_r): touch_map["mjump"]="jump"; jump_down=True
            elif button_hit(p,action_center,action_r):
                if p[0] < action_center[0]: touch_map["mattack"]="attack"; attack_down=True
                else: touch_map["mwater"]="water"; water_down=True
            elif p[0]<SW*.38:
                mouse_joy=True; joy_dx=max(-1,min(1,(p[0]-joy_center[0])/joy_r))
        elif e.type==pygame.MOUSEMOTION and mouse_joy:
            joy_dx=max(-1,min(1,(e.pos[0]-joy_center[0])/joy_r))
        elif e.type==pygame.MOUSEBUTTONUP:
            mouse_joy=False; joy_dx=0
            touch_map.pop("mjump",None); touch_map.pop("mattack",None); touch_map.pop("mwater",None)
    return True

# Character selection screen.
def selection_screen():
    global char_index
    while True:
        # Separate event handling so selection taps are not consumed by gameplay controls.
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: return None
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: return None
                if ev.key in (pygame.K_LEFT,pygame.K_a): char_index=(char_index-1)%len(characters)
                if ev.key in (pygame.K_RIGHT,pygame.K_d): char_index=(char_index+1)%len(characters)
                if ev.key in (pygame.K_RETURN,pygame.K_SPACE): return characters[char_index]
            if ev.type in (pygame.MOUSEBUTTONDOWN,pygame.FINGERDOWN):
                p=ev.pos if ev.type==pygame.MOUSEBUTTONDOWN else (int(ev.x*SW),int(ev.y*SH))
                card_w=min(210,int(SW*.23)); card_h=int(SH*.49)
                gap=int(SW*.025); total=card_w*3+gap*2; start=(SW-total)//2
                card_y=int(SH*.29)
                start_btn=pygame.Rect(int(SW*.39),int(SH*.88),int(SW*.22),int(SH*.095))
                if start_btn.collidepoint(p): return characters[char_index]
                for i in range(len(characters)):
                    cx=start+i*(card_w+gap)
                    if cx<=p[0]<=cx+card_w and card_y<=p[1]<=card_y+card_h:
                        char_index=i
        background()
        panel((int(SW*.20),int(SH*.07),int(SW*.60),int(SH*.18)),(9,14,29,230),(79,106,151),18,2)
        text("WRAITH RUNNER",SW*.5,SH*.12,FONT,GOLD,True)
        text("PILIH KARAKTER",SW*.5,SH*.20,SMALL,MUTED,True)
        card_w=min(210,int(SW*.23)); card_h=int(SH*.49)
        gap=int(SW*.025)
        total=card_w*3+gap*2; start=(SW-total)//2
        for i,ch in enumerate(characters):
            x=start+i*(card_w+gap); y=int(SH*.29)
            active=i==char_index
            panel((x,y,card_w,card_h),(19,29,50,235),GOLD if active else (65,83,117),16,4 if active else 2)
            # Display character, anchored and scaled to card.
            img=ch["scaled"]["idle"][0]
            b=ch["bbox"]
            ax=ch["anchor_x"]; ay=ch["anchor_y"]
            draw_x=x+card_w//2-ax
            draw_y=y+int(card_h*.66)-ay
            screen.blit(img,(draw_x,draw_y))
            text(ch["name"],x+card_w//2,y+card_h-48,SMALL,GOLD if active else WHITE,True)
            text(["BALANCED","QUICK","POWER"][i],x+card_w//2,y+card_h-24,TINY,MUTED,True)
        text("TAP KARTU UNTUK MEMILIH",SW*.5,SH*.84,TINY,MUTED,True)
        start_btn=pygame.Rect(int(SW*.39),int(SH*.88),int(SW*.22),int(SH*.095))
        panel(start_btn,(29,75,91,245),CYAN,14,3)
        text("MULAI",SW*.5,start_btn.centery,SMALL,WHITE,True)
        pygame.display.flip()
        # Selection taps are processed in the event loop above on the next iteration.

selected=selection_screen()
if selected is None:
    pygame.quit(); raise SystemExit
ch=selected
anim="idle"; anim_i=0; anim_clock=0
# World player position uses the visible feet point, not the full transparent sprite canvas.
px=130.0; feet_y=float(ground_y); vx=0.0; vy=0.0; grounded=False; face=1
camera=0.0; game_over=False; won=False
projectiles=[]; particles=[]
enemies=[]
for ex,ey in [(780,ground_y),(1580,ground_y-132),(2110,ground_y-58),(2940,ground_y-28),(4010,ground_y-4),(5290,ground_y-25)]:
    enemies.append({"x":float(ex),"feet":float(ey),"alive":True,"phase":random.random()*6.28})
score=0; hp=3; invuln=0.0; cast_cool=0.0; attack_cool=0.0; status=""

def reset():
    global px,feet_y,vx,vy,grounded,camera,game_over,won,projectiles,particles,score,hp,invuln,anim,anim_i,anim_clock
    px=130.; feet_y=float(ground_y); vx=vy=0.; grounded=False; camera=0.; game_over=won=False
    projectiles=[]; particles=[]; score=0; hp=3; invuln=0.; anim="idle"; anim_i=anim_clock=0
    for e in enemies: e["alive"]=True

def begin_anim(name):
    global anim,anim_i,anim_clock
    anim=name; anim_i=0; anim_clock=0

def player_box():
    # Approximate collision box from visible alpha bounds.
    w=ch["visible_w"]*.62; h=ch["visible_h"]*.83
    return pygame.Rect(int(px-w/2),int(feet_y-h),int(w),int(h))

def spawn_water():
    global cast_cool
    cast_cool=.55
    projectiles.append({"x":px+face*ch["visible_w"]*.40,"y":feet_y-ch["visible_h"]*.54,
                        "vx":face*610,"life":2.2,"frame":0,"tick":0,"hit":set()})
    for _ in range(9):
        particles.append({"x":px+face*25,"y":feet_y-ch["visible_h"]*.55,
                          "vx":random.uniform(-65,65),"vy":random.uniform(-100,40),"life":.35,"color":CYAN})

def do_attack():
    global attack_cool,score
    attack_cool=.42
    # Melee hitbox extends forward from the visible character.
    reach=ch["visible_w"]*.95
    hit=pygame.Rect(int(px+face*(ch["visible_w"]*.25) - (0 if face>0 else reach)),
                    int(feet_y-ch["visible_h"]*.72),int(reach),int(ch["visible_h"]*.58))
    for e in enemies:
        if e["alive"]:
            er=pygame.Rect(int(e["x"]-24),int(e["feet"]-55),48,55)
            if hit.colliderect(er):
                e["alive"]=False; score+=100
                for _ in range(12):
                    particles.append({"x":e["x"],"y":e["feet"]-25,"vx":random.uniform(-120,120),"vy":random.uniform(-180,30),"life":.45,"color":GOLD})

def draw_effect(frames,idx,x,y,wanted_w=100):
    if not frames:return
    img=frames[idx%len(frames)]
    if img.get_width()>wanted_w:
        ratio=wanted_w/img.get_width()
        img=pygame.transform.scale(img,(wanted_w,max(1,int(img.get_height()*ratio))))
    screen.blit(img,(int(x-img.get_width()/2),int(y-img.get_height()/2)))

running=True
while running:
    dt=min(clock.tick(60)/1000,0.035)
    if not current_input_events(): break
    if retry_tap and (game_over or won):
        reset()
    keys=pygame.key.get_pressed()
    direction=(1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0)-(1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
    if not direction: direction=1 if joy_dx>.18 else -1 if joy_dx<-.18 else 0
    jump_now=jump_down and not prev_jump
    attack_now=attack_down and not prev_attack
    water_now=water_down and not prev_water
    prev_jump=jump_down; prev_attack=attack_down; prev_water=water_down

    if not game_over and not won:
        if direction:
            vx=direction*300; face=direction
        else:
            vx*=max(0,1-9*dt)
            if abs(vx)<10:vx=0
        if jump_now and grounded:
            vy=-650; grounded=False
        if attack_now and attack_cool<=0:
            do_attack(); begin_anim("attack")
        if water_now and cast_cool<=0:
            spawn_water(); begin_anim("cast")
        attack_cool=max(0,attack_cool-dt); cast_cool=max(0,cast_cool-dt); invuln=max(0,invuln-dt)

        old_feet=feet_y
        px=max(0,min(level_end-35,px+vx*dt))
        vy+=1650*dt
        feet_y+=vy*dt
        grounded=False
        if vy>=0:
            for x,y,w in platforms:
                if px+ch["visible_w"]*.28>x and px-ch["visible_w"]*.28<x+w:
                    if old_feet<=y+8 and feet_y>=y:
                        feet_y=float(y); vy=0; grounded=True; break
        if feet_y>SH+180:
            game_over=True
        if px>=level_end-100:
            won=True
        camera=max(0,min(level_end-SW+120,px-SW*.34))

        # Projectiles travel, animate, and damage enemies.
        for p in projectiles[:]:
            p["x"]+=p["vx"]*dt; p["life"]-=dt; p["tick"]+=dt
            if p["tick"]>.055:
                p["frame"]+=1; p["tick"]=0
            pr=pygame.Rect(int(p["x"]-22),int(p["y"]-18),44,36)
            for e in enemies:
                if e["alive"] and e["x"]-25 < p["x"] < e["x"]+25 and abs((e["feet"]-28)-p["y"])<50:
                    e["alive"]=False; score+=150
                    for _ in range(16):
                        particles.append({"x":p["x"],"y":p["y"],"vx":random.uniform(-150,150),"vy":random.uniform(-180,70),"life":.5,"color":CYAN})
                    p["life"]=0
            if p["life"]<=0 or p["x"]<0 or p["x"]>level_end: projectiles.remove(p)
        # Simple enemy contact damage
        pb=player_box()
        for e in enemies:
            if e["alive"]:
                er=pygame.Rect(int(e["x"]-23),int(e["feet"]-50),46,50)
                if pb.colliderect(er) and invuln<=0:
                    hp-=1; invuln=1.1; vx=-face*180; vy=-250
                    if hp<=0: game_over=True
                    break
        for p in particles[:]:
            p["x"]+=p["vx"]*dt; p["y"]+=p["vy"]*dt; p["vy"]+=300*dt; p["life"]-=dt
            if p["life"]<=0: particles.remove(p)

        # Animation state. Jump/fall is a single idle frame so body remains foot-anchored.
        if anim in ("attack","cast","hurt"):
            seq=ch["scaled"].get(anim,[])
            anim_clock+=dt
            frame_delay=.055 if anim=="cast" else .065
            if seq and anim_clock>=frame_delay:
                anim_clock=0; anim_i+=1
                if anim_i>=len(seq):
                    anim="walk" if abs(vx)>20 else "idle"; anim_i=0
        else:
            target="walk" if abs(vx)>30 and grounded else "idle"
            if target!=anim: begin_anim(target)
            anim_clock+=dt
            seq=ch["scaled"].get(anim,[])
            if seq and anim_clock>.085:
                anim_clock=0; anim_i=(anim_i+1)%len(seq)

    background(camera)
    draw_platforms(camera)

    # Goal portal
    gx=int(level_end-camera)
    if -60<gx<SW+60:
        pygame.draw.rect(screen,CYAN,(gx,ground_y-180,8,180))
        pygame.draw.circle(screen,GOLD,(gx+4,ground_y-188),14)

    # Enemies
    for e in enemies:
        if not e["alive"]: continue
        ex=int(e["x"]-camera); ey=int(e["feet"])
        if -60<ex<SW+60:
            bob=int(math.sin(pygame.time.get_ticks()*.006+e["phase"])*3)
            pygame.draw.ellipse(screen,(12,18,30),(ex-24,ey-6,48,12))
            pygame.draw.rect(screen,(115,89,153),(ex-19,ey-42+bob,38,36),border_radius=9)
            pygame.draw.rect(screen,(180,149,221),(ex-19,ey-42+bob,38,36),2,border_radius=9)
            pygame.draw.circle(screen,(255,111,137),(ex-7,ey-29+bob),3)
            pygame.draw.circle(screen,(255,111,137),(ex+7,ey-29+bob),3)

    # Water projectiles/effects
    for p in projectiles:
        x=int(p["x"]-camera); y=int(p["y"])
        if water_frames:
            fx=water_frames[p["frame"]%len(water_frames)]
            # compact crop already prepared; scale to visible projectile size
            fx=pygame.transform.scale(fx,(max(24,int(SH*.065)),max(16,int(SH*.04))))
            if p["vx"]<0: fx=pygame.transform.flip(fx,True,False)
            screen.blit(fx,(x-fx.get_width()//2,y-fx.get_height()//2))
        else:
            pygame.draw.circle(screen,CYAN,(x,y),12)
            pygame.draw.circle(screen,WHITE,(x,y),5)

    for p in particles:
        pygame.draw.circle(screen,p["color"],(int(p["x"]-camera),int(p["y"])),max(2,int(4*p["life"]/.5)))

    # Draw sprite aligned by visible feet anchor, so transparent padding never makes it float.
    seq=ch["scaled"].get(anim) or ch["scaled"]["idle"]
    img=seq[min(anim_i,len(seq)-1)]
    if face<0: img=pygame.transform.flip(img,True,False)
    draw_x=int(px-ch["anchor_x"]-camera)
    draw_y=int(feet_y-ch["anchor_y"])
    if invuln>0 and int(invuln*14)%2==0:
        tint=img.copy(); tint.fill((120,210,255,100),special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(tint,(draw_x,draw_y))
    else:
        screen.blit(img,(draw_x,draw_y))

    # HUD
    panel((14,12,min(390,SW-28),54),(8,13,27,220),(68,88,126),12,2)
    text("WRAITH RUNNER  V2",28,19,SMALL,GOLD)
    text(f"{ch['name']}   SCORE {score}",28,43,TINY,MUTED)
    for i in range(3):
        pygame.draw.circle(screen,RED if i<hp else (70,77,96),(SW-35-i*27,32),9)
    prog=max(0,min(1,px/level_end))
    barw=min(170,int(SW*.18))
    pygame.draw.rect(screen,(45,57,80),(SW//2-barw//2,20,barw,8),border_radius=4)
    pygame.draw.rect(screen,CYAN,(SW//2-barw//2,20,int(barw*prog),8),border_radius=4)
    text(f"{int(prog*100)}%",SW//2,43,TINY,WHITE,True)

    draw_joystick()
    # Separate skill buttons: attack at 70%, water at 79%, jump at 89%.
    attack_center=(int(SW*.69),int(SH*.80))
    water_center=(int(SW*.79),int(SH*.80))
    draw_button(attack_center,action_r,"ATK",GOLD,attack_down)
    draw_button(water_center,action_r,"WATER",CYAN,water_down)
    draw_button(jump_center,jump_r,"JUMP",WHITE,jump_down)

    if game_over or won:
        shade=pygame.Surface((SW,SH),pygame.SRCALPHA); shade.fill((4,7,16,205)); screen.blit(shade,(0,0))
        title="LEVEL COMPLETE!" if won else ("KAMU KALAH" if hp<=0 else "JATUH KE JURANG")
        text(title,SW/2,SH*.39,FONT,GOLD if won else WHITE,True)
        text("Sentuh RETRY untuk bermain lagi",SW/2,SH*.47,SMALL,MUTED,True)
        retry=pygame.Rect(int(SW*.40),int(SH*.55),int(SW*.20),int(SH*.12))
        panel(retry,(31,71,91,245),CYAN,14,3)
        text("RETRY",SW/2,retry.centery,SMALL,WHITE,True)
    pygame.display.flip()

pygame.quit()
