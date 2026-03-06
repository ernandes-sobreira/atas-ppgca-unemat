from flask import Flask, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import Image as RLImage
from docx import Document as DocxDocument
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io, os

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
LOGO1 = os.path.join(BASE, 'logo1.png')
LOGO2 = os.path.join(BASE, 'logo2.png')
LOGO3 = os.path.join(BASE, 'logo3.jpeg')

TITLES = {
    ('qualificacao','mestrado'):  'ATA DO EXAME DE QUALIFICAÇÃO DE DISSERTAÇÃO',
    ('qualificacao','doutorado'): 'ATA DE EXAME DE QUALIFICAÇÃO DE DOUTORADO',
    ('defesa','mestrado'):        'ATA DE DEFESA DE DISSERTAÇÃO',
    ('defesa','doutorado'):       'ATA DE DEFESA DE TESE',
}

def get_linhas(tipo, nivel, d):
    niv  = 'Mestre' if nivel == 'mestrado' else ('Doutor' if tipo=='defesa' else 'doutor')
    trab = 'dissertação' if nivel == 'mestrado' else 'tese'
    if tipo == 'defesa':
        return [(
            f"Aos {d['dia']} dias do mês de {d['mes']}, do ano de dois mil e vinte e {d['ano']}, "
            f"às {d['hora']}, {d['modalidade']}, realizou-se a Defesa do(a) discente "
            f"{d['discente']}, como parte das exigências para obtenção do título de {niv}, com a "
            f"{trab} intitulada: \u201c{d['titulo']}\u201d do Curso de Pós-graduação Stricto Sensu em "
            f"Ciências Ambientais, perante a banca examinadora, composta pelos(as) examinadores(as) "
            f"listados(as) abaixo, onde a sessão foi aberta pelo(a) presidente "
            f"{d['or_trat']} {d['or_nome']} e, após apresentação, o(a) discente foi arguido(a) "
            f"pela Banca Examinadora. Em sessão secreta foi decidido o resultado da defesa, sendo "
            f"o(a) discente considerado(a) {d['resultado']}. Encerrada a sessão secreta, o Presidente "
            f"informou o resultado. Nada mais havendo a tratar, eu, Presidente da banca, lavrei a "
            f"presente ata que assino juntamente com os membros da Banca Examinadora. Para a obtenção "
            f"do título ainda é necessário o cumprimento das exigências contidas no Regimento do "
            f"Programa de Pós-graduação Stricto Sensu em Ciências Ambientais - Resolução n.º {d['resolucao']}."
        )]
    else:
        return [
            (f"Aos {d['dia']} dias do mês de {d['mes']} do ano de dois mil e vinte e {d['ano']}, "
             f"às {d['hora']}, {d['modalidade']} realizou-se o Exame de Qualificação do(a) discente "
             f"{d['discente']}, como parte das exigências para obtenção do título de {niv}, com a "
             f"versão preliminar da {trab} intitulada: \u201c{d['titulo']}\u201d do Curso de "
             f"Pós-graduação Stricto Sensu em Ciências Ambientais, perante a banca examinadora, "
             f"composta pelos professores abaixo."),
            '',
            f"Após apresentação e arguição, a banca examinadora conclui pela APROVAÇÃO do(a) discente com conceito final do Exame de Qualificação: {d['conceito']}",
            '',
            'I. \u201cA\u201d \u2013 aprovação, considerando pequenas reformulações sugeridas pela banca;',
            'II. \u201cB\u201d \u2013 aprovação, com reformulações estruturais de acordo com as sugestões da Banca;',
            'III. \u201cC\u201d \u2013 aprovação, com reformulações estruturais e metodológicas apresentadas pela Banca;',
            'IV. \u201cD\u201d \u2013 Reprovação e recomendação de ampla reformulação para novo Exame de Qualificação.',
            '',
            'Em seguida a presidente da banca agradeceu a participação dos presentes e deu por encerrada a presente reunião, a tudo presenciei, lavrei e assinei a presente ata.',
        ]

