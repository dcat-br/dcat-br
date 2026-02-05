"""
Service for converting CSV data to RDF format
"""
import csv
import json
import sys
from typing import Dict, Any, List
from pathlib import Path


class CsvToRdfService:
    """Service for converting CSV data to the format expected by ApiToRdfService"""
    
    def csv_row_to_dict(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert a CSV row to the dictionary format expected by ApiToRdfService
        
        Args:
            row: Dictionary with CSV column names as keys
            
        Returns:
            Dictionary in the format expected by ApiToRdfService
        """
        data = {}
        
        # Basic fields
        data["id"] = row.get("id", "")
        data["titulo"] = row.get("titulo", "")
        data["nome"] = row.get("nome", "")
        data["organizacao"] = row.get("organizacao", "")
        data["descricao"] = row.get("descricao", "")
        data["licenca"] = row.get("licenca", "")
        data["responsavel"] = row.get("responsavel", "")
        data["emailResponsavel"] = row.get("emailResponsavel", "")
        data["periodicidade"] = row.get("periodicidade", "")
        data["versao"] = row.get("versao", "")
        data["coberturaEspacial"] = row.get("coberturaEspacial", "")
        data["granularidadeEspacial"] = row.get("granularidadeEspacial", "")
        data["coberturaTemporalInicio"] = row.get("coberturaTemporalInicio", "")
        data["coberturaTemporalFim"] = row.get("coberturaTemporalFim", "")
        data["dataCatalogacao"] = row.get("dataCatalogacao", "")
        data["dataUltimaAtualizacaoMetadados"] = row.get("dataUltimaAtualizacaoMetadados", "")
        data["observanciaLegal"] = row.get("observanciaLegal", "")
        
        # Boolean fields
        dados_raca_etnia = row.get("dadosRacaEtnia", "")
        if dados_raca_etnia:
            data["dadosRacaEtnia"] = dados_raca_etnia.lower() in ("true", "sim", "1", "yes")
        
        dados_genero = row.get("dadosGenero", "")
        if dados_genero:
            data["dadosGenero"] = dados_genero.lower() in ("true", "sim", "1", "yes")
        
        # Parse temas (JSON array)
        temas_str = row.get("temas", "")
        if temas_str:
            try:
                data["temas"] = json.loads(temas_str)
            except json.JSONDecodeError:
                data["temas"] = []
        else:
            data["temas"] = []
        
        # Parse tags (JSON array)
        tags_str = row.get("tags", "")
        if tags_str:
            try:
                data["tags"] = json.loads(tags_str)
            except json.JSONDecodeError:
                data["tags"] = []
        else:
            data["tags"] = []
        
        # Parse recursos (JSON array)
        recursos_str = row.get("recursos", "")
        if recursos_str:
            try:
                data["recursos"] = json.loads(recursos_str)
            except json.JSONDecodeError:
                data["recursos"] = []
        else:
            data["recursos"] = []
        
        return data
    
    def read_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Read CSV file and convert each row to the expected format
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of dictionaries in the format expected by ApiToRdfService
        """
        data_list = []
        
        # Increase CSV field size limit (default is 131072)
        # Required for large fields such as descriptions
        csv.field_size_limit(min(2**31 - 1, sys.maxsize))
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                converted_row = self.csv_row_to_dict(row)
                data_list.append(converted_row)
        
        return data_list

