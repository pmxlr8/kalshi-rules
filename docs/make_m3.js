// Milestone 3 report generator. Numbers come from results/m3/numbers.json
// (src/m3_report.py, then src/m3_numbers.py). Build: cd docs && npm install docx@9.5.1 && node make_m3.js
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, AlignmentType,
} = require('docx');

const SZ = Number(process.env.SZ || 19);
const MARGIN = Number(process.env.MARGIN || 1080);
const OUT = process.env.OUT || 'Milestone3_Progress_Report.docx';
const N = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'results', 'm3', 'numbers.json'), 'utf8'));
const TEXT = require('./m3_text.js')(N);

function runs(text, size = SZ) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map(p => p.startsWith('**')
    ? new TextRun({ text: p.slice(2, -2), bold: true, size, font: 'Arial' })
    : new TextRun({ text: p, size, font: 'Arial' }));
}
const P = (t, after = 50) => new Paragraph({ children: runs(t), spacing: { before: 0, after, line: 235 } });
const H = t => new Paragraph({ children: [new TextRun({ text: t, bold: true, size: SZ + 3, font: 'Arial' })], spacing: { before: 90, after: 25, line: 235 }, keepNext: true });
const B = t => new Paragraph({ children: runs(t), numbering: { reference: 'b', level: 0 }, spacing: { before: 0, after: 15, line: 235 } });

const border = { style: BorderStyle.SINGLE, size: 4, color: '999999' };
const borders = { top: border, bottom: border, left: border, right: border };
function table(rows, cols, size = SZ - 2) {
  const total = cols.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: cols,
    rows: rows.map((r, ri) => new TableRow({
      children: r.map((t, i) => new TableCell({
        borders, width: { size: cols[i], type: WidthType.DXA },
        shading: ri === 0 ? { fill: 'E8E8E8', type: ShadingType.CLEAR, color: 'auto' } : undefined,
        margins: { top: 15, bottom: 15, left: 60, right: 60 },
        children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
          children: runs(ri === 0 ? `**${t}**` : String(t), size), spacing: { before: 0, after: 0, line: 220 } })],
      })),
    })),
  });
}

const blocks = TEXT.blocks.map(b => {
  if (b.h) return H(b.h);
  if (b.p) return P(b.p, b.after);
  if (b.b) return B(b.b);
  if (b.table) return table(b.table, b.cols, b.size);
  throw new Error('bad block ' + JSON.stringify(b));
});

const doc = new Document({
  styles: { default: { document: { run: { font: 'Arial', size: SZ } } } },
  numbering: { config: [{ reference: 'b', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 280, hanging: 180 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } }, children: blocks }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(path.join(__dirname, OUT), b); console.log('wrote', OUT); });
