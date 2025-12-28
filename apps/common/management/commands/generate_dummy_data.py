"""
Management command to generate dummy data for demo purposes.

Usage:
    python manage.py generate_dummy_data

This will create:
    - 100 homeowner users with profiles
    - 100 handyman users with profiles
    - 500 jobs distributed across homeowners

All generated data will have is_dummy=True for easy cleanup.
Images are shared across records to speed up generation.
"""

import io
import random
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobCategory, JobImage, JobTask
from apps.profiles.models import HandymanProfile, HomeownerProfile

# Configuration
NUM_HOMEOWNERS = 100
NUM_HANDYMEN = 100
NUM_JOBS = 500
DUMMY_PASSWORD = "SolutionBank123#"

# Canadian first names
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

# Canadian last names
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

# Canadian area codes
AREA_CODES = ["416", "647", "437", "905", "289", "365", "604", "778", "403"]

# Street names
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
]

# Job titles and descriptions by category
JOB_DATA_BY_CATEGORY = {
    "plumbing": {
        "titles": [
            "Fix leaky faucet",
            "Unclog drain",
            "Replace toilet",
            "Install sink",
        ],
        "descriptions": ["Need a professional plumber to fix the issue."],
    },
    "electrical": {
        "titles": ["Install ceiling fan", "Replace switches", "Fix flickering lights"],
        "descriptions": ["Need a licensed electrician for this work."],
    },
    "carpentry": {
        "titles": ["Build shelving", "Repair deck", "Install door", "Fix floors"],
        "descriptions": ["Looking for a skilled carpenter."],
    },
    "cleaning": {
        "titles": ["Deep clean house", "Move-out cleaning", "Carpet cleaning"],
        "descriptions": ["Need thorough cleaning service."],
    },
    "painting": {
        "titles": ["Paint living room", "Exterior painting", "Paint cabinets"],
        "descriptions": ["Looking for experienced painters."],
    },
    "landscaping": {
        "titles": ["Lawn mowing", "Tree trimming", "Garden installation"],
        "descriptions": ["Need lawn maintenance service."],
    },
    "hvac": {
        "titles": ["AC repair", "Furnace maintenance", "Install thermostat"],
        "descriptions": ["Need HVAC technician."],
    },
    "roofing": {
        "titles": ["Repair roof leak", "Replace shingles", "Gutter repair"],
        "descriptions": ["Need experienced roofer."],
    },
    "flooring": {
        "titles": ["Install hardwood", "Replace carpet", "Tile installation"],
        "descriptions": ["Need flooring installer."],
    },
    "appliance-repair": {
        "titles": ["Fix washing machine", "Repair refrigerator", "Dryer repair"],
        "descriptions": ["Need appliance repair technician."],
    },
}

# Job items
JOB_ITEMS = [
    "Inspect the issue",
    "Provide estimate",
    "Complete the work",
    "Clean up area",
    "Test and verify",
]

# Canadian postal code prefixes by province
POSTAL_PREFIXES = {
    "ON": ["M", "N", "K", "L"],
    "BC": ["V"],
    "AB": ["T"],
    "QC": ["H", "J"],
    "MB": ["R"],
    "NS": ["B"],
}


