"""Original vector artwork for the algorithm overview; no external assets."""
from reportlab.lib import colors


def emblem(c, x, y, role, color, scale=1):
    """Five restrained line emblems, drawn at a common optical size."""
    c.saveState()
    c.translate(x, y)
    c.scale(scale, scale)
    c.setLineWidth(1.05)
    c.setStrokeColor(color)
    c.setFillColor(colors.white)
    p = c.beginPath()
    if role == 0:  # shield
        p.moveTo(-4, 5); p.lineTo(4, 5); p.lineTo(4, 0)
        p.curveTo(4, -3, 1, -5, 0, -6)
        p.curveTo(-1, -5, -4, -3, -4, 0); p.close()
        c.drawPath(p); c.line(0, 3, 0, -3)
    elif role == 1:  # leaf
        p.moveTo(-4, -4); p.curveTo(-7, 4, 1, 6, 5, 5)
        p.curveTo(6, -1, 2, -6, -4, -4)
        c.drawPath(p); c.line(-4, -5, 3, 3); c.line(-1, -1, -2, 2)
    elif role == 2:  # orb and orbit
        c.circle(0, 0, 3.3, stroke=1, fill=0)
        c.ellipse(-6, -1.7, 6, 1.7, stroke=1, fill=0)
        c.line(0, 5, 0, 6.5)
    elif role == 3:  # bow and arrow
        p.moveTo(-3, -5); p.curveTo(5, -4, 5, 4, -3, 5)
        c.drawPath(p); c.line(-3, -5, -3, 5); c.line(-5, 0, 6, 0)
        c.line(6, 0, 3.7, 2); c.line(6, 0, 3.7, -2)
    else:  # lantern
        c.rect(-3.5, -3.5, 7, 7, stroke=1, fill=0)
        c.line(-4.5, 4, 4.5, 4); c.line(-4.5, -4, 4.5, -4)
        c.line(-1.5, 4, -1.5, 6); c.line(1.5, 4, 1.5, 6)
        c.line(-1.5, 6, 1.5, 6); c.line(0, -2, 0, 2)
    c.restoreState()


