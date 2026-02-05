# DCAT-BR evaluation for Dados.gov.br

**Scraping:** collect dataset metadata from the portal API. **Evaluation:** convert CSV to RDF and validate with DCAT-BR SHACL.

## Scraping (2 steps)

1. **web_scrap.py** — Get metadata infos, output CSV: `id`, `nome`, `titulo`, `nomeOrganizacao`, `ultimaAtualizacaoDados`..

```bash
uv run python scripts/web_scrap.py 
```

Defaults: `set_list.py` → `lista_conjuntos.csv` (20 items, termo=aberto). `search_details.py` → reads that, writes `dados/dados_scraping.csv`.

## Evaluation

**evaluate_csv_datasets.py** — CSV → RDF (Turtle) → SHACL validation. Output: `validation_results_*.json`, `validation_summary_*.csv`, `rdf_files/*.ttl`.

```bash
uv run python scripts/evaluate_csv_datasets.py "path/to/file.csv" [--limit N] [--output-dir dir]
```

CSV must have columns like `id`, `titulo`, `nome`, `organizacao`, `descricao`, `recursos` (JSON), `temas`, `tags`, etc. — same format as scraping output or `dados_abertos_publicos_5k`.
