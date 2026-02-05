from pathlib import Path
from typing import List, Tuple, Optional
from rdflib import Graph
from rdflib.namespace import RDF
import pyshacl


class ValidateRdfService:
    """Service for validating RDF files using SHACL"""

    @staticmethod
    def validate_rdf(file_content: bytes, filename: Optional[str] = None) -> Tuple[bool, List[str], List[str]]:
        """
        Validate RDF file using SHACL per DCAT-BR standard.
        
        Args:
            file_content: RDF file content in bytes
            filename: File name (optional, used to detect format)
            
        Returns:
            Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
        """
        try:
            # Detect file format
            rdf_format = ValidateRdfService._detect_rdf_format(file_content, filename)
            
            # Convert bytes to string
            rdf_content = file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content
            
            # Load RDF content into rdflib Graph
            data_graph = Graph()
            parse_error = None
            parsed = False
            used_format = None
            
            # Try first with detected format
            try:
                data_graph.parse(data=rdf_content, format=rdf_format)
                # Check if Graph was populated
                if len(data_graph) > 0:
                    parsed = True
                    used_format = rdf_format
            except Exception as e:
                parse_error = e
                # If failed, try other common formats in order of probability
                formats_to_try = ['turtle', 'xml', 'json-ld', 'ntriples', 'n3']
                # Remove already tried format from list
                if rdf_format in formats_to_try:
                    formats_to_try.remove(rdf_format)
                
                for fmt in formats_to_try:
                    try:
                        data_graph = Graph()
                        data_graph.parse(data=rdf_content, format=fmt)
                        # Check if Graph was populated
                        if len(data_graph) > 0:
                            parsed = True
                            used_format = fmt
                            break
                    except Exception as parse_ex:
                        parse_error = parse_ex
                        continue
            
            if not parsed:
                return False, [f"Error parsing RDF file. Detected format: {rdf_format}. Error: {str(parse_error)}"], []
            
            # Verificar se o Graph está vazio
            if len(data_graph) == 0:
                return False, ["O arquivo RDF está vazio ou não contém dados válidos"], []
            
            # Get path to SHACL files
            shacl_path = ValidateRdfService._get_shacl_path()
            if not shacl_path or not shacl_path.exists():
                return False, ["SHACL files directory not found"], []
            
            # Load SHACL files in correct order into a single Graph
            shapes_files = [
                shacl_path / "shapes.ttl",
                shacl_path / "range.ttl",
                shacl_path / "shapes_recommended.ttl",
                shacl_path / "mdr-vocabularies.shape.ttl",
            ]
            
            # Check which files exist
            existing_shapes_files = [f for f in shapes_files if f.exists()]
            
            if not existing_shapes_files:
                return False, ["No SHACL files found"], []
            
            # Load all SHACL files into a single Graph
            shacl_graph = Graph()
            for shape_file in existing_shapes_files:
                try:
                    shacl_graph.parse(str(shape_file), format='turtle')
                except Exception as e:
                    return False, [f"Error loading SHACL file {shape_file.name}: {str(e)}"], []
            
            # Ontology files (imports) - also load into Graph
            ont_graph = Graph()
            imports_file = shacl_path / "imports.ttl"
            mdr_imports_file = shacl_path / "mdr_imports.ttl"
            
            if imports_file.exists():
                try:
                    ont_graph.parse(str(imports_file), format='turtle')
                except Exception as e:
                    pass  # Non-critical if it fails
            if mdr_imports_file.exists():
                try:
                    ont_graph.parse(str(mdr_imports_file), format='turtle')
                except Exception as e:
                    pass  # Non-critical if it fails
            
            # Use None if ont_graph is empty
            final_ont_graph = ont_graph if len(ont_graph) > 0 else None
            
            # Perform SHACL validation
            try:
                conforms, v_graph, v_text = pyshacl.validate(
                    data_graph,
                    shacl_graph=shacl_graph,
                    ont_graph=final_ont_graph,
                    inference='rdfs',
                    abort_on_first=False,
                    allow_infos=True,
                    allow_warnings=True,
                    meta_shacl=False,
                    advanced=False,
                    js=False
                )
                
                # Process validation results
                errors, warnings = ValidateRdfService._parse_validation_results(v_graph, v_text)
                
                return conforms, errors, warnings
                
            except Exception as e:
                return False, [f"Error during SHACL validation: {str(e)}"], []
                
        except UnicodeDecodeError:
            return False, ["Error decoding file. Ensure it is UTF-8 encoded"], []
        except Exception as e:
            return False, [f"RDF validation error: {str(e)}"], []

    @staticmethod
    def _detect_rdf_format(content: bytes, filename: Optional[str] = None) -> str:
        """Detect RDF format based on file extension or content."""
        if filename:
            filename_lower = filename.lower()
            if filename_lower.endswith('.ttl'):
                return 'turtle'
            elif filename_lower.endswith('.rdf') or filename_lower.endswith('.xml'):
                return 'xml'
            elif filename_lower.endswith('.jsonld') or filename_lower.endswith('.json'):
                return 'json-ld'
            elif filename_lower.endswith('.nt'):
                return 'ntriples'
            elif filename_lower.endswith('.n3'):
                return 'n3'
        
        # Try to detect from content
        content_str = content.decode('utf-8', errors='ignore')[:500]
        if content_str.strip().startswith('<?xml') or '<rdf:RDF' in content_str:
            return 'xml'
        elif content_str.strip().startswith('@prefix') or content_str.strip().startswith('PREFIX'):
            return 'turtle'
        elif '{' in content_str and '@context' in content_str:
            return 'json-ld'
        
        # Default: try turtle first
        return 'turtle'

    @staticmethod
    def _get_shacl_path() -> Optional[Path]:
        """Get path to SHACL files."""
        # Get absolute path of current file
        current_file = Path(__file__).resolve()
        
        # Possible paths, ordered by priority
        possible_paths = [
            current_file.parent.parent / "DCAT-BR" / "docs" / "shacl" / "1.0",
            Path.cwd() / "DCAT-BR" / "docs" / "shacl" / "1.0",
            Path.cwd().parent / "DCAT-BR" / "docs" / "shacl" / "1.0",
            # 3. Caminho relativo simples (se executado da raiz do projeto)
            Path("DCAT-BR") / "docs" / "shacl" / "1.0",
            current_file.parent / "DCAT-BR" / "docs" / "shacl" / "1.0",
        ]
        
        # Tentar cada caminho
        for path in possible_paths:
            try:
                resolved_path = path.resolve()
                if resolved_path.exists() and resolved_path.is_dir():
                    shapes_file = resolved_path / "shapes.ttl"
                    if shapes_file.exists() and shapes_file.is_file():
                        return resolved_path
            except (OSError, ValueError) as e:
                # Ignore path errors and continue trying
                continue
        
        return None

    @staticmethod
    def _parse_validation_results(v_graph: Optional[Graph], v_text: Optional[str]) -> Tuple[List[str], List[str]]:
        """
        Process SHACL validation results and extract errors and warnings.
        
        Args:
            v_graph: RDF graph with validation report
            v_text: Validation report text
            
        Returns:
            Tuple[List[str], List[str]]: (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Process validation graph if available
        if v_graph:
            try:
                from rdflib import Namespace
                SH = Namespace("http://www.w3.org/ns/shacl#")
                
                # Buscar violações (sh:Violation)
                violations = list(v_graph.subjects(RDF.type, SH.Violation))
                for violation in violations:
                    # Get violation message
                    message = v_graph.value(violation, SH.resultMessage)
                    focus_node = v_graph.value(violation, SH.focusNode)
                    result_path = v_graph.value(violation, SH.resultPath)
                    
                    error_msg = str(message) if message else "Violation found"
                    if focus_node:
                        error_msg += f" at {focus_node}"
                    if result_path:
                        error_msg += f" (property: {result_path})"
                    
                    errors.append(error_msg)
                
                # Find warnings (sh:Warning)
                warning_nodes = list(v_graph.subjects(RDF.type, SH.Warning))
                for warning in warning_nodes:
                    message = v_graph.value(warning, SH.resultMessage)
                    focus_node = v_graph.value(warning, SH.focusNode)
                    
                    warning_msg = str(message) if message else "Warning found"
                    if focus_node:
                        warning_msg += f" at {focus_node}"
                    
                    warnings.append(warning_msg)
                    
            except Exception as e:
                # If graph processing fails, use text
                pass
        
        # Process report text if graph did not provide sufficient information
        if v_text and (not errors and not warnings):
            lines = v_text.split('\n')
            for line in lines:
                line_lower = line.lower()
                if 'violation' in line_lower or 'error' in line_lower:
                    if line.strip():
                        errors.append(line.strip())
                elif 'warning' in line_lower:
                    if line.strip():
                        warnings.append(line.strip())
        
        return errors, warnings

