# Validation Scripts

## evaluate_csv_datasets.py

Script to convert CSV to RDF, validate RDF using SHACL (DCAT-BR) and store results.

### Usage

```bash
# Process all datasets from CSV
uv run scripts/evaluate_csv_datasets.py "path/to/file.csv"

# Process only the first 10 datasets (useful for testing)
uv run scripts/evaluate_csv_datasets.py "path/to/file.csv" --limit 10

# Specify output directory
uv run scripts/evaluate_csv_datasets.py "path/to/file.csv" --output-dir results
```

### Example

```bash
cd DCAT-BR
uv run scripts/evaluate_csv_datasets.py "path/to/datasets.csv" --limit 5 --output-dir results
```

### Output

The script generates:

1. **validation_results_TIMESTAMP.json**: Complete JSON file with all results, including:
   - Execution metadata (total, valid, invalid)
   - Full results per dataset (including RDF, SHACL errors and warnings)
   - Processing errors

2. **validation_summary_TIMESTAMP.csv**: CSV summary with:
   - Dataset ID
   - Title
   - Organization
   - Status (success/error)
   - Valid (true/false)
   - Error count
   - Warning count
   - Error list
   - Warning list
   - Processing errors (if any)

3. **rdf_files/**: Directory with individual RDF files (.ttl) for each successfully processed dataset

### CSV Structure

The CSV must contain the following columns:

- `id`: Unique identifier
- `titulo`: Dataset title
- `nome`: Dataset name/slug
- `organizacao`: Organization name
- `descricao`: Dataset description
- `licenca`: License (e.g. odc-odbl)
- `responsavel`: Technical contact
- `emailResponsavel`: Contact email
- `periodicidade`: Update frequency
- `temas`: JSON array with themes
- `tags`: JSON array with tags
- `recursos`: JSON array with resources/distributions
- Other fields as needed
