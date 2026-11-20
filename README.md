# LLMs on GCP: From RAG to Agentic AI (3-Hour Hands-On Lab)

**Session Duration:** 3.0 Hours (180 Minutes)  
**Author:** [Ujala Jha](https://ujalajha.me) (`ujalajha.me`)  
**Enterprise Use Case:** CloudCorp Smart Assistant (AskHR Agent)  

---

## Table of Contents
1. [Session Overview & Architecture](#session-overview)
2. [Budget & Cost Guardrails](#budget-guardrails)
3. [Prerequisites & System Requirements](#prerequisites)
4. [Environment Setup & Dependencies](#environment-setup)
5. [Section 1: Ingestion & Document Corpus Setup (20 Mins)](#section-1)
6. [Section 2: Building Grounded RAG Pipeline (55 Mins)](#section-2)
7. [Section 3: Extending RAG to an Agentic AI Workflow (25 Mins)](#section-3)
8. [Section 4: Production Deployment Track — Serverless Microservices (50 Mins)](#section-4)
   - [Track 4A: Serverless Production Deployment (Cloud Run + In-Memory RAG)](#track-4a)
   - [Bonus Section 4B: Scaling to Millions of Documents with Vertex AI Vector Search](#bonus-section-4b)
9. [Section 5: Production Architecture & Cost Controls (10 Mins)](#section-5)
10. [Section 6: Mandatory Resource Cleanup (10 Mins)](#section-6)
11. [Troubleshooting & Enterprise Best Practices (Learnings & Gotchas)](#troubleshooting)
---

<a id="session-overview"></a>
## Session Overview & Architecture

In this 3-hour workshop, learners build, deploy, and observe a production-ready enterprise GenAI application using **Google Cloud Platform (GCP)** managed services. 

The lab follows a continuous business story: **CloudCorp**, a global enterprise modernizing its internal employee support operations with an intelligent **AskHR Agent**.

```mermaid
flowchart TD
    subgraph Client["Employee Requests"]
        U1["Scenario 1: 'What is remote work policy?'"]
        U2["Scenario 2: 'My laptop screen is broken'"]
        U3["Scenario 3: 'What is status of INC-501?'"]
    end

    U1 --> Agent
    U2 --> Agent
    U3 --> Agent

    subgraph Orchestration["Agent Orchestrator (Cloud Workflows)"]
        Agent{"AskHR Agent<br/>Intent Router"}
    end

    subgraph KnowledgeLayer["Knowledge Layer (Cloud Run)"]
        RAG["CloudCorp RAG Service<br/>(FastAPI Microservice)<br/>• text-embedding-004<br/>• Gemini 3.5 Flash Lite Grounding"]
        GCS[("Google Cloud Storage<br/>• hr_pto_policy.txt<br/>• it_laptop_policy.txt<br/>• remote_work_policy.txt")]
        RAG -->|Chunk & Search| GCS
    end

    subgraph ActionLayer["Action Layer (Cloud Functions)"]
        Tool["IT Helpdesk Tool<br/>(Python 3.11 HTTP Function)<br/>• action='create' -> Ticket INC-501<br/>• action='check' -> Status Lookup"]
    end

    %% Dynamic Routing Branches
    Agent -->|"Branch 1: Policy Guidance"| RAG
    Agent -->|"Branch 2: Replacement Request"| RAG
    RAG -.->|"Auto-generate replacement ticket"| Tool
    Agent -->|"Branch 3: Ticket Status Query"| Tool

    %% Output Node
    Out(["Unified Synthesized Response<br/>(Grounded Policy / New Ticket ID / Live Status)"])
    RAG --> Out
    Tool --> Out

    classDef gcp fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#1A202C;
    classDef storage fill:#ECFDF5,stroke:#10B981,stroke-width:2px,color:#065F46;
    classDef action fill:#FEF3C7,stroke:#F59E0B,stroke-width:2px,color:#92400E;
    classDef router fill:#F3E8FF,stroke:#8B5CF6,stroke-width:2px,color:#4C1D95;
    class Agent router;
    class RAG gcp;
    class GCS storage;
    class Tool action;
```

```
+-----------------------------------------------------------------------------------------+
|                                    EMPLOYEE QUERIES                                     |
|   [Scenario 1: Policy QA]    |   [Scenario 2: Broken Laptop]   |  [Scenario 3: Status]  |
|  "What is remote work rule?" | "Laptop screen is broken"       | "Status of INC-501?"   |
+------------------------------+---------------------------------+------------------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------+
|                                      AskHR Agent                                        |
|                          (Orchestrated via Cloud Workflows)                             |
|                                                                                         |
|       [Intent: Policy QA]          [Intent: Damaged Device]        [Intent: Ticket ID]  |
|               |                                |                            |           |
+---------------+--------------------------------+----------------------------+-----------+
                |                                |                            |
                v                                v                            |
+---------------------------------------------------------------+             |
|                 KNOWLEDGE LAYER: RAG SERVICE                  |             |
|                    (Cloud Run Microservice)                   |             |
|                                                               |             |
|  • Semantic Chunking via '\n---'                              |             |
|  • Embeddings: Vertex AI text-embedding-004                   |             |
|  • Reasoning: Gemini 3.5 Flash Lite Grounding                      |             |
|  • Source Corpus: Google Cloud Storage (GCS)                  |             |
+---------------------------------------------------------------+             |
                |                                |                            |
                | (Returns Policy)               | (Auto-triggers             |
                |                                |  ticket creation)          |
                |                                v                            v
                |               +---------------------------------------------------------+
                |               |                ACTION LAYER: IT TOOL                    |
                |               |              (Cloud Functions 2nd Gen)                  |
                |               |                                                         |
                |               |  • action="create" -> Creates ticket INC-501 for loaner |
                |               |  • action="check"  -> Queries live ticket status & ETA  |
                |               +---------------------------------------------------------+
                |                                                |
                v                                                v
+-----------------------------------------------------------------------------------------+
|                               UNIFIED SYNTHESIZED RESPONSE                              |
|   Scenario 1: Grounded Remote Work Policy (3 days/wk, 10-3 core hours, $500 stipend)    |
|   Scenario 2: Hardware Policy + Newly Generated Ticket INC-501 + Loaner Pickup Protocol |
|   Scenario 3: Live Helpdesk Progress (Approved, Assigned: Floor 2 Desk, ETA: 24 Hours)  |
+-----------------------------------------------------------------------------------------+
```

### The Three Operational Scenarios

1. **Scenario 1 — Pure Policy Grounding (RAG Path):**
   * **User Asks:** *"What is remote work policy?"*
   * **AskHR Agent Routing:** Directs query to the RAG knowledge layer. Cites CloudCorp's hybrid guidelines: employees can work remotely up to 3 days per week with core hours 10 AM to 3 PM and a $500 home office stipend. Zero external tool calls.
2. **Scenario 2 — Equipment Malfunction $\to$ RAG Policy + Autonomous Ticket Creation (Agentic Path):**
   * **User Asks:** *"My laptop screen is broken and flickering, what should I do?"*
   * **AskHR Agent Routing:** Retrieves IT hardware policy confirming screen fractures qualify for expedited replacement, automatically invokes the helpdesk tool to generate replacement ticket **`INC-501`**, and instructs the employee to pick up an emergency loaner at the Floor 2 Tech Depot.
3. **Scenario 3 — Live Incident Status Check (Tool Path):**
   * **User Asks:** *"What is the status of my ticket INC-501?"*
   * **AskHR Agent Routing:** Extracts incident identifier `INC-501`, queries the live helpdesk database, and returns real-time progress (`Status: Created / Approved for Loaner`, `Assigned: Hardware Desk`, `ETA: 24h`).

---

<a id="budget-guardrails"></a>
## Budget & Cost Guardrails

This workshop is engineered to execute safely with minimal to no cost:

| GCP Service | Lab Usage Configuration | Cost Model / Free Tier | Projected Cost |
| :--- | :--- | :--- | :--- |
| **Cloud Storage** | 1 regional bucket, 3 policy text files (< 100 KB total) | $0.02 / GB / mo | **<$0.001** |
| **Vertex AI Embeddings** | `text-embedding-004` (~25 chunks embedded across lab) | $0.000025 per 1,000 characters | **<$0.002** |
| **Vertex AI Gemini** | `gemini-3.5-flash-lite` (~30 queries during testing) | $0.075 / 1M input tokens, $0.30 / 1M output tokens | **<$0.03** |
| **Cloud Run** | 1 service, 512 MiB RAM, 1 vCPU, min-instances=0 | First 2M requests & 180,000 vCPU-sec free/mo | **$0.00** |
| **Cloud Functions** | 1 function, 256 MiB RAM, min-instances=0 | First 2M invocations free/mo | **$0.00** |
| **Cloud Workflows** | ~15 test executions (under 100 steps) | First 5,000 internal steps free/mo | **$0.00** |
| **Total Estimated Spend**| | | **~$0.05 – $0.20** |

> [!WARNING]
> **Vector Search Endpoint Cost Trap:** In full production, Vertex AI Vector Search deploys to dedicated VM nodes (`e2-standard-2`) costing ~$0.25 to $0.35/hour that **do not scale down to zero**. To eliminate lingering charges, our hands-on lab runs vector cosine similarity in memory on Cloud Run / Colab, while the lecture explains how dedicated Vector Search endpoints operate at scale.

---

<a id="prerequisites"></a>
## Prerequisites & System Requirements

Before beginning the workshop, review the following account, runtime, and developer environment requirements:

### 1. Developer Environment & IDE (Choose One)

| Environment / IDE | Recommendation | When to Use | Setup Notes |
| :--- | :--- | :--- | :--- |
| **Google Cloud Shell & Cloud Shell Editor** | 🌟 **Top Recommendation** (preffered for this lab) | Fastest zero-install setup directly in browser | Pre-installed with `gcloud`, `git`, `python3.11`, `curl`, and a browser-based VS Code interface. No local installation required! |
| **VS Code / Cursor (Local)** | Recommended for Local Dev | Developing and debugging locally on your laptop | Requires **Python extension** (`ms-python.python`) and **Jupyter extension** (`ms-toolsai.jupyter`) for opening `.ipynb` notebooks. |
| **Google Colab** | Recommended for Notebook Track | Running only the interactive notebooks (`notebooks/`) | Zero-install cloud Jupyter runtime. Works directly with `google.colab.auth.authenticate_user()`. |
| **PyCharm (Professional / Community)** | Optional | JetBrains IDE preference | Configure Python 3.10 or 3.11 virtual environment as the project interpreter. |

---

### 2. Runtime & Software Requirements

* **Python Runtime:**
  * **Required Version:** **Python 3.10** or **Python 3.11** *(Python 3.11 strongly recommended)* to match the Cloud Functions 2nd Gen runtime (`python311`) and Cloud Run container.
  * Check version: `python3 --version`
* **Python Package Manager (`pip`):**
  * `pip >= 23.0`
  * Check version: `pip --version`
* **Google Cloud SDK (`gcloud` CLI):**
  * Version: **`gcloud >= 480.0.0`** (Pre-installed in Google Cloud Shell).
  * Check version: `gcloud --version`
  * If running locally, install via [Google Cloud SDK Installation Guide](https://cloud.google.com/sdk/docs/install) or on macOS: `brew install google-cloud-sdk`.
* **Git CLI:**
  * `git >= 2.30.0` for cloning and managing the lab repository.
  * Check version: `git --version`
* **HTTP Client (`curl`):**
  * Pre-installed on macOS, Linux, and Cloud Shell for running REST verification smoke tests against deployed microservices.

---

### 3. Google Cloud Platform (GCP) Account & Access

* **Active GCP Project:** An active Google Cloud project with billing enabled (e.g. standard personal GCP account, or student sandbox project provided by UpGrad / NuveLabs / Qwiklabs).
* **IAM Permissions:** Your account should have **`Editor`** (`roles/editor`) or **`Owner`** access to enable APIs, create Cloud Storage buckets, deploy Cloud Run services, deploy Cloud Functions, and register Cloud Workflows.
* **Target GCP Region:** **`us-central1`** (Iowa) is used throughout this workshop for low cost and immediate availability of Vertex AI `text-embedding-004` and Cloud Storage. Foundation model reasoning uses the **`global`** endpoint (`gemini-3.5-flash-lite`).

---

### 4. Operating System Compatibility

* **macOS:** Fully compatible with default `zsh` or `bash`.
* **Linux (Ubuntu, Debian, RedHat):** Fully compatible with `bash`.
* **Windows:**
  * **Recommended:** Use **Google Cloud Shell** directly in Chrome/Edge, or use **WSL2 (Windows Subsystem for Linux)** with Ubuntu.
  * *Avoid running bash deployment scripts (`.sh`) directly in native Windows Command Prompt (cmd) or Windows PowerShell.*

---

<a id="environment-setup"></a>
## Environment Setup & Dependencies


### 🛠️ Step 0: Setup in Google Cloud Shell Editor (Recommended)

The fastest and most reliable way to execute this is inside **Google Cloud Shell Editor** (a full browser-based VS Code environment with pre-authenticated `gcloud`):

1. **Open Google Cloud Shell Editor:**
   In the [Google Cloud Console](https://console.cloud.google.com/), click the **`>_`** terminal icon in the top-right navbar, then click the **Open Editor** button on the Cloud Shell toolbar.

2. **Clone the Repository in Cloud Shell:**
   Open the terminal inside Cloud Shell and clone the lab repository:
   ```bash
   git clone https://github.com/UjalaJha/cloudcorp-llms-on-gcp-lab.git
   cd cloudcorp-llms-on-gcp-lab
   ```
   *(To open this repository in the Editor file explorer sidebar, run: `cloudshell workspace .` or click **File** $\to$ **Open Folder** $\to$ `cloudcorp-llms-on-gcp-lab`)*.

3. **Generate and Source `.env` (Why `cat` is Needed Here):**
   > [!IMPORTANT]
   > **Why is the `cat` step required right here?**  
   > 1. `.env` is in `.gitignore` to prevent leaking cloud secrets, so `git clone` intentionally does not include it.  
   > 2. Uploading a `.env` file from your local laptop through the Cloud Shell web upload dialog often fails or suppresses the file because it is a hidden UNIX dotfile (`.*`).  
   > 
   > Running this one-liner directly in your Cloud Shell terminal creates `.env`, automatically populates your active `PROJECT_ID`, and exports all variables into your shell session in one step:

   ```bash
   cat << EOF > .env
   PROJECT_ID=$(gcloud config get-value project)
   REGION=us-central1
   BUCKET_NAME=$(gcloud config get-value project)-cloudcorp-policies
   EMBEDDING_MODEL=text-embedding-004
   GENERATIVE_MODEL=gemini-3.5-flash-lite
   EOF

   set -a; source .env; set +a
   ```
 

4. **Enable Services:**
    ```bash
      # 1. Set your active Project ID
      gcloud config set project $PROJECT_ID

      # 2. Enable Vertex AI, Cloud Storage, Serverless, and Build APIs
      gcloud services enable \
        aiplatform.googleapis.com \
        storage.googleapis.com \
        run.googleapis.com \
        cloudfunctions.googleapis.com \
        workflows.googleapis.com \
        artifactregistry.googleapis.com \
        cloudbuild.googleapis.com

      echo "✅ All CloudCorp workshop services successfully activated for $PROJECT_ID!"
    ```


---

### Do You Need a Virtual Environment (`venv`)?
* **If running in Google Colab:** **No `venv` needed.** Colab runs inside an isolated container VM. The notebooks are 100% self-bootstrapping (auto-installing required libraries and auto-populating policy files if running standalone). Just ensure:

* **If running locally on your laptop / Mac:** **Yes, using a `venv` is recommended** to prevent package conflicts with your system Python:
  ```bash
  # 1. Create and activate virtual environment
  python3 -m venv .venv
  source .venv/bin/activate

  # 2. Install required workshop dependencies
  pip install -r requirements.txt
  ```

### Centralized Configuration (`.env`)

Depending on your environment, configure `.env`:

#### Running Locally on Laptop
Copy the provided `.env.example` to `.env` and fill in your GCP project details:
```bash
cp .env.example .env
```
In `.env`:
```env
PROJECT_ID=your-gcp-project-id
REGION=us-central1
BUCKET_NAME=your-gcp-project-id-cloudcorp-policies
EMBEDDING_MODEL=text-embedding-004
GENERATIVE_MODEL=gemini-3.5-flash-lite

# Optional: Path to local Service Account JSON key (for running locally without gcloud)
# Leave blank if running in Google Colab (Colab uses built-in OAuth popup)
GOOGLE_APPLICATION_CREDENTIALS=
```
*(All notebooks in `notebooks/` automatically detect and load `.env` at runtime!)*

### How to Generate & Configure `GOOGLE_APPLICATION_CREDENTIALS` (For Local Execution)

If running locally on your laptop without the `gcloud` CLI installed, generate a Service Account JSON key using **either** Cloud Shell commands or the manual GCP Console:

#### Option A: Cloud Shell Commands Only (Fastest — 10 Seconds)

Open **Google Cloud Shell** (`>_` icon in top-right of [GCP Console](https://console.cloud.google.com/)) and run:

```bash
# 1. Set your Project ID
PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# 2. Create the Service Account
gcloud iam service-accounts create cloudcorp-lab-sa \
  --display-name="CloudCorp Lab Service Account"

# 3. Grant the Editor role (covers Vertex AI and Cloud Storage)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/editor"

# 4. Generate the private JSON key
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 5. Automatically download the key file to your laptop
cloudshell download gcp-key.json
```

---

#### Option B: Manual Console Steps (Via GCP Web UI)

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select your project.
2. In the navigation menu (☰), go to **IAM & Admin** $\to$ **Service Accounts**.
3. Click **+ CREATE SERVICE ACCOUNT** at the top:
   * **Name:** `cloudcorp-lab-sa`
   * Click **CREATE AND CONTINUE**.
4. **Grant Access:** In the **Select a role** dropdown, choose **Basic** $\to$ **Editor** (or type `Editor`). Click **CONTINUE**, then **DONE**.
5. **Download Key:** Click on the newly created `cloudcorp-lab-sa` email $\to$ go to the **KEYS** tab $\to$ click **ADD KEY** $\to$ **Create new key** $\to$ choose **JSON** $\to$ **CREATE**.

---

#### Step 3: Link Key in `.env`
Place the downloaded file into this project directory as `gcp-key.json` and set it in `.env`:
```env
GOOGLE_APPLICATION_CREDENTIALS=gcp-key.json
```
*(All notebooks in `notebooks/` automatically detect and load this key at runtime on Step 1.2).*

> [!WARNING]
> Never commit your private JSON service account key to Git! Our repository's `.gitignore` already blocks `.env` and `*.json` key files.

---

<a id="section-1"></a>
## Section 1: Ingestion & Document Corpus Setup

### Concept & Theory
In an enterprise LLM architecture, raw knowledge assets reside in centralized object storage (**Google Cloud Storage**) before vectorization. Documents must be loaded dynamically from the file repository rather than hardcoded in application logic.

### Sample Policy Corpus (`sample_policies/`)
* `hr_pto_policy.txt`: Multi-section HR document covering accrual, 5-day rollover limit, March 31 expiration, medical note requirement (>3 days sick), quarterly financial close blackout periods.
* `it_laptop_policy.txt`: 36-month hardware refresh cycles, damaged equipment replacement procedure, and same-day loaner protocols.
* `remote_work_policy.txt`: Up to 3 days/week remote, core hours 10 AM – 3 PM, $500 annual home office stipend.

### 👉 Hands-On Execution
Open and execute the Section 1 notebook:
➡️ **[`notebooks/01_Section1_Setup_and_Corpus.ipynb`](notebooks/01_Section1_Setup_and_Corpus.ipynb)**

---

<a id="section-2"></a>
## Section 2: Building Grounded RAG Pipeline

### Concept & Theory
1. **Semantic Section Chunking:** Documents are divided along logical section boundaries (`\n---`) to preserve self-contained legal and operational context.
2. **Asymmetric Embeddings (`text-embedding-004`):**
   * Uses `task_type="RETRIEVAL_DOCUMENT"` when indexing policy chunks into vector space.
   * Uses `task_type="RETRIEVAL_QUERY"` when embedding short user questions.
3. **In-Memory Cosine Similarity:** Fast vector dot-product scoring without recurring cluster charges.
4. **Grounded Generation (Gemini 3.5 Flash Lite):** Retrieved context chunks are injected into Gemini's system prompt with strict anti-hallucination guardrails and source citation tracking (`chunk_id`).

### Sample Test Queries & Grounded Answers
* **Query 1:** *"How many days of PTO can I carry over, and when do they expire?"*  
  ➔ **Grounded Answer:** Cites Section 2: maximum 5 days carry-over, strictly expiring on March 31 of Q1.
* **Query 2:** *"Do I need to submit a doctor's certificate if I take sick leave for 4 days?"*  
  ➔ **Grounded Answer:** Cites Section 4: medical certificate required for illness exceeding 3 consecutive days.
* **Query 3:** *"Can I take 2 weeks off during the end of December?"*  
  ➔ **Grounded Answer:** Cites Section 3: extended leaves prohibited during Q4 financial close blackout (Dec 25-31).

### 👉 Hands-On Execution
Open and execute the Section 2 notebook:
➡️ **[`notebooks/02_Section2_RAG_Pipeline.ipynb`](notebooks/02_Section2_RAG_Pipeline.ipynb)**

> [!TIP]
> **Cloud Shell Editor ADC Quota Project Tip:**
> If running in Google Cloud Shell Editor with user credentials and you encounter a `403 PermissionDenied ... consumer: projects/618104708054` error in Cell 2, run this one command in your Cloud Shell terminal:
> ```bash
> gcloud auth application-default set-quota-project $(gcloud config get-value project)
> ```
> This permanently attaches your project ID as the quota project for Vertex AI.

*(Note: The exact same chunking and grounded retrieval logic is packaged inside [`rag_service/main.py`](rag_service/main.py) for serverless deployment on Google Cloud Run).*

---

<a id="section-3"></a>
## Section 3: Extending RAG to an Agentic AI Workflow

### Concept & Theory
Static RAG can only read; it cannot take action, file tickets, or query live databases. An **Agentic AI Workflow** adds:
1. **Autonomous Tool Declarations:** Vertex AI `FunctionDeclaration` defines external tools that Gemini can call.
2. **Tool 1 (`create_it_ticket`):** Automatically creates a replacement incident ticket (`INC-501`) when damaged hardware is reported.
3. **Tool 2 (`lookup_it_ticket`):** Queries live helpdesk status by ticket ID.
4. **Autonomous Reasoning Loop:** Gemini inspects user intent, decides whether tools are required, invokes them, and synthesizes a final response.

### Sample Execution Across the 3 Scenarios
* **Scenario 1 (Pure Policy):** *"What is remote work policy?"* ➔ Gemini answers directly from policy chunks with zero tool invocations.
* **Scenario 2 (Hardware Malfunction):** *"My laptop screen is broken and flickering, what should I do?"* ➔ Gemini retrieves replacement policy, autonomously calls `create_it_ticket`, and returns ticket `INC-501` with Floor 2 loaner pickup steps.
* **Scenario 3 (Status Check):** *"What is the status of my ticket INC-501?"* ➔ Gemini calls `lookup_it_ticket` and returns real-time progress (`Status: Created / Approved for Loaner`).

### 👉 Hands-On Execution
Open and execute the Section 3 notebook:
➡️ **[`notebooks/03_Section3_Agentic_Workflow.ipynb`](notebooks/03_Section3_Agentic_Workflow.ipynb)**

*(Note: In production on GCP, tools run on **Cloud Functions** [`ticket_tool/main.py`](ticket_tool/main.py) and multi-step decisions are orchestrated declaratively via **Cloud Workflows** [`workflows/workflow.yaml`](workflows/workflow.yaml)).*

---

<a id="section-4"></a>
## Section 4: Production Deployment Track — Serverless Microservices

> [!NOTE]
> **Pedagogical Note for Learners & Instructors:**  
> In Sections 1 through 3, you prototyped, tested, and evaluated RAG and agentic tool-calling interactively inside Python notebooks.  
> In this production track, you deploy that exact same code into live enterprise serverless infrastructure on Google Cloud Platform:
> * **Cloud Run** hosts the containerized FastAPI RAG service (`rag_service/`).
> * **Cloud Functions (2nd Gen)** hosts the lightweight IT helpdesk tool (`ticket_tool/`).
> * **Cloud Workflows** orchestrates the multi-step intent routing and tool execution (`workflows/workflow.yaml`).

### Architecture: How the Live Services Connect

```mermaid
flowchart LR
    Client["Client / Cloud Shell<br/>(gcloud workflows run)"] -->|1. User Query| WF["Cloud Workflows<br/>(Intent Router)"]
    
    subgraph KnowledgeLayer["Knowledge Layer"]
        WF -->|"2. POST /ask (Query)"| CR["Cloud Run<br/>(rag_service/main.py)"]
        CR -->|Retrieve & Ground| GCS[("Cloud Storage<br/>(Policies)")]
        CR -->|"3. Policy Context"| WF
    end
    
    subgraph ActionLayer["Action Layer"]
        WF -->|"4. POST (create/check)"| CF["Cloud Function<br/>(ticket_tool/main.py)"]
        CF -->|"5. Ticket INC-501"| WF
    end
    
    WF -->|"6. Unified Response"| Client

    classDef gcp fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#1A202C;
    classDef storage fill:#ECFDF5,stroke:#10B981,stroke-width:2px,color:#065F46;
    classDef action fill:#FEF3C7,stroke:#F59E0B,stroke-width:2px,color:#92400E;
    classDef router fill:#F3E8FF,stroke:#8B5CF6,stroke-width:2px,color:#4C1D95;
    class WF router;
    class CR gcp;
    class GCS storage;
    class CF action;
```

---

### 🛠️ Step 0: Setup in Google Cloud Shell Editor (Recommended)

If you executed Sections 1 through 3 in Google Colab or locally, Section 4 transitions to live cloud serverless infrastructure. The fastest and most reliable way to execute this is inside **Google Cloud Shell Editor** (a full browser-based VS Code environment with pre-authenticated `gcloud`):

1. **Open Google Cloud Shell Editor:**
   In the [Google Cloud Console](https://console.cloud.google.com/), click the **`>_`** terminal icon in the top-right navbar, then click the **Open Editor** button on the Cloud Shell toolbar.

2. **Clone the Repository in Cloud Shell:**
   Open the terminal inside Cloud Shell and clone the lab repository:
   ```bash
   git clone https://github.com/UjalaJha/cloudcorp-llms-on-gcp-lab.git
   cd cloudcorp-llms-on-gcp-lab
   ```
   *(To open this repository in the Editor file explorer sidebar, run: `cloudshell workspace .` or click **File** $\to$ **Open Folder** $\to$ `cloudcorp-llms-on-gcp-lab`)*.

3. **Generate and Source `.env` (Why `cat` is Needed Here):**
   > [!IMPORTANT]
   > **Why is the `cat` step required right here?**  
   > 1. `.env` is in `.gitignore` to prevent leaking cloud secrets, so `git clone` intentionally does not include it.  
   > 2. Uploading a `.env` file from your local laptop through the Cloud Shell web upload dialog often fails or suppresses the file because it is a hidden UNIX dotfile (`.*`).  
   > 
   > Running this one-liner directly in your Cloud Shell terminal creates `.env`, automatically populates your active `PROJECT_ID`, and exports all variables into your shell session in one step:

   ```bash
   cat << EOF > .env
   PROJECT_ID=$(gcloud config get-value project)
   REGION=us-central1
   BUCKET_NAME=$(gcloud config get-value project)-cloudcorp-policies
   EMBEDDING_MODEL=text-embedding-004
   GENERATIVE_MODEL=gemini-3.5-flash-lite
   EOF

   set -a; source .env; set +a
   ```

4. **Inspect the Service Code in the Editor:**
   In the Cloud Shell Editor file tree, you can now inspect the production code you are about to deploy:
   * [`rag_service/main.py`](rag_service/main.py) & [`rag_service/Dockerfile`](rag_service/Dockerfile): Containerized FastAPI RAG service.
   * [`ticket_tool/main.py`](ticket_tool/main.py): Cloud Functions 2nd Gen IT helpdesk tool.
   * [`workflows/workflow.yaml`](workflows/workflow.yaml): Cloud Workflows declarative intent router.

---

<a id="track-4a"></a>
### Track 4A: Serverless Production Deployment (Cloud Run + In-Memory NumPy RAG)

### Option A: 1-Click Automated Deployment Script (Not Recommended for Lab)

In **Google Cloud Shell**, run our automated deployment script:
```bash
./deploy_production.sh
```
*(The script automatically reads and exports `PROJECT_ID`, `REGION`, and `BUCKET_NAME` directly from your `.env` file, verifies APIs, deploys Cloud Run, deploys Cloud Function, deploys Cloud Workflows with environment linking, and runs live verification tests across all 3 scenarios).*

---

### Option B: Step-by-Step Manual Deployment (Recommended for Learning)

First, load your environment variables (or auto-create `.env` if not uploaded) and authorize service account permissions upfront:
```bash

# Ensure the lab Service Account exists and grant required roles
gcloud iam service-accounts create cloudcorp-lab-sa \
  --display-name="CloudCorp Lab Service Account" \
  --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/editor" \
  --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet
```
*(This instantly ensures your service account has authorization to invoke Cloud Run and generate workflow OIDC tokens).*

#### Step 1: Deploy Cloud Run RAG Service (Knowledge Layer)
The RAG logic from Notebook 2 is packaged inside `rag_service/main.py` with FastAPI and a `Dockerfile`.
Deploy the containerized service:
```bash
gcloud run deploy cloudcorp-rag-service \
  --source=rag_service \
  --region=${REGION:-us-central1} \
  --service-account="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME:-${PROJECT_ID}-cloudcorp-policies},REGION=${REGION:-us-central1},GENERATIVE_MODEL=gemini-3.5-flash-lite,GENAI_LOCATION=global"
```

Capture the live service URL:
```bash
export RAG_SERVICE_URL=$(gcloud run services describe cloudcorp-rag-service --region=${REGION:-us-central1} --format='value(status.url)')
echo "✅ Cloud Run RAG URL: $RAG_SERVICE_URL"
```

**Quick Smoke Test:**
```bash
curl -X POST "${RAG_SERVICE_URL}/ask" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many days of PTO can I carry over?"}'
```

---

#### Step 2: Deploy Cloud Function IT Helpdesk Tool (Action Layer)
The helpdesk ticketing tool from Notebook 3 is packaged inside `ticket_tool/main.py` as a serverless 2nd Gen HTTP function.
Deploy the HTTP function:
```bash
gcloud functions deploy cloudcorp-ticket-tool \
  --gen2 \
  --runtime=python311 \
  --source=ticket_tool \
  --entry-point=handle_it_ticket \
  --trigger-http \
  --service-account="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --region=${REGION:-us-central1}
```

> [!NOTE]
> **Encountered `Permission 'run.services.setIamPolicy' denied` during function deploy?**  
> In student and lab sandbox environments (e.g. NuveLabs / UpGrad), individual service-level IAM modification is locked down by GCP organization policies. The function container itself **deploys successfully**! We authorize invocations cleanly in Step 3 via project-level role bindings (`gcloud projects add-iam-policy-binding`).

Capture the live function URI:
```bash
export TICKET_TOOL_URL=$(gcloud functions describe cloudcorp-ticket-tool --region=${REGION:-us-central1} --format='value(serviceConfig.uri)')
echo "✅ Cloud Function Tool URL: $TICKET_TOOL_URL"
```

**Quick Smoke Test:**
```bash
curl -X POST "${TICKET_TOOL_URL}" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"action": "create", "summary": "Broken MacBook display", "category": "Hardware Replacement"}'
```

---

#### Step 3: Deploy Cloud Workflows Intent Router (Orchestration Layer)
Deploy the declarative YAML workflow linking Cloud Run and Cloud Functions:  
*(⚠️ **Syntax Note:** Cloud Workflows strictly uses `--location`, NOT `--region`)*
```bash
gcloud workflows deploy cloudcorp-agent-workflow \
  --source=workflows/workflow.yaml \
  --location=${REGION:-us-central1} \
  --service-account="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="RAG_SERVICE_URL=${RAG_SERVICE_URL},TICKET_TOOL_URL=${TICKET_TOOL_URL}"

echo "✅ Cloud Workflows deployed successfully!"
```

---

#### Step 4: Live Execution Across the 3 Enterprise Scenarios

Now execute the complete agentic pipeline directly from Cloud Shell:

**Scenario 1: Pure Policy Grounding (Zero Tool Calls)**
```bash
gcloud workflows run cloudcorp-agent-workflow \
  --location=${REGION:-us-central1} \
  --data='{"query": "What is remote work policy?"}'
```
*Expected Result:* Routes to Cloud Run RAG service; returns grounded policy with core working hours and equipment stipends.

**Scenario 2: Hardware Incident -> RAG Policy + Automatic Ticket Creation**
```bash
gcloud workflows run cloudcorp-agent-workflow \
  --location=${REGION:-us-central1} \
  --data='{"query": "My laptop screen is broken and flickering, what should I do?"}'
```
*Expected Result:* RAG confirms replacement eligibility ➔ automatically calls Cloud Function to generate ticket `INC-501` ➔ returns Floor 2 loaner pickup instructions.

**Scenario 3: Live Incident Status Lookup**
```bash
gcloud workflows run cloudcorp-agent-workflow \
  --location=${REGION:-us-central1} \
  --data='{"query": "What is the status of my ticket INC-501?", "ticket_id": "INC-501"}'
```
*Expected Result:* Directly calls Cloud Function tool ➔ queries database ➔ returns live progress (`Status: Created / Approved for Loaner`).

---

<a id="bonus-section-4b"></a>
### 🎁 Bonus Section 4B: Scaling to Millions of Documents with Vertex AI Vector Search (Matching Engine)

> [!NOTE]
> **Enterprise Architecture Track:**  
> In **Track 4A**, we computed cosine similarity in-memory using NumPy inside our Cloud Run container (`rag_service/`). This is ideal for knowledge bases up to ~50,000 chunks because Cloud Run scales down to **zero instances**, costing **$0.00** when idle.  
> 
> However, enterprise corporations indexing **millions to billions of document vectors** cannot use linear $O(N)$ in-memory scanning. They require **Vertex AI Vector Search (Matching Engine)**: Google's sub-10ms, billion-scale Approximate Nearest Neighbor (ANN) vector database powered by the **ScaNN (Score-aware Approximate Nearest Neighbor)** algorithm.

#### In-Memory NumPy vs. Vertex AI Vector Search Comparison

| Dimension | Track 4A: In-Memory NumPy on Cloud Run | Track 4B: Vertex AI Vector Search (Matching Engine) |
| :--- | :--- | :--- |
| **Search Algorithm** | Exact Linear Scan ($O(N)$ brute-force cosine) | Approximate Nearest Neighbor ($O(\log N)$ ScaNN Tree-AH) |
| **Max Scale** | Up to ~50,000 vectors | **Billions** of dense vectors |
| **Retrieval Latency** | ~20ms – 150ms (increases with corpus size) | **<10ms P99** at 100,000+ QPS |
| **Idle Infrastructure Cost**| **$0.00** (Scales to zero on Cloud Run) | **~$0.25 to $0.35/hour** (Requires active VM node for index endpoint) |
| **Best For** | Departmental tools, FAQs, prototyping, workshops | Massive enterprise knowledge graphs, global vector search |

---

#### ⏱️ Lifecycle Timing & Execution Breakdown

> [!TIP]
> **Instructor & Student Guide:**  
> do not need to wait for full deployment to understand the architecture. The entire pipeline takes **~35 to 45 minutes**, with over **85% being passive cloud provisioning wait time**. GO through the code, architecture diagram, and review the cost trade-offs even if you choose not to deploy the live endpoint during class!

| Step / Phase | Action Taken | Duration | Type | Pedagogical Takeaway |
| :--- | :--- | :--- | :--- | :--- |
| **1. Chunk & Embed Corpus** | Python script generates 768-dim vectors (`text-embedding-004`) | **~30 sec** | Active Script | Shows how raw text transforms into dense geometric vectors. |
| **2. Build Tree-AH Index** | Vertex AI MapReduce clusters vectors into ScaNN leaf nodes | **~15–20 mins** | Passive GCP Wait | Demonstrates how billion-scale datasets are pre-indexed into fast search trees. |
| **3. Create Index Endpoint** | API call provisions public endpoint gateway | **~1–2 mins** | Passive GCP Wait | Sets up the network entrypoint for Cloud Run microservices. |
| **4. Deploy Index to Node** | GCP spins up dedicated serving VM (`e2-standard-2`/`16`), loads index to RAM | **~15–20 mins** | Passive GCP Wait | Explains why vector search cannot scale to zero (RAM residency is required for <10ms latency). |
| **5. Deploy Cloud Run Service** | Container builds & deploys FastAPI service (`rag_service_vector_search/`) | **~2–3 mins** | Active CLI | Shows standard microservice decoupling from vector storage. |
| **6. Query & Ground (`/ask`)** | Asymmetric retrieval + Gemini 3.5 Flash Lite synthesis | **~1–2 mins** | Live Test | Shows <10ms vector lookup + distance metrics returned in JSON. |
| **7. Mandatory Teardown** | Undeploy index and decommission endpoint VM | **~5–8 mins** | Active Script | Reinforces enterprise cloud financial governance (FinOps). |
| **Total Pipeline** | **End-to-End Enterprise Vector Search** | **~35–45 mins** | *(~5m Active / ~35m Passive)* | Complete enterprise scale-out architecture mastery. |

---

#### Architecture: Vertex AI Vector Search Microservice

```mermaid
flowchart LR
    Client["Client / Cloud Workflows<br/>(POST /ask)"] --> CR["Cloud Run Microservice<br/>(rag_service_vector_search/main.py)"]
    
    subgraph VertexAI["Vertex AI Managed Services"]
        CR -->|"1. Asymmetric Query Embedding"| TE["text-embedding-004<br/>(RETRIEVAL_QUERY)"]
        TE -->|"2. 768-dim Vector"| CR
        CR -->|"3. find_neighbors(q_vec)"| VE["Vector Search Index Endpoint<br/>(ScaNN Tree-AH Index)"]
        VE -->|"4. Top-K IDs + Distances"| CR
        CR -->|"6. Grounded Generation Prompt"| GEM["Gemini 3.5 Flash Lite<br/>(global)"]
        GEM -->|"7. Grounded Answer"| CR
    end
    
    subgraph Storage["Metadata Cache"]
        CR -->|"5. Resolve Chunk ID to Text"| GCS[("Google Cloud Storage<br/>(chunks_meta.json)")]
    end
    
    CR -->|"8. JSON Response (Answer + Citations + Distances)"| Client

    classDef gcp fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#1A202C;
    classDef storage fill:#ECFDF5,stroke:#10B981,stroke-width:2px,color:#065F46;
    classDef ai fill:#F3E8FF,stroke:#8B5CF6,stroke-width:2px,color:#4C1D95;
    class CR gcp;
    class GCS storage;
    class TE,VE,GEM ai;
```

---

#### Hands-On: How to Deploy & Test the Vector Search Service

The repository provides a dedicated, production-ready directory [`rag_service_vector_search/`](rag_service_vector_search/):
* [`rag_service_vector_search/index_policies.py`](rag_service_vector_search/index_policies.py): Pipeline script to embed corpus, upload JSONL to GCS, create Tree-AH Index, create Index Endpoint, and deploy.
* [`rag_service_vector_search/main.py`](rag_service_vector_search/main.py): Production FastAPI microservice querying `aiplatform.MatchingEngineIndexEndpoint.find_neighbors()`.
* [`rag_service_vector_search/cleanup_vector_search.sh`](rag_service_vector_search/cleanup_vector_search.sh): Automated one-click teardown script to undeploy and delete the endpoint.

##### Step 1: Run Batch Indexing & Index Deployment
In **Google Cloud Shell**, run:
```bash
python rag_service_vector_search/index_policies.py
```
*(This chunks policies from GCS, generates embeddings, uploads `gs://${BUCKET_NAME}/vector_search_data/embeddings.json`, creates the Tree-AH ScaNN index, and deploys it to a public endpoint. Building and deploying an index takes ~15-20 minutes in GCP).*

When complete, the script outputs your:
```bash
export INDEX_ENDPOINT_ID="projects/.../locations/us-central1/indexEndpoints/..."
export DEPLOYED_INDEX_ID="cloudcorp_policy_deployed"
```

##### Step 2: Deploy Cloud Run Vector Search Microservice
```bash
gcloud run deploy cloudcorp-rag-service-vector-search \
  --source=rag_service_vector_search \
  --region=${REGION:-us-central1} \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},REGION=${REGION:-us-central1},BUCKET_NAME=${BUCKET_NAME},INDEX_ENDPOINT_ID=${INDEX_ENDPOINT_ID},DEPLOYED_INDEX_ID=cloudcorp_policy_deployed" \
  --service-account="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --quiet
```

##### Step 3: Test Grounded Retrieval via Vector Search
```bash
VS_RAG_URL=$(gcloud run services describe cloudcorp-rag-service-vector-search --region=${REGION:-us-central1} --format="value(status.url)")

curl -X POST "${VS_RAG_URL}/ask" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many days of PTO can I carry over?", "top_k": 2}'
```

> [!CAUTION]
> **MANDATORY TEARDOWN FOR BONUS SECTION 4B:**  
> A deployed Vertex AI Vector Search endpoint deploys a dedicated virtual machine node (`e2-standard-2`) that **does not scale to zero**. To prevent ongoing charges (~$0.25/hr), immediately tear it down after testing:
> ```bash
> bash rag_service_vector_search/cleanup_vector_search.sh
> ```

---

<a id="section-5"></a>
## Section 5: Production Architecture & Cost Controls

### Concept & Theory
1. **Latency Profiles:** Standard RAG requires 1 retrieval + 1 LLM call (~1.2s). Agentic workflows require multiple reasoning and tool loops (~4.5s).
2. **Token Amplification:** Agents accumulate conversation history and tool schemas across turns. Guardrails include setting `max_steps=5` and concise tool parameters.
3. **Matryoshka Representation Learning (MRL):** `text-embedding-004` supports truncating 768-dim vectors to 256-dim, slashing memory usage by 66.7% with <1.5% loss in precision.
4. **Managed Vector Search vs. In-Memory:** When scaling to >100,000 vectors, transition from in-memory cosine to **Vertex AI Vector Search** with ScaNN.
5. **Least Priviledged Principle:** When scaling to prod, grant granular roles for resources needed rather than editor role.


### 👉 Hands-On Execution
Open and execute the Section 4 notebook:
➡️ **[`notebooks/04_Section4_Production_and_Costs.ipynb`](notebooks/04_Section4_Production_and_Costs.ipynb)**

---

<a id="section-6"></a>
## Section 6: Mandatory Resource Cleanup

To ensure zero ongoing charges and guarantee your total workshop bill remains under **$5.00** (projected actual: **<$0.30**), clean up all deployed compute instances, storage, container images, service accounts, and IAM bindings before concluding your session.

### Option A: 1-Click Automated Teardown Script (Recommended)

In **Google Cloud Shell** or your local terminal, run our automated teardown script:
```bash
./cleanup.sh
```
*(The script automatically reads `.env`, deletes Cloud Workflows, Cloud Functions, Cloud Run, Artifact Registry repositories, empties and deletes the GCS bucket, revokes all project-level IAM bindings, deletes the Service Account, and removes any local credential keys).*

---

### Option B: Step-by-Step Manual Teardown

If executing manually in Google Cloud Shell:

```bash
# Ensure environment variables are loaded
set -a; source .env; set +a
SERVICE_ACCOUNT="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 1. Delete Serverless Microservices
gcloud workflows delete cloudcorp-agent-workflow --location=${REGION:-us-central1} --quiet 2>/dev/null || true
gcloud functions delete cloudcorp-ticket-tool --region=${REGION:-us-central1} --quiet 2>/dev/null || true
gcloud run services delete cloudcorp-rag-service --region=${REGION:-us-central1} --quiet 2>/dev/null || true

# 2. Delete Artifact Registry Container Repositories (Built by source deploys)
gcloud artifacts repositories delete cloud-run-source-deploy --location=${REGION:-us-central1} --quiet 2>/dev/null || true
gcloud artifacts repositories delete gcf-artifacts --location=${REGION:-us-central1} --quiet 2>/dev/null || true

# 3. Empty and delete Google Cloud Storage bucket
gcloud storage rm -r "gs://${BUCKET_NAME}" 2>/dev/null || gsutil rm -r "gs://${BUCKET_NAME}" 2>/dev/null || true

# 4. Revoke Project-Level IAM Role Bindings
gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.invoker" \
  --quiet 2>/dev/null || true

gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet 2>/dev/null || true

gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/editor" \
  --quiet 2>/dev/null || true

# 5. Delete Service Account & Secret Credentials
gcloud iam service-accounts delete "${SERVICE_ACCOUNT}" --quiet 2>/dev/null || true
gcloud secrets delete cloudcorp-agent-key --quiet 2>/dev/null || true
rm -f gcp-key.json

echo "=== Cleanup completed! All lab resources, IAM bindings, and credentials successfully removed. ==="
```

---

<a id="troubleshooting"></a>
## Troubleshooting & Enterprise Best Practices (Learnings & Gotchas)

During real-world enterprise deployments and live workshop executions, several subtle GCP SDK behaviors, authentication nuances, and regional model availability policies can arise. The codebase incorporates proactive guardrails for each:

### 1. Model Availability & Multi-Region Architecture (`global` vs `us-central1`)
* **Symptom:** `NotFound: 404 Publisher model ... was not found or your project does not have access to it.`
* **Root Cause:** In modern Google Cloud projects (including educational sandboxes like `upgradlabs-*`), older foundation models (`gemini-1.5-flash`, `gemini-2.5-flash`) or regional endpoints for new foundation models may not be accessible. The production model is **`gemini-3.5-flash-lite`** hosted on the **`global`** endpoint.
* **Resolution:** 
  * Vertex AI Text Embeddings (`text-embedding-004`) and Cloud Storage buckets operate regionally in `us-central1` (`location="us-central1"`).
  * Vertex AI Gemini (`gemini-3.5-flash-lite`) operates globally (`location="global"`).
  * In code, initialize the appropriate location context:
    ```python
    # For Regional Embeddings (us-central1):
    vertexai.init(project=PROJECT_ID, location="us-central1")
    embed_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

    # For Foundation Generative Model (global):
    vertexai.init(project=PROJECT_ID, location="global")
    agent_llm = GenerativeModel("gemini-3.5-flash-lite", tools=[agent_tools])
    ```

### 2. Cloud Build & Artifact Registry APIs Missing on Deploy from Source
* **Symptom:** Interactive prompt during deployment:  
  `API [cloudbuild.googleapis.com] not enabled on project ... Deploying from source requires an Artifact Registry Docker repository to store built containers. Would you like to enable and retry (this will take a few minutes)? (Y/n)?`
* **Root Cause:** Deploying Cloud Run or 2nd Gen Cloud Functions directly from source code (`--source`) automatically invokes Google Cloud Build to construct container images and push them into Artifact Registry. If `cloudbuild.googleapis.com` and `artifactregistry.googleapis.com` are not enabled beforehand, the deployment hangs or fails in non-interactive CI/CD pipelines.
* **Resolution:** Activate both APIs upfront before initiating deployments:
  ```bash
  gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com --quiet
  ```
  *(Both `deploy_production.sh` and Section 4 automated deployment pre-enable these APIs).*

### 3. Cloud Shell `.env` Upload Failure & Sourcing Gotcha
* **Symptom:** `cloud shell is not reading .env`, `PROJECT_ID` evaluates to empty string, or unable to upload `.env` through the Cloud Shell web interface.
* **Root Cause:** 
  1. **Upload Failure:** Cloud Shell's web file upload dialog suppresses hidden UNIX dotfiles (`.*`), preventing users from uploading `.env` directly from their laptop.
  2. **Git Protection:** `.env` is in `.gitignore` to prevent secret leaks, so git clone does not pull it.
  3. **Shell Sourcing:** In Linux/Cloud Shell, simply having a `.env` file does not automatically expose environment variables to commands in your session.
* **Resolution:** 
  1. Bypass the upload menu entirely and create `.env` directly via `cat`:
     ```bash
     cat << EOF > .env
     PROJECT_ID=$(gcloud config get-value project)
     REGION=us-central1
     BUCKET_NAME=$(gcloud config get-value project)-cloudcorp-policies
     EMBEDDING_MODEL=text-embedding-004
     GENERATIVE_MODEL=gemini-3.5-flash-lite
     EOF
     ```
  2. Export variables into your active Cloud Shell terminal session:
     ```bash
     set -a; source .env; set +a
     ```
  *(Note: `./deploy_production.sh` also includes automatic detection and will generate and source `.env` automatically if missing).*

### 4. Cloud Run Internal Server Error & Container Healthchecks
* **Symptom:** `curl -X POST "${RAG_SERVICE_URL}/ask"` returns `500 Internal Server Error`, or Cloud Run logs display:  
  `ValueError: Unsupported region for Vertex AI, select from frozenset({'australia-southeast1', ...})`
* **Root Cause:**
  1. Older pinned versions of `google-cloud-aiplatform` (< 2.0.0) strictly validated regional endpoints against a legacy set and crashed when passed `location="global"`.
  2. Instantiating AI models and downloading tokenizer weights at the top of the file (global module scope) blocks container startup, causing Cloud Run's port healthcheck to time out before FastAPI begins listening.
* **Resolution:**
  1. In [`rag_service/requirements.txt`](rag_service/requirements.txt), require `google-cloud-aiplatform>=2.0.0`.
  2. In [`rag_service/main.py`](rag_service/main.py), use lazy model loading (`get_models()`) and provide lightweight `/` and `/health` endpoints so container health checks return instant HTTP 200 before the first AI prediction is called.

### 5. Sandbox IAM Restriction: `run.services.setIamPolicy` Denied vs Project-Level IAM
* **Symptom:** During `gcloud functions deploy` or `gcloud run services add-iam-policy-binding`:  
  `ERROR: ResponseError: status=[403], message=[Permission 'run.services.setIamPolicy' denied on resource 'projects/.../services/cloudcorp-ticket-tool']`
* **Root Cause:** In educational sandboxes (e.g., UpGrad / NuveLabs), student user accounts are barred by organization policies from modifying resource-level IAM policies (`setIamPolicy`) to prevent exposing services to `allUsers`.
* **Resolution:** 
  1. Do not worry about the deployment warning—the Cloud Function or Cloud Run service has **successfully compiled and deployed**.
  2. Apply the invoker role at the **project level** rather than the individual service level:
     ```bash
     gcloud projects add-iam-policy-binding "$PROJECT_ID" \
       --member="serviceAccount:cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
       --role="roles/run.invoker" \
       --quiet
     ```

### 6. Cloud Workflows CLI Syntax: `--location` vs `--region`
* **Symptom:** `ERROR: (gcloud.workflows.deploy) unrecognized arguments: --region=us-central1`
* **Root Cause:** Unlike `gcloud run` and `gcloud functions` which use the `--region` flag, `gcloud workflows` commands (`deploy`, `run`, `delete`) strictly mandate `--location`.
* **Resolution:** Always pass `--location`:
  ```bash
  gcloud workflows deploy cloudcorp-agent-workflow \
    --source=workflows/workflow.yaml \
    --location=${REGION:-us-central1} \
    ...
  ```

### 7. Cloud Workflows OIDC Token Audience Mismatch & Token Creator Permissions
* **Symptom:** `AuthError: IAM permission denied for service account ... in step handle_pure_rag_flow`.
* **Root Cause:** 
  1. The workflow service account lacks permission to impersonate or create tokens for itself (`roles/iam.serviceAccountTokenCreator`).
  2. When Cloud Workflows makes an authenticated HTTP call to a subpath like `${rag_url + "/ask"}`, by default it mints an OIDC token with the full target URL as the audience. Cloud Run rejects this because its expected audience is the root base service URL (`${rag_url}`).
* **Resolution:** 
  1. Grant the token creator role at the project level:
     ```bash
     gcloud projects add-iam-policy-binding "$PROJECT_ID" \
       --member="serviceAccount:cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
       --role="roles/iam.serviceAccountTokenCreator" \
       --quiet
     ```
  2. In [`workflows/workflow.yaml`](workflows/workflow.yaml), explicitly specify `audience: ${rag_url}` and `audience: ${ticket_url}` in every `auth: type: OIDC` block:
     ```yaml
     call: http.post
     args:
       url: ${rag_url + "/ask"}
       auth:
         type: OIDC
         audience: ${rag_url}
     ```

### 8. Autonomous Tool Calling vs. Conversational Text Fallback
* **Symptom:** Agent responds *"I will go ahead and create an IT incident ticket for you..."* in text, but takes the pure RAG path and never calls the tool.
* **Root Cause:** If system instructions suggest *"explain policy and call create_it_ticket"*, the LLM attempts to output conversational text first. In Vertex AI single-turn generation, if the candidate output contains text, it omits the `function_call` payload.
* **Resolution:** Hardened system instructions with explicit, deterministic rules:
  ```python
  system_instruction=(
      "You are CloudCorp's AskHR & IT Agent.\n"
      "CRITICAL RULES:\n"
      "1. HARDWARE MALFUNCTION / DAMAGE: If an employee reports broken, damaged, or malfunctioning hardware, "
      "you MUST immediately call the `create_it_ticket` tool. Do NOT answer with plain text alone or just promise to create a ticket—invoke create_it_ticket immediately.\n"
      "2. TICKET STATUS LOOKUP: If an employee asks about an existing ticket status, you MUST call `lookup_it_ticket`.\n"
      "3. GENERAL HR QUESTIONS: For general HR policy questions, answer directly from policy context without calling tools."
  )
  ```

### 9. Safe `function_call` Inspection in Vertex AI SDK
* **Symptom:** `AttributeError: 'NoneType' object has no attribute 'name'` at `part.function_call.name`.
* **Root Cause:** In `google-cloud-aiplatform`, a response `Part` always has the attribute `function_call`, but its value is `None` when text is returned. `hasattr(part, "function_call")` evaluates to `True`, causing `part.function_call.name` to crash.
* **Resolution:** Use safe attribute retrieval:
  ```python
  part = response.candidates[0].content.parts[0]
  func_call = getattr(part, "function_call", None)
  if func_call and getattr(func_call, "name", None):
      fn_name = func_call.name
      fn_args = dict(func_call.args)
  ```

### 10. Dynamic Ticket ID Propagation Across Scenarios
* **Symptom:** Scenario 3 checks `What is the status of my ticket INC-501?` and returns `Not Found`.
* **Root Cause:** Hardcoding `INC-501` assumes Scenario 2 always succeeded in generating that exact ID in the current session.
* **Resolution:** Dynamically capture the generated ticket record from Scenario 2 and pass it to Scenario 3, with fallback to pre-seeded records:
  ```python
  created_ticket = run_askhr_agent("My laptop screen is broken and flickering, what should I do?")
  ticket_to_check = created_ticket.get("ticket_id", "INC-402") if created_ticket else "INC-402"
  run_askhr_agent(f"What is the status of my ticket {ticket_to_check}?")
  ```

### 11. Seamless Service Account Key Traversal (`gcp-key.json`)
* **Symptom:** `FileNotFoundError: gcp-key.json` when running from `notebooks/` subfolder.
* **Resolution:** All notebooks include recursive directory traversal (`.`, `..`, `notebooks/`, `~/Documents`) to automatically discover and resolve `gcp-key.json` regardless of whether the notebook kernel was started from project root or inside `notebooks/`.

### 12. Standalone Cell Execution Guardrails
* **Symptom:** `NameError: name 'PROJECT_ID' is not defined` or `NameError: name 'np' is not defined`.
* **Resolution:** Every standalone section notebook now includes independent imports (`import numpy as np`, `import time`, `import os`) and the complete authentication/configuration loader block so any notebook or cell can be run independently in any order.

### 13. macOS zsh `#` Interactive Comment Execution Gotcha
* **Symptom:** `zsh: command not found: #` when copying and pasting multi-line shell snippets.
* **Root Cause:** On macOS, the default `zsh` interactive shell treats `#` as an executable command rather than a comment unless `setopt interactivecomments` is configured in `~/.zshrc`.
* **Resolution:** All multi-line code boxes in the README are cleanly partitioned into pure executable statements without embedded comment lines.

### 14. Cloud Shell / ADC Quota Project Error (`projects/618104708054`)
* **Symptom:** When running notebook cells (such as Cell 2 of Section 2) in Cloud Shell Editor, Vertex AI throws:
  ```
  PermissionDenied: 403 Your application is authenticating by using local Application Default Credentials.
  The aiplatform.googleapis.com API requires a quota project, which is not set by default. ...
  reason: "SERVICE_DISABLED", consumer: "projects/618104708054"
  ```
* **Root Cause:** In Cloud Shell, user Application Default Credentials (ADC) default quota billing to Google's internal Cloud Shell client project (`618104708054`), where the Vertex AI API (`aiplatform.googleapis.com`) is not enabled.
* **Resolution (2 Solutions):**
  1. **Terminal Command (Immediate 1-Liner):** In the Cloud Shell terminal, set your project as the quota project on your ADC:
     ```bash
     gcloud auth application-default set-quota-project $(gcloud config get-value project)
     ```
  2. **Automatic Code-Level Binding (Built-In):** The updated notebook auth cells automatically bind `os.environ["GOOGLE_CLOUD_PROJECT"]` and `os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"]`, request ADC with `google.auth.default(quota_project_id=PROJECT_ID)`, and attach `credentials.with_quota_project(PROJECT_ID)` directly into `vertexai.init(..., credentials=credentials)` and `storage.Client(..., credentials=credentials)`.
  3. **Service Account Fallback:** Point to the service account key generated during Step 0 (`gcp-key.json`), which bypasses user ADC quota checks entirely.

---

### Master All-in-One Notebook
For learners who prefer executing the entire 3-hour workshop inside a single unified Colab file:
➡️ **[`notebooks/00_Full_Master_Lab.ipynb`](notebooks/00_Full_Master_Lab.ipynb)**
