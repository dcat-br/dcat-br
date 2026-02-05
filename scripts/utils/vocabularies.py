"""
Utilitário para carregar e converter valores dos vocabulários controlados DCAT-BR.
Carrega os CSVs dos vocabulários e faz conversão de literais para IRIs.
"""
import csv
import os
from pathlib import Path
from typing import Dict, Optional
import urllib.request
import urllib.error

# Cache para os vocabulários carregados
_vocab_cache: Dict[str, Dict[str, str]] = {}


def _get_vocab_path(vocab_name: str) -> Optional[Path]:
    """Retorna o caminho do arquivo CSV do vocabulário."""
    # Tenta encontrar o arquivo localmente primeiro
    # __file__ está em src/utils/vocabularies.py
    # Precisamos subir: src/utils -> src -> inspire-catalogo-pyapis -> projeto_1 -> DCAT-BR
    current_file = Path(__file__)
    # src/utils/vocabularies.py -> src -> inspire-catalogo-pyapis -> projeto_1
    project_root = current_file.parent.parent.parent.parent
    base_path = project_root / "DCAT-BR" / "docs" / "vocabularies"
    
    vocab_paths = {
        "freq": base_path / "VCR-FR" / "freq.csv",
        "sei": base_path / "SEI" / "sei.csv",
        "formato": base_path / "formato" / "formatos.csv",
        "tipo-recurso": base_path / "tipo-recurso" / "tipo-recurso.csv",
        "themes": base_path / "themes" / "themes.csv",
        "vcr-ce": base_path / "VCR-CE" / "cobertura-espacial.csv",
        "vcr-lu": base_path / "VCR-LU" / "licensa-uso.csv",
    }
    
    return vocab_paths.get(vocab_name.lower())


