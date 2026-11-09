"""Genera la propuesta con la clase UNSA de la plantilla original."""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent


def escapar(texto):
    cambios = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
               '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}',
               '^': r'\textasciicircum{}', '—': '---', '–': '--'}
    return ''.join(cambios.get(c, c) for c in texto)


def inline(texto):
    partes = re.split(r'(\[[^\]]+\]\(https?://[^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*|https?://\S+)', texto)
    salida = []
    for parte in partes:
        if parte.startswith('[') and '](http' in parte:
            etiqueta, url = parte[1:-1].split('](', 1)
            salida.append(r'\href{' + url + '}{' + escapar(etiqueta) + '}')
        elif parte.startswith('**') and parte.endswith('**'):
            salida.append(r'\textbf{' + escapar(parte[2:-2]) + '}')
        elif parte.startswith('*') and parte.endswith('*'):
            salida.append(r'\emph{' + escapar(parte[1:-1]) + '}')
        elif parte.startswith(('http://', 'https://')):
            url = parte.rstrip('.,;:')
            salida.append(r'\url{' + url + '}' + escapar(parte[len(url):]))
        else:
            salida.append(re.sub(r'\[([1-9])\]', lambda m: r'\cite{ref' + m.group(1) + '}', escapar(parte)))
    return ''.join(salida)


def titulo(texto):
    return re.sub(r'^\d+(?:\.\d+)*\.\s+', '', texto)


def convertir(texto):
    lineas = texto.splitlines()
    salida = []
    i = 1  # El primer título se presenta en la portada.
    primer_capitulo = False
    en_bibliografia = False
    while i < len(lineas):
        linea = lineas[i].strip()
        if not linea:
            salida.append('')
        elif linea.startswith('```mermaid'):
            while i + 1 < len(lineas) and not lineas[i + 1].strip().startswith('```'):
                i += 1
            i += 1
            salida.append(r'La Figura~\ref{fig:pipeline} presenta las etapas del procedimiento propuesto.')
            salida.append(r'\input{pipeline.tex}')
        elif linea.startswith('|'):
            filas = []
            while i < len(lineas) and lineas[i].strip().startswith('|'):
                celdas = [x.strip() for x in lineas[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', c or '-') for c in celdas):
                    filas.append(celdas)
                i += 1
            i -= 1
            n = len(filas[0])
            anchos = [r'0.24\linewidth', r'0.64\linewidth'] if n == 2 else [r'0.20\linewidth', r'0.31\linewidth', r'0.38\linewidth']
            if n not in (2, 3):
                raise ValueError('Tabla no admitida')
            salida.append(r'\begin{longtable}{' + ''.join('p{' + w + '}' for w in anchos) + '}')
            for num, fila in enumerate(filas):
                salida.append(' & '.join(inline(x) for x in fila) + r' \\')
                if num == 0:
                    salida.append(r'\hline')
            salida.append(r'\end{longtable}')
        elif linea.startswith('# '):
            heading = titulo(linea[2:])
            if heading == 'Referencias':
                salida.append(r'\addcontentsline{toc}{chapter}{Bibliografía}' + '\n' + r'\begin{thebibliography}{9}')
                en_bibliografia = True
            else:
                if not primer_capitulo:
                    salida.append(r'\end{abstract}\begin{singlespace}\small\tableofcontents\normalsize\end{singlespace}\end{frontmatter}\pagestyle{fancyplain}')
                    primer_capitulo = True
                salida.append(r'\chapter{' + inline(heading) + '}' + '\n' + r'\hrule\bigskip\vspace*{1cm}')
        elif linea.startswith('### '):
            salida.append(r'\subsection{' + inline(titulo(linea[4:])) + '}')
        elif linea.startswith('## '):
            heading = titulo(linea[3:])
            if not primer_capitulo and heading == 'Resumen':
                salida.append(r'\addcontentsline{toc}{chapter}{Resumen}\begin{abstract}\hrule\bigskip\vspace*{1cm}')
            else:
                if heading == 'Relación con la propuesta':
                    salida.append(r'\Needspace{21\baselineskip}')
                salida.append(r'\section{' + inline(heading) + '}')
        elif en_bibliografia and re.match(r'^\[[1-9]\]\s', linea):
            m = re.match(r'^\[([1-9])\]\s+(.*)$', linea)
            salida.append(r'\bibitem{ref' + m.group(1) + '} ' + inline(m.group(2)))
        elif linea.startswith('- '):
            salida.append(r'\begin{itemize}')
            while i < len(lineas) and lineas[i].strip().startswith('- '):
                salida.append(r'\item ' + inline(lineas[i].strip()[2:]))
                i += 1
            salida.append(r'\end{itemize}')
            i -= 1
        elif re.match(r'^\d+\.\s', linea):
            salida.append(r'\begin{enumerate}')
            while i < len(lineas) and re.match(r'^\d+\.\s', lineas[i].strip()):
                salida.append(r'\item ' + inline(re.sub(r'^\d+\.\s+', '', lineas[i].strip())))
                i += 1
            salida.append(r'\end{enumerate}')
            i -= 1
        else:
            salida.append(inline(linea.lstrip('> ').strip()))
        i += 1
    if en_bibliografia:
        salida.append(r'\end{thebibliography}')
    return '\n'.join(salida)


def main():
    encabezado = r'''\documentclass[11pt,openright,final]{unsa}
\usepackage{longtable,array,needspace}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric}
\hypersetup{hidelinks}
\setlength{\emergencystretch}{3em}
\title{Refactorización de código Python asistida por modelos de lenguaje y guiada por contraejemplos}
\author{Llampi Hancco Yamil Yonder}
\date{\today}
\begin{document}
\hypersetup{pageanchor=false}
\makeFirstCover\makeSecondCover
\hypersetup{pageanchor=true}
\begin{frontmatter}
'''
    cuerpo = convertir((BASE / 'propuesta.md').read_text(encoding='utf-8'))
    (BASE / 'Tesis_RefactorTrace.tex').write_text(encabezado + cuerpo + '\n\\end{document}\n', encoding='utf-8')
    print('Generado:', BASE / 'Tesis_RefactorTrace.tex')


if __name__ == '__main__':
    main()
