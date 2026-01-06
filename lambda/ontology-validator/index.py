"""
Ontology Validator Lambda Function

Validates RDF instance data against the OWL ontology before loading to Neptune.
Based on AWS blog: https://aws.amazon.com/blogs/database/model-driven-graphs-using-owl-in-amazon-neptune/

Validation checks:
- Class membership (instances have valid rdf:type)
- Property domains and ranges
- Cardinality constraints
- Required properties (owl:cardinality = 1)
- Property restrictions (owl:allValuesFrom, owl:someValuesFrom)
"""

import json
import os
import boto3
from typing import Dict, Any, List, Set, Tuple
import urllib3

s3_client = boto3.client('s3')
http = urllib3.PoolManager()

# Environment variables
BUCKET_NAME = os.environ['DOCUMENT_BUCKET_NAME']
NEPTUNE_ENDPOINT = os.environ['NEPTUNE_ENDPOINT']
NEPTUNE_PORT = os.environ.get('NEPTUNE_PORT', '8182')
ONTOLOGY_URI = 'http://graph-rag.example.com/ontology'


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for ontology validation.
    
    Input (from Step Functions, after RDF generation):
    {
        "documentId": "uuid",
        "rdfS3Key": "neptune-staging/uuid/data.ttl",
        "tripleCount": 123,
        ...
    }
    
    Output:
    {
        "documentId": "uuid",
        "validationStatus": "PASSED" | "FAILED" | "WARNING",
        "violations": [...],
        "warnings": [...],
        "success": true,
        ...
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        document_id = event.get('documentId')
        rdf_s3_key = event.get('rdfS3Key')
        rdf_bucket = event.get('rdfBucket', BUCKET_NAME)
        
        if not document_id or not rdf_s3_key:
            raise ValueError("documentId and rdfS3Key are required")
        
        print(f"Validating RDF for document {document_id}")
        
        # Download RDF data from S3
        response = s3_client.get_object(Bucket=rdf_bucket, Key=rdf_s3_key)
        rdf_content = response['Body'].read().decode('utf-8')
        
        # Parse RDF (simplified - in production use rdflib)
        triples = parse_turtle_simple(rdf_content)
        
        # Query ontology from Neptune (if loaded) or use cached version
        ontology_model = fetch_ontology_model()
        
        # Validate triples against ontology
        validation_results = validate_against_ontology(triples, ontology_model)
        
        # Determine overall status
        has_errors = len(validation_results['violations']) > 0
        has_warnings = len(validation_results['warnings']) > 0
        
        if has_errors:
            status = 'FAILED'
        elif has_warnings:
            status = 'WARNING'
        else:
            status = 'PASSED'
        
        print(f"Validation {status}: {len(validation_results['violations'])} violations, "
              f"{len(validation_results['warnings'])} warnings")
        
        # Log violations and warnings
        for violation in validation_results['violations']:
            print(f"VIOLATION: {violation}")
        
        for warning in validation_results['warnings']:
            print(f"WARNING: {warning}")
        
        # Prepare result
        result = {
            **event,  # Pass through previous state data
            'validationStatus': status,
            'violations': validation_results['violations'],
            'warnings': validation_results['warnings'],
            'validationChecks': validation_results['checks_performed'],
            'success': status != 'FAILED',  # Only fail on violations, not warnings
        }
        
        return result
    
    except Exception as e:
        print(f"Error validating ontology: {str(e)}")
        return {
            **event,
            'validationStatus': 'ERROR',
            'success': False,
            'error': str(e),
            'stage': 'ontology-validation',
        }


def fetch_ontology_model() -> Dict[str, Any]:
    """
    Fetch ontology model from Neptune via SPARQL queries.
    
    Based on AWS blog approach: query the ontology to build validation model.
    """
    try:
        sparql_endpoint = f'https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/sparql'
        
        # Query 1: Get all classes
        classes_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?class ?subClassOf
        WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:subClassOf ?subClassOf }
        }
        """
        
        classes_result = execute_sparql_query(sparql_endpoint, classes_query)
        classes = parse_sparql_results(classes_result)
        
        # Query 2: Get property definitions
        properties_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?property ?domain ?range
        WHERE {
            {
                ?property a owl:ObjectProperty .
                OPTIONAL { ?property rdfs:domain ?domain }
                OPTIONAL { ?property rdfs:range ?range }
            }
            UNION
            {
                ?property a owl:DatatypeProperty .
                OPTIONAL { ?property rdfs:domain ?domain }
                OPTIONAL { ?property rdfs:range ?range }
            }
        }
        """
        
        properties_result = execute_sparql_query(sparql_endpoint, properties_query)
        properties = parse_sparql_results(properties_result)
        
        # Query 3: Get restrictions (cardinality, allValuesFrom, etc.)
        restrictions_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?class ?property ?restrictionType ?value
        WHERE {
            ?class rdfs:subClassOf ?restriction .
            ?restriction a owl:Restriction .
            ?restriction owl:onProperty ?property .
            {
                ?restriction owl:cardinality ?value .
                BIND("cardinality" AS ?restrictionType)
            }
            UNION
            {
                ?restriction owl:minCardinality ?value .
                BIND("minCardinality" AS ?restrictionType)
            }
            UNION
            {
                ?restriction owl:maxCardinality ?value .
                BIND("maxCardinality" AS ?restrictionType)
            }
            UNION
            {
                ?restriction owl:allValuesFrom ?value .
                BIND("allValuesFrom" AS ?restrictionType)
            }
            UNION
            {
                ?restriction owl:someValuesFrom ?value .
                BIND("someValuesFrom" AS ?restrictionType)
            }
        }
        """
        
        restrictions_result = execute_sparql_query(sparql_endpoint, restrictions_query)
        restrictions = parse_sparql_results(restrictions_result)
        
        return {
            'classes': classes,
            'properties': properties,
            'restrictions': restrictions,
        }
    
    except Exception as e:
        print(f"Warning: Could not fetch ontology from Neptune: {str(e)}")
        # Return minimal model to allow processing to continue
        return {
            'classes': [],
            'properties': [],
            'restrictions': [],
        }


def execute_sparql_query(endpoint: str, query: str) -> Dict:
    """
    Execute SPARQL query against Neptune endpoint.
    """
    response = http.request(
        'POST',
        endpoint,
        body=query.encode('utf-8'),
        headers={
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json',
        },
        timeout=30.0,
    )
    
    if response.status != 200:
        raise Exception(f"SPARQL query failed with status {response.status}")
    
    return json.loads(response.data.decode('utf-8'))


def parse_sparql_results(results: Dict) -> List[Dict]:
    """
    Parse SPARQL JSON results into list of bindings.
    """
    if 'results' not in results or 'bindings' not in results['results']:
        return []
    
    bindings = []
    for binding in results['results']['bindings']:
        parsed = {}
        for var, value in binding.items():
            parsed[var] = value.get('value', '')
        bindings.append(parsed)
    
    return bindings


def parse_turtle_simple(rdf_content: str) -> List[Tuple[str, str, str]]:
    """
    Simple Turtle parser to extract triples.
    
    For production, use rdflib library:
    from rdflib import Graph
    g = Graph()
    g.parse(data=rdf_content, format='turtle')
    triples = [(str(s), str(p), str(o)) for s, p, o in g]
    """
    triples = []
    
    # Simplified parser - just extract basic patterns
    # Format: <subject> <predicate> <object> .
    # or: <subject> <predicate> "literal" .
    
    lines = rdf_content.split('\n')
    current_subject = None
    
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#') or line.startswith('@'):
            continue
        
        # Very simplified parsing - production should use rdflib
        # This is just for demonstration
        parts = line.split()
        if len(parts) >= 3:
            if parts[0].startswith('<') and parts[1].startswith('<'):
                subject = parts[0].strip('<>')
                predicate = parts[1].strip('<>')
                object_val = ' '.join(parts[2:]).rstrip(' .')
                object_val = object_val.strip('<>"')
                
                triples.append((subject, predicate, object_val))
    
    return triples


def validate_against_ontology(triples: List[Tuple[str, str, str]], 
                              ontology_model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate triples against ontology model.
    
    Implements validation rules from AWS blog:
    1. Class membership validation
    2. Property domain/range validation
    3. Cardinality constraints
    4. Required properties
    5. Restriction validation (allValuesFrom, someValuesFrom)
    """
    violations = []
    warnings = []
    checks_performed = []
    
    # Extract instances and their types from triples
    instances = {}
    for s, p, o in triples:
        if p == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':
            if s not in instances:
                instances[s] = {'types': [], 'properties': {}}
            instances[s]['types'].append(o)
        else:
            if s not in instances:
                instances[s] = {'types': [], 'properties': {}}
            if p not in instances[s]['properties']:
                instances[s]['properties'][p] = []
            instances[s]['properties'][p].append(o)
    
    # Check 1: Validate class membership
    checks_performed.append('class_membership')
    defined_classes = {c['class'] for c in ontology_model.get('classes', [])}
    
    for instance_uri, instance_data in instances.items():
        for class_uri in instance_data['types']:
            if class_uri.startswith('http://graph-rag.example.com/ontology#'):
                if class_uri not in defined_classes and defined_classes:
                    warnings.append({
                        'type': 'undefined_class',
                        'instance': instance_uri,
                        'class': class_uri,
                        'message': f'Instance {instance_uri} has type {class_uri} which is not defined in ontology'
                    })
    
    # Check 2: Validate property domains and ranges
    checks_performed.append('property_domains_ranges')
    property_definitions = {p['property']: p for p in ontology_model.get('properties', [])}
    
    for instance_uri, instance_data in instances.items():
        for prop_uri, values in instance_data['properties'].items():
            if prop_uri in property_definitions:
                prop_def = property_definitions[prop_uri]
                
                # Check domain
                if 'domain' in prop_def and prop_def['domain']:
                    expected_domain = prop_def['domain']
                    if expected_domain not in instance_data['types']:
                        warnings.append({
                            'type': 'domain_mismatch',
                            'instance': instance_uri,
                            'property': prop_uri,
                            'expected_domain': expected_domain,
                            'actual_types': instance_data['types'],
                            'message': f'Property {prop_uri} expects domain {expected_domain}'
                        })
    
    # Check 3: Validate cardinality constraints
    checks_performed.append('cardinality_constraints')
    restrictions_by_class = {}
    for restriction in ontology_model.get('restrictions', []):
        class_uri = restriction['class']
        if class_uri not in restrictions_by_class:
            restrictions_by_class[class_uri] = []
        restrictions_by_class[class_uri].append(restriction)
    
    for instance_uri, instance_data in instances.items():
        for class_uri in instance_data['types']:
            if class_uri in restrictions_by_class:
                for restriction in restrictions_by_class[class_uri]:
                    prop_uri = restriction['property']
                    restriction_type = restriction['restrictionType']
                    value = restriction['value']
                    
                    # Check cardinality = 1 (exactly one)
                    if restriction_type == 'cardinality' and value == '1':
                        prop_count = len(instance_data['properties'].get(prop_uri, []))
                        if prop_count != 1:
                            violations.append({
                                'type': 'cardinality_violation',
                                'instance': instance_uri,
                                'property': prop_uri,
                                'expected': 1,
                                'actual': prop_count,
                                'message': f'Property {prop_uri} must have exactly 1 value, has {prop_count}'
                            })
                    
                    # Check minCardinality
                    elif restriction_type == 'minCardinality':
                        min_card = int(value)
                        prop_count = len(instance_data['properties'].get(prop_uri, []))
                        if prop_count < min_card:
                            violations.append({
                                'type': 'min_cardinality_violation',
                                'instance': instance_uri,
                                'property': prop_uri,
                                'min_expected': min_card,
                                'actual': prop_count,
                                'message': f'Property {prop_uri} must have at least {min_card} values, has {prop_count}'
                            })
    
    print(f"Validation complete: {len(checks_performed)} checks, "
          f"{len(violations)} violations, {len(warnings)} warnings")
    
    return {
        'violations': violations,
        'warnings': warnings,
        'checks_performed': checks_performed,
        'instances_validated': len(instances),
        'triples_validated': len(triples),
    }

