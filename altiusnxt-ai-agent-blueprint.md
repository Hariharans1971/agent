# AltiusNxt AI Agent Blueprint

## Product Name
AltiusNxt Team Copilot

## Recommended Product Shape
Build one internal AI workspace for AltiusNxt with two specialized copilots:
- Marketing Copilot
- HR Copilot

This is better than a single generic chatbot because both teams need different workflows, tone, permissions, and guardrails. A shared company knowledge layer keeps the messaging and company facts consistent, while each copilot handles its own use cases.

## Why This Fits AltiusNxt
AltiusNxt positions itself as a specialist in B2B eCommerce product data enrichment, taxonomy, product attributes, PIM, MDM, eCommerce consulting, and platform integration for industrial distributors. The website also highlights long industry experience, enterprise delivery, multi-region presence, and an active hiring funnel.

That makes AltiusNxt a strong candidate for an internal AI agent that can:
- help marketing generate accurate industry-specific content faster
- help HR standardize hiring communication and candidate operations
- reuse company-approved service positioning and proof points
- reduce repetitive work across sales support, employer branding, and recruitment coordination

## Core Business Objective
Improve team productivity, content consistency, hiring responsiveness, and operational speed without increasing headcount for repetitive internal work.

## Users
- Marketing manager
- Content marketer
- SEO specialist
- Business development support team
- HR manager
- Recruiter
- Hiring coordinator
- Leadership users who need fast drafts and summaries

## High-Level Product Vision
An internal AI assistant that understands AltiusNxt's services, industries, positioning, and hiring context, and helps employees produce high-quality work in minutes instead of hours.

## Shared Knowledge Base
The copilot should be grounded in approved company information and internal documents.

### Public Knowledge Sources
- company website pages
- service pages
- case studies
- about page
- careers page
- FAQs
- contact details

### Internal Knowledge Sources
- service decks and capability statements
- case study source files
- approved messaging and brand guidelines
- proposal templates
- HR policies
- job descriptions
- interview scorecards
- onboarding checklists
- employee handbook
- hiring process documentation

## Copilot 1: Marketing Copilot

### Primary Purpose
Help the marketing team create B2B industrial eCommerce marketing assets that are specific, conversion-focused, and aligned with AltiusNxt's positioning.

### Key Use Cases
- website copy drafts
- landing page creation
- email campaigns
- LinkedIn posts
- case study summaries
- blog outlines
- SEO keyword clustering
- ad copy generation
- campaign brief creation
- webinar and event promotion copy
- sales enablement one-pagers
- proposal support content
- customer outreach personalization

### What It Should Be Able To Do
- answer questions about AltiusNxt services and positioning
- generate channel-specific marketing copy using approved tone
- rewrite technical services into business-value language
- create audience-specific versions for distributors, eCommerce teams, and digital transformation leaders
- repurpose one asset into multiple formats
- suggest calls to action based on funnel stage
- extract proof points from case studies and approved client wins
- generate keyword and topic ideas for industrial search intent

### Example Prompts
- Create a landing page for product taxonomy services targeting industrial distributors.
- Turn this case study into a LinkedIn post, a sales email, and two ad variants.
- Write a thought-leadership post on why product data quality affects B2B conversion.
- Build a campaign brief for promoting PIM implementation services to midmarket distributors.

### Marketing Guardrails
- never invent client names, metrics, certifications, or platform partnerships
- clearly mark assumptions when proof points are missing
- stay grounded in industrial B2B eCommerce language
- avoid generic consumer-marketing phrasing
- keep all claims aligned with approved company messaging

## Copilot 2: HR Copilot

### Primary Purpose
Help HR and recruiting teams move faster on hiring communication, screening preparation, coordination, and onboarding documentation.

### Key Use Cases
- job description drafts
- candidate outreach emails
- resume summarization
- interview question generation
- interview panel briefing notes
- scorecard templates
- candidate comparison summaries
- rejection and follow-up communication drafts
- onboarding checklists
- policy Q&A support
- internal announcement drafts
- employer branding content

### What It Should Be Able To Do
- generate role-specific JDs aligned with AltiusNxt's service model
- summarize resumes against defined role criteria
- draft recruiter outreach based on role and candidate profile
- create interview questions for technical, content, operations, and leadership roles
- generate first-day and first-week onboarding plans
- answer HR process questions from approved policy documents
- create standardized internal communication drafts