def algorithm_overview(b, ctx):
    c = ctx['C']; black = ctx['BLACK']; gray = ctx['GRAY']; accent = ctx['BURGUNDY']
    light = colors.HexColor('#DCD6CE'); pale = colors.HexColor('#F3F0EB')
    ochre = ctx['OCHRE']
    x = b.x; top = b.y; gap = 13; pw = (b.w - 3 * gap) / 4
    px = [x + i * (pw + gap) for i in range(4)]
    roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']
    scores = [1500, 1510, 1490, 1520, 1480]
    ys = [top - 49 - 20 * i for i in range(5)]
    for i, label in enumerate(['Arrival queue', 'Widening band', 'Subset search', 'Complete team']):
        c.setFillColor(black); c.setFont('SansB', 9)
        c.drawString(px[i], top - 11, f'{i+1}  {label}')
        c.setStrokeColor(light); c.setLineWidth(.6)
        c.line(px[i], top - 21, px[i] + pw, top - 21)
    # Queue: the same five player identities are retained throughout the story.
    c.setFillColor(pale); c.roundRect(px[0], ys[0]-9, pw, 18, 3, stroke=0, fill=1)
    c.setStrokeColor(accent); c.setLineWidth(1.5); c.line(px[0], ys[0]-8, px[0], ys[0]+8)
    for role, yy in enumerate(ys):
        co = accent if role == 0 else gray
        emblem(c, px[0]+11, yy, role, co, .85)
        c.setFillColor(black); c.setFont('Sans', 8)
        c.drawString(px[0]+23, yy-2.7, roles[role])
        c.drawRightString(px[0]+87, yy-2.7, str(scores[role]))
        c.setFillColor(gray); c.drawRightString(px[0]+pw-3, yy-2.7, f'{4-role}s')
    c.setFillColor(gray); c.setFont('Sans', 7.5)
    c.drawString(px[0], top-148, '+ jungle 1650 (new)')
    c.setFillColor(accent); c.setFont('Sans', 7.8)
    c.drawString(px[0], top-165, 'Oldest feasible anchor')
    # A vertical eligibility lens leaves each candidate on a separate role row.
    lo, hi = px[1]+12, px[1]+pw-6
    def sx(s): return lo+(s-1410)/290*(hi-lo)
    c.setFillColor(pale); c.rect(sx(1410), ys[-1]-11, sx(1590)-sx(1410), ys[0]-ys[-1]+22, stroke=0, fill=1)
    for s in [1410,1590]:
        c.setStrokeColor(ochre); c.setLineWidth(.6)
        c.line(sx(s),ys[-1]-11,sx(s),ys[0]+11)
    for role, yy in enumerate(ys):
        c.setStrokeColor(light); c.line(lo, yy, hi, yy)
        c.setStrokeColor(accent if role == 0 else gray)
        c.setFillColor(accent if role == 0 else gray)
        c.circle(sx(scores[role]), yy, 2.7, stroke=0, fill=1)
    c.setStrokeColor(gray); c.setFillColor(colors.white)
    c.circle(sx(1650),ys[1],2.7,stroke=1,fill=1)
    c.setFont('Sans',7); c.setFillColor(gray)
    c.drawCentredString(sx(1650),ys[1]+7,'1650')
    c.drawCentredString(sx(1410),top-150,'1410')
    c.drawCentredString(sx(1590),top-150,'1590')
    c.setFont('Sans',7.8); c.setFillColor(accent)
    c.drawString(px[1],top-165,'50 + 10 × 4 = 90 points')
    # The display is one selected path through 32 states, not the full state DAG.
    c.setFont('Sans',7.7); c.setFillColor(gray)
    c.drawString(px[2],top-34,'32 states; selected path:')
    order = [4,2,0,1,3]; masks = ['10000','10100','10101','10111','11111']
    c.setFont('Sans',7.7); c.setFillColor(gray); c.drawString(px[2]+8,top-46,'00000')
    for i, (role, mask) in enumerate(zip(order,masks)):
        yy = top-63-18*i
        c.setStrokeColor(light); c.setLineWidth(.65)
        c.line(px[2]+25,yy+13,px[2]+25,yy+5)
        c.setFillColor(accent if role==0 else black); c.setFont('Sans',8)
        c.drawString(px[2]+8,yy-2,mask)
        emblem(c,px[2]+56,yy+1,role,accent if role==0 else gray,.67)
        c.setFont('Sans',7.7); c.drawRightString(px[2]+pw,yy-2,str(scores[role]))
    c.setFont('Sans',7.8); c.setFillColor(gray)
    c.drawString(px[2],top-165,'Process in score order')
    for role, yy in enumerate(ys):
        emblem(c,px[3]+12,yy,role,accent if role==0 else gray,.85)
        c.setFont('Sans',8); c.setFillColor(black)
        c.drawString(px[3]+26,yy-2.7,roles[role])
        c.drawRightString(px[3]+pw-2,yy-2.7,str(scores[role]))
    c.setFont('SansB',8); c.setFillColor(accent)
    c.drawString(px[3],top-156,'Gap 20 pts · wait 2 s')
    # Small directional arrows in gutters; all labels remain within panels.
    for i in range(3):
        ax=px[i]+pw+3; yy=top-89
        c.setStrokeColor(gray); c.setLineWidth(.7)
        c.line(ax,yy,ax+7,yy); c.line(ax+7,yy,ax+4,yy+2.5); c.line(ax+7,yy,ax+4,yy-2.5)
    b.y=top-179
    b.caption('Figure 1.', 'From queue to team at time 4 s. Role emblems identify the same players across stages; the top anchor is highlighted. '
              'The band also rejects a jungle candidate at 1650. The search considers all 32 role subsets; only its selected path is drawn. '
              'Bits, from right to left, represent top, jungle, mid, ADC, and support. Selected requests are removed together.')
