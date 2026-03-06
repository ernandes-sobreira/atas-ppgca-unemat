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
    ('qualificacao','mestrado'):  'ATA DO EXAME DE QUALIFICACAO DE DISSERTACAO',
    ('qualificacao','doutorado'): 'ATA DE EXAME DE QUALIFICACAO DE DOUTORADO',
    ('defesa','mestrado'):        'ATA DE DEFESA DE DISSERTACAO',
    ('defesa','doutorado'):       'ATA DE DEFESA DE TESE',
}

TITLES_PT = {
    ('qualificacao','mestrado'):  'ATA DO EXAME DE QUALIFICA\u00c7\u00c3O DE DISSERTA\u00c7\u00c3O',
    ('qualificacao','doutorado'): 'ATA DE EXAME DE QUALIFICA\u00c7\u00c3O DE DOUTORADO',
    ('defesa','mestrado'):        'ATA DE DEFESA DE DISSERTA\u00c7\u00c3O',
    ('defesa','doutorado'):       'ATA DE DEFESA DE TESE',
}

def get_linhas(tipo, nivel, d):
    niv  = 'Mestre' if nivel == 'mestrado' else ('Doutor' if tipo=='defesa' else 'doutor')
    trab = 'disserta\u00e7\u00e3o' if nivel == 'mestrado' else 'tese'
    if tipo == 'defesa':
        return [(
            "Aos " + d['dia'] + " dias do m\u00eas de " + d['mes'] + ", do ano de dois mil e vinte e " + d['ano'] + ", "
            "\u00e0s " + d['hora'] + ", " + d['modalidade'] + ", realizou-se a Defesa do(a) discente "
            + d['discente'] + ", como parte das exig\u00eancias para obten\u00e7\u00e3o do t\u00edtulo de " + niv + ", com a "
            + trab + " intitulada: \u201c" + d['titulo'] + "\u201d do Curso de P\u00f3s-gradua\u00e7\u00e3o Stricto Sensu em "
            "Ci\u00eancias Ambientais, perante a banca examinadora, composta pelos(as) examinadores(as) "
            "listados(as) abaixo, onde a sess\u00e3o foi aberta pelo(a) presidente "
            + d['or_trat'] + " " + d['or_nome'] + " e, ap\u00f3s apresenta\u00e7\u00e3o, o(a) discente foi arguido(a) "
            "pela Banca Examinadora. Em sess\u00e3o secreta foi decidido o resultado da defesa, sendo "
            "o(a) discente considerado(a) " + d['resultado'] + ". Encerrada a sess\u00e3o secreta, o Presidente "
            "informou o resultado. Nada mais havendo a tratar, eu, Presidente da banca, lavrei a "
            "presente ata que assino juntamente com os membros da Banca Examinadora. Para a obten\u00e7\u00e3o "
            "do t\u00edtulo ainda \u00e9 necess\u00e1rio o cumprimento das exig\u00eancias contidas no Regimento do "
            "Programa de P\u00f3s-gradua\u00e7\u00e3o Stricto Sensu em Ci\u00eancias Ambientais - Resolu\u00e7\u00e3o n.\u00ba " + d['resolucao'] + "."
        )]
    else:
        return [
            "Aos " + d['dia'] + " dias do m\u00eas de " + d['mes'] + " do ano de dois mil e vinte e " + d['ano'] + ", "
            "\u00e0s " + d['hora'] + ", " + d['modalidade'] + " realizou-se o Exame de Qualifica\u00e7\u00e3o do(a) discente "
            + d['discente'] + ", como parte das exig\u00eancias para obten\u00e7\u00e3o do t\u00edtulo de " + niv + ", com a "
            "vers\u00e3o preliminar da " + trab + " intitulada: \u201c" + d['titulo'] + "\u201d do Curso de "
            "P\u00f3s-gradua\u00e7\u00e3o Stricto Sensu em Ci\u00eancias Ambientais, perante a banca examinadora, "
            "composta pelos professores abaixo.",
            '',
            "Ap\u00f3s apresenta\u00e7\u00e3o e argui\u00e7\u00e3o, a banca examinadora conclui pela APROVA\u00c7\u00c3O do(a) discente com conceito final do Exame de Qualifica\u00e7\u00e3o: " + d['conceito'],
            '',
            'I. \u201cA\u201d \u2013 aprova\u00e7\u00e3o, considerando pequenas reformula\u00e7\u00f5es sugeridas pela banca;',
            'II. \u201cB\u201d \u2013 aprova\u00e7\u00e3o, com reformula\u00e7\u00f5es estruturais de acordo com as sugest\u00f5es da Banca;',
            'III. \u201cC\u201d \u2013 aprova\u00e7\u00e3o, com reformula\u00e7\u00f5es estruturais e metodol\u00f3gicas apresentadas pela Banca;',
            'IV. \u201cD\u201d \u2013 Reprova\u00e7\u00e3o e recomenda\u00e7\u00e3o de ampla reformula\u00e7\u00e3o para novo Exame de Qualifica\u00e7\u00e3o.',
            '',
            'Em seguida a presidente da banca agradeceu a participa\u00e7\u00e3o dos presentes e deu por encerrada a presente reuni\u00e3o, a tudo presenciei, lavrei e assinei a presente ata.',
        ]