### Example Prompts
- Draft a job description for a PIM implementation consultant.
- Summarize these five resumes against the requirements for a product data analyst.
- Create first-round interview questions for a B2B content marketing manager.
- Write an onboarding checklist for a new catalog enrichment specialist.

### HR Guardrails
- do not make final hiring decisions
- do not rank candidates using protected characteristics
- do not generate discriminatory or non-compliant screening criteria
- treat all resume analysis as recruiter support, not automated rejection authority
- only answer policy questions from approved HR documentation
- escalate sensitive employee issues to HR leadership

## Recommended MVP
Launch a focused MVP with the smallest set of features that deliver clear internal value.

### MVP Features
- secure internal login
- role selection: Marketing or HR
- chat interface with saved prompt templates
- company knowledge base retrieval
- document upload for resumes, job descriptions, case studies, and briefs
- output types: email, post, landing page, JD, summary, checklist
- conversation history
- copy-to-clipboard and export
- admin panel for managing approved source files

### MVP Workflows
#### Marketing
1. User selects Marketing Copilot.
2. User chooses a task template or enters a request.
3. Agent retrieves relevant company and service context.
4. Agent generates output in the requested format.
5. User refines, exports, or saves result.

#### HR
1. User selects HR Copilot.
2. User uploads a resume or selects a template.
3. Agent extracts role-relevant information and creates a structured summary.
4. Agent drafts outreach, interview questions, or onboarding docs.
5. User reviews and finalizes content manually.

## Recommended Technical Architecture

### Front End
- internal web app
- clean dashboard with separate workspaces for Marketing and HR
- template library
- chat panel
- saved outputs and recent tasks

### Back End
- LLM orchestration layer
- retrieval-augmented generation over approved company documents
- file storage for uploaded documents
- audit logs for prompts and outputs
- role-based access control

### Data And Integrations
- website content ingestion
- Google Drive or SharePoint for internal docs
- HR resume folder or ATS export ingestion
- optional CRM integration later for marketing and sales alignment

### Model Setup
- one shared base model
- two system prompts specialized by team
- retrieval layer for company facts and source-grounded answers
- output templates for repeatable tasks

## UI Recommendation
Keep the interface simple and operational:
- left navigation for Marketing Copilot, HR Copilot, Templates, Knowledge Base, and Admin
- main panel for chat and generated content
- right panel for source context, quick actions, and export
- separate color accents for each copilot, but one unified AltiusNxt brand feel

## Success Metrics

### Marketing
- reduction in time to create campaign assets
- increase in output consistency across channels
- number of reusable assets generated per month
- percentage of content drafts approved with minor edits

### HR
- faster time to draft JDs and candidate outreach
- reduced recruiter admin effort
- faster interview-kit preparation
- improved consistency of hiring communication

## Implementation Roadmap

### Phase 1
- build internal copilot MVP
- load public company content
- add templates for top 10 marketing and HR tasks

### Phase 2
- connect internal documents
- add output saving and approval workflows
- add richer resume and JD comparison flows

### Phase 3
- integrate ATS or HR systems
- integrate CRM and sales collateral
- add analytics, feedback scoring, and workflow automation

## Recommended First Templates

### Marketing Templates
- landing page draft
- LinkedIn post
- SEO brief
- ad copy set
- case study repurposing
- webinar invite

### HR Templates
- job description draft
- candidate outreach email
- resume summary
- interview question set
- candidate comparison sheet
- onboarding checklist

## Key Risks And Controls
- inaccurate claims in marketing outputs
- outdated company information in responses
- resume screening used as an automated rejection system
- exposure of HR-sensitive documents to non-HR users
- inconsistent tone without approved templates

### Controls
- retrieval only from approved sources
- explicit citation or source panel in the UI
- separate HR permissions
- human review required before sending or publishing
- prompt logging and admin oversight

## Best First Version
The best first version for AltiusNxt is not a broad enterprise assistant. It is a lightweight internal copilot with two team modes, company-grounded knowledge, reusable templates, and strong review guardrails.

This approach delivers real value quickly, keeps risk manageable, and creates a clear path to later integrations with CRM, ATS, PIM, or document systems.
