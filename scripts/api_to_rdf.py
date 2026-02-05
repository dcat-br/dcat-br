from typing import Dict, Any
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import DCAT, FOAF, DCTERMS, XSD, SKOS
from utils.vocabularies import (
    freq_to_iri, sei_to_iri, formato_to_iri, 
    tipo_recurso_to_iri, theme_to_iri, licenca_to_iri
)
from utils.date_utils import normalize_date
import os
from dotenv import load_dotenv

load_dotenv()

class ApiToRdfService:
    """Service for api to rdf business logic"""
    
    def _get_extra_value(self, data: Dict[str, Any], key: str) -> Any:
        """Extract value from extras array by key (for compatibility with legacy API)."""
        # First try at root level (legacy API)
        if key in data:
            return data[key]
        # Then try in extras (new API)
        extras = data.get("extras", [])
        if not extras:
            return None
        for extra in extras:
            if extra.get("key") == key:
                return extra.get("value")
        return None
    
    async def api_to_rdf(self, data: Dict[str, Any]) -> str:
        """
        Convert API data to DCAT-BR RDF/Turtle format
        
        Args:
            data: Dictionary containing the dataset information
            
        Returns:
            String containing the RDF in Turtle format
        """
        g = Graph()
        
        # Define Namespaces
        DCATBR = Namespace("http://purl.org/dcat-br/")
        VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
        
        # Bind Namespaces
        g.bind("dcat", DCAT)
        g.bind("dct", DCTERMS)
        g.bind("foaf", FOAF)
        g.bind("dcatbr", DCATBR)
        g.bind("vcard", VCARD)
        g.bind("skos", SKOS)
        g.bind("xsd", XSD)
        
        # Define dcat:version explicitly (not in standard DCAT namespace in rdflib)
        DCAT_VERSION = URIRef("http://www.w3.org/ns/dcat#version")
        
        # Dataset URI
        dataset_name = data.get("nome", data.get("name", data.get("id")))
        base_uri = f"{os.getenv('DADOS_GOV_BR_API_URL')}/{dataset_name}"
        dataset_uri = URIRef(base_uri)
        
        # Add Dataset Type
        g.add((dataset_uri, RDF.type, DCAT.Dataset))
        
        # Basic Properties
        if data.get("id"):
            g.add((dataset_uri, DCTERMS.identifier, Literal(data["id"])))
            
        # Title - legacy uses "titulo", new uses "title"
        titulo = data.get("titulo") or data.get("title")
        if titulo:
            g.add((dataset_uri, DCTERMS.title, Literal(titulo, lang="pt-BR")))
            
        # Description - legacy uses "descricao", new uses "notes"
        descricao = data.get("descricao") or data.get("notes")
        if descricao:
            g.add((dataset_uri, DCTERMS.description, Literal(descricao, lang="pt-BR")))
            
        # Accrual periodicity - legacy at root level, new in extras
        periodicidade = data.get("periodicidade") or self._get_extra_value(data, "periodicidade")
        if periodicidade:
            # Convert frequency to IRI using VCR-FR vocabulary
            freq_iri = freq_to_iri(periodicidade)
            if freq_iri:
                freq_uri = URIRef(freq_iri)
                g.add((dataset_uri, DCTERMS.accrualPeriodicity, freq_uri))
                # Add explicit statements for SHACL validation
                g.add((freq_uri, RDF.type, DCTERMS.Frequency))
                g.add((freq_uri, RDF.type, SKOS.Concept))
                g.add((freq_uri, SKOS.inScheme, URIRef("https://dcat-br.github.io/dcat-br/docs/vocabularies/VCR-FR")))
            else:
                # Fallback: use as literal if not found in vocabulary
                g.add((dataset_uri, DCTERMS.accrualPeriodicity, Literal(periodicidade)))
        
        # Spatial coverage
        cobertura_espacial = data.get("coberturaEspacial") or self._get_extra_value(data, "coberturaEspacial")
        if cobertura_espacial and cobertura_espacial != "-" and cobertura_espacial is not None:
            g.add((dataset_uri, DCTERMS.spatial, Literal(cobertura_espacial)))

        # Legal observance (access rights)
        observancia_legal = data.get("observanciaLegal") or self._get_extra_value(data, "observanciaLegal")
        if observancia_legal:
            # Convert to IRI using SEI vocabulary
            sei_iri = sei_to_iri(observancia_legal)
            if sei_iri:
                sei_uri = URIRef(sei_iri)
                g.add((dataset_uri, DCTERMS.accessRights, sei_uri))
                # Add explicit statements for SHACL validation
                g.add((sei_uri, RDF.type, DCTERMS.RightsStatement))
                g.add((sei_uri, RDF.type, SKOS.Concept))
                g.add((sei_uri, SKOS.inScheme, URIRef("https://dcat-br.github.io/dcat-br/docs/vocabularies/SEI/esquema")))
        
        # Catalog date - legacy uses "dataCatalogacao", new uses "metadata_created"
        data_catalogacao = data.get("dataCatalogacao") or data.get("metadata_created")
        if data_catalogacao:
            # Normalize and convert to xsd:date
            normalized_date = normalize_date(data_catalogacao)
            if normalized_date:
                g.add((dataset_uri, DCTERMS.issued, Literal(normalized_date, datatype=XSD.date)))
             
        # Last metadata update - legacy uses "dataUltimaAtualizacaoMetadados"
        metadata_modified = data.get("dataUltimaAtualizacaoMetadados") or data.get("metadata_modified")
        if metadata_modified:
            # Normalize and convert to xsd:date
            normalized_date = normalize_date(metadata_modified)
            if normalized_date:
                g.add((dataset_uri, DCTERMS.modified, Literal(normalized_date, datatype=XSD.date)))
        
        # License - legacy uses "licenca", new uses "license_id"
        license_id = data.get("licenca") or data.get("license_id")
        if license_id:
            if license_id.startswith("http://") or license_id.startswith("https://"):
                g.add((dataset_uri, DCTERMS.license, URIRef(license_id)))
            else:
                # Try to convert using VCR-LU vocabulary
                licenca_iri = licenca_to_iri(license_id)
                if licenca_iri:
                    g.add((dataset_uri, DCTERMS.license, URIRef(licenca_iri)))
             
        # Contact Point - legacy uses "emailResponsavel", new uses "maintainer_email"
        maintainer_email = data.get("emailResponsavel") or data.get("maintainer_email")
        if maintainer_email:
            contact_node = BNode()
            g.add((dataset_uri, DCAT.contactPoint, contact_node))
            g.add((contact_node, RDF.type, VCARD.Kind))
            g.add((contact_node, VCARD.hasEmail, URIRef(f"mailto:{maintainer_email}")))

        # Publisher - legacy uses "responsavel", new uses "maintainer"
        maintainer = data.get("responsavel") or data.get("maintainer")
        if maintainer:
            publisher_node = BNode()
            g.add((dataset_uri, DCTERMS.publisher, publisher_node))
            g.add((publisher_node, RDF.type, FOAF.Agent))
            g.add((publisher_node, RDF.type, FOAF.Organization))
            g.add((publisher_node, FOAF.name, Literal(maintainer)))
            
            if maintainer_email:
                g.add((publisher_node, FOAF.mbox, URIRef(f"mailto:{maintainer_email}")))

        # Creator - legacy uses "organizacao" as string, new uses "organization" as object
        organizacao = data.get("organizacao")
        if organizacao:
            if isinstance(organizacao, str):
                org_name = organizacao
            else:
                org_name = organizacao.get("title") or organizacao.get("display_name") or organizacao.get("name")
        else:
            organization = data.get("organization", {})
            org_name = organization.get("title") or organization.get("display_name") or organization.get("name")
        
        if org_name:
            creator_node = BNode()
            g.add((dataset_uri, DCTERMS.creator, creator_node))
            g.add((creator_node, RDF.type, FOAF.Agent))
            g.add((creator_node, RDF.type, FOAF.Organization))
            g.add((creator_node, FOAF.name, Literal(org_name)))

        # Version - legacy uses "versao", new uses "version"
        versao = data.get("versao") or data.get("version")
        if versao:
            g.add((dataset_uri, DCAT_VERSION, Literal(versao)))

        # DCAT-BR specific properties
        dados_raca_etnia = data.get("dadosRacaEtnia")
        if dados_raca_etnia is None:
            dados_raca_etnia = self._get_extra_value(data, "dadosRacaEtnia")
        if dados_raca_etnia is not None:
            # Convert string "true"/"false" or boolean to boolean
            if isinstance(dados_raca_etnia, bool):
                is_true = dados_raca_etnia
            else:
                is_true = str(dados_raca_etnia).lower() == "true"
            g.add((dataset_uri, DCATBR.dadosRacaEtnia, Literal(is_true, datatype=XSD.boolean)))
        
        dados_genero = data.get("dadosGenero")
        if dados_genero is None:
            dados_genero = self._get_extra_value(data, "dadosGenero")
        if dados_genero is not None:
            # Convert string "true"/"false" or boolean to boolean
            if isinstance(dados_genero, bool):
                is_true = dados_genero
            else:
                is_true = str(dados_genero).lower() == "true"
            g.add((dataset_uri, DCATBR.dadosGenero, Literal(is_true, datatype=XSD.boolean)))

        # Spatial granularity
        granularidade_espacial = data.get("granularidadeEspacial") or self._get_extra_value(data, "granularidadeEspacial")
        if granularidade_espacial:
            g.add((dataset_uri, DCAT.spatialResolutionInMeters, Literal(granularidade_espacial)))

        # Tags/Keywords
        for tag in data.get("tags", []):
            if tag.get("name"):
                g.add((dataset_uri, DCAT.keyword, Literal(tag["name"])))
        
        # Temporal coverage (dcat:startDate and dcat:endDate)
        cobertura_temporal_inicio = data.get("coberturaTemporalInicio") or self._get_extra_value(data, "coberturaTemporalInicio")
        if cobertura_temporal_inicio:
            normalized_start = normalize_date(cobertura_temporal_inicio)
            if normalized_start:
                g.add((dataset_uri, DCAT.startDate, Literal(normalized_start, datatype=XSD.date)))
        
        cobertura_temporal_fim = data.get("coberturaTemporalFim") or self._get_extra_value(data, "coberturaTemporalFim")
        if cobertura_temporal_fim:
            normalized_end = normalize_date(cobertura_temporal_fim)
            if normalized_end:
                g.add((dataset_uri, DCAT.endDate, Literal(normalized_end, datatype=XSD.date)))
        
        # Themes - legacy uses "temas", new uses "groups"
        temas = data.get("temas", []) or data.get("groups", [])
        for tema in temas:
            theme_value = tema.get("name") or tema.get("title")
            if theme_value:
                # Convert theme to IRI using themes vocabulary
                theme_iri = theme_to_iri(theme_value)
                if theme_iri:
                    theme_uri = URIRef(theme_iri)
                    g.add((dataset_uri, DCAT.theme, theme_uri))
                    # Add explicit statements for SHACL validation
                    g.add((theme_uri, RDF.type, SKOS.Concept))
                    g.add((theme_uri, SKOS.inScheme, URIRef("https://dcat-br.github.io/dcat-br/docs/vocabularies/themes/")))
        # Distributions - legacy uses "recursos", new uses "resources"
        recursos = data.get("recursos", []) or data.get("resources", [])
        for resource in recursos:
            resource_id = resource.get("id", "unknown")
            distribution_uri = URIRef(f"{base_uri}/resource/{resource_id}")
            
            g.add((dataset_uri, DCAT.distribution, distribution_uri))
            g.add((distribution_uri, RDF.type, DCAT.Distribution))
            
            # Title - may be in name, titulo or recursoApiView/recursoForm
            resource_title = resource.get("name") or resource.get("titulo") or resource.get("recursoApiView", {}).get("titulo") or resource.get("recursoForm", {}).get("titulo")
            if resource_title:
                g.add((distribution_uri, DCTERMS.title, Literal(resource_title, lang="pt-BR")))
                
            # Description - may be in description, descricao or recursoApiView/recursoForm
            resource_description = resource.get("description") or resource.get("descricao") or resource.get("recursoApiView", {}).get("descricao") or resource.get("recursoForm", {}).get("descricao")
            if resource_description:
                g.add((distribution_uri, DCTERMS.description, Literal(resource_description, lang="pt-BR")))
                
            # Format - may be in format, formato or recursoApiView/recursoForm
            resource_format = resource.get("format") or resource.get("formato") or resource.get("recursoApiView", {}).get("formato") or resource.get("recursoForm", {}).get("formato")
            if resource_format:
                # Convert format to IRI (IANA Media Type)
                formato_iri = formato_to_iri(resource_format)
                if formato_iri:
                    formato_uri = URIRef(formato_iri)
                    g.add((distribution_uri, DCTERMS.format, formato_uri))
                    g.add((distribution_uri, DCAT.mediaType, formato_uri))
                    # Add explicit statements for SHACL validation
                    g.add((formato_uri, RDF.type, DCTERMS.MediaType))
                    MediaTypeOrExtent = URIRef("http://purl.org/dc/terms/MediaTypeOrExtent")
                    g.add((formato_uri, RDF.type, MediaTypeOrExtent))
                    g.add((formato_uri, RDF.type, SKOS.Concept))
                    g.add((formato_uri, SKOS.inScheme, URIRef("https://dcat-br.github.io/dcat-br/docs/vocabularies/formato/esquema")))
                else:
                    # Fallback: use as literal if not found in vocabulary
                    g.add((distribution_uri, DCTERMS.format, Literal(resource_format)))
                    g.add((distribution_uri, DCAT.mediaType, Literal(resource_format)))

            # URL - may be in url, link or recursoApiView/recursoForm
            resource_url = resource.get("url") or resource.get("link") or resource.get("recursoApiView", {}).get("link") or resource.get("recursoForm", {}).get("link")
            if resource_url:
                g.add((distribution_uri, DCAT.accessURL, URIRef(resource_url)))
                # Assuming link is also download URL for files
                g.add((distribution_uri, DCAT.downloadURL, URIRef(resource_url)))
                
            # Catalog date - may be in created, dataCatalogacao or recursoApiView/recursoForm
            resource_created = resource.get("created") or resource.get("dataCatalogacao") or resource.get("recursoApiView", {}).get("dataCatalogacao") or resource.get("recursoForm", {}).get("dataCatalogacao")
            if resource_created:
                # Normalize and convert to xsd:date
                normalized_date = normalize_date(resource_created)
                if normalized_date:
                    g.add((distribution_uri, DCTERMS.issued, Literal(normalized_date, datatype=XSD.date)))
                
            # Type - may be in tipo or recursoApiView/recursoForm
            resource_type = resource.get("tipo") or resource.get("recursoApiView", {}).get("tipo") or resource.get("recursoForm", {}).get("tipo")
            if resource_type:
                # Convert resource type to IRI
                tipo_iri = tipo_recurso_to_iri(resource_type)
                if tipo_iri:
                    tipo_uri = URIRef(tipo_iri)
                    g.add((distribution_uri, DCTERMS.type, tipo_uri))
                    # Add explicit statements for SHACL validation
                    g.add((tipo_uri, RDF.type, SKOS.Concept))
                    g.add((tipo_uri, SKOS.inScheme, URIRef("https://dcat-br.github.io/dcat-br/docs/vocabularies/tipo-recurso/")))
                else:
                    # Fallback: use as literal if not found in vocabulary
                    g.add((distribution_uri, DCTERMS.type, Literal(resource_type)))
            
            # Last file update - may be in last_modified, dataUltimaAtualizacaoArquivo or recursoApiView/recursoForm
            # Ignore values indicating unavailability
            resource_modified = resource.get("last_modified") or resource.get("dataUltimaAtualizacaoArquivo") or resource.get("recursoApiView", {}).get("dataUltimaAtualizacaoArquivo") or resource.get("recursoForm", {}).get("dataUltimaAtualizacaoArquivo")
            if resource_modified and not resource_modified.startswith("Indisponível"):
                # Normalize and convert to xsd:date
                normalized_date = normalize_date(resource_modified)
                if normalized_date:
                    g.add((distribution_uri, DCTERMS.modified, Literal(normalized_date, datatype=XSD.date)))

            # Size - may be in size, tamanho or recursoApiView/recursoForm
            resource_size = resource.get("size") or resource.get("tamanho") or resource.get("recursoApiView", {}).get("tamanho") or resource.get("recursoForm", {}).get("tamanho")
            if resource_size is not None:
                # byteSize should be xsd:decimal; only add if size > 0
                try:
                    tamanho = float(resource_size)
                    if tamanho > 0:
                        g.add((distribution_uri, DCAT.byteSize, Literal(tamanho, datatype=XSD.decimal)))
                except (ValueError, TypeError):
                    # If conversion fails and not 0, try adding as literal
                    if resource_size and str(resource_size).strip() != "0":
                        g.add((distribution_uri, DCAT.byteSize, Literal(resource_size)))
        
        rdf = g.serialize(format="turtle")
        print(rdf)
        return rdf
    
