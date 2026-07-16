import asyncio
import sys
import os
import uuid
import random
import time
import hashlib
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models import (
    User, UserProfile, Publisher, Story, StoryRelation,
    Article, ArticleDuplicate, StoryTimeline
)
from app.services.embedder import EmbedderService
from app.utils.auth import hash_password

# ── Mock Data Templates and Parameters ───────────────────────────────────────

COMPANIES = ["Aether Corp", "QuantumLink", "BioSphere", "NeuralFlow", "NovaTech", "ApexSystems", "HelixCorp", "VortexIndustries", "Zenith AI", "Starlight Tech"]
PRODUCTS = ["CoreEngine v5", "SyncPrism", "OmniPulse", "DeepTrust AI", "AuraOS", "BioSynthesize", "QuantumGrid", "NexusPlatform"]
FOCUS_AREAS = ["energy efficiency", "privacy compliance", "automated reasoning", "cost reduction", "data scalability", "predictive security", "decentralized identity"]
COUNTRIES = ["United States", "Germany", "Japan", "India", "United Kingdom", "Canada", "Australia", "Brazil", "France", "South Korea"]
ISSUES = ["carbon emissions", "cyber threats", "economic disparity", "water scarcity", "supply chain bottlenecks", "inflationary pressures", "infrastructure decay"]
POLICIES = ["regulatory framework", "green subsidy scheme", "renewable energy mandate", "infrastructure bill", "trade agreement", "privacy charter"]
DISCOVERIES = ["room-temperature superconductor", "novel cancer antibody", "ancient ruin mapping", "deep-sea geothermal vents", "high-efficiency perovskite solar cell"]
FIELDS = ["materials science", "immunology", "anthropology", "marine biology", "photovoltaics"]
INSTITUTIONS = ["MIT", "Stanford University", "Max Planck Institute", "Tokyo University", "Oxford University", "Cambridge Laboratories"]
PLANETS = ["Kepler-186f", "TOI-700 d", "Proxima Centauri b", "Gliese 581g", "LHS 1140b"]
ROVERS = ["Perseverance", "Curiosity", "Zhurong", "Opportunity", "Sojourner"]
ATHLETES = ["Marcus Vance", "Elena Rostova", "Hiroshi Tanaka", "Sarah Jenkins", "David Okoye"]
SPORTS = ["100m sprint", "marathon", "200m freestyle swimming", "cycling time trial", "long jump"]
CELEBRITIES = ["Amara Sterling", "Christian Bale", "Scarlett Johansson", "Keanu Reeves", "Zendaya"]
MEDIA_TYPES = ["directing debut", "sci-fi blockbuster", "indie drama series", "music album launch"]

CATEGORIES = [
    "Technology", "Business", "Science", "Health", "World", 
    "Politics", "Sports", "Entertainment", "Environment", "Education",
    "Space", "AI", "Cybersecurity", "Gaming", "Finance"
]

