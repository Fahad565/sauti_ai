"""Realistic seed dataset generator for Sauti AI.

Populates sample data for 6 constituencies (Likoni, Mvita, Nyali, Kisauni, Changamwe, Jomvu)
covering Infrastructure (Roads, Schools, Hospitals, Markets, Water points, Boreholes, Bridges)
and Projects (Ongoing, Planned, Completed), plus sample users, submissions, and issues.
"""

import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.domain import (
    User,
    ConversationSession,
    Submission,
    Issue,
    Cluster,
    Infrastructure,
    Project,
    AgentAction,
    AISummary,
)

logger = logging.getLogger(__name__)

CONSTITUENCIES = ["Likoni", "Mvita", "Nyali", "Kisauni", "Changamwe", "Jomvu"]

INFRASTRUCTURE_DATA = [
    # Likoni
    {"constituency": "Likoni", "name": "Likoni Ferry Access Road", "type": "Roads", "location": "Ferry Ramp Area", "status": "operational", "capacity_details": "4-lane asphalt road handling 50,000+ commuters daily"},
    {"constituency": "Likoni", "name": "Likoni Primary School", "type": "Schools", "location": "Mtongwe Ward", "status": "operational", "capacity_details": "1,200 students capacity with computer lab"},
    {"constituency": "Likoni", "name": "Likoni Sub-County Hospital", "type": "Hospitals", "location": "Likoni Town", "status": "operational", "capacity_details": "100-bed level 4 public hospital with maternity wing"},
    {"constituency": "Likoni", "name": "Likoni Municipal Market", "type": "Markets", "location": "Shelly Beach Junction", "status": "maintenance_required", "capacity_details": "300 vendor stalls with cold storage facility"},
    {"constituency": "Likoni", "name": "Likoni Community Water Kiosk", "type": "Water points", "location": "Bofu Ward", "status": "operational", "capacity_details": "10,000L daily supply for 500 households"},
    {"constituency": "Likoni", "name": "Likoni Mtongwe Solar Borehole", "type": "Boreholes", "location": "Mtongwe Village", "status": "operational", "capacity_details": "Solar-powered 50m deep borehole delivering 15m3/hr"},
    {"constituency": "Likoni", "name": "Likoni Floating Footbridge", "type": "Bridges", "location": "Liwatoni Channel", "status": "operational", "capacity_details": "Pedestrian floating bridge connecting Island to South Coast"},

    # Mvita
    {"constituency": "Mvita", "name": "Mvita Digo Road Dualing", "type": "Roads", "location": "CBD Central Ward", "status": "operational", "capacity_details": "Primary urban artery serving downtown commerce"},
    {"constituency": "Mvita", "name": "Mvita Secondary School", "type": "Schools", "location": "Tudor Ward", "status": "operational", "capacity_details": "800 students capacity, specialized science laboratories"},
    {"constituency": "Mvita", "name": "Mvita Coast General Hospital Annex", "type": "Hospitals", "location": "Old Town Ward", "status": "operational", "capacity_details": "Regional referral unit with specialized pediatric care"},
    {"constituency": "Mvita", "name": "Mvita Mackinnon Market", "type": "Markets", "location": "Old Town", "status": "operational", "capacity_details": "Historic fresh produce and spice market with 400 stalls"},
    {"constituency": "Mvita", "name": "Mvita Island Water Station", "type": "Water points", "location": "Majengo", "status": "operational", "capacity_details": "High capacity booster station pumping 500,000L daily"},
    {"constituency": "Mvita", "name": "Mvita Tudor Borehole", "type": "Boreholes", "location": "Tudor Creek", "status": "non_functional", "capacity_details": "Pump motor failure under maintenance assessment"},
    {"constituency": "Mvita", "name": "Mvita Nyali Bridge Access", "type": "Bridges", "location": "Tudor Channel", "status": "operational", "capacity_details": "6-lane arterial bridge connecting Island to North Coast"},

    # Nyali
    {"constituency": "Nyali", "name": "Nyali Beach Link Road", "type": "Roads", "location": "Frere Town", "status": "operational", "capacity_details": "Dual carriageway with pedestrian walkways and streetlights"},
    {"constituency": "Nyali", "name": "Nyali Girls High School", "type": "Schools", "location": "Kongowea Ward", "status": "operational", "capacity_details": "Boarding high school for 900 students with STEM center"},
    {"constituency": "Nyali", "name": "Nyali Health Centre", "type": "Hospitals", "location": "Maweni", "status": "operational", "capacity_details": "Level 3 health facility serving 30,000 residents"},
    {"constituency": "Nyali", "name": "Nyali Kongowea Market", "type": "Markets", "location": "Kongowea", "status": "operational", "capacity_details": "Largest wholesale agricultural market in Coast Region"},
    {"constituency": "Nyali", "name": "Nyali Desalination Unit", "type": "Water points", "location": "Nyali Beach", "status": "operational", "capacity_details": "Desalination plant producing 20,000L potable water daily"},
    {"constituency": "Nyali", "name": "Nyali Mtwapa Border Borehole", "type": "Boreholes", "location": "Cadiz", "status": "operational", "capacity_details": "Deep aquifer borehole powering community irrigation"},
    {"constituency": "Nyali", "name": "Nyali New Creek Bridge", "type": "Bridges", "location": "Kongowea Creek", "status": "operational", "capacity_details": "Heavy transport bridge carrying North Coast traffic"},

    # Kisauni
    {"constituency": "Kisauni", "name": "Kisauni Bypass Road", "type": "Roads", "location": "Bamburi Ward", "status": "under_construction", "capacity_details": "12km relief highway bypassing congestion hotspots"},
    {"constituency": "Kisauni", "name": "Kisauni Technical Institute", "type": "Schools", "location": "Magogoni", "status": "operational", "capacity_details": "Vocational college enrolling 1,500 vocational students"},
    {"constituency": "Kisauni", "name": "Kisauni Dispensary", "type": "Hospitals", "location": "Mjambere Ward", "status": "maintenance_required", "capacity_details": "Outpatient clinic providing immunizations and maternal care"},
    {"constituency": "Kisauni", "name": "Kisauni Bamburi Market", "type": "Markets", "location": "Bamburi Centre", "status": "operational", "capacity_details": "Retail fresh produce market with 250 open stalls"},
    {"constituency": "Kisauni", "name": "Kisauni Kiembeni Water Point", "type": "Water points", "location": "Kiembeni Estate", "status": "operational", "capacity_details": "Piped water distribution center for 1,200 households"},
    {"constituency": "Kisauni", "name": "Kisauni Utange Deep Borehole", "type": "Boreholes", "location": "Utange Ward", "status": "operational", "capacity_details": "Solar-assisted 80m deep borehole producing 25m3/hr"},
    {"constituency": "Kisauni", "name": "Kisauni Bamburi Footbridge", "type": "Bridges", "location": "Bamburi Highway", "status": "operational", "capacity_details": "Overhead pedestrian bridge for school safety"},

    # Changamwe
    {"constituency": "Changamwe", "name": "Changamwe Industrial Corridor Road", "type": "Roads", "location": "Airport Ward", "status": "operational", "capacity_details": "Heavy duty logistics corridor connecting Port to Airport"},
    {"constituency": "Changamwe", "name": "Changamwe Secondary School", "type": "Schools", "location": "Chaani Ward", "status": "operational", "capacity_details": "1,000 student capacity with technical workshops"},
    {"constituency": "Changamwe", "name": "Changamwe Health Centre", "type": "Hospitals", "location": "Kipevu", "status": "operational", "capacity_details": "24-hour emergency and casualty center"},
    {"constituency": "Changamwe", "name": "Changamwe West Market", "type": "Markets", "location": "Magongo Ward", "status": "operational", "capacity_details": "Industrial employee market with 180 food stalls"},
    {"constituency": "Changamwe", "name": "Changamwe Port Water Kiosk", "type": "Water points", "location": "Port Reitz", "status": "operational", "capacity_details": "Clean drinking water supply for port workers and community"},
    {"constituency": "Changamwe", "name": "Changamwe Chaani Borehole", "type": "Boreholes", "location": "Chaani", "status": "operational", "capacity_details": "High yield borehole supplying emergency water reservoir"},
    {"constituency": "Changamwe", "name": "Changamwe Overpass Bridge", "type": "Bridges", "location": "Magongo Junction", "status": "operational", "capacity_details": "Grade-separated flyover bridge eliminating truck gridlock"},

    # Jomvu
    {"constituency": "Jomvu", "name": "Jomvu-Miritini Interchange Road", "type": "Roads", "location": "Miritini Ward", "status": "operational", "capacity_details": "Modern highway connecting SGR Terminal to Nairobi Highway"},
    {"constituency": "Jomvu", "name": "Jomvu Primary School", "type": "Schools", "location": "Mikindani Ward", "status": "operational", "capacity_details": "1,100 pupils primary school with early childhood development centre"},
    {"constituency": "Jomvu", "name": "Jomvu Model Health Centre", "type": "Hospitals", "location": "Jomvu Kuu", "status": "operational", "capacity_details": "Recently upgraded 50-bed sub-county medical center"},
    {"constituency": "Jomvu", "name": "Jomvu Owino Uhuru Market", "type": "Markets", "location": "Owino Uhuru", "status": "operational", "capacity_details": "Open-air agricultural trading market"},
    {"constituency": "Jomvu", "name": "Jomvu Water Distribution Kiosk", "type": "Water points", "location": "Mikindani", "status": "operational", "capacity_details": "Prepaid smart card water kiosk serving 800 families"},
    {"constituency": "Jomvu", "name": "Jomvu Mikindani Borehole", "type": "Boreholes", "location": "Mikindani Estate", "status": "operational", "capacity_details": "Community-managed deep borehole supplying 30m3/hr"},
    {"constituency": "Jomvu", "name": "Jomvu Creek Railway Bridge", "type": "Bridges", "location": "Miritini Rail Line", "status": "operational", "capacity_details": "Heavy freight rail bridge connecting Port to SGR main line"},
]

