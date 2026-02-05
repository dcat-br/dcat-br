"""
Fetches datasets via API /api/publico/conjuntos-dados/buscar (paginated; returns full
detail per registro) and writes CSV in dados_abertos_publicos_5k format.
Usage: python search_details.py [output_details.csv] [base_url] [max_registros]
  max_registros: optional limit (default: fetch all). Example: 5000
"""
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlencode

import requests

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

BUSCAR_PATH = "/api/publico/conjuntos-dados/buscar"

# Columns matching reference CSV dados_abertos_publicos_5k
CSV_COLUMNS = [
    "id", "titulo", "nome", "organizacao", "descricao", "licenca", "responsavel",
    "emailResponsavel", "periodicidade", "temas", "tags",
    "coberturaTemporalInicio", "coberturaTemporalFim", "coberturaEspacial",
    "valorCoberturaEspacial", "granularidadeEspacial", "versao", "atualizacaoVersao",
    "visibilidade", "descontinuado", "dataDescontinuacao", "reuso", "recursos",
    "conjuntoDadosAssociados", "dataUltimaAtualizacaoMetadados",
    "dataUltimaAtualizacaoArquivo", "dataCatalogacao", "atualizado",
    "dadosRacaEtnia", "dadosGenero", "observanciaLegal", "dadosAbertos", "selo",
    "origemCadastro", "Dados Abertos", "Dados Públicos",
]

# Resource key order matching dados_abertos_publicos_5k
RECURSO_KEYS_5K = [
    "dataUltimaAtualizacaoArquivo", "dataCatalogacao", "link", "idConjuntoDados",
    "descricao", "titulo", "formato", "tipo", "numOrdem", "nomeArquivo",
    "quantidadeDownloads", "tamanho", "id",
]


