Sauti AI
Sauti AI is an AI-powered civic engagement platform that helps Members of Parliament understand and prioritize constituent needs. Citizens can send complaints, suggestions, and development requests through WhatsApp using text, voice notes, photos, and screenshots. Gemma 4 processes the submissions, groups related issues, extracts location clues, and helps produce actionable insights for the MP.

Problem
Constituency feedback is often scattered across letters, voice notes, photos, and informal messages. This makes it difficult for MPs and their teams to quickly identify the most urgent community needs, understand where problems are concentrated, and decide what to address first.

Solution
Sauti AI centralizes and analyzes citizen submissions in one place. It transforms raw public feedback into structured insights such as:

recurring issue themes
urgency levels
location-based demand hotspots
ranked recommendations for action
Key Features
WhatsApp-based citizen submission intake
Support for text, audio, images, and screenshots
Multilingual and multimodal analysis with Gemma 4
Automatic clustering of related community concerns
Geospatial hotspot detection by location
Priority ranking based on frequency, sentiment, and impact
MP dashboard for reviewing submissions and insights
How It Works
Citizens submit complaints, ideas, or requests through WhatsApp.
A webhook receives the incoming message.
The system processes text, voice, and image inputs.
Gemma 4 analyzes the submissions and identifies themes.
The system extracts locations and estimates urgency.
The MP dashboard displays submissions, priorities, and hotspot maps.
System Architecture

1. Entry / Ingestion Layer
   Receives messages through a WhatsApp sandbox connected with webhook infrastructure.

2. Analysis Layer
   Gemma 4 acts as the core reasoning engine. It:

transcribes voice notes
interprets text submissions
analyzes images and screenshots
groups similar concerns
ranks issues by priority 3. Data Layer
Stores structured submission data such as:

location
issue category
urgency score
submission type
timestamps 4. Dashboard Layer
Provides the MP with a clear view of:

all citizen submissions
AI-generated priority clusters
ranked recommendations
demand hotspot maps
Example Data Fields
Location: neighborhood, street, or coordinates
Issue Category: roads, water and sanitation, health, security
Urgency Score: 1–10 based on frequency, sentiment, and impact
Submission Type: text, voice note, image, screenshot
Use Cases
identifying roads that need repair
spotting water supply complaints in a specific ward
tracking repeated security concerns
grouping public proposals for local development
helping MPs prioritize limited resources more effectively
Why Sauti AI Matters
Sauti AI makes civic engagement faster, clearer, and more data-driven. Instead of relying on manual review of unstructured feedback, MPs can use AI-generated insights to understand citizen needs and respond with better-informed decisions.

Future Improvements
support for more languages
stronger location extraction and mapping
sentiment analysis for urgency estimation
analytics for trend tracking over time
automated report generation for MPs and staff
Hackathon Summary
Sauti AI is a practical constituency-planning assistant that turns citizen feedback into decision-ready insights. By combining WhatsApp intake, multimodal AI analysis, and dashboard visualizations, it helps MPs listen to communities at scale and act on what matters most.