PROJECTS_DATA = [
    # Ongoing
    {"constituency": "Likoni", "name": "Shelly Beach Road Tarmacking Phase II", "type": "Infrastructure", "status": "Ongoing", "budget": 45000000.0, "description": "Upgrading 4.5km dirt road to bitumen standards with drainage storm channels.", "start_date": "2026-01-15", "target_completion_date": "2026-11-30"},
    {"constituency": "Mvita", "name": "Tudor Waterfront Promenade Restoration", "type": "Urban Development", "status": "Ongoing", "budget": 35000000.0, "description": "Developing green spaces, public walkways, and eco-tourism amenities along Tudor Creek.", "start_date": "2026-03-01", "target_completion_date": "2026-12-15"},
    {"constituency": "Nyali", "name": "Kongowea Market Solarization & Lighting Project", "type": "Energy", "status": "Ongoing", "budget": 28000000.0, "description": "Installing 500kW rooftop solar grid and high-mast LED floodlights for 24-hr trading.", "start_date": "2026-02-10", "target_completion_date": "2026-08-30"},
    {"constituency": "Kisauni", "name": "Utange Water Pipeline Extension", "type": "Water & Sanitation", "status": "Ongoing", "budget": 52000000.0, "description": "Laying 15km high-density polyethylene pipeline to deliver clean water to Utange and Mjambere.", "start_date": "2026-01-05", "target_completion_date": "2026-09-30"},
    {"constituency": "Changamwe", "name": "Chaani Youth Empowerment & Vocational Hub", "type": "Education & Skills", "status": "Ongoing", "budget": 40000000.0, "description": "Constructing state-of-the-art welding, robotics, and IT vocational training complex.", "start_date": "2026-04-01", "target_completion_date": "2026-12-01"},
    {"constituency": "Jomvu", "name": "Mikindani Stormwater Drainage Mitigation Project", "type": "Disaster Management", "status": "Ongoing", "budget": 60000000.0, "description": "Constructing deep concrete culverts to eliminate annual monsoon floodwaters in Mikindani.", "start_date": "2025-11-01", "target_completion_date": "2026-10-31"},

    # Planned
    {"constituency": "Likoni", "name": "Bofu Ward Community Health Clinic", "type": "Healthcare", "status": "Planned", "budget": 30000000.0, "description": "Planning 30-bed outpatient healthcare facility to relieve pressure on Likoni Sub-County Hospital.", "start_date": "2026-09-01", "target_completion_date": "2027-05-30"},
    {"constituency": "Mvita", "name": "Old Town Heritage & Smart Sewerage Overhaul", "type": "Sanitation", "status": "Planned", "budget": 75000000.0, "description": "Upgrading subterranean sewer network without damaging UNESCO heritage structures.", "start_date": "2026-10-01", "target_completion_date": "2027-12-31"},
    {"constituency": "Nyali", "name": "Frere Town High School Modern Science Complex", "type": "Education", "status": "Planned", "budget": 25000000.0, "description": "Adding physics, chemistry, and digital learning labs.", "start_date": "2026-08-15", "target_completion_date": "2027-03-31"},
    {"constituency": "Kisauni", "name": "Bamburi Modern Bus Terminus & Taxi Park", "type": "Transport", "status": "Planned", "budget": 48000000.0, "description": "Building organized passenger bay with electronic ticketing and security surveillance.", "start_date": "2026-11-01", "target_completion_date": "2027-08-30"},
    {"constituency": "Changamwe", "name": "Magongo Eco-Park & Community Sports Centre", "type": "Recreation", "status": "Planned", "budget": 32000000.0, "description": "Developing football pitch, basketball court, and recreational garden.", "start_date": "2026-09-15", "target_completion_date": "2027-06-30"},
    {"constituency": "Jomvu", "name": "Owino Uhuru Desalination & Purification Plant", "type": "Water", "status": "Planned", "budget": 85000000.0, "description": "Large-scale water purification plant addressing historic industrial pollution issues.", "start_date": "2026-12-01", "target_completion_date": "2027-11-30"},

    # Completed
    {"constituency": "Likoni", "name": "Mtongwe Primary School Digital Classroom Block", "type": "Education", "status": "Completed", "budget": 18000000.0, "description": "Constructed 6 digital classrooms equipped with tablets and solar backup power.", "start_date": "2025-03-01", "target_completion_date": "2025-11-15"},
    {"constituency": "Mvita", "name": "Majengo Streetlight Grid Expansion", "type": "Public Safety", "status": "Completed", "budget": 15000000.0, "description": "Installed 250 solar LED streetlamps reducing nighttime crime rates by 40%.", "start_date": "2025-05-10", "target_completion_date": "2025-10-30"},
    {"constituency": "Nyali", "name": "Maweni Maternity Unit Expansion", "type": "Healthcare", "status": "Completed", "budget": 22000000.0, "description": "Added 25 maternity beds, newborn incubator unit, and ultrasound facility.", "start_date": "2025-01-10", "target_completion_date": "2025-09-20"},
    {"constituency": "Kisauni", "name": "Kiembeni Market Security & Sanitation Block", "type": "Sanitation", "status": "Completed", "budget": 12000000.0, "description": "Built modern ablution block and perimeter fencing for vendor safety.", "start_date": "2025-06-01", "target_completion_date": "2025-12-15"},
    {"constituency": "Changamwe", "name": "Port Reitz Access Footbridge", "type": "Pedestrian Safety", "status": "Completed", "budget": 14000000.0, "description": "Erected steel footbridge for school children crossing heavy industrial freight road.", "start_date": "2025-02-15", "target_completion_date": "2025-08-30"},
    {"constituency": "Jomvu", "name": "Miritini SGR Bus Station Link", "type": "Transport", "status": "Completed", "budget": 20000000.0, "description": "Built paved matatu and taxi terminal adjacent to Mombasa SGR terminus.", "start_date": "2025-04-01", "target_completion_date": "2025-10-15"},
]


