# DCAT-BR

DCAT Application Profile for Data Catalogues in Brazil

## About

DCAT-BR is an application profile based on the W3C [Data Catalogue Vocabulary (DCAT)](https://www.w3.org/TR/vocab-dcat-3/), developed specifically to describe public data catalogues in Brazil.

## Repository Structure

```
DCAT-BR/
├── index.html              # Main site page
├── CHANGELOG.md            # Change history
├── releases.json           # Release information
├── assets/                 # Static resources
│   ├── css/
│   │   └── style.css       # Site styles
│   └── js/
│       ├── main.js         # Main scripts
│       └── releases.js     # Release loading
├── docs/
│   ├── releases/           # DCAT-BR versions
│   │   └── 1.0/
│   │       ├── index.html  # Version page
│   │       ├── dcat-br.html
│   │       ├── dcat-br.pdf
│   │       └── dcat-br.rdf
│   ├── shacl/              # SHACL files
│   └── vocabularies/       # Controlled vocabularies
└── README.md               # This file
```

## How to Add a New Version

1. **Create version directory**:
   ```bash
   mkdir -p docs/releases/1.1
   ```

2. **Add specification files**:
   - `dcat-br.html` - HTML specification
   - `dcat-br.pdf` - PDF specification
   - `dcat-br.rdf` - RDF specification

3. **Create version page**:
   - Copy `docs/releases/1.0/index.html` to `docs/releases/1.1/index.html`
   - Update version information

4. **Update `releases.json`**:
   ```json
   {
     "version": "1.1",
     "date": "2025-12-12",
     "status": "Recommendation",
     "description": "Description of the new version...",
     "links": {
       "html": "docs/releases/1.1/dcat-br.html",
       "pdf": "docs/releases/1.1/dcat-br.pdf",
       "rdf": "docs/releases/1.1/dcat-br.rdf"
     },
     "shacl": "docs/shacl/1.1/"
   }
   ```

5. **Update `CHANGELOG.md`**:
   - Add an entry for the new version following the existing format

6. **Update `assets/js/releases.js`**:
   - Add the new version to the `releasesData.releases` array

7. **Update latest version**:
   - Update the `latest` field in `releases.json`

## Local Development

To view the site locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/dcat-br/dcat-br.git
   cd dcat-br
   ```

2. Open `index.html` in a browser or use a local server:
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Node.js (with http-server)
   npx http-server
   ```

3. Access `http://localhost:8000`

## Contributing

Issues or suggestions can be submitted as [issues](https://github.com/dcat-br/dcat-br/issues) on GitHub.

## License

Copyright © 2025 DCAT-BR. All material in this repository is published under the [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) license, unless explicitly stated otherwise.
