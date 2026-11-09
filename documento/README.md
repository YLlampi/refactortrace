# Documento de tesis

`propuesta.md` contiene el texto editable y `Tesis_RefactorTrace.tex` es la versión LaTeX generada con la clase `unsa` de la plantilla original. El diagrama está en `pipeline.tex`. Para regenerar el archivo TeX tras editar el Markdown:

```powershell
python documento/generar_tex.py
```

Compile `documento/Tesis_RefactorTrace.tex` con una instalación LaTeX compatible o Tectonic. La plantilla, los estilos y el logotipo proceden de los archivos facilitados para el documento original; en la copia de la clase se eliminó una carga duplicada de codificación incompatible con LaTeX actual. La investigación se presenta como propuesta y no incluye resultados finales no obtenidos.
