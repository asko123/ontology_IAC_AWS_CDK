# Graph RAG Ontology Guide

## Overview

This document explains the OWL (Web Ontology Language) ontology used in the Graph RAG system, based on AWS best practices from the blog post: [Model-driven graphs using OWL in Amazon Neptune](https://aws.amazon.com/blogs/database/model-driven-graphs-using-owl-in-amazon-neptune/).

## Why Use OWL Ontologies?

### Benefits

1. **Formal Model**: OWL provides a formal, machine-readable specification of your data model
2. **Validation**: Automatically validate instance data against constraints
3. **Inference**: Reasoners can derive new facts from existing data
4. **Interoperability**: Standard W3C format enables integration with other systems
5. **Flexibility**: Define complex logical constraints beyond simple schemas
6. **Documentation**: Self-documenting model with rdfs:label and rdfs:comment

### OWL vs. Traditional Schema

| Feature | Relational Schema | OWL Ontology |
|---------|-------------------|--------------|
| Structure | Rigid tables | Flexible graph |
| Validation | Database constraints | Logical rules |
| Inference | Limited | Extensive |
| Evolution | Schema migrations | Additive changes |
| Interoperability | Custom | W3C standard |

## Ontology Structure

Our Graph RAG ontology (`ontologies/graph-rag-ontology.ttl`) defines the following structure:

### Core Classes

```turtle
:Document
  ├── :Policy
  ├── :Standard
  ├── :Report
  └── :Specification

:TextChunk

:Entity
  ├── :Person
  ├── :Organization
  ├── :Location
  └── :Concept

:Keyword
:Author
:Embedding
```

### Key Relationships

```
Document --hasChunk--> TextChunk
Document --hasKeyword--> Keyword
Document --hasAuthor--> Author
Document --hasType--> DocumentType

TextChunk --mentions--> Entity
TextChunk --hasEmbedding--> Embedding
TextChunk --partOf--> Document

Entity --relatedTo--> Entity
Entity --coOccursWith--> Entity
```

## OWL Features Used

### 1. Class Definitions

```turtle
:Document rdf:type owl:Class ;
    rdfs:label "Document"@en ;
    rdfs:comment "A document uploaded to the Graph RAG system."@en ;
    rdfs:subClassOf foaf:Document .
```

### 2. Property Definitions

#### Object Properties (relationships between instances)

```turtle
:hasChunk rdf:type owl:ObjectProperty ;
    rdfs:label "has chunk"@en ;
    rdfs:domain :Document ;
    rdfs:range :TextChunk .
```

#### Datatype Properties (literal values)

```turtle
:hasFileName rdf:type owl:DatatypeProperty ;
    rdfs:domain :Document ;
    rdfs:range xsd:string .
```

### 3. Cardinality Constraints

Ensure specific properties appear exactly once, at least once, or at most once:

```turtle
:Document rdfs:subClassOf 
    [ rdf:type owl:Restriction ;
      owl:onProperty :hasId ;
      owl:cardinality "1"^^xsd:nonNegativeInteger  # Exactly 1
    ] ,
    [ rdf:type owl:Restriction ;
      owl:onProperty :hasChunk ;
      owl:minCardinality "1"^^xsd:nonNegativeInteger  # At least 1
    ] .
```

**Validation Rules:**
- `owl:cardinality "1"` - Exactly one value required
- `owl:minCardinality "1"` - At least one value required
- `owl:maxCardinality "1"` - At most one value allowed

### 4. Property Characteristics

#### Symmetric Property

```turtle
:relatedTo rdf:type owl:SymmetricProperty ;
    rdfs:comment "If A relatedTo B, then B relatedTo A" .
```

#### Inverse Properties

```turtle
:hasChunk owl:inverseOf :partOf .
# If Document hasChunk Chunk, then Chunk partOf Document
```

### 5. Integration with Standard Vocabularies

```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

:Document rdfs:subClassOf foaf:Document .
:Person rdfs:subClassOf foaf:Person .
:Concept rdfs:subClassOf skos:Concept .
```

## Validation Rules

The ontology validator Lambda (`lambda/ontology-validator/`) checks:

### 1. Class Membership

```sparql
# Check: All instances have valid rdf:type
SELECT ?instance ?type
WHERE {
    ?instance rdf:type ?type .
    FILTER NOT EXISTS { ?type a owl:Class }
}
```

### 2. Property Domain/Range

```sparql
# Check: hasAuthor only used on Documents
SELECT ?subject
WHERE {
    ?subject :hasAuthor ?author .
    FILTER NOT EXISTS { ?subject a :Document }
}
```

### 3. Cardinality Constraints

```python
# Check: Document must have exactly 1 hasId
violations = []
for doc in documents:
    id_count = count(doc, :hasId)
    if id_count != 1:
        violations.append(f"{doc} has {id_count} IDs, expected 1")
```

### 4. Required Properties

```sparql
# Check: All Documents have required properties
SELECT ?doc
WHERE {
    ?doc a :Document .
    FILTER NOT EXISTS { ?doc :hasId ?id }
}
```

## Loading the Ontology into Neptune

### Option 1: Bulk Load via S3

```bash
# Upload ontology to S3
aws s3 cp ontologies/graph-rag-ontology.ttl s3://your-bucket/ontologies/

# Load into Neptune
aws neptune-data create-bulk-load \
  --source s3://your-bucket/ontologies/graph-rag-ontology.ttl \
  --format turtle \
  --s3-bucket your-bucket \
  --role-arn arn:aws:iam::ACCOUNT:role/NeptuneBulkLoadRole
```

### Option 2: Direct SPARQL INSERT

```sparql
# Read ontology file and insert
LOAD <http://graph-rag.example.com/ontology>
```

### Option 3: Automated via CDK

The CDK stack automatically loads the ontology on first deployment (see implementation below).

## Querying with the Ontology

### Example 1: Find All Documents with Required Properties

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?doc ?id ?fileName ?createdAt
WHERE {
    ?doc rdf:type :Document ;
         :hasId ?id ;
         :hasFileName ?fileName ;
         :createdAt ?createdAt .
}
```

### Example 2: Find Documents Missing Required Chunks

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?doc
WHERE {
    ?doc rdf:type :Document .
    FILTER NOT EXISTS { ?doc :hasChunk ?chunk }
}
```

### Example 3: Find Co-occurring Entities

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?entity1 ?entity2 ?chunk
WHERE {
    ?chunk :mentions ?entity1 ;
           :mentions ?entity2 .
    FILTER(?entity1 != ?entity2)
}
```

### Example 4: Traverse Relationships with Inference

```sparql
# Using RDFS inference, partOf is automatically inferred from hasChunk
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?chunk ?doc
WHERE {
    ?chunk :partOf ?doc .  # Inferred from inverse property
}
```

## Extending the Ontology

### Adding New Classes

```turtle
:TechnicalSpecification rdf:type owl:Class ;
    rdfs:label "Technical Specification"@en ;
    rdfs:subClassOf :Specification ;
    rdfs:comment "A technical specification document with detailed requirements."@en .
```

### Adding New Properties

```turtle
:hasVersion rdf:type owl:DatatypeProperty ;
    rdfs:label "has version"@en ;
    rdfs:domain :Document ;
    rdfs:range xsd:string ;
    rdfs:comment "Version identifier of the document."@en .
```

### Adding Restrictions

```turtle
:TechnicalSpecification rdfs:subClassOf
    [ rdf:type owl:Restriction ;
      owl:onProperty :hasVersion ;
      owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

## Best Practices

### 1. Use Standard Vocabularies

Leverage existing W3C vocabularies instead of reinventing:
- **FOAF**: For people and organizations
- **Dublin Core**: For metadata (creator, date, title)
- **SKOS**: For concepts and taxonomies
- **Schema.org**: For common entities

### 2. Define Clear Hierarchies

```turtle
:Entity              # Abstract base class
  ├── :Person       # Concrete subclass
  ├── :Organization
  └── :Location
```

### 3. Document Thoroughly

```turtle
:hasChunk rdfs:label "has chunk"@en ;
    rdfs:comment "Relates a document to its text chunks. Each document must have at least one chunk for processing."@en ;
    rdfs:seeAlso <https://docs.example.com/chunking> .
```

### 4. Version Your Ontology

```turtle
<http://graph-rag.example.com/ontology> rdf:type owl:Ontology ;
    owl:versionInfo "1.0" ;
    dcterms:modified "2025-01-05"^^xsd:date ;
    owl:priorVersion <http://graph-rag.example.com/ontology/0.9> .
```

### 5. Test with Examples

Include example instances in the ontology file for validation testing:

```turtle
:examplePolicy rdf:type :Document , :Policy ;
    :hasId "example-123" ;
    :hasFileName "test-policy.pdf" ;
    :createdAt "2025-01-05T10:00:00Z"^^xsd:dateTime .
```

## Integration with Processing Pipeline

### Pipeline Flow with Ontology

```
1. Document Upload
   ↓
2. Parse Document
   ↓
3. Generate RDF (conforming to ontology) ← Uses ontology classes/properties
   ↓
4. **Validate RDF** ← ontology-validator Lambda
   ↓
5. Load to Neptune (if valid)
   ↓
6. Query with ontology-aware SPARQL
```

### RDF Generator Updates

The `lambda/rdf-generator/` now uses ontology-defined classes and properties:

**Before (ad-hoc):**
```turtle
<doc123> <http://example.com/has-name> "test.pdf" .
```

**After (ontology-conformant):**
```turtle
@prefix : <http://graph-rag.example.com/ontology#> .

<doc123> rdf:type :Document ;
    :hasFileName "test.pdf" ;
    :hasId "doc123" ;
    :createdAt "2025-01-05T10:00:00Z"^^xsd:dateTime .
```

## Reasoning and Inference

### Enable RDFS Reasoning in Neptune

Neptune supports RDFS inference. Enable it when querying:

```sparql
# Query with inference
SELECT ?chunk ?doc
WHERE {
    ?chunk :partOf ?doc .  # Inferred from inverse of :hasChunk
}
```

### Common Inferences

1. **Inverse Properties**: `hasChunk` ↔ `partOf`
2. **Subclass Hierarchy**: `:Policy rdf:type :Document` inferred from `:Policy rdfs:subClassOf :Document`
3. **Transitive Properties**: If defined, e.g., `:subOrgOf owl:TransitiveProperty`
4. **Co-occurrence**: Entities in same chunk are related

### External Reasoners

For advanced OWL reasoning (OWL-DL, OWL-Full):
- Use **owlrl** library in Python
- Use **Apache Jena** with OWL reasoner
- Use **Protégé** for ontology development and validation

## Troubleshooting

### Issue: Validation Fails with "Undefined Class"

**Cause:** Instance uses class not defined in ontology

**Solution:**
```turtle
# Add to ontology
:YourNewClass rdf:type owl:Class ;
    rdfs:label "Your New Class"@en .
```

### Issue: Cardinality Violation

**Cause:** Instance has wrong number of property values

**Solution:** Ensure instance data matches restrictions:
```turtle
# Ontology requires exactly 1
:Document rdfs:subClassOf [ owl:onProperty :hasId ; owl:cardinality "1" ] .

# Instance must have exactly 1
:myDoc :hasId "doc-123" .  # ✓ Valid
:myDoc :hasId "doc-123" , "doc-456" .  # ✗ Invalid
```

### Issue: Domain/Range Mismatch

**Cause:** Property used on wrong class

**Solution:** Check property domain:
```turtle
:hasAuthor rdfs:domain :Document .

# Valid
:myDoc :hasAuthor :johnDoe .

# Invalid
:myChunk :hasAuthor :johnDoe .  # Chunk is not a Document
```

## Resources

- **AWS Blog**: [Model-driven graphs using OWL in Amazon Neptune](https://aws.amazon.com/blogs/database/model-driven-graphs-using-owl-in-amazon-neptune/)
- **GitHub Example**: [amazon-neptune-ontology-example-blog](https://github.com/aws-samples/amazon-neptune-ontology-example-blog)
- **W3C OWL Specification**: https://www.w3.org/TR/owl2-overview/
- **W3C Organizational Ontology**: https://www.w3.org/TR/vocab-org/
- **FOAF Vocabulary**: http://xmlns.com/foaf/spec/
- **Dublin Core**: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- **Neptune SPARQL**: https://docs.aws.amazon.com/neptune/latest/userguide/sparql-ref.html

## Next Steps

1. ✅ Review the ontology file: `ontologies/graph-rag-ontology.ttl`
2. ✅ Test validation with example instances
3. ✅ Extend ontology for your domain-specific needs
4. ✅ Deploy updated CDK stack with validation Lambda
5. ✅ Query Neptune using ontology-aware SPARQL
6. Consider adding OWL reasoning for advanced inference

