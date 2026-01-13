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

### Monthly Cost Distribution (~$259/month)

| Service | Instance/Configuration | Cost/Month | Percentage | Use Case |
|---------|----------------------|------------|------------|----------|
| **SageMaker** | ml.m5.large (24/7) | $84 | 32% | Embedding generation |
| **Neptune** | db.t3.medium (Primary + Replica) | $70 | 27% | Graph database |
| **OpenSearch** | 2× t3.small.search nodes | $60 | 23% | Vector search + storage |
| **NAT Gateway** | 1 gateway in 1 AZ | $35 | 14% | Private subnet internet access |
| **Lambda & Other** | 6 functions + Step Functions + API Gateway | $10 | 4% | Processing & orchestration |
| **TOTAL** | | **$259** | **100%** | Complete system |

### Cost Optimization Options

**Quick Wins**:
- 💰 **Save $48/month**: Use ml.t3.medium for SageMaker (dev/testing)
- 💰 **Save $48-$74/month**: Use SageMaker Serverless for low volume (< 1000 docs/day)
- 💰 **Save $35/month**: Remove NAT Gateway (use VPC endpoints instead)
- 💰 **Save $28/month**: Use 1 OpenSearch node (non-HA)

**Long-term Savings**:
- 💰 **Save 20-64%**: SageMaker Savings Plans
- 💰 **Save 40-60%**: Neptune Reserved Instances
- 💰 **Save 30-45%**: OpenSearch Reserved Instances

### Alternative Pie Chart (Optional)

```mermaid
pie title Monthly Cost Distribution (~$259/month)
    "SageMaker (ml.m5.large)" : 84
    "Neptune (db.t3.medium)" : 70
    "OpenSearch (2x t3.small)" : 60
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

---

## Advanced AI Agent Pipeline (Future²) 🚀

### Multi-Agent Architecture with Tree of Thoughts

```mermaid
graph TB
    User["User Complex Query"]
    Orchestrator["🧠 Agent Orchestrator"]
    
    subgraph "Tree of Thoughts Reasoning"
        ToT["Tree of Thoughts Engine"]
        Branch1["Branch 1: Direct Answer"]
        Branch2["Branch 2: Analytical"]
        Branch3["Branch 3: Creative"]
        Evaluate["Evaluate & Score Branches"]
        BestPath["Select Best Reasoning Path"]
    end
    
    subgraph "Specialized Agents"
        SearchAgent["🔍 Search Agent<br/>Vector + Graph Retrieval"]
        ReasonAgent["🤔 Reasoning Agent<br/>Logical Inference"]
        ValidationAgent["✓ Validation Agent<br/>Fact Checking"]
        SynthesisAgent["📝 Synthesis Agent<br/>Answer Generation"]
    end
    
    subgraph "Knowledge Base"
        Neptune2["Neptune<br/>Graph Knowledge"]
        OS2["OpenSearch<br/>Vector Search"]
        Memory["Agent Memory<br/>DynamoDB"]
    end
    
    LLM["🤖 Advanced LLM<br/>GPT-4/Claude/Bedrock"]
    FinalAnswer["Rich Answer + Reasoning Tree"]
    
    User --> Orchestrator
    Orchestrator --> ToT
    ToT --> Branch1
    ToT --> Branch2
    ToT --> Branch3
    Branch1 --> Evaluate
    Branch2 --> Evaluate
    Branch3 --> Evaluate
    Evaluate --> BestPath
    
    BestPath --> SearchAgent
    SearchAgent --> Neptune2
    SearchAgent --> OS2
    SearchAgent --> ReasonAgent
    
    ReasonAgent --> LLM
    ReasonAgent --> ValidationAgent
    ValidationAgent --> Neptune2
    ValidationAgent --> SynthesisAgent
    
    SynthesisAgent --> Memory
    SynthesisAgent --> LLM
    LLM --> FinalAnswer
    FinalAnswer --> User
    
    Orchestrator -.->|Track State| Memory
    
    style ToT fill:#FF6B9D,stroke:#232F3E,stroke-width:3px
    style Orchestrator fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style LLM fill:#9D4EDD,stroke:#232F3E,stroke-width:2px
    style FinalAnswer fill:#FFD93D,stroke:#232F3E,stroke-width:2px