def parse_membros(form, prefix):
    membros = [{'trat': form.get(prefix+'_or_trat','Prof. Dr.'),
                'nome': form.get(prefix+'_or_nome',''),
                'cpf':  form.get(prefix+'_or_cpf',''),
                'inst': form.get(prefix+'_or_inst','UNEMAT')}]
    for i in range(1, 20):
        nome = form.get(prefix+'_m'+str(i)+'_nome','').strip()
        if not nome: break
        membros.append({'trat': form.get(prefix+'_m'+str(i)+'_trat','Prof. Dr.'),
                        'nome': nome,
                        'cpf':  form.get(prefix+'_m'+str(i)+'_cpf',''),
                        'inst': form.get(prefix+'_m'+str(i)+'_inst','UNEMAT')})
    return membros

def gerar_pdf(titulo_pt, linhas, membros):
    buf = io.BytesIO()
    W_page, _ = A4
    ML,MR,MT,MB = 25*mm,20*mm,18*mm,20*mm
    W = W_page - ML - MR
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    def s(**kw): return ParagraphStyle('s', **kw)
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
                  Paragraph('Programa de P\u00f3s-Gradua\u00e7\u00e3o Stricto Sensu em Ci\u00eancias Ambientais',sI),
                  Paragraph('Campus de C\u00e1ceres \u2013 Alta Floresta \u2013 Nova Xavantina',sI)],
                 RLImage(LOGO2,18*mm,20*mm)]],
                colWidths=[22*mm, W-44*mm, 22*mm])
    ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story += [ht, HRFlowable(width=W,thickness=0.5,color=colors.Color(.7,.7,.7),spaceAfter=4),
              Paragraph(titulo_pt, sT)]
    for l in linhas:
        if l == '': story.append(Spacer(1,5))
        elif l.startswith('I.') or l.startswith('II.') or l.startswith('III.') or l.startswith('IV.'): story.append(Paragraph(l,sL))
        else: story.append(Paragraph(l,sB))
    story.append(Spacer(1,14))
    SH = 42*mm
    def sc(m):
        return [Spacer(1,SH-20*mm), Paragraph('_'*44,sSN),
                Paragraph(m['trat']+' '+m['nome'],sSN),
                Paragraph(m['inst'],sSI),
                Paragraph('CPF: '+m['cpf'],sSC) if m.get('cpf') else Spacer(1,4)]
    rows = []
    for i in range(0,len(membros),2):
        a = membros[i]
        b = membros[i+1] if i+1 < len(membros) else None
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
              Paragraph('Concep\u00e7\u00e3o: Prof. Dr. Ernandes Sobreira Oliveira Junior \u00b7 Bi\u00f3logo \u00b7 UNEMAT',sFT)]
    doc.build(story)
    buf.seek(0)
    return buf

