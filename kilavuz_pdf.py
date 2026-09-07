#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  KILAVUZ.md  →  PDF
#
#  YAZI TİPİ NEDEN DEJAVU:
#    ReportLab'in yerleşik Helvetica'si WinAnsi (CP1252) kodlamasi
#    kullanir; `ş ğ ı İ` harfleri BU KUMEDE YOKTUR ve siyah kutu
#    olarak basilir. DejaVu Sans tam kapsama sahip.
# ══════════════════════════════════════════════════════════════════════
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether,
                                ListFlowable, ListItem, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

KOK = Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DJ', KOK / 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DJ-B', KOK / 'DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DJ-I', KOK / 'DejaVuSans-Oblique.ttf'))
pdfmetrics.registerFont(TTFont('DJM', KOK / 'DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily('DJ', normal='DJ', bold='DJ-B', italic='DJ-I')

YESIL = colors.HexColor('#1F4E3D')
KEHRIBAR = colors.HexColor('#8a6d1f')
SOLUK = colors.HexColor('#6b6b6b')
CIZGI = colors.HexColor('#d8d8d0')
ZEMIN = colors.HexColor('#f6f6f1')

ss = getSampleStyleSheet()


def st(ad, **kw):
    t = dict(fontName='DJ', fontSize=9.5, leading=14.5, textColor=colors.HexColor('#1a1a1a'))
    t.update(kw)
    return ParagraphStyle(ad, parent=ss['Normal'], **t)


S = {
    'h1': st('h1', fontName='DJ-B', fontSize=19, leading=24, textColor=YESIL,
             spaceBefore=0, spaceAfter=10),
    'h2': st('h2', fontName='DJ-B', fontSize=14, leading=19, textColor=YESIL,
             spaceBefore=16, spaceAfter=7),
    'h3': st('h3', fontName='DJ-B', fontSize=11, leading=15,
             textColor=colors.HexColor('#2a2a2a'), spaceBefore=11, spaceAfter=4),
    'p': st('p', spaceAfter=6, alignment=TA_LEFT),
    'li': st('li', spaceAfter=2.5, leading=14),
    'kod': st('kod', fontName='DJM', fontSize=8.3, leading=12.2,
              textColor=colors.HexColor('#22322c'),
              backColor=ZEMIN, borderPadding=(7, 8, 7, 8), spaceAfter=8),
    'alinti': st('alinti', fontSize=9.3, leading=14, textColor=colors.HexColor('#5a4a1a'),
                 backColor=colors.HexColor('#fdf6e3'), borderPadding=(7, 9, 7, 9),
                 leftIndent=2, spaceAfter=8),
    'tb': st('tb', fontSize=8.6, leading=12),
    'tbb': st('tbb', fontName='DJ-B', fontSize=8.6, leading=12, textColor=colors.white),
    'kapak_alt': st('kapak_alt', fontSize=11, leading=17, textColor=SOLUK),
    'dip': st('dip', fontSize=7.6, textColor=SOLUK),
}


def satir_ici(t):
    """Markdown satır içi biçimlendirmeyi ReportLab etiketlerine çevirir."""
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'`([^`]+)`',
               r'<font face="DJM" size="8.4" color="#22322c">\1</font>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)      # bağlantı → düz metin
    return t


def tablo_yap(satirlar):
    ham = [[h.strip() for h in s.strip().strip('|').split('|')] for s in satirlar]
    ham = [r for r in ham if not all(re.fullmatch(r':?-{2,}:?', c or '') for c in r)]
    if not ham:
        return None
    veri = [[Paragraph(satir_ici(c), S['tbb'] if i == 0 else S['tb']) for c in r]
            for i, r in enumerate(ham)]
    sut = len(ham[0])
    genis = (170 * mm) / sut
    t = Table(veri, colWidths=[genis] * sut, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), YESIL),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, CIZGI),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ZEMIN]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