def fetch_conjunto_detail(base_url: str, nome: str, session: requests.Session, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """GET /api/publico/conjuntos-dados/{nome}"""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    url = f"{base}/api/publico/conjuntos-dados/{nome}"
    try:
        r = session.get(url, timeout=timeout, headers={**session.headers, "Accept": "application/json"})
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def fetch_buscar_page(
    base_url: str,
    offset: int,
    tamanho_pagina: int,
    session: requests.Session,
    timeout: int = 30,
    dados_abertos: bool = True,
) -> Optional[Dict[str, Any]]:
    """GET /api/publico/conjuntos-dados/buscar?offset=&tamanhoPagina=&dadosAbertos="""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    params = {"offset": offset, "tamanhoPagina": tamanho_pagina, "dadosAbertos": "true" if dados_abertos else "false"}
    url = f"{base}{BUSCAR_PATH}?{urlencode(params)}"
    try:
        r = session.get(url, timeout=timeout, headers={**session.headers, "Accept": "application/json"})
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def _normalize_buscar_to_detail(registro: Dict[str, Any]) -> Dict[str, Any]:
    """Converte um item de registros da API buscar para o formato esperado por _detail_to_row_5k."""
    extras_obj = registro.get("extras") or {}
    extras_list = [{"key": k, "value": v} for k, v in extras_obj.items()]
    org_title = (registro.get("organizationTitle") or "").strip()
    org_name = (registro.get("organizationName") or "").strip()
    return {
        "id": registro.get("id"),
        "name": registro.get("name"),
        "title": registro.get("title"),
        "notes": registro.get("notes"),
        "organization": {"display_name": org_title, "title": org_title, "name": org_name},
        "maintainer": registro.get("maintainer"),
        "maintainer_email": registro.get("maintainerEmail"),
        "license_id": registro.get("licenca"),
        "version": registro.get("version"),
        "metadata_created": registro.get("metadataCreated"),
        "metadata_modified": registro.get("ultimaAtualizacaoMetadados"),
        "extras": extras_list,
        "tags": registro.get("tagsFormatado") or registro.get("tagsAcessoRapido") or [],
        "groups": registro.get("temasFormatado") or registro.get("temasAcessoRapido") or [],
        "resources": registro.get("resourcesFormatado") or registro.get("resourcesAcessoRapido") or [],
    }


def _recurso_to_5k(res: Dict, rf: Dict, dataset_id: str) -> Dict[str, Any]:
    """Monta um recurso no formato do dados_abertos_publicos_5k (ordem de chaves e campos)."""
    link = res.get("url") or rf.get("link") or ""
    titulo_rec = res.get("name") or rf.get("titulo") or ""
    desc_rec = res.get("description") or rf.get("descricao") or ""
    formato = res.get("format") or rf.get("formato") or ""
    tipo = res.get("tipo") or rf.get("tipo")
    data_cat = rf.get("dataCatalogacao") or res.get("created") or ""
    data_ult = rf.get("dataUltimaAtualizacaoArquivo") or res.get("last_modified") or ""
    tamanho = res.get("size") or rf.get("tamanho") or 0
    rec_id = res.get("id")
    raw = {
        "dataUltimaAtualizacaoArquivo": data_ult or "",
        "dataCatalogacao": data_cat or "",
        "link": link,
        "idConjuntoDados": dataset_id,
        "descricao": desc_rec or "",
        "titulo": titulo_rec or "",
        "formato": formato or "",
        "tipo": tipo,
        "numOrdem": None,
        "nomeArquivo": None,
        "quantidadeDownloads": None,
        "tamanho": tamanho if tamanho is not None else 0,
        "id": rec_id,
    }
    return {k: raw[k] for k in RECURSO_KEYS_5K}


def _detail_to_row_5k(detail: Dict[str, Any]) -> Dict[str, Any]:
    """Converte resposta da API conjuntos-dados/{nome} para linha CSV no formato 5k."""
    dataset_id = detail.get("id") or ""
    name = (detail.get("name") or "").strip()
    title = (detail.get("title") or "").strip()
    notes = (detail.get("notes") or "").strip()
    org = detail.get("organization") or {}
    org_name = (org.get("display_name") or org.get("title") or org.get("name") or "").strip()
    maintainer = (detail.get("maintainer") or "").strip()
    maintainer_email = (detail.get("maintainer_email") or "").strip()
    license_id = (detail.get("license_id") or "notspecified").strip()
    version = (detail.get("version") or "").strip()
    metadata_created = detail.get("metadata_created") or ""
    metadata_modified = detail.get("metadata_modified") or ""

    extras_list = detail.get("extras") or []
    extras = {e.get("key"): e.get("value") for e in extras_list if isinstance(e, dict) and e.get("key")}
    periodicidade = (extras.get("periodicidade") or "").strip() if extras.get("periodicidade") else ""
    # Formato 5k: dadosRacaEtnia, dadosGenero, observanciaLegal vazios ou texto; não "false"/"1"
    def _norm_opt(v):
        if v is None or v == "": return ""
        s = str(v).strip().lower()
        if s in ("false", "true", "0", "1") or v in (True, False, 0, 1): return ""
        return str(v).strip()
    dados_raca = _norm_opt(extras.get("dadosRacaEtnia"))
    dados_genero = _norm_opt(extras.get("dadosGenero"))
    observancia = _norm_opt(extras.get("observanciaLegal"))
    descontinuado = str(extras.get("descontinuado", "false")).lower() == "true"
    data_descontinuacao = (extras.get("dataDescontinuacao") or "").strip()
    ultima_metadados = extras.get("ultimaAtualizacaoMetadados", metadata_modified)
    cobertura_espacial = (extras.get("coberturaEspacial") or "").strip()
    valor_cobertura_espacial = (extras.get("valorCoberturaEspacial") or "").strip()
    granularidade_espacial = (extras.get("granularidadeEspacial") or "").strip()
    conjunto_associados = (extras.get("conjuntoDadosAssociados") or "[]").strip()
    if conjunto_associados and not conjunto_associados.startswith("["):
        conjunto_associados = "[]"

    tags_list = detail.get("tags") or []
    tags_str = json.dumps([
        {"id": t.get("id"), "name": t.get("name"), "display_name": t.get("display_name")}
        for t in tags_list
    ], ensure_ascii=False)

    groups = detail.get("groups") or []
    temas_str = json.dumps([{"name": g.get("name"), "title": g.get("title")} for g in groups], ensure_ascii=False)

    recursos_list = []
    for res in detail.get("resources") or []:
        rf = res.get("recursoForm") or res.get("recursoApiView") or res
        recursos_list.append(_recurso_to_5k(res, rf, dataset_id))
    recursos_str = json.dumps(recursos_list, ensure_ascii=False)

    data_ult_arquivo = "Indisponível"
    if recursos_list and recursos_list[0].get("dataUltimaAtualizacaoArquivo"):
        val = recursos_list[0]["dataUltimaAtualizacaoArquivo"]
        if val and "Indisponível" not in str(val):
            data_ult_arquivo = val

    # Formato 5k: descricao em uma linha (sem quebras), para não quebrar linhas do CSV
    descricao_raw = (notes[:5000] if notes else "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    descricao = re.sub(r"  +", " ", descricao_raw).strip()
    return {
        "id": dataset_id,
        "titulo": title or name or "Sem título",
        "nome": name,
        "organizacao": org_name,
        "descricao": descricao,
        "licenca": license_id,
        "responsavel": maintainer,
        "emailResponsavel": maintainer_email,
        "periodicidade": periodicidade,
        "temas": temas_str,
        "tags": tags_str,
        "coberturaTemporalInicio": "",
        "coberturaTemporalFim": "",
        "coberturaEspacial": cobertura_espacial,
        "valorCoberturaEspacial": valor_cobertura_espacial,
        "granularidadeEspacial": granularidade_espacial,
        "versao": version,
        "atualizacaoVersao": "",
        "visibilidade": "PUBLICA",
        "descontinuado": "True" if descontinuado else "False",
        "dataDescontinuacao": data_descontinuacao,
        "reuso": "False",
        "recursos": recursos_str,
        "conjuntoDadosAssociados": conjunto_associados,
        "dataUltimaAtualizacaoMetadados": ultima_metadados or metadata_modified,
        "dataUltimaAtualizacaoArquivo": data_ult_arquivo,
        "dataCatalogacao": metadata_created,
        "atualizado": "Atualização não verificável",
        "dadosRacaEtnia": dados_raca,
        "dadosGenero": dados_genero,
        "observanciaLegal": observancia,
        "dadosAbertos": "Aberto",
        "selo": "Público",
        "origemCadastro": "Scraping",
        "Dados Abertos": "Aberto",
        "Dados Públicos": "Público",
    }


def row_from_lista_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal row when detail is not available (fallback)."""
    return {
        "id": item.get("id") or "",
        "titulo": (item.get("titulo") or "").strip() or "Sem título",
        "nome": (item.get("nome") or "").strip(),
        "organizacao": (item.get("nomeOrganizacao") or "").strip(),
        "descricao": "",
        "licenca": "notspecified",
        "responsavel": "",
        "emailResponsavel": "",
        "periodicidade": "",
        "temas": "[]",
        "tags": "[]",
        "coberturaTemporalInicio": "",
        "coberturaTemporalFim": "",
        "coberturaEspacial": "",
        "valorCoberturaEspacial": "",
        "granularidadeEspacial": "",
        "versao": "",
        "atualizacaoVersao": "",
        "visibilidade": "PUBLICA",
        "descontinuado": "False",
        "dataDescontinuacao": "",
        "reuso": "False",
        "recursos": "[]",
        "conjuntoDadosAssociados": "[]",
        "dataUltimaAtualizacaoMetadados": "",
        "dataUltimaAtualizacaoArquivo": (item.get("ultimaAtualizacaoDados") or "").strip(),
        "dataCatalogacao": "",
        "atualizado": "Atualização não verificável",
        "dadosRacaEtnia": "",
        "dadosGenero": "",
        "observanciaLegal": "",
        "dadosAbertos": "Aberto",
        "selo": "Público",
        "origemCadastro": "Scraping",
        "Dados Abertos": "Aberto",
        "Dados Públicos": "Público",
    }


def buscar_detalhes(
    output_csv: str,
    base_url: str = "https://dados.gov.br",
    tamanho_pagina: int = 100,
    max_registros: Optional[int] = None,
    dados_abertos: bool = True,
    delay: float = 0.5,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetches all datasets via GET {base_url}/api/publico/conjuntos-dados/buscar
    (paginated; each page returns full detail). Converts to CSV in 5k format.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    results: List[Dict[str, Any]] = []
    offset = 0
    total_registros = None

    while True:
        if max_registros is not None and len(results) >= max_registros:
            break
        page_size = tamanho_pagina
        if max_registros is not None:
            page_size = min(tamanho_pagina, max_registros - len(results))
        data = fetch_buscar_page(
            base_url, offset, page_size, session, timeout=timeout, dados_abertos=dados_abertos
        )
        if not data:
            print(f"  Request failed at offset {offset}")
            break
        registros = data.get("registros") or []
        if total_registros is None:
            total_registros = data.get("totalRegistros", 0)
            print(f"  Total no portal: {total_registros}")
        for registro in registros:
            detail = _normalize_buscar_to_detail(registro)
            results.append(_detail_to_row_5k(detail))
        n = len(registros)
        print(f"  Offset {offset}: got {n} registros (total collected: {len(results)})")
        if n == 0 or n < page_size:
            break
        offset += n
        if delay > 0:
            time.sleep(delay)

    if output_csv and results:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in results:
                writer.writerow({c: (row.get(c) or "") for c in CSV_COLUMNS})
        print(f"Wrote {len(results)} rows to {output_csv}")
    return results


def main():
    saida_csv = sys.argv[1] if len(sys.argv) > 1 else "dados/dados_scraping.csv"
    base_url = sys.argv[2] if len(sys.argv) > 2 else "https://dados.gov.br"
    max_reg = None
    if len(sys.argv) > 3:
        try:
            max_reg = int(sys.argv[3])
        except ValueError:
            pass
    buscar_detalhes(output_csv=saida_csv, base_url=base_url, max_registros=max_reg)


if __name__ == "__main__":
    main()
