# Graph RAG Ontology - Quick Reference Card

## Namespace

```turtle
@prefix : <http://graph-rag.example.com/ontology#> .
```

## Core Classes

| Class | Description | Required Properties |
|-------|-------------|---------------------|
| `:Document` | Uploaded document | `:hasId`, `:hasFileName`, `:createdAt`, `:hasChunk` (≥1) |
| `:TextChunk` | Text segment | `:hasChunkId`, `:hasText`, `:hasStartPosition` |
| `:Entity` | Extracted entity | `:hasValue` |
| `:Keyword` | Document keyword | `:hasValue` |
| `:Author` | Document author | `:hasName` |
| `:Embedding` | Vector embedding | `:hasVector`, `:hasDimensions`, `:generatedBy` |

## Document Type Subclasses

```
:DocumentType
  ├── :Policy
  ├── :Standard
  ├── :Report
  └── :Specification
```

## Entity Subclasses

```
:Entity
  ├── :Person (also foaf:Person)
  ├── :Organization (also foaf:Organization)
  ├── :Location
  └── :Concept (also skos:Concept)
```

## Object Properties (Relationships)

| Property | Domain | Range | Description |
|----------|--------|-------|-------------|
| `:hasChunk` | `:Document` | `:TextChunk` | Document contains chunks |
| `:partOf` | `:TextChunk` | `:Document` | Inverse of hasChunk |
| `:hasKeyword` | `:Document` | `:Keyword` | Document tagged with keyword |
| `:hasAuthor` | `:Document` | `:Author` | Document created by author |
| `:hasType` | `:Document` | `:DocumentType` | Document classification |
| `:mentions` | `:TextChunk` | `:Entity` | Chunk mentions entity |
| `:hasEmbedding` | `:TextChunk` | `:Embedding` | Chunk has vector embedding |
| `:relatedTo` | `:Entity` | `:Entity` | Entity related to entity (symmetric) |
| `:coOccursWith` | `:Entity` | `:Entity` | Entities in same chunk (symmetric) |

## Datatype Properties (Attributes)

| Property | Domain | Range | Description |
|----------|--------|-------|-------------|
| `:hasId` | Any | `xsd:string` | Unique identifier |
| `:hasFileName` | `:Document` | `xsd:string` | Original filename |
| `:hasText` | `:TextChunk`, `:Entity` | `xsd:string` | Text content |
| `:hasValue` | `:Entity`, `:Keyword` | `xsd:string` | String value |
| `:hasName` | `:Author` | `xsd:string` | Person name |
| `:hasChunkId` | `:TextChunk` | `xsd:integer` | Chunk number |
| `:hasTextLength` | `:Document` | `xsd:integer` | Length in characters |
| `:hasStartPosition` | `:TextChunk` | `xsd:integer` | Starting position |
| `:hasEndPosition` | `:TextChunk` | `xsd:integer` | Ending position |
| `:hasLength` | `:TextChunk` | `xsd:integer` | Chunk length |
| `:hasDimensions` | `:Embedding` | `xsd:integer` | Vector dimensions |
| `:hasVector` | `:Embedding` | `xsd:string` | Vector values |
| `:generatedBy` | `:Embedding` | `xsd:string` | Model name |
| `:createdAt` | Any | `xsd:dateTime` | Creation timestamp |
| `:updatedAt` | Any | `xsd:dateTime` | Update timestamp |
| `:hasConfidenceScore` | Any | `xsd:decimal` | Confidence (0-1) |
| `:hasRelevanceScore` | Any | `xsd:decimal` | Relevance score |

## Common SPARQL Queries

### List All Documents

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?doc ?fileName ?createdAt
WHERE {
    ?doc a :Document ;
         :hasFileName ?fileName ;
         :createdAt ?createdAt .
}
ORDER BY DESC(?createdAt)
```

### Find Document Chunks

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?chunk ?text ?chunkId
WHERE {
    <http://graph-rag.example.com/document/DOC-ID> 
        :hasChunk ?chunk .
    ?chunk :hasChunkId ?chunkId ;
           :hasText ?text .
}
ORDER BY ?chunkId
```

### Find Entities Mentioned in Document

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT DISTINCT ?entity ?value ?type
WHERE {
    <http://graph-rag.example.com/document/DOC-ID> 
        :hasChunk ?chunk .
    ?chunk :mentions ?entity .
    ?entity a ?type ;
            :hasValue ?value .
}
```

### Find Co-occurring Entities

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?entity1 ?value1 ?entity2 ?value2 ?chunk
WHERE {
    ?chunk :mentions ?entity1 ;
           :mentions ?entity2 .
    ?entity1 :hasValue ?value1 .
    ?entity2 :hasValue ?value2 .
    FILTER(?entity1 != ?entity2)
}
```

### Find Documents by Keyword

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?doc ?fileName
WHERE {
    ?doc a :Document ;
         :hasFileName ?fileName ;
         :hasKeyword ?keyword .
    ?keyword :hasValue "compliance" .
}
```

### Find Policy Documents

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?doc ?fileName
WHERE {
    ?doc a :Policy ;  # Subclass of :Document
         :hasFileName ?fileName .
}
```

