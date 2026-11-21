# Verificación de referencias (2026-11-21)

Cada entrada de `documento/bibliography/references.bib` se buscó en la web. Se confirmaron autores, revista, volumen y páginas contra PubMed, el DOI, el sitio de la revista o repositorios institucionales. Para la mayoría solo vi resúmenes y registros, no el texto completo.

## Confirmadas sin cambios
| Clave | Fuente que la confirma |
|---|---|
| Dunlosky2013 | DOI 10.1177/1529100612453266 (PSPI 14(1), 4-58) |
| Roediger2006 | PubMed 16507066 |
| Cepeda2006 | PubMed 16719566, DOI 10.1037/0033-2909.132.3.354 |
| Rohrer2007 | DOI 10.1007/s11251-007-9015-8 (481-498) |
| Chi1994 | DBLP y ASU (Cognitive Science 18, 439-477) |
| Ariga2011 | DOI 10.1016/j.cognition.2010.12.007 |
| Gollwitzer2006 | DOI 10.1016/S0065-2601(06)38002-1 |
| Steel2007 | DOI 10.1037/0033-2909.133.1.65 |
| Curcio2006 | PubMed 16564189, DOI 10.1016/j.smrv.2005.11.001 |
| Hillman2008 | DOI 10.1038/nrn2298 |
| Ward2017 | DOI 10.1086/691462 |
| Ramirez2011 | PubMed 21233387, DOI 10.1126/science.1199427 |
| Vaswani2017 | NeurIPS 30 (2017) |
| Lewis2020 | NeurIPS 33 (2020), arXiv 2005.11401 |
| Ji2023 | ACM Computing Surveys 55(12), 1-38, DOI 10.1145/3571730 |
| Liu1973 | DOI 10.1145/321738.321743 |
| Schaerf1999 | DOI 10.1023/A:1006576209967 |
| Romero2020 | DOI 10.1002/widm.1355 |
| Kuzilek2017 | DOI 10.1038/sdata.2017.171 |
| Elbadrawy2016 | RecSys '16, pp. 183-190 (DOI 10.1145/2959100.2959133) |
| Pardos2019 | DBLP: UMUAI 29(2), 487-525 |
| Russell2021 | Pearson, Hoboken, 4.ª ed. (el sitio de Pearson indica © 2022) |

## Corregidas
- **Berry2011:** se agregaron páginas (40:1-40:22) y DOI 10.1145/1989734.1989744.
- **Qwen2024:** el autor en arXiv es «Qwen» (An Yang y otros); se ajustó el campo.

## Matices
- **Qwen2.5 3B:** 3,09 mil millones de parámetros (Ollama `qwen2.5:3b`, cuantización Q4_K_M). Se distribuye con la licencia de Qwen, que limita el uso comercial; ya está anotado en el documento.
- **Vaswani2017:** la versión de NeurIPS reporta 27,5 BLEU y la de arXiv 28,4; el documento no cita la cifra.
- **Decreto 1330 de 2019:** varias universidades citan el art. 2.5.3.2.4.1 y los 48 horas por crédito y por periodo; no pude leer el texto oficial. Conviene abrir el [Gestor Normativo de Función Pública](https://www.funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=98270) y confirmar el número del artículo. El texto aclara que la proporción entre trabajo con docente e independiente la define cada institución; las 16 semanas son un supuesto del proyecto.
- **Reclaim, Motion y Ollama:** los tres sitios existen y describen lo que dice el documento (Reclaim ahora es parte de Dropbox). Revisa que `reclaim.ai`, `usemotion.com` y `ollama.com` abran.
- **Afirmaciones sobre el contenido:** Ariga y Lleras, Ward y otros solo los vi en resúmenes y notas de prensa. Las afirmaciones del asistente («la sola presencia del celular reduce la capacidad cognitiva», «las pausas breves ayudan a sostener la atención») coinciden con esos resúmenes.