```

### Tree of Thoughts Reasoning Flow

```mermaid
sequenceDiagram
    participant User
    participant Orch as Orchestrator
    participant ToT as Tree of Thoughts
    participant Search as Search Agent
    participant Reason as Reasoning Agent
    participant Valid as Validation Agent
    participant Synth as Synthesis Agent
    participant KB as Knowledge Base
    participant LLM as Advanced LLM
    
    User->>Orch: "Explain the relationship between<br/>security policies and compliance"
    
    Orch->>ToT: Decompose query
    
    Note over ToT: Generate reasoning branches
    ToT->>ToT: Branch 1: Historical approach
    ToT->>ToT: Branch 2: Current standards
    ToT->>ToT: Branch 3: Future trends
    ToT->>ToT: Evaluate branches (score 0-1)
    ToT->>Orch: Best path: Branch 2 (score: 0.92)
    
    Orch->>Search: Retrieve relevant context
    Search->>KB: k-NN vector search
    KB-->>Search: Top-10 chunks
    Search->>KB: Graph traversal (entities)
    KB-->>Search: Related documents
    Search-->>Reason: Combined context
    
    Reason->>LLM: Analyze relationships
    LLM-->>Reason: Initial reasoning
    Reason->>Valid: Validate claims
    
    Valid->>KB: Check facts against ontology
    KB-->>Valid: Verified: 8/10 claims
    Valid-->>Synth: Validated reasoning + confidence
    
    Synth->>LLM: Generate structured answer
    LLM-->>Synth: Draft answer
    Synth->>Synth: Add citations + reasoning tree
    Synth-->>User: Rich answer with provenance
    
    Note over User: Answer includes:<br/>- Main response<br/>- Reasoning steps<br/>- Confidence scores<br/>- Source citations<br/>- Alternative paths explored
```

### Agent Collaboration Pattern

```mermaid
graph LR
    subgraph "Agent Loop"
        A1["👁️ Observe<br/>User query + context"]
        A2["🧠 Think<br/>Tree of Thoughts reasoning"]
        A3["🎯 Plan<br/>Action sequence"]
        A4["⚡ Act<br/>Execute via specialized agents"]
        A5["📊 Reflect<br/>Evaluate outcome"]
    end
    
    Memory[("Agent Memory<br/>Past interactions<br/>Learned patterns")]
    Tools["Tool Arsenal<br/>- Neptune Query<br/>- Vector Search<br/>- Validation<br/>- External APIs"]
    
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5
    A5 -.->|Feedback loop| A1
    
    A2 <--> Memory
    A4 --> Tools
    A5 --> Memory
    
    style A2 fill:#FF6B9D,stroke:#232F3E,stroke-width:2px
    style Memory fill:#FFD93D,stroke:#232F3E,stroke-width:2px
```

### Tree of Thoughts Expansion

```mermaid
graph TB
    Root["Root Query:<br/>Find security policies<br/>related to data protection"]
    
    subgraph "Depth 1: Initial Thoughts"
        T1["💭 Thought 1:<br/>Search by keywords"]
        T2["💭 Thought 2:<br/>Search by entities"]
        T3["💭 Thought 3:<br/>Search by relationships"]
    end
    
    subgraph "Depth 2: Expand Best Path"
        T2_1["Identify entities:<br/>GDPR, PII, encryption"]
        T2_2["Graph traversal:<br/>policy → compliance"]
        T2_3["Vector similarity:<br/>related concepts"]
    end
    
    subgraph "Depth 3: Validation"
        V1["✓ Check ontology"]
        V2["✓ Verify relationships"]
        V3["✓ Score confidence"]
    end
    
    subgraph "Pruning & Selection"
        Prune["🔪 Prune low-scoring<br/>branches (< 0.7)"]
        Select["⭐ Select best path<br/>(score: 0.94)"]
    end
    
    Result["Final Result:<br/>5 policies found<br/>with confidence scores"]
    
    Root --> T1
    Root --> T2
    Root --> T3
    
    T1 -.->|Score: 0.65| Prune
    T2 -->|Score: 0.89| T2_1
    T3 -.->|Score: 0.71| Prune
    
    T2_1 --> V1
    T2_2 --> V2
    T2_3 --> V3
    
    T2 --> T2_2
    T2 --> T2_3
    
    V1 --> Select
    V2 --> Select
    V3 --> Select
    
    Select --> Result
    
    style Root fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style T2 fill:#9D4EDD,stroke:#232F3E,stroke-width:2px
    style Select fill:#FFD93D,stroke:#232F3E,stroke-width:2px
    style Prune fill:#FF6B6B,stroke:#232F3E,stroke-width:2px
