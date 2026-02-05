"""
Utilitário para normalizar e validar datas para formato xsd:date (ISO 8601).
"""
import re
from datetime import datetime
from typing import Optional


def normalize_date(date_str: str) -> Optional[str]:
    """
    Normaliza uma data para formato ISO 8601 (YYYY-MM-DD) esperado por xsd:date.
    
    Suporta formatos:
    - DD/MM/YYYY
    - DD/MM/YYYY HH:MM:SS
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    
    Args:
        date_str: String com a data em qualquer formato
        
    Returns:
        String no formato YYYY-MM-DD ou None se inválida
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    
    # Ignora valores inválidos conhecidos
    invalid_patterns = [
        "indisponível",
        "não encontrado",
        "inválido",
        "null",
        "none",
        "n/a",
        "na",
    ]
    
    date_lower = date_str.lower()
    if any(pattern in date_lower for pattern in invalid_patterns):
        return None
    
    # Tenta formatos brasileiros: DD/MM/YYYY ou DD/MM/YYYY HH:MM:SS
    br_date_pattern = r'^(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2}):(\d{2}))?$'
    match = re.match(br_date_pattern, date_str)
    if match:
        day, month, year = match.groups()[:3]
        try:
            # Valida a data
            datetime(int(year), int(month), int(day))
            return f"{year}-{month}-{day}"
        except (ValueError, TypeError):
            return None
    
    # Tenta formato ISO: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS
    iso_pattern = r'^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2}))?'
    match = re.match(iso_pattern, date_str)
    if match:
        year, month, day = match.groups()[:3]
        try:
            # Valida a data
            datetime(int(year), int(month), int(day))
            return f"{year}-{month}-{day}"
        except (ValueError, TypeError):
            return None
    
    # Tenta outros formatos comuns
    try:
        # Tenta parsear com datetime
        for fmt in [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M:%S",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    except Exception:
        pass
    
    return None


def is_valid_date(date_str: str) -> bool:
    """
    Verifica se uma string é uma data válida.
    
    Args:
        date_str: String com a data
        
    Returns:
        True se for uma data válida, False caso contrário
    """
    return normalize_date(date_str) is not None