class Command(BaseCommand):
    help = "Generate dummy data for demo purposes"

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

        # Create shared images (upload once)
        self.stdout.write("\nCreating shared images (one-time upload)...")
        shared_images = self._create_and_upload_shared_images()

        self.stdout.write("\nGenerating dummy data...")

        # Get reference data
        categories = list(JobCategory.objects.filter(is_active=True))
        cities = list(City.objects.filter(is_active=True))

        # Generate users and jobs
        with transaction.atomic():
            homeowners = self._create_homeowners(cities, shared_images)
            self.stdout.write(
                self.style.SUCCESS(f"  Created {len(homeowners)} homeowners")
            )

            handymen = self._create_handymen(cities, shared_images)
            self.stdout.write(self.style.SUCCESS(f"  Created {len(handymen)} handymen"))

            jobs, status_counts = self._create_jobs(
                homeowners, categories, cities, shared_images
            )
            self.stdout.write(self.style.SUCCESS(f"  Created {len(jobs)} jobs"))

        # Print summary
        self.stdout.write("\n" + self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  - Homeowners: {len(homeowners)}")
        self.stdout.write(f"  - Handymen: {len(handymen)}")
        self.stdout.write(
            f"  - Jobs: {len(jobs)} "
            f"({status_counts['open']} open, "
            f"{status_counts['in_progress']} in_progress, "
            f"{status_counts['completed']} completed)"
        )
        self.stdout.write(
            "\n" + self.style.SUCCESS("Done! All dummy data has is_dummy=True.")
        )

    def _create_and_upload_shared_images(self):
        """Create and upload shared images once, return their paths."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.stdout.write(
                self.style.WARNING("  Pillow not installed, skipping images")
            )
            return {}

        shared = {}

        # Create ONE avatar image and upload it
        img = Image.new("RGB", (200, 200), (52, 152, 219))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        except OSError:
            font = ImageFont.load_default()
        text = "U"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (200 - (bbox[2] - bbox[0])) // 2
        y = (200 - (bbox[3] - bbox[1])) // 2 - 10
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)

        # Upload once and store path
        from django.core.files.storage import default_storage

        avatar_path = default_storage.save(
            "dummy/shared_avatar.jpg", ContentFile(img_bytes.getvalue())
        )
        shared["avatar_path"] = avatar_path
        self.stdout.write(
            self.style.SUCCESS(f"  Uploaded shared avatar: {avatar_path}")
        )

        # Create ONE job image and upload it
        img = Image.new("RGB", (800, 600), (46, 204, 113))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except OSError:
            font = ImageFont.load_default()
        text = "Job Image"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (800 - (bbox[2] - bbox[0])) // 2
        y = (600 - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)

        job_path = default_storage.save(
            "dummy/shared_job_image.jpg", ContentFile(img_bytes.getvalue())
        )
        shared["job_image_path"] = job_path
        self.stdout.write(
            self.style.SUCCESS(f"  Uploaded shared job image: {job_path}")
        )

        return shared

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

    def _create_homeowners(self, cities, shared_images):
        """Create homeowner users with profiles (no individual uploads)."""
        now = timezone.now()
        homeowners = []
        avatar_path = shared_images.get("avatar_path", "")

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
                email_verified_at=now,
            )

            UserRole.objects.create(user=user, role="homeowner", next_action="none")

            # Use shared avatar path directly (no upload)
            HomeownerProfile.objects.create(
                user=user,
                display_name=name,
                avatar=avatar_path,
                phone_number=self._generate_phone(),
                phone_verified_at=now,
                address=self._generate_address(city),
            )

            homeowners.append(user)

        return homeowners

    def _create_handymen(self, cities, shared_images):
        """Create handyman users with profiles (no individual uploads)."""
        now = timezone.now()
        handymen = []
        avatar_path = shared_images.get("avatar_path", "")

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
                email_verified_at=now,
            )

            UserRole.objects.create(user=user, role="handyman", next_action="none")

            # Use shared avatar path directly (no upload)
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
                phone_verified_at=now,
                address=self._generate_address(city),
            )

            handymen.append(user)

        return handymen

    def _create_jobs(self, homeowners, categories, cities, shared_images):
        """Create jobs (no individual image uploads)."""
        now = timezone.now()
        jobs = []
        status_counts = {"open": 0, "in_progress": 0, "completed": 0}
        job_image_path = shared_images.get("job_image_path", "")

        statuses = ["open"] * 60 + ["in_progress"] * 25 + ["completed"] * 15

        for _i in range(NUM_JOBS):
            homeowner = random.choice(homeowners)
            category = random.choice(categories)
            city = random.choice(cities)
            status = random.choice(statuses)

            category_slug = category.slug
            job_data = JOB_DATA_BY_CATEGORY.get(
                category_slug, JOB_DATA_BY_CATEGORY["plumbing"]
            )

            title = random.choice(job_data["titles"])
            description = random.choice(job_data["descriptions"])
            lat, lng = self._vary_coordinates(city.latitude, city.longitude)

            num_items = random.randint(2, 4)
            task_titles = random.sample(JOB_ITEMS, min(num_items, len(JOB_ITEMS)))

            job = Job(
                homeowner=homeowner,
                title=title,
                description=description,
                estimated_budget=Decimal(str(random.randint(50, 2000))),
                category=category,
                city=city,
                address=self._generate_address(city),
                postal_code=self._generate_postal_code(city.province_code),
                latitude=lat,
                longitude=lng,
                status=status,
                status_at=now,
                is_dummy=True,
            )
            job.save()

            # Create job tasks
            for idx, task_title in enumerate(task_titles):
                JobTask.objects.create(job=job, title=task_title, order=idx)

            # Use shared job image path directly (no upload)
            if job_image_path:
                JobImage.objects.create(job=job, image=job_image_path, order=0)

            jobs.append(job)
            status_counts[status] += 1

        return jobs, status_counts
