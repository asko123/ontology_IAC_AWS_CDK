# Graph RAG Ontology - Visual Diagram

## Class Hierarchy

```
owl:Thing
  │
  ├── foaf:Document
  │     └── :Document
  │           ├── :Policy
  │           ├── :Standard
  │           ├── :Report
  │           └── :Specification
  │
  ├── :TextChunk
  │
  ├── :Entity
  │     ├── :Person (also foaf:Person)
  │     ├── :Organization (also foaf:Organization)
  │     ├── :Location
  │     └── :Concept (also skos:Concept)
  │
  ├── :Keyword
  │
  ├── :Author (foaf:Person)
  │
  ├── :Embedding
  │
  └── :DocumentType
```

## Relationship Graph

```
┌─────────────┐
│  Document   │───────hasAuthor─────────▶│  Author   │
│             │                           │           │
│ Properties: │                           │hasName    │
│ - hasId     │                           └───────────┘
│ - fileName  │
│ - createdAt │
│ - textLen   │
└──────┬──────┘
       │
       │ hasChunk
       │ (1..*)
       ↓
┌─────────────┐
│  TextChunk  │───────mentions──────────▶┌───────────┐
│             │       (0..*)             │  Entity   │
│ Properties: │                          │           │
│ - chunkId   │                          │ hasValue  │
│ - text      │◀─────coOccursWith────────│           │
│ - startPos  │      (symmetric)         └─────┬─────┘
│ - endPos    │                                │
│ - length    │                                │ relatedTo
└──────┬──────┘                                │ (symmetric)
       │                                       ↓
       │ hasEmbedding                    ┌───────────┐
       │ (0..1)                          │  Entity   │
       ↓                                 └───────────┘
┌─────────────┐
│  Embedding  │
│             │
│ Properties: │
│ - vector    │
│ - dimensions│
│ - genBy     │
└─────────────┘
```

## Document with Metadata

```
                    ┌─────────────┐
              ┌─────│  Keyword    │
              │     │             │
              │     │  hasValue   │
              │     └─────────────┘
              │
       hasKeyword
              │
              │     ┌─────────────┐
┌─────────────┴─────│  Document   │──────hasType────▶┌──────────────┐
│                   │             │                  │ DocumentType │
│                   │  :Policy    │                  │              │
│                   │  :Standard  │                  │  :Policy     │
│                   │  :Report    │                  │  :Standard   │
│                   └─────────────┘                  │  :Report     │
│                                                    │  :Spec       │
hasKeyword                                           └──────────────┘
│
│            ┌─────────────┐
└────────────│  Keyword    │
             │             │
             │  hasValue   │
             └─────────────┘
```

## Entity Types and Relationships

```
┌──────────────┐         ┌──────────────┐
│   Person     │◀────────│ Organization │
│              │ workFor │              │
│ - hasName    │         │ - hasValue   │
│ - hasValue   │         └──────────────┘
└──────┬───────┘
       │
       │ relatedTo
       │ (symmetric)
       ↓
┌──────────────┐
│   Concept    │
│              │
│ - hasValue   │
│ - confidence │
└──────────────┘
       ↑
       │ mentions
       │
┌──────────────┐         ┌──────────────┐
│  TextChunk   │─────────│   Location   │
│              │ mentions│              │
│ - text       │         │ - hasValue   │
│ - chunkId    │         └──────────────┘
└──────────────┘
```

## Complete Document Processing Flow

```
1. Upload Document
   │
   ↓
┌─────────────────────────────────────────┐
│           Document Instance             │
│                                         │
│  :doc123 a :Document , :Policy          │
│    :hasId "doc123"                      │
│    :hasFileName "security-policy.pdf"   │
│    :hasTextLength "5234"^^xsd:integer   │
│    :createdAt "2025-01-05T10:00:00Z"    │
└────────────┬────────────────────────────┘
             │
             │ hasChunk
             ↓
2. Parse & Chunk
   │
   ↓
┌─────────────────────────────────────────┐
│         TextChunk Instances             │
│                                         │
│  :chunk0 a :TextChunk                   │
│    :hasChunkId "0"^^xsd:integer         │
│    :hasText "All employees must..."     │
│    :hasStartPosition "0"^^xsd:integer   │
│    :partOf :doc123  [inferred]          │
└────────────┬────────────────────────────┘
             │
             │ mentions
             ↓
3. Extract Entities
   │
   ↓
┌─────────────────────────────────────────┐
│          Entity Instances               │
│                                         │
│  :entity-employees a :Concept           │
│    :hasValue "employees"                │
│    :hasConfidenceScore "0.95"           │
│                                         │
│  :entity-aws a :Organization            │
│    :hasValue "AWS"                      │
│    :hasConfidenceScore "0.98"           │
└────────────┬────────────────────────────┘
             │
             │ coOccursWith (inferred)
             ↓
4. Infer Relationships
   │
   ↓
┌─────────────────────────────────────────┐
│     Inferred Co-occurrence              │
│                                         │
│  :entity-employees                      │
│    :coOccursWith :entity-aws            │
│                                         │
│  :entity-aws                            │
│    :coOccursWith :entity-employees      │
│      [symmetric property]               │
└─────────────────────────────────────────┘
```

## Cardinality Visualization