TEMPLATES = {
    "AI": [
        ("OpenAI releases {product} with multimodal capabilities", 
         "OpenAI has officially launched {product}, a new AI model designed to process text, image, and audio inputs simultaneously. Industry analysts predict this will revolutionize automated workflows.",
         "Google DeepMind announces competing reasoning benchmarks.",
         "Industry groups publish concerns over safety bounds."),
        ("Google DeepMind unveils {product} to tackle complex reasoning",
         "Google DeepMind announced the release of {product}, a state-of-the-art AI system designed to solve complex scientific and mathematical reasoning tasks with high accuracy.",
         "MIT researchers praise the reasoning architecture.",
         "Stock prices rally on the heels of the product launch."),
        ("Anthropic introduces {product} for secure enterprise scaling",
         "Anthropic has rolled out {product}, focused on long-context processing and secure data handling for large enterprises. The model claims advanced prompt validation checks.",
         "Enterprise security audits verify privacy claims.",
         "Competitors claim comparable security standards exist."),
        ("US regulators draft new safety guidelines for {product} models",
         "Government authorities have released a draft proposal outlining safety standards for large language models like {product}, aiming to mitigate systemic risks while fostering innovation.",
         "Senate hearings discuss compliance benchmarks.",
         "Tech trade groups lobby for relaxed safety guidelines.")
    ],
    "Space": [
        ("NASA Artemis mission prepares for {rocket} launch",
         "NASA's Artemis program completed a successful launch pad test of the {rocket} system, preparing for the upcoming crewed lunar flyby scheduled for late next year.",
         "ESA confirms payload integration schedules.",
         "Private contractors report supply chain delays."),
        ("SpaceX Starship orbital test flight reaches new milestone",
         "SpaceX's next-generation Starship spacecraft successfully completed its orbit phase before splashdown, paving the way for rapid reuse testing.",
         "Launch engineers analyze heat shield telemetry.",
         "Local environmental groups voice noise pollution concerns."),
        ("James Webb Telescope detects signs of water on exoplanet {planet}",
         "Using advanced transmission spectroscopy, the James Webb Space Telescope has identified water vapor signatures in the atmosphere of exoplanet {planet}.",
         "Astronomers debate potential atmospheric pressure layers.",
         "Space agency releases revised habitable zone charts.")
    ],
    "Business": [
        ("Global markets rally as inflation rates decline in {country}",
         "Stock indexes surged across international markets today as {country} reported lower-than-expected inflation numbers, fueling hopes for interest rate cuts.",
         "Federal Reserve hints at upcoming rate cuts.",
         "Economists advise caution on long-term employment data."),
        ("Apple hits new record {product} sales during holiday quarter",
         "Apple announced record-breaking quarterly revenue driven by unprecedented consumer demand for its newly launched {product} hardware line.",
         "Retailers report short stock supply lines.",
         "Hardware teardown reveals new custom silicon designs.")
    ],
    "Science": [
        ("Researchers synthesize {discovery} in groundbreaking study",
         "A team of scientists has successfully synthesized a {discovery}, representing a monumental breakthrough in the field of {field} after decades of research.",
         "Independent laboratory replication attempts begin.",
         "Nobel laureates highlight industrial scaling potential.")
    ],
    "Health": [
        ("New clinical trials show {discovery} reduces severe symptoms",
         "Clinical phase-III trials conducted by {institution} show that a {discovery} substantially reduces symptoms with negligible side effects.",
         "FDA fast-tracks review of the therapeutic agent.",
         "Public healthcare advocates raise pricing equity concerns.")
    ],
    "Cybersecurity": [
        ("Ransomware attack targets electric grid infrastructure in {country}",
         "State-sponsored cyber threat actors launched a sophisticated ransomware campaign targeting power grids across {country}, causing temporary localized outages.",
         "National guard cyber division deployed to assist.",
         "Security experts trace exploit signatures to known groups.")
    ],
    "World": [
        ("Diplomats gather in {country} to sign historic maritime treaty",
         "Representatives from over thirty nations gathered in {country} to establish unified rules governing international shipping lanes and ecological borders.",
         "Environmental watchdogs praise the treaty terms.",
         "Coastal nations highlight enforcement funding shortages.")
    ],
    "Politics": [
        ("Legislators in {country} vote to pass massive {policy} bill",
         "The parliament of {country} passed a landmark {policy} package, allocating billions in funding to address pressing {issue} concerns over the next decade.",
         "Opposition parties vote down parts of the package.",
         "Public surveys report mixed sentiment regarding the tax impact.")
    ],
    "Sports": [
        ("Athlete {athlete} breaks world record in {sport} championship",
         "In an historic athletic performance, {athlete} shattered the standing world record in the {sport} finals, claiming gold ahead of top competitors.",
         "Coaching staff highlights specialized wind tunnel training.",
         "Official sporting body validates record metrics.")
    ],
    "Entertainment": [
        ("Actress {celebrity} announces highly anticipated {media_type}",
         "Award-winning artist {celebrity} surprised fans today by detailing plans for her next {media_type}, set to launch across major digital networks next month.",
         "Studio releases teaser footage to critical acclaim.",
         "Distribution platforms compete for exclusive rights.")
    ],
    "Environment": [
        ("Renewable energy supplies exceed fossil fuels in {country}",
         "National grid operators in {country} reported that wind, solar, and hydro supplies contributed over 60% of total electrical consumption last month.",
         "Coal power plants transition to standby status.",
         "Grid stability analysts recommend battery expansions.")
    ],
    "Education": [
        ("Top universities launch joint online credential in {field}",
         "Leading academic institutions announced a joint professional certification in {field}, aiming to expand access to high-demand technical training.",
         "Student unions praise lower pricing structures.",
         "Education specialists evaluate student engagement data.")
    ],
    "Gaming": [
        ("Developers showcase sequel to award-winning {product} franchise",
         "Game studio representatives unveiled gameplay footage for their upcoming sequel, promising a revamped graphics engine and expansive narrative paths.",
         "Pre-orders break industry platform records.",
         "Engine developers detail custom physics optimizations.")
    ],
    "Finance": [
        ("Investment firms launch structured funds tracking {field} assets",
         "Major investment managers announced the launch of index funds targeted at sustainable {field} startups, attracting high institutional interest.",
         "Regulatory reviews examine greenwashing risks.",
         "Fund managers project double-digit yield growth.")
    ]
}

