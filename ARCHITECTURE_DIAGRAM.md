# Graph RAG Architecture - Mermaid Diagrams

## Complete System Architecture

```mermaid
graph TB
    User["User/Client"]
    APIGW["API Gateway - REST API"]
    UploadLambda["Lambda - Upload Handler"]
    S3["S3 Bucket - Documents"]
    EventBridge["EventBridge - Event Rules"]
    StepFunctions["Step Functions - State Machine"]
    DLQ["SQS DLQ - Failed Events"]
    DocParser["Lambda - Document Parser"]
    RDFGen["Lambda - RDF Generator"]
    OntologyVal["Lambda - Ontology Validator NEW"]
    NeptuneWriter["Lambda - Neptune Writer"]
    EmbedGen["Lambda - Embedding Generator"]
    OSWriter["Lambda - OpenSearch Writer"]
    SageMaker["SageMaker Endpoint - Hugging Face"]
    Neptune["Neptune Cluster - Graph Database"]
    OpenSearch["OpenSearch - Vector Search"]
    OWL["OWL Ontology - graph-rag-ontology.ttl NEW"]
    CloudWatch["CloudWatch - Logs"]

    User -->|Upload| APIGW
    APIGW -->|Invoke| UploadLambda
    UploadLambda -->|Store| S3
    S3 -.->|Event| EventBridge
    EventBridge -->|Trigger| StepFunctions
    EventBridge -.->|Failed| DLQ
    StepFunctions -->|Parse| DocParser
    DocParser -->|Text| RDFGen
    RDFGen -->|RDF| OntologyVal
    OntologyVal -->|Validate| OWL
    OntologyVal -->|Valid RDF| NeptuneWriter
    OntologyVal -->|Chunks| EmbedGen
    NeptuneWriter -->|Stage| S3
    S3 -->|Load| Neptune
    EmbedGen -->|Generate| SageMaker
    SageMaker -->|Vectors| EmbedGen
    EmbedGen -->|Index| OSWriter
    OSWriter -->|Store| OpenSearch
    StepFunctions -.->|Logs| CloudWatch
    
    classDef awsOrange fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsBlue fill:#3B48CC,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsGreen fill:#3F8624,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsPurple fill:#8C4FFF,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsRed fill:#D13212,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef newFeature fill:#00D4AA,stroke:#232F3E,stroke-width:3px,color:#000

    class APIGW,S3 awsOrange
    class Neptune,OpenSearch awsBlue
    class UploadLambda,DocParser,RDFGen,NeptuneWriter,EmbedGen,OSWriter awsGreen
    class StepFunctions,EventBridge awsPurple
    class SageMaker awsRed
    class OntologyVal,OWL newFeature
```

## Upload Pipeline Detail

```mermaid
sequenceDiagram
    participant User
    participant API as API Gateway
    participant Upload as Upload Lambda
    participant S3 as S3 Bucket
    participant EB as EventBridge
    participant SF as Step Functions

    User->>API: POST /upload
    API->>Upload: Invoke with request
    Upload->>Upload: Validate file
    Upload->>Upload: Generate UUID
    Upload->>S3: PutObject
    Upload->>S3: Add tags
    Upload-->>API: Success response
    API-->>User: Upload confirmation
    S3->>EB: Object Created Event
    EB->>SF: Start Execution
    Note over SF: Processing pipeline starts
```

## Processing Pipeline (Step Functions)

