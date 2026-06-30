# Third-party notices

This file lists software **not** authored in this repository but installed at runtime on the MCP server host (R packages, Python dependencies). This repo’s license is in [LICENSE](LICENSE) (MIT, Miguel Escribano).

## openair (R)

Charts, statistics, and network imports are produced by calling the **[openair](https://github.com/openair-project/openair)** R package.

- **License:** MIT  
- **Copyright:** openair authors (see `https://github.com/openair-project/openair`)  
- **Citation (figures / papers):** Carslaw, D. C. and K. Ropkins (2012). *openair — an R package for air quality data analysis.* Environmental Modelling & Software, 27–28, 52–61. [doi:10.1016/j.envsoft.2011.09.008](https://doi.org/10.1016/j.envsoft.2011.09.008)

MIT license text (openair):

```
Copyright (c) 2025 openair authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Source: [openair LICENSE](https://openair-project.github.io/openair/LICENSE.html)

**Relationship:** openair-3-mcp-server-oss is an independent, open-source MCP wrapper. It is **not affiliated with or endorsed by** openair-project maintainers.

## Public air-quality data

Tools such as `import_aurn` and `import_europe` fetch **third-party datasets** over the network. Licences belong to the data providers (e.g. UK [Open Government Licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)). See **Third-party and attribution** in [README.md](README.md).

## Python stack

Server Python code (FastMCP, Pydantic, etc.) is installed via `pip install -e .` from [pyproject.toml](pyproject.toml). Each package carries its own licence on PyPI.