```
Document
├── hasId (1)              ◀─ Exactly 1 required
├── hasFileName (1)        ◀─ Exactly 1 required
├── createdAt (1)          ◀─ Exactly 1 required
├── hasChunk (1..*)        ◀─ At least 1 required
├── hasKeyword (0..*)      ◀─ Zero or more
├── hasAuthor (0..1)       ◀─ Zero or one
└── hasType (0..*)         ◀─ Zero or more

TextChunk
├── hasChunkId (1)         ◀─ Exactly 1 required
├── hasText (1)            ◀─ Exactly 1 required
├── hasStartPosition (1)   ◀─ Exactly 1 required
├── hasEmbedding (0..1)    ◀─ Zero or one
└── mentions (0..*)        ◀─ Zero or more

Entity
└── hasValue (1)           ◀─ Exactly 1 required

Embedding
├── hasVector (1)          ◀─ Exactly 1 required
├── hasDimensions (1)      ◀─ Exactly 1 required
└── generatedBy (1)        ◀─ Exactly 1 required
```

## Validation Flow

```
┌─────────────┐
│  RDF Data   │
│  Generated  │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────┐
│   Ontology Validator Lambda     │
├─────────────────────────────────┤
│                                 │
│  1. Check Class Membership      │
│     ✓ All instances have        │
│       valid rdf:type?           │
│                                 │
│  2. Check Property Domains      │
│     ✓ Properties used on        │
│       correct classes?          │
│                                 │
│  3. Check Cardinality           │
│     ✓ Required properties       │
│       present?                  │
│     ✓ Cardinality = 1?          │
│     ✓ MinCardinality met?       │
│                                 │
│  4. Check Property Ranges       │
│     ✓ Values have correct       │
│       type?                     │
│                                 │
└──────┬──────────────┬───────────┘
       │              │
       ↓              ↓
  ✓ PASS        ❌ FAIL
       │              │
       ↓              ↓
┌─────────────┐  ┌─────────────┐
│  Load to    │  │  Reject &   │
│  Neptune    │  │  Log Errors │
└─────────────┘  └─────────────┘
```

## Property Characteristics

### Symmetric Properties

```
Entity A ──relatedTo──▶ Entity B
         ◀──relatedTo──
         
If A relatedTo B, then B relatedTo A
```

### Inverse Properties

```
Document ──hasChunk──▶ TextChunk
         ◀──partOf────
         
If Doc hasChunk Chunk, then Chunk partOf Doc
```

### Transitive Properties (Future)

```
Org A ──subOrganizationOf──▶ Org B ──subOrganizationOf──▶ Org C
       └──────────────subOrganizationOf──────────────────▶
       
If A subOrgOf B and B subOrgOf C, then A subOrgOf C
```

## Integration with Standard Vocabularies

```
Graph RAG Ontology
│
├── FOAF (Friend of a Friend)
│   ├── foaf:Document ◀─ :Document
│   ├── foaf:Person ◀─ :Person, :Author
│   └── foaf:Organization ◀─ :Organization
│
├── Dublin Core
│   ├── dcterms:title
│   ├── dcterms:creator
│   ├── dcterms:created
│   └── dcterms:modified
│
├── SKOS (Simple Knowledge Organization)
│   └── skos:Concept ◀─ :Concept
│
└── Schema.org (Future)
    ├── schema:Document
    └── schema:Organization
```

## Query Patterns

### Pattern 1: Find Document Chunks

```sparql
:doc123 ──hasChunk──▶ ?chunk
```

### Pattern 2: Find Entities in Document

```sparql
:doc123 ──hasChunk──▶ ?chunk ──mentions──▶ ?entity
```

### Pattern 3: Find Co-occurring Entities

```sparql
?chunk ──mentions──▶ ?entity1
       ──mentions──▶ ?entity2
       
?entity1 ──coOccursWith──▶ ?entity2 [inferred]
```

### Pattern 4: Find Related Documents

```sparql
:doc1 ──hasChunk──▶ ?chunk1 ──mentions──▶ ?entity
                                          ◀──mentions── ?chunk2 ◀──hasChunk── :doc2
```

## Legend

```
┌─────────┐
│  Class  │    OWL Class
└─────────┘

───────────▶   Object Property (relationship)

- property     Datatype Property (attribute)

(0..1)         Cardinality: Zero or one
(1)            Cardinality: Exactly one
(1..*)         Cardinality: One or more
(0..*)         Cardinality: Zero or more

◀───symmetric───▶   Symmetric property

a → b          Inverse properties
a ← b

[inferred]     Derived by reasoner
```

## Namespace Prefixes

```turtle
@prefix : <http://graph-rag.example.com/ontology#> .
@prefix doc: <http://graph-rag.example.com/document/> .
@prefix entity: <http://graph-rag.example.com/entity/> .

@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
```

---

## Quick Navigation

- **Ontology File**: `ontologies/graph-rag-ontology.ttl`
- **Full Guide**: [ONTOLOGY_GUIDE.md](ONTOLOGY_GUIDE.md)
- **Quick Reference**: [ONTOLOGY_QUICK_REFERENCE.md](ONTOLOGY_QUICK_REFERENCE.md)
- **Implementation**: [ONTOLOGY_UPLIFTS.md](ONTOLOGY_UPLIFTS.md)
- **Summary**: [SUMMARY_ONTOLOGY_NEPTUNE_UPLIFTS.md](SUMMARY_ONTOLOGY_NEPTUNE_UPLIFTS.md)