```mermaid
stateDiagram-v2
    [*] --> ParseDocument
    
    state ParseDocument {
        [*] --> ExtractText
        ExtractText --> SplitChunks
        SplitChunks --> ExtractMetadata
        ExtractMetadata --> [*]
    }
    
    ParseDocument --> GenerateRDF
    
    state GenerateRDF {
        [*] --> CreateTriples
        CreateTriples --> DefineEntities
        DefineEntities --> BuildRelationships
        BuildRelationships --> SerializeRDF
        SerializeRDF --> [*]
    }
    
    GenerateRDF --> ValidateOntology
    
    state ValidateOntology {
        [*] --> QueryOntology
        QueryOntology --> CheckClasses
        CheckClasses --> CheckCardinality
        CheckCardinality --> CheckDomains
        CheckDomains --> ReportViolations
        ReportViolations --> [*]
    }
    
    ValidateOntology --> ValidationCheck
    
    state ValidationCheck <<choice>>
    ValidationCheck --> ParallelProcessing: Valid
    ValidationCheck --> Failed: Violations
    
    state ParallelProcessing {
        state fork_state <<fork>>
        [*] --> fork_state
        
        fork_state --> NeptuneBranch
        fork_state --> EmbeddingBranch
        
        state NeptuneBranch {
            [*] --> StageRDF
            StageRDF --> BulkLoad
            BulkLoad --> PollStatus
            PollStatus --> [*]
        }
        
        state EmbeddingBranch {
            [*] --> GenerateEmbeddings
            GenerateEmbeddings --> CallSageMaker
            CallSageMaker --> IndexOpenSearch
            IndexOpenSearch --> [*]
        }
        
        state join_state <<join>>
        NeptuneBranch --> join_state
        EmbeddingBranch --> join_state
        join_state --> [*]
    }
    
    ParallelProcessing --> Success
    Failed --> [*]
    Success --> [*]
```

## Data Flow with Ontology Validation

```mermaid
graph LR
    Doc["Document - PDF/DOCX/CSV"]
    Parse["Parse - Extract Text"]
    RDF["Generate RDF Triples"]
    Validate["Validate - NEW"]
    Onto["OWL Ontology - Classes & Rules"]
    R1["Check Class Membership"]
    R2["Check Cardinality"]
    R3["Check Domain/Range"]
    R4["Check Required Props"]
    Nep["Neptune - Graph"]
    OS["OpenSearch - Vectors"]
    DLQ2["DLQ"]

    Doc --> Parse
    Parse --> RDF
    RDF --> Validate
    Validate --> Onto
    Onto --> R1
    Onto --> R2
    Onto --> R3
    Onto --> R4
    R1 --> Validate
    R2 --> Validate
    R3 --> Validate
    R4 --> Validate
    Validate -->|Pass| Nep
    Validate -->|Pass| OS
    Validate -->|Fail| DLQ2

    style Validate fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style Onto fill:#00D4AA,stroke:#232F3E,stroke-width:3px
```

## VPC Architecture

```mermaid
graph TB
    Internet["Internet"]
    IGW["Internet Gateway"]
    NAT1["NAT Gateway AZ1"]
    NAT2["NAT Gateway AZ2"]
    PublicSubnet1["Public Subnet 1 - 10.0.0.0/24"]
    PublicSubnet2["Public Subnet 2 - 10.0.2.0/24"]
    PrivateSubnet1["Private Subnet 1 - 10.0.1.0/24"]
    PrivateSubnet2["Private Subnet 2 - 10.0.3.0/24"]
    Lambda1["Lambda Functions"]
    Neptune1["Neptune Primary"]
    Neptune2["Neptune Replica"]
    OS1["OpenSearch Node 1"]
    OS2["OpenSearch Node 2"]

    Internet --> IGW
    IGW --> PublicSubnet1
    IGW --> PublicSubnet2
    PublicSubnet1 --> NAT1
    PublicSubnet2 --> NAT2
    NAT1 --> PrivateSubnet1
    NAT2 --> PrivateSubnet2
    PrivateSubnet1 --> Lambda1
    PrivateSubnet1 --> Neptune1
    PrivateSubnet1 --> OS1
    PrivateSubnet2 --> Neptune2
    PrivateSubnet2 --> OS2
    Lambda1 -.->|Port 8182| Neptune1
    Lambda1 -.->|Port 443| OS1

    style PrivateSubnet1 fill:#FF6B6B,stroke:#C92A2A
    style PrivateSubnet2 fill:#FF6B6B,stroke:#C92A2A
    style PublicSubnet1 fill:#51CF66,stroke:#2F9E44
    style PublicSubnet2 fill:#51CF66,stroke:#2F9E44
```

## Neptune & OpenSearch Architecture

