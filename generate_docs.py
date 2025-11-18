import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Ensure output directory exists
output_dir = "/mnt/data/"
os.makedirs(output_dir, exist_ok=True)

# Function to create PDF from text content
def create_pdf(filename, title, content_list):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles['Title'])]
    for item in content_list:
        story.append(Paragraph(item, styles['Normal']))
        story.append(Spacer(1, 12))
    doc.build(story)

# 1. Generate ultimate_bundle_website.html (HTML version of the bundle)
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Ultimate Master Bundle - Website Version</title>
<style>
body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
h1, h2 { color: #1A5AFF; }
section { margin-bottom: 40px; }
hr { margin: 40px 0; }
</style>
</head>
<body>
<h1>Ultimate Master Documentation Bundle</h1>
<p>This is the website-friendly version of your complete enterprise documentation bundle. All sections are consolidated into a clean HTML format suitable for hosting, sharing, or importing into CMS systems.</p>

<section>
<h2>1. Executive Summary</h2>
<p>This platform automates real-estate lead scraping, enrichment, scoring, CRM syncing, and agent notifications using a full AI-driven microservice architecture.</p>
</section>

<section>
<h2>2. System Architecture Overview</h2>
<p>Microservice architecture, orchestrator-driven pipelines, ML scoring engines, scrapers, enrichment modules, CRM sync service, and dashboard UI.</p>
</section>

<section>
<h2>3. Engineering Specifications</h2>
<p>Service definitions, APIs, schemas, queues, workers, orchestration logic, and scaling model.</p>
</section>

<section>
<h2>4. Development Roadmap</h2>
<p>Six-sprint development plan covering foundation, scrapers, enrichment, scoring, CRM syncing, dashboard, and deployment.</p>
</section>

<section>
<h2>5. Database Schema</h2>
<p>Tables: leads_raw, leads_enriched, leads_scored, hubspot_sync, with indexing and migrations.</p>
</section>

<section>
<h2>6. API Documentation</h2>
<p>REST endpoints including: /scrape/run, /lead/{id}/enrich, /lead/{id}/score, /hubspot/sync/{id}, /dashboard/leads</p>
</section>

<section>
<h2>7. Security & Compliance</h2>
<p>UAE PDPL, GDPR, CCPA compliance, encryption standards, retention policy, audit logs, and data minimization rules.</p>
</section>

<section>
<h2>8. Deployment Handbook</h2>
<p>Kubernetes, Helm, CI/CD, observability stack, and rollback procedures.</p>
</section>

<section>
<h2>9. Operations & Support</h2>
<p>Incident response, severity levels, escalation channels, on-call rotation.</p>
</section>

<section>
<h2>10. Sales & Customer Experience Playbooks</h2>
<p>HOT/WARM/COLD scripts, negotiation flows, objection handling.</p>
</section>

<section>
<h2>11. Branding & Marketing</h2>
<p>Color palette, typography, slogans, ad copy, landing-page messaging.</p>
</section>

<section>
<h2>12. Legal Pack</h2>
<p>MSA, SOW, DPA, privacy policy, data rights.</p>
</section>

<section>
<h2>13. GTM Strategy</h2>
<p>Market entry, pricing, competitive differentiation, channel strategy.</p>
</section>

<section>
<h2>14. AI Lifecycle Management</h2>
<p>Retraining, drift detection, model health monitoring.</p>
</section>

<section>
<h2>15. Final Notes</h2>
<p>This HTML export serves as the master web version of your end-to-end documentation suite.</p>
</section>

</body>
</html>
"""

with open(os.path.join(output_dir, "ultimate_bundle_website.html"), "w") as f:
    f.write(html_content)

# 2. Generate full_master_bundle.pdf (Detailed PDF with all sections)
content = [
    "1. Executive Summary: Platform automates lead scraping, enrichment, scoring, CRM syncing, and notifications via AI microservices. Reduces manual qualification by 95%, boosts conversions by 40%.",
    "2. System Architecture Overview: Microservices: Orchestrator, scrapers, enrichment, scoring, CRM sync, dashboard. Event-driven, scalable on Kubernetes.",
    "3. Engineering Specifications: Services: 12 microservices (e.g., scraper-engine, lead-scoring). Tech: Node.js, Python, Postgres, RabbitMQ, Docker/K8s.",
    "4. Development Roadmap: Six sprints: Foundation, scrapers, enrichment, scoring, CRM, dashboard/deployment. Timeline: 6 months to MVP.",
    "5. Database Schema: Tables: leads_raw, leads_enriched, leads_scored, hubspot_sync. Indexing and migrations included.",
    "6. API Documentation: Endpoints: /scrape/run, /lead/{id}/enrich, /lead/{id}/score, /hubspot/sync/{id}, /dashboard/leads.",
    "7. Security & Compliance: Compliance: UAE PDPL, GDPR, CCPA. Encryption, audit logs, data minimization.",
    "8. Deployment Handbook: Tools: Kubernetes, Helm, CI/CD, Grafana. Rollback and observability procedures.",
    "9. Operations & Support: Incident response, SEV levels, on-call rotation. Troubleshooting and support SOPs.",
    "10. Sales & Customer Experience Playbooks: Scripts: HOT/WARM/COLD leads, objection handling. Negotiation flows and SLAs.",
    "11. Branding & Marketing: Palette: Blue (#1A5AFF), typography, slogans. Ad copy and landing-page messaging.",
    "12. Legal Pack: Documents: MSA, SOW, DPA, privacy policy. Data rights and obligations.",
    "13. GTM Strategy: Entry: UAE market, pricing tiers, channels. Differentiation and partnerships.",
    "14. AI Lifecycle Management: Retraining, drift detection, monitoring. Validation and improvement workflows.",
    "15. Final Notes: Master web version for hosting/sharing. Condensed outline in ultimate_bundle.pdf."
]
create_pdf(os.path.join(output_dir, "full_master_bundle.pdf"), "Full Master Bundle", content)

# 3. Generate ultimate_bundle.pdf (Condensed outline)
outline_content = [
    "Table of Contents:",
    "1. Executive Summary",
    "2. System Architecture Overview",
    "3. Engineering Specifications",
    "4. Development Roadmap",
    "5. Database Schema",
    "6. API Documentation",
    "7. Security & Compliance",
    "8. Deployment Handbook",
    "9. Operations & Support",
    "10. Sales & Customer Experience Playbooks",
    "11. Branding & Marketing",
    "12. Legal Pack",
    "13. GTM Strategy",
    "14. AI Lifecycle Management",
    "15. Final Notes"
]
create_pdf(os.path.join(output_dir, "ultimate_bundle.pdf"), "Ultimate Bundle Outline", outline_content)

# 4. Generate investor_pitch_deck.pdf
pitch_content = [
    "Slide 1: Title - LeadAI Realty pitch.",
    "Slide 2: Problem - 80% wasted time on leads.",
    "Slide 3: Solution - AI automation platform.",
    "Slide 4: Market - $50B TAM, 20% CAGR.",
    "Slide 5: Demo - Dashboard screenshots.",
    "Slide 6: Traction - Beta tests, 20% uplift.",
    "Slide 7: Business Model - SaaS at $99–$299/month.",
    "Slide 8: GTM - UAE launch, partnerships.",
    "Slide 9: Team - Expert founders.",
    "Slide 10: Financials - $1M ask, 10x ROI.",
    "Slide 11: Risks - Mitigated compliance/scaling.",
    "Slide 12: CTA - Invest for 20% equity."
]
create_pdf(os.path.join(output_dir, "investor_pitch_deck.pdf"), "Investor Pitch Deck", pitch_content)

# 5. Generate legal_pack.pdf
legal_content = [
    "Master Service Agreement (MSA): Defines terms for platform usage, including scope, fees, termination, and liability limits. Includes indemnification clauses for data breaches.",
    "Statement of Work (SOW): Outlines project deliverables, timelines, and milestones for custom integrations. Payment terms and acceptance criteria.",
    "Data Processing Agreement (DPA): Details data handling, security, and GDPR/PDPL compliance. Sub-processor lists and audit rights.",
    "Privacy Policy: User-facing policy explaining data collection, usage, and rights (e.g., erasure). Compliant with UAE PDPL, GDPR, CCPA.",
    "Data Rights and Obligations: Rights: Access, rectification, portability. Obligations: Consent logging, minimization, retention (e.g., 7 years for audits)."
]
create_pdf(os.path.join(output_dir, "legal_pack.pdf"), "Legal Pack", legal_content)

# 6. Generate employee_handbook.pdf
handbook_content = [
    "System Usage Guidelines: Access: Role-based permissions (e.g., admins for full dashboard). Best Practices: Log all actions, avoid sharing credentials.",
    "Data Handling Procedures: Compliance: Encrypt data, obtain consent. Incident Reporting: Notify legal within 24 hours of breaches.",
    "Operational Procedures: Daily Tasks: Monitor dashboards, respond to alerts. Escalation: SEV1 incidents to on-call team.",
    "Training and Onboarding: Modules: AI model usage, CRM sync troubleshooting. Certification: Annual compliance training."
]
create_pdf(os.path.join(output_dir, "employee_handbook.pdf"), "Employee Handbook", handbook_content)

# 7. Generate marketing_copy.pdf
marketing_content = [
    "Slogans: 'Turn Leads into Deals with AI Power.' 'Real-Estate Intelligence, Automated.'",
    "Ad Copy: Facebook: 'Boost conversions by 40%—automate your leads today!' LinkedIn: 'Enterprise AI for real-estate pros: Scrape, score, sell faster.'",
    "Landing-Page Messaging: Headline: 'AI-Driven Lead Automation for Real-Estate Agents.' CTA: 'Start Free Trial—Transform Your Workflow.'",
    "Social Media Campaigns: Posts: Case studies, webinars on AI in proptech. Hashtags: #AIRealEstate, #LeadAutomation."
]
create_pdf(os.path.join(output_dir, "marketing_copy.pdf"), "Marketing Copy", marketing_content)

print("All files generated successfully in /mnt/data/")