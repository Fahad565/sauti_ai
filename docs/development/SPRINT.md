## Sprint 7 — MP Dashboard & Civic Intelligence Platform

## The dashboard should answer questions like:

What is happening in my constituency today?

What are the top issues?

What has been reported in the last 24 hours?

Which areas need immediate attention?

What infrastructure projects are planned or ongoing?

Are there any emerging trends or hotspots?

How do complaints compare month-over-month? 

## Sprint 7 — MP Dashboard

## Objective

Build a polished dashboard that showcases everything the backend already does.

No login.

No authentication.

No user management.

No RBAC.

Just open the URL and immediately see the intelligence.


Feature 7.1 — Dashboard Shell

One page layout.

┌──────────────────────────────────────────┐
│ Sauti AI                                │
├───────────────┬──────────────────────────┤
│ Sidebar       │ Main Content             │
│               │                          │
│ Dashboard     │                          │
│ Issues        │                          │
│ Projects      │                          │
│ Infrastructure│                          │
│ AI Pipeline   │                          │
│ Analytics     │                          │
└───────────────┴──────────────────────────┘
Feature 7.2 — Overview

Landing page.

Cards

Citizen Reports

Open Issues

Projects

Infrastructure

Critical Issues

Today's Reports

Charts

Reports by Constituency

Categories

Priority

Top Topics

Trend

Everything comes from the APIs you've already built.

Feature 7.3 — Issues Explorer

A searchable table.

Columns

Citizen

Message

Category

Priority

Constituency

Topics

Status

Created

Filters

Constituency

Category

Priority

Topic

Click a row →

Show full complaint.

Feature 7.4 — Infrastructure Explorer

Cards

Roads

Schools

Hospitals

Markets

Bridges

Water

Search

Likoni

Nyali

Changamwe

Uses

GET /api/v1/infrastructure
Feature 7.5 — Projects

Display

Completed

Planned

Ongoing

Filters

Constituency

Budget

Status
Feature 7.6 — AI Pipeline Visualizer

This is the showpiece.

Citizen message

↓

Classifier

↓

Duplicate Detection

↓

Priority

↓

Geographic Extraction

↓

Topic Tagging

↓

Trend Detection

↓

SQL Retrieval

↓

Gemma

↓

Final Response

For every stage show

Confidence

Detected keywords

Reason

Timing

Output

Judges love seeing explainability.

Feature 7.7 — Analytics

Simple charts.

Complaints

Categories

Priority

Constituencies

Projects

Infrastructure

Weekly Trend

You already have almost all the data.

Feature 7.8 — Live Feed

A panel showing

Incoming WhatsApp

↓

Pipeline

↓

Stored

↓

Response