```

### Multi-Agent System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI["User Interface<br/>Chat + Reasoning Visualizer"]
        API3["API Gateway<br/>WebSocket + REST"]
    end
    
    subgraph "Agent Orchestration Layer"
        Orchestrator2["Agent Orchestrator<br/>Step Functions + Bedrock Agents"]
        ToTEngine["Tree of Thoughts Engine<br/>Lambda + SageMaker"]
        AgentMemory["Agent Memory Service<br/>DynamoDB + ElastiCache"]
    end
    
    subgraph "Specialized Agent Pool"
        direction LR
        Agent1["🔍 Search Agent"]
        Agent2["🤔 Reasoning Agent"]
        Agent3["✓ Validation Agent"]
        Agent4["📝 Synthesis Agent"]
        Agent5["🔬 Analysis Agent"]
        Agent6["🎨 Creative Agent"]
    end
    
    subgraph "Knowledge & Data Layer"
        Neptune3["Neptune<br/>Graph + Ontology"]
        OS3["OpenSearch<br/>Vectors + Full-text"]
        S3_2["S3<br/>Documents + Artifacts"]
        External["External APIs<br/>Weather, News, etc."]
    end
    
    subgraph "AI/ML Layer"
        Bedrock["AWS Bedrock<br/>Claude/Llama"]
        SageMaker2["SageMaker<br/>Custom Models"]
        StepFunctions2["Step Functions<br/>Workflow Orchestration"]
    end
    
    UI --> API3
    API3 --> Orchestrator2
    Orchestrator2 --> ToTEngine
    Orchestrator2 --> AgentMemory
    
    ToTEngine --> Agent1
    ToTEngine --> Agent2
    ToTEngine --> Agent3
    ToTEngine --> Agent4
    ToTEngine --> Agent5
    ToTEngine --> Agent6
    
    Agent1 --> Neptune3
    Agent1 --> OS3
    Agent2 --> Bedrock
    Agent3 --> Neptune3
    Agent4 --> SageMaker2
    Agent5 --> S3_2
    Agent6 --> External
    
    Orchestrator2 --> StepFunctions2
    StepFunctions2 --> Bedrock
    
    style Orchestrator2 fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style ToTEngine fill:#FF6B9D,stroke:#232F3E,stroke-width:3px
    style Bedrock fill:#9D4EDD,stroke:#232F3E,stroke-width:2px
```

### Cost Estimation (Future² Architecture)

**Additional Components**:

| Component | Configuration | Monthly Cost | Notes |
|-----------|--------------|--------------|-------|
| **AWS Bedrock** | Claude 3.5 Sonnet | $50-200 | Based on token usage (10K-40K requests) |
| **DynamoDB** | Agent Memory (On-demand) | $10-25 | State storage + conversation history |
| **ElastiCache** | Redis t3.small | $15 | Agent state caching |
| **Additional Lambda** | 4 agent functions | $5-10 | Specialized agent logic |
| **Step Functions** | Agent orchestration | $5-15 | Complex workflows |
| **CloudWatch** | Enhanced monitoring | $5-10 | Agent metrics + traces |
| **X-Ray** | Distributed tracing | $3-5 | Agent interaction tracing |
| **TOTAL (Additional)** | | **$93-280** | On top of existing $259 |
| **GRAND TOTAL** | | **$352-539** | Complete agentic system |

**Cost Optimization**:
- 💡 Use Bedrock On-Demand vs Provisioned Throughput
- 💡 Cache agent responses in ElastiCache
- 💡 Implement agent result memoization
- 💡 Use Step Functions Express for high-volume workflows

---

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

### Current Implementation
1. **Complete System Architecture** - Full end-to-end flow
2. **Upload Pipeline Detail** - Sequence diagram of upload
3. **Processing Pipeline** - State machine visualization
4. **Data Flow with Ontology** - Validation flow (🆕 NEW)
5. **VPC Architecture** - Network layout
6. **Neptune & OpenSearch** - Data store architecture
7. **Ontology Structure** - OWL class diagram (🆕 NEW)
8. **SageMaker Embedding** - ML pipeline
9. **Cost Breakdown** - Monthly costs with optimization tips

### Future Roadmap
10. **Query Pipeline (Future)** - Basic RAG retrieval with LLM

### Advanced Future (Future²) 🚀
11. **Multi-Agent Architecture** - Tree of Thoughts with specialized agents
12. **Tree of Thoughts Reasoning Flow** - Sequence diagram of agent reasoning
13. **Agent Collaboration Pattern** - Observe-Think-Plan-Act-Reflect loop
14. **Tree of Thoughts Expansion** - Branch generation and pruning
15. **Multi-Agent System Architecture** - Complete agentic system with AWS Bedrock
16. **Future² Cost Estimation** - Additional components and optimization

### Deployment & Reference
17. **Deployment Timeline** - Setup stages
18. **Legend** - Diagram symbols and conventions