# Add default templates for any missing categories to prevent KeyError
for cat in CATEGORIES:
    if cat not in TEMPLATES:
        TEMPLATES[cat] = [
            ("New initiatives launched in {cat} sector",
             "A coalition of organizations announced a new initiative in the {cat} sector, hoping to drive standard practices and long-term sustainability.",
             "Supporting members declare early milestone achievements.",
             "Critics voice concerns over regulatory oversight gaps.")
        ]

# ── Helper Generative Logic ──────────────────────────────────────────────────

def generate_hashes(title: str, body: str):
    """Creates MD5 or SHA hashes to replicate data validator requirements."""
    content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    article_hash = hashlib.sha256((title + body).encode('utf-8')).hexdigest()
    return content_hash, article_hash

# ── Main Seed Task ───────────────────────────────────────────────────────────

async def seed_demo_mode_data():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: OFFLINE DEMO MODE SEEDING")
    print("=" * 60)
    print(f"PostgreSQL target: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    print(f"Qdrant target: {settings.QDRANT_URL}")
    print(f"Redis target: {settings.REDIS_URL}")

    # 1. Truncate Database Tables
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        print("\n[*] Resetting database schemas and tables...")
        # Cascade truncate to drop all table rows efficiently
        await conn.execute(text("""
            TRUNCATE TABLE 
                users, 
                user_profiles, 
                publishers, 
                stories, 
                story_relations, 
                articles, 
                article_duplicates, 
                story_timelines, 
                chat_sessions, 
                chat_messages, 
                user_recommendation_logs 
            RESTART IDENTITY CASCADE;
        """))
        print("[PASS] Database tables truncated successfully.")

    # 2. Reset Qdrant Collections
    q_client = QdrantClient(url=settings.QDRANT_URL)
    cols = ["articles", "stories", "user_preferences"]
    print("\n[*] Resetting Qdrant vector collections...")
    for c in cols:
        try:
            q_client.delete_collection(c)
            print(f"  [-] Deleted collection: {c}")
        except Exception:
            pass
        q_client.create_collection(
            collection_name=c,
            vectors_config=models.VectorParams(
                size=384,
                distance=models.Distance.COSINE
            )
        )
        print(f"  [+] Created collection: {c}")

    # 3. Seed Publishers
    publishers_data = [
        {"id": "bbc", "name": "BBC News", "url": "https://www.bbc.com", "cred": 0.92, "bias": "center"},
        {"id": "reuters", "name": "Reuters News", "url": "https://www.reuters.com", "cred": 0.95, "bias": "center"},
        {"id": "ap", "name": "Associated Press", "url": "https://apnews.com", "cred": 0.94, "bias": "center"},
        {"id": "techcrunch", "name": "TechCrunch", "url": "https://techcrunch.com", "cred": 0.88, "bias": "center"},
        {"id": "theverge", "name": "The Verge", "url": "https://www.theverge.com", "cred": 0.87, "bias": "center"},
        {"id": "mit_tech_review", "name": "MIT Technology Review", "url": "https://www.technologyreview.com", "cred": 0.93, "bias": "center"},
        {"id": "wired", "name": "Wired", "url": "https://www.wired.com", "cred": 0.89, "bias": "center"},
        {"id": "cnbc", "name": "CNBC", "url": "https://www.cnbc.com", "cred": 0.89, "bias": "center"},
        {"id": "thehindu", "name": "The Hindu", "url": "https://www.thehindu.com", "cred": 0.88, "bias": "center"},
        {"id": "guardian", "name": "The Guardian", "url": "https://www.theguardian.com", "cred": 0.91, "bias": "center"},
        {"id": "bloomberg", "name": "Bloomberg", "url": "https://www.bloomberg.com", "cred": 0.94, "bias": "center"},
        {"id": "nytimes", "name": "The New York Times", "url": "https://www.nytimes.com", "cred": 0.92, "bias": "center"},
        {"id": "wsj", "name": "The Wall Street Journal", "url": "https://www.wsj.com", "cred": 0.93, "bias": "center"},
        {"id": "cnn", "name": "CNN", "url": "https://www.cnn.com", "cred": 0.86, "bias": "left-center"},
        {"id": "aljazeera", "name": "Al Jazeera", "url": "https://www.aljazeera.com", "cred": 0.87, "bias": "center"}
    ]

    async with async_session() as session:
        print("\n[*] Seeding 15 news publishers...")
        for p in publishers_data:
            pub = Publisher(
                id=p["id"],
                name=p["name"],
                base_url=p["url"],
                credibility_score=p["cred"],
                bias_rating=p["bias"]
            )
            session.add(pub)
        await session.commit()
        print(f"[PASS] Seeded {len(publishers_data)} publishers.")

    # 4. Generate 300 Stories & Articles in a loop
    embedder = EmbedderService()
    
    # We want stories to be spread chronologically over the last 10 days
    base_time = datetime.now(timezone.utc)
    
    print("\n[*] Preparing story generation pipeline...")
    story_records = []
    article_records = []
    timeline_records = []
    
    story_embeddings_to_generate = []
    story_texts_for_embeddings = []
    
    # Track stories created per category to dynamically build relations
    stories_by_category = {cat: [] for cat in CATEGORIES}

    random.seed(42)  # Deterministic mock generation

    for cat in CATEGORIES:
        category_templates = TEMPLATES.get(cat, TEMPLATES["AI"])
        for i in range(20):  # 20 stories per category = 300 stories total
            story_id = uuid.uuid4()
            pub_date = base_time - timedelta(days=random.randint(0, 9), hours=random.randint(0, 23))

            # Pick template
            tpl = random.choice(category_templates)
            title_tpl, body_tpl, detail1, detail2 = tpl
            
            # Format parameters
            company = random.choice(COMPANIES)
            product = random.choice(PRODUCTS)
            focus = random.choice(FOCUS_AREAS)
            country = random.choice(COUNTRIES)
            issue = random.choice(ISSUES)
            policy = random.choice(POLICIES)
            discovery = random.choice(DISCOVERIES)
            field = random.choice(FIELDS)
            inst = random.choice(INSTITUTIONS)
            planet = random.choice(PLANETS)
            rover = random.choice(ROVERS)
            athlete = random.choice(ATHLETES)
            sport = random.choice(SPORTS)
            celeb = random.choice(CELEBRITIES)
            media = random.choice(MEDIA_TYPES)
            rocket = random.choice(["SLS", "Falcon Heavy", "Starship", "Vulcan"])
            
            title = title_tpl.format(
                company=company, product=product, focus=focus, country=country, issue=issue,
                policy=policy, discovery=discovery, field=field, institution=inst, planet=planet,
                rover=rover, athlete=athlete, sport=sport, celebrity=celeb, media_type=media,
                rocket=rocket, version=random.randint(2, 5), cat=cat
            )
            
            summary = body_tpl.format(
                company=company, product=product, focus=focus, country=country, issue=issue,
                policy=policy, discovery=discovery, field=field, institution=inst, planet=planet,
                rover=rover, athlete=athlete, sport=sport, celebrity=celeb, media_type=media,
                rocket=rocket, version=random.randint(2, 5), cat=cat
            )

            # Generate multi-level summaries
            summary_quick = f"QUICK SUM: {summary[:120]}..."
            summary_beginner = f"BEGINNER SUM: The event focuses on {cat.lower()}. Specifically, {summary}"
            summary_professional = f"PROFESSIONAL DEEP DIVE: Analysts report {summary} Implications on industry regulations are developing."

            # Mock scores
            credibility_score = round(random.uniform(0.75, 0.95), 2)
            verification_score = round(random.uniform(0.60, 0.98), 2)
            has_conflicts = random.choice([True, False, False, False]) # 25% chance of conflict
            
            # Determine article count: 1 to 3
            art_count = random.randint(1, 3)
            
            story_dict = {
                "id": story_id,
                "title": title,
                "summary": summary,
                "summary_quick": summary_quick,
                "summary_beginner": summary_beginner,
                "summary_professional": summary_professional,
                "importance_score": round(random.uniform(0.3, 0.95), 2),
                "trending_score": round(random.uniform(0.2, 0.90), 2),
                "credibility_score": credibility_score,
                "verification_score": verification_score,
                "has_conflicts": has_conflicts,
                "publisher_diversity": art_count,
                "article_count": art_count,
                "first_reported_at": pub_date - timedelta(hours=12),
                "last_updated_at": pub_date,
                "status": "ACTIVE",
                "evidence": [],
                "verification_metadata": {
                    "agreement_score": round(random.uniform(0.70, 0.98), 2),
                    "publisher_diversity": art_count,
                    "trusted_publishers": art_count,
                    "supporting_articles": art_count,
                    "conflicting_articles": 1 if has_conflicts else 0,
                    "semantic_confidence": 0.88
                }
            }

            story_records.append(story_dict)
            stories_by_category[cat].append(story_id)
            
            # Keep text for vector generation
            story_texts_for_embeddings.append((story_id, f"{title}. {summary[:500]}", cat))
            
            # Generate Articles
            selected_pubs = random.sample(publishers_data, art_count)
            for a_idx in range(art_count):
                art_id = uuid.uuid4()
                pub = selected_pubs[a_idx]
                
                art_title = title if a_idx == 0 else f"{pub['name']} Reports: {title}"
                art_body = f"{summary} In addition, {detail1 if a_idx == 0 else detail2}. Reporting from the ground, correspondents highlighted the impact of this event on local communities and international markets. [Ref: {str(art_id)[:8]}]"
                
                content_hash, article_hash = generate_hashes(art_title, art_body)
                
                article_dict = {
                    "id": art_id,
                    "story_id": story_id,
                    "publisher_id": pub["id"],
                    "title": art_title,
                    "body_text": art_body,
                    "source_url": f"{pub['url']}/article/{art_id}",
                    "published_at": pub_date - timedelta(hours=(art_count - 1 - a_idx) * 4),
                    "content_hash": content_hash,
                    "article_hash": article_hash,
                    "quality_score": round(random.uniform(0.70, 0.98), 2),
                    "predicted_category": cat,
                    "category_confidence": 0.95
                }
                article_records.append(article_dict)
                
                # Update story evidence
                story_dict["evidence"].append({
                    "publisher_id": pub["id"],
                    "credibility": pub["cred"],
                    "article_title": art_title,
                    "article_hash": article_hash
                })

            # Generate Timelines
            for t_idx in range(random.randint(1, 3)):
                timeline_records.append({
                    "id": uuid.uuid4(),
                    "story_id": story_id,
                    "event_timestamp": pub_date - timedelta(hours=(3 - t_idx) * 6),
                    "headline": f"Milestone update: {title[:80]}...",
                    "description": f"Details and developments emerge regarding the event. Publishers from multiple regions report steady progress and investigate local impacts.",
                    "event_type": "first_appearance" if t_idx == 0 else ("correction" if has_conflicts and t_idx == 1 else "update"),
                    "confidence_score": round(random.uniform(0.80, 0.98), 2),
                    "supporting_articles": art_count,
                    "supporting_publishers": art_count
                })

    print(f"[+] Formulated {len(story_records)} stories and {len(article_records)} articles.")

    # 5. Compute real SentenceTransformer embeddings for Stories and upsert to Qdrant
    print("\n[*] Generating SentenceTransformer vector embeddings for story centroids...")
    t_emb_start = time.time()
    texts = [item[1] for item in story_texts_for_embeddings]
    embeddings = embedder.generate_embeddings_batch(texts)
    print(f"  [OK] Generated {len(embeddings)} vectors in {time.time() - t_emb_start:.2f}s.")

    # Upsert to Qdrant (stories and articles)
    print("[*] Uploading vectors to Qdrant collection: 'stories'...")
    points = []
    for idx, (story_id, text_content, category) in enumerate(story_texts_for_embeddings):
        points.append(
            models.PointStruct(
                id=str(story_id),
                vector=embeddings[idx],
                payload={
                    "title": story_records[idx]["title"],
                    "category": category,
                    "importance_score": story_records[idx]["importance_score"],
                    "trending_score": story_records[idx]["trending_score"]
                }
            )
        )
    # Batch upsert to Qdrant
    q_client.upsert(
        collection_name="stories",
        points=points,
        wait=True
    )
    print("[PASS] Story vectors uploaded.")

    # Also upload article vectors
    print("[*] Uploading vectors to Qdrant collection: 'articles'...")
    art_points = []
    # We will compute embeddings for all articles in a batch
    art_texts = [f"{a['title']}. {a['body_text'][:500]}" for a in article_records]
    t_art_emb_start = time.time()
    art_embeddings = embedder.generate_embeddings_batch(art_texts)
    print(f"  [OK] Generated {len(art_embeddings)} article vectors in {time.time() - t_art_emb_start:.2f}s.")

    for idx, a in enumerate(article_records):
        art_points.append(
            models.PointStruct(
                id=str(a["id"]),
                vector=art_embeddings[idx],
                payload={
                    "publisher_id": a["publisher_id"],
                    "category": a["predicted_category"]
                }
            )
        )
    # Chunk large uploads
    chunk_size = 200
    for chunk_idx in range(0, len(art_points), chunk_size):
        q_client.upsert(
            collection_name="articles",
            points=art_points[chunk_idx:chunk_idx + chunk_size],
            wait=True
        )
    print("[PASS] Article vectors uploaded.")

    # 6. Bulk Insert to PostgreSQL Database
    async with async_session() as session:
        print("\n[*] Inserting stories and articles to PostgreSQL database...")
        # Insert Stories
        for s in story_records:
            db_story = Story(
                id=s["id"],
                title=s["title"],
                summary=s["summary"],
                summary_quick=s["summary_quick"],
                summary_beginner=s["summary_beginner"],
                summary_professional=s["summary_professional"],
                importance_score=s["importance_score"],
                trending_score=s["trending_score"],
                credibility_score=s["credibility_score"],
                verification_score=s["verification_score"],
                has_conflicts=s["has_conflicts"],
                publisher_diversity=s["publisher_diversity"],
                article_count=s["article_count"],
                first_reported_at=s["first_reported_at"],
                last_updated_at=s["last_updated_at"],
                status=s["status"],
                evidence=s["evidence"],
                verification_metadata=s["verification_metadata"],
                centroid_vector_id=str(s["id"])
            )
            session.add(db_story)
        await session.commit()
        print(f"  [+] Saved {len(story_records)} stories.")

        # Insert Articles
        for a in article_records:
            db_art = Article(
                id=a["id"],
                story_id=a["story_id"],
                publisher_id=a["publisher_id"],
                title=a["title"],
                body_text=a["body_text"],
                source_url=a["source_url"],
                published_at=a["published_at"],
                content_hash=a["content_hash"],
                article_hash=a["article_hash"],
                quality_score=a["quality_score"],
                predicted_category=a["predicted_category"],
                category_confidence=a["category_confidence"]
            )
            session.add(db_art)
        await session.commit()
        print(f"  [+] Saved {len(article_records)} articles.")

        # Set representative_article_id on Stories (pick the first article as representative)
        for s in story_records:
            # Find first article associated with this story
            story_arts = [a for a in article_records if a["story_id"] == s["id"]]
            if story_arts:
                stmt_u = text("UPDATE stories SET representative_article_id = :art_id WHERE id = :story_id")
                await session.execute(stmt_u, {"art_id": story_arts[0]["id"], "story_id": s["id"]})
        await session.commit()
        print("  [+] Updated representative article links.")

        # Insert Timelines
        for t in timeline_records:
            db_tl = StoryTimeline(
                id=t["id"],
                story_id=t["story_id"],
                event_timestamp=t["event_timestamp"],
                headline=t["headline"],
                description=t["description"],
                event_type=t["event_type"],
                confidence_score=t["confidence_score"],
                supporting_articles=t["supporting_articles"],
                supporting_publishers=t["supporting_publishers"]
            )
            session.add(db_tl)
        await session.commit()
        print(f"  [+] Saved {len(timeline_records)} timeline milestones.")

        # Generate and Insert StoryRelations
        print("[*] Generating story-to-story graph relations...")
        relations_seeded = 0
        for cat, s_ids in stories_by_category.items():
            # Link sequential stories in same category
            for r_idx in range(len(s_ids) - 1):
                parent_id = s_ids[r_idx]
                child_id = s_ids[r_idx + 1]
                relation = StoryRelation(
                    parent_story_id=parent_id,
                    child_story_id=child_id,
                    relation_type="FOLLOW_UP" if r_idx % 2 == 0 else "RELATED"
                )
                session.add(relation)
                relations_seeded += 1
        await session.commit()
        print(f"  [+] Saved {relations_seeded} story relations.")

        # 7. Seed Test Users
        print("\n[*] Seeding test users (cold@test.com & warm@test.com)...")
        default_hash = hash_password("password123")
        cold_id = uuid.uuid4()
        cold_user = User(
            id=cold_id,
            email="cold@test.com",
            interaction_count=0,
            hashed_password=default_hash
        )
        session.add(cold_user)
        
        warm_id = uuid.UUID("93831985-52fa-47a8-91f9-08a312d06613")  # Hardcoded or stable UUID for warm user
        warm_user = User(
            id=warm_id,
            email="warm@test.com",
            interaction_count=10,
            preference_vector_id=str(warm_id),
            hashed_password=default_hash
        )
        session.add(warm_user)
        
        profile = UserProfile(
            user_id=warm_id,
            preference_vector_id=str(warm_id),
            interaction_count=10,
            muted_categories=["Sports"],
            muted_publishers=[]
        )
        session.add(profile)
        await session.commit()
        print("[PASS] Test users created.")

        # 8. Set up warm user preference vector in Qdrant & Redis
        # Warm user preference is centered around "Technology" and "AI"
        tech_story_vectors = [embeddings[idx] for idx, item in enumerate(story_texts_for_embeddings) if item[2] in ["Technology", "AI"]]
        if tech_story_vectors:
            # Average vector
            mean_vector = np.mean(np.array(tech_story_vectors), axis=0)
            # L2 normalize
            mean_vector = mean_vector / np.linalg.norm(mean_vector)
            mean_vector_list = mean_vector.tolist()
        else:
            mean_vector_list = [0.1] * 384  # fallback
            
        print("[*] Uploading warm user preference vector to Qdrant 'user_preferences' collection...")
        q_client.upsert(
            collection_name="user_preferences",
            points=[
                models.PointStruct(
                    id=str(warm_id),
                    vector=mean_vector_list,
                    payload={"email": "warm@test.com"}
                )
            ],
            wait=True
        )
        print("[PASS] Qdrant user preference vector uploaded.")

        # Hydrate Redis for warm user preference vector ID
        import redis.asyncio as aioredis
        r_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
        # Store user preference vector key
        redis_key = f"user:pref:{warm_id}"
        # We store the Qdrant reference string
        await r_client.set(redis_key, str(warm_id))
        await r_client.aclose()
        print("[PASS] Redis preference vector reference cached.")

    await engine.dispose()
    print("\n" + "=" * 60)
    print("      DEMO DATA SEEDING COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(seed_demo_mode_data())
