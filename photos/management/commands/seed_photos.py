import random
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction

from photos.models import Photo

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


class Command(BaseCommand):
    help = "Seed Photo table with fake test data (default: 3000)."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=3000, help="How many photos to generate")
        parser.add_argument("--flush", action="store_true", help="Delete all existing Photo rows before seeding")

    @transaction.atomic
    def handle(self, *args, **options):
        count = int(options["count"])
        flush = bool(options["flush"])

        # 1. 基础数据定义 (20 items)
        models = [
            "Boeing 737-800", "ARJ21-700", "Boeing 747-8", "Airbus A380-800",
            "Boeing 777-300ER", "Airbus A321XLR", "Embraer E190-E2", "Bombardier CRJ900",
            "Airbus A350-900", "Boeing 787-9", "Comac C919", "Boeing 737 MAX 9",
            "Airbus A320neo", "Boeing 767-300ER", "Airbus A330-900neo", "Boeing 757-200",
            "McDonnell Douglas MD-11", "Lockheed L-1011 TriStar", "Concorde", "Antonov An-225"
        ]

        sub_model_map = {
            "Boeing 737-800": ["B737-8AS", "B737-8H6", "B737-8Z9"],
            "ARJ21-700": ["ARJ21-700STD"],
            "Boeing 747-8": ["B747-89L"],
            "Airbus A380-800": ["A380-841", "A380-861", "A380-842"],
            "Boeing 777-300ER": ["B777-36NER", "B777-3H6ER", "B777-3D7ER", "B777-3B5ER"],
            "Airbus A321XLR": ["A321-253NY", "A321-271NX", "A321-271N"],
            "Embraer E190-E2": ["ERJ-190-300 STD"],
            "Bombardier CRJ900": ["CL-600-2D24"],
            "Airbus A350-900": ["A350-941", "A350-941ULR"],
            "Boeing 787-9": ["B787-9 Dreamliner"],
            "Comac C919": ["C919-100"],
            "Boeing 737 MAX 9": ["B737-MAX9"],
            "Airbus A320neo": ["A320-271N"],
            "Boeing 767-300ER": ["B767-336ER"],
            "Airbus A330-900neo": ["A330-941"],
            "Boeing 757-200": ["B757-223"],
            "McDonnell Douglas MD-11": ["MD-11F"],
            "Lockheed L-1011 TriStar": ["L-1011-500"],
            "Concorde": ["Concorde-British"],
            "Antonov An-225": ["An-225 Mriya"]
        }

        remarks_pool = [
            "Stunning landing during golden hour on runway {rwy}.",
            "Taxing to gate {gate} after a long-haul flight.",
            "Special livery detail captured at {airport}.",
            "Beautiful rotation shot with clear blue sky.",
            "Heavy aircraft rotating from runway {rwy} for departure.",
            "Rare visitor at {airport} today.",
            "Maintenance check completed, ready for the next flight."
        ]

        # (60 items)
        airlines = [
            "Qatar Airways", "Singapore Airlines", "ANA All Nippon Airways", "Emirates",
            "Japan Airlines", "Turkish Airlines", "Air France", "Korean Air",
            "Swiss International Air Lines", "British Airways", "Lufthansa", "Cathay Pacific",
            "China Southern Airlines", "China Eastern Airlines", "Air China", "Hainan Airlines",
            "EVA Air", "Virgin Atlantic", "Qantas Airways", "Asiana Airlines",
            "Delta Air Lines", "American Airlines", "United Airlines", "KLM Royal Dutch Airlines",
            "Garuda Indonesia", "Thai Airways", "Malaysia Airlines", "Aeroflot",
            "Iberia", "Austrian Airlines", "Fiji Airways", "Alaska Airlines",
            "Etihad Airways", "Saudi Arabian Airlines", "Vietnam Airlines", "IndiGo",
            "WestJet", "JetBlue Airways", "Air New Zealand", "LATAM Airlines",
            "South African Airways", "Philippine Airlines", "Air India", "Scoot",
            "Vistara", "Finnair", "Brussels Airlines", "TAP Air Portugal",
            "Cebu Pacific", "AirAsia", "Ryanair", "easyJet",
            "Norwegian Air Shuttle", "Wizz Air", "Spirit Airlines", "Frontier Airlines",
            "Jetstar Airways", "Peach Aviation", "Volaris", "Azul Brazilian Airlines"
        ]

        # (50 items)
        airports = [
            "ATL", "PEK", "LAX", "DXB", "HND", "ORD", "LHR", "PVG", "CDG", "DFW",
            "CAN", "AMS", "FRA", "IST", "JFK", "SIN", "ICN", "DEN", "BKK", "SFO",
            "KUL", "MAD", "LAS", "SEA", "MIA", "MUC", "CLT", "PHX", "IAH", "SYD",
            "MEL", "GRU", "YYZ", "DEL", "BCN", "DOH", "EWR", "MSP", "FCO", "DME",
            "SVO", "ZRH", "VIE", "OSL", "ARN", "HEL", "BRU", "CPT", "JNB", "GIG"
        ]

        camera_ids = ["C1", "C2"]
        lens_ids = ["L1", "L2", "L3"]

        if flush:
            deleted, _ = Photo.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Flushed Photo table: deleted {deleted} rows."))

        objs = []
        iterator = range(1, count + 1)
        if tqdm is not None:
            iterator = tqdm(iterator, desc="Generating data")

        for i in iterator:
            # Models: 20 items, 20 weights
            model = random.choices(models, weights=[
                15, 8, 5, 3, 10, 7, 6, 4, 9, 10,
                5, 6, 8, 7, 6, 5, 2, 1, 1, 1
            ], k=1)[0]

            # Airlines: 60 items, 60 weights
            airline = random.choices(
                airlines,
                weights=[
                    5, 5, 4, 5, 4, 4, 3, 3, 3, 3,
                    3, 4, 4, 4, 4, 3, 3, 2, 2, 2,
                    3, 3, 3, 2, 2, 2, 2, 2, 2, 1,
                    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                    1, 1, 1, 1, 1, 1, 1, 1, 1, 1
                ],
                k=1
            )[0]

            # Airports: 50 items, 50 weights
            airport = random.choices(airports, weights=[
                10, 8, 9, 7, 8, 9, 8, 7, 6, 7,
                6, 6, 5, 5, 6, 5, 5, 4, 4, 4,
                3, 3, 3, 3, 2, 2, 2, 2, 2, 1,
                1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                1, 1, 1, 1, 1, 1, 1, 1, 1, 1
            ], k=1)[0]

            # 修正 sub_model 选择逻辑，从列表中随机选一个
            sub_model_options = sub_model_map.get(model, ["Standard"])
            sub_model = random.choice(sub_model_options)

            remark = random.choice(remarks_pool).format(
                rwy=random.choice(["02L", "02R", "20L", "20R", "15", "33"]),
                gate=random.randint(1, 150),
                airport=airport
            )

            year = random.randint(1998, 2026)
            month = random.randint(1, 12)
            if month in {1, 3, 5, 7, 8, 10, 12}:
                day = random.randint(1, 31)
            elif month in {4, 6, 9, 11}:
                day = random.randint(1, 30)
            else:
                day = random.randint(1, 28)

            featured = random.choice([True] + [False] * 9)

            objs.append(Photo(
                reg=f"B-{random.randint(1000, 9999)}",
                model=model,
                sub_model=sub_model,
                remarks=remark,
                airline=airline,
                airport=airport,
                camera_id=random.choice(camera_ids),
                lens_id=random.choice(lens_ids),
                src=f"https://picsum.photos/seed/{i}/800/533",
                date=date(year, month, day),
                featured=featured,
            ))

        Photo.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"Seeded {count} Photo rows successfully."))