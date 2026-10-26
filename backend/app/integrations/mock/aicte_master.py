"""Mock implementation of AicteMasterClient.

SPEC.md section 18:
MockAicteMasterClient: 30 fake colleges across 8 states, 2 to 5 courses each,
intake values such as 60, 120, 180, some courses with supernumerary seats.
"""

from datetime import date

from app.integrations.interfaces import (
    AicteCourseInfo,
    AicteInstitutionInfo,
    AicteMasterClient,
)


def _build_default_30_colleges() -> dict[str, AicteInstitutionInfo]:
    """Generate the canonical 30 simulated colleges across 8 states."""
    data = [
        # Maharashtra
        (
            "1-10000001",
            "Pune Institute of Advanced Engineering & Technology",
            "Maharashtra",
            "Pune",
            "Survey 45, Katraj-Dehu Road Bypass, Pune 411046",
            "contact@piaet-pune.edu.in",
            "9822011221",
            "Dr. Rajesh Deshmukh",
            "Savitribai Phule Pune University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo(
                    "Electronics and Telecommunication", "UG", "Electronics", 4, True, 120, 6
                ),
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, False, 60, 0),
                AicteCourseInfo(
                    "Artificial Intelligence & Data Science",
                    "PG",
                    "Computer Science",
                    2,
                    True,
                    60,
                    3,
                ),
            ],
        ),
        (
            "1-10000002",
            "Mumbai Metropolitan Institute of Technology",
            "Maharashtra",
            "Mumbai",
            "Bandra-Kurla Complex, Bandra East, Mumbai 400051",
            "admin@mmit-mumbai.ac.in",
            "9822011222",
            "Dr. Sneha Kulkarni",
            "University of Mumbai",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo(
                    "Information Technology", "UG", "Information Technology", 4, True, 120, 6
                ),
                AicteCourseInfo("Computer Engineering", "UG", "Computer Science", 4, True, 180, 9),
                AicteCourseInfo(
                    "Data Science & Business Analytics", "PGDM", "Management", 2, False, 60, 0
                ),
            ],
        ),
        (
            "1-10000003",
            "Nagpur Government Engineering College",
            "Maharashtra",
            "Nagpur",
            "Civil Lines, Nagpur 440001",
            "office@ngec-nagpur.gov.in",
            "9822011223",
            "Dr. Vijay Wankhede",
            "Rashtrasant Tukadoji Maharaj Nagpur University",
            "active",
            date(2029, 6, 30),
            [
                AicteCourseInfo("Civil Engineering", "UG", "Civil", 4, False, 60, 0),
                AicteCourseInfo("Electrical Engineering", "UG", "Electrical", 4, True, 60, 3),
            ],
        ),
        # Karnataka
        (
            "1-10000004",
            "Bengaluru National Institute of Technology & Science",
            "Karnataka",
            "Bengaluru",
            "Outer Ring Road, Marathahalli, Bengaluru 560037",
            "director@bnits-blr.edu.in",
            "9845011224",
            "Dr. Ramesh Rao",
            "Visvesvaraya Technological University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo(
                    "Information Science and Engineering",
                    "UG",
                    "Information Science",
                    4,
                    True,
                    120,
                    6,
                ),
                AicteCourseInfo("Cyber Security", "PG", "Computer Science", 2, True, 60, 3),
                AicteCourseInfo(
                    "Master of Computer Applications", "PG", "Computer Science", 2, False, 60, 0
                ),
            ],
        ),
        (
            "1-10000005",
            "Mysuru Royal College of Engineering",
            "Karnataka",
            "Mysuru",
            "Hunsur Road, Mysuru 570012",
            "info@mrce-mysuru.ac.in",
            "9845011225",
            "Dr. Ananth Murthy",
            "Visvesvaraya Technological University",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, True, 120, 6),
                AicteCourseInfo(
                    "Industrial Production Engineering", "UG", "Production", 4, False, 60, 0
                ),
                AicteCourseInfo(
                    "Electronics and Instrumentation", "UG", "Electronics", 4, False, 60, 0
                ),
            ],
        ),
        (
            "1-10000006",
            "Hubballi Technical Institute",
            "Karnataka",
            "Hubballi",
            "Vidyanagar, Hubballi 580031",
            "principal@hti-hubballi.ac.in",
            "9845011226",
            "Dr. Girish Patil",
            "Visvesvaraya Technological University",
            "active",
            date(2026, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 60, 3
                ),
                AicteCourseInfo(
                    "Diploma in Mechanical Engineering", "Diploma", "Mechanical", 3, False, 60, 0
                ),
            ],
        ),
        # Tamil Nadu
        (
            "1-10000007",
            "Madras Advanced Engineering Institute",
            "Tamil Nadu",
            "Chennai",
            "OMR IT Corridor, Thoraipakkam, Chennai 600097",
            "registrar@maei-chennai.edu.in",
            "9840011227",
            "Dr. S. Subramanian",
            "Anna University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo("Biomedical Engineering", "UG", "Biomedical", 4, True, 60, 3),
                AicteCourseInfo("VLSI Design", "PG", "Electronics", 2, True, 60, 3),
                AicteCourseInfo("Robotics and Automation", "UG", "Robotics", 4, False, 60, 0),
                AicteCourseInfo(
                    "Diploma in Electrical Engineering", "Diploma", "Electrical", 3, False, 60, 0
                ),
            ],
        ),
        (
            "1-10000008",
            "Coimbatore Institute of Applied Sciences",
            "Tamil Nadu",
            "Coimbatore",
            "Avinashi Road, Peelamedu, Coimbatore 641004",
            "contact@cias-cbe.edu.in",
            "9840011228",
            "Dr. Meenakshi Sundaram",
            "Anna University",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo("Textile Technology", "UG", "Textile", 4, False, 60, 0),
                AicteCourseInfo("Mechatronics", "UG", "Mechatronics", 4, True, 60, 3),
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
            ],
        ),
        (
            "1-10000009",
            "Madurai Regional Technical College",
            "Tamil Nadu",
            "Madurai",
            "Alagar Kovil Road, Madurai 625002",
            "principal@mrtc-madurai.edu.in",
            "9840011229",
            "Dr. K. Pandian",
            "Anna University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo("Civil Engineering", "UG", "Civil", 4, False, 60, 0),
                AicteCourseInfo(
                    "Electrical and Electronics Engineering", "UG", "Electrical", 4, True, 120, 6
                ),
            ],
        ),
        # Uttar Pradesh
        (
            "1-10000010",
            "Lucknow National College of Engineering",
            "Uttar Pradesh",
            "Lucknow",
            "Sitapur Road, Bakshi Ka Talab, Lucknow 226201",
            "head@lnce-lucknow.ac.in",
            "9415011230",
            "Dr. Arvind Tripathi",
            "Dr. A.P.J. Abdul Kalam Technical University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo(
                    "Information Technology", "UG", "Information Technology", 4, True, 120, 6
                ),
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, False, 60, 0),
            ],
        ),
        (
            "1-10000011",
            "Kanpur Institute of Information Technology",
            "Uttar Pradesh",
            "Kanpur",
            "GT Road, Kalyanpur, Kanpur 208016",
            "info@kiit-kanpur.ac.in",
            "9415011231",
            "Dr. Pradeep Mishra",
            "Dr. A.P.J. Abdul Kalam Technical University",
            "active",
            date(2029, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
                AicteCourseInfo("Chemical Engineering", "UG", "Chemical", 4, False, 60, 0),
            ],
        ),
        (
            "1-10000012",
            "Noida International Engineering Academy",
            "Uttar Pradesh",
            "Noida",
            "Sector 62, Institutional Area, Noida 201309",
            "dean@niea-noida.edu.in",
            "9415011232",
            "Dr. Shalini Saxena",
            "Dr. A.P.J. Abdul Kalam Technical University",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo(
                    "Artificial Intelligence & Machine Learning",
                    "UG",
                    "Computer Science",
                    4,
                    True,
                    120,
                    6,
                ),
                AicteCourseInfo(
                    "Post Graduate Diploma in Management", "PGDM", "Management", 2, True, 120, 6
                ),
            ],
        ),
        # Delhi
        (
            "1-10000013",
            "Delhi Technological & Applied Sciences Institute",
            "Delhi",
            "New Delhi",
            "Bawana Road, Shahbad Daulatpur, Delhi 110042",
            "director@dtasi-delhi.ac.in",
            "9811011233",
            "Dr. Harsh Vardhan",
            "Delhi Technological University",
            "active",
            date(2029, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo("Software Engineering", "UG", "Computer Science", 4, True, 120, 6),
                AicteCourseInfo("Environmental Engineering", "UG", "Civil", 4, False, 60, 0),
            ],
        ),
        (
            "1-10000014",
            "Indraprastha Engineering Academy",
            "Delhi",
            "North Delhi",
            "Kashmere Gate, Delhi 110006",
            "principal@iea-delhi.ac.in",
            "9811011234",
            "Dr. Sunita Sen",
            "Guru Gobind Singh Indraprastha University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Electronics and Communication", "UG", "Electronics", 4, True, 120, 6
                ),
                AicteCourseInfo(
                    "Information Technology", "UG", "Information Technology", 4, True, 120, 6
                ),
            ],
        ),
        # Gujarat
        (
            "1-10000015",
            "Ahmedabad Engineering and Technology Institute",
            "Gujarat",
            "Ahmedabad",
            "SG Highway, Gota, Ahmedabad 382481",
            "office@aeti-ahmedabad.ac.in",
            "9825011235",
            "Dr. Bhavesh Patel",
            "Gujarat Technological University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo(
                    "Information Technology", "UG", "Information Technology", 4, True, 120, 6
                ),
                AicteCourseInfo("Civil Engineering", "UG", "Civil", 4, False, 60, 0),
                AicteCourseInfo("Electrical Engineering", "UG", "Electrical", 4, False, 60, 0),
            ],
        ),
        (
            "1-10000016",
            "Vadodara State Institute of Technology",
            "Gujarat",
            "Vadodara",
            "Sayajigunj, Vadodara 390002",
            "principal@vsit-baroda.edu.in",
            "9825011236",
            "Dr. Chetan Bhatt",
            "Gujarat Technological University",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo("Petrochemical Engineering", "UG", "Chemical", 4, False, 60, 0),
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, True, 60, 3),
            ],
        ),
        (
            "1-10000017",
            "Surat Advanced Technical College",
            "Gujarat",
            "Surat",
            "Dumas Road, Surat 395007",
            "info@satc-surat.ac.in",
            "9825011237",
            "Dr. Manoj Shah",
            "Gujarat Technological University",
            "active",
            date(2029, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
                AicteCourseInfo("Chemical Engineering", "UG", "Chemical", 4, True, 60, 3),
            ],
        ),
        # West Bengal
        (
            "1-10000018",
            "Kolkata Institute of Technology & Management",
            "West Bengal",
            "Kolkata",
            "Sector V, Salt Lake, Kolkata 700091",
            "head@kitm-kolkata.edu.in",
            "9830011238",
            "Dr. Soumen Banerjee",
            "Maulana Abul Kalam Azad University of Technology",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo(
                    "Electronics and Communication", "UG", "Electronics", 4, True, 120, 6
                ),
                AicteCourseInfo(
                    "Information Technology", "UG", "Information Technology", 4, True, 60, 3
                ),
            ],
        ),
        (
            "1-10000019",
            "Durgapur Regional Engineering College",
            "West Bengal",
            "Durgapur",
            "Mahatma Gandhi Avenue, Durgapur 713209",
            "contact@drec-durgapur.edu.in",
            "9830011239",
            "Dr. Kalyan Ghosh",
            "Maulana Abul Kalam Azad University of Technology",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo(
                    "Metallurgical and Materials Engineering", "UG", "Metallurgy", 4, False, 60, 0
                ),
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, True, 120, 6),
            ],
        ),
        (
            "1-10000020",
            "Bengal Institute of Applied Sciences",
            "West Bengal",
            "Howrah",
            "Shibpur, Howrah 711103",
            "admin@bias-howrah.ac.in",
            "9830011240",
            "Dr. Anirban Roy",
            "Maulana Abul Kalam Azad University of Technology",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
                AicteCourseInfo("Electrical Engineering", "UG", "Electrical", 4, False, 60, 0),
            ],
        ),
        # Telangana
        (
            "1-10000021",
            "Hyderabad Institute of Technology & Management",
            "Telangana",
            "Hyderabad",
            "HITEC City, Madhapur, Hyderabad 500081",
            "director@hitm-hyd.ac.in",
            "9849011241",
            "Dr. K. V. Ramana",
            "Jawaharlal Nehru Technological University Hyderabad",
            "active",
            date(2029, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 180, 9
                ),
                AicteCourseInfo("Data Science", "UG", "Computer Science", 4, True, 120, 6),
                AicteCourseInfo("Cyber Security", "UG", "Computer Science", 4, True, 60, 3),
                AicteCourseInfo(
                    "Master of Business Administration", "PG", "Management", 2, False, 120, 0
                ),
            ],
        ),
        (
            "1-10000022",
            "Warangal Regional Engineering College",
            "Telangana",
            "Warangal",
            "Kazipet, Warangal 506004",
            "principal@wrec-warangal.ac.in",
            "9849011242",
            "Dr. T. Srinivas",
            "Kakatiya University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo("Civil Engineering", "UG", "Civil", 4, False, 60, 0),
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, True, 60, 3),
            ],
        ),
        (
            "1-10000023",
            "Secunderabad Institute of Technological Studies",
            "Telangana",
            "Hyderabad",
            "Maredpally, Secunderabad 500026",
            "contact@sits-secunderabad.edu.in",
            "9849011243",
            "Dr. N. Sudhakar",
            "Osmania University",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
                AicteCourseInfo(
                    "Electronics and Communication", "UG", "Electronics", 4, True, 60, 3
                ),
            ],
        ),
        # Additional across the 8 states to make exactly 30
        (
            "1-10000024",
            "Chhatrapati Sambhajinagar Engineering Institute",
            "Maharashtra",
            "Chhatrapati Sambhajinagar",
            "Station Road, Aurangabad 431005",
            "contact@csei-mh.edu.in",
            "9822011244",
            "Dr. Santosh Jadhav",
            "Dr. Babasaheb Ambedkar Marathwada University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, False, 60, 0),
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
            ],
        ),
        (
            "1-10000025",
            "Mangalore Coast Institute of Technology",
            "Karnataka",
            "Mangalore",
            "Kottara Chowki, Mangalore 575006",
            "admin@mcit-mangalore.edu.in",
            "9845011245",
            "Dr. Praveen Hegde",
            "Visvesvaraya Technological University",
            "active",
            date(2027, 6, 30),
            [
                AicteCourseInfo("Marine Engineering", "UG", "Marine", 4, False, 60, 0),
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
            ],
        ),
        (
            "1-10000026",
            "Tiruchirappalli Technical Institute",
            "Tamil Nadu",
            "Tiruchirappalli",
            "Thuvakudi, Tiruchirappalli 620015",
            "office@tti-trichy.ac.in",
            "9840011246",
            "Dr. R. Natarajan",
            "Anna University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Instrumentation and Control", "UG", "Instrumentation", 4, True, 60, 3
                ),
                AicteCourseInfo("Production Engineering", "UG", "Production", 4, False, 60, 0),
            ],
        ),
        (
            "1-10000027",
            "Varanasi Engineering & Management Institute",
            "Uttar Pradesh",
            "Varanasi",
            "Ashapur, Sarnath, Varanasi 221007",
            "dean@vemi-varanasi.edu.in",
            "9415011247",
            "Dr. Rakesh Pandey",
            "Dr. A.P.J. Abdul Kalam Technical University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
                AicteCourseInfo(
                    "Post Graduate Diploma in Management", "PGDM", "Management", 2, True, 60, 3
                ),
            ],
        ),
        (
            "1-10000028",
            "South Delhi Polytechnic & Engineering Academy",
            "Delhi",
            "South Delhi",
            "Okhla Industrial Area Phase III, New Delhi 110020",
            "principal@sdpea-delhi.ac.in",
            "9811011248",
            "Dr. Neeraj Malik",
            "Delhi Skill and Entrepreneurship University",
            "active",
            date(2028, 6, 30),
            [
                AicteCourseInfo(
                    "Diploma in Computer Engineering",
                    "Diploma",
                    "Computer Science",
                    3,
                    False,
                    60,
                    0,
                ),
                AicteCourseInfo(
                    "Diploma in Civil Engineering", "Diploma", "Civil", 3, False, 60, 0
                ),
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, True, 120, 6
                ),
            ],
        ),
        (
            "1-10000029",
            "Rajkot Institute of Technology (Suspended)",
            "Gujarat",
            "Rajkot",
            "Kalawad Road, Rajkot 360005",
            "admin@rit-rajkot.ac.in",
            "9825011249",
            "Dr. Dhaval Dave",
            "Gujarat Technological University",
            "suspended",  # suspended edge case
            date(2026, 6, 30),
            [
                AicteCourseInfo("Mechanical Engineering", "UG", "Mechanical", 4, False, 60, 0),
                AicteCourseInfo("Electrical Engineering", "UG", "Electrical", 4, False, 60, 0),
            ],
        ),
        (
            "1-10000030",
            "Cyberabad Technical College (Expired)",
            "Telangana",
            "Rangareddy",
            "Gachibowli, Rangareddy 500032",
            "office@ctc-cyberabad.ac.in",
            "9849011250",
            "Dr. Madhavi Latha",
            "Jawaharlal Nehru Technological University Hyderabad",
            "expired",  # expired approval edge case
            date(2024, 6, 30),
            [
                AicteCourseInfo(
                    "Computer Science and Engineering", "UG", "Computer Science", 4, False, 60, 0
                ),
                AicteCourseInfo(
                    "Information Technology", "UG", "Information Technology", 4, False, 60, 0
                ),
            ],
        ),
    ]

    colleges = {}
    for (
        aicte_id,
        name,
        state,
        district,
        address,
        email,
        phone,
        head,
        univ,
        approval_status,
        valid_to,
        courses,
    ) in data:
        colleges[aicte_id] = AicteInstitutionInfo(
            aicte_id=aicte_id,
            name=name,
            state=state,
            district=district,
            address=address,
            official_email=email,
            official_phone=phone,
            head_name=head,
            affiliating_university=univ,
            approval_status=approval_status,
            approval_valid_to=valid_to,
            courses=courses,
        )
    return colleges


class MockAicteMasterClient(AicteMasterClient):
    """Simulated AICTE master registry client with 30 institutions across 8 states."""

    def __init__(
        self,
        institutions: dict[str, AicteInstitutionInfo] | None = None,
    ) -> None:
        self._institutions = (
            institutions if institutions is not None else _build_default_30_colleges()
        )

    def get_institution(self, aicte_id: str) -> AicteInstitutionInfo | None:
        """Retrieve institution by AICTE ID."""
        return self._institutions.get(aicte_id)

    def list_institutions(self) -> list[AicteInstitutionInfo]:
        """List all institutions in the AICTE master list."""
        return list(self._institutions.values())

    def get_courses(self, aicte_id: str) -> list[AicteCourseInfo]:
        """List approved courses for an institution."""
        inst = self.get_institution(aicte_id)
        if inst is None:
            return []
        return inst.courses