def parse_membros(form, prefix):
    membros = [{'trat': form.get(f'{prefix}_or_trat','Prof. Dr.'),
                'nome': form.get(f'{prefix}_or_nome',''),
                'cpf':  form.get(f'{prefix}_or_cpf',''),
                'inst': form.get(f'{prefix}_or_inst','UNEMAT')}]
    for i in range(1, 20):
        nome = form.get(f'{prefix}_m{i}_nome','').strip()
        if not nome: break
        membros.append({'trat': form.get(f'{prefix}_m{i}_trat','Prof. Dr.'),
                        'nome': nome,
                        'cpf':  form.get(f'{prefix}_m{i}_cpf',''),
                        'inst': form.get(f'{prefix}_m{i}_inst','UNEMAT')})
    return membros

def gerar_pdf(titulo, linhas, membros):
    buf = io.BytesIO()
    W_page, _ = A4
    ML,MR,MT,MB = 25*mm,20*mm,18*mm,20*mm
    W = W_page - ML - MR
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    s = lambda **kw: ParagraphStyle('s', **kw)
    sIB = s(fontName='Helvetica-Bold', fontSize=9,  alignment=TA_CENTER, leading=12)
    sI  = s(fontName='Helvetica',      fontSize=8,  alignment=TA_CENTER, leading=11)
    sT  = s(fontName='Times-Bold',     fontSize=13, alignment=TA_CENTER, leading=17, spaceBefore=8, spaceAfter=12)
    sB  = s(fontName='Times-Roman',    fontSize=11, alignment=TA_JUSTIFY, leading=17, firstLineIndent=18, spaceAfter=6)
    sL  = s(fontName='Times-Roman',    fontSize=11, alignment=TA_JUSTIFY, leading=16, spaceAfter=4)
    sSN = s(fontName='Times-Bold',     fontSize=9,  alignment=TA_CENTER, leading=12)
    sSI = s(fontName='Times-Roman',    fontSize=8,  alignment=TA_CENTER, leading=11, textColor=colors.Color(.3,.3,.3))
    sSC = s(fontName='Times-Roman',    fontSize=7.5,alignment=TA_CENTER, leading=10, textColor=colors.Color(.4,.4,.4))
    sFT = s(fontName='Helvetica',      fontSize=7,  alignment=TA_CENTER, leading=9,  textColor=colors.Color(.6,.6,.6))

    story = []
    ht = Table([[RLImage(LOGO1,18*mm,20*mm),
                 [Paragraph('UNIVERSIDADE DO ESTADO DE MATO GROSSO',sIB),
                  Paragraph('Programa de Pós-Graduação Stricto Sensu em Ciências Ambientais',sI),
                  Paragraph('Campus de Cáceres – Alta Floresta – Nova Xavantina',sI)],
                 RLImage(LOGO2,18*mm,20*mm)]],
                colWidths=[22*mm, W-44*mm, 22*mm])
    ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story += [ht, HRFlowable(width=W,thickness=0.5,color=colors.Color(.7,.7,.7),spaceAfter=4),
              Paragraph(titulo, sT)]

    for l in linhas:
        if l == '': story.append(Spacer(1,5))
        elif any(l.startswith(x) for x in ['I.','II.','III.','IV.']): story.append(Paragraph(l,sL))
        else: story.append(Paragraph(l,sB))

    story.append(Spacer(1,14))
    SH = 42*mm
    def sc(m):
        return [Spacer(1,SH-20*mm), Paragraph('_'*44,sSN),
                Paragraph(f'{m["trat"]} {m["nome"]}',sSN),
                Paragraph(m['inst'],sSI),
                Paragraph(f'CPF: {m["cpf"]}',sSC) if m.get('cpf') else Spacer(1,4)]
    rows = []
    for i in range(0,len(membros),2):
        a,b = membros[i], membros[i+1] if i+1<len(membros) else None
        rows.append([sc(a), sc(b) if b else [Spacer(1,SH)]])
    st = Table(rows, colWidths=[W/2-3*mm,W/2-3*mm], rowHeights=[SH]*len(rows))
    st.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.5,colors.Color(.6,.6,.6)),
        ('INNERGRID',(0,0),(-1,-1),0.5,colors.Color(.6,.6,.6)),
        ('VALIGN',(0,0),(-1,-1),'BOTTOM'),('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('BACKGROUND',(0,0),(-1,-1),colors.white)]))
    story += [st, Spacer(1,8),
              Paragraph('Concepção: Prof. Dr. Ernandes Sobreira Oliveira Junior · Biólogo · UNEMAT',sFT)]
    doc.build(story)
    buf.seek(0)
    return buf

def gerar_docx(titulo, linhas, membros):
    buf = io.BytesIO()
    doc = DocxDocument()
    sec = doc.sections[0]
    sec.page_width=Mm(210); sec.page_height=Mm(297)
    sec.left_margin=Mm(25); sec.right_margin=Mm(20)
    sec.top_margin=Mm(18);  sec.bottom_margin=Mm(20)

    def p(txt, bold=False, size=10, align=WD_ALIGN_PARAGRAPH.CENTER,
          font='Arial', sa=4, sb=0, fi=None, italic=False, rgb=None):
        para = doc.add_paragraph()
        para.alignment = align
        para.paragraph_format.space_after  = Pt(sa)
        para.paragraph_format.space_before = Pt(sb)
        if fi: para.paragraph_format.first_line_indent = Mm(fi)
        r = para.add_run(txt)
        r.bold=bold; r.italic=italic
        r.font.size=Pt(size); r.font.name=font
        if rgb: r.font.color.rgb=RGBColor(*rgb)
        return para

    p('UNIVERSIDADE DO ESTADO DE MATO GROSSO', bold=True, size=10)
    p('Programa de Pós-Graduação Stricto Sensu em Ciências Ambientais', size=9)
    p('Campus de Cáceres – Alta Floresta – Nova Xavantina', size=9, sa=6)
    sep = doc.add_paragraph(); sep.paragraph_format.space_after=Pt(4)
    pPr = sep._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bot = OxmlElement('w:bottom')
    bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'4')
    bot.set(qn('w:space'),'1');    bot.set(qn('w:color'),'AAAAAA')
    pBdr.append(bot); pPr.append(pBdr)
    p(titulo, bold=True, size=13, font='Times New Roman', sb=8, sa=12)

    for l in linhas:
        if l == '': doc.add_paragraph().paragraph_format.space_after=Pt(3); continue
        isit = any(l.startswith(x) for x in ['I.','II.','III.','IV.'])
        p(l, size=11, align=WD_ALIGN_PARAGRAPH.JUSTIFY, font='Times New Roman', sa=5, fi=(None if isit else 10))

    doc.add_paragraph().paragraph_format.space_after=Pt(6)
    n_rows = (len(membros)+1)//2
    tbl = doc.add_table(rows=n_rows, cols=2)
    tbl.style='Table Grid'
    for row in tbl.rows:
        row.height=Mm(42)
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            for side in ['top','left','bottom','right']:
                b=OxmlElement(f'w:{side}')
                b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'6')
                b.set(qn('w:space'),'0');    b.set(qn('w:color'),'AAAAAA')
                tcPr.append(b)

    for idx, m in enumerate(membros):
        cell = tbl.cell(idx//2, idx%2)
        for para in cell.paragraphs:
            for r in para.runs: r.text=''
        def cp(txt='', bold=False, size=9, rgb=None):
            para = cell.add_paragraph()
            para.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if txt:
                r=para.add_run(txt); r.bold=bold
                r.font.size=Pt(size); r.font.name='Times New Roman'
                if rgb: r.font.color.rgb=RGBColor(*rgb)
        for _ in range(3): cp()
        cp('_'*42)
        cp(f'{m["trat"]} {m["nome"]}', bold=True)
        cp(m['inst'], rgb=(80,80,80))
        if m.get('cpf'): cp(f'CPF: {m["cpf"]}', size=8, rgb=(100,100,100))

    doc.add_paragraph().paragraph_format.space_after=Pt(4)
    p('Concepção: Prof. Dr. Ernandes Sobreira Oliveira Junior · Biólogo · UNEMAT',
      size=7, italic=True, rgb=(150,150,150))
    doc.save(buf); buf.seek(0)
    return buf

@app.route('/logo1')
def logo1(): return send_file(LOGO1, mimetype='image/png')
@app.route('/logo2')
def logo2(): return send_file(LOGO2, mimetype='image/png')
@app.route('/logo3')
def logo3(): return send_file(LOGO3, mimetype='image/jpeg')

@app.route('/gerar', methods=['POST'])
def gerar():
    form   = request.form
    tipo   = form.get('tipo','defesa')
    nivel  = form.get('nivel','mestrado')
    fmt    = form.get('fmt','pdf')
    prefix = {'qualificacao':{'mestrado':'qm','doutorado':'qd'},
              'defesa':       {'mestrado':'dm','doutorado':'dd'}}[tipo][nivel]
    d = dict(dia=form.get('dia',''), mes=form.get('mes',''), ano=form.get('ano',''),
             hora=form.get('hora',''), modalidade=form.get('modalidade','de forma virtual'),
             discente=form.get('discente',''), titulo=form.get('titulo',''),
             or_trat=form.get(f'{prefix}_or_trat',''), or_nome=form.get(f'{prefix}_or_nome',''),
             resultado=form.get('resultado','APROVADO(A)'),
             conceito=form.get('conceito','A'),
             resolucao=form.get('resolucao',''))
    membros = parse_membros(form, prefix)
    titulo  = TITLES[(tipo, nivel)]
    linhas  = get_linhas(tipo, nivel, d)
    nome    = titulo.replace(' ','_').replace('/','_')
    if fmt == 'pdf':
        return send_file(gerar_pdf(titulo,linhas,membros), mimetype='application/pdf',
                         as_attachment=True, download_name=f'{nome}.pdf')
    else:
        return send_file(gerar_docx(titulo,linhas,membros),
                         mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         as_attachment=True, download_name=f'{nome}.docx')

@app.route('/')
def index():
    def mes_opts():
        meses = ['janeiro','fevereiro','março','abril','maio','junho',
                 'julho','agosto','setembro','outubro','novembro','dezembro']
        return ''.join(f'<option value="{m}">{m.capitalize()}</option>' for m in meses)

    def or_block(p):
        return f'''<div class="mb">
          <div class="mbl"><span class="badge">P</span> Orientador(a) / Presidente</div>
          <div class="row r3">
            <div class="f"><label>Tratamento</label>
              <select name="{p}_or_trat"><option>Prof. Dr.</option><option>Profa. Dra.</option><option>Prof. Me.</option><option>Profa. Me.</option></select></div>
            <div class="f"><label>Nome *</label>
              <input type="text" name="{p}_or_nome" required placeholder="Nome completo"></div>
            <div class="f"><label>CPF</label>
              <input type="text" name="{p}_or_cpf" placeholder="000.000.000-00"></div>
          </div>
          <div class="row r2">
            <div class="f"><label>Instituição</label>
              <input type="text" name="{p}_or_inst" value="UNEMAT"></div>
          </div></div>'''

    def mb_block(p, n, label):
        return f'''<div class="mb">
          <div class="mbl"><span class="badge">{n+1}</span> {label}</div>
          <div class="row r3">
            <div class="f"><label>Tratamento</label>
              <select name="{p}_m{n}_trat"><option>Prof. Dr.</option><option>Profa. Dra.</option><option>Prof. Me.</option><option>Profa. Me.</option></select></div>
            <div class="f"><label>Nome</label>
              <input type="text" name="{p}_m{n}_nome" placeholder="Nome completo"></div>
            <div class="f"><label>CPF</label>
              <input type="text" name="{p}_m{n}_cpf" placeholder="000.000.000-00"></div>
          </div>
          <div class="row r2">
            <div class="f"><label>Instituição</label>
              <input type="text" name="{p}_m{n}_inst" value="UNEMAT"></div>
          </div></div>'''

    def form_fields(prefix, trab, n_membros, resolucao_default, is_qual):
        members = ''.join(mb_block(prefix, i+1, f'Membro {i+1}') for i in range(n_membros))
        res = f'''<div class="f"><label>Conceito Final *</label>
            <select name="conceito">
              <option value="A">A – Aprovação com pequenas reformulações</option>
              <option value="B">B – Aprovação com reformulações estruturais</option>
              <option value="C">C – Aprovação com reformulações estruturais e metodológicas</option>
              <option value="D">D – Reprovação</option>
            </select></div>''' if is_qual else f'''<div class="f"><label>Resultado *</label>
            <select name="resultado">
              <option value="APROVADO(A)">APROVADO(A)</option>
              <option value="REPROVADO(A)">REPROVADO(A)</option>
            </select></div>'''
        return f'''
        <div class="sec">📅 Data e Hora</div>
        <div class="row r3">
          <div class="f"><label>Dia (por extenso) *</label>
            <input type="text" name="dia" required placeholder="vinte e cinco"></div>
          <div class="f"><label>Mês *</label>
            <select name="mes">{mes_opts()}</select></div>
          <div class="f"><label>Ano (ex: cinco) *</label>
            <input type="text" name="ano" required placeholder="cinco"></div>
        </div>
        <div class="row r2">
          <div class="f"><label>Horário (por extenso) *</label>
            <input type="text" name="hora" required placeholder="quatorze horas"></div>
          <div class="f"><label>Modalidade</label>
            <select name="modalidade">
              <option value="de forma virtual">Virtual (online)</option>
              <option value="presencialmente">Presencial</option>
              <option value="em formato híbrido">Híbrido</option>
            </select></div>
        </div>
        <div class="sec">👤 Discente</div>
        <div class="f"><label>Nome completo *</label>
          <input type="text" name="discente" required placeholder="Nome completo do(a) discente"></div>
        <div class="f"><label>Título da {trab} *</label>
          <input type="text" name="titulo" required placeholder="Título completo"></div>
        <div class="sec">👨‍🏫 Orientador(a) – Presidente</div>
        {or_block(prefix)}
        <div class="sec">👥 Membros da Banca</div>
        <div id="members-{prefix}">{members}</div>
        <button type="button" class="btn-add" onclick="addMember('{prefix}')">+ Adicionar membro</button>
        <div class="sec">✅ Resultado</div>
        <div class="row r2">
          {res}
          <div class="f"><label>Resolução</label>
            <input type="text" name="resolucao" value="{resolucao_default}"></div>
        </div>
        <div class="btn-row">
          <button type="submit" name="fmt" value="pdf"  class="btn btn-green">⬇ Baixar PDF</button>
          <button type="submit" name="fmt" value="docx" class="btn btn-gold">📄 Baixar Word</button>
        </div>'''

    tabs = {
        'qm': ('qualificacao','mestrado','dissertação', 2,'10/2026-CONSUNI',  True,  '📋 Qualif. Mestrado'),
        'qd': ('qualificacao','doutorado','tese',       3,'046/2024-CONSUNI', True,  '📋 Qualif. Doutorado'),
        'dm': ('defesa',      'mestrado','dissertação', 3,'10/2026-CONSUNI',  False, '🎓 Defesa Mestrado'),
        'dd': ('defesa',      'doutorado','tese',       4,'046/2024-CONSUNI', False, '🎓 Defesa Doutorado'),
    }

    btn_parts = []
    for i,(k,v) in enumerate(tabs.items()):
        active = ' active' if i==0 else ''
        btn = '<button id="btn-' + k + '" class="tab-btn' + active
        btn += '" onclick="setTab(' + chr(39) + k + chr(39) + ')">' + v[6] + '</button>'
        btn_parts.append(btn)
    tab_buttons = ''.join(btn_parts)

    tab_forms = ''
    for i,(k,v) in enumerate(tabs.items()):
        tipo,nivel,trab,n_mb,resolucao,is_qual,_ = v
        fields = form_fields(k, trab, n_mb, resolucao, is_qual)
        display = '' if i==0 else ' style="display:none"'
        tab_forms += f'''
        <div id="tab-{k}" class="tab-pane"{display}>
          <form action="/gerar" method="POST">
            <input type="hidden" name="tipo"  value="{tipo}">
            <input type="hidden" name="nivel" value="{nivel}">
            {fields}
          </form>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gerador de Atas – PPGCA/UNEMAT</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:linear-gradient(135deg,#0e3d26,#1a5c3a 50%,#1d6640);min-height:100vh}}
.hero{{padding:28px 20px 0;text-align:center}}
.hero-logos{{display:flex;justify-content:center;align-items:center;gap:20px;margin-bottom:14px;flex-wrap:wrap}}
.hero-logos img{{height:66px;object-fit:contain;filter:drop-shadow(0 2px 8px rgba(0,0,0,.4))}}
.hero h1{{font-family:'Playfair Display',serif;font-size:clamp(1.3rem,4vw,2.1rem);color:#fff;margin-bottom:5px}}
.hero p{{font-size:.86rem;color:rgba(255,255,255,.75);margin-bottom:3px}}
.credit{{font-size:.75rem;color:#f0d98a;margin-bottom:20px;font-style:italic}}
.tab-bar{{display:flex;justify-content:center;gap:4px;flex-wrap:wrap;padding:0 12px}}
.tab-btn{{background:rgba(255,255,255,.12);color:rgba(255,255,255,.82);border:1.5px solid rgba(255,255,255,.18);border-bottom:none;border-radius:10px 10px 0 0;padding:9px 14px;font-family:'DM Sans',sans-serif;font-size:.81rem;font-weight:500;cursor:pointer;transition:.2s;white-space:nowrap}}
.tab-btn:hover{{background:rgba(255,255,255,.2);color:#fff}}
.tab-btn.active{{background:#fff;color:#1a5c3a;font-weight:700;border-color:#fff}}
.card{{background:#fff;border-radius:0 0 12px 12px;box-shadow:0 8px 40px rgba(26,92,58,.18);max-width:820px;margin:0 auto;padding:26px 30px 30px;position:relative}}
.card::before{{content:'';position:absolute;top:0;left:30px;right:30px;height:3px;background:linear-gradient(90deg,#1a5c3a,#c8a84b,#1a5c3a);border-radius:0 0 4px 4px}}
.wrap{{max-width:820px;margin:0 auto;padding:0 12px 48px}}
.sec{{font-family:'Playfair Display',serif;font-size:.95rem;color:#1a5c3a;margin:18px 0 9px;padding-bottom:5px;border-bottom:1.5px solid #e8f4ee;display:flex;align-items:center;gap:7px}}
.sec::before{{content:'';width:4px;height:14px;background:#c8a84b;border-radius:2px;flex-shrink:0}}
.row{{display:grid;gap:11px}}
.r2{{grid-template-columns:1fr 1fr}}
.r3{{grid-template-columns:1fr 1fr 1fr}}
.f{{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}}
.f label{{font-size:.7rem;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.06em}}
.f input,.f select{{border:1.5px solid #d1d5db;border-radius:8px;padding:10px 12px;font-family:'DM Sans',sans-serif;font-size:.88rem;color:#111;background:#f9fafb;outline:none;width:100%;transition:.15s}}
.f input:focus,.f select:focus{{border-color:#1a5c3a;box-shadow:0 0 0 3px rgba(26,92,58,.1);background:#fff}}
.mb{{background:#f9fafb;border:1.5px solid #eee;border-radius:10px;padding:12px 14px 4px;margin-bottom:9px}}
.mbl{{font-size:.7rem;font-weight:700;color:#1a5c3a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;display:flex;align-items:center;gap:5px}}
.badge{{background:#1a5c3a;color:#fff;font-size:.62rem;font-weight:700;padding:2px 7px;border-radius:20px}}
.btn-add{{background:#fff;color:#1a5c3a;border:1.5px solid #1a5c3a;border-radius:8px;padding:7px 13px;font-family:'DM Sans',sans-serif;font-size:.79rem;font-weight:600;cursor:pointer;margin:3px 0 4px;transition:.15s}}
.btn-add:hover{{background:#e8f4ee}}
.btn-row{{display:flex;gap:8px;margin-top:22px;flex-wrap:wrap}}
.btn{{padding:13px 26px;border-radius:10px;font-family:'DM Sans',sans-serif;font-size:.93rem;font-weight:700;cursor:pointer;border:none;transition:.18s}}
.btn-green{{background:linear-gradient(135deg,#1a5c3a,#2d7a52);color:#fff;box-shadow:0 4px 16px rgba(26,92,58,.25)}}
.btn-green:hover{{transform:translateY(-1px)}}
.btn-gold{{background:linear-gradient(135deg,#c8a84b,#b8943b);color:#fff;box-shadow:0 4px 16px rgba(200,168,75,.3)}}
.btn-gold:hover{{transform:translateY(-1px)}}
@media(max-width:580px){{.card{{padding:15px 12px}}.r2,.r3{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="hero">
  <div class="hero-logos">
    <img src="/logo1" alt="MT"><img src="/logo2" alt="UNEMAT"><img src="/logo3" alt="CA">
  </div>
  <h1>Gerador de Atas Acadêmicas</h1>
  <p>Programa de Pós-Graduação Stricto Sensu em Ciências Ambientais – UNEMAT</p>
  <p class="credit">💡 Concepção: Prof. Dr. Ernandes Sobreira Oliveira Junior · Biólogo · UNEMAT | Moldado com IA</p>
</div>
<div class="wrap">
  <div class="tab-bar">{tab_buttons}</div>
  <div class="card">{tab_forms}</div>
</div>
<script>
function setTab(id) {{
  document.querySelectorAll('.tab-pane').forEach(function(e){{ e.style.display='none'; }});
  document.querySelectorAll('.tab-btn').forEach(function(b){{ b.classList.remove('active'); }});
  document.getElementById('tab-'+id).style.display='';
  document.getElementById('btn-'+id).classList.add('active');
}}
var memberCount = {{}};
function addMember(prefix) {{
  var container = document.getElementById('members-'+prefix);
  var n = container.querySelectorAll('.mb').length + 1;
  var div = document.createElement('div');
  div.className = 'mb';
  div.innerHTML = '<div class="mbl"><span class="badge">'+(n+1)+'</span> Membro '+n
    +' <button type="button" onclick="this.closest(\\'.mb\\').remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:#bbb;font-size:1rem">✕</button></div>'
    +'<div class="row r3">'
    +'<div class="f"><label>Tratamento</label><select name="'+prefix+'_m'+n+'_trat"><option>Prof. Dr.</option><option>Profa. Dra.</option><option>Prof. Me.</option><option>Profa. Me.</option></select></div>'
    +'<div class="f"><label>Nome</label><input type="text" name="'+prefix+'_m'+n+'_nome" placeholder="Nome completo"></div>'
    +'<div class="f"><label>CPF</label><input type="text" name="'+prefix+'_m'+n+'_cpf" placeholder="000.000.000-00"></div>'
    +'</div><div class="row r2">'
    +'<div class="f"><label>Instituição</label><input type="text" name="'+prefix+'_m'+n+'_inst" value="UNEMAT"></div>'
    +'</div>';
  container.appendChild(div);
}}
</script>
</body>
</html>'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