def cevir(md):
    ak = []
    L = md.split('\n')
    i = 0
    ilk_h1 = True
    while i < len(L):
        s = L[i]

        # ── kod bloğu ──
        if s.startswith('```'):
            i += 1
            blok = []
            while i < len(L) and not L[i].startswith('```'):
                blok.append(L[i])
                i += 1
            i += 1
            metin = '\n'.join(blok).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            ak.append(Paragraph(metin.replace('\n', '<br/>'), S['kod']))
            continue

        # ── tablo ──
        if s.strip().startswith('|') and i + 1 < len(L) and set(L[i + 1].strip()) <= set('|-: '):
            blok = []
            while i < len(L) and L[i].strip().startswith('|'):
                blok.append(L[i])
                i += 1
            t = tablo_yap(blok)
            if t:
                ak.append(Spacer(1, 3))
                ak.append(t)
                ak.append(Spacer(1, 9))
            continue

        # ── ayraç ──
        if re.fullmatch(r'-{3,}', s.strip()):
            ak.append(Spacer(1, 5))
            i += 1
            continue

        # ── başlıklar ──
        if s.startswith('### '):
            ak.append(Paragraph(satir_ici(s[4:]), S['h3']))
            i += 1
            continue
        if s.startswith('## '):
            ak.append(Paragraph(satir_ici(re.sub(r'^\d+\.\s*', '', s[3:])), S['h2']))
            i += 1
            continue
        if s.startswith('# '):
            if not ilk_h1:
                ak.append(PageBreak())
            ilk_h1 = False
            ak.append(Paragraph(satir_ici(s[2:]), S['h1']))
            i += 1
            continue

        # ── alıntı (uyarı kutusu) ──
        if s.startswith('> '):
            blok = []
            while i < len(L) and L[i].startswith('>'):
                blok.append(L[i].lstrip('>').strip())
                i += 1
            ak.append(Paragraph(satir_ici(' '.join(blok)), S['alinti']))
            continue

        # ── liste ──
        # DEVAM SATIRLARI BIRLESTIRILIR: kaynak .md sabit sarilmis,
        # her satir ayri oge olsaydi cumleler ortadan bolunurdu.
        if re.match(r'^\s*(-|\d+\.)\s+', s):
            ogeler = []
            sirali = bool(re.match(r'^\s*\d+\.', s))
            while i < len(L) and re.match(r'^\s*(-|\d+\.)\s+', L[i]):
                metin = re.sub(r'^\s*(-|\d+\.)\s+', '', L[i])
                i += 1
                while (i < len(L) and L[i].strip()
                       and not re.match(r'^\s*(-|\d+\.)\s+', L[i])
                       and not L[i].startswith(('#', '>', '|', '```'))
                       and not re.fullmatch(r'-{3,}', L[i].strip())):
                    metin += ' ' + L[i].strip()
                    i += 1
                ogeler.append(ListItem(Paragraph(satir_ici(metin), S['li']),
                                       leftIndent=13))
            ak.append(ListFlowable(ogeler, bulletType='1' if sirali else 'bullet',
                                   bulletFontName='DJ', bulletFontSize=8,
                                   leftIndent=13, bulletOffsetY=-0.6))
            ak.append(Spacer(1, 5))
            continue

        # ── boş / paragraf ──
        if not s.strip():
            i += 1
            continue
        # PARAGRAF: bos satira kadar TUM satirlari birlestir.
        # Ilk surumde her kaynak satiri ayri paragraf oluyordu ve
        # cumleler ortadan bolunuyordu.
        parca = [s.strip()]
        i += 1
        while (i < len(L) and L[i].strip()
               and not L[i].startswith(('#', '>', '|', '```'))
               and not re.match(r'^\s*(-|\d+\.)\s+', L[i])
               and not re.fullmatch(r'-{3,}', L[i].strip())):
            parca.append(L[i].strip())
            i += 1
        ak.append(Paragraph(satir_ici(' '.join(parca)), S['p']))
    return ak


def sayfa_suslemesi(kanvas, belge):
    kanvas.saveState()
    if belge.page > 1:
        kanvas.setFont('DJ', 7.6)
        kanvas.setFillColor(SOLUK)
        kanvas.drawString(20 * mm, 12 * mm, 'Milestone ERP — Kullanım Kılavuzu')
        kanvas.drawRightString(190 * mm, 12 * mm, str(belge.page))
        kanvas.setStrokeColor(CIZGI)
        kanvas.setLineWidth(0.4)
        kanvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    kanvas.restoreState()


def kapak():
    p = []
    p.append(Spacer(1, 62 * mm))
    p.append(Paragraph('MILESTONE ERP',
                       st('k1', fontName='DJ-B', fontSize=30, leading=36, textColor=YESIL)))
    p.append(Spacer(1, 5))
    p.append(Paragraph('Kullanım Kılavuzu',
                       st('k2', fontName='DJ', fontSize=17, leading=23, textColor=colors.HexColor('#2a2a2a'))))
    p.append(Spacer(1, 13))
    cz = Table([['']], colWidths=[52 * mm], rowHeights=[2])
    cz.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), KEHRIBAR)]))
    cz.hAlign = 'LEFT'
    p.append(cz)
    p.append(Spacer(1, 17))
    p.append(Paragraph(
        'Cari hesaplar · Stok · Maliyet · Satış hattı · Tahsilat<br/>'
        'Çek ve senet · Belgeler · Nakit akışı', S['kapak_alt']))
    p.append(Spacer(1, 88 * mm))
    p.append(Paragraph('Milestone Mermer San. ve Tic. Ltd. Şti.', S['dip']))
    p.append(PageBreak())
    return p


def uret(md_yolu, pdf_yolu):
    md = Path(md_yolu).read_text(encoding='utf-8')
    # Kapak basligi ve icindekiler PDF'te ayri uretiliyor
    md = re.sub(r'^# Milestone ERP — Kullanım Kılavuzu\n', '', md)
    md = re.sub(r'## İçindekiler.*?(?=\n---)', '', md, flags=re.S)

    belge = BaseDocTemplate(
        str(pdf_yolu), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title='Milestone ERP — Kullanım Kılavuzu',
        author='Milestone Mermer')
    cerceve = Frame(belge.leftMargin, belge.bottomMargin,
                    belge.width, belge.height, id='ana')
    belge.addPageTemplates([PageTemplate(id='std', frames=[cerceve],
                                         onPage=sayfa_suslemesi)])
    belge.build(kapak() + cevir(md))
    return pdf_yolu


if __name__ == '__main__':
    import sys
    cikti = uret(sys.argv[1], sys.argv[2])
    print(f'  ✓ {cikti}')