```mermaid
graph TB
    L1["Neptune Writer Lambda"]
    L2["OpenSearch Writer Lambda"]
    L3["Validator Lambda"]
    S3Stage["S3 Staging - neptune-staging/"]
    NepPrimary["Neptune Primary - db.t3.medium"]
    NepReplica["Neptune Replica - db.t3.medium"]
    NepData[("RDF Triples & Ontology")]
    OSNode1["OpenSearch Node 1 - t3.small.search"]
    OSNode2["OpenSearch Node 2 - t3.small.search"]
    OSData[("Embeddings & k-NN Index")]

    L1 -->|1. Write RDF| S3Stage
    S3Stage -->|2. Bulk Load| NepPrimary
    NepPrimary -->|3. Store| NepData
    NepPrimary -->|Replication| NepReplica
    L3 -->|Query Ontology| NepPrimary
    NepPrimary -->|OWL Rules| L3
    L2 -->|Index Vectors| OSNode1
    OSNode1 <-->|Cluster Sync| OSNode2
    OSNode1 -->|Store| OSData
    
    style NepData fill:#3B48CC
    style OSData fill:#3B48CC
```

## Ontology Structure (OWL Classes)

```mermaid
classDiagram
    class Document {
        +hasId: string [1]
        +hasFileName: string [1]
        +hasTextLength: integer
        +createdAt: dateTime [1]
        +hasChunk() [1..*]
        +hasKeyword() [0..*]
        +hasAuthor() [0..1]
        +hasType() [0..*]
    }

    class TextChunk {
        +hasChunkId: integer [1]
        +hasText: string [1]
        +hasStartPosition: integer [1]
        +hasEndPosition: integer
        +hasLength: integer
        +partOf() [1]
        +mentions() [0..*]
        +hasEmbedding() [0..1]
    }

    class Entity {
        +hasValue: string [1]
        +hasConfidenceScore: decimal
        +relatedTo() [0..*]
        +coOccursWith() [0..*]
    }

    class Person {
        <<Entity>>
        +hasName: string
    }

    class Organization {
        <<Entity>>
    }

    class Keyword {
        +hasValue: string [1]
    }

    class Author {
        +hasName: string [1]
    }

    class Embedding {
        +hasVector: string [1]
        +hasDimensions: integer [1]
        +generatedBy: string [1]
    }

    class Policy {
        <<Document>>
    }

    class Standard {
        <<Document>>
    }

    Document "1" --> "1..*" TextChunk : hasChunk
    Document "1" --> "0..*" Keyword : hasKeyword
    Document "1" --> "0..1" Author : hasAuthor
    TextChunk "1" --> "0..*" Entity : mentions
    TextChunk "1" --> "0..1" Embedding : hasEmbedding
    Entity <--> Entity : coOccursWith
    Entity <--> Entity : relatedTo
    Person --|> Entity
    Organization --|> Entity
    Policy --|> Document
    Standard --|> Document

    note for Document "🆕 NEW: OWL Ontology\nCardinality: [min..max]\n[1] = exactly one\n[1..*] = one or more\n[0..*] = zero or more"
```

## SageMaker Embedding Flow

```mermaid
graph LR
    Chunks["Text Chunks from Document"]
    EmbedLambda["Embedding Generator Lambda"]
    Batch["Batch Chunks"]
    Invoke["Invoke Endpoint"]
    Collect["Collect Vectors"]
    Endpoint["SageMaker Endpoint ml.m5.large"]
    Model["Hugging Face Model all-mpnet-base-v2"]
    Vectors["Embeddings 768-dim vectors"]

    Chunks --> EmbedLambda
    EmbedLambda --> Batch
    Batch --> Invoke
    Invoke -->|HTTP POST| Endpoint
    Endpoint --> Model
    Model -->|JSON Response| Invoke
    Invoke --> Collect
    Collect --> Vectors

    style Model fill:#FF9900
    style Endpoint fill:#D13212
```

## Cost Breakdown

```mermaid
pie title Monthly Cost Distribution (~$259/month)
    "Neptune (db.t3.medium)" : 70
    "OpenSearch (2x t3.small)" : 60
    "SageMaker (ml.m5.large)" : 84
    "NAT Gateway" : 35
    "Lambda & Other" : 10
```

## Query Pipeline (Future)

