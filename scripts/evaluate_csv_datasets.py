"""
Script to convert CSV to RDF, validate RDF using SHACL and store results.
"""
import asyncio
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from csv_to_rdf import CsvToRdfService
from rdf_format import RdfFormatService
from validate_rdf import ValidateRdfService


class CsvValidationPipeline:
    """Pipeline to validate datasets from CSV using SHACL."""
    
    def __init__(self):
        self.csv_service = CsvToRdfService()
        self.rdf_service = RdfFormatService()
        self.validation_service = ValidateRdfService()
    
    async def process_csv(
        self, 
        csv_path: str, 
        output_dir: str = "results",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Process CSV, convert to RDF, validate using SHACL and store results.
        
        Args:
            csv_path: Path to CSV file
            output_dir: Directory to save results
            limit: Limit of datasets to process (None = all)
            
        Returns:
            List of validation results
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Read CSV
        print(f"Reading CSV: {csv_path}")
        datasets = self.csv_service.read_csv(csv_path)
        
        if limit:
            datasets = datasets[:limit]
        
        print(f"Total datasets to process: {len(datasets)}")
        
        results = []
        errors = []
        
        # Process each dataset
        for idx, dataset in enumerate(datasets, 1):
            dataset_id = dataset.get("id", f"dataset_{idx}")
            print(f"\n[{idx}/{len(datasets)}] Processing: {dataset.get('titulo', dataset_id)}")
            
            try:
                # Convert to RDF
                rdf_content = await self.rdf_service.api_to_rdf(dataset)
                
                # Validate using SHACL
                rdf_bytes = rdf_content.encode('utf-8')
                is_valid, validation_errors, validation_warnings = self.validation_service.validate_rdf(
                    rdf_bytes, 
                    filename=f"{dataset_id}.ttl"
                )
                
                # Prepare result
                result = {
                    "dataset_id": dataset_id,
                    "titulo": dataset.get("titulo", ""),
                    "nome": dataset.get("nome", ""),
                    "organizacao": dataset.get("organizacao", ""),
                    "validation": {
                        "valid": is_valid,
                        "errors": validation_errors,
                        "warnings": validation_warnings,
                        "errors_count": len(validation_errors),
                        "warnings_count": len(validation_warnings)
                    },
                    "rdf": rdf_content,
                    "processed_at": datetime.now().isoformat(),
                    "status": "success"
                }
                
                results.append(result)
                status_icon = "✓" if is_valid else "✗"
                print(f"  {status_icon} Validated - Valid: {is_valid}, Errors: {len(validation_errors)}, Warnings: {len(validation_warnings)}")
                
            except Exception as e:
                error_result = {
                    "dataset_id": dataset_id,
                    "titulo": dataset.get("titulo", ""),
                    "nome": dataset.get("nome", ""),
                    "error": str(e),
                    "processed_at": datetime.now().isoformat(),
                    "status": "error"
                }
                errors.append(error_result)
                print(f"  ✗ Error: {str(e)}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full results to JSON
        results_file = output_path / f"validation_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "total_datasets": len(datasets),
                    "successful": len(results),
                    "errors": len(errors),
                    "valid_count": sum(1 for r in results if r.get("validation", {}).get("valid", False)),
                    "invalid_count": sum(1 for r in results if not r.get("validation", {}).get("valid", True)),
                    "processed_at": datetime.now().isoformat()
                },
                "results": results,
                "errors": errors
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Full results saved to: {results_file}")
        
        # Save summary to CSV
        summary_file = output_path / f"validation_summary_{timestamp}.csv"
        self._save_summary_csv(results, errors, summary_file)
        print(f"✓ Summary saved to: {summary_file}")
        
        # Save individual RDF files
        rdf_dir = output_path / "rdf_files"
        rdf_dir.mkdir(exist_ok=True)
        for result in results:
            if result.get("status") == "success":
                rdf_file = rdf_dir / f"{result['dataset_id']}.ttl"
                with open(rdf_file, 'w', encoding='utf-8') as f:
                    f.write(result["rdf"])
        
        print(f"\n✓ Individual RDF files saved to: {rdf_dir}")
        
        return results
    
    def _save_summary_csv(
        self, 
        results: List[Dict[str, Any]], 
        errors: List[Dict[str, Any]],
        output_file: Path
    ):
        """Save validation summary to CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "dataset_id",
                "titulo",
                "organizacao",
                "status",
                "valid",
                "errors_count",
                "warnings_count",
                "errors",
                "warnings",
                "error"
            ])
            
            # Results
            for result in results:
                validation_data = result.get("validation", {})
                errors_list = validation_data.get("errors", [])
                warnings_list = validation_data.get("warnings", [])
                
                # Limit field size for CSV (first 500 chars)
                errors_str = "; ".join(errors_list[:5])  # First 5 errors
                if len(errors_list) > 5:
                    errors_str += f" ... (+{len(errors_list) - 5} more)"
                if len(errors_str) > 500:
                    errors_str = errors_str[:500] + "..."
                
                warnings_str = "; ".join(warnings_list[:5])  # First 5 warnings
                if len(warnings_list) > 5:
                    warnings_str += f" ... (+{len(warnings_list) - 5} more)"
                if len(warnings_str) > 500:
                    warnings_str = warnings_str[:500] + "..."
                
                writer.writerow([
                    result.get("dataset_id", ""),
                    result.get("titulo", ""),
                    result.get("organizacao", ""),
                    result.get("status", ""),
                    validation_data.get("valid", False),
                    validation_data.get("errors_count", 0),
                    validation_data.get("warnings_count", 0),
                    errors_str,
                    warnings_str,
                    ""
                ])
            
            # Errors (datasets that failed during processing)
            for error in errors:
                writer.writerow([
                    error.get("dataset_id", ""),
                    error.get("titulo", ""),
                    "",
                    error.get("status", ""),
                    "",
                    "",
                    "",
                    "",
                    "",
                    error.get("error", "")
                ])


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert CSV to RDF and validate using SHACL")
    parser.add_argument(
        "csv_path",
        help="Path to CSV file"
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to save results (default: results)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of datasets to process (optional)"
    )
    
    args = parser.parse_args()
    
    pipeline = CsvValidationPipeline()
    await pipeline.process_csv(
        csv_path=args.csv_path,
        output_dir=args.output_dir,
        limit=args.limit
    )


if __name__ == "__main__":
    asyncio.run(main())