### Count Chunks per Document

```sparql
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?doc ?fileName (COUNT(?chunk) AS ?chunkCount)
WHERE {
    ?doc a :Document ;
         :hasFileName ?fileName ;
         :hasChunk ?chunk .
}
GROUP BY ?doc ?fileName
ORDER BY DESC(?chunkCount)
```

## Cardinality Constraints

| Class | Property | Constraint |
|-------|----------|------------|
| `:Document` | `:hasId` | Exactly 1 |
| `:Document` | `:hasFileName` | Exactly 1 |
| `:Document` | `:createdAt` | Exactly 1 |
| `:Document` | `:hasChunk` | ≥ 1 |
| `:TextChunk` | `:hasText` | Exactly 1 |
| `:TextChunk` | `:hasChunkId` | Exactly 1 |
| `:TextChunk` | `:hasStartPosition` | Exactly 1 |
| `:TextChunk` | `:hasEmbedding` | ≤ 1 |
| `:Entity` | `:hasValue` | Exactly 1 |
| `:Keyword` | `:hasValue` | Exactly 1 |
| `:Author` | `:hasName` | Exactly 1 |
| `:Embedding` | `:hasVector` | Exactly 1 |
| `:Embedding` | `:hasDimensions` | Exactly 1 |
| `:Embedding` | `:generatedBy` | Exactly 1 |

## Example Instance

```turtle
@prefix : <http://graph-rag.example.com/ontology#> .
@prefix doc: <http://graph-rag.example.com/document/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Document
doc:550e8400-e29b-41d4-a716-446655440000 
    a :Document , :Policy ;
    :hasId "550e8400-e29b-41d4-a716-446655440000" ;
    :hasFileName "security-policy.pdf" ;
    :hasTextLength "5234"^^xsd:integer ;
    :createdAt "2025-01-05T10:30:00Z"^^xsd:dateTime ;
    :hasKeyword <http://graph-rag.example.com/entity/security> ;
    :hasKeyword <http://graph-rag.example.com/entity/compliance> ;
    :hasChunk doc:550e8400-e29b-41d4-a716-446655440000/chunk/0 .

# Text Chunk
doc:550e8400-e29b-41d4-a716-446655440000/chunk/0
    a :TextChunk ;
    :hasChunkId "0"^^xsd:integer ;
    :hasText "All employees must comply with security policies..." ;
    :hasStartPosition "0"^^xsd:integer ;
    :hasEndPosition "128"^^xsd:integer ;
    :hasLength "128"^^xsd:integer ;
    :partOf doc:550e8400-e29b-41d4-a716-446655440000 ;
    :mentions <http://graph-rag.example.com/entity/employees> ;
    :mentions <http://graph-rag.example.com/entity/security-policies> .

# Entity
<http://graph-rag.example.com/entity/employees>
    a :Concept ;
    :hasValue "employees" ;
    :hasConfidenceScore "0.95"^^xsd:decimal .
```

## Validation Rules

✅ **Pass**: Instance conforms to ontology  
⚠️ **Warning**: Non-critical issue (e.g., undefined class)  
❌ **Fail**: Violates constraint (e.g., missing required property)

### Common Violations

1. **Missing Required Property**
   ```
   ❌ Document missing :hasId
   ```

2. **Cardinality Violation**
   ```
   ❌ Document has 0 chunks (requires ≥ 1)
   ❌ Document has 2 IDs (requires exactly 1)
   ```

3. **Domain Mismatch**
   ```
   ❌ :hasAuthor used on :TextChunk (domain is :Document)
   ```

4. **Undefined Class**
   ```
   ⚠️ Instance type :UnknownClass not defined in ontology
   ```

## Integration with Standard Vocabularies

```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

# Our classes extend standard vocabularies
:Document rdfs:subClassOf foaf:Document .
:Person rdfs:subClassOf foaf:Person .
:Organization rdfs:subClassOf foaf:Organization .
:Concept rdfs:subClassOf skos:Concept .
```

## Tools and Resources

- **Ontology File**: `ontologies/graph-rag-ontology.ttl`
- **Validation Lambda**: `lambda/ontology-validator/`
- **Full Guide**: [ONTOLOGY_GUIDE.md](ONTOLOGY_GUIDE.md)
- **Implementation Details**: [ONTOLOGY_UPLIFTS.md](ONTOLOGY_UPLIFTS.md)
- **AWS Blog**: [Model-driven graphs using OWL](https://aws.amazon.com/blogs/database/model-driven-graphs-using-owl-in-amazon-neptune/)

## Quick Commands

```bash
# Load ontology to S3
aws s3 cp ontologies/graph-rag-ontology.ttl \
  s3://your-bucket/ontologies/

# Query Neptune
aws neptune-data execute-sparql-query \
  --endpoint your-endpoint.neptune.amazonaws.com \
  --query-string "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

# Test validation
# Upload document → Check CloudWatch logs for validation results
```

---

**Need More Details?** See [ONTOLOGY_GUIDE.md](ONTOLOGY_GUIDE.md) for comprehensive documentation.