```mermaid
graph TB
    UserQ["User Query"]
    API2["API Gateway POST /query"]
    QueryLambda["Query Lambda"]
    EmbedQ["Generate Query Embedding"]
    OSQuery["OpenSearch k-NN Search"]
    NepQuery["Neptune Graph Traversal"]
    Context["Enriched Context"]
    SageMakerLLM["SageMaker LLM Endpoint"]
    Answer["Generated Answer with Citations"]

    UserQ --> API2
    API2 --> QueryLambda
    QueryLambda --> EmbedQ
    EmbedQ -->|Vector| OSQuery
    OSQuery -->|Top-k Chunks| Context
    QueryLambda -->|Document IDs| NepQuery
    NepQuery -->|Related Entities| Context
    Context --> SageMakerLLM
    SageMakerLLM --> Answer
    Answer --> UserQ

    style QueryLambda fill:#00D4AA,stroke:#232F3E,stroke-width:2px
    style Context fill:#FFD93D,stroke:#232F3E,stroke-width:2px
```

## Legend

```mermaid
graph LR
    API["API Gateway"]
    Lambda["Lambda"]
    S3["S3"]
    EB["EventBridge"]
    SF["Step Functions"]
    Nep["Neptune"]
    OS["OpenSearch"]
    SM["SageMaker"]
    SQS2["SQS"]
    CW2["CloudWatch"]
    New["NEW FEATURE - Ontology Validation"]
    Existing["Existing Feature"]
    A["Service A"]
    B["Service B"]
    C["Service C"]
    D["Service D"]

    A -->|Synchronous| B
    C -.->|Asynchronous| D

    style New fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style Existing fill:#FF9900,stroke:#232F3E,stroke-width:2px
```

## Deployment Stages

```mermaid
timeline
    title Deployment & Setup Timeline
    
    section Prerequisites
        Install Node.js : AWS CLI
                       : CDK CLI
    
    section SageMaker Setup
        Deploy Endpoint : Create Model
                       : Configure Instance
                       : Test Endpoint
                       : ~10 minutes
    
    section CDK Deployment
        Bootstrap : cdk bootstrap
        
        Deploy Networking : VPC
                         : Subnets
                         : Security Groups
                         : ~10 minutes
        
        Deploy Storage : S3 Bucket
                      : Lifecycle Policies
                      : ~2 minutes
        
        Deploy Data Stores : Neptune Cluster
                          : OpenSearch Domain
                          : ~25 minutes
        
        Deploy Processing : Lambda Functions
                         : Ontology Validator
                         : ~5 minutes
        
        Deploy Orchestration : Step Functions
                            : EventBridge Rules
                            : ~3 minutes
        
        Deploy API : API Gateway
                  : Upload Handler
                  : ~2 minutes
    
    section Post-Deployment
        Load Ontology : Upload to S3
                     : Bulk Load to Neptune
        
        Test Pipeline : Upload Document
                     : Monitor Execution
                     : Verify Results
        
        Total Time : ~50-60 minutes
```

---

## How to Use These Diagrams

### In GitHub/GitLab
These Mermaid diagrams will render automatically in:
- README.md
- Wiki pages
- Issues/PRs

### In Documentation Sites
- **Docusaurus**: Supports Mermaid via plugin
- **MkDocs**: Use `mkdocs-mermaid2-plugin`
- **Sphinx**: Use `sphinxcontrib-mermaid`

### Export as Images
Use [Mermaid Live Editor](https://mermaid.live/):
1. Copy diagram code
2. Paste in editor
3. Export as PNG/SVG

### In VS Code
Install extension: `Markdown Preview Mermaid Support`

---

## Diagram Index

1. **Complete System Architecture** - Full end-to-end flow
2. **Upload Pipeline Detail** - Sequence diagram of upload
3. **Processing Pipeline** - State machine visualization
4. **Data Flow with Ontology** - Validation flow (🆕 NEW)
5. **VPC Architecture** - Network layout
6. **Neptune & OpenSearch** - Data store architecture
7. **Ontology Structure** - OWL class diagram (🆕 NEW)
8. **SageMaker Embedding** - ML pipeline
9. **Cost Breakdown** - Monthly costs
10. **Query Pipeline** - Future RAG retrieval
11. **Deployment Timeline** - Setup stages