def seed_database(db: Session) -> None:
    """Populate database with seed data if tables are empty."""
    Base.metadata.create_all(bind=engine)

    # Check if infrastructure already exists
    if db.query(Infrastructure).first():
        logger.info("Database already contains infrastructure data, skipping seed.")
        return

    logger.info("Seeding constituency infrastructure...")
    for infra in INFRASTRUCTURE_DATA:
        db.add(Infrastructure(**infra))

    logger.info("Seeding constituency projects...")
    for proj in PROJECTS_DATA:
        db.add(Project(**proj))

    # Seed initial sample users and submissions
    logger.info("Seeding sample citizen users & complaints...")
    u1 = User(phone_number="+254712345678", name="Amina Hassan", constituency="Likoni", ward="Mtongwe")
    u2 = User(phone_number="+254723456789", name="John Omondi", constituency="Kisauni", ward="Bamburi")
    u3 = User(phone_number="+254734567890", name="Fatuma Ali", constituency="Mvita", ward="Old Town")

    db.add_all([u1, u2, u3])
    db.flush()

    s1 = ConversationSession(user_id=u1.id, channel="whatsapp", status="active")
    s2 = ConversationSession(user_id=u2.id, channel="whatsapp", status="active")
    db.add_all([s1, s2])
    db.flush()

    sub1 = Submission(
        session_id=s1.id,
        user_id=u1.id,
        raw_content="The water borehole in Mtongwe has low pressure and dirty water. Please fix it urgently.",
        constituency="Likoni",
        ward="Mtongwe",
        status="categorized",
    )
    sub2 = Submission(
        session_id=s2.id,
        user_id=u2.id,
        raw_content="Deep potholes along the Bamburi Road are causing heavy traffic and vehicle breakdowns.",
        constituency="Kisauni",
        ward="Bamburi",
        status="received",
    )
    db.add_all([sub1, sub2])
    db.flush()

    issue1 = Issue(
        submission_id=sub1.id,
        title="Contaminated / Low pressure water supply",
        category="Boreholes",
        severity="high",
        status="open",
    )
    issue2 = Issue(
        submission_id=sub2.id,
        title="Road surface degradation and potholes",
        category="Roads",
        severity="medium",
        status="open",
    )
    db.add_all([issue1, issue2])

    summary1 = AISummary(
        submission_id=sub1.id,
        session_id=s1.id,
        summary_text="Citizen reports water quality and pressure issues at Mtongwe Borehole in Likoni.",
        extracted_intent="report_infrastructure_fault",
        key_entities="Likoni, Mtongwe, Borehole",
        confidence_score=0.95,
    )
    db.add(summary1)

    db.commit()
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