def _load_vocab_from_url(url: str) -> Dict[str, str]:
    """Carrega um vocabulário de uma URL."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            content = response.read().decode('utf-8')
            return _parse_csv(content)
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"⚠️  Erro ao carregar vocabulário de {url}: {e}")
        return {}


def _parse_csv(content: str) -> Dict[str, str]:
    """Parseia conteúdo CSV no formato URI,NOTACAO ou URI,LABEL."""
    vocab_map = {}
    lines = content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Formato: URI,NOTACAO ou URI,LABEL
        # Usa csv.reader para lidar com vírgulas dentro de strings
        try:
            import csv as csv_module
            from io import StringIO
            reader = csv_module.reader(StringIO(line))
            parts = next(reader)
        except:
            # Fallback: split simples
            parts = line.split(',', 1)
        
        if len(parts) >= 2:
            uri = parts[0].strip()
            notation_or_label = parts[1].strip()
            # Mapeia tanto pela notação quanto pelo label (case-insensitive e case-sensitive)
            vocab_map[notation_or_label.upper()] = uri
            vocab_map[notation_or_label] = uri
            # Também mapeia versões com espaços/hífens normalizados
            normalized = notation_or_label.lower().replace(" ", "-").replace("_", "-")
            if normalized != notation_or_label.lower():
                vocab_map[normalized] = uri
                vocab_map[normalized.upper()] = uri
    
    return vocab_map


def load_vocab(vocab_name: str, force_reload: bool = False) -> Dict[str, str]:
    """
    Carrega um vocabulário do cache ou do arquivo/URL.
    
    Args:
        vocab_name: Nome do vocabulário (freq, sei, formato, tipo-recurso, themes, etc.)
        force_reload: Se True, força recarregar mesmo se já estiver em cache
        
    Returns:
        Dicionário mapeando valores (notação/label) para URIs
    """
    cache_key = vocab_name.lower()
    
    # Retorna do cache se já estiver carregado
    if not force_reload and cache_key in _vocab_cache:
        return _vocab_cache[cache_key]
    
    vocab_map = {}
    
    # Tenta carregar localmente primeiro
    local_path = _get_vocab_path(cache_key)
    if local_path and local_path.exists():
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                vocab_map = _parse_csv(f.read())
        except Exception as e:
            print(f"⚠️  Erro ao carregar vocabulário local {local_path}: {e}")
    
    # Se não encontrou localmente, tenta carregar da URL do GitHub
    if not vocab_map:
        urls = {
            "freq": "https://dcat-br.github.io/dcat-br/docs/vocabularies/VCR-FR/freq.csv",
            "sei": "https://dcat-br.github.io/dcat-br/docs/vocabularies/SEI/sei.csv",
            "formato": "https://dcat-br.github.io/dcat-br/docs/vocabularies/formato/formatos.csv",
            "tipo-recurso": "https://dcat-br.github.io/dcat-br/docs/vocabularies/tipo-recurso/tipo-recurso.csv",
            "themes": "https://dcat-br.github.io/dcat-br/docs/vocabularies/themes/themes.csv",
            "vcr-ce": "https://dcat-br.github.io/dcat-br/docs/vocabularies/VCR-CE/cobertura-espacial.csv",
            "vcr-lu": "https://dcat-br.github.io/dcat-br/docs/vocabularies/VCR-LU/licensa-uso.csv",
        }
        
        url = urls.get(cache_key)
        if url:
            vocab_map = _load_vocab_from_url(url)
    
    # Salva no cache
    if vocab_map:
        _vocab_cache[cache_key] = vocab_map
    
    return vocab_map


def convert_to_iri(value: str, vocab_name: str) -> Optional[str]:
    """
    Converte um valor literal para IRI usando o vocabulário especificado.
    
    Args:
        value: Valor literal do JSON (ex: "MENSAL", "Público", "PDF")
        vocab_name: Nome do vocabulário (freq, sei, formato, tipo-recurso, themes)
        
    Returns:
        URI correspondente ou None se não encontrado
    """
    if not value:
        return None
    
    vocab = load_vocab(vocab_name)
    
    # Tenta encontrar exato (case-insensitive)
    value_upper = value.strip().upper()
    if value_upper in vocab:
        return vocab[value_upper]
    
    # Tenta encontrar com o valor original
    value_stripped = value.strip()
    if value_stripped in vocab:
        return vocab[value_stripped]
    
    # Para licenças, tenta normalizar (cc-by, cc_by, CC-BY, etc.)
    if vocab_name == "vcr-lu":
        # Normaliza: remove espaços, converte para minúsculas, substitui _ por -
        normalized = value_stripped.lower().replace("_", "-").replace(" ", "-")
        if normalized in vocab:
            return vocab[normalized]
        # Tenta também com hífen substituído por underscore
        normalized_underscore = value_stripped.lower().replace("-", "_").replace(" ", "_")
        if normalized_underscore in vocab:
            return vocab[normalized_underscore]
    
    # Para temas, tenta normalizar o nome e construir a URI
    if vocab_name == "themes":
        # Tenta encontrar no vocabulário primeiro
        if vocab:
            # Normaliza o nome: remove acentos, espaços, underscores
            import unicodedata
            # Remove acentos
            name_no_accents = ''.join(
                c for c in unicodedata.normalize('NFD', value_stripped.lower())
                if unicodedata.category(c) != 'Mn'
            )
            name_normalized = name_no_accents.replace(" ", "-").replace("_", "-")
            # Verifica se existe no vocabulário com o nome normalizado
            if name_normalized in vocab:
                return vocab[name_normalized]
            # Se não encontrou, constrói a URI baseada no nome normalizado
            return f"https://dcat-br.github.io/dcat-br/docs/vocabularies/themes/{name_normalized}"
    
    return None


# Funções de conveniência para cada vocabulário
def freq_to_iri(value: str) -> Optional[str]:
    """Converte frequência para IRI."""
    return convert_to_iri(value, "freq")


def sei_to_iri(value: str) -> Optional[str]:
    """Converte observância legal (SEI) para IRI."""
    return convert_to_iri(value, "sei")


def formato_to_iri(value: str) -> Optional[str]:
    """Converte formato para IRI (IANA Media Type)."""
    return convert_to_iri(value, "formato")


def tipo_recurso_to_iri(value: str) -> Optional[str]:
    """Converte tipo de recurso para IRI."""
    return convert_to_iri(value, "tipo-recurso")


def theme_to_iri(value: str) -> Optional[str]:
    """Converte tema para IRI."""
    return convert_to_iri(value, "themes")


def licenca_to_iri(value: str) -> Optional[str]:
    """Converte licença para IRI (VCR-LU)."""
    return convert_to_iri(value, "vcr-lu")

