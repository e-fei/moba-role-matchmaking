"""Typeset the homework as a compact, conference-inspired research paper.

All figures are vector drawings generated from the saved experiments. The layout
borrows ICML conventions; it does not claim to be an ICML submission/template.
"""
import json
import math
import statistics as stats
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/MOBA_Matchmaking_Report.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
(ROOT/'tmp/pdfs').mkdir(parents=True, exist_ok=True)
DATA = json.loads((ROOT/'experiment_results.json').read_text())
BEFORE = json.loads((ROOT/'results/benchmark_before.json').read_text())
AFTER = json.loads((ROOT/'results/benchmark_after.json').read_text())
EXT = json.loads((ROOT/'results/waiting_extension.json').read_text())
REPOSITORY_PATH = ROOT/'repository.json'
REPOSITORY = json.loads(REPOSITORY_PATH.read_text()) if REPOSITORY_PATH.is_file() else None
from overview import algorithm_overview
from charts import result_figure as draw_results, queue_residence_figure
FONT = Path('/System/Library/Fonts/Supplemental')
for name, file in [('TimesR','Times New Roman.ttf'),('TimesB','Times New Roman Bold.ttf'),
                   ('TimesI','Times New Roman Italic.ttf'),('TimesBI','Times New Roman Bold Italic.ttf'),
                   ('Sans','Arial.ttf'),('SansB','Arial Bold.ttf'),('Mono','Courier New.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFont(TTFont('MathSymbols','/System/Library/Fonts/Symbol.ttf'))
pdfmetrics.registerFontFamily('TimesR',normal='TimesR',bold='TimesB',italic='TimesI',boldItalic='TimesBI')
pdfmetrics.registerFontFamily('Sans',normal='Sans',bold='SansB',italic='Sans',boldItalic='SansB')
W,H=612,792
L=54
FULL=504
GUTTER=18
COL=(FULL-GUTTER)/2
BOTTOM=55
BLACK=colors.HexColor('#24211F')
GRAY=colors.HexColor('#706B65')
LIGHT=colors.HexColor('#DCD6CE')
BURGUNDY=colors.HexColor('#7A263A')
OCHRE=colors.HexColor('#A8782A')
WARMGRAY=colors.HexColor('#89847D')
POLICIES=['role_fifo','fixed_50','adaptive_10','adaptive_30']
LABELS={'role_fifo':'FIFO','fixed_50':'Fixed 50','adaptive_10':'Adaptive 10','adaptive_30':'Adaptive 30'}
COLORS={'role_fifo':BLACK,'fixed_50':WARMGRAY,'adaptive_10':BURGUNDY,'adaptive_30':OCHRE}
MARKERS={'role_fifo':'circle','fixed_50':'square','adaptive_10':'triangle','adaptive_30':'diamond'}
STYLES={
 'body':ParagraphStyle('body',fontName='TimesR',fontSize=10,leading=11.7,alignment=TA_JUSTIFY,textColor=BLACK),
 'small':ParagraphStyle('small',fontName='TimesR',fontSize=9,leading=10.6,alignment=TA_LEFT,textColor=BLACK),
 'caption':ParagraphStyle('caption',fontName='TimesR',fontSize=9,leading=10.6,alignment=TA_JUSTIFY,textColor=BLACK),
 'h1':ParagraphStyle('h1',fontName='TimesB',fontSize=11.5,leading=13.4,textColor=BLACK),
 'h2':ParagraphStyle('h2',fontName='TimesB',fontSize=10,leading=12,textColor=BLACK),
 'table':ParagraphStyle('table',fontName='TimesR',fontSize=9,leading=10.5,textColor=BLACK),
 'th':ParagraphStyle('th',fontName='TimesB',fontSize=8.8,leading=10.2,textColor=BLACK),
 'math':ParagraphStyle('math',fontName='TimesR',fontSize=10.3,leading=14.5,alignment=TA_CENTER,textColor=BLACK),
 'mono':ParagraphStyle('mono',fontName='Mono',fontSize=8.1,leading=10.6,textColor=BLACK),
}
DOCLOG=[]
C=canvas.Canvas(str(OUT),pagesize=(W,H),pageCompression=1)
C.setTitle('Queueing and Team Formation with Role Constraints')
C.setSubject('Adaptive eligibility and exact within-team score balancing for a five-role MOBA queue')
C.setAuthor('')
C.setCreator('Homework report')
PAGE=0

def newpage(first=False):
    global PAGE
    if PAGE:C.showPage()
    PAGE+=1
    C.setFillColor(BLACK)
    if not first:
        C.setFont('TimesR',9)
        C.drawCentredString(W/2,751,'Queueing and Team Formation with Role Constraints')
        C.setLineWidth(.45);C.setStrokeColor(BLACK);C.line(L,744,L+FULL,744)
    C.setFont('TimesR',10)
    C.drawCentredString(W/2,34,str(PAGE))
    C.bookmarkPage(f'page{PAGE}')

class Block:
    def __init__(self,x=L,y=730,w=COL,bottom=BOTTOM,label=''):
        self.x,self.y,self.w,self.bottom=x,y,w,bottom
        self.label=label
    def space(self,n):self.y-=n
    def p(self,text,kind='body',after=5.5,style=None):
        p=Paragraph(text,style or STYLES[kind]);_,h=p.wrap(self.w,1000)
        if self.y-h<self.bottom:raise RuntimeError(f'Page {PAGE} {self.label}: overflow {self.y-h:.1f}: {text[:75]}')
        p.drawOn(C,self.x,self.y-h)
        DOCLOG.append((PAGE,self.label,self.y-h,text[:65]))
        self.y-=h+after
        return h
    def h(self,text,sub=False):
        self.space(6 if sub else 9)
        self.p(text,'h2' if sub else 'h1',after=6)
    def eq(self,text,number):
        self.space(3)
        rows = math_equations(number)
        h = sum(height for _,height in rows)
        if self.y-h<self.bottom:raise RuntimeError('equation overflow')
        yy = self.y
        for expression,height in rows:
            scale = min(1,(self.w-25)/expression.w)
            C.saveState()
            C.translate(self.x+(self.w-22-expression.w*scale)/2,yy-(18 if height>=30 else 12))
            C.scale(scale,scale)
            expression.draw(0,0)
            C.restoreState()
            yy -= height
        C.setFont('TimesR',9.5);C.setFillColor(BLACK)
        C.drawRightString(self.x+self.w,self.y-h/2-3,f'({number})')
        self.y-=h+9
    def caption(self,label,text):self.p(f'<b>{label}</b> {text}','caption',after=9)
    def table(self,rows,widths,caption=None,midrules=(),font=9,padding=5):
        if caption:self.caption(*caption)
        data=[]
        for i,row in enumerate(rows):
            data.append([Paragraph(str(v),STYLES['th' if i==0 else 'table']) for v in row])
        t=Table(data,colWidths=widths,hAlign='LEFT')
        cmd=[('LINEABOVE',(0,0),(-1,0),.8,BLACK),('LINEBELOW',(0,0),(-1,0),.45,BLACK),
             ('LINEBELOW',(0,-1),(-1,-1),.8,BLACK),('VALIGN',(0,0),(-1,-1),'TOP'),
             ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
             ('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding)]
        for i in midrules:cmd.append(('LINEABOVE',(0,i),(-1,i),.4,BLACK))
        t.setStyle(TableStyle(cmd));_,h=t.wrap(self.w,1000)
        if self.y-h<self.bottom:raise RuntimeError(f'table overflow p{PAGE}: y={self.y}, height={h}')
        t.drawOn(C,self.x,self.y-h);self.y-=h+10
    def code(self,lines):
        for line in lines.splitlines():
            self.p(escape(line).replace(' ','&nbsp;'),'mono',after=1)
        self.space(5)

# Small vector math compositor: scripts share a horizontal position, and sums
# place bounds above/below the operator instead of spacing them as ordinary text.
class Atom:
    def __init__(self,text,font='TimesR',size=10.3):
        self.text,self.font,self.size=text,font,size
        self.w=pdfmetrics.stringWidth(text,font,size)
    def draw(self,x,y):
        C.setFillColor(BLACK);C.setFont(self.font,self.size);C.drawString(x,y,self.text)

class MathBox:
    def __init__(self,*parts):
        self.parts=parts;self.w=sum(p.w for p in parts)
    def draw(self,x,y):
        for p in self.parts:p.draw(x,y);x+=p.w

class Script:
    def __init__(self,base,sub=None,sup=None):
        self.base,self.sub,self.sup=base,sub,sup
        self.w=base.w+max(sub.w if sub else 0,sup.w if sup else 0)+.4
    def draw(self,x,y):
        self.base.draw(x,y)
        if self.sub:self.sub.draw(x+self.base.w,y-2.8)
        if self.sup:self.sup.draw(x+self.base.w,y+5.1)

class Fraction:
    def __init__(self,den):
        self.num=Atom('1',size=8.5);self.den=Atom(str(den),size=8.5)
        self.w=max(self.num.w,self.den.w)+3
    def draw(self,x,y):
        self.num.draw(x+(self.w-self.num.w)/2,y+6.5)
        self.den.draw(x+(self.w-self.den.w)/2,y-5.8)
        C.setStrokeColor(BLACK);C.setLineWidth(.45);C.line(x,y+3.6,x+self.w,y+3.6)

class BigSum:
    def __init__(self,lower,upper=None):
        self.glyph=Atom('∑','MathSymbols',15)
        self.lower,self.upper=lower,upper
        self.w=max(self.glyph.w,lower.w,upper.w if upper else 0)+3
    def draw(self,x,y):
        self.glyph.draw(x+(self.w-self.glyph.w)/2,y-1.6)
        self.lower.draw(x+(self.w-self.lower.w)/2,y-10)
        if self.upper:self.upper.draw(x+(self.w-self.upper.w)/2,y+13)

def mi(text,size=10.3):return Atom(text,'TimesI',size)
def a(text,size=10.3):return Atom(text,'TimesR',size)
def v(letter,index):return Script(mi(letter),mi(str(index),7))
def math_equations(n):
    if n==1:
        low=MathBox(mi('i',7),Atom('∈','MathSymbols',7),mi('T',7))
        return [(MathBox(mi('W'),a('('),mi('T'),a(', '),mi('t'),a(') = '),Fraction(5),a(' '),BigSum(low),a(' ('),mi('t'),a(' - '),v('a','i'),a('),')),30)]
    if n==2:
        low=MathBox(mi('i',7),a(' < ',7),mi('j',7),a('; ',7),mi('i,j',7),Atom('∈','MathSymbols',7),mi('T',7))
        return [(MathBox(mi('G'),a('('),mi('T'),a(') = '),Fraction(10),a(' '),BigSum(low),a(' |'),v('s','i'),a(' - '),v('s','j'),a('|.')),30)]
    if n==3:
        return [(MathBox(v('b','q'),a('('),mi('t'),a(') = floor(min{'),mi('B'),a(', '),v('b','0'),a(' + '),mi('g'),a('('),mi('t'),a(' - '),v('a','q'),a(')}).')),20)]
    if n==4:
        one=MathBox(a('10'),mi('G'),a('('),mi('T'),a(') = '),BigSum(MathBox(mi('k',7),a('=0',7)),a('4',7)),a(' (2'),mi('k'),a(' - 4)'),v('x','k'))
        two=MathBox(a('= -4'),v('x','0'),a(' - 2'),v('x','1'),a(' + 2'),v('x','3'),a(' + 4'),v('x','4'),a('.'))
        return [(one,33),(two,19)]
    if n==8:
        return [(MathBox(v('W','H'),a(' = '),Fraction('N'),a(' '),BigSum(MathBox(mi('i',7),a('=1',7)),mi('N',7)),a(' [min('),v('d','i'),a(', '),mi('H'),a(') - '),v('a','i'),a('].')),33)]
    if n==5:
        low=MathBox(mi('i',7),Atom('∈','MathSymbols',7),mi('T',7))
        one=MathBox(v('J','λ'),a('('),mi('T'),a(') = '),mi('G'),a('('),mi('T'),a(') - '),mi('λ'),mi('R'),a('('),mi('T'),a('),'))
        two=MathBox(mi('R'),a('('),mi('T'),a(') = '),Fraction(5),a(' '),BigSum(low),a(' min('),mi('t'),a(' - '),v('a','i'),a(', '),mi('C'),a(').'))
        return [(one,22),(two,32)]
    if n==6:
        return [(MathBox(a('Δ = (2'),mi('k'),a(' - 4)'),v('s','i'),a(' - 2'),mi('λ'),a(' min('),mi('t'),a(' - '),v('a','i'),a(', '),mi('C'),a(').')),20)]
    if n==7:
        one=MathBox(a('0 ≤ '),mi('G'),a('('),v('T','λ'),a(') - '),mi('G'),a('('),v('T','0'),a(')'))
        two=MathBox(a('≤ '),mi('λ'),a('['),mi('R'),a('('),v('T','λ'),a(') - '),mi('R'),a('('),v('T','0'),a(')] ≤ 4'),mi('λ'),mi('C'),a('/5.'))
        return [(one,19),(two,20)]
    raise ValueError(n)


def marker(x,y,kind,color,size=3.4,fill=True,alpha=1):
    C.saveState();C.setStrokeColor(color);C.setFillColor(color if fill else colors.white)
    C.setLineWidth(.8)
    if alpha<1:C.setFillAlpha(alpha);C.setStrokeAlpha(alpha)
    if kind=='circle':C.circle(x,y,size,fill=1,stroke=1)
    elif kind=='square':C.rect(x-size,y-size,2*size,2*size,fill=1,stroke=1)
    else:
        p=C.beginPath()
        pts=[(x,y+size*1.25),(x-size*1.1,y-size),(x+size*1.1,y-size)] if kind=='triangle' else [(x,y+size*1.4),(x-size,y),(x,y-size*1.4),(x+size,y)]
        p.moveTo(*pts[0])
        for pt in pts[1:]:p.lineTo(*pt)
        p.close();C.drawPath(p,fill=1,stroke=1)
    C.restoreState()


def get_scenario(name):return next(s for s in DATA['scenarios'] if s['name']==name)
def get_result(scenario,policy):return next(r for r in get_scenario(scenario)['results'] if r['policy']==policy)
def pooled(scenario,policy):return get_result(scenario,policy)['pooled']


def result_figure(b):
    draw_results(b, globals())


def queue_delta_figure(b):
    queue_residence_figure(b, globals())


# PAGE 1: title, abstract, introduction, formulation, and policy.
newpage(True)
C.setStrokeColor(BLACK);C.setLineWidth(1);C.line(L,726,L+FULL,726)
C.setFont('TimesB',16);C.setFillColor(BLACK)
C.drawCentredString(W/2,705,'Queueing and Team Formation with Role Constraints')
C.setLineWidth(.8);C.line(L,692,L+FULL,692)
if REPOSITORY is not None:
    repository_url = REPOSITORY['html_url']
    if not repository_url.startswith('https://github.com/') or REPOSITORY.get('visibility') != 'public':
        raise ValueError('The paper requires a verified public GitHub repository.')
    C.setFillColor(BURGUNDY);C.setFont('SansB',9.2)
    C.drawCentredString(W/2,674,'OPEN-SOURCE IMPLEMENTATION  ·  MIT LICENSE')
    link_size = min(11.5, FULL/pdfmetrics.stringWidth(repository_url,'SansB',11.5)*11.5)
    C.setFont('SansB',link_size)
    link_width = pdfmetrics.stringWidth(repository_url,'SansB',link_size)
    C.drawCentredString(W/2,655,repository_url)
    C.setStrokeColor(BURGUNDY);C.setLineWidth(.55)
    C.line((W-link_width)/2,652,(W+link_width)/2,652)
    C.linkURL(repository_url,((W-link_width)/2,652,(W+link_width)/2,667),relative=0,thickness=0)
    C.setFillColor(GRAY);C.setFont('TimesR',8)
    C.drawString(L,34,'Data Structures Homework  |  15 October 2026')
else:
    C.setFont('TimesR',10);C.drawCentredString(W/2,673,'Data Structures Homework')
    C.setFont('TimesR',9);C.drawCentredString(W/2,658,'15 October 2026')
left=Block(y=636,label='p1-left');right=Block(L+COL+GUTTER,636,label='p1-right')
left.p('Abstract',style=ParagraphStyle('abstracthead',fontName='TimesB',fontSize=11,leading=13,alignment=TA_CENTER),after=6)
left.p('Forming a five-player MOBA team requires one player in each role, but close skill matches may require longer waits. '
       'This report studies a policy that scans players in arrival order and widens the acceptable score band as they wait. '
       'For the first player whose band contains all five roles, a 32-state dynamic program minimizes the mean absolute score difference within the team. '
       'On five balanced-role simulations, the default policy matches all 5,000 arrivals, reduces mean score gap from 331.86 to 104.69 points, and raises mean wait from 6.72 to 9.12 seconds relative to role-wise FIFO. '
       'When support players are scarce, every policy reaches only 50% completion; the unmatched queue then changes how waiting-time results should be interpreted. '
       'An optional age reward preserves the 32-state optimizer and admits a bound on local score-quality loss. '
       'The scheduling policy remains heuristic.',after=10)
left.h('1. Introduction')
left.p('Consider an old request from a top player and a queue containing many mid and ADC players but no support. '
       'Neither a wider score band nor a more elaborate optimizer can form a team. Once a support arrives, however, selecting the oldest player in each role may produce a large skill gap. '
       'The assignment therefore involves two decisions: which waiting player to serve next, and which compatible teammates to select.')
left.p('A strict score threshold makes team quality easy to control but can leave requests stranded. Ignoring scores removes that restriction at the cost of uneven teams. '
       'The policy used here starts with a narrow interval and relaxes it with age. It serves the oldest <i>feasible</i> request, rather than stopping behind the oldest request when a required role is unavailable.')
left.p('Rating estimation is treated as an upstream task. TrueSkill, for example, infers player skill from game outcomes (Herbrich et al., 2006). '
       'Here the ranking score is supplied as input; the task is to assemble one team from existing scores. No opposing-team match or outcome prediction is required.')
right.h('2. Problem and Queueing Policy')
right.p('A player is represented by <i>p</i> = (id, <i>r</i>, <i>s</i>, <i>a</i>), where <i>r</i> is one fixed role, <i>s</i> is the score, and <i>a</i> is the request time. '
        'A valid team <i>T</i> contains exactly one top, jungle, mid, ADC, and support player. For a team formed at time <i>t</i>, define')
right.eq('<i>W</i>(<i>T</i>, <i>t</i>) = (1/5) ∑<sub><i>i</i> <font name="MathSymbols">∈</font> <i>T</i></sub> (<i>t</i> - <i>a</i><sub><i>i</i></sub>),',1)
right.eq('<i>G</i>(<i>T</i>) = (1/10) ∑<sub><i>i</i> &lt; <i>j</i>; <i>i,j</i> <font name="MathSymbols">∈</font> <i>T</i></sub> |<i>s</i><sub><i>i</i></sub> - <i>s</i><sub><i>j</i></sub>|.',2)
right.p('Equation (2) interprets the assignment\'s score gap as the mean over the ten unordered player pairs. '
        'The two objectives do not specify a unique optimum: waiting for future arrivals can improve <i>G</i> while increasing <i>W</i>. '
        'The widening rate below is the explicit tradeoff parameter.')
right.h('2.1. Age-Dependent Eligibility',True)
right.p('Scan the queue in arrival order. For a candidate anchor <i>q</i>, use the integer band')
right.eq('<i>b</i><sub><i>q</i></sub>(<i>t</i>) = floor(min{<i>B</i>, <i>b</i><sub>0</sub> + <i>g</i>(<i>t</i> - <i>a</i><sub><i>q</i></sub>)}).',3)
right.p('A teammate <i>p</i> is eligible if |<i>s</i><sub><i>p</i></sub> - <i>s</i><sub><i>q</i></sub>| ≤ <i>b</i><sub><i>q</i></sub>(<i>t</i>). '
        'If any role is missing, move to the next anchor. For the first feasible anchor, minimize <i>G</i> among eligible teams that include it, remove those five players, and repeat.')
right.p('The default parameters are <i>b</i><sub>0</sub> = 50, <i>g</i> = 10 points/s, and <i>B</i> = 10<super>6</super>. '
        'Scores lie in [0, 10<super>6</super>]. Equal-time anchors keep insertion order. Equal-gap teams are ordered by their sorted (request time, ID) lists, with earlier times and then smaller IDs preferred.')
right.h('2.2. Maintaining the Queue',True)
right.p('An arrival-ordered vector preserves waiting priority. For each team selection, a score-sorted copy and five prefix counters allow binary-search interval lookup and role-availability checks. '
        'A global five-bit role mask avoids sorting if a role is absent from the entire queue.')
right.p('The band belongs to the anchor, not to each teammate: two selected scores can differ by twice its width. Matching is reconsidered after arrivals and on a timer; the simulator uses one-second ticks.')

# PAGE 2: an illustrated pipeline and the exact optimizer.
newpage();wide=Block(w=FULL,label='p2-wide');algorithm_overview(wide,globals())
top=wide.y
left=Block(y=top,label='p2-left');right=Block(L+COL+GUTTER,top,label='p2-right')
left.h('3. Exact Team Selection')
left.p('Figure 1 follows one request through the policy. Selecting the nearest player to the anchor in each role need not minimize the pairwise team gap. '
       'A subset dynamic program evaluates the choices jointly without enumerating every combination.')
left.h('3.1. An Additive Form of the Objective',True)
left.p('Write the selected scores in ascending order as <i>x</i><sub>0</sub> ≤ ... ≤ <i>x</i><sub>4</sub>. '
       'A score at position <i>k</i> appears positively in <i>k</i> differences and negatively in 4 - <i>k</i> differences. Hence')
left.eq('',4)
left.p('Each role corresponds to one bit. For a score-sorted prefix, <i>D</i>[<i>M</i>] records the least weighted sum among selections with role mask <i>M</i>. '
       'Only the empty mask is initially reachable. If <i>k</i> roles have been chosen, selecting score <i>s</i> adds (2<i>k</i> - 4)<i>s</i>. '
       'Excluding every other player with the anchor\'s role forces the anchor into any complete team.')
left.p('There are 2<super>5</super> = 32 role subsets, regardless of queue size. Intermediate costs may be negative; only the completed expression represents a sum of absolute differences.')
right.space(9)
C.setLineWidth(.8);C.setStrokeColor(BLACK);C.line(right.x,right.y,right.x+right.w,right.y);right.space(6)
right.p('<b>Algorithm 1</b> Minimum-gap team for an anchor','small',after=5)
C.setLineWidth(.4);C.line(right.x,right.y,right.x+right.w,right.y);right.space(6)
right.p('<b>Input:</b> anchor <i>q</i>, eligible players sorted by (score, ID).<br/><b>Output:</b> a team containing <i>q</i>.','small',after=6)
algorithm=[
('1','Set <i>D</i>[0] to the empty selection; all other states are unreachable.'),
('2','<b>for</b> each eligible player <i>p</i> <b>do</b>'),
('3','&nbsp;&nbsp;Skip <i>p</i> if it has <i>q</i>\'s role but is not <i>q</i>.'),
('4','&nbsp;&nbsp;Let <i>u</i> be the bit for <i>p</i>\'s role.'),
('5','&nbsp;&nbsp;<b>for</b> masks <i>M</i> = 31,...,0 <b>do</b>'),
('6','&nbsp;&nbsp;&nbsp;&nbsp;Skip unreachable states and masks containing <i>u</i>.'),
('7','&nbsp;&nbsp;&nbsp;&nbsp;Set <i>k</i> = popcount(<i>M</i>).'),
('8','&nbsp;&nbsp;&nbsp;&nbsp;Extend <i>D</i>[<i>M</i>] by <i>p</i>, adding (2<i>k</i> - 4)<i>s</i><sub><i>p</i></sub>.'),
('9','&nbsp;&nbsp;&nbsp;&nbsp;Improve <i>D</i>[<i>M</i> | <i>u</i>] by cost, then the age/ID key.'),
('10','<b>return</b> the five players in <i>D</i>[31].')]
for n,text in algorithm:
    p=Paragraph(text,STYLES['small']);_,hh=p.wrap(right.w-17,1000)
    C.setFont('TimesR',8);C.setFillColor(GRAY);C.drawRightString(right.x+10,right.y-8,n)
    p.drawOn(C,right.x+17,right.y-hh);right.y-=hh+3
C.setLineWidth(.8);C.setStrokeColor(BLACK);C.line(right.x,right.y,right.x+right.w,right.y);right.space(10)
right.p('Here | denotes bitwise OR. Descending masks prevent a state updated for the current player from being reused in the same pass. The final cost is divided by ten.')
right.p('The same search will support the waiting-aware extension in Section 4: only the incremental cost in line 8 changes. Eligibility, anchor priority, and the number of states stay fixed.')

# PAGE 3: local correctness and a bounded age-aware extension.
newpage();left=Block(label='p3-left');right=Block(L+COL+GUTTER,label='p3-right')
left.h('3.2. Correctness',True)
left.p('<b>Proposition 1.</b> <i>For a fixed feasible anchor and band, Algorithm 1 returns a valid team with minimum mean pairwise score gap, using the stated tie rule.</i>')
left.p('<i>Proof.</i> Every transition adds one unused role, so mask 31 contains five distinct roles. All candidates satisfy the band constraint, and the anchor is the only available player for its role.')
left.p('Induct on the processed prefix. Partial selections with the same mask have the same size and the same remaining candidates. '
       'By Eq. (4), every common completion adds the same future cost to both. A more expensive partial selection can therefore be discarded. '
       'Every legal team appears as a score-ordered subsequence of skip/select decisions, so the cheapest complete state is optimal.')
left.p('For equal costs, inserting a common future player into two sorted age/ID keys preserves their lexicographic order. The tie-breaking state is therefore safe to retain. <font name="Sans">□</font>')
left.h('Why Nearest-Neighbor Selection Fails',True)
left.p('Fix a top anchor at 1500 and band 50. Mid, ADC, and support each have score 1550. Jungle offers two choices:')
left.table([['Jungle choice','Anchor distance','Team gap'],['1460 (nearest)','40','46'],['1550 (joint optimum)','50','20']],[109,74,60])
left.p('Choosing 1460 is closer to the anchor but farther from three teammates. The pairwise objective therefore favors 1550.')
left.h('3.3. Cost and Scope',True)
left.table([['Operation','Worst-case time'],['Sort and role prefix counts','O(<i>n</i> log <i>n</i>)'],['Find a feasible anchor','O(<i>n</i> log <i>n</i>)'],['DP over <i>m</i> candidates','O(32<i>m</i>)'],['Remove five players','O(<i>n</i>)']],
            [COL*.61,COL*.39],caption=('Table 1.','Cost of one team selection; <i>m</i> ≤ <i>n</i>.'))
left.p('One selection takes O(<i>n</i> log <i>n</i> + 32<i>n</i>) time and O(<i>n</i>) auxiliary space. '
       'Rebuilding the index after each team gives an O(<i>n</i><super>2</super> log <i>n</i>) batch bound. '
       'The proof is local: greedy removals need not minimize total gap or maximize throughput over later teams.')
right.h('4. Serving Older Teammates')
right.p('Anchor priority does not favor older teammates when a younger candidate has a smaller gap. An optional age reward uses <i>C</i> = 120 s and λ ≥ 0:')
right.eq('',5)
right.p('Keep the 32 states and replace line 8 by this cost, where <i>k</i> is the number of selected roles:')
right.eq('',6)
right.p('This minimizes 10<i>J</i><sub>λ</sub> exactly. The weight λ has units of points/s; tested values use integer-scaled costs for exact ties. Setting λ = 0 recovers the baseline.')
right.h('4.1. An Interpretable Quality Budget',True)
right.p('<b>Proposition 2.</b> <i>For the same anchor and candidate pool, let T</i><sub>0</sub> <i>minimize G and T</i><sub>λ</sub> <i>minimize J</i><sub>λ</sub><i>. Then</i>')
right.eq('',7)
right.p('<i>Proof.</i> Optimality gives <i>J</i><sub>λ</sub>(<i>T</i><sub>λ</sub>) ≤ <i>J</i><sub>λ</sub>(<i>T</i><sub>0</sub>). Rearranging yields the first upper bound. '
        'The shared anchor cancels in the age difference; each of the other four ages lies in [0, <i>C</i>]. <font name="Sans">□</font>')
right.p('Choosing λ = 5ε/(4<i>C</i>) limits the local gap penalty to ε points. For λ = 0.1, the bound is 9.6 points. '
        'This is a sufficient bound for one selection, not a guarantee about the final online schedule.')
right.h('4.2. Exploratory Sweep',True)
ext_scarce=next(x for x in EXT['scenarios'] if x['name']=='support_scarce')['results']
erows=[['λ','Gap (pts)','Wait (s)','Pending p95 (s)']]
for run in ext_scarce:
    m=run['pooled']['original_metrics']
    erows.append([f"{run['lambda']:g}",f"{m['mean_team_pairwise_gap']:.2f}",f"{m['mean_matched_wait_seconds']:.2f}",str(run['pooled']['p95_pending_age_seconds'])])
right.table(erows,[29,67,65,82],caption=('Table 2.','Scarce-support sweep on five streams (Section 5). Wait is matched-player mean; pending p95 is cutoff age. Completion is 50% throughout.'),padding=1.5)
right.p('At λ = 0.1, pending p95 falls from 256 to 244 s and matched p95 from 123 to 119 s. Serving older players raises the completed mean wait; '
        'all-arrival queue residence stays 109.912 s. The reward redistributes service without removing the role bottleneck.')

# PAGE 4: full-width statistical figure; paired narrative underneath.
newpage();wide=Block(w=FULL,label='p4-wide');result_figure(wide)
top=wide.y-1
left=Block(y=top,label='p4-left');right=Block(L+COL+GUTTER,top,label='p4-right')
left.h('5. Experimental Setup')
left.p('All policies receive the same stream for each seed and scenario. A run contains 1,000 arrivals: five players per second for <i>t</i> = 0,...,199. '
       'At each tick, the five arrivals are enqueued before matching. Matching then continues through <i>H</i> = 319, providing 120 additional drain ticks.')
left.p('Scores are uniform integers in [1000, 2000]. The balanced scenario contains exactly 200 players per role. '
       'The support-scarce scenario contains 225 players in each other role and 100 supports. A Fisher-Yates shuffle randomizes arrival roles; SplitMix64 with rejection sampling generates the bounded integers. Seeds 1,...,5 produce five runs per scenario.')
left.h('5.1. Compared Policies',True)
left.p('<i>FIFO</i> takes the oldest player from each role whenever all five roles are available, without score filtering. '
       '<i>Fixed 50</i> uses the same anchor scan and exact optimizer as the proposed policy, but keeps the band at 50. '
       '<i>Adaptive 10</i> and <i>Adaptive 30</i> start at 50 and widen by 10 or 30 points/s, with a cap of 10<super>6</super>.')
left.p('Figure 2 plots pooled waiting time and score gap, with completion rates stated above each panel. Table 3 reports these pooled metrics; its p95 is the nearest-rank percentile of matched-player waits. '
       'Pending counts and ages are measured at the common cutoff. The five runs describe synthetic workloads rather than a sample of commercial-game traffic.')
right.h('6. Results')
right.h('6.1. Balanced Roles',True)
right.p('Adaptive 10 matches every arrival and lowers the pooled mean gap from 331.86 to 104.69 points, a 68.5% reduction relative to FIFO. '
        'Its mean wait is 9.12 s instead of 6.72 s, and p95 rises from 18 to 30 s. Thus the gain in score similarity is accompanied by both a higher mean wait and a longer tail.')
right.p('Increasing the growth rate to 30 moves the policy toward FIFO: mean wait falls to 7.14 s, while gap rises to 153.17 points. '
        'Both adaptive settings finish all players by the cutoff. Fixed 50 gives the smallest gap, 27.44 points, but only 88.2% completion, leaving 590 players pending across the five runs.')
right.p('Changing the growth rate changes eligibility, not the exact optimizer. A fixed band can leave globally available roles locally incompatible; widening resolves such score-related blocks.')
right.p('The separate age-reward sweep also matches all balanced arrivals. Mean wait ranges from 9.01 to 9.17 s and gap from 101.32 to 104.69 points across the seven weights; changes are small and not monotone.')
right.h('6.2. Scarce Support',True)
right.p('Only 100 supports arrive in each scarce run. The role constraint therefore permits at most 100 teams, or 50% of the 1,000 players. '
        'Every tested policy reaches this bound. Unlike the balanced case, Fixed 50 sacrifices no completion rate here and yields the smallest gap, 18.60 points; adaptive widening is not uniformly preferable.')

# PAGE 5: full-width results table; censoring, discussion, references.
newpage();wide=Block(w=FULL,label='p5-wide')
rows=[['Roles','Policy','Match (%)','Mean wait (s)','p95 (s)','Gap (pts)','<i>W</i><sub>H</sub> (s)','Pending']]
for scenario,title in [('balanced','Balanced'),('support_scarce','Scarce')]:
    for i,key in enumerate(POLICIES):
        m=pooled(scenario,key)
        rows.append([title if i==0 else '',LABELS[key],f"{100*m['match_rate']:.1f}",f"{m['mean_matched_wait_seconds']:.2f}",str(m['p95_matched_wait_seconds']),f"{m['mean_team_pairwise_gap']:.2f}",f"{m['observed_mean_queue_time_seconds']:.2f}",f"{m['pending_players']:,}"])
wide.table(rows,[54,83,51,68,42,65,62,79],caption=('Table 3.','Pooled results for five seeds and 5,000 arrivals per policy in each scenario. Mean wait and p95 refer only to matched players. <i>W</i><sub>H</sub> includes observed residence time for every arrival through <i>H</i> = 319 s (Eq. (8)). Gap is the mean of the ten pairwise differences per team.'),midrules=(5,))
top=wide.y
left=Block(y=top,label='p5-left');right=Block(L+COL+GUTTER,top,label='p5-right')
left.h('6.3. Accounting for Unmatched Players',True)
left.p('To keep pending requests in the evaluation, let <i>d</i><sub><i>i</i></sub> be player <i>i</i>\'s match time, or infinity if unmatched. Define the observed queue residence time')
left.eq('<i>W</i><sub><i>H</i></sub> = (1/<i>N</i>) ∑<sub><i>i</i>=1</sub><super><i>N</i></super> [min(<i>d</i><sub><i>i</i></sub>, <i>H</i>) - <i>a</i><sub><i>i</i></sub>].',8)
left.p('This quantity counts each completed wait and each pending player\'s current age. It is truncated at the cutoff, not an estimate of eventual completed waiting time.')
queue_delta_figure(left)
left.p('In the scarce setting, FIFO has <i>W</i><sub>H</sub> = 109.71 s and Adaptive 10 has 109.91 s, despite the latter\'s lower matched-only mean. '
       'Their oldest pending requests are 238 and 273 s old, respectively (maximum over seeds). Each policy leaves 625 players in each non-support role and no support pending.')
right.h('7. Discussion and Conclusion')
right.p('Widening is useful when score compatibility, rather than role supply, prevents progress. The balanced experiment illustrates that case. '
        'The scarce experiment illustrates the opposite: enough score-compatible combinations exist to use every support, and no policy can exceed the role-supply limit.')
right.p('Age priority gives no minimum-wait guarantee: an infeasible player can remain behind, and newer players may join a team. Missing roles can cause unbounded waiting. Parties, latency, and individual score limits would require additional constraints.')
right.p('The age reward adds a controlled preference for older teammates. It can change later candidate pools, so Table 2 need not be monotone in gap. '
        'The capped reward provides no starvation guarantee. A useful next step is to distinguish ticks blocked by missing roles from those blocked only by score compatibility.')
right.p('A small exact optimizer makes the online policy easy to test. In balanced streams, growth 10 yields closer teams for 2.40 s of extra mean wait. Choosing a band and age reward should depend on role supply and acceptable queue tails.')
right.h('References')
right.p('Herbrich, R., Minka, T., and Graepel, T. TrueSkill: A Bayesian skill rating system. In <i>Advances in Neural Information Processing Systems</i>, 19:569-576, 2006. '
        '<link href="https://www.microsoft.com/en-us/research/wp-content/uploads/2007/01/NIPS2006_0688.pdf" color="#181818">Author manuscript.</link>','small',after=8)
right.p('ICML. <i>Submission and Formatting Instructions for ICML 2026</i>, 2026. '
        '<link href="https://media.icml.cc/Conferences/ICML2026/Styles/example_paper.pdf" color="#181818">Official example paper.</link> Used as a typography and figure-format reference.','small',after=8)
right.p('Course assignment. <i>Implementing a game matching algorithm.</i> Problem statement supplied as an image. The report adopts its five-role requirement and two optimization objectives.','small')

# PAGE 6: compact appendix, full-width benchmark then two-column implementation details.
newpage();wide=Block(w=FULL,label='p6-wide')
wide.h('Appendix A. Implementation and Reproducibility')
bench=[['Workload','Original (ms)','Revised (ms)','What is measured']]
for key,name,desc in [('equal_scores_500','500 players; equal scores','One call forming 100 teams'),('mixed_scores_500','500 players; mixed scores','One call forming 100 teams'),('missing_role_5000_100_ticks','5,000 players; missing role','100 ticks; no teams formed')]:
    bench.append([name,f"{BEFORE[key]['median_ms']:.3f}",f"{AFTER[key]['median_ms']:.3f}",desc])
wide.table(bench,[172,80,80,172],caption=('Table 4.','Local microbenchmarks, reported as median elapsed time over seven runs. Both versions use C++17 and Apple Clang 21 with -O2 on the same ARM64 macOS environment. Queue construction is excluded. The first two workloads allow unrestricted score bands.'))
top=wide.y
left=Block(y=top,label='p6-left');right=Block(L+COL+GUTTER,top,label='p6-right')
left.h('A.1. Implementation Choices',True)
left.p('The reference implementation is single-threaded. Joining and cancellation scan the vector for a player ID and take O(<i>n</i>) time. '
       'Matching removes all five selected records before the next search. The CLI rejects extra tokens before mutating queue state, and request/match times must be nonnegative and nondecreasing.')
left.p('Each DP state now stores five fixed player slots and a sorted age/ID key. Inserting a candidate updates that key directly, avoiding temporary vectors and repeated sorting during tie comparisons. '
       'A preliminary role-mask scan returns before building a score index when a required role is globally absent. These changes preserve the selection rule and improve constants; they do not change the general batch bound.')
left.p('Table 4 compares the preserved original header with the revised implementation. The speedups depend on workload and compiler behavior. '
       'They should not be interpreted as server throughput, and the benchmark excludes queue construction, which still uses linear ID checks.')
left.h('A.2. Verification',True)
left.p('The independent oracle enumerates all role combinations for the first feasible anchor, sums the ten absolute differences directly, and sorts the final age/ID key. '
       'It does not use Eq. (4). Across 1,000 seeded queues, all 1,437 selected teams match the oracle exactly.')
left.p('Assertions also check role uniqueness, anchor inclusion, band eligibility, unchanged player records, no reuse, and absence of a feasible team after a matching batch. '
       'Targeted cases cover missing roles, equal timestamps, fractional growth, caps, score extremes, cancellation/rejoining, invalid policies, and timestamps near the integer limit.')
left.p('Five malformed CLI commands are rejected without side effects. The test suite also passes AddressSanitizer and UndefinedBehaviorSanitizer without diagnostics.')
left.p('The extension passes 3,822 exhaustive checks over 2,100 queues, including the gap bound. At λ = 0, IDs and times match the baseline on 300 queues and ten streams. Its sanitizer checks also pass.')
right.h('A.3. Reproducing the Results',True)
right.p('The project builds with a C++17 compiler and <font name="Mono" size="8.5">make</font>. Python 3 is used only for the CLI regression and report-generation utilities. From the project directory:')
right.code('''make
make waiting-experiment
make test
make sanitize
make experiment
make benchmark-compare''')
right.p('The simulation writes <font name="Mono" size="8.3">experiment_results.json</font>, including every seed and pooled metrics. '
        'The timing command writes both summaries under <font name="Mono" size="8.3">results/</font>. '
        'The original matching header is retained under <font name="Mono" size="8.3">reference/</font>. '
        'The separate age-reward prototype and full sweep instructions are under <font name="Mono" size="8.3">research/</font>.')
right.h('A.4. A Small End-to-End Example',True)
right.p('Enter the following commands after <font name="Mono" size="8.5">make run</font>. Roles are abbreviated as top, jun, mid, adc, and sup.')
right.code('''join 1 top 1500 0
join 2 jun 1510 1
join 3 mid 1490 2
join 4 adc 1520 3
join 5 sup 1480 4
match 4
quit''')
right.p('At time 4, player 1 is the anchor and its band is 50 + 10 × 4 = 90 points. All roles lie within [1410, 1590]. '
        'The waits are 4, 3, 2, 1, 0 s, so the mean is 2 s. The sorted scores are 1480, 1490, 1500, 1510, 1520; Eq. (4) gives a pairwise sum of 200 and a mean gap of 20.')
right.h('A.5. Reporting Conventions',True)
right.p('Figures 2 and 3 and Table 3 pool observations over five runs. Per-seed data and run-level standard deviations are supplied separately; no confidence interval or significance test is claimed. '
        'Baseline measurements were saved on 19 September 2026; the age-reward sweep was added on 11 October 2026. The complete per-seed sweep is included with the submission.')
C.save()
(ROOT/'tmp/pdfs/paper_layout_log.json').write_text(json.dumps(DOCLOG,indent=2))
print(f'Created {OUT}: {PAGE} pages; all content passed layout bounds.')