def gerar_docx(titulo_pt, linhas, membros):
    buf = io.BytesIO()
    doc = DocxDocument()
    sec = doc.sections[0]
    sec.page_width=Mm(210); sec.page_height=Mm(297)
    sec.left_margin=Mm(25); sec.right_margin=Mm(20)
    sec.top_margin=Mm(18);  sec.bottom_margin=Mm(20)
    def p(txt, bold=False, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, font='Arial', sa=4, sb=0, fi=None, italic=False, rgb=None):
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
    p('Programa de P\u00f3s-Gradua\u00e7\u00e3o Stricto Sensu em Ci\u00eancias Ambientais', size=9)
    p('Campus de C\u00e1ceres \u2013 Alta Floresta \u2013 Nova Xavantina', size=9, sa=6)
    sep = doc.add_paragraph(); sep.paragraph_format.space_after=Pt(4)
    pPr = sep._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bot = OxmlElement('w:bottom')
    bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'4')
    bot.set(qn('w:space'),'1');    bot.set(qn('w:color'),'AAAAAA')
    pBdr.append(bot); pPr.append(pBdr)
    p(titulo_pt, bold=True, size=13, font='Times New Roman', sb=8, sa=12)
    for l in linhas:
        if l == '':
            doc.add_paragraph().paragraph_format.space_after=Pt(3)
            continue
        isit = l.startswith('I.') or l.startswith('II.') or l.startswith('III.') or l.startswith('IV.')
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
                b=OxmlElement('w:'+side)
                b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'6')
                b.set(qn('w:space'),'0');    b.set(qn('w:color'),'AAAAAA')
                tcPr.append(b)
    for idx, m in enumerate(membros):
        cell = tbl.cell(idx//2, idx%2)
        for para in cell.paragraphs:
            for r in para.runs: r.text=''
        def cp(txt='', bold=False, size=9, rgb=None, _cell=cell):
            para = _cell.add_paragraph()
            para.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if txt:
                r=para.add_run(txt); r.bold=bold
                r.font.size=Pt(size); r.font.name='Times New Roman'
                if rgb: r.font.color.rgb=RGBColor(*rgb)
        for _ in range(3): cp()
        cp('_'*42)
        cp(m['trat']+' '+m['nome'], bold=True)
        cp(m['inst'], rgb=(80,80,80))
        if m.get('cpf'): cp('CPF: '+m['cpf'], size=8, rgb=(100,100,100))
    doc.add_paragraph().paragraph_format.space_after=Pt(4)
    p('Concep\u00e7\u00e3o: Prof. Dr. Ernandes Sobreira Oliveira Junior \u00b7 Bi\u00f3logo \u00b7 UNEMAT',
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
              'defesa':{'mestrado':'dm','doutorado':'dd'}}[tipo][nivel]
    d = {'dia':form.get('dia',''), 'mes':form.get('mes',''), 'ano':form.get('ano',''),
         'hora':form.get('hora',''), 'modalidade':form.get('modalidade','de forma virtual'),
         'discente':form.get('discente',''), 'titulo':form.get('titulo',''),
         'or_trat':form.get(prefix+'_or_trat',''), 'or_nome':form.get(prefix+'_or_nome',''),
         'resultado':form.get('resultado','APROVADO(A)'),
         'conceito':form.get('conceito','A'),
         'resolucao':form.get('resolucao','')}
    membros   = parse_membros(form, prefix)
    titulo_pt = TITLES_PT[(tipo, nivel)]
    titulo_fn = TITLES[(tipo, nivel)]
    linhas    = get_linhas(tipo, nivel, d)
    nome      = titulo_fn.replace(' ','_')
    if fmt == 'pdf':
        return send_file(gerar_pdf(titulo_pt, linhas, membros),
                         mimetype='application/pdf',
                         as_attachment=True, download_name=nome+'.pdf')
    else:
        return send_file(gerar_docx(titulo_pt, linhas, membros),
                         mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         as_attachment=True, download_name=nome+'.docx')

@app.route('/')
def index():
    meses = ['janeiro','fevereiro','marco','abril','maio','junho',
             'julho','agosto','setembro','outubro','novembro','dezembro']
    meses_pt = ['Janeiro','Fevereiro','Mar\u00e7o','Abril','Maio','Junho',
                'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    mes_opts = ''.join('<option value="'+meses[i]+'">'+meses_pt[i]+'</option>' for i in range(12))

    def trat_opts(name):
        return ('<select name="'+name+'">'
                '<option>Prof. Dr.</option><option>Profa. Dra.</option>'
                '<option>Prof. Me.</option><option>Profa. Me.</option>'
                '</select>')

    def or_block(pr):
        return (
            '<div class="mb"><div class="mbl"><span class="badge">P</span> Orientador(a) / Presidente</div>'
            '<div class="row r3">'
            '<div class="f"><label>Tratamento</label>'+trat_opts(pr+'_or_trat')+'</div>'
            '<div class="f"><label>Nome *</label><input type="text" name="'+pr+'_or_nome" required placeholder="Nome completo"></div>'
            '<div class="f"><label>CPF</label><input type="text" name="'+pr+'_or_cpf" placeholder="000.000.000-00"></div>'
            '</div><div class="row r2">'
            '<div class="f"><label>Institui\u00e7\u00e3o</label><input type="text" name="'+pr+'_or_inst" value="UNEMAT"></div>'
            '</div></div>')

    def mb_block(pr, n):
        ns = str(n)
        return (
            '<div class="mb"><div class="mbl"><span class="badge">'+str(n+1)+'</span> Membro '+ns+'</div>'
            '<div class="row r3">'
            '<div class="f"><label>Tratamento</label>'+trat_opts(pr+'_m'+ns+'_trat')+'</div>'
            '<div class="f"><label>Nome</label><input type="text" name="'+pr+'_m'+ns+'_nome" placeholder="Nome completo"></div>'
            '<div class="f"><label>CPF</label><input type="text" name="'+pr+'_m'+ns+'_cpf" placeholder="000.000.000-00"></div>'
            '</div><div class="row r2">'
            '<div class="f"><label>Institui\u00e7\u00e3o</label><input type="text" name="'+pr+'_m'+ns+'_inst" value="UNEMAT"></div>'
            '</div></div>')

    def make_form(pr, trab, n_mb, res_default, is_qual):
        members = ''.join(mb_block(pr, i+1) for i in range(n_mb))
        if is_qual:
            res_field = ('<div class="f"><label>Conceito Final *</label>'
                '<select name="conceito">'
                '<option value="A">A \u2013 Aprova\u00e7\u00e3o com pequenas reformula\u00e7\u00f5es</option>'
                '<option value="B">B \u2013 Aprova\u00e7\u00e3o com reformula\u00e7\u00f5es estruturais</option>'
                '<option value="C">C \u2013 Aprova\u00e7\u00e3o com reformula\u00e7\u00f5es estruturais e metodol\u00f3gicas</option>'
                '<option value="D">D \u2013 Reprova\u00e7\u00e3o</option>'
                '</select></div>')
        else:
            res_field = ('<div class="f"><label>Resultado *</label>'
                '<select name="resultado">'
                '<option value="APROVADO(A)">APROVADO(A)</option>'
                '<option value="REPROVADO(A)">REPROVADO(A)</option>'
                '</select></div>')
        return (
            '<div class="sec">Data e Hora</div>'
            '<div class="row r3">'
            '<div class="f"><label>Dia (por extenso) *</label><input type="text" name="dia" required placeholder="vinte e cinco"></div>'
            '<div class="f"><label>M\u00eas *</label><select name="mes">'+mes_opts+'</select></div>'
            '<div class="f"><label>Ano (ex: cinco) *</label><input type="text" name="ano" required placeholder="cinco"></div>'
            '</div><div class="row r2">'
            '<div class="f"><label>Hor\u00e1rio (por extenso) *</label><input type="text" name="hora" required placeholder="quatorze horas"></div>'
            '<div class="f"><label>Modalidade</label><select name="modalidade">'
            '<option value="de forma virtual">Virtual (online)</option>'
            '<option value="presencialmente">Presencial</option>'
            '<option value="em formato h\u00edbrido">H\u00edbrido</option>'
            '</select></div></div>'
            '<div class="sec">Discente</div>'
            '<div class="f"><label>Nome completo *</label><input type="text" name="discente" required placeholder="Nome completo do(a) discente"></div>'
            '<div class="f"><label>T\u00edtulo da '+trab+' *</label><input type="text" name="titulo" required placeholder="T\u00edtulo completo"></div>'
            '<div class="sec">Orientador(a) \u2013 Presidente da Banca</div>'
            + or_block(pr) +
            '<div class="sec">Membros da Banca</div>'
            '<div id="members-'+pr+'">'+members+'</div>'
            '<button type="button" class="btn-add" onclick="addMember(\''+pr+'\')">+ Adicionar membro</button>'
            '<div class="sec">Resultado</div>'
            '<div class="row r2">'
            + res_field +
            '<div class="f"><label>Resolu\u00e7\u00e3o</label><input type="text" name="resolucao" value="'+res_default+'"></div>'
            '</div>'
            '<div class="btn-row">'
            '<button type="submit" name="fmt" value="pdf" class="btn btn-green">Baixar PDF</button>'
            '<button type="submit" name="fmt" value="docx" class="btn btn-gold">Baixar Word</button>'
            '</div>')

    tabs = [
        ('qm','qualificacao','mestrado','disserta\u00e7\u00e3o',2,'10/2026-CONSUNI',True,'Qualif. Mestrado'),
        ('qd','qualificacao','doutorado','tese',3,'046/2024-CONSUNI',True,'Qualif. Doutorado'),
        ('dm','defesa','mestrado','disserta\u00e7\u00e3o',3,'10/2026-CONSUNI',False,'Defesa Mestrado'),
        ('dd','defesa','doutorado','tese',4,'046/2024-CONSUNI',False,'Defesa Doutorado'),
    ]

    btn_html = ''
    forms_html = ''
    for i, tab in enumerate(tabs):
        pr,tipo,nivel,trab,n_mb,res_def,is_qual,label = tab
        active = ' active' if i == 0 else ''
        display = '' if i == 0 else ' style="display:none"'
        btn_html += '<button id="btn-'+pr+'" class="tab-btn'+active+'" onclick="setTab(\''+pr+'\')">'+label+'</button>'
        form_content = make_form(pr, trab, n_mb, res_def, is_qual)
        forms_html += ('<div id="tab-'+pr+'" class="tab-pane"'+display+'>'
                       '<form action="/gerar" method="POST">'
                       '<input type="hidden" name="tipo" value="'+tipo+'">'
                       '<input type="hidden" name="nivel" value="'+nivel+'">'
                       + form_content +
                       '</form></div>')

    return ('''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gerador de Atas \u2013 PPGCA/UNEMAT</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"DM Sans",sans-serif;background:linear-gradient(135deg,#0e3d26,#1a5c3a 50%,#1d6640);min-height:100vh}
.hero{padding:28px 20px 0;text-align:center}
.hero-logos{display:flex;justify-content:center;align-items:center;gap:20px;margin-bottom:14px;flex-wrap:wrap}
.hero-logos img{height:66px;object-fit:contain;filter:drop-shadow(0 2px 8px rgba(0,0,0,.4))}
.hero h1{font-family:"Playfair Display",serif;font-size:clamp(1.3rem,4vw,2.1rem);color:#fff;margin-bottom:5px}
.hero p{font-size:.86rem;color:rgba(255,255,255,.75);margin-bottom:3px}
.credit{font-size:.75rem;color:#f0d98a;margin-bottom:20px;font-style:italic}
.tab-bar{display:flex;justify-content:center;gap:4px;flex-wrap:wrap;padding:0 12px}
.tab-btn{background:rgba(255,255,255,.12);color:rgba(255,255,255,.82);border:1.5px solid rgba(255,255,255,.18);border-bottom:none;border-radius:10px 10px 0 0;padding:9px 14px;font-family:"DM Sans",sans-serif;font-size:.81rem;font-weight:500;cursor:pointer;transition:.2s;white-space:nowrap}
.tab-btn:hover{background:rgba(255,255,255,.2);color:#fff}
.tab-btn.active{background:#fff;color:#1a5c3a;font-weight:700;border-color:#fff}
.card{background:#fff;border-radius:0 0 12px 12px;box-shadow:0 8px 40px rgba(26,92,58,.18);max-width:820px;margin:0 auto;padding:26px 30px 30px;position:relative}
.card::before{content:"";position:absolute;top:0;left:30px;right:30px;height:3px;background:linear-gradient(90deg,#1a5c3a,#c8a84b,#1a5c3a);border-radius:0 0 4px 4px}
.wrap{max-width:820px;margin:0 auto;padding:0 12px 48px}
.sec{font-family:"Playfair Display",serif;font-size:.95rem;color:#1a5c3a;margin:18px 0 9px;padding-bottom:5px;border-bottom:1.5px solid #e8f4ee;display:flex;align-items:center;gap:7px}
.sec::before{content:"";width:4px;height:14px;background:#c8a84b;border-radius:2px;flex-shrink:0}
.row{display:grid;gap:11px}
.r2{grid-template-columns:1fr 1fr}
.r3{grid-template-columns:1fr 1fr 1fr}
.f{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}
.f label{font-size:.7rem;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.06em}
.f input,.f select{border:1.5px solid #d1d5db;border-radius:8px;padding:10px 12px;font-family:"DM Sans",sans-serif;font-size:.88rem;color:#111;background:#f9fafb;outline:none;width:100%;transition:.15s}
.f input:focus,.f select:focus{border-color:#1a5c3a;box-shadow:0 0 0 3px rgba(26,92,58,.1);background:#fff}
.mb{background:#f9fafb;border:1.5px solid #eee;border-radius:10px;padding:12px 14px 4px;margin-bottom:9px}
.mbl{font-size:.7rem;font-weight:700;color:#1a5c3a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;display:flex;align-items:center;gap:5px}
.badge{background:#1a5c3a;color:#fff;font-size:.62rem;font-weight:700;padding:2px 7px;border-radius:20px}
.btn-add{background:#fff;color:#1a5c3a;border:1.5px solid #1a5c3a;border-radius:8px;padding:7px 13px;font-family:"DM Sans",sans-serif;font-size:.79rem;font-weight:600;cursor:pointer;margin:3px 0 4px;transition:.15s}
.btn-add:hover{background:#e8f4ee}
.btn-row{display:flex;gap:8px;margin-top:22px;flex-wrap:wrap}
.btn{padding:13px 26px;border-radius:10px;font-family:"DM Sans",sans-serif;font-size:.93rem;font-weight:700;cursor:pointer;border:none;transition:.18s}
.btn-green{background:linear-gradient(135deg,#1a5c3a,#2d7a52);color:#fff;box-shadow:0 4px 16px rgba(26,92,58,.25)}
.btn-green:hover{transform:translateY(-1px)}
.btn-gold{background:linear-gradient(135deg,#c8a84b,#b8943b);color:#fff;box-shadow:0 4px 16px rgba(200,168,75,.3)}
.btn-gold:hover{transform:translateY(-1px)}
@media(max-width:580px){.card{padding:15px 12px}.r2,.r3{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="hero">
  <div class="hero-logos">
    <img src="/logo1" alt="MT"><img src="/logo2" alt="UNEMAT"><img src="/logo3" alt="CA">
  </div>
  <h1>Gerador de Atas Acad\u00eamicas</h1>
  <p>Programa de P\u00f3s-Gradua\u00e7\u00e3o Stricto Sensu em Ci\u00eancias Ambientais \u2013 UNEMAT</p>
  <p class="credit">Concep\u00e7\u00e3o: Prof. Dr. Ernandes Sobreira Oliveira Junior \u00b7 Bi\u00f3logo \u00b7 UNEMAT | Moldado com IA</p>
</div>
<div class="wrap">
  <div class="tab-bar">''' + btn_html + '''</div>
  <div class="card">''' + forms_html + '''</div>
</div>
<script>
function setTab(id) {
  var panes = document.querySelectorAll(".tab-pane");
  for (var i=0; i<panes.length; i++) panes[i].style.display = "none";
  var btns = document.querySelectorAll(".tab-btn");
  for (var i=0; i<btns.length; i++) btns[i].classList.remove("active");
  document.getElementById("tab-" + id).style.display = "";
  document.getElementById("btn-" + id).classList.add("active");
}
function addMember(pr) {
  var container = document.getElementById("members-" + pr);
  var n = container.querySelectorAll(".mb").length + 1;
  var div = document.createElement("div");
  div.className = "mb";
  div.innerHTML = '<div class="mbl"><span class="badge">'+(n+1)+'</span> Membro '+n
    +' <button type="button" onclick="this.closest(\\'.mb\\').remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:#bbb;font-size:1rem">x</button></div>'
    +'<div class="row r3">'
    +'<div class="f"><label>Tratamento</label><select name="'+pr+'_m'+n+'_trat"><option>Prof. Dr.</option><option>Profa. Dra.</option><option>Prof. Me.</option><option>Profa. Me.</option></select></div>'
    +'<div class="f"><label>Nome</label><input type="text" name="'+pr+'_m'+n+'_nome" placeholder="Nome completo"></div>'
    +'<div class="f"><label>CPF</label><input type="text" name="'+pr+'_m'+n+'_cpf" placeholder="000.000.000-00"></div>'
    +'</div><div class="row r2">'
    +'<div class="f"><label>Institui\u00e7\u00e3o</label><input type="text" name="'+pr+'_m'+n+'_inst" value="UNEMAT"></div>'
    +'</div>';
  container.appendChild(div);
}
</script>
</body>
</html>''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
