# Dependency and license notes

UPT's original Python source and documentation are provided under the MIT license in `LICENSE`, with copyright placeholders for the publisher to replace. That license does **not** relicense Python, Qt, PySide, Python-Markdown, or their dependencies.

This source archive contains no dependency wheels, Python runtime, Qt DLLs, fonts, or other third-party binaries. Install dependencies from their upstream distributions. The license copies under `licenses/` are reference notices, not a claim that those projects are UPT's original work.

## Runtime

| Component | Version | License / role |
| --- | --- | --- |
| Python | Verified 3.12.14; package targets 3.11–3.13 | PSF license and bundled notices; interpreter installed separately |
| PySide6 Essentials | 6.8.3 | Upstream metadata: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; Qt Python UI bindings and Qt shared libraries |
| shiboken6 | 6.8.3 | Same license alternatives in upstream metadata; Python/C++ binding helper |
| Qt Core, GUI, Widgets | 6.8.3 via the PySide wheel | Open-source Qt modules used by this app; LGPLv3 route, subject to module/third-party notices |
| Python-Markdown | 3.7 | BSD 3-Clause; Markdown conversion |

The intended source-use route for Qt/PySide is the community **LGPLv3** option with ordinary dynamically loaded Python modules/shared libraries. UPT does not modify Qt/PySide, statically link it, embed a web engine, restrict library replacement, or impose restrictions on debugging modifications. The MIT application source remains separately licensed. A commercial Qt license is an alternative offered by Qt; no commercial license is supplied here.

Qt/PySide have additional bundled components and notices; the Essentials wheel includes modules beyond those imported by UPT. A binary redistributor must inspect the **actual included files**, retain applicable licenses/notices, provide corresponding library source/access as required, and preserve the user's ability to replace/relink and debug modified LGPL libraries. Source-only dependency declarations do not constitute a complete frozen-binary compliance package. Do not simply bundle the entire development environment and label it MIT.

Upstream sources and license references:

- [Qt for Python 6.8 documentation](https://doc.qt.io/qtforpython-6.8/)
- [PySide6 Essentials 6.8.3 metadata and wheels](https://pypi.org/project/PySide6-Essentials/6.8.3/)
- [shiboken6 6.8.3 metadata](https://pypi.org/project/shiboken6/6.8.3/)
- [Qt/PySide source repository, v6.8.3](https://code.qt.io/cgit/pyside/pyside-setup.git/tree/?h=v6.8.3)
- [Qt 6.8 LGPL license](https://doc.qt.io/qt-6.8/lgpl.html) and [Qt licensing overview](https://doc.qt.io/qt-6.8/licensing.html)
- [Qt for Python third-party licenses](https://doc.qt.io/qtforpython-6.8/licenses.html)
- [Qt's third-party license inventory](https://doc.qt.io/qt-6.8/licenses-used-in-qt.html)
- [Python-Markdown source/license](https://github.com/Python-Markdown/markdown/blob/3.7/LICENSE.md)
- [Python license](https://docs.python.org/3/license.html)

`licenses/Python-Markdown-BSD-3-Clause.txt` is copied verbatim from the installed Markdown 3.7 distribution, including its copyright notices. `licenses/LGPL-3.0-only.txt` and `licenses/GPL-3.0-only.txt` are unmodified license texts from the PySide v6.8.3 source's `LICENSES` directory, mirrored at [the official GitHub repository](https://github.com/pyside/pyside-setup/tree/v6.8.3/LICENSES). LGPLv3 incorporates the GPLv3 terms, so both reference texts are included. These are not alternate application licenses.

## Testing and building

pytest 8.3.5 is MIT-licensed and used only for development. Its installed dependencies include colorama (BSD 3-Clause), iniconfig (MIT), packaging (Apache-2.0 OR BSD-2-Clause), and pluggy (MIT). The verified environment used colorama 0.4.6, iniconfig 2.3.1, packaging 26.3, and pluggy 1.7.0. The requirements pin pytest itself; these helper versions are not frozen across all future installations. Read their upstream distributions' notices if redistributing them. They are not included in the source ZIP.

setuptools is the MIT-licensed build backend; build and pip are optional development/setup tools. The verified packaging environment used setuptools 80.9.0, build 1.2.2.post1, and pip 25.1.1. UPT does not import these at runtime.

## Assets

UI colors, layout, documentation, and example notes are original to this delivery. File/folder icons come from Qt's standard style at runtime. System fonts are requested by family name and are not redistributed. No proprietary branding, screenshots of another editor, logos, or icon sets are bundled.

Review these notes again when changing dependencies or creating installers; the obligations depend on what is actually distributed. The publication checklist calls out this review before any binary release.
