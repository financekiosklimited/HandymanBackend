"""
Management command to generate dummy data for demo purposes.

Usage:
    python manage.py generate_dummy_data

This will create:
    - 200 homeowner users with profiles
    - 200 handyman users with profiles
    - 1000 jobs with varied attachments (0-5 per job)
    - Job applications for open jobs
    - Work sessions for in_progress/completed jobs
    - Daily reports based on work sessions
    - Reviews for completed jobs

All generated data will have is_dummy=True for easy cleanup.
Images are shared across records to speed up generation.
"""

import io
import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import (
    City,
    DailyReport,
    DailyReportTask,
    Job,
    JobApplication,
    JobApplicationAttachment,
    JobApplicationMaterial,
    JobAttachment,
    JobCategory,
    JobTask,
    Review,
    WorkSession,
    WorkSessionMedia,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile

# =============================================================================
# CONFIGURATION
# =============================================================================

NUM_HOMEOWNERS = 200
NUM_HANDYMEN = 200
NUM_JOBS = 1000
DUMMY_PASSWORD = "SolutionBank123#"

# Job status distribution (percentages)
STATUS_WEIGHTS = {
    "open": 50,
    "in_progress": 30,
    "completed": 20,
}

# Attachment distribution per job (num_attachments: weight)
ATTACHMENT_WEIGHTS = {
    0: 15,
    1: 15,
    2: 20,
    3: 25,
    4: 15,
    5: 10,
}

# Direct offer percentage
DIRECT_OFFER_PERCENT = 15

# Applications per open job
MIN_APPLICATIONS = 2
MAX_APPLICATIONS = 6

# Work sessions per in_progress/completed job
MIN_WORK_SESSIONS = 1
MAX_WORK_SESSIONS = 3

# Session media per work session
MIN_SESSION_MEDIA = 0
MAX_SESSION_MEDIA = 3

# Review rating weights (higher ratings more common)
RATING_WEIGHTS = {
    5: 40,
    4: 35,
    3: 15,
    2: 7,
    1: 3,
}

# Daily report status weights
REPORT_STATUS_WEIGHTS = {
    "approved": 60,
    "pending": 30,
    "rejected": 10,
}

# =============================================================================
# NAME DATA
# =============================================================================

FIRST_NAMES = [
    "James",
    "John",
    "Robert",
    "Michael",
    "William",
    "David",
    "Richard",
    "Joseph",
    "Thomas",
    "Christopher",
    "Mary",
    "Patricia",
    "Jennifer",
    "Linda",
    "Elizabeth",
    "Barbara",
    "Susan",
    "Jessica",
    "Sarah",
    "Karen",
    "Daniel",
    "Matthew",
    "Anthony",
    "Mark",
    "Donald",
    "Steven",
    "Paul",
    "Andrew",
    "Joshua",
    "Kenneth",
    "Nancy",
    "Betty",
    "Margaret",
    "Sandra",
    "Ashley",
    "Kimberly",
    "Emily",
    "Donna",
    "Michelle",
    "Dorothy",
    "Kevin",
    "Brian",
    "George",
    "Timothy",
    "Ronald",
    "Edward",
    "Jason",
    "Jeffrey",
    "Ryan",
    "Jacob",
    "Carol",
    "Amanda",
    "Melissa",
    "Deborah",
    "Stephanie",
    "Rebecca",
    "Sharon",
    "Laura",
    "Cynthia",
    "Kathleen",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
    "Carter",
    "Roberts",
]

# =============================================================================
# LOCATION DATA
# =============================================================================

AREA_CODES = ["416", "647", "437", "905", "289", "365", "604", "778", "403"]

STREET_NAMES = [
    "Main Street",
    "Oak Avenue",
    "Maple Drive",
    "King Street",
    "Queen Street",
    "Yonge Street",
    "Bloor Street",
    "College Street",
    "Dundas Street",
    "Bay Street",
    "Front Street",
    "Adelaide Street",
    "Wellington Street",
    "Elm Street",
    "Pine Road",
    "Cedar Lane",
    "Birch Avenue",
    "Willow Way",
    "Cherry Crescent",
    "Spruce Boulevard",
]

POSTAL_PREFIXES = {
    "ON": ["M", "N", "K", "L"],
    "BC": ["V"],
    "AB": ["T"],
    "QC": ["H", "J"],
    "MB": ["R"],
    "NS": ["B"],
}

# =============================================================================
# JOB DATA BY CATEGORY
# =============================================================================

JOB_DATA_BY_CATEGORY = {
    "plumbing": {
        "titles": [
            "Fix leaky faucet in kitchen",
            "Unclog bathroom drain",
            "Replace toilet in master bath",
            "Install new sink in basement",
            "Repair water heater",
            "Fix shower head leak",
            "Replace garbage disposal",
            "Install water filtration system",
        ],
        "descriptions": [
            "Water is leaking from under the sink. Need someone to fix it ASAP.",
            "My toilet keeps running constantly. Looking for a plumber to diagnose.",
            "Need to replace old corroded pipes in the basement showing rust.",
            "Shower head drips constantly and the drain is very slow.",
            "Water pressure has dropped significantly throughout the house.",
            "Looking for a licensed plumber to install new fixtures.",
        ],
        "tasks": [
            "Inspect plumbing issue",
            "Turn off water supply",
            "Remove old fixtures",
            "Install new parts",
            "Test for leaks",
            "Clean work area",
            "Dispose of old materials",
        ],
    },
    "electrical": {
        "titles": [
            "Install ceiling fan in bedroom",
            "Replace light switches",
            "Fix flickering lights",
            "Add electrical outlet",
            "Install dimmer switches",
            "Upgrade electrical panel",
            "Install outdoor lighting",
            "Fix circuit breaker issues",
        ],
        "descriptions": [
            "Need a licensed electrician to install a new ceiling fan.",
            "Several outlets in the house have stopped working.",
            "Lights flicker randomly. Concerned about electrical safety.",
            "Looking to add more outlets in the home office.",
            "Want to upgrade to smart dimmer switches throughout.",
            "Circuit breaker keeps tripping. Need professional assessment.",
        ],
        "tasks": [
            "Inspect electrical system",
            "Turn off power at breaker",
            "Remove old wiring/fixtures",
            "Install new components",
            "Test all connections",
            "Verify safety compliance",
            "Clean up work area",
        ],
    },
    "carpentry": {
        "titles": [
            "Build custom shelving unit",
            "Repair deck boards",
            "Install interior door",
            "Fix squeaky floors",
            "Build closet organizer",
            "Repair window frame",
            "Install crown molding",
            "Build garden shed",
        ],
        "descriptions": [
            "Looking for a skilled carpenter to build custom storage.",
            "Deck has several rotting boards that need replacement.",
            "Need a new door installed with proper framing.",
            "Floors creak loudly in multiple rooms. Need fixing.",
            "Want a custom closet organization system built.",
            "Window frame is damaged and letting in drafts.",
        ],
        "tasks": [
            "Measure and plan",
            "Gather materials",
            "Remove damaged sections",
            "Cut new pieces to size",
            "Install and secure",
            "Sand and finish",
            "Clean work area",
        ],
    },
    "cleaning": {
        "titles": [
            "Deep clean entire house",
            "Move-out cleaning service",
            "Carpet deep cleaning",
            "Window cleaning inside/out",
            "Post-construction cleanup",
            "Spring cleaning service",
            "Garage cleanout",
            "Basement deep clean",
        ],
        "descriptions": [
            "Need thorough deep cleaning of 3-bedroom house.",
            "Moving out and need professional cleaning for deposit.",
            "Carpets haven't been cleaned in years. Need professional service.",
            "All windows need cleaning inside and outside.",
            "Just finished renovation. Need all dust and debris cleaned.",
            "Annual spring cleaning needed throughout the home.",
        ],
        "tasks": [
            "Dust all surfaces",
            "Vacuum and mop floors",
            "Clean bathrooms thoroughly",
            "Clean kitchen appliances",
            "Wash windows",
            "Empty trash and recycling",
            "Final inspection",
        ],
    },
    "painting": {
        "titles": [
            "Paint living room walls",
            "Exterior house painting",
            "Paint kitchen cabinets",
            "Stain deck",
            "Paint bedroom",
            "Touch up paint throughout",
            "Paint fence",
            "Paint garage interior",
        ],
        "descriptions": [
            "Looking for experienced painters to refresh living room.",
            "House exterior needs new coat of paint. About 2000 sq ft.",
            "Want to update kitchen cabinets with new paint color.",
            "Deck needs to be sanded and stained for protection.",
            "Need two bedrooms painted with different colors.",
            "Various rooms need touch-up painting and repairs.",
        ],
        "tasks": [
            "Prep surfaces",
            "Apply painter's tape",
            "Apply primer coat",
            "Apply first paint coat",
            "Apply second coat",
            "Remove tape carefully",
            "Clean up and touch-ups",
        ],
    },
    "landscaping": {
        "titles": [
            "Weekly lawn mowing",
            "Tree trimming service",
            "Garden bed installation",
            "Install irrigation system",
            "Hedge trimming",
            "Leaf removal service",
            "Plant flowers and shrubs",
            "Mulching service",
        ],
        "descriptions": [
            "Need regular lawn maintenance for medium-sized yard.",
            "Several trees need professional trimming and shaping.",
            "Want to create new garden beds in front yard.",
            "Looking to install drip irrigation for garden.",
            "Hedges are overgrown and need professional trimming.",
            "Large yard with many trees. Need fall leaf cleanup.",
        ],
        "tasks": [
            "Assess landscape needs",
            "Gather tools and materials",
            "Mow/trim as needed",
            "Edge along walkways",
            "Remove debris",
            "Apply treatments if needed",
            "Final cleanup",
        ],
    },
    "hvac": {
        "titles": [
            "AC unit not cooling",
            "Furnace maintenance",
            "Install smart thermostat",
            "Clean air ducts",
            "Replace AC filter",
            "Heat pump repair",
            "Install ceiling fan",
            "Fix ventilation issues",
        ],
        "descriptions": [
            "Air conditioner running but not cooling the house.",
            "Need annual furnace tune-up before winter.",
            "Want to upgrade to a smart thermostat system.",
            "Air quality seems poor. Ducts may need cleaning.",
            "Looking for HVAC technician to diagnose heating issue.",
            "Vents not pushing enough air in some rooms.",
        ],
        "tasks": [
            "Inspect HVAC system",
            "Check refrigerant levels",
            "Clean or replace filters",
            "Test thermostat",
            "Check ductwork",
            "Make repairs as needed",
            "Test system operation",
        ],
    },
    "roofing": {
        "titles": [
            "Repair roof leak",
            "Replace missing shingles",
            "Gutter cleaning and repair",
            "Install gutter guards",
            "Roof inspection",
            "Fix flashing around chimney",
            "Repair soffit damage",
            "Skylight repair",
        ],
        "descriptions": [
            "Water stains on ceiling indicate roof leak somewhere.",
            "Storm damage caused several shingles to blow off.",
            "Gutters are clogged and pulling away from house.",
            "Want gutter guards installed to prevent clogging.",
            "Need professional roof inspection before buying home.",
            "Water leaking around chimney area during rain.",
        ],
        "tasks": [
            "Inspect roof damage",
            "Set up safety equipment",
            "Remove damaged materials",
            "Install new materials",
            "Seal all edges",
            "Test for leaks",
            "Clean up debris",
        ],
    },
    "flooring": {
        "titles": [
            "Install hardwood floors",
            "Replace carpet with laminate",
            "Tile bathroom floor",
            "Refinish hardwood floors",
            "Install vinyl plank flooring",
            "Repair damaged tiles",
            "Install heated floor",
            "Level subfloor",
        ],
        "descriptions": [
            "Want to install engineered hardwood in living areas.",
            "Old carpet needs to go. Want laminate throughout.",
            "Bathroom floor tiles are cracked and dated.",
            "Hardwood floors scratched and dull. Need refinishing.",
            "Looking to install luxury vinyl plank in kitchen.",
            "Several floor tiles are cracked and need replacement.",
        ],
        "tasks": [
            "Remove old flooring",
            "Prepare subfloor",
            "Measure and cut materials",
            "Install underlayment",
            "Install flooring",
            "Install transitions/trim",
            "Final cleanup",
        ],
    },
    "appliance-repair": {
        "titles": [
            "Fix washing machine",
            "Repair refrigerator",
            "Dryer not heating",
            "Dishwasher leaking",
            "Oven not heating properly",
            "Fix ice maker",
            "Microwave repair",
            "Garbage disposal jammed",
        ],
        "descriptions": [
            "Washing machine won't spin. Makes grinding noise.",
            "Refrigerator not cooling properly. Food spoiling.",
            "Dryer runs but doesn't produce any heat.",
            "Dishwasher leaks water onto floor during cycle.",
            "Oven temperature seems off. Food not cooking evenly.",
            "Ice maker stopped producing ice. Need diagnosis.",
        ],
        "tasks": [
            "Diagnose the issue",
            "Order replacement parts",
            "Disconnect appliance",
            "Replace faulty components",
            "Reassemble unit",
            "Test operation",
            "Clean work area",
        ],
    },
}

# =============================================================================
# APPLICATION DATA
# =============================================================================

NEGOTIATION_REASONS = [
    "Based on my assessment, this job requires specialized tools and materials "
    "that I've factored into my estimate.",
    "The scope of work is slightly larger than described. I've included time "
    "for proper surface preparation and cleanup.",
    "I've completed many similar jobs before. This estimate includes "
    "high-quality materials for a lasting result.",
    "Price includes thorough cleanup and proper disposal of all old materials "
    "according to local regulations.",
    "My estimate accounts for potential complications that often arise with "
    "this type of work. Better to plan ahead.",
    "I use professional-grade materials and tools which ensure quality work "
    "that will last for years.",
    "This price includes a warranty on my workmanship for peace of mind.",
    "I've included extra time for careful work to ensure everything is done "
    "right the first time.",
]

MATERIALS_CATALOG = {
    "plumbing": [
        {"name": "PVC Pipes", "price": 25.00, "description": "10ft sections"},
        {"name": "Pipe fittings", "price": 15.00, "description": "Assorted set"},
        {"name": "Plumber's tape", "price": 5.00, "description": "2 rolls"},
        {"name": "Drain cleaner", "price": 12.00, "description": "Professional grade"},
        {"name": "Replacement valves", "price": 35.00, "description": "Brass"},
        {"name": "Silicone sealant", "price": 8.00, "description": "Waterproof"},
    ],
    "electrical": [
        {"name": "Wire (14 gauge)", "price": 45.00, "description": "100ft roll"},
        {"name": "Outlets", "price": 20.00, "description": "Pack of 5"},
        {"name": "Switch plates", "price": 12.00, "description": "Pack of 3"},
        {"name": "Wire nuts", "price": 8.00, "description": "Assorted sizes"},
        {"name": "Electrical tape", "price": 6.00, "description": "3 rolls"},
        {"name": "Junction boxes", "price": 15.00, "description": "Pack of 4"},
    ],
    "carpentry": [
        {"name": "Lumber (2x4)", "price": 35.00, "description": "8ft pieces x5"},
        {"name": "Wood screws", "price": 12.00, "description": "Box of 100"},
        {"name": "Wood glue", "price": 8.00, "description": "16oz bottle"},
        {"name": "Sandpaper", "price": 15.00, "description": "Assorted grits"},
        {"name": "Wood stain", "price": 25.00, "description": "1 quart"},
        {"name": "Finishing nails", "price": 10.00, "description": "Box of 200"},
    ],
    "painting": [
        {"name": "Interior paint", "price": 45.00, "description": "1 gallon"},
        {"name": "Primer", "price": 30.00, "description": "1 gallon"},
        {"name": "Paint brushes", "price": 25.00, "description": "Set of 5"},
        {"name": "Roller covers", "price": 18.00, "description": "Pack of 6"},
        {"name": "Painter's tape", "price": 12.00, "description": "3 rolls"},
        {"name": "Drop cloths", "price": 20.00, "description": "Pack of 2"},
    ],
    "landscaping": [
        {"name": "Mulch", "price": 40.00, "description": "2 cubic yards"},
        {"name": "Topsoil", "price": 35.00, "description": "1 cubic yard"},
        {"name": "Fertilizer", "price": 25.00, "description": "20lb bag"},
        {"name": "Plants/shrubs", "price": 60.00, "description": "Assorted"},
        {"name": "Landscape fabric", "price": 30.00, "description": "50ft roll"},
        {"name": "Edging", "price": 22.00, "description": "20ft"},
    ],
    "hvac": [
        {"name": "Air filters", "price": 35.00, "description": "Pack of 4"},
        {"name": "Refrigerant", "price": 75.00, "description": "Per pound"},
        {"name": "Thermostat wire", "price": 20.00, "description": "50ft"},
        {"name": "Duct tape (HVAC)", "price": 15.00, "description": "2 rolls"},
        {"name": "Condensate line", "price": 12.00, "description": "10ft"},
        {"name": "Capacitor", "price": 45.00, "description": "Replacement"},
    ],
    "roofing": [
        {"name": "Shingles", "price": 85.00, "description": "Bundle"},
        {"name": "Roofing nails", "price": 20.00, "description": "5lb box"},
        {"name": "Roof sealant", "price": 25.00, "description": "Tube"},
        {"name": "Flashing", "price": 35.00, "description": "10ft roll"},
        {"name": "Underlayment", "price": 45.00, "description": "Roll"},
        {"name": "Gutter hangers", "price": 18.00, "description": "Pack of 10"},
    ],
    "flooring": [
        {"name": "Underlayment", "price": 40.00, "description": "200 sq ft"},
        {"name": "Transition strips", "price": 25.00, "description": "Pack of 3"},
        {"name": "Floor adhesive", "price": 35.00, "description": "1 gallon"},
        {"name": "Spacers", "price": 8.00, "description": "Pack of 50"},
        {"name": "Quarter round", "price": 20.00, "description": "8ft pieces"},
        {"name": "Tapping block", "price": 12.00, "description": "1 piece"},
    ],
    "appliance-repair": [
        {"name": "Replacement belt", "price": 25.00, "description": "OEM part"},
        {"name": "Heating element", "price": 55.00, "description": "OEM part"},
        {"name": "Door seal", "price": 35.00, "description": "OEM part"},
        {"name": "Thermostat", "price": 40.00, "description": "OEM part"},
        {"name": "Motor brushes", "price": 20.00, "description": "Pair"},
        {"name": "Water inlet valve", "price": 30.00, "description": "OEM part"},
    ],
    "cleaning": [
        {"name": "Cleaning supplies", "price": 30.00, "description": "Assorted"},
        {"name": "Trash bags", "price": 15.00, "description": "Box of 50"},
        {"name": "Microfiber cloths", "price": 12.00, "description": "Pack of 10"},
        {"name": "Vacuum bags", "price": 18.00, "description": "Pack of 5"},
    ],
}

# =============================================================================
# REPORT AND REVIEW DATA
# =============================================================================

REPORT_SUMMARIES = [
    "Completed the initial inspection and prepared the work area. "
    "Identified all issues and gathered necessary materials.",
    "Made excellent progress on the main repair today. Work is approximately "
    "60% complete. Will finish tomorrow.",
    "Continued work on the project. Encountered a minor issue that required "
    "additional time but resolved it successfully.",
    "Finished all major work today. Did final testing and everything is "
    "functioning properly.",
    "Wrapped up the job completely. Cleaned the entire work area and disposed "
    "of all debris properly.",
    "Good productive day. Completed several key tasks and the project is "
    "on track for completion.",
    "Focused on detail work today. Taking extra care to ensure quality "
    "results that will last.",
    "Final day on the job. Completed all remaining tasks and did a thorough "
    "walkthrough with the homeowner.",
]

HOMEOWNER_REVIEW_COMMENTS = [
    "Excellent work! Very professional and thorough. Cleaned up perfectly "
    "after completing the job. Highly recommended!",
    "Great experience from start to finish. Arrived on time, communicated "
    "well, and did quality work. Would hire again.",
    "Very satisfied with the results. The handyman was knowledgeable and "
    "efficient. Fair pricing too.",
    "Good job overall. Work was completed as expected. Minor communication "
    "delays but nothing major.",
    "Professional service. Took time to explain what was being done and why. "
    "Appreciate the attention to detail.",
    "Solid work. Got the job done right. Would recommend to others looking "
    "for reliable help.",
    "Happy with the outcome. The work area was left clean and tidy. "
    "Reasonable pricing for quality work.",
    "Dependable and skilled. Showed up when promised and completed the work "
    "efficiently. Will call again for future projects.",
    "The work exceeded my expectations. Very impressed with the quality and "
    "professionalism shown throughout.",
    "Adequate work. Job was completed but took longer than estimated. "
    "Results are satisfactory.",
]

HANDYMAN_REVIEW_COMMENTS = [
    "Great homeowner to work with! Clear communication about what was needed "
    "and prompt payment. Would work for them again.",
    "Pleasant experience. The job was exactly as described and the homeowner "
    "was accommodating with scheduling.",
    "Good client. Provided access to work area and was available to answer "
    "questions. Fair and reasonable.",
    "Easy to work with. Clear expectations and appreciated the quality of "
    "work. Thank you for the opportunity.",
    "Professional homeowner who respects tradespeople. Provided all necessary "
    "information upfront.",
    "Nice home to work in. Homeowner was friendly and offered refreshments. "
    "Would definitely work here again.",
    "Straightforward job with a great client. Communication was excellent "
    "throughout the project.",
    "Homeowner was patient when unexpected issues arose. Appreciated their "
    "understanding and flexibility.",
    "Good experience overall. Job scope was clear and payment was prompt. "
    "Recommend this client.",
    "Decent job. Some scope changes during the project but we worked it out. "
    "Fair outcome for everyone.",
]

# =============================================================================
# IMAGE CONFIGURATION
# =============================================================================

# Colors for different shared images (RGB tuples)
JOB_IMAGE_COLORS = [
    ((46, 204, 113), "Job Photo 1"),  # Green
    ((52, 152, 219), "Job Photo 2"),  # Blue
    ((230, 126, 34), "Job Photo 3"),  # Orange
    ((231, 76, 60), "Job Photo 4"),  # Red
    ((155, 89, 182), "Job Photo 5"),  # Purple
]

VIDEO_THUMB_COLORS = [
    ((44, 62, 80), "Video 1"),  # Dark blue
    ((39, 174, 96), "Video 2"),  # Green
    ((192, 57, 43), "Video 3"),  # Dark red
]

WORK_PHOTO_COLORS = [
    ((41, 128, 185), "Work 1"),  # Blue
    ((22, 160, 133), "Work 2"),  # Teal
    ((142, 68, 173), "Work 3"),  # Purple
]

DOCUMENT_COLORS = [
    ((149, 165, 166), "Doc 1"),  # Gray
    ((127, 140, 141), "Doc 2"),  # Darker gray
]


class Command(BaseCommand):
    help = "Generate comprehensive dummy data for demo purposes"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.now = timezone.now()

    def handle(self, *args, **options):
        self.stdout.write("Checking seed data...")

        # Check and seed categories if needed
        category_count = JobCategory.objects.filter(is_active=True).count()
        if category_count == 0:
            self.stdout.write("  Seeding job categories...")
            call_command("seed_categories", verbosity=0)
            category_count = JobCategory.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(f"  JobCategory: {category_count} categories found")
        )

        # Check and seed cities if needed
        city_count = City.objects.filter(is_active=True).count()
        if city_count == 0:
            self.stdout.write("  Seeding cities...")
            call_command("seed_cities", verbosity=0)
            city_count = City.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"  City: {city_count} cities found"))

        # Create shared assets (upload once)
        self.stdout.write("\nCreating shared assets (one-time upload)...")
        shared_assets = self._create_shared_assets()

        self.stdout.write("\nGenerating dummy data...")

        # Get reference data
        categories = list(JobCategory.objects.filter(is_active=True))
        cities = list(City.objects.filter(is_active=True))

        # Generate all data
        with transaction.atomic():
            # Create users
            homeowners = self._create_homeowners(cities, shared_assets)
            self.stdout.write(
                self.style.SUCCESS(f"  Created {len(homeowners)} homeowners")
            )

            handymen = self._create_handymen(cities, shared_assets)
            self.stdout.write(self.style.SUCCESS(f"  Created {len(handymen)} handymen"))

            # Create jobs with attachments and tasks
            jobs, job_stats = self._create_jobs(
                homeowners, handymen, categories, cities, shared_assets
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created {len(jobs)} jobs "
                    f"({job_stats['open']} open, {job_stats['in_progress']} in_progress, "
                    f"{job_stats['completed']} completed, "
                    f"{job_stats['direct_offers']} direct offers)"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"    - {job_stats['attachments']} attachments, "
                    f"{job_stats['tasks']} tasks"
                )
            )

            # Create job applications for open jobs
            open_jobs = [j for j in jobs if j.status == "open"]
            app_stats = self._create_applications(
                open_jobs, handymen, shared_assets, categories
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created {app_stats['applications']} applications "
                    f"({app_stats['materials']} materials, "
                    f"{app_stats['attachments']} attachments)"
                )
            )

            # Create work sessions for in_progress/completed jobs
            active_jobs = [j for j in jobs if j.status in ("in_progress", "completed")]
            session_stats = self._create_work_sessions(active_jobs, shared_assets)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created {session_stats['sessions']} work sessions "
                    f"({session_stats['media']} media items)"
                )
            )

            # Create daily reports based on work sessions
            report_stats = self._create_daily_reports(active_jobs)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created {report_stats['reports']} daily reports "
                    f"({report_stats['tasks']} tasks worked)"
                )
            )

            # Create reviews for completed jobs
            completed_jobs = [j for j in jobs if j.status == "completed"]
            review_count = self._create_reviews(completed_jobs)
            self.stdout.write(self.style.SUCCESS(f"  Created {review_count} reviews"))

        # Print summary
        self._print_summary(
            homeowners,
            handymen,
            jobs,
            job_stats,
            app_stats,
            session_stats,
            report_stats,
            review_count,
        )

    # =========================================================================
    # SHARED ASSETS
    # =========================================================================

    def _create_shared_assets(self):
        """Create and upload all shared assets once for reuse."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.stdout.write(
                self.style.WARNING("  Pillow not installed, skipping images")
            )
            return {}

        from django.core.files.storage import default_storage

        shared = {}

        # Helper to create and upload an image
        def create_image(color, text, size, path):
            # Check if already exists
            if default_storage.exists(path):
                return path

            img = Image.new("RGB", size, color)
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            except OSError:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            x = (size[0] - (bbox[2] - bbox[0])) // 2
            y = (size[1] - (bbox[3] - bbox[1])) // 2
            draw.text((x, y), text, fill=(255, 255, 255), font=font)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=85)
            return default_storage.save(path, ContentFile(img_bytes.getvalue()))

        # Helper to create video thumbnail with play button
        def create_video_thumb(color, text, path):
            if default_storage.exists(path):
                return path

            size = (800, 600)
            img = Image.new("RGB", size, color)
            draw = ImageDraw.Draw(img)

            # Draw play button triangle
            center_x, center_y = size[0] // 2, size[1] // 2
            triangle_size = 60
            points = [
                (center_x - triangle_size // 2, center_y - triangle_size),
                (center_x - triangle_size // 2, center_y + triangle_size),
                (center_x + triangle_size, center_y),
            ]
            draw.polygon(points, fill=(255, 255, 255, 200))

            # Draw circle around play button
            draw.ellipse(
                [
                    center_x - triangle_size - 20,
                    center_y - triangle_size - 20,
                    center_x + triangle_size + 20,
                    center_y + triangle_size + 20,
                ],
                outline=(255, 255, 255),
                width=3,
            )

            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except OSError:
                font = ImageFont.load_default()
            draw.text((20, size[1] - 50), text, fill=(255, 255, 255), font=font)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=85)
            return default_storage.save(path, ContentFile(img_bytes.getvalue()))

        # 1. Create avatar
        shared["avatar"] = create_image(
            (52, 152, 219), "U", (200, 200), "dummy/shared_avatar.jpg"
        )
        self.stdout.write(f"  Avatar: {shared['avatar']}")

        # 2. Create job images (5 different colors)
        shared["job_images"] = []
        for i, (color, text) in enumerate(JOB_IMAGE_COLORS, 1):
            path = create_image(color, text, (800, 600), f"dummy/shared_job_{i}.jpg")
            shared["job_images"].append(path)
        self.stdout.write(f"  Job images: {len(shared['job_images'])} created")

        # 3. Create video thumbnails
        shared["video_thumbs"] = []
        for i, (color, text) in enumerate(VIDEO_THUMB_COLORS, 1):
            path = create_video_thumb(color, text, f"dummy/shared_video_{i}.jpg")
            shared["video_thumbs"].append(path)
        self.stdout.write(f"  Video thumbnails: {len(shared['video_thumbs'])} created")

        # 4. Create work photos
        shared["work_photos"] = []
        for i, (color, text) in enumerate(WORK_PHOTO_COLORS, 1):
            path = create_image(color, text, (800, 600), f"dummy/shared_work_{i}.jpg")
            shared["work_photos"].append(path)
        self.stdout.write(f"  Work photos: {len(shared['work_photos'])} created")

        # 5. Create document placeholders
        shared["documents"] = []
        for i, (color, text) in enumerate(DOCUMENT_COLORS, 1):
            path = create_image(color, text, (400, 300), f"dummy/shared_doc_{i}.jpg")
            shared["documents"].append(path)
        self.stdout.write(f"  Documents: {len(shared['documents'])} created")

        return shared

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _weighted_choice(self, weights_dict):
        """Select a key from dict based on weights."""
        choices = list(weights_dict.keys())
        weights = list(weights_dict.values())
        return random.choices(choices, weights=weights, k=1)[0]

    def _generate_name(self):
        return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

    def _generate_phone(self):
        area_code = random.choice(AREA_CODES)
        number = "".join([str(random.randint(0, 9)) for _ in range(7)])
        return f"+1{area_code}{number}"

    def _generate_address(self, city):
        street_num = random.randint(1, 9999)
        street = random.choice(STREET_NAMES)
        return f"{street_num} {street}, {city.name}, {city.province_code}"

    def _generate_postal_code(self, province_code):
        prefixes = POSTAL_PREFIXES.get(province_code, ["M"])
        prefix = random.choice(prefixes)
        return (
            f"{prefix}{random.randint(0, 9)}{chr(random.randint(65, 90))} "
            f"{random.randint(0, 9)}{chr(random.randint(65, 90))}{random.randint(0, 9)}"
        )

    def _vary_coordinates(self, lat, lng, variation=0.05):
        if lat is None or lng is None:
            return None, None
        new_lat = float(lat) + random.uniform(-variation, variation)
        new_lng = float(lng) + random.uniform(-variation, variation)
        return Decimal(str(round(new_lat, 6))), Decimal(str(round(new_lng, 6)))

    # =========================================================================
    # USER CREATION
    # =========================================================================

    def _create_homeowners(self, cities, shared_assets):
        """Create homeowner users with profiles."""
        homeowners = []
        avatar_path = shared_assets.get("avatar", "")

        for i in range(1, NUM_HOMEOWNERS + 1):
            email = f"dummy_homeowner_{i:03d}@example.com"

            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                homeowners.append(user)
                continue

            city = random.choice(cities)
            name = self._generate_name()

            user = User.objects.create_user(
                email=email,
                password=DUMMY_PASSWORD,
                is_dummy=True,
                email_verified_at=self.now,
            )

            UserRole.objects.create(user=user, role="homeowner", next_action="none")

            HomeownerProfile.objects.create(
                user=user,
                display_name=name,
                avatar=avatar_path,
                phone_number=self._generate_phone(),
                phone_verified_at=self.now,
                address=self._generate_address(city),
            )

            homeowners.append(user)

        return homeowners

    def _create_handymen(self, cities, shared_assets):
        """Create handyman users with profiles."""
        handymen = []
        avatar_path = shared_assets.get("avatar", "")

        for i in range(1, NUM_HANDYMEN + 1):
            email = f"dummy_handyman_{i:03d}@example.com"

            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                handymen.append(user)
                continue

            city = random.choice(cities)
            name = self._generate_name()
            lat, lng = self._vary_coordinates(city.latitude, city.longitude, 0.1)

            user = User.objects.create_user(
                email=email,
                password=DUMMY_PASSWORD,
                is_dummy=True,
                email_verified_at=self.now,
            )

            UserRole.objects.create(user=user, role="handyman", next_action="none")

            HandymanProfile.objects.create(
                user=user,
                display_name=name,
                avatar=avatar_path,
                rating=Decimal(str(round(random.uniform(3.5, 5.0), 2))),
                hourly_rate=Decimal(str(random.randint(25, 150))),
                latitude=lat,
                longitude=lng,
                is_active=True,
                is_available=True,
                is_approved=True,
                phone_number=self._generate_phone(),
                phone_verified_at=self.now,
                address=self._generate_address(city),
            )

            handymen.append(user)

        return handymen

    # =========================================================================
    # JOB CREATION
    # =========================================================================

    def _create_jobs(self, homeowners, handymen, categories, cities, shared_assets):
        """Create jobs with varied attachments and tasks."""
        jobs = []
        stats = {
            "open": 0,
            "in_progress": 0,
            "completed": 0,
            "direct_offers": 0,
            "attachments": 0,
            "tasks": 0,
        }

        for _i in range(NUM_JOBS):
            homeowner = random.choice(homeowners)
            category = random.choice(categories)
            city = random.choice(cities)
            status = self._weighted_choice(STATUS_WEIGHTS)

            # Get job data for this category
            category_slug = category.slug
            job_data = JOB_DATA_BY_CATEGORY.get(
                category_slug, JOB_DATA_BY_CATEGORY["plumbing"]
            )

            title = random.choice(job_data["titles"])
            description = random.choice(job_data["descriptions"])
            lat, lng = self._vary_coordinates(city.latitude, city.longitude)

            # Determine if direct offer
            is_direct_offer = random.randint(1, 100) <= DIRECT_OFFER_PERCENT
            target_handyman = None
            offer_status = None
            offer_expires_at = None

            if is_direct_offer:
                target_handyman = random.choice(handymen)
                offer_status = random.choice(["pending", "accepted", "rejected"])
                offer_expires_at = self.now + timedelta(days=random.randint(1, 7))
                stats["direct_offers"] += 1

            # Assign handyman for in_progress/completed jobs
            assigned_handyman = None
            completed_at = None
            if status in ("in_progress", "completed"):
                if is_direct_offer and offer_status == "accepted":
                    assigned_handyman = target_handyman
                else:
                    assigned_handyman = random.choice(handymen)

                if status == "completed":
                    completed_at = self.now - timedelta(days=random.randint(1, 30))

            job = Job(
                homeowner=homeowner,
                title=title,
                description=description,
                estimated_budget=Decimal(str(random.randint(50, 5000))),
                category=category,
                city=city,
                address=self._generate_address(city),
                postal_code=self._generate_postal_code(city.province_code),
                latitude=lat,
                longitude=lng,
                status=status,
                status_at=self.now,
                is_dummy=True,
                is_direct_offer=is_direct_offer,
                target_handyman=target_handyman,
                offer_status=offer_status,
                offer_expires_at=offer_expires_at,
                assigned_handyman=assigned_handyman,
                completed_at=completed_at,
            )
            job.save()

            # Create job tasks
            task_titles = job_data.get(
                "tasks", JOB_DATA_BY_CATEGORY["plumbing"]["tasks"]
            )
            num_tasks = random.randint(2, min(5, len(task_titles)))
            selected_tasks = random.sample(task_titles, num_tasks)

            for idx, task_title in enumerate(selected_tasks):
                is_completed = status == "completed" or (
                    status == "in_progress" and random.random() < 0.3
                )
                JobTask.objects.create(
                    job=job,
                    title=task_title,
                    order=idx,
                    is_completed=is_completed,
                    completed_at=self.now if is_completed else None,
                    completed_by=assigned_handyman if is_completed else None,
                )
                stats["tasks"] += 1

            # Create job attachments (0-5) - only if shared assets exist
            job_images = shared_assets.get("job_images", [])
            video_thumbs = shared_assets.get("video_thumbs", [])

            if job_images or video_thumbs:
                num_attachments = self._weighted_choice(ATTACHMENT_WEIGHTS)
                for order in range(num_attachments):
                    # 80% image, 20% video (fallback to available type)
                    use_image = random.random() < 0.8
                    if use_image and job_images:
                        file_path = random.choice(job_images)
                        file_type = "image"
                        duration = None
                    elif video_thumbs:
                        file_path = random.choice(video_thumbs)
                        file_type = "video"
                        duration = random.randint(10, 180)
                    else:
                        # Fallback: use_image was False but no video_thumbs, use job_images
                        file_path = random.choice(job_images)
                        file_type = "image"
                        duration = None

                    JobAttachment.objects.create(
                        job=job,
                        file=file_path,
                        file_type=file_type,
                        file_name=file_path.split("/")[-1],
                        file_size=random.randint(50000, 500000),
                        order=order,
                        duration_seconds=duration,
                    )
                    stats["attachments"] += 1

            jobs.append(job)
            stats[status] += 1

        return jobs, stats

    # =========================================================================
    # JOB APPLICATIONS
    # =========================================================================

    def _create_applications(self, open_jobs, handymen, shared_assets, categories):
        """Create job applications for open jobs."""
        stats = {"applications": 0, "materials": 0, "attachments": 0}

        for job in open_jobs:
            num_apps = random.randint(MIN_APPLICATIONS, MAX_APPLICATIONS)
            applicants = random.sample(handymen, min(num_apps, len(handymen)))

            for handyman in applicants:
                # Skip if handyman is target of direct offer
                if job.is_direct_offer and job.target_handyman == handyman:
                    continue

                try:
                    hourly_rate = handyman.handyman_profile.hourly_rate
                    if hourly_rate is None:
                        hourly_rate = Decimal("50.00")
                    elif not isinstance(hourly_rate, Decimal):
                        hourly_rate = Decimal(str(hourly_rate))
                except HandymanProfile.DoesNotExist:
                    hourly_rate = Decimal("50.00")

                hours = Decimal(str(random.randint(2, 40)))
                labor_cost = hourly_rate * hours
                material_cost = Decimal(str(random.randint(0, 500)))

                app = JobApplication.objects.create(
                    job=job,
                    handyman=handyman,
                    status=random.choices(
                        ["pending", "rejected", "withdrawn"], weights=[70, 20, 10], k=1
                    )[0],
                    status_at=self.now,
                    predicted_hours=hours,
                    estimated_total_price=labor_cost + material_cost,
                    negotiation_reasoning=random.choice(NEGOTIATION_REASONS),
                )
                stats["applications"] += 1

                # Add materials (0-4)
                category_slug = job.category.slug
                materials_list = MATERIALS_CATALOG.get(
                    category_slug, MATERIALS_CATALOG["plumbing"]
                )
                num_materials = random.randint(0, min(4, len(materials_list)))
                selected_materials = random.sample(materials_list, num_materials)

                for mat in selected_materials:
                    JobApplicationMaterial.objects.create(
                        application=app,
                        name=mat["name"],
                        price=Decimal(str(mat["price"])),
                        description=mat["description"],
                    )
                    stats["materials"] += 1

                # Add attachments (0-2) - only if shared assets exist
                documents = shared_assets.get("documents", [])
                job_images = shared_assets.get("job_images", [])

                if documents or job_images:
                    num_app_attachments = random.randint(0, 2)
                    for _ in range(num_app_attachments):
                        # 60% document, 40% image (fallback to available type)
                        use_document = random.random() < 0.6
                        if use_document and documents:
                            file_path = random.choice(documents)
                            file_type = "document"
                        elif job_images:
                            file_path = random.choice(job_images)
                            file_type = "image"
                        else:
                            # Fallback: use_document was False but no job_images, use documents
                            file_path = random.choice(documents)
                            file_type = "document"

                        JobApplicationAttachment.objects.create(
                            application=app,
                            file=file_path,
                            file_type=file_type,
                            file_name=file_path.split("/")[-1],
                            file_size=random.randint(10000, 200000),
                        )
                        stats["attachments"] += 1

        return stats

    # =========================================================================
    # WORK SESSIONS
    # =========================================================================

    def _create_work_sessions(self, active_jobs, shared_assets):
        """Create work sessions for in_progress and completed jobs."""
        stats = {"sessions": 0, "media": 0}

        work_photos = shared_assets.get("work_photos", [])
        video_thumbs = shared_assets.get("video_thumbs", [])

        # Skip creating work sessions if no photos available (required field)
        if not work_photos:
            return stats

        for job in active_jobs:
            if not job.assigned_handyman:
                continue

            num_sessions = random.randint(MIN_WORK_SESSIONS, MAX_WORK_SESSIONS)
            base_date = job.created_at + timedelta(days=1)

            for i in range(num_sessions):
                session_date = base_date + timedelta(days=i)
                start_hour = random.randint(8, 14)
                duration_hours = random.randint(1, 8)

                started_at = session_date.replace(
                    hour=start_hour, minute=0, second=0, microsecond=0
                )
                ended_at = started_at + timedelta(hours=duration_hours)

                # Vary location slightly from job location
                start_lat, start_lng = self._vary_coordinates(
                    job.latitude, job.longitude, 0.001
                )
                end_lat, end_lng = self._vary_coordinates(
                    job.latitude, job.longitude, 0.001
                )

                start_photo = random.choice(work_photos)
                end_photo = random.choice(work_photos)

                session = WorkSession.objects.create(
                    job=job,
                    handyman=job.assigned_handyman,
                    started_at=started_at,
                    ended_at=ended_at,
                    start_latitude=start_lat or Decimal("43.6532"),
                    start_longitude=start_lng or Decimal("-79.3832"),
                    start_accuracy=random.uniform(5.0, 20.0),
                    start_photo=start_photo,
                    end_latitude=end_lat or Decimal("43.6532"),
                    end_longitude=end_lng or Decimal("-79.3832"),
                    end_accuracy=random.uniform(5.0, 20.0),
                    end_photo=end_photo,
                    status="completed",
                )
                stats["sessions"] += 1

                # Add session media (0-3) - work_photos is guaranteed non-empty at this point
                num_media = random.randint(MIN_SESSION_MEDIA, MAX_SESSION_MEDIA)
                for _ in range(num_media):
                    # 70% photo, 30% video (fallback to available type)
                    use_photo = random.random() < 0.7
                    if use_photo and work_photos:
                        file_path = random.choice(work_photos)
                        media_type = "photo"
                        duration = None
                    elif video_thumbs:
                        file_path = random.choice(video_thumbs)
                        media_type = "video"
                        duration = random.randint(5, 60)
                    else:
                        # Fallback: use_photo was False but no video_thumbs, use work_photos
                        file_path = random.choice(work_photos)
                        media_type = "photo"
                        duration = None

                    WorkSessionMedia.objects.create(
                        work_session=session,
                        media_type=media_type,
                        file=file_path,
                        description=f"Work progress {media_type}",
                        file_size=random.randint(50000, 500000),
                        duration_seconds=duration,
                    )
                    stats["media"] += 1

        return stats

    # =========================================================================
    # DAILY REPORTS
    # =========================================================================

    def _create_daily_reports(self, active_jobs):
        """Create daily reports based on work sessions."""
        stats = {"reports": 0, "tasks": 0}

        for job in active_jobs:
            if not job.assigned_handyman:
                continue

            # Get work sessions for this job
            sessions = WorkSession.objects.filter(job=job).order_by("started_at")
            if not sessions.exists():
                continue

            # Group sessions by date
            sessions_by_date = {}
            for session in sessions:
                date = session.started_at.date()
                if date not in sessions_by_date:
                    sessions_by_date[date] = []
                sessions_by_date[date].append(session)

            # Create one report per date
            for report_date, date_sessions in sessions_by_date.items():
                # Calculate total duration for the day
                total_duration = timedelta()
                for session in date_sessions:
                    if session.ended_at and session.started_at:
                        total_duration += session.ended_at - session.started_at

                # Skip if no duration
                if total_duration.total_seconds() == 0:
                    total_duration = timedelta(hours=random.randint(1, 8))

                status = self._weighted_choice(REPORT_STATUS_WEIGHTS)
                reviewed_at = None
                reviewed_by = None

                if status in ("approved", "rejected"):
                    reviewed_at = self.now
                    reviewed_by = job.homeowner

                report = DailyReport.objects.create(
                    job=job,
                    handyman=job.assigned_handyman,
                    report_date=report_date,
                    summary=random.choice(REPORT_SUMMARIES),
                    total_work_duration=total_duration,
                    status=status,
                    homeowner_comment=(
                        "Looks good!"
                        if status == "approved"
                        else ("Need more details" if status == "rejected" else "")
                    ),
                    reviewed_at=reviewed_at,
                    reviewed_by=reviewed_by,
                    review_deadline=self.now + timedelta(days=3),
                )
                stats["reports"] += 1

                # Link tasks worked on (2-4 tasks)
                job_tasks = list(job.tasks.all())
                if job_tasks:
                    num_tasks = random.randint(2, min(4, len(job_tasks)))
                    selected_tasks = random.sample(job_tasks, num_tasks)

                    for task in selected_tasks:
                        DailyReportTask.objects.create(
                            daily_report=report,
                            task=task,
                            notes=f"Worked on: {task.title}",
                            marked_complete=task.is_completed,
                        )
                        stats["tasks"] += 1

        return stats

    # =========================================================================
    # REVIEWS
    # =========================================================================

    def _create_reviews(self, completed_jobs):
        """Create mutual reviews for completed jobs."""
        review_count = 0

        for job in completed_jobs:
            if not job.assigned_handyman:
                continue

            # Check if reviews already exist
            existing_reviews = Review.objects.filter(job=job)
            if existing_reviews.exists():
                continue

            # Homeowner reviews handyman
            Review.objects.create(
                job=job,
                reviewer=job.homeowner,
                reviewee=job.assigned_handyman,
                reviewer_type="homeowner",
                rating=self._weighted_choice(RATING_WEIGHTS),
                comment=random.choice(HOMEOWNER_REVIEW_COMMENTS),
            )
            review_count += 1

            # Handyman reviews homeowner
            Review.objects.create(
                job=job,
                reviewer=job.assigned_handyman,
                reviewee=job.homeowner,
                reviewer_type="handyman",
                rating=self._weighted_choice(RATING_WEIGHTS),
                comment=random.choice(HANDYMAN_REVIEW_COMMENTS),
            )
            review_count += 1

        return review_count

    # =========================================================================
    # SUMMARY
    # =========================================================================

    def _print_summary(
        self,
        homeowners,
        handymen,
        jobs,
        job_stats,
        app_stats,
        session_stats,
        report_stats,
        review_count,
    ):
        """Print generation summary."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("GENERATION SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write("\nUsers:")
        self.stdout.write(f"  - Homeowners: {len(homeowners)}")
        self.stdout.write(f"  - Handymen: {len(handymen)}")
        self.stdout.write(f"\nJobs: {len(jobs)}")
        self.stdout.write(f"  - Open: {job_stats['open']}")
        self.stdout.write(f"  - In Progress: {job_stats['in_progress']}")
        self.stdout.write(f"  - Completed: {job_stats['completed']}")
        self.stdout.write(f"  - Direct Offers: {job_stats['direct_offers']}")
        self.stdout.write(f"  - Attachments: {job_stats['attachments']}")
        self.stdout.write(f"  - Tasks: {job_stats['tasks']}")
        self.stdout.write(f"\nApplications: {app_stats['applications']}")
        self.stdout.write(f"  - Materials: {app_stats['materials']}")
        self.stdout.write(f"  - Attachments: {app_stats['attachments']}")
        self.stdout.write(f"\nWork Sessions: {session_stats['sessions']}")
        self.stdout.write(f"  - Media Items: {session_stats['media']}")
        self.stdout.write(f"\nDaily Reports: {report_stats['reports']}")
        self.stdout.write(f"  - Tasks Worked: {report_stats['tasks']}")
        self.stdout.write(f"\nReviews: {review_count}")
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Done! All dummy data has is_dummy=True."))
        self.stdout.write("=" * 60 + "\n")
